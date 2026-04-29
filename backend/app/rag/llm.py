from typing import Any

import httpx

from backend.app.core.config import get_settings


class OpenAICompatibleLLM:
    """Minimal OpenAI-compatible chat completion client."""

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self.api_base = api_base or settings.llm_base_url or settings.openai_api_base
        self.api_key = api_key or settings.llm_api_key or settings.openai_api_key
        self.model = model or settings.llm_model or settings.openai_model

    @property
    def configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    def answer(self, question: str, evidence: list[dict[str, Any]]) -> str:
        if not self.configured:
            raise RuntimeError("LLM is not configured")
        context = "\n\n".join(
            f"[{idx + 1}] {item['citation_text']}\n{item['source_text']}"
            for idx, item in enumerate(evidence)
        )
        payload = {
            "model": self.model,
            "messages": [
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
            "temperature": 0.1,
        }
        response = httpx.post(
            f"{self.api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
