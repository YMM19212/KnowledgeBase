#!/usr/bin/env python
import argparse

from backend.app.db.session import SessionLocal, engine
from backend.app.models.db import Base
from backend.app.parsers.mock import MockParser
from backend.app.services.indexing_service import IndexingService
from backend.app.services.knowledge_base_service import KnowledgeBaseService


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the sample MinerU output into a KB.")
    parser.add_argument("--kb-id", type=int)
    parser.add_argument("--kb-name", default="Demo Medical KB")
    parser.add_argument("--json-path", default=None)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        kb_service = KnowledgeBaseService(db)
        kb_id = args.kb_id
        if kb_id is None:
            kb = kb_service.create(args.kb_name, "Sample clinical trial knowledge base")
            kb_id = kb.id
        parser_adapter = MockParser(args.json_path)
        document = IndexingService(db, parser=parser_adapter).ingest_pdf(kb_id)
        chunk_count = len(IndexingService(db).chunker.chunk(parser_adapter.parse_pdf()))
        print(f"Ingested document {document.id} into KB {kb_id}; chunks={chunk_count}")


if __name__ == "__main__":
    main()
