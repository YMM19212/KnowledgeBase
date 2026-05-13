import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import db_session
from backend.app.core.config import get_settings
from backend.app.models.db import ChunkRecord, KnowledgeBase
from backend.app.rag.service import RAGService

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    user: str | None = None


def _check_benchmark_api_key(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.benchmark_api_key:
        return
    expected = f"Bearer {settings.benchmark_api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid benchmark API key")


def _extract_text_content(message: ChatMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    fragments = [
        str(item.get("text", "")).strip()
        for item in content
        if item.get("type") == "text"
    ]
    return "\n".join(fragment for fragment in fragments if fragment)


def _extract_prompt(messages: list[ChatMessage]) -> str:
    parts: list[str] = []
    for message in messages:
        text = _extract_text_content(message)
        if not text:
            continue
        parts.append(f"{message.role}: {text}")
    if not parts:
        raise HTTPException(status_code=400, detail="No usable text content found in messages")
    return "\n\n".join(parts)


def _extract_last_user_message(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role != "user":
            continue
        text = _extract_text_content(message)
        if text:
            return text
    raise HTTPException(status_code=400, detail="No usable user message found in messages")


def _resolve_knowledge_base_id(db: Session) -> int:
    settings = get_settings()
    if settings.benchmark_default_kb_id:
        kb = db.get(KnowledgeBase, settings.benchmark_default_kb_id)
        if kb:
            return kb.id
    rows = db.execute(
        select(KnowledgeBase.id, func.count(ChunkRecord.id).label("chunk_count"))
        .outerjoin(ChunkRecord, ChunkRecord.knowledge_base_id == KnowledgeBase.id)
        .group_by(KnowledgeBase.id)
        .order_by(KnowledgeBase.id.asc())
    ).all()
    for kb_id, chunk_count in rows:
        if chunk_count and chunk_count > 0:
            return kb_id
    if rows:
        return rows[0][0]
    raise HTTPException(
        status_code=503,
        detail="No knowledge base is available for benchmark serving",
    )


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@router.get("/models", dependencies=[Depends(_check_benchmark_api_key)])
def list_models():
    settings = get_settings()
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": settings.benchmark_model_id,
                "object": "model",
                "created": now,
                "owned_by": settings.app_name,
            }
        ],
    }


@router.get("/benchmark/info", dependencies=[Depends(_check_benchmark_api_key)])
def benchmark_info():
    settings = get_settings()
    return {
        "model_name": settings.benchmark_model_name,
        "parameter_count": settings.benchmark_parameter_count,
        "open_source": settings.benchmark_open_source,
        "context_length": settings.benchmark_context_length,
        "model_api_endpoint": "/v1/chat/completions",
        "model_id": settings.benchmark_model_id,
        "api_key_required": bool(settings.benchmark_api_key),
        "github_url": settings.benchmark_github_url,
        "release_date": settings.benchmark_release_date,
        "serving_mode": "single_turn_rag",
    }


@router.post("/chat/completions", dependencies=[Depends(_check_benchmark_api_key)])
def chat_completions(
    payload: ChatCompletionRequest,
    db: Session = Depends(db_session),
):
    settings = get_settings()
    if payload.stream:
        raise HTTPException(status_code=400, detail="Streaming is not supported")
    if payload.model and payload.model != settings.benchmark_model_id:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown model '{payload.model}'. "
                f"Use '{settings.benchmark_model_id}' instead."
            ),
        )
    raw_prompt = _extract_prompt(payload.messages)
    query = _extract_last_user_message(payload.messages)
    knowledge_base_id = _resolve_knowledge_base_id(db)
    response_mode = "rag"
    logger.info(
        "benchmark request model=%s kb_id=%s prompt_chars=%s stream=%s",
        payload.model,
        knowledge_base_id,
        len(raw_prompt),
        payload.stream,
    )
    try:
        result = RAGService(db).query(
            knowledge_base_id=knowledge_base_id,
            query=query,
            top_k=settings.default_top_k,
        )
        answer = result["answer"]
        response_mode = result.get("answer_mode", "rag")
    except Exception:
        answer = "当前后端问答链路暂不可用，无法可靠回答。"
        result = {
            "citations": [],
            "retrieved_chunks": [],
            "evidence_units": [],
            "evidence_sufficiency": "insufficient",
        }
        response_mode = "fallback"
    prompt_tokens = _estimate_tokens(raw_prompt)
    completion_tokens = _estimate_tokens(answer)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": settings.benchmark_model_id,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "citations": result.get("citations", []),
        "retrieved_chunks": result.get("retrieved_chunks", []),
        "evidence_units": result.get("evidence_units", []),
        "evidence_sufficiency": result.get("evidence_sufficiency", "partial"),
        "knowledge_base_id": knowledge_base_id,
        "response_mode": response_mode,
    }
