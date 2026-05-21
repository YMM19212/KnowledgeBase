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


class MinerUSourceExample(BaseModel):
    source: str
    label: str
    description: str
    example_config: dict[str, Any] = Field(default_factory=dict)


class MinerUSettingsRead(BaseModel):
    mineru_source: str
    mineru_source_origin: str
    mineru_api_url: str | None = None
    mineru_cli_command: str
    mineru_local_output_dir: str
    mineru_remote_host: str | None = None
    mineru_remote_port: int = 22
    mineru_remote_user: str = "root"
    mineru_remote_key_path: str | None = None
    mineru_remote_work_dir: str = "/tmp/medrag_mineru"
    mineru_remote_output_dir: str = "./data/mineru_remote_outputs"
    mineru_remote_source: str = "environment"
    mineru_remote_password_configured: bool = False
    mineru_remote_password_masked: str | None = None
    mineru_remote_configured: bool = False
    examples: list[MinerUSourceExample] = Field(default_factory=list)
    recommended_upload_endpoint: str


class MinerUSettingsUpdate(BaseModel):
    mineru_source: str | None = None
    mineru_api_url: str | None = None
    mineru_remote_host: str | None = None
    mineru_remote_port: int | None = Field(default=None, ge=1, le=65535)
    mineru_remote_user: str | None = None
    mineru_remote_password: str | None = None
    mineru_remote_key_path: str | None = None
    mineru_remote_work_dir: str | None = None
    mineru_remote_output_dir: str | None = None


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


class EvidenceUnitRead(BaseModel):
    id: int
    knowledge_base_id: int
    document_id: str
    chunk_id: str
    evidence_type: str
    canonical_section: str
    claim_text: str
    normalized_facts: dict[str, Any] = Field(default_factory=dict)
    source_text: str
    page_start: int | None = None
    page_end: int | None = None
    citation_text: str
    confidence: float
    created_at: str | None = None


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
    evidence_units: list[dict[str, Any]] = Field(default_factory=list)
    evidence_sufficiency: str = "sufficient"
    answer_mode: str = "rag"
    guard_reason: str | None = None


class EmbeddingSettingsRead(BaseModel):
    embedding_backend: str
    embedding_model: str
    embedding_source: str
    jina_api_key_configured: bool = False
    jina_api_key_masked: str | None = None


class EmbeddingSettingsUpdate(BaseModel):
    embedding_backend: str | None = None
    embedding_model: str | None = None
    jina_api_key: str | None = None


class LLMSettingsRead(BaseModel):
    llm_provider: str
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_source: str
    llm_api_key_configured: bool = False
    llm_api_key_masked: str | None = None


class LLMSettingsUpdate(BaseModel):
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None


class MinerURemoteSettingsRead(BaseModel):
    mineru_remote_host: str | None = None
    mineru_remote_port: int = 22
    mineru_remote_user: str = "root"
    mineru_remote_key_path: str | None = None
    mineru_remote_work_dir: str = "/tmp/medrag_mineru"
    mineru_remote_output_dir: str = "./data/mineru_remote_outputs"
    mineru_remote_source: str = "environment"
    mineru_remote_password_configured: bool = False
    mineru_remote_password_masked: str | None = None
    mineru_remote_configured: bool = False


class MinerURemoteSettingsUpdate(BaseModel):
    mineru_remote_host: str | None = None
    mineru_remote_port: int | None = Field(default=None, ge=1, le=65535)
    mineru_remote_user: str | None = None
    mineru_remote_password: str | None = None
    mineru_remote_key_path: str | None = None
    mineru_remote_work_dir: str | None = None
    mineru_remote_output_dir: str | None = None


class MinerUPipelineRunRead(BaseModel):
    source: str
    parser: str
    status: str = "completed"
    input_file: str | None = None
    output_dir: str | None = None
    command: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float | None = None
    mineru_api_url: str | None = None
    remote_host: str | None = None


class MinerUPipelineIngestResponse(BaseModel):
    document: DocumentRead
    pipeline: MinerUPipelineRunRead
