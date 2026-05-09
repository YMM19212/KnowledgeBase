# Agent Benchmark API

This project exposes an OpenAI-compatible HTTP interface so benchmark
platforms can call the knowledge-base agent as if it were a chat model.

## Endpoints

- `GET /v1/models`
- `GET /v1/benchmark/info`
- `POST /v1/chat/completions`

Base URL example:

```text
http://127.0.0.1:8000/v1
```

## Model Metadata

The benchmark-facing metadata is configurable through environment variables:

```env
MEDRAG_BENCHMARK_MODEL_NAME=KnowledgeBase-Agent
MEDRAG_BENCHMARK_MODEL_ID=knowledgebase-agent-v1
MEDRAG_BENCHMARK_PARAMETER_COUNT=backbone-dependent
MEDRAG_BENCHMARK_OPEN_SOURCE=true
MEDRAG_BENCHMARK_CONTEXT_LENGTH=32768
MEDRAG_BENCHMARK_API_KEY=
MEDRAG_BENCHMARK_DEFAULT_KB_ID=1
MEDRAG_BENCHMARK_RELEASE_DATE=2026-05-09
MEDRAG_BENCHMARK_GITHUB_URL=https://github.com/YMM19212/KnowledgeBase
```

`MEDRAG_BENCHMARK_DEFAULT_KB_ID` is recommended for benchmark runs. If it is
not set, the service uses the first available knowledge base.

## OpenAI-Compatible Example

```python
import json
from openai import OpenAI

api_key = ""
base_url = "http://127.0.0.1:8000/v1/"
path = "knowledgebase-agent-v1"
question = "请根据知识库回答：主要结局是什么？"

client = OpenAI(
    api_key=api_key or "EMPTY",
    base_url=base_url,
)

completion = client.chat.completions.create(
    model=path,
    messages=[{"role": "user", "content": question}],
)
response = json.loads(completion.model_dump_json())
print(response["choices"][0]["message"]["content"])
```

If `MEDRAG_BENCHMARK_API_KEY` is configured, send it as a Bearer token:

```python
client = OpenAI(
    api_key="your-benchmark-key",
    base_url="http://127.0.0.1:8000/v1/",
)
```

## Request Shape

`POST /v1/chat/completions`

```json
{
  "model": "knowledgebase-agent-v1",
  "messages": [
    {
      "role": "user",
      "content": "请根据知识库回答：主要结局是什么？"
    }
  ],
  "temperature": 0.1,
  "max_tokens": 1024,
  "stream": false
}
```

## Response Shape

The response follows the OpenAI chat completions format and also includes
traceability fields useful for RAG evaluation:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1746750000,
  "model": "knowledgebase-agent-v1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 123,
    "completion_tokens": 88,
    "total_tokens": 211
  },
  "citations": [],
  "retrieved_chunks": [],
  "evidence_units": [],
  "evidence_sufficiency": "partial",
  "knowledge_base_id": 1
}
```

## Notes

- Streaming is not supported.
- If an OpenAI-compatible LLM is configured, benchmark requests are answered
  directly by that chat model.
- If no LLM is configured, the service falls back to the existing RAG pipeline
  and routes prompts to the configured knowledge base.
- For organizer forms that require "parameter count" or "context length", use
  the metadata of the backbone model you actually deploy behind this service,
  or keep the default benchmark wrapper metadata for smoke-test runs.
