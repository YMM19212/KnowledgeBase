#!/usr/bin/env python
import argparse
import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from backend.app.db.session import SessionLocal, engine
from backend.app.models.db import (
    AppSetting,
    Base,
    ChunkRecord,
    DocumentRecord,
    EvidenceUnit,
    KnowledgeBase,
    VectorEntry,
)
from backend.app.parsers.local_mineru import LocalMinerUParserAdapter
from backend.app.rag.service import RAGService
from backend.app.services.indexing_service import IndexingService
from backend.app.services.knowledge_base_service import KnowledgeBaseService

LLM_KEYS = ["llm.provider", "llm.base_url", "llm.model", "llm.api_key"]


def find_mineru_output_dirs(root: Path) -> list[Path]:
    candidates: set[Path] = set()
    for content_list in root.rglob("*_content_list.json"):
        candidates.add(content_list.parent)
    for markdown in root.rglob("*.md"):
        if any(markdown.parent.glob("*_content_list.json")):
            candidates.add(markdown.parent)
    return sorted(candidates)


def normalize_text(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", text).lower()


def expected_aliases(source: str) -> list[str]:
    normalized = normalize_text(source)
    aliases = {normalized}
    aliases.add(normalized.removesuffix("pdf"))
    aliases.add(normalized.removesuffix("版"))
    return sorted(alias for alias in aliases if alias)


@contextmanager
def llm_disabled(db):
    saved = {
        key: (db.get(AppSetting, key).value if db.get(AppSetting, key) else None)
        for key in LLM_KEYS
    }
    for key in LLM_KEYS:
        setting = db.get(AppSetting, key)
        if key == "llm.provider":
            if setting:
                setting.value = "none"
            else:
                db.add(AppSetting(key=key, value="none"))
        elif setting:
            db.delete(setting)
    db.commit()
    try:
        yield
    finally:
        for key in LLM_KEYS:
            setting = db.get(AppSetting, key)
            previous = saved[key]
            if previous is None:
                if setting:
                    db.delete(setting)
            else:
                if setting:
                    setting.value = previous
                else:
                    db.add(AppSetting(key=key, value=previous))
        db.commit()


def rebuild_eval_kb(db, kb_name: str, input_dir: Path) -> int:
    existing = db.scalar(select(KnowledgeBase).where(KnowledgeBase.name == kb_name))
    if existing:
        db.execute(delete(EvidenceUnit).where(EvidenceUnit.knowledge_base_id == existing.id))
        db.execute(delete(VectorEntry).where(VectorEntry.knowledge_base_id == existing.id))
        db.execute(delete(ChunkRecord).where(ChunkRecord.knowledge_base_id == existing.id))
        db.execute(delete(DocumentRecord).where(DocumentRecord.knowledge_base_id == existing.id))
        db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == existing.id))
        db.commit()

    kb = KnowledgeBaseService(db).create(
        kb_name,
        "Retrieval evaluation KB built from pre-cleaned CompetitionMinerU artifacts.",
    )
    parser_adapter = LocalMinerUParserAdapter()
    indexer = IndexingService(db, parser=parser_adapter)
    for output_dir in find_mineru_output_dirs(input_dir):
        parsed = parser_adapter.parse_output_dir(output_dir)
        document = indexer.ingest_parsed_document(kb.id, parsed)
        print(f"Ingested {document.id} from {output_dir}")
    return kb.id


def source_hit(citations: list[dict[str, Any]], source: str, top_n: int) -> bool:
    aliases = expected_aliases(source)
    for citation in citations[:top_n]:
        haystack = " ".join(
            [
                normalize_text(str(citation.get("document_id") or "")),
                normalize_text(str(citation.get("citation_text") or "")),
                normalize_text(str(citation.get("section_path") or "")),
            ]
        )
        if any(alias and alias in haystack for alias in aliases):
            return True
    return False


def query_with_source_hint(query: str, source: str) -> str:
    return f"请根据 {source}，{query.removeprefix('请根据输入的文献内容，')}"


def evaluate_queries(
    db,
    kb_id: int,
    queries: list[dict[str, Any]],
    mode: str,
) -> dict[str, Any]:
    rag = RAGService(db)
    top1_hits = 0
    top3_hits = 0
    results: list[dict[str, Any]] = []

    for item in queries:
        query = item["query"]
        if mode == "source-hint":
            query = query_with_source_hint(query, item["source"])
        result = rag.query(kb_id, query, top_k=5)
        citations = result.get("citations", [])
        top1 = source_hit(citations, item["source"], 1)
        top3 = source_hit(citations, item["source"], 3)
        top1_hits += int(top1)
        top3_hits += int(top3)
        results.append(
            {
                "id": item["id"],
                "query": query,
                "expected_source": item["source"],
                "answer_mode": result.get("answer_mode"),
                "top1_source_hit": top1,
                "top3_source_hit": top3,
                "top_citations": [
                    {
                        "document_id": citation.get("document_id"),
                        "section_path": citation.get("section_path"),
                        "page_start": citation.get("page_start"),
                        "page_end": citation.get("page_end"),
                        "score": round(float(citation.get("score", 0.0)), 4),
                        "evidence_role": citation.get("evidence_role"),
                        "citation_text": citation.get("citation_text"),
                    }
                    for citation in citations[:3]
                ],
            }
        )

    total = len(queries) or 1
    return {
        "mode": mode,
        "query_count": len(queries),
        "top1_source_recall": round(top1_hits / total, 4),
        "top3_source_recall": round(top3_hits / total, 4),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run retrieval-only evaluation on pre-cleaned competition MinerU outputs."
    )
    parser.add_argument("--input-dir", default="CompetitionMinerU")
    parser.add_argument("--queries", default="examples/competition_queries.json")
    parser.add_argument("--kb-name", default="Competition Retrieval Eval KB")
    parser.add_argument("--reuse-kb", action="store_true")
    parser.add_argument("--mode", choices=["mixed", "source-hint", "both"], default="both")
    parser.add_argument("--output", default="data/eval/competition_retrieval_report.json")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    input_dir = Path(args.input_dir)
    query_file = Path(args.queries)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    queries = json.loads(query_file.read_text())

    with SessionLocal() as db, llm_disabled(db):
        kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.name == args.kb_name))
        if args.reuse_kb and kb:
            kb_id = kb.id
        else:
            kb_id = rebuild_eval_kb(db, args.kb_name, input_dir)

        modes = ["mixed", "source-hint"] if args.mode == "both" else [args.mode]
        report = {
            "kb_id": kb_id,
            "kb_name": args.kb_name,
            "input_dir": str(input_dir),
            "query_file": str(query_file),
            "reports": [evaluate_queries(db, kb_id, queries, mode) for mode in modes],
        }
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\nSaved report to {output_file}")


if __name__ == "__main__":
    main()
