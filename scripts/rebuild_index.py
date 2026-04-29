#!/usr/bin/env python
import argparse

from backend.app.db.session import SessionLocal, engine
from backend.app.models.db import Base
from backend.app.services.indexing_service import IndexingService


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild vector index for a KB.")
    parser.add_argument("--kb-id", type=int, required=True)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        count = IndexingService(db).rebuild_index(args.kb_id)
        print(f"Rebuilt index for KB {args.kb_id}; indexed_chunks={count}")


if __name__ == "__main__":
    main()
