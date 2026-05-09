import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.deps import db_session
from backend.app.core.config import get_settings
from backend.app.models.db import KnowledgeBase
from backend.app.rag.llm import OpenAICompatibleLLM
from backend.app.rag.service import RAGService
from backend.app.services.settings_service import AppSettingsService

router = APIRouter()


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


def _extract_prompt(messages: list[ChatMessage]) -> str:
    parts: list[str] = []
    for message in messages:
        content = message.content
        if isinstance(content, str):
            text = content.strip()
        else:
            fragments = [
                str(item.get("text", "")).strip()
                for item in content
                if item.get("type") == "text"
            ]
            text = "\n".join(fragment for fragment in fragments if fragment)
        if not text:
            continue
        parts.append(f"{message.role}: {text}")
    if not parts:
        raise HTTPException(status_code=400, detail="No usable text content found in messages")
    return "\n\n".join(parts)


def _to_llm_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
    llm_messages: list[dict[str, str]] = []
    for message in messages:
        content = message.content
        if isinstance(content, str):
            text = content.strip()
        else:
            fragments = [
                str(item.get("text", "")).strip()
                for item in content
                if item.get("type") == "text"
            ]
            text = "\n".join(fragment for fragment in fragments if fragment)
        if text:
            llm_messages.append({"role": message.role, "content": text})
    if not llm_messages:
        raise HTTPException(status_code=400, detail="No usable text content found in messages")
    return llm_messages


def _resolve_knowledge_base_id(db: Session) -> int:
    settings = get_settings()
    if settings.benchmark_default_kb_id:
        kb = db.get(KnowledgeBase, settings.benchmark_default_kb_id)
        if kb:
            return kb.id
    kb = db.query(KnowledgeBase).order_by(KnowledgeBase.id.asc()).first()
    if kb:
        return kb.id
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
    llm = OpenAICompatibleLLM(
        runtime_settings=AppSettingsService(db).effective_llm_settings()
    )
    prompt = _extract_prompt(payload.messages)
    knowledge_base_id: int | None = None
    response_mode = "fallback"
    if llm.configured:
        try:
            answer = llm.chat(
                _to_llm_messages(payload.messages),
                temperature=payload.temperature or 0.1,
                max_tokens=payload.max_tokens,
            )
            result = {
                "citations": [],
                "retrieved_chunks": [],
                "evidence_units": [],
                "evidence_sufficiency": "not_applicable",
            }
            response_mode = "llm"
        except Exception:
            answer = ""
            result = {}
    else:
        answer = ""
        result = {}

    if not answer:
        try:
            knowledge_base_id = _resolve_knowledge_base_id(db)
            result = RAGService(db).query(
                knowledge_base_id=knowledge_base_id,
                query=prompt,
                top_k=settings.default_top_k,
            )
            answer = result["answer"]
            response_mode = "rag"
        except Exception:
            answer = "当前后端没有可用的通用模型或检索能力，无法可靠回答。"
            result = {
                "citations": [],
                "retrieved_chunks": [],
                "evidence_units": [],
                "evidence_sufficiency": "insufficient",
            }
    prompt_tokens = _estimate_tokens(prompt)
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
