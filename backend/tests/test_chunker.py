from backend.app.chunking.medical_semantic import MedicalSemanticChunker
from backend.app.parsers.mock import MockParser
from backend.app.schemas.parsed import Paragraph, ParsedDocument, Section


def test_medical_chunker_preserves_outcome_and_table_metadata():
    document = MockParser("examples/sample_mineru_output.json").parse_pdf()
    chunks = MedicalSemanticChunker(max_tokens=120).chunk(document)

    section_paths = {chunk.section_path for chunk in chunks}
    table_chunks = [chunk for chunk in chunks if chunk.content_type == "table"]

    assert "Results > Primary outcome" in section_paths
    assert table_chunks
    assert table_chunks[0].metadata["table_id"] == "T1"
    assert all(chunk.citation_text for chunk in chunks)
    assert any(chunk.section_path == "Abstract > Results" for chunk in chunks)
    assert any(chunk.metadata.get("table_role") == "baseline_table" for chunk in table_chunks)


def test_chunker_creates_guideline_question_and_recommendation_roles():
    document = ParsedDocument(
        document_id="guideline-doc",
        title="中国专家共识",
        sections=[
            Section(
                title="问题四",
                level=1,
                page_start=2,
                page_end=2,
                paragraphs=[
                    Paragraph(text="问题四：推荐采用经阴道超声作为首选检查方式。", page_number=2),
                    Paragraph(text="推荐意见：对疑似患者应优先进行规范化超声评估。", page_number=2),
                ],
            )
        ],
    )
    chunks = MedicalSemanticChunker(max_tokens=80).chunk(document)

    assert any(chunk.metadata.get("evidence_role") == "question_answer_block" for chunk in chunks)
    assert any(chunk.metadata.get("evidence_role") == "recommendation_block" for chunk in chunks)
    assert any(chunk.metadata.get("clinical_question_id") == "问题四" for chunk in chunks)
