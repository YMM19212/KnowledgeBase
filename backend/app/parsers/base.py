from abc import ABC, abstractmethod
from pathlib import Path

from backend.app.schemas.parsed import ParsedDocument


class BaseParser(ABC):
    """Common parser interface for MinerU, mock data, and future OCR/PDF parsers."""

    @abstractmethod
    def parse_pdf(self, pdf_path: Path | str | None = None) -> ParsedDocument:
        """Parse a PDF-like input into the normalized internal document schema."""
