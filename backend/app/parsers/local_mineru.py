import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.parsers.base import BaseParser
from backend.app.schemas.parsed import Figure, Paragraph, ParsedDocument, Section, Table


@dataclass
class LocalMinerURun:
    command: list[str]
    output_dir: str
    artifacts: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0


class LocalMinerUParserAdapter(BaseParser):
    """Run local MinerU CLI in pipeline mode and normalize its artifacts."""

    def __init__(
        self,
        output_dir: Path | str | None = None,
        method: str = "auto",
        lang: str = "ch",
        formula: bool = True,
        table: bool = True,
    ) -> None:
        settings = get_settings()
        self.command = settings.mineru_cli_command
        self.output_dir = Path(output_dir or settings.mineru_local_output_dir)
        self.timeout = settings.mineru_cli_timeout_seconds
        self.method = method
        self.lang = lang
        self.formula = formula
        self.table = table
        self.last_run: LocalMinerURun | None = None

    def parse_pdf(self, pdf_path: Path | str | None = None) -> ParsedDocument:
        if not pdf_path:
            raise ValueError("Local MinerU parser requires a PDF path.")
        run = self.run_pipeline(Path(pdf_path))
        raw = self.load_best_artifact(Path(run.output_dir))
        return self.normalize_mineru_output(
            raw, source_file=str(pdf_path), output_dir=Path(run.output_dir)
        )

    def run_pipeline(self, input_path: Path) -> LocalMinerURun:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        command = [
            self.command,
            "-p",
            str(input_path),
            "-o",
            str(self.output_dir),
            "-b",
            "pipeline",
            "-m",
            self.method,
            "-l",
            self.lang,
            "-f",
            str(self.formula),
            "-t",
            str(self.table),
        ]
        start = time.monotonic()
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        duration = time.monotonic() - start
        artifacts = [str(path) for path in self._artifact_files(self.output_dir)]
        self.last_run = LocalMinerURun(
            command=command,
            output_dir=str(self.output_dir),
            artifacts=artifacts,
            stdout=completed.stdout[-8000:],
            stderr=completed.stderr[-8000:],
            duration_seconds=round(duration, 2),
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Local MinerU pipeline failed: "
                f"{completed.stderr.strip() or completed.stdout.strip() or completed.returncode}"
            )
        return self.last_run

    def load_best_artifact(self, output_dir: Path) -> dict[str, Any]:
        files = self._artifact_files(output_dir)
        content_json = self._find_first(files, ["content_list.json", "_content_list.json"])
        if content_json:
            return {
                "kind": "content_list",
                "payload": self._load_json(content_json),
                "path": str(content_json),
            }
        middle_json = self._find_first(files, ["middle.json", "_middle.json"])
        if middle_json:
            return {
                "kind": "json",
                "payload": self._load_json(middle_json),
                "path": str(middle_json),
            }
        generic_json = next((path for path in files if path.suffix.lower() == ".json"), None)
        if generic_json:
            return {
                "kind": "json",
                "payload": self._load_json(generic_json),
                "path": str(generic_json),
            }
        markdown = next((path for path in files if path.suffix.lower() == ".md"), None)
        if markdown:
            return {
                "kind": "markdown",
                "payload": markdown.read_text(encoding="utf-8"),
                "path": str(markdown),
            }
        raise FileNotFoundError(f"No MinerU JSON or Markdown artifact found in {output_dir}")

    def normalize_mineru_output(
        self,
        raw: dict[str, Any],
        source_file: str,
        output_dir: Path,
    ) -> ParsedDocument:
        source = Path(source_file)
        document_id = self._safe_id(source.stem)
        title = (
            source.stem.replace("_", " ").replace("-", " ").strip() or "Untitled Medical Document"
        )
        kind = raw.get("kind")
        payload = raw.get("payload")
        if kind == "markdown":
            sections = self._sections_from_markdown(str(payload))
            abstract = self._abstract_from_sections(sections)
            raw_json = {"mineru_artifact": raw.get("path"), "markdown": str(payload)[:20000]}
        else:
            sections = self._sections_from_content_list(
                payload if isinstance(payload, list) else []
            )
            if not sections:
                sections = self._sections_from_unknown_json(payload)
            abstract = self._abstract_from_sections(sections)
            raw_json = {
                "mineru_artifact": raw.get("path"),
                "mineru_output_dir": str(output_dir),
                "payload_preview": payload,
            }
        return ParsedDocument(
            document_id=document_id,
            title=title,
            authors=[],
            abstract=abstract,
            sections=sections,
            references=[],
            source_file=source_file,
            raw_mineru_json=raw_json,
        )

    def _sections_from_content_list(self, items: list[dict[str, Any]]) -> list[Section]:
        sections: list[Section] = []
        current = Section(title="Document", level=1, paragraphs=[])
        table_index = 1
        figure_index = 1
        for item in items:
            text = self._item_text(item)
            page = self._page_number(item)
            item_type = str(item.get("type") or item.get("category") or "").lower()
            if self._is_heading(item, text):
                if current.paragraphs or current.tables or current.figures:
                    current.page_end = current.page_end or page
                    sections.append(current)
                current = Section(
                    title=self._clean_heading(text),
                    level=self._heading_level(item, text),
                    page_start=page,
                    page_end=page,
                )
                continue
            if not text.strip():
                continue
            if "table" in item_type:
                current.tables.append(
                    Table(
                        table_id=f"T{table_index}",
                        title=item.get("table_caption") or item.get("caption"),
                        caption=item.get("table_caption") or item.get("caption"),
                        markdown=text,
                        page_number=page,
                    )
                )
                table_index += 1
            elif "image" in item_type or "figure" in item_type:
                current.figures.append(
                    Figure(figure_id=f"F{figure_index}", caption=text, page_number=page)
                )
                figure_index += 1
            else:
                current.paragraphs.append(Paragraph(text=text, page_number=page))
            current.page_start = current.page_start or page
            current.page_end = page or current.page_end
        if current.paragraphs or current.tables or current.figures:
            sections.append(current)
        return self._promote_abstract_title(sections)

    def _sections_from_markdown(self, markdown: str) -> list[Section]:
        sections: list[Section] = []
        current = Section(title="Document", level=1)
        buffer: list[str] = []
        for line in markdown.splitlines():
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                self._flush_markdown_section(sections, current, buffer)
                current = Section(title=heading.group(2).strip(), level=len(heading.group(1)))
                buffer = []
                continue
            buffer.append(line)
        self._flush_markdown_section(sections, current, buffer)
        return self._promote_abstract_title(sections)

    def _flush_markdown_section(
        self, sections: list[Section], current: Section, buffer: list[str]
    ) -> None:
        text = "\n".join(buffer).strip()
        if not text and current.title == "Document":
            return
        table_blocks, paragraph_text = self._extract_markdown_tables(text)
        current.paragraphs = [
            Paragraph(text=part.strip())
            for part in re.split(r"\n\s*\n", paragraph_text)
            if part.strip()
        ]
        current.tables = [
            Table(table_id=f"T{idx + 1}", markdown=table, caption="MinerU extracted table")
            for idx, table in enumerate(table_blocks)
        ]
        sections.append(current)

    def _sections_from_unknown_json(self, payload: Any) -> list[Section]:
        text = json.dumps(payload, ensure_ascii=False)[:20000]
        return [Section(title="MinerU Parsed Content", level=1, paragraphs=[Paragraph(text=text)])]

    def _extract_markdown_tables(self, text: str) -> tuple[list[str], str]:
        lines = text.splitlines()
        tables: list[str] = []
        remaining: list[str] = []
        index = 0
        while index < len(lines):
            if (
                "|" in lines[index]
                and index + 1 < len(lines)
                and re.search(r"\|?\s*:?-{3,}", lines[index + 1])
            ):
                block = [lines[index], lines[index + 1]]
                index += 2
                while index < len(lines) and "|" in lines[index]:
                    block.append(lines[index])
                    index += 1
                tables.append("\n".join(block))
                continue
            remaining.append(lines[index])
            index += 1
        return tables, "\n".join(remaining)

    def _item_text(self, item: dict[str, Any]) -> str:
        candidates = [
            item.get("text"),
            item.get("content"),
            item.get("md"),
            item.get("table_body"),
            item.get("table"),
            item.get("caption"),
            item.get("img_caption"),
        ]
        for value in candidates:
            if isinstance(value, list):
                value = " ".join(str(part) for part in value)
            if value:
                return str(value).strip()
        return ""

    def _is_heading(self, item: dict[str, Any], text: str) -> bool:
        item_type = str(item.get("type") or item.get("category") or "").lower()
        if "title" in item_type or "heading" in item_type:
            return True
        return bool(re.match(r"^\s{0,3}(#{1,6})\s+\S+", text))

    def _heading_level(self, item: dict[str, Any], text: str) -> int:
        if item.get("level"):
            return int(item["level"])
        match = re.match(r"^\s{0,3}(#{1,6})\s+\S+", text)
        return len(match.group(1)) if match else 1

    def _clean_heading(self, text: str) -> str:
        return re.sub(r"^\s{0,3}#{1,6}\s+", "", text).strip()[:200] or "Untitled Section"

    def _page_number(self, item: dict[str, Any]) -> int | None:
        for key in ("page_number", "page_idx", "page"):
            value = item.get(key)
            if isinstance(value, int):
                return value + 1 if key == "page_idx" else value
        return None

    def _abstract_from_sections(self, sections: list[Section]) -> str | None:
        for section in sections:
            if re.search(r"abstract|摘要", section.title, re.I):
                return "\n\n".join(paragraph.text for paragraph in section.paragraphs) or None
        return None

    def _promote_abstract_title(self, sections: list[Section]) -> list[Section]:
        if not sections:
            return sections
        first = sections[0]
        if first.title == "Document" and first.paragraphs:
            text = first.paragraphs[0].text.strip()
            if re.match(r"^(abstract|摘要)[:：]?", text, re.I):
                first.title = "Abstract"
                first.paragraphs[0].text = re.sub(
                    r"^(abstract|摘要)[:：]?\s*", "", text, flags=re.I
                )
        return sections

    def _artifact_files(self, output_dir: Path) -> list[Path]:
        return sorted(path for path in output_dir.rglob("*") if path.is_file())

    def _find_first(self, files: list[Path], suffixes: list[str]) -> Path | None:
        for suffix in suffixes:
            found = next((path for path in files if path.name.endswith(suffix)), None)
            if found:
                return found
        return None

    def _load_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _safe_id(self, value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
        return cleaned or f"mineru-doc-{int(time.time())}"
