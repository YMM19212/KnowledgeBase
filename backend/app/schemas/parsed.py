from typing import Any, Literal

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Paragraph(BaseModel):
    text: str
    page_number: int | None = None
    bounding_box: BoundingBox | None = None


class Table(BaseModel):
    table_id: str
    title: str | None = None
    caption: str | None = None
    markdown: str
    page_number: int | None = None
    bounding_box: BoundingBox | None = None


class Figure(BaseModel):
    figure_id: str
    caption: str
    page_number: int | None = None
    bounding_box: BoundingBox | None = None


class Section(BaseModel):
    title: str
    level: int = 1
    page_start: int | None = None
    page_end: int | None = None
    paragraphs: list[Paragraph] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    subsections: list["Section"] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    document_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    sections: list[Section] = Field(default_factory=list)
    paragraphs: list[Paragraph] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    page_number: int | None = None
    source_file: str | None = None
    raw_mineru_json: dict[str, Any] | None = None


class Chunk(BaseModel):
    document_id: str
    chunk_id: str
    content: str
    section_path: str
    page_start: int | None = None
    page_end: int | None = None
    content_type: Literal["text", "table", "figure_caption", "mixed"] = "text"
    evidence_level: str | None = None
    source_span: dict[str, Any] = Field(default_factory=dict)
    citation_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


Section.model_rebuild()
