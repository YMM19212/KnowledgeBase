from backend.app.chunking.medical_semantic import MedicalSemanticChunker
from backend.app.parsers.mock import MockParser


def test_medical_chunker_preserves_outcome_and_table_metadata():
    document = MockParser("examples/sample_mineru_output.json").parse_pdf()
    chunks = MedicalSemanticChunker(max_tokens=120).chunk(document)

    section_paths = {chunk.section_path for chunk in chunks}
    table_chunks = [chunk for chunk in chunks if chunk.content_type == "table"]

    assert "Results > Primary outcome" in section_paths
    assert table_chunks
    assert table_chunks[0].metadata["table_id"] == "T1"
    assert all(chunk.citation_text for chunk in chunks)
