from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.db import AppSetting

EMBEDDING_BACKEND_KEY = "embedding.backend"
EMBEDDING_MODEL_KEY = "embedding.model"
JINA_API_KEY_KEY = "embedding.jina_api_key"
LLM_PROVIDER_KEY = "llm.provider"
LLM_BASE_URL_KEY = "llm.base_url"
LLM_MODEL_KEY = "llm.model"
LLM_API_KEY_KEY = "llm.api_key"


@dataclass(frozen=True)
class EffectiveEmbeddingSettings:
    backend: str
    model: str
    jina_api_key: str | None
    source: str


@dataclass(frozen=True)
class EffectiveLLMSettings:
    provider: str
    base_url: str | None
    model: str | None
    api_key: str | None
    source: str


class AppSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, key: str) -> str | None:
        setting = self.db.get(AppSetting, key)
        return setting.value if setting else None

    def set(self, key: str, value: str) -> None:
        setting = self.db.get(AppSetting, key)
        if setting:
            setting.value = value
        else:
            self.db.add(AppSetting(key=key, value=value))
        self.db.commit()

    def effective_embedding_settings(self) -> EffectiveEmbeddingSettings:
        settings = get_settings()
        backend = self.get(EMBEDDING_BACKEND_KEY) or settings.embedding_backend
        default_model = (
            settings.jina_embedding_model
            if backend.lower() == "jina"
            else settings.embedding_model
        )
        model = self.get(EMBEDDING_MODEL_KEY) or default_model
        jina_api_key = self.get(JINA_API_KEY_KEY) or settings.jina_api_key
        source = "database" if self.get(EMBEDDING_BACKEND_KEY) else "environment"
        return EffectiveEmbeddingSettings(
            backend=backend,
            model=model,
            jina_api_key=jina_api_key,
            source=source,
        )

    def effective_llm_settings(self) -> EffectiveLLMSettings:
        settings = get_settings()
        provider = (
            self.get(LLM_PROVIDER_KEY)
            or settings.llm_provider
            or ("openai-compatible" if settings.openai_api_key else "none")
        )
        default_base_url = settings.llm_base_url or settings.openai_api_base
        default_model = settings.llm_model or settings.openai_model
        default_api_key = settings.llm_api_key or settings.openai_api_key
        base_url = self.get(LLM_BASE_URL_KEY) or default_base_url
        model = self.get(LLM_MODEL_KEY) or default_model
        api_key = self.get(LLM_API_KEY_KEY) or default_api_key
        source = "database" if self.get(LLM_PROVIDER_KEY) else "environment"
        return EffectiveLLMSettings(
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
            source=source,
        )

    def all_public_settings(self) -> dict[str, str | bool | None]:
        effective = self.effective_embedding_settings()
        llm = self.effective_llm_settings()
        return {
            "embedding_backend": effective.backend,
            "embedding_model": effective.model,
            "embedding_source": effective.source,
            "jina_api_key_configured": bool(effective.jina_api_key),
            "jina_api_key_masked": mask_secret(effective.jina_api_key),
            "llm_provider": llm.provider,
            "llm_base_url": llm.base_url,
            "llm_model": llm.model,
            "llm_source": llm.source,
            "llm_api_key_configured": bool(llm.api_key),
            "llm_api_key_masked": mask_secret(llm.api_key),
        }


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:8]}...{value[-4:]}"
