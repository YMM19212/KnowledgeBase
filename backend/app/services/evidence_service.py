import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.models.db import ChunkRecord, EvidenceUnit
from backend.app.services.settings_service import AppSettingsService, EffectiveLLMSettings

logger = logging.getLogger(__name__)


@dataclass
class EvidencePayload:
    evidence_type: str
    canonical_section: str
    claim_text: str
    normalized_facts: dict[str, Any]
    confidence: float


class KimiEvidenceEnricher:
    """Optional OpenAI-compatible evidence enrichment client."""

    def __init__(self, settings: EffectiveLLMSettings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.provider.lower() in {"moonshot", "kimi", "openai-compatible"}
            and self.settings.base_url
            and self.settings.api_key
            and self.settings.model
        )

    def enrich(self, chunk: ChunkRecord, payload: EvidencePayload) -> EvidencePayload:
        if not self.configured:
            return payload
        system_prompt = (
            "You extract structured evidence from medical literature chunks. "
            "Return JSON only. Do not add unsupported facts. Preserve numbers, units, "
            "groups, p-values, timepoints, table/figure references, and limitations."
        )
        user_prompt = {
            "section_path": chunk.section_path,
            "content_type": chunk.content_type,
            "citation_text": payload.normalized_facts.get("citation_text"),
            "source_text": chunk.content[:12000],
            "fallback_evidence_type": payload.evidence_type,
        }
        response = httpx.post(
            f"{self.settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.api_key}"},
            json={
                "model": self.settings.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Extract evidence as JSON with keys: evidence_type, claim_text, "
                            "medical_entities, outcomes, groups, timepoints, values, units, "
                            "limitations, evidence_sufficiency.\n\n"
                            f"{json.dumps(user_prompt, ensure_ascii=False)}"
                        ),
                    },
                ],
                "temperature": 0,
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = self._parse_json(content)
        facts = {
            **payload.normalized_facts,
            "llm_enriched": True,
            "medical_entities": data.get("medical_entities", []),
            "outcomes": data.get("outcomes", []),
            "groups": data.get("groups", []),
            "timepoints": data.get("timepoints", []),
            "values": data.get("values", []),
            "units": data.get("units", []),
            "limitations": data.get("limitations", []),
            "evidence_sufficiency": data.get(
                "evidence_sufficiency", payload.normalized_facts["evidence_sufficiency"]
            ),
        }
        return EvidencePayload(
            evidence_type=data.get("evidence_type") or payload.evidence_type,
            canonical_section=payload.canonical_section,
            claim_text=data.get("claim_text") or payload.claim_text,
            normalized_facts=facts,
            confidence=max(payload.confidence, 0.85),
        )

    def _parse_json(self, content: str) -> dict[str, Any]:
        content = content.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", content, re.S)
        if fenced:
            content = fenced.group(1).strip()
        return json.loads(content)


class EvidenceService:
    """Builds evidence units from chunks and keeps chunk metadata in sync."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm_settings = AppSettingsService(db).effective_llm_settings()
        self.enricher = KimiEvidenceEnricher(self.llm_settings)

    def rebuild_knowledge_base(self, knowledge_base_id: int) -> int:
        document_ids = self.db.scalars(
            select(ChunkRecord.document_id)
            .where(ChunkRecord.knowledge_base_id == knowledge_base_id)
            .distinct()
        ).all()
        count = 0
        for document_id in document_ids:
            count += self.replace_document_evidence(knowledge_base_id, document_id)
        return count

    def replace_document_evidence(self, knowledge_base_id: int, document_id: str) -> int:
        self.db.execute(
            delete(EvidenceUnit).where(
                EvidenceUnit.knowledge_base_id == knowledge_base_id,
                EvidenceUnit.document_id == document_id,
            )
        )
        chunks = self.db.scalars(
            select(ChunkRecord)
            .where(
                ChunkRecord.knowledge_base_id == knowledge_base_id,
                ChunkRecord.document_id == document_id,
            )
            .order_by(ChunkRecord.id)
        ).all()
        count = 0
        for chunk in chunks:
            payload = self._build_rule_payload(chunk)
            try:
                payload = self.enricher.enrich(chunk, payload)
            except Exception as exc:  # pragma: no cover - depends on remote API
                logger.warning("Kimi evidence enrichment failed for %s: %s", chunk.chunk_id, exc)
                payload.normalized_facts["llm_error"] = str(exc)[:500]
            self._sync_chunk_metadata(chunk, payload)
            self.db.add(
                EvidenceUnit(
                    knowledge_base_id=knowledge_base_id,
                    document_id=document_id,
                    chunk_id=chunk.chunk_id,
                    evidence_type=payload.evidence_type,
                    canonical_section=payload.canonical_section,
                    claim_text=payload.claim_text,
                    normalized_facts_json=json.dumps(
                        payload.normalized_facts, ensure_ascii=False
                    ),
                    source_text=chunk.content,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    citation_text=payload.normalized_facts.get("citation_text", ""),
                    confidence=payload.confidence,
                )
            )
            count += 1
        self.db.commit()
        return count

    def list_by_document(self, document_id: str) -> list[EvidenceUnit]:
        return list(
            self.db.scalars(
                select(EvidenceUnit)
                .where(EvidenceUnit.document_id == document_id)
                .order_by(EvidenceUnit.id)
            )
        )

    def list_by_knowledge_base(self, knowledge_base_id: int) -> list[EvidenceUnit]:
        return list(
            self.db.scalars(
                select(EvidenceUnit)
                .where(EvidenceUnit.knowledge_base_id == knowledge_base_id)
                .order_by(EvidenceUnit.id)
            )
        )

    def find_for_chunks(self, chunk_ids: list[str]) -> list[EvidenceUnit]:
        if not chunk_ids:
            return []
        return list(
            self.db.scalars(
                select(EvidenceUnit)
                .where(EvidenceUnit.chunk_id.in_(chunk_ids))
                .order_by(EvidenceUnit.confidence.desc(), EvidenceUnit.id)
            )
        )

    def _build_rule_payload(self, chunk: ChunkRecord) -> EvidencePayload:
        metadata = json.loads(chunk.metadata_json or "{}")
        canonical = str(metadata.get("canonical_section") or self._canonical_section(chunk))
        evidence_type = self._evidence_type(chunk, canonical)
        facts = {
            "llm_enriched": False,
            "medical_entities": self._extract_medical_entities(chunk.content),
            "outcomes": self._extract_outcome_sentences(chunk.content),
            "groups": self._extract_groups(chunk.content),
            "timepoints": self._extract_timepoints(chunk.content),
            "values": self._extract_values(chunk.content),
            "units": self._extract_units(chunk.content),
            "limitations": self._extract_limitations(chunk.content),
            "evidence_sufficiency": self._evidence_sufficiency(chunk),
            "citation_text": metadata.get("citation_text", ""),
            "content_type": chunk.content_type,
            "section_path": chunk.section_path,
        }
        return EvidencePayload(
            evidence_type=evidence_type,
            canonical_section=canonical,
            claim_text=self._claim_text(chunk.content),
            normalized_facts=facts,
            confidence=self._confidence(chunk, evidence_type),
        )

    def _sync_chunk_metadata(self, chunk: ChunkRecord, payload: EvidencePayload) -> None:
        metadata = json.loads(chunk.metadata_json or "{}")
        metadata.update(
            {
                "evidence_type": payload.evidence_type,
                "canonical_section": payload.canonical_section,
                "evidence_sufficiency": payload.normalized_facts.get(
                    "evidence_sufficiency", "partial"
                ),
                "llm_enriched": payload.normalized_facts.get("llm_enriched", False),
            }
        )
        chunk.metadata_json = json.dumps(metadata, ensure_ascii=False)

    def _canonical_section(self, chunk: ChunkRecord) -> str:
        section = chunk.section_path.lower()
        if re.search(r"primary outcome|primary endpoint|主要结局|主要终点", section):
            return "primary outcome"
        if re.search(r"secondary outcome|secondary endpoint|次要结局|次要终点", section):
            return "secondary outcome"
        if re.search(r"adverse|safety|harms|不良|安全", section):
            return "adverse events"
        if re.search(r"result|结果", section):
            return "results"
        if re.search(r"method|方法", section):
            return "methods"
        if re.search(r"conclusion|结论", section):
            return "conclusion"
        if re.search(r"discussion|讨论", section):
            return "discussion"
        return "other"

    def _evidence_type(self, chunk: ChunkRecord, canonical: str) -> str:
        section = chunk.section_path.lower()
        content = chunk.content.lower()
        if chunk.content_type == "table":
            return "table_evidence"
        if chunk.content_type == "figure_caption":
            return "figure_evidence"
        if re.search(r"问题[一二三四五六七八九十\d]+", chunk.section_path):
            return "clinical_question_answer"
        if canonical == "primary outcome":
            return "primary_outcome"
        if canonical == "secondary outcome":
            return "secondary_outcome"
        if canonical == "adverse events":
            return "safety_or_adverse_event"
        if canonical == "results" and (chunk.page_start == 1 or "abstract" in section):
            return "abstract_result"
        if re.search(r"\btable\s*\d+|表\s*\d+", content):
            return "table_evidence"
        if re.search(r"\bfig(?:ure)?\.?\s*\d+|图\s*\d+", content):
            return "figure_evidence"
        if canonical != "other":
            return f"{canonical.replace(' ', '_')}_evidence"
        return "text_evidence"

    def _claim_text(self, text: str) -> str:
        sentences = re.split(r"(?<=[。.!?])\s+", text.strip())
        for sentence in sentences:
            if re.search(r"\d|±|%|p\s*[<=>]|significant|显著|主要|结果", sentence, re.I):
                return sentence[:900]
        return text.strip()[:900]

    def _extract_outcome_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[。.!?])\s+", text.strip())
        return [
            sentence[:500]
            for sentence in sentences
            if re.search(
                r"outcome|endpoint|mortality|ci|primary|secondary|结局|终点|死亡",
                sentence,
                re.I,
            )
        ][:5]

    def _extract_values(self, text: str) -> list[str]:
        text = self._normalize_numeric_text(text)
        patterns = [
            r"[+-]?\d+(?:\.\d+)?\s*(?:±|\+/-)\s*\d+(?:\.\d+)?",
            r"\bp\s*[<=>]\s*0?\.\d+",
            r"\d+(?:\.\d+)?\s*%",
            r"\b\d+(?:\.\d+)?\s*(?:mg/kg|mmol/l|l/min/m2|l/min|ml/h|μmol/l)\b",
        ]
        values: list[str] = []
        for pattern in patterns:
            values.extend(re.findall(pattern, text, flags=re.I))
        return list(dict.fromkeys(values))[:20]

    def _extract_units(self, text: str) -> list[str]:
        text = self._normalize_numeric_text(text)
        units = re.findall(
            r"(?:l/min/m\^?2|l/min/m2|l/min|ml/h|mg/kg|mmol/l|μmol/l|mm hg|%)",
            text,
            flags=re.I,
        )
        if "/min/m2" in text.lower() and "l/min/m2" not in [unit.lower() for unit in units]:
            units.append("l/min/m2")
        return list(dict.fromkeys(units))[:20]

    def _normalize_numeric_text(self, text: str) -> str:
        text = re.sub(r"\\(?:mathrm|mathsf|bf|boldsymbol)\s*\{([^{}]*)\}", r"\1", text)
        text = text.replace("\\pm", "±").replace("\\Delta", "Δ")
        text = re.sub(r"\bm\s*i\s*n\b", "min", text, flags=re.I)
        text = re.sub(r"(?<=\d)\s+\.\s+(?=\d)", ".", text)
        text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
        text = re.sub(r"\s*/\s*", "/", text)
        text = re.sub(r"\bm\s*\^\s*\{\s*2\s*\}", "m2", text, flags=re.I)
        text = re.sub(r"\s*\^\s*\{\s*2\s*\}", "2", text)
        return text

    def _extract_timepoints(self, text: str) -> list[str]:
        matches = re.findall(
            r"\b\d+\s*(?:min|minutes?|h|hours?|days?|weeks?|months?|mo|years?|yr|d)\b",
            text,
            flags=re.I,
        )
        matches.extend(re.findall(r"\d+\s*(?:分钟|小时|天|周|月|年)", text))
        return list(dict.fromkeys(matches))[:20]

    def _extract_groups(self, text: str) -> list[str]:
        groups = re.findall(
            r"\b(?:Impella(?: LP2\.5)?|IABP|LVAD|control|intervention|placebo)[\w .-]*",
            text,
            flags=re.I,
        )
        groups.extend(re.findall(r"[\u4e00-\u9fff]{2,12}(?:组|患者|人群)", text))
        return list(dict.fromkeys(group.strip() for group in groups if group.strip()))[:20]

    def _extract_medical_entities(self, text: str) -> list[str]:
        patterns = [
            "cardiogenic shock",
            "acute myocardial infarction",
            "aortic dissection",
            "endometriosis",
            "Impella",
            "IABP",
            "主动脉夹层",
            "子宫内膜异位症",
            "彩色多普勒",
            "CDFI",
        ]
        text_lower = text.lower()
        return [entity for entity in patterns if entity.lower() in text_lower]

    def _extract_limitations(self, text: str) -> list[str]:
        if not re.search(r"limitation|局限", text, re.I):
            return []
        return [self._claim_text(text)]

    def _evidence_sufficiency(self, chunk: ChunkRecord) -> str:
        if chunk.content_type in {"table", "figure_caption"}:
            return "sufficient" if len(chunk.content.strip()) > 20 else "partial"
        if re.search(r"\d|±|%|table|figure|图|表", chunk.content, re.I):
            return "sufficient"
        return "partial"

    def _confidence(self, chunk: ChunkRecord, evidence_type: str) -> float:
        if evidence_type in {"table_evidence", "figure_evidence"}:
            return 0.8
        if re.search(r"\d|±|%|p\s*[<=>]", chunk.content, re.I):
            return 0.75
        return 0.55


def evidence_unit_to_dict(unit: EvidenceUnit) -> dict[str, Any]:
    return {
        "id": unit.id,
        "knowledge_base_id": unit.knowledge_base_id,
        "document_id": unit.document_id,
        "chunk_id": unit.chunk_id,
        "evidence_type": unit.evidence_type,
        "canonical_section": unit.canonical_section,
        "claim_text": unit.claim_text,
        "normalized_facts": json.loads(unit.normalized_facts_json or "{}"),
        "source_text": unit.source_text,
        "page_start": unit.page_start,
        "page_end": unit.page_end,
        "citation_text": unit.citation_text,
        "confidence": unit.confidence,
        "created_at": unit.created_at.isoformat() if unit.created_at else None,
    }
