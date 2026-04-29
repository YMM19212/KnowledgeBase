from backend.app.parsers.local_mineru import LocalMinerUParserAdapter
from backend.app.parsers.mock import MockParser


def test_mock_parser_normalizes_sample():
    document = MockParser("examples/sample_mineru_output.json").parse_pdf()

    assert document.document_id == "demo-trial-001"
    assert document.title.startswith("A Randomized Trial")
    assert document.sections
    assert document.sections[1].subsections[0].tables[0].table_id == "T1"


def test_local_mineru_parser_uses_text_level_headings(tmp_path):
    output_dir = tmp_path / "article" / "auto"
    output_dir.mkdir(parents=True)
    (output_dir / "article_origin.pdf").write_bytes(b"%PDF")
    (output_dir / "article_content_list.json").write_text(
        """
        [
          {"type": "text", "text_level": 1, "page_idx": 0, "text": "Results"},
          {"type": "text", "page_idx": 0, "text": "Primary endpoint improved."},
          {"type": "table", "page_idx": 0, "table_caption": ["Table 1"], "table_body": "| A | B |"}
        ]
        """,
        encoding="utf-8",
    )

    document = LocalMinerUParserAdapter().parse_output_dir(output_dir)

    assert document.document_id == "article"
    assert document.sections[0].title == "Results"
    assert document.sections[0].paragraphs[0].text == "Primary endpoint improved."
    assert document.sections[0].tables[0].caption == "Table 1"
