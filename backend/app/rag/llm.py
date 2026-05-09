from typing import Any

import httpx

from backend.app.core.config import get_settings
from backend.app.services.settings_service import EffectiveLLMSettings


class OpenAICompatibleLLM:
    """Minimal OpenAI-compatible chat completion client."""

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        runtime_settings: EffectiveLLMSettings | None = None,
    ) -> None:
        settings = get_settings()
        default_api_base = settings.llm_base_url or settings.openai_api_base
        default_api_key = settings.llm_api_key or settings.openai_api_key
        default_model = settings.llm_model or settings.openai_model
        runtime_api_base = runtime_settings.base_url if runtime_settings else None
        runtime_api_key = runtime_settings.api_key if runtime_settings else None
        runtime_model = runtime_settings.model if runtime_settings else None
        self.api_base = api_base or runtime_api_base or default_api_base
        self.api_key = api_key or runtime_api_key or default_api_key
        self.model = model or runtime_model or default_model

    @property
    def configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        if not self.configured:
            raise RuntimeError("LLM is not configured")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        response = httpx.post(
            f"{self.api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def answer(self, question: str, evidence: list[dict[str, Any]]) -> str:
        context = "\n\n".join(
            f"[{idx + 1}] {item['citation_text']}\n{item['source_text']}"
            for idx, item in enumerate(evidence)
        )
        return self.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You answer medical literature questions strictly from the "
                        "provided evidence. "
                        "If evidence is insufficient, say so. Include citation numbers."
                    ),
                },
                {"role": "user", "content": f"Question: {question}\n\nEvidence:\n{context}"},
            ],
            temperature=0.1,
        )
