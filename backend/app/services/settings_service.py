from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.db import AppSetting

EMBEDDING_BACKEND_KEY = "embedding.backend"
EMBEDDING_MODEL_KEY = "embedding.model"
JINA_API_KEY_KEY = "embedding.jina_api_key"


@dataclass(frozen=True)
class EffectiveEmbeddingSettings:
    backend: str
    model: str
    jina_api_key: str | None
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

    def all_public_settings(self) -> dict[str, str | bool | None]:
        effective = self.effective_embedding_settings()
        return {
            "embedding_backend": effective.backend,
            "embedding_model": effective.model,
            "embedding_source": effective.source,
            "jina_api_key_configured": bool(effective.jina_api_key),
            "jina_api_key_masked": mask_secret(effective.jina_api_key),
        }


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:8]}...{value[-4:]}"
