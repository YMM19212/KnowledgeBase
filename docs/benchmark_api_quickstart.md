# Benchmark API Quickstart

Use this page for benchmark-platform integration. The service exposes an OpenAI-compatible chat-completions endpoint.

## Required Values

- Base URL: `https://curve-zone-excitement-clan.trycloudflare.com/v1`
- Model ID: `knowledgebase-agent-v1`
- API Key: optional, use `EMPTY` if the platform requires a value

## Python Example

```python
# openai==2.7.2
# requests==2.32.5
# httpx==0.28.1
import json
from openai import OpenAI

api_key = "EMPTY"
base_url = "https://curve-zone-excitement-clan.trycloudflare.com/v1"
path = "knowledgebase-agent-v1"
question = "你好"

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

completion = client.chat.completions.create(
    model=path,
    messages=[{"role": "user", "content": question}],
)

response = json.loads(completion.model_dump_json())
print(response["choices"][0]["message"]["content"])
```

## cURL Example

```bash
curl https://curve-zone-excitement-clan.trycloudflare.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "knowledgebase-agent-v1",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

## Notes

- Fill the benchmark platform endpoint with the `/v1` base URL, not `/v1/chat/completions`.
- The platform should send requests to `POST /v1/chat/completions`.
- This service is a single-turn QA benchmark adapter over the medical literature knowledge base.
