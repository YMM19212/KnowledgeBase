from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    chunk_id: str
    document_id: str
    knowledge_base_id: int
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, items: list[VectorDocument]) -> None:
        """Insert or replace vector documents."""

    @abstractmethod
    def delete_document(self, knowledge_base_id: int, document_id: str) -> None:
        """Delete vectors for one document."""

    @abstractmethod
    def delete_knowledge_base(self, knowledge_base_id: int) -> None:
        """Delete vectors for one knowledge base."""

    @abstractmethod
    def similarity_search(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Return nearest chunks scoped to a knowledge base."""
