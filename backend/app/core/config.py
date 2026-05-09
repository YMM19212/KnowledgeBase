from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env files."""

    model_config = SettingsConfigDict(env_prefix="MEDRAG_", env_file=".env", extra="ignore")

    app_name: str = "MinerU Medical RAG"
    env: str = "local"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./data/sqlite/medrag.db"
    storage_dir: Path = Path("./data/storage")

    vector_store: str = "chroma"
    chroma_persist_dir: Path = Path("./data/chroma")

    embedding_backend: str = "auto"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    jina_api_key: str | None = None
    jina_embedding_model: str = "jina-embeddings-v5-text-small"

    mock_mineru_json: Path = Path("./examples/sample_mineru_output.json")
    mineru_api_url: str | None = None
    mineru_cli_command: str = "mineru"
    mineru_local_output_dir: Path = Path("./data/mineru_outputs")
    mineru_cli_timeout_seconds: int = Field(default=1800, ge=30)
    mineru_remote_host: str | None = None
    mineru_remote_port: int = Field(default=22, ge=1, le=65535)
    mineru_remote_user: str = "root"
    mineru_remote_password: str | None = None
    mineru_remote_key_path: Path | None = None
    mineru_remote_work_dir: str = "/tmp/medrag_mineru"
    mineru_remote_output_dir: Path = Path("./data/mineru_remote_outputs")

    openai_api_base: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    llm_provider: str = "none"
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None

    benchmark_model_name: str = "KnowledgeBase-Agent"
    benchmark_model_id: str = "knowledgebase-agent-v1"
    benchmark_parameter_count: str = "backbone-dependent"
    benchmark_open_source: bool = True
    benchmark_context_length: int = 32768
    benchmark_api_key: str | None = None
    benchmark_default_kb_id: int | None = None
    benchmark_release_date: str = "2026-05-09"
    benchmark_github_url: str = "https://github.com/YMM19212/KnowledgeBase"

    rag_min_score: float = Field(default=0.05, ge=0.0, le=1.0)
    default_top_k: int = Field(default=5, ge=1, le=50)
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
