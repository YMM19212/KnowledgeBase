#!/usr/bin/env python
import argparse
import json

from backend.app.db.session import SessionLocal, engine
from backend.app.models.db import Base
from backend.app.rag.service import RAGService


def main() -> None:
    parser = argparse.ArgumentParser(description="Query a medical RAG knowledge base.")
    parser.add_argument("--kb-id", type=int, required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = RAGService(db).query(args.kb_id, args.query, args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
