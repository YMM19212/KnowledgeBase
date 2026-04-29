import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.chunking.medical_semantic import MedicalSemanticChunker
from backend.app.models.db import ChunkRecord, DocumentRecord
from backend.app.parsers.base import BaseParser
from backend.app.parsers.mock import MockParser
from backend.app.rag.embeddings import EmbeddingService, get_embedding_service
from backend.app.schemas.parsed import Chunk, ParsedDocument
from backend.app.services.settings_service import AppSettingsService
from backend.app.vectorstores.base import VectorDocument
from backend.app.vectorstores.factory import get_vector_store


class IndexingService:
    """Coordinates parsed documents, semantic chunks, metadata DB records, and vectors."""

    def __init__(
        self,
        db: Session,
        parser: BaseParser | None = None,
        chunker: MedicalSemanticChunker | None = None,
        embeddings: EmbeddingService | None = None,
    ) -> None:
        self.db = db
        self.parser = parser or MockParser()
        self.chunker = chunker or MedicalSemanticChunker()
        runtime_embedding = AppSettingsService(db).effective_embedding_settings()
        self.embeddings = embeddings or get_embedding_service(runtime_embedding)
        self.vector_store = get_vector_store(db)

    def ingest_pdf(
        self, knowledge_base_id: int, pdf_path: Path | str | None = None
    ) -> DocumentRecord:
        parsed = self.parser.parse_pdf(pdf_path)
        return self.ingest_parsed_document(knowledge_base_id, parsed)

    def ingest_parsed_document(
        self, knowledge_base_id: int, parsed: ParsedDocument
    ) -> DocumentRecord:
        chunks = self.chunker.chunk(parsed)
        record = self._upsert_document(knowledge_base_id, parsed)
        self._replace_chunks(knowledge_base_id, parsed.document_id, chunks)
        self._index_chunks(knowledge_base_id, chunks)
        return record

    def rebuild_index(self, knowledge_base_id: int) -> int:
        chunks = list(
            self.db.scalars(
                select(ChunkRecord)
                .where(ChunkRecord.knowledge_base_id == knowledge_base_id)
                .order_by(ChunkRecord.id)
            )
        )
        vectors = self.embeddings.embed_texts([chunk.content for chunk in chunks])
        self.vector_store.delete_knowledge_base(knowledge_base_id)
        self.vector_store.upsert(
            [
                VectorDocument(
                    knowledge_base_id=knowledge_base_id,
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    embedding=embedding,
                    metadata=json.loads(chunk.metadata_json or "{}"),
                )
                for chunk, embedding in zip(chunks, vectors, strict=True)
            ]
        )
        return len(chunks)

    def _upsert_document(self, knowledge_base_id: int, parsed: ParsedDocument) -> DocumentRecord:
        record = self.db.get(DocumentRecord, parsed.document_id)
        payload = {
            "knowledge_base_id": knowledge_base_id,
            "title": parsed.title,
            "authors_json": json.dumps(parsed.authors, ensure_ascii=False),
            "abstract": parsed.abstract,
            "source_file": parsed.source_file,
            "parse_status": "parsed",
            "raw_json": parsed.model_dump_json(),
        }
        if record:
            for key, value in payload.items():
                setattr(record, key, value)
        else:
            record = DocumentRecord(id=parsed.document_id, **payload)
            self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def _replace_chunks(
        self, knowledge_base_id: int, document_id: str, chunks: list[Chunk]
    ) -> None:
        self.vector_store.delete_document(knowledge_base_id, document_id)
        for existing in list(
            self.db.scalars(select(ChunkRecord).where(ChunkRecord.document_id == document_id))
        ):
            self.db.delete(existing)
        for chunk in chunks:
            metadata = {**chunk.metadata, **chunk.source_span, "citation_text": chunk.citation_text}
            self.db.add(
                ChunkRecord(
                    document_id=document_id,
                    knowledge_base_id=knowledge_base_id,
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    content_type=chunk.content_type,
                    section_path=chunk.section_path,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                )
            )
        self.db.commit()

    def _index_chunks(self, knowledge_base_id: int, chunks: list[Chunk]) -> None:
        embeddings = self.embeddings.embed_texts([chunk.content for chunk in chunks])
        items = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            metadata = {
                **chunk.metadata,
                **chunk.source_span,
                "citation_text": chunk.citation_text,
                "section_path": chunk.section_path,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "content_type": chunk.content_type,
            }
            items.append(
                VectorDocument(
                    knowledge_base_id=knowledge_base_id,
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    embedding=embedding,
                    metadata=metadata,
                )
            )
        self.vector_store.upsert(items)
