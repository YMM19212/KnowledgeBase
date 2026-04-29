from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings


def _prepare_sqlite_path(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    db_path = database_url.replace("sqlite:///", "", 1)
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


settings = get_settings()
_prepare_sqlite_path(settings.database_url)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
