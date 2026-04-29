#!/usr/bin/env python
import argparse

from backend.app.db.session import SessionLocal, engine
from backend.app.models.db import Base
from backend.app.services.knowledge_base_service import KnowledgeBaseService


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a medical RAG knowledge base.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        kb = KnowledgeBaseService(db).create(args.name, args.description)
        print(f"Created knowledge base: id={kb.id}, name={kb.name}")


if __name__ == "__main__":
    main()
