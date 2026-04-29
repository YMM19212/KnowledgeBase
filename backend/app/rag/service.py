import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.db import ChunkRecord, DocumentRecord
from backend.app.rag.embeddings import EmbeddingService, get_embedding_service
from backend.app.rag.llm import OpenAICompatibleLLM
from backend.app.services.settings_service import AppSettingsService
from backend.app.vectorstores.factory import get_vector_store


class RAGService:
    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingService | None = None,
        llm: OpenAICompatibleLLM | None = None,
    ) -> None:
        self.db = db
        runtime_embedding = AppSettingsService(db).effective_embedding_settings()
        self.embeddings = embeddings or get_embedding_service(runtime_embedding)
        self.vector_store = get_vector_store(db)
        self.llm = llm or OpenAICompatibleLLM()
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
        query_vector = self.embeddings.embed_query(query)
        search_k = max(top_k * 5, top_k)
        results = self.vector_store.similarity_search(
            knowledge_base_id, query_vector, search_k, effective_filters
        )
        enriched = self._rerank(query, [self._enrich_result(result) for result in results])[:top_k]
        usable = [item for item in enriched if item["score"] >= self.settings.rag_min_score]
        if not usable:
            return {
                "answer": "证据不足，无法可靠回答。",
                "citations": [],
                "retrieved_chunks": enriched,
            }
        try:
            answer = (
                self.llm.answer(query, usable)
                if self.llm.configured
                else self._extractive_answer(query, usable)
            )
        except Exception:
            answer = self._extractive_answer(query, usable)
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
        }

    def _rerank(self, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        query_lower = query.lower()
        section_keywords = {
            "results": ["results", "结果"],
            "methods": ["methods", "方法"],
            "conclusions": ["conclusions", "conclusion", "结论"],
            "discussion": ["discussion", "讨论"],
            "table": ["table", "表格", "表 "],
            "figure": ["figure", "fig.", "图"],
            "abstract": ["abstract", "摘要"],
        }
        requested = {
            section
            for section, terms in section_keywords.items()
            if any(term in query_lower for term in terms)
        }
        reranked: list[dict[str, Any]] = []
        for item in results:
            adjusted = dict(item)
            score = float(adjusted["score"])
            section_path = str(adjusted.get("section_path") or "").lower()
            content_type = str(adjusted.get("content_type") or "").lower()
            if "results" in requested and "result" in section_path:
                score += 0.25
            if "methods" in requested and "method" in section_path:
                score += 0.2
            if "conclusions" in requested and "conclusion" in section_path:
                score += 0.2
            if "discussion" in requested and "discussion" in section_path:
                score += 0.2
            if "table" in requested and content_type == "table":
                score += 0.2
            if "figure" in requested and content_type == "figure_caption":
                score += 0.2
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
            adjusted["score"] = min(score, 1.0)
            reranked.append(adjusted)
        return sorted(reranked, key=lambda item: item["score"], reverse=True)

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
        metadata = dict(result.metadata)
        if chunk:
            metadata = {**json.loads(chunk.metadata_json or "{}"), **metadata}
        return {
            "chunk_id": result.chunk_id,
            "document_id": result.document_id,
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
