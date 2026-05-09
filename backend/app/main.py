from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.openai_routes import router as openai_router
from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.db.session import engine
from backend.app.models.db import Base

configure_logging()
settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MinerU-ready medical literature RAG knowledge base API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(router, prefix=settings.api_prefix)
app.include_router(openai_router, prefix="/v1")
