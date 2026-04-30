# API

Base URL: `/api/v1`

## Health

`GET /health`

Returns service status.

## Knowledge Bases

`POST /knowledge-bases`

```json
{"name":"Demo Medical KB","description":"Clinical trial demo"}
```

`GET /knowledge-bases`

Returns all knowledge bases with document counts.

`DELETE /knowledge-bases/{kb_id}`

Deletes metadata, documents, chunks, and vectors for the KB.

## Documents

`POST /knowledge-bases/{kb_id}/documents`

Multipart upload. In the mock phase, uploaded PDF bytes are saved locally and parsed through the mock parser unless the parser is replaced.

`POST /knowledge-bases/{kb_id}/documents/mineru-remote`

Multipart upload. The backend uploads the file to the configured SSH server,
runs remote MinerU pipeline, downloads artifacts, then ingests the normalized
document.

`GET /mineru/remote/status`

Checks SSH connectivity and remote `mineru --version`.

`GET /knowledge-bases/{kb_id}/documents`

Lists documents in a KB.

`GET /documents/{document_id}`

Returns document metadata and parse status.

`DELETE /documents/{document_id}`

Deletes the document, chunks, and vectors.

`GET /documents/{document_id}/chunks`

Returns chunk content and source metadata.

`GET /documents/{document_id}/evidence-units`

Returns medical evidence units derived from the document chunks.

`GET /knowledge-bases/{kb_id}/evidence-units`

Returns all evidence units in a knowledge base.

## Indexing

`POST /knowledge-bases/{kb_id}/index/rebuild`

Rebuilds evidence units and vectors from stored chunks.

`POST /knowledge-bases/{kb_id}/evidence/rebuild`

Rebuilds only the evidence-unit layer. If Kimi is configured, this endpoint runs
LLM enrichment during rebuild; otherwise it uses rule extraction.

## Query

`POST /query`

```json
{
  "knowledge_base_id": 1,
  "query": "What was the primary outcome at week 24?",
  "top_k": 5,
  "filters": {"content_type": "text"}
}
```

Response:

```json
{
  "answer": "...",
  "citations": [
    {
      "chunk_id": "...",
      "document_id": "...",
      "section_path": "Results > Primary outcome",
      "page_start": 5,
      "page_end": 6,
      "citation_text": "Results > Primary outcome (pp.5-6)",
      "source_text": "...",
      "score": 0.82
    }
  ],
  "retrieved_chunks": [],
  "evidence_units": [
    {
      "evidence_type": "primary_outcome",
      "canonical_section": "primary outcome",
      "claim_text": "...",
      "normalized_facts": {
        "llm_enriched": false,
        "values": ["0.11 ± 0.31"]
      }
    }
  ],
  "evidence_sufficiency": "sufficient"
}
```

## Settings

`GET /settings/embedding` and `PUT /settings/embedding` manage embedding backend,
model, and Jina API key.

`GET /settings/llm` and `PUT /settings/llm` manage Kimi/OpenAI-compatible evidence
enrichment settings:

```json
{
  "llm_provider": "moonshot",
  "llm_base_url": "https://api.moonshot.ai/v1",
  "llm_model": "kimi-k2.5",
  "llm_api_key": "..."
}
```

## Mock Parsing

`POST /parse/mock`

With body `{"knowledge_base_id":1}` the endpoint parses and ingests the sample. Without `knowledge_base_id`, it returns the normalized parsed document.

## Stats

`GET /stats`

Returns counts of knowledge bases, documents, chunks, and SQLite fallback vectors.
