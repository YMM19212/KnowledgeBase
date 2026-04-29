import json
import math
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.models.db import VectorEntry
from backend.app.vectorstores.base import SearchResult, VectorDocument, VectorStore


class SQLiteVectorStore(VectorStore):
    """Small local vector store for tests and fallback deployments."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, items: list[VectorDocument]) -> None:
        for item in items:
            existing = self.db.scalar(
                select(VectorEntry).where(
                    VectorEntry.knowledge_base_id == item.knowledge_base_id,
                    VectorEntry.chunk_id == item.chunk_id,
                )
            )
            payload = {
                "knowledge_base_id": item.knowledge_base_id,
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "content": item.content,
                "metadata_json": json.dumps(item.metadata, ensure_ascii=False),
                "embedding_json": json.dumps(item.embedding),
            }
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
            else:
                self.db.add(VectorEntry(**payload))
        self.db.commit()

    def delete_document(self, knowledge_base_id: int, document_id: str) -> None:
        self.db.execute(
            delete(VectorEntry).where(
                VectorEntry.knowledge_base_id == knowledge_base_id,
                VectorEntry.document_id == document_id,
            )
        )
        self.db.commit()

    def delete_knowledge_base(self, knowledge_base_id: int) -> None:
        self.db.execute(
            delete(VectorEntry).where(VectorEntry.knowledge_base_id == knowledge_base_id)
        )
        self.db.commit()

    def similarity_search(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        entries = self.db.scalars(
            select(VectorEntry).where(VectorEntry.knowledge_base_id == knowledge_base_id)
        ).all()
        results: list[SearchResult] = []
        for entry in entries:
            metadata = json.loads(entry.metadata_json or "{}")
            if not self._matches(metadata, filters or {}):
                continue
            score = self._cosine(query_embedding, json.loads(entry.embedding_json))
            results.append(
                SearchResult(
                    chunk_id=entry.chunk_id,
                    document_id=entry.document_id,
                    content=entry.content,
                    score=score,
                    metadata=metadata,
                )
            )
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    def _matches(self, metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        return all(metadata.get(key) == value for key, value in filters.items())

    def _cosine(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return float(numerator / (left_norm * right_norm))
