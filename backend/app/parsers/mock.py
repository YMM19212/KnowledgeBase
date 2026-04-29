import json
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.parsers.base import BaseParser
from backend.app.schemas.parsed import Figure, Paragraph, ParsedDocument, Section, Table


class MockParser(BaseParser):
    """Load a sample MinerU-like JSON file and normalize it as if MinerU parsed a PDF."""

    def __init__(self, json_path: Path | str | None = None) -> None:
        self.json_path = Path(json_path or get_settings().mock_mineru_json)

    def parse_pdf(self, pdf_path: Path | str | None = None) -> ParsedDocument:
        with self.json_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        doc = self.normalize(raw)
        if pdf_path:
            doc.source_file = str(pdf_path)
        return doc

    def normalize(self, raw: dict) -> ParsedDocument:
        sections = [self._section(item) for item in raw.get("sections", [])]
        return ParsedDocument(
            document_id=raw["document_id"],
            title=raw.get("title", "Untitled Medical Document"),
            authors=raw.get("authors", []),
            abstract=raw.get("abstract"),
            sections=sections,
            paragraphs=[self._paragraph(p) for p in raw.get("paragraphs", [])],
            tables=[self._table(t) for t in raw.get("tables", [])],
            figures=[self._figure(f) for f in raw.get("figures", [])],
            references=raw.get("references", []),
            page_number=raw.get("page_number"),
            source_file=raw.get("source_file"),
            raw_mineru_json=raw,
        )

    def _paragraph(self, item: dict) -> Paragraph:
        return Paragraph(text=item["text"], page_number=item.get("page_number"))

    def _table(self, item: dict) -> Table:
        return Table(
            table_id=item["table_id"],
            title=item.get("title"),
            caption=item.get("caption"),
            markdown=item.get("markdown", ""),
            page_number=item.get("page_number"),
        )

    def _figure(self, item: dict) -> Figure:
        return Figure(
            figure_id=item["figure_id"],
            caption=item.get("caption", ""),
            page_number=item.get("page_number"),
        )

    def _section(self, item: dict) -> Section:
        return Section(
            title=item["title"],
            level=item.get("level", 1),
            page_start=item.get("page_start"),
            page_end=item.get("page_end"),
            paragraphs=[self._paragraph(p) for p in item.get("paragraphs", [])],
            tables=[self._table(t) for t in item.get("tables", [])],
            figures=[self._figure(f) for f in item.get("figures", [])],
            subsections=[self._section(s) for s in item.get("subsections", [])],
        )
