import hashlib
import logging
import math
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
import numpy as np

from backend.app.core.config import get_settings
from backend.app.services.settings_service import EffectiveEmbeddingSettings

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text."""

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class HashEmbeddingService(EmbeddingService):
    """Deterministic local embeddings for tests and offline demos."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(float(np.dot(vector, vector)))
        if norm > 0:
            vector /= norm
        return vector.astype(float).tolist()


class SentenceTransformerEmbeddingService(EmbeddingService):
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.astype(float).tolist()


class JinaEmbeddingService(EmbeddingService):
    """Jina AI embedding client for multilingual retrieval."""

    def __init__(
        self,
        api_key: str,
        model: str = "jina-embeddings-v5-text-small",
        batch_size: int = 8,
        max_retries: int = 5,
        max_input_chars: int = 12000,
    ) -> None:
        if not api_key:
            raise ValueError("Jina API key is required for Jina embeddings.")
        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.max_input_chars = max_input_chars

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            vectors.extend(self._embed(batch, task="retrieval.passage"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task="retrieval.query")[0]

    def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        if not texts:
            return []
        prepared_texts = [self._prepare_text(text) for text in texts]
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = httpx.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json={
                        "model": self.model,
                        "task": task,
                        "normalized": True,
                        "input": prepared_texts,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json().get("data", [])
                vectors = [item["embedding"] for item in data]
                if len(vectors) != len(texts):
                    raise RuntimeError(
                        "Jina embeddings returned an unexpected vector count: "
                        f"expected {len(texts)}, got {len(vectors)}"
                    )
                return vectors
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
        if len(texts) > 1:
            midpoint = len(texts) // 2
            return self._embed(texts[:midpoint], task) + self._embed(texts[midpoint:], task)
        assert last_error is not None
        raise last_error

    def _prepare_text(self, text: str) -> str:
        text = text.strip()
        if len(text) <= self.max_input_chars:
            return text
        return text[: self.max_input_chars]


@dataclass(frozen=True)
class EmbeddingFactoryConfig:
    backend: str
    model: str
    jina_api_key: str | None = None


def get_embedding_service(
    runtime_settings: EffectiveEmbeddingSettings | EmbeddingFactoryConfig | None = None,
) -> EmbeddingService:
    settings = get_settings()
    backend = (runtime_settings.backend if runtime_settings else settings.embedding_backend).lower()
    model = runtime_settings.model if runtime_settings else settings.embedding_model
    jina_api_key = runtime_settings.jina_api_key if runtime_settings else settings.jina_api_key
    if backend == "hash":
        return HashEmbeddingService(settings.embedding_dimension)
    if backend == "jina":
        return JinaEmbeddingService(
            api_key=jina_api_key or "",
            model=model or settings.jina_embedding_model,
        )
    if backend in {"sentence-transformers", "sentence_transformers"}:
        return SentenceTransformerEmbeddingService(model)
    try:
        return SentenceTransformerEmbeddingService(model)
    except Exception as exc:  # pragma: no cover - depends on optional runtime packages
        logger.warning("Falling back to hash embeddings: %s", exc)
        return HashEmbeddingService(settings.embedding_dimension)
