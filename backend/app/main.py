import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.openai_routes import router as openai_router
from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging, mask_ip
from backend.app.db.session import engine
from backend.app.models.db import Base

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)

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


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    client_ip = request.client.host if request.client else None
    forwarded_for = request.headers.get("x-forwarded-for")
    cf_ip = request.headers.get("cf-connecting-ip")
    user_agent = request.headers.get("user-agent", "-")
    logger.info(
        (
            "access method=%s path=%s status=%s duration_ms=%.2f "
            "client_ip=%s cf_ip=%s forwarded_for=%s user_agent=%s"
        ),
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        mask_ip(client_ip),
        mask_ip(cf_ip),
        forwarded_for or "-",
        user_agent[:160],
    )
    return response


app.include_router(router, prefix=settings.api_prefix)
app.include_router(openai_router, prefix="/v1")
