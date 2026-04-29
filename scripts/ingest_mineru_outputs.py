#!/usr/bin/env python
import argparse
from pathlib import Path

from backend.app.db.session import SessionLocal, engine
from backend.app.models.db import Base
from backend.app.parsers.local_mineru import LocalMinerUParserAdapter
from backend.app.services.indexing_service import IndexingService
from backend.app.services.knowledge_base_service import KnowledgeBaseService


def find_mineru_output_dirs(root: Path) -> list[Path]:
    candidates: set[Path] = set()
    for content_list in root.rglob("*_content_list.json"):
        candidates.add(content_list.parent)
    for markdown in root.rglob("*.md"):
        if any(markdown.parent.glob("*_content_list.json")):
            candidates.add(markdown.parent)
    return sorted(candidates)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest already-cleaned MinerU output directories into a knowledge base."
    )
    parser.add_argument("--input-dir", default="CompetitionMinerU")
    parser.add_argument("--kb-id", type=int)
    parser.add_argument("--kb-name", default="Competition Medical Literature KB")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise SystemExit(f"Input directory not found: {input_dir}")

    output_dirs = find_mineru_output_dirs(input_dir)
    if not output_dirs:
        raise SystemExit(f"No MinerU output directories found under: {input_dir}")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        kb_id = args.kb_id
        if kb_id is None:
            kb = KnowledgeBaseService(db).create(
                args.kb_name,
                "Knowledge base initialized from pre-cleaned MinerU competition artifacts.",
            )
            kb_id = kb.id

        parser_adapter = LocalMinerUParserAdapter()
        indexer = IndexingService(db, parser=parser_adapter)
        for output_dir in output_dirs:
            parsed = parser_adapter.parse_output_dir(output_dir)
            document = indexer.ingest_parsed_document(kb_id, parsed)
            print(f"Ingested {document.id} from {output_dir}")

        print(f"Done. kb_id={kb_id}, documents={len(output_dirs)}")


if __name__ == "__main__":
    main()

