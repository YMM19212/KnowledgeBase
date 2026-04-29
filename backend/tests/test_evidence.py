from backend.app.rag.embeddings import HashEmbeddingService
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
