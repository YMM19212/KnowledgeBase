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

`GET /knowledge-bases/{kb_id}/documents`

Lists documents in a KB.

`GET /documents/{document_id}`

Returns document metadata and parse status.

`DELETE /documents/{document_id}`

Deletes the document, chunks, and vectors.

`GET /documents/{document_id}/chunks`

Returns chunk content and source metadata.

## Indexing

`POST /knowledge-bases/{kb_id}/index/rebuild`

Rebuilds vectors from stored chunks.

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
  "retrieved_chunks": []
}
```

## Mock Parsing

`POST /parse/mock`

With body `{"knowledge_base_id":1}` the endpoint parses and ingests the sample. Without `knowledge_base_id`, it returns the normalized parsed document.

## Stats

`GET /stats`

Returns counts of knowledge bases, documents, chunks, and SQLite fallback vectors.

