import json

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.models.db import ChunkRecord, DocumentRecord, KnowledgeBase
from backend.app.vectorstores.factory import get_vector_store


class KnowledgeBaseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, name: str, description: str | None = None) -> KnowledgeBase:
        kb = KnowledgeBase(name=name, description=description)
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def list(self) -> list[tuple[KnowledgeBase, int, int]]:
        knowledge_bases = self.db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.id)).all()
        rows: list[tuple[KnowledgeBase, int, int]] = []
        for kb in knowledge_bases:
            doc_count = self.db.scalar(
                select(func.count(DocumentRecord.id)).where(
                    DocumentRecord.knowledge_base_id == kb.id
                )
            )
            chunk_count = self.db.scalar(
                select(func.count(ChunkRecord.id)).where(ChunkRecord.knowledge_base_id == kb.id)
            )
            rows.append((kb, doc_count or 0, chunk_count or 0))
        return rows

    def get(self, kb_id: int) -> KnowledgeBase | None:
        return self.db.get(KnowledgeBase, kb_id)

    def delete(self, kb_id: int) -> bool:
        kb = self.db.get(KnowledgeBase, kb_id)
        if not kb:
            return False
        get_vector_store(self.db).delete_knowledge_base(kb_id)
        self.db.delete(kb)
        self.db.commit()
        return True


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, document_id: str) -> DocumentRecord | None:
        return self.db.get(DocumentRecord, document_id)

    def list_by_kb(self, kb_id: int) -> list[DocumentRecord]:
        return list(
            self.db.scalars(
                select(DocumentRecord)
                .where(DocumentRecord.knowledge_base_id == kb_id)
                .order_by(DocumentRecord.created_at)
            )
        )

    def list_chunks(self, document_id: str) -> list[ChunkRecord]:
        return list(
            self.db.scalars(
                select(ChunkRecord)
                .where(ChunkRecord.document_id == document_id)
                .order_by(ChunkRecord.id)
            )
        )

    def delete(self, document_id: str) -> bool:
        document = self.db.get(DocumentRecord, document_id)
        if not document:
            return False
        get_vector_store(self.db).delete_document(document.knowledge_base_id, document_id)
        self.db.delete(document)
        self.db.commit()
        return True

    def delete_chunks(self, document_id: str) -> None:
        self.db.execute(delete(ChunkRecord).where(ChunkRecord.document_id == document_id))
        self.db.commit()


def document_to_dict(record: DocumentRecord) -> dict:
    chunk_count = len(record.chunks) if record.chunks is not None else 0
    return {
        "id": record.id,
        "knowledge_base_id": record.knowledge_base_id,
        "title": record.title,
        "authors": json.loads(record.authors_json or "[]"),
        "abstract": record.abstract,
        "source_file": record.source_file,
        "parse_status": record.parse_status,
        "chunk_count": chunk_count,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
