import json
import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.db import ChunkRecord, DocumentRecord
from backend.app.rag.embeddings import EmbeddingService, get_embedding_service
from backend.app.rag.llm import OpenAICompatibleLLM
from backend.app.rag.query_guard import QueryGuard
from backend.app.services.evidence_service import EvidenceService, evidence_unit_to_dict
from backend.app.services.settings_service import AppSettingsService
from backend.app.vectorstores.factory import get_vector_store

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingService | None = None,
        llm: OpenAICompatibleLLM | None = None,
    ) -> None:
        self.db = db
        app_settings = AppSettingsService(db)
        runtime_embedding = app_settings.effective_embedding_settings()
        runtime_llm = app_settings.effective_llm_settings()
        self.embeddings = embeddings or get_embedding_service(runtime_embedding)
        self.vector_store = get_vector_store(db)
        self.llm = llm or OpenAICompatibleLLM(runtime_settings=runtime_llm)
        self.query_guard = QueryGuard(db, self.llm)
        self.settings = get_settings()

    def query(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        effective_filters = self._infer_filters_from_query(knowledge_base_id, query)
        effective_filters.update(filters or {})
        guard_decision = self.query_guard.evaluate(knowledge_base_id, query, effective_filters)
        if guard_decision.action in {"reject", "needs_hint"}:
            logger.info(
                "rag query kb_id=%s top_k=%s filters=%s answer_mode=%s reason=%s",
                knowledge_base_id,
                top_k,
                effective_filters,
                f"guard-{guard_decision.action}",
                guard_decision.reason,
            )
            return {
                "answer": guard_decision.message or "证据不足，无法可靠回答。",
                "citations": [],
                "retrieved_chunks": [],
                "evidence_units": [],
                "evidence_sufficiency": "insufficient",
                "answer_mode": f"guard-{guard_decision.action}",
                "guard_reason": guard_decision.reason,
            }
        query_vector = self.embeddings.embed_query(query)
        search_k = max(top_k * 10, top_k)
        results = self.vector_store.similarity_search(
            knowledge_base_id, query_vector, search_k, effective_filters
        )
        enriched = self._rerank(query, [self._enrich_result(result) for result in results])[:top_k]
        usable = [item for item in enriched if item["score"] >= self.settings.rag_min_score]
        evidence_units = self._evidence_for_results([item["chunk_id"] for item in usable])
        if not usable:
            logger.info(
                "rag query kb_id=%s top_k=%s filters=%s answer_mode=insufficient retrieved=%s",
                knowledge_base_id,
                top_k,
                effective_filters,
                len(enriched),
            )
            return {
                "answer": "证据不足，无法可靠回答。",
                "citations": [],
                "retrieved_chunks": enriched,
                "evidence_units": [],
                "evidence_sufficiency": "insufficient",
                "answer_mode": "insufficient",
                "guard_reason": guard_decision.reason,
            }
        answer_mode = "extractive"
        try:
            answer = (
                self.llm.answer(query, usable)
                if self.llm.configured
                else self._extractive_answer(query, usable)
            )
            answer_mode = "llm" if self.llm.configured else "extractive"
        except Exception as exc:
            logger.warning("LLM answer synthesis failed, falling back to extractive: %s", exc)
            answer = self._extractive_answer(query, usable)
            answer_mode = "extractive-fallback"
        logger.info(
            (
                "rag query kb_id=%s top_k=%s filters=%s answer_mode=%s "
                "retrieved=%s usable=%s top_score=%.4f"
            ),
            knowledge_base_id,
            top_k,
            effective_filters,
            answer_mode,
            len(enriched),
            len(usable),
            usable[0]["score"] if usable else 0.0,
        )
        return {
            "answer": answer,
            "citations": [
                {
                    "chunk_id": item["chunk_id"],
                    "document_id": item["document_id"],
                    "section_path": item["section_path"],
                    "page_start": item["page_start"],
                    "page_end": item["page_end"],
                    "citation_text": item["citation_text"],
                    "source_text": item["source_text"],
                    "score": item["score"],
                }
                for item in usable
            ],
            "retrieved_chunks": enriched,
            "evidence_units": evidence_units,
            "evidence_sufficiency": self._evidence_sufficiency(evidence_units),
            "answer_mode": answer_mode,
            "guard_reason": guard_decision.reason,
        }

    def _rerank(self, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        intent = self._analyze_query_intent(query)
        requested = intent["requested_sections"]
        reranked: list[dict[str, Any]] = []
        for item in results:
            adjusted = dict(item)
            score = float(adjusted["score"])
            metadata = adjusted.get("metadata", {})
            section_path = str(adjusted.get("section_path") or "").lower()
            content_type = str(adjusted.get("content_type") or "").lower()
            evidence_type = str(metadata.get("evidence_type") or "").lower()
            citation_text = str(adjusted.get("citation_text") or "").lower()
            document_title = str(adjusted.get("document_title") or "").lower()
            table_id = str(metadata.get("table_id") or "").lower()
            figure_id = str(metadata.get("figure_id") or "").lower()

            if "results" in requested and "result" in section_path:
                score += 0.25
            if "methods" in requested and "method" in section_path:
                score += 0.2
            if "conclusions" in requested and "conclusion" in section_path:
                score += 0.2
            if "discussion" in requested and "discussion" in section_path:
                score += 0.2
            if "table" in requested and content_type == "table":
                score += 0.35
            if "table" in requested and evidence_type == "table_evidence":
                score += 0.15
            if "figure" in requested and content_type == "figure_caption":
                score += 0.35
            if "figure" in requested and evidence_type == "figure_evidence":
                score += 0.15
            if "question" in requested and evidence_type == "clinical_question_answer":
                score += 0.35
            if "abstract" in requested and adjusted.get("page_start") == 1:
                abstract_sections = {
                    "objectives",
                    "background",
                    "methods",
                    "results",
                    "conclusions",
                    "abstract",
                    "摘要",
                }
                if any(section in section_path for section in abstract_sections):
                    score += 0.15

            if intent["table_refs"]:
                if table_id and table_id in intent["table_refs"]:
                    score += 0.55
                elif any(ref in citation_text for ref in intent["table_refs"]):
                    score += 0.25
            if intent["figure_refs"]:
                if figure_id and figure_id in intent["figure_refs"]:
                    score += 0.55
                elif any(ref in citation_text for ref in intent["figure_refs"]):
                    score += 0.25
            if intent["question_refs"]:
                if any(
                    ref in section_path or ref in citation_text
                    for ref in intent["question_refs"]
                ):
                    score += 0.45
            if intent["page_refs"]:
                page_start = adjusted.get("page_start")
                page_end = adjusted.get("page_end") or page_start
                if isinstance(page_start, int) and isinstance(page_end, int):
                    if any(page_start <= page <= page_end for page in intent["page_refs"]):
                        score += 0.35

            overlap = self._lexical_overlap(
                intent["query_terms"],
                {
                    section_path,
                    citation_text,
                    document_title,
                    str(adjusted.get("source_text") or "").lower(),
                },
            )
            score += min(0.18, overlap * 0.03)

            adjusted["score"] = score
            reranked.append(adjusted)
        return sorted(reranked, key=lambda item: item["score"], reverse=True)

    def _analyze_query_intent(self, query: str) -> dict[str, Any]:
        query_lower = query.lower()
        section_keywords = {
            "results": ["results", "结果"],
            "methods": ["methods", "方法"],
            "conclusions": ["conclusions", "conclusion", "结论"],
            "discussion": ["discussion", "讨论"],
            "table": ["table", "表格", "表 "],
            "figure": ["figure", "fig.", "图"],
            "abstract": ["abstract", "摘要"],
            "question": ["问题一", "问题二", "问题三", "问题四", "问题五"],
        }
        requested = {
            section
            for section, terms in section_keywords.items()
            if any(term in query_lower for term in terms)
        }
        table_refs = {
            f"t{match}"
            for match in re.findall(
                r"(?:table|表)\s*([0-9]{1,2})",
                query_lower,
                flags=re.IGNORECASE,
            )
        }
        figure_refs = {
            f"f{match}"
            for match in re.findall(
                r"(?:figure|fig\.?|图)\s*([0-9]{1,2})",
                query_lower,
                flags=re.IGNORECASE,
            )
        }
        normalized_pages: set[int] = set()
        for match in re.findall(
            r"(?:第\s*([0-9]{1,3})\s*页|p(?:age)?\.?\s*([0-9]{1,3}))",
            query_lower,
        ):
            for raw in match:
                if raw:
                    normalized_pages.add(int(raw))
        chinese_question_map = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }
        question_refs = {
            f"问题{match}"
            for match in re.findall(r"问题\s*([0-9]{1,2})", query)
        }
        question_refs.update(
            f"问题{char}"
            for char in chinese_question_map
            if f"问题{char}" in query
        )
        return {
            "requested_sections": requested,
            "table_refs": table_refs,
            "figure_refs": figure_refs,
            "page_refs": normalized_pages,
            "question_refs": {item.lower() for item in question_refs},
            "query_terms": self._tokenize_query_terms(query),
        }

    def _evidence_for_results(self, chunk_ids: list[str]) -> list[dict[str, Any]]:
        units = EvidenceService(self.db).find_for_chunks(chunk_ids)
        by_chunk: dict[str, dict[str, Any]] = {}
        for unit in units:
            by_chunk.setdefault(unit.chunk_id, evidence_unit_to_dict(unit))
        return [by_chunk[chunk_id] for chunk_id in chunk_ids if chunk_id in by_chunk]

    def _evidence_sufficiency(self, units: list[dict[str, Any]]) -> str:
        if not units:
            return "insufficient"
        statuses = [
            str(unit.get("normalized_facts", {}).get("evidence_sufficiency", "partial"))
            for unit in units
        ]
        return "sufficient" if any(status == "sufficient" for status in statuses) else "partial"

    def _infer_filters_from_query(
        self, knowledge_base_id: int, query: str
    ) -> dict[str, Any]:
        query_lower = query.lower()
        documents = self.db.scalars(
            select(DocumentRecord).where(DocumentRecord.knowledge_base_id == knowledge_base_id)
        ).all()
        for document in documents:
            candidates = {
                document.id,
                document.title,
                f"{document.id}.pdf",
                f"{document.title}.pdf",
            }
            if document.source_file:
                source = str(document.source_file)
                candidates.add(source)
                candidates.add(source.split("/")[-1])
            if any(candidate and candidate.lower() in query_lower for candidate in candidates):
                return {"document_id": document.id}
        return {}

    def _enrich_result(self, result) -> dict[str, Any]:
        chunk = self.db.scalar(select(ChunkRecord).where(ChunkRecord.chunk_id == result.chunk_id))
        document = (
            self.db.scalar(select(DocumentRecord).where(DocumentRecord.id == result.document_id))
            if result.document_id
            else None
        )
        metadata = dict(result.metadata)
        if chunk:
            metadata = {**json.loads(chunk.metadata_json or "{}"), **metadata}
        return {
            "chunk_id": result.chunk_id,
            "document_id": result.document_id,
            "document_title": document.title if document else result.document_id,
            "content": result.content,
            "source_text": result.content,
            "score": result.score,
            "section_path": metadata.get("section_path") or (chunk.section_path if chunk else ""),
            "page_start": metadata.get("page_start") or (chunk.page_start if chunk else None),
            "page_end": metadata.get("page_end") or (chunk.page_end if chunk else None),
            "content_type": metadata.get("content_type")
            or (chunk.content_type if chunk else "text"),
            "citation_text": metadata.get("citation_text") or "",
            "metadata": metadata,
        }

    def _tokenize_query_terms(self, query: str) -> set[str]:
        raw_terms = re.findall(r"[a-z0-9][a-z0-9._-]+|[\u4e00-\u9fff]{2,}", query.lower())
        stopwords = {
            "什么",
            "多少",
            "如何",
            "请问",
            "根据",
            "提取",
            "内容",
            "部分",
            "回答",
            "一下",
            "请用",
            "一句话",
        }
        return {term for term in raw_terms if term not in stopwords}

    def _lexical_overlap(self, query_terms: set[str], fields: set[str]) -> int:
        if not query_terms:
            return 0
        joined = "\n".join(field for field in fields if field)
        return sum(1 for term in query_terms if term and term in joined)

    def _extractive_answer(self, query: str, evidence: list[dict[str, Any]]) -> str:
        top = evidence[:3]
        lines = [
            "基于当前检索证据，相关内容如下：",
            *[
                f"[{idx + 1}] {item['source_text'][:700]} 来源：{item['citation_text']}"
                for idx, item in enumerate(top)
            ],
            "以上回答仅依据列出的检索片段；如证据不足，请补充文献或调整问题。",
        ]
        return "\n".join(lines)
