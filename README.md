# MinerU Medical RAG

MinerU Medical RAG is a production-oriented starter project for building high-quality, traceable RAG knowledge bases from medical literature. It is designed for the MinerU medical document parsing challenge, but the current stage runs without a live MinerU server by using a mock MinerU JSON sample.

## Features

- FastAPI backend with versioned APIs.
- SQLite metadata store for local development.
- Chroma vector store adapter, with SQLite vector fallback for offline demos and tests.
- Configurable embedding layer: sentence-transformers by default, deterministic hash embeddings when offline.
- MinerU-ready parser boundary: `BaseParser`, `MinerUParserAdapter`, and `MockParser`.
- Medical semantic chunking based on paper sections such as Primary outcome, Secondary outcome, Adverse events, Subgroup analysis, Limitations, and tables/figures.
- Traceable retrieval and QA responses with chunk, document, section, page, score, and source text.
- CLI scripts for creating knowledge bases, ingesting sample data, rebuilding indexes, and querying.
- Dockerfile, docker-compose, pytest tests, ruff/black configuration, MIT license.

## Architecture

```text
PDF / MinerU JSON
  -> Parser adapter
  -> Normalized ParsedDocument
  -> MedicalSemanticChunker
  -> Metadata DB + Vector Store
  -> Retrieval + optional LLM
  -> Answer with citations
```

The system keeps parsing, chunking, indexing, retrieval, and answer generation as separate modules so each layer can be replaced independently.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
make install
cp .env.example .env
MEDRAG_EMBEDDING_BACKEND=hash MEDRAG_VECTOR_STORE=sqlite make ingest-sample
MEDRAG_EMBEDDING_BACKEND=hash MEDRAG_VECTOR_STORE=sqlite make dev
```

Open:

- API health: [http://localhost:8000/health](http://localhost:8000/health)
- OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

For real embedding and Chroma indexing:

```bash
make install-rag
make ingest-sample
make dev
```

## Docker Start

```bash
docker compose up --build
```

The API listens on `http://localhost:8000`. The Web console listens on
`http://localhost:5173`.

## Frontend Console

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The console provides Dashboard, KB management, document/chunk inspection,
traceable RAG QA, MinerU integration settings, evaluation analysis, and system
settings pages.

## Jina Embeddings

Jina embeddings are supported through environment variables or the frontend
System Settings page:

```bash
MEDRAG_EMBEDDING_BACKEND=jina
MEDRAG_EMBEDDING_MODEL=jina-embeddings-v5-text-small
MEDRAG_JINA_API_KEY=your_jina_api_key
```

After changing embedding settings, rebuild the target knowledge base index.

## API Usage

Create a KB:

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Medical KB","description":"Clinical trial demo"}'
```

Ingest the mock MinerU output into KB `1`:

```bash
curl -X POST http://localhost:8000/api/v1/parse/mock \
  -H "Content-Type: application/json" \
  -d '{"knowledge_base_id":1}'
```

Query:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"knowledge_base_id":1,"query":"What was the primary outcome at week 24?","top_k":5}'
```

CLI:

```bash
python scripts/create_kb.py --name "Demo Medical KB"
python scripts/ingest_sample.py --kb-id 1
python scripts/query.py --kb-id 1 --query "Were serious adverse events increased?"
```

## MinerU Integration Roadmap

The current mock phase reads `examples/sample_mineru_output.json`. The formal MinerU phase should implement:

- `MinerUParserAdapter.submit_parse_task()`
- `MinerUParserAdapter.get_parse_result()`
- `MinerUParserAdapter.parse_pdf()`
- `MinerUParserAdapter.normalize_mineru_json()`

The normalized output should keep the same internal `ParsedDocument` schema so chunking, indexing, retrieval, QA, and APIs do not need to change.

## Evaluation

See [docs/evaluation_plan.md](docs/evaluation_plan.md). The baseline plan measures parsing structure preservation, semantic chunk quality, retrieval recall, citation accuracy, and answer faithfulness.

## Project Structure

```text
backend/app/
  api/            FastAPI routes and dependencies
  core/           settings and logging
  db/             database session and base metadata
  models/         SQLAlchemy models
  schemas/        Pydantic API and parser schemas
  parsers/        BaseParser, MockParser, MinerU adapter
  chunking/       medical semantic chunker
  vectorstores/   Chroma and SQLite vector stores
  rag/            embeddings, optional LLM, query service
  services/       KB, document, indexing orchestration
backend/tests/    pytest tests
examples/         mock MinerU output and sample queries
docs/             architecture and integration docs
scripts/          CLI utilities
```

## License

MIT License.
