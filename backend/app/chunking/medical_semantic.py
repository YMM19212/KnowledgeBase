import re
from collections.abc import Iterable
from hashlib import sha1

from backend.app.schemas.parsed import Chunk, Figure, ParsedDocument, Section, Table

MEDICAL_SECTION_PATTERNS = {
    "abstract": r"abstract|summary|摘要",
    "primary outcome": r"primary outcome|primary endpoint|主要结局|主要终点",
    "secondary outcome": r"secondary outcome|secondary endpoint|次要结局|次要终点",
    "subgroup analysis": r"subgroup analysis",
    "sensitivity analysis": r"sensitivity analysis",
    "adverse events": r"adverse events?|safety|harms?|不良|安全",
    "participants": r"participants|patients|population|eligibility|受试者|患者|纳入|排除",
    "intervention": r"intervention|treatment|randomization|干预|治疗|随机",
    "outcomes": r"outcomes?|endpoints?|结局|终点",
    "introduction": r"introduction|background|引言|背景",
    "methods": r"methods?|materials and methods|study design|方法|研究设计",
    "results": r"results|findings|结果",
    "discussion": r"discussion|讨论",
    "conclusion": r"conclusions?|结论",
    "limitations": r"limitations?|局限",
}


class MedicalSemanticChunker:
    """Chunk medical papers by section logic, with token limits as a fallback."""

    def __init__(self, max_tokens: int = 420, overlap_tokens: int = 60) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        if document.abstract:
            chunks.extend(
                self._text_chunks(
                    document_id=document.document_id,
                    text=document.abstract,
                    section_path="Abstract",
                    page_start=1,
                    page_end=1,
                    ordinal=len(chunks),
                )
            )
        for section in document.sections:
            chunks.extend(self._chunk_section(document.document_id, section, [], len(chunks)))
        return chunks

    def _chunk_section(
        self, document_id: str, section: Section, parents: list[str], start_ordinal: int
    ) -> list[Chunk]:
        section_path = " > ".join([*parents, section.title])
        chunks: list[Chunk] = []
        text = "\n\n".join(p.text for p in section.paragraphs if p.text.strip())
        if text.strip():
            chunks.extend(
                self._text_chunks(
                    document_id=document_id,
                    text=text,
                    section_path=section_path,
                    page_start=section.page_start,
                    page_end=section.page_end,
                    ordinal=start_ordinal + len(chunks),
                )
            )
        for table in section.tables:
            chunks.append(
                self._table_chunk(document_id, table, section_path, start_ordinal + len(chunks))
            )
        for figure in section.figures:
            chunks.append(
                self._figure_chunk(document_id, figure, section_path, start_ordinal + len(chunks))
            )
        for child in section.subsections:
            chunks.extend(
                self._chunk_section(
                    document_id, child, [*parents, section.title], start_ordinal + len(chunks)
                )
            )
        return chunks

    def _text_chunks(
        self,
        document_id: str,
        text: str,
        section_path: str,
        page_start: int | None,
        page_end: int | None,
        ordinal: int,
    ) -> list[Chunk]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        groups = self._group_paragraphs(paragraphs)
        return [
            Chunk(
                document_id=document_id,
                chunk_id=self._chunk_id(document_id, section_path, ordinal + idx, group),
                content=group,
                section_path=section_path,
                page_start=page_start,
                page_end=page_end,
                content_type="text",
                evidence_level=self._evidence_level(section_path),
                source_span={"type": "section", "section_path": section_path},
                citation_text=self._citation(section_path, page_start, page_end),
                metadata={
                    "section_path": section_path,
                    "canonical_section": self._canonical_section(section_path),
                    "evidence_type": self._evidence_type(section_path, "text"),
                },
            )
            for idx, group in enumerate(groups)
        ]

    def _table_chunk(
        self, document_id: str, table: Table, section_path: str, ordinal: int
    ) -> Chunk:
        content = "\n".join(
            item
            for item in [table.title or "", table.caption or "", table.markdown]
            if item.strip()
        )
        return Chunk(
            document_id=document_id,
            chunk_id=self._chunk_id(document_id, section_path, ordinal, content),
            content=content,
            section_path=section_path,
            page_start=table.page_number,
            page_end=table.page_number,
            content_type="table",
            evidence_level=self._evidence_level(section_path),
            source_span={"type": "table", "table_id": table.table_id},
            citation_text=self._citation(
                section_path, table.page_number, table.page_number, table.table_id
            ),
            metadata={
                "section_path": section_path,
                "canonical_section": self._canonical_section(section_path),
                "evidence_type": "table_evidence",
                "table_id": table.table_id,
            },
        )

    def _figure_chunk(
        self, document_id: str, figure: Figure, section_path: str, ordinal: int
    ) -> Chunk:
        return Chunk(
            document_id=document_id,
            chunk_id=self._chunk_id(document_id, section_path, ordinal, figure.caption),
            content=figure.caption,
            section_path=section_path,
            page_start=figure.page_number,
            page_end=figure.page_number,
            content_type="figure_caption",
            evidence_level=self._evidence_level(section_path),
            source_span={"type": "figure", "figure_id": figure.figure_id},
            citation_text=self._citation(
                section_path, figure.page_number, figure.page_number, figure.figure_id
            ),
            metadata={
                "section_path": section_path,
                "canonical_section": self._canonical_section(section_path),
                "evidence_type": "figure_evidence",
                "figure_id": figure.figure_id,
            },
        )

    def _group_paragraphs(self, paragraphs: Iterable[str]) -> list[str]:
        groups: list[str] = []
        current: list[str] = []
        for paragraph in paragraphs:
            if self._token_count("\n\n".join([*current, paragraph])) <= self.max_tokens:
                current.append(paragraph)
                continue
            if current:
                groups.append("\n\n".join(current))
            if self._token_count(paragraph) <= self.max_tokens:
                current = [paragraph]
            else:
                groups.extend(self._fallback_split(paragraph))
                current = []
        if current:
            groups.append("\n\n".join(current))
        return groups or [""]

    def _fallback_split(self, text: str) -> list[str]:
        words = text.split()
        if not words:
            return []
        step = max(1, self.max_tokens - self.overlap_tokens)
        return [" ".join(words[i : i + self.max_tokens]) for i in range(0, len(words), step)]

    def _token_count(self, text: str) -> int:
        return max(1, len(re.findall(r"\w+|[\u4e00-\u9fff]", text)))

    def _canonical_section(self, section_path: str) -> str:
        text = section_path.lower()
        for canonical, pattern in MEDICAL_SECTION_PATTERNS.items():
            if re.search(pattern, text):
                return canonical
        return "other"

    def _evidence_level(self, section_path: str) -> str | None:
        canonical = self._canonical_section(section_path)
        if canonical in {"primary outcome", "secondary outcome", "adverse events"}:
            return "clinical_outcome"
        if canonical in {"methods", "participants", "intervention"}:
            return "study_design"
        return None

    def _evidence_type(self, section_path: str, content_type: str) -> str:
        if content_type == "table":
            return "table_evidence"
        if content_type == "figure_caption":
            return "figure_evidence"
        if re.search(r"问题[一二三四五六七八九十\d]+", section_path):
            return "clinical_question_answer"
        canonical = self._canonical_section(section_path)
        if canonical == "primary outcome":
            return "primary_outcome"
        if canonical == "secondary outcome":
            return "secondary_outcome"
        if canonical == "adverse events":
            return "safety_or_adverse_event"
        if canonical == "results" and re.search(r"abstract|摘要", section_path, re.I):
            return "abstract_result"
        if canonical != "other":
            return f"{canonical.replace(' ', '_')}_evidence"
        return "text_evidence"

    def _citation(
        self,
        section_path: str,
        page_start: int | None,
        page_end: int | None,
        source_id: str | None = None,
    ) -> str:
        page = (
            f"p.{page_start}"
            if page_start == page_end or page_end is None
            else f"pp.{page_start}-{page_end}"
        )
        suffix = f", {source_id}" if source_id else ""
        return f"{section_path} ({page}{suffix})" if page_start else f"{section_path}{suffix}"

    def _chunk_id(self, document_id: str, section_path: str, ordinal: int, content: str) -> str:
        digest = sha1(f"{document_id}|{section_path}|{ordinal}|{content}".encode()).hexdigest()[:12]
        return f"{document_id}-c{ordinal:04d}-{digest}"
