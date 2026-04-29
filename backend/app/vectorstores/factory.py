import logging

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.vectorstores.base import VectorStore
from backend.app.vectorstores.sqlite import SQLiteVectorStore

logger = logging.getLogger(__name__)


def get_vector_store(db: Session) -> VectorStore:
    settings = get_settings()
    if settings.vector_store.lower() == "sqlite":
        return SQLiteVectorStore(db)
    if settings.vector_store.lower() == "chroma":
        try:
            from backend.app.vectorstores.chroma import ChromaVectorStore

            return ChromaVectorStore(settings.chroma_persist_dir)
        except Exception as exc:  # pragma: no cover - optional dependency path
            logger.warning("Falling back to SQLite vector store: %s", exc)
            return SQLiteVectorStore(db)
    raise ValueError(f"Unsupported vector store: {settings.vector_store}")
