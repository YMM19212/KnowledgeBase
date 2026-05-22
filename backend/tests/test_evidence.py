import json

from backend.app.rag.embeddings import HashEmbeddingService
from backend.app.schemas.parsed import Paragraph, ParsedDocument, Section
from backend.app.services.evidence_service import EvidenceService
from backend.app.services.indexing_service import IndexingService
from backend.app.services.knowledge_base_service import KnowledgeBaseService


def test_ingest_creates_evidence_units_and_chunk_metadata(db_session):
    kb = KnowledgeBaseService(db_session).create("Evidence Test KB")
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_pdf(kb.id)

    units = EvidenceService(db_session).list_by_knowledge_base(kb.id)

    assert units
    assert any(unit.evidence_type == "primary_outcome" for unit in units)
    assert any(unit.evidence_type == "table_evidence" for unit in units)
    assert all(unit.claim_text for unit in units)


def test_evidence_rebuild_is_idempotent(db_session):
    kb = KnowledgeBaseService(db_session).create("Evidence Rebuild KB")
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_pdf(kb.id)
    first_count = len(EvidenceService(db_session).list_by_knowledge_base(kb.id))

    rebuilt = EvidenceService(db_session).rebuild_knowledge_base(kb.id)
    second_count = len(EvidenceService(db_session).list_by_knowledge_base(kb.id))

    assert rebuilt == first_count
    assert second_count == first_count


def test_rule_extraction_preserves_spaced_medical_values(db_session):
    service = EvidenceService(db_session)
    text = (
        r"IABP: $\Delta { \sf c } { \sf I } =$ "
        r"$0 . 1 1 \pm 0 . 3 1 | / \mathrm { m i n } / \mathrm { m } ^ { 2 }$"
    )
    values = service._extract_values(text)  # noqa: SLF001
    units = service._extract_units(text)  # noqa: SLF001

    assert "0.11 ± 0.31" in values
    assert "l/min/m2" in units


def test_evidence_contains_structured_trial_and_table_fields(db_session):
    kb = KnowledgeBaseService(db_session).create("Structured Trial KB")
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_pdf(kb.id)

    units = EvidenceService(db_session).list_by_knowledge_base(kb.id)
    baseline_table = next(
        unit
        for unit in units
        if json.loads(unit.normalized_facts_json or "{}").get("table", {}).get("role")
        == "baseline_table"
    )
    primary_unit = next(
        unit
        for unit in units
        if unit.evidence_type == "primary_outcome"
        and json.loads(unit.normalized_facts_json or "{}")
        .get("trial", {})
        .get("effect_value")
    )

    baseline_facts = json.loads(baseline_table.normalized_facts_json or "{}")
    primary_facts = json.loads(primary_unit.normalized_facts_json or "{}")

    assert baseline_facts["table"]["role"] == "baseline_table"
    assert baseline_facts["table"]["headers"]
    assert primary_facts["trial"]["effect_value"]
    assert primary_facts["document_type"] == "trial"


def test_guideline_evidence_extracts_recommendation_and_question_id(db_session):
    kb = KnowledgeBaseService(db_session).create("Guideline Evidence KB")
    document = ParsedDocument(
        document_id="guideline-evidence",
        title="中国专家共识",
        sections=[
            Section(
                title="问题四",
                level=1,
                page_start=2,
                page_end=2,
                paragraphs=[
                    Paragraph(
                        text="推荐意见：建议首选经阴道超声检查。推荐级别 1 类。",
                        page_number=2,
                    )
                ],
            )
        ],
    )
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_parsed_document(
        kb.id, document
    )

    units = EvidenceService(db_session).list_by_knowledge_base(kb.id)
    facts = json.loads(units[0].normalized_facts_json or "{}")

    assert facts["guideline"]["recommendation_statement"]
    assert facts["guideline"]["clinical_question_id"] == "问题四"
