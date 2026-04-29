from typing import Any

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class KnowledgeBaseRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    document_count: int = 0
    chunk_count: int = 0
    index_status: str = "ready"
    created_at: str | None = None


class DocumentRead(BaseModel):
    id: str
    knowledge_base_id: int
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    source_file: str | None = None
    parse_status: str
    chunk_count: int = 0
    created_at: str | None = None


class LocalMinerURunRead(BaseModel):
    command: list[str]
    output_dir: str
    artifacts: list[str] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0


class LocalMinerUIngestResponse(BaseModel):
    document: DocumentRead
    mineru: LocalMinerURunRead


class LocalMinerUStatus(BaseModel):
    available: bool
    command: str
    version: str | None = None
    error: str | None = None


class ChunkRead(BaseModel):
    document_id: str
    chunk_id: str
    content: str
    section_path: str
    page_start: int | None = None
    page_end: int | None = None
    content_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MockParseRequest(BaseModel):
    knowledge_base_id: int | None = None


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    knowledge_base_id: int
    top_k: int = Field(default=5, ge=1, le=50)
    filters: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    section_path: str
    page_start: int | None = None
    page_end: int | None = None
    citation_text: str
    source_text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_chunks: list[dict[str, Any]]
