from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from backend.app.core.config import get_settings
from backend.app.parsers.base import BaseParser
from backend.app.parsers.mock import MockParser
from backend.app.schemas.parsed import ParsedDocument


class MinerUParserAdapter(BaseParser):
    """Future adapter boundary for a remote MinerU parsing service.

    The current implementation keeps method contracts stable and returns mock
    data when no MinerU API URL is configured. Wiring the real service should
    only require changing submit_parse_task/get_parse_result/normalize_mineru_json.
    """

    def __init__(self, mineru_api_url: str | None = None) -> None:
        settings = get_settings()
        self.mineru_api_url = mineru_api_url or settings.mineru_api_url

    def submit_parse_task(self, pdf_path: Path | str) -> str:
        if not self.mineru_api_url:
            return f"mock-task-{uuid4().hex}"
        with Path(pdf_path).open("rb") as f:
            response = httpx.post(
                f"{self.mineru_api_url.rstrip('/')}/parse",
                files={"file": (Path(pdf_path).name, f, "application/pdf")},
                timeout=120,
            )
        response.raise_for_status()
        return response.json()["task_id"]

    def get_parse_result(self, task_id: str) -> dict[str, Any]:
        if not self.mineru_api_url:
            return MockParser().parse_pdf().raw_mineru_json or {}
        response = httpx.get(
            f"{self.mineru_api_url.rstrip('/')}/parse/{task_id}",
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def parse_pdf(self, pdf_path: Path | str | None = None) -> ParsedDocument:
        if not pdf_path or not self.mineru_api_url:
            return MockParser().parse_pdf(pdf_path)
        task_id = self.submit_parse_task(pdf_path)
        result = self.get_parse_result(task_id)
        return self.normalize_mineru_json(result, source_file=str(pdf_path))

    def normalize_mineru_json(
        self, raw_mineru_json: dict[str, Any], source_file: str | None = None
    ) -> ParsedDocument:
        doc = MockParser().normalize(raw_mineru_json)
        if source_file:
            doc.source_file = source_file
        return doc
