import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod

import numpy as np

from backend.app.core.config import get_settings

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


def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    backend = settings.embedding_backend.lower()
    if backend == "hash":
        return HashEmbeddingService(settings.embedding_dimension)
    if backend in {"sentence-transformers", "sentence_transformers"}:
        return SentenceTransformerEmbeddingService(settings.embedding_model)
    try:
        return SentenceTransformerEmbeddingService(settings.embedding_model)
    except Exception as exc:  # pragma: no cover - depends on optional runtime packages
        logger.warning("Falling back to hash embeddings: %s", exc)
        return HashEmbeddingService(settings.embedding_dimension)
