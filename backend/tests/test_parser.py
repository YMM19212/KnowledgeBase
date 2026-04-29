from backend.app.parsers.mock import MockParser


def test_mock_parser_normalizes_sample():
    document = MockParser("examples/sample_mineru_output.json").parse_pdf()

    assert document.document_id == "demo-trial-001"
    assert document.title.startswith("A Randomized Trial")
    assert document.sections
    assert document.sections[1].subsections[0].tables[0].table_id == "T1"
