from backend.app.chunking.medical_semantic import MedicalSemanticChunker
from backend.app.parsers.mock import MockParser


def test_chunk_metadata_contains_traceable_fields():
    document = MockParser("examples/sample_mineru_output.json").parse_pdf()
    chunk = MedicalSemanticChunker().chunk(document)[0]

    assert chunk.document_id
    assert chunk.chunk_id
    assert chunk.section_path
    assert "canonical_section" in chunk.metadata
    assert chunk.source_span["type"] == "section"
