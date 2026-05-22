import json
import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.medical_profiles import has_medical_scope_hint
from backend.app.models.db import ChunkRecord, DocumentRecord
from backend.app.rag.llm import OpenAICompatibleLLM

logger = logging.getLogger(__name__)

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]+|[\u4e00-\u9fff]{2,}")
GREETINGS = {
    "hi",
    "hello",
    "hey",
    "你好",
    "您好",
    "在吗",
    "在不在",
    "早上好",
    "下午好",
    "晚上好",
}
DEFINITION_HINTS = (
    "是什么",
    "什么是",
    "什么意思",
    "定义",
    "介绍一下",
    "解释一下",
    "是什么病",
    "what is",
)
STRUCTURED_HINTS = (
    "table",
    "表",
    "figure",
    "fig",
    "图",
    "第",
    "页",
    "results",
    "methods",
    "discussion",
    "conclusion",
    "abstract",
    "摘要",
    "结果",
    "方法",
    "结论",
    "讨论",
    "问题",
    ".pdf",
)


@dataclass(frozen=True)
class QueryGuardDecision:
    action: str
    reason: str
    message: str | None = None


class QueryGuard:
    def __init__(self, db: Session, llm: OpenAICompatibleLLM | None = None) -> None:
        self.db = db
        self.llm = llm
        self.settings = get_settings()

    def evaluate(
        self,
        knowledge_base_id: int,
        query: str,
        inferred_filters: dict[str, str] | None = None,
    ) -> QueryGuardDecision:
        clean_query = query.strip()
        filters = inferred_filters or {}
        if filters.get("document_id"):
            return QueryGuardDecision("retrieve", "document_hint_present")

        rule_decision = self._rule_decision(knowledge_base_id, clean_query)
        if rule_decision.action != "defer":
            return rule_decision

        if self.settings.query_guard_mode.lower() not in {"llm", "hybrid"}:
            return QueryGuardDecision("retrieve", "rule_pass")
        if not self.llm or not self.llm.configured:
            return QueryGuardDecision("retrieve", "llm_unavailable_rule_pass")

        llm_decision = self._llm_decision(knowledge_base_id, clean_query)
        if llm_decision:
            return llm_decision
        return QueryGuardDecision("retrieve", "llm_guard_fallback")

    def _rule_decision(self, knowledge_base_id: int, query: str) -> QueryGuardDecision:
        lowered = query.lower()
        if lowered in GREETINGS:
            return QueryGuardDecision(
                "reject",
                "greeting",
                "当前问题不属于医疗文献检索问题，无法基于知识库证据回答。",
            )
        if has_medical_scope_hint(query):
            return QueryGuardDecision("defer", "medical_scope_hint_present")
        if any(token in lowered for token in STRUCTURED_HINTS):
            return QueryGuardDecision("defer", "structured_hint_present")

        query_terms = self._tokenize(query)
        corpus_terms = self._knowledge_base_terms(knowledge_base_id)
        overlap = query_terms & corpus_terms

        if not query_terms:
            return QueryGuardDecision(
                "reject",
                "empty_semantic_query",
                "当前问题缺少可检索的医学语义信息，无法基于知识库证据回答。",
            )

        if any(hint in query for hint in DEFINITION_HINTS) and not overlap:
            return QueryGuardDecision(
                "reject",
                "generic_definition_out_of_scope",
                "当前问题超出已入库文献范围，无法基于证据可靠回答。",
            )

        if len(query_terms) <= 2 and not overlap:
            return QueryGuardDecision(
                "needs_hint",
                "query_too_broad",
                "当前问题范围过宽，请指定文献名、章节、表号、图号或页码后再查询。",
            )

        return QueryGuardDecision("defer", "rule_uncertain")

    def _llm_decision(
        self,
        knowledge_base_id: int,
        query: str,
    ) -> QueryGuardDecision | None:
        document_titles = [
            row[0]
            for row in self.db.execute(
                select(DocumentRecord.title).where(
                    DocumentRecord.knowledge_base_id == knowledge_base_id
                )
            ).all()
        ]
        section_paths = [
            row[0]
            for row in self.db.execute(
                select(ChunkRecord.section_path)
                .where(ChunkRecord.knowledge_base_id == knowledge_base_id)
                .distinct()
                .limit(30)
            ).all()
        ]
        prompt = {
            "task": "classify_query_scope",
            "allowed_labels": ["IN_SCOPE", "OUT_OF_SCOPE", "NEEDS_DOCUMENT_HINT"],
            "knowledge_base_documents": document_titles[:10],
            "knowledge_base_sections": section_paths[:20],
            "instructions": [
                "Return JSON only.",
                (
                    "Use OUT_OF_SCOPE for greetings, casual chat, or broad "
                    "encyclopedia questions unrelated to the indexed literature."
                ),
                (
                    "Use NEEDS_DOCUMENT_HINT when the question could be "
                    "answerable from the literature but is too broad without "
                    "document or section hints."
                ),
                "Use IN_SCOPE when the query clearly targets indexed literature evidence.",
            ],
            "query": query,
        }
        try:
            raw = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict classifier for a medical literature RAG system. "
                            "Return JSON only with keys label and reason."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                max_tokens=120,
            )
            parsed = json.loads(self._extract_json_object(raw))
        except Exception as exc:
            logger.warning("LLM query guard failed, falling back to retrieval: %s", exc)
            return None

        label = str(parsed.get("label", "")).upper()
        reason = str(parsed.get("reason", "llm_scope_decision"))
        if label == "OUT_OF_SCOPE":
            return QueryGuardDecision(
                "reject",
                reason,
                "当前问题超出已入库文献范围，无法基于证据可靠回答。",
            )
        if label == "NEEDS_DOCUMENT_HINT":
            return QueryGuardDecision(
                "needs_hint",
                reason,
                "当前问题范围过宽，请指定文献名、章节、表号、图号或页码后再查询。",
            )
        if label == "IN_SCOPE":
            return QueryGuardDecision("retrieve", reason)
        return None

    def _knowledge_base_terms(self, knowledge_base_id: int) -> set[str]:
        rows = self.db.execute(
            select(DocumentRecord.title, ChunkRecord.section_path)
            .join(ChunkRecord, ChunkRecord.document_id == DocumentRecord.id)
            .where(DocumentRecord.knowledge_base_id == knowledge_base_id)
        ).all()
        terms: set[str] = set()
        for title, section_path in rows:
            terms.update(self._tokenize(title or ""))
            terms.update(self._tokenize(section_path or ""))
        return terms

    def _tokenize(self, text: str) -> set[str]:
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
            "一下子",
            "这个",
            "那个",
        }
        return {token for token in TOKEN_PATTERN.findall(text.lower()) if token not in stopwords}

    def _extract_json_object(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in LLM response")
        return text[start : end + 1]
