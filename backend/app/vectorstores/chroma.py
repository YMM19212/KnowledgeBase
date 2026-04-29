from pathlib import Path
from typing import Any

from backend.app.vectorstores.base import SearchResult, VectorDocument, VectorStore


class ChromaVectorStore(VectorStore):
    """Chroma implementation using persistent local collections."""

    def __init__(self, persist_dir: Path | str) -> None:
        import chromadb

        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection("medical_rag_chunks")

    def upsert(self, items: list[VectorDocument]) -> None:
        if not items:
            return
        self.collection.upsert(
            ids=[item.chunk_id for item in items],
            embeddings=[item.embedding for item in items],
            documents=[item.content for item in items],
            metadatas=[
                {
                    **item.metadata,
                    "knowledge_base_id": item.knowledge_base_id,
                    "document_id": item.document_id,
                }
                for item in items
            ],
        )

    def delete_document(self, knowledge_base_id: int, document_id: str) -> None:
        self.collection.delete(
            where={"$and": [{"knowledge_base_id": knowledge_base_id}, {"document_id": document_id}]}
        )

    def delete_knowledge_base(self, knowledge_base_id: int) -> None:
        self.collection.delete(where={"knowledge_base_id": knowledge_base_id})

    def similarity_search(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        where = {"knowledge_base_id": knowledge_base_id}
        for key, value in (filters or {}).items():
            where = {"$and": [where, {key: value}]}
        response = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        results: list[SearchResult] = []
        for idx, chunk_id in enumerate(response.get("ids", [[]])[0]):
            metadata = response["metadatas"][0][idx] or {}
            distance = response["distances"][0][idx]
            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=metadata.get("document_id", ""),
                    content=response["documents"][0][idx],
                    score=max(0.0, 1.0 - float(distance)),
                    metadata=metadata,
                )
            )
        return results
