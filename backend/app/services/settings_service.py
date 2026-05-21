from dataclasses import dataclass
from pathlib import Path

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
MINERU_SOURCE_KEY = "mineru.source"
MINERU_API_URL_KEY = "mineru.api_url"
MINERU_REMOTE_HOST_KEY = "mineru.remote.host"
MINERU_REMOTE_PORT_KEY = "mineru.remote.port"
MINERU_REMOTE_USER_KEY = "mineru.remote.user"
MINERU_REMOTE_PASSWORD_KEY = "mineru.remote.password"
MINERU_REMOTE_KEY_PATH_KEY = "mineru.remote.key_path"
MINERU_REMOTE_WORK_DIR_KEY = "mineru.remote.work_dir"
MINERU_REMOTE_OUTPUT_DIR_KEY = "mineru.remote.output_dir"


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


@dataclass(frozen=True)
class EffectiveMinerURemoteSettings:
    host: str | None
    port: int
    user: str
    password: str | None
    key_path: Path | None
    work_dir: str
    output_dir: Path
    source: str


@dataclass(frozen=True)
class EffectiveMinerUSettings:
    source: str
    api_url: str | None
    cli_command: str
    local_output_dir: Path
    remote: EffectiveMinerURemoteSettings
    source_origin: str


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

    def effective_mineru_remote_settings(self) -> EffectiveMinerURemoteSettings:
        settings = get_settings()
        host = self.get(MINERU_REMOTE_HOST_KEY) or settings.mineru_remote_host
        port_raw = self.get(MINERU_REMOTE_PORT_KEY)
        try:
            port = int(port_raw) if port_raw else settings.mineru_remote_port
        except ValueError:
            port = settings.mineru_remote_port
        user = self.get(MINERU_REMOTE_USER_KEY) or settings.mineru_remote_user
        password = self.get(MINERU_REMOTE_PASSWORD_KEY) or settings.mineru_remote_password
        key_path_raw = self.get(MINERU_REMOTE_KEY_PATH_KEY)
        key_path = Path(key_path_raw) if key_path_raw else settings.mineru_remote_key_path
        work_dir = self.get(MINERU_REMOTE_WORK_DIR_KEY) or settings.mineru_remote_work_dir
        output_dir_raw = self.get(MINERU_REMOTE_OUTPUT_DIR_KEY)
        output_dir = Path(output_dir_raw) if output_dir_raw else settings.mineru_remote_output_dir
        source = "database" if self.get(MINERU_REMOTE_HOST_KEY) else "environment"
        return EffectiveMinerURemoteSettings(
            host=host,
            port=port,
            user=user,
            password=password,
            key_path=key_path,
            work_dir=work_dir,
            output_dir=output_dir,
            source=source,
        )

    def effective_mineru_settings(self) -> EffectiveMinerUSettings:
        settings = get_settings()
        remote = self.effective_mineru_remote_settings()
        source = self.get(MINERU_SOURCE_KEY)
        api_url = self.get(MINERU_API_URL_KEY) or settings.mineru_api_url
        if not source:
            if remote.host and (remote.password or remote.key_path):
                source = "remote-ssh"
            elif api_url:
                source = "remote-api"
            elif settings.mineru_cli_command:
                source = "local-cli"
            else:
                source = "mock"
        return EffectiveMinerUSettings(
            source=source,
            api_url=api_url,
            cli_command=settings.mineru_cli_command,
            local_output_dir=settings.mineru_local_output_dir,
            remote=remote,
            source_origin="database" if self.get(MINERU_SOURCE_KEY) else "environment",
        )

    def all_public_settings(self) -> dict[str, str | int | bool | None]:
        effective = self.effective_embedding_settings()
        llm = self.effective_llm_settings()
        mineru = self.effective_mineru_settings()
        mineru_remote = mineru.remote
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
            "mineru_source": mineru.source,
            "mineru_source_origin": mineru.source_origin,
            "mineru_api_url": mineru.api_url,
            "mineru_cli_command": mineru.cli_command,
            "mineru_local_output_dir": str(mineru.local_output_dir),
            "mineru_remote_host": mineru_remote.host,
            "mineru_remote_port": mineru_remote.port,
            "mineru_remote_user": mineru_remote.user,
            "mineru_remote_key_path": (
                str(mineru_remote.key_path) if mineru_remote.key_path else None
            ),
            "mineru_remote_work_dir": mineru_remote.work_dir,
            "mineru_remote_output_dir": str(mineru_remote.output_dir),
            "mineru_remote_source": mineru_remote.source,
            "mineru_remote_password_configured": bool(mineru_remote.password),
            "mineru_remote_password_masked": mask_secret(mineru_remote.password),
            "mineru_remote_configured": bool(
                mineru_remote.host
                and mineru_remote.user
                and (mineru_remote.password or mineru_remote.key_path)
            ),
        }


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:8]}...{value[-4:]}"
