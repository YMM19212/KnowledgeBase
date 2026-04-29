import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.db import ChunkRecord
from backend.app.rag.embeddings import EmbeddingService, get_embedding_service
from backend.app.rag.llm import OpenAICompatibleLLM
from backend.app.vectorstores.factory import get_vector_store


class RAGService:
    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingService | None = None,
        llm: OpenAICompatibleLLM | None = None,
    ) -> None:
        self.db = db
        self.embeddings = embeddings or get_embedding_service()
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
        query_vector = self.embeddings.embed_query(query)
        results = self.vector_store.similarity_search(
            knowledge_base_id, query_vector, top_k, filters
        )
        enriched = [self._enrich_result(result) for result in results]
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
