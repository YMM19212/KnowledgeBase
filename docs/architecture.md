# Architecture

## Goals

The project turns parsed medical literature into a traceable RAG knowledge base. It separates document parsing, normalization, semantic chunking, metadata storage, vector indexing, retrieval, and answer generation.

## Components

1. Parser layer
   - `BaseParser` defines the common interface.
   - `MockParser` loads a sample MinerU-like JSON file.
   - `MinerUParserAdapter` reserves the remote MinerU integration contract.

2. Normalized document schema
   - `ParsedDocument` stores title, authors, abstract, sections, paragraphs, tables, figures, references, page numbers, source file, and raw MinerU JSON.

3. Chunking layer
   - `MedicalSemanticChunker` uses section hierarchy first.
   - It normalizes section paths and identifies medical evidence roles such as
     `primary_endpoint_result`, `recommendation_block`, and `baseline_table`.
   - `max_tokens` and `overlap_tokens` are fallback controls for unusually long sections.
   - Tables and figure captions become first-class chunks.

4. Evidence layer
   - `EvidenceService` persists `evidence_units` from chunk metadata.
   - Rule extraction builds structured trial, guideline, review/meta, and table
     facts.
   - Optional Kimi enrichment runs only during ingestion or evidence rebuild and
     writes `extraction_mode=hybrid` when successful.

5. Storage layer
   - SQLite stores KB metadata, document metadata, chunks, and fallback vectors.
   - Chroma is the production local vector store adapter.

6. RAG layer
   - Embeddings are provided by sentence-transformers when available.
   - Jina Embeddings can be used for multilingual retrieval through the runtime settings page.
   - Hash embeddings allow offline deterministic tests and demos.
   - QueryGuard blocks out-of-scope prompts but lets broad in-scope medical
     prompts continue.
   - Retrieval reranking is evidence-aware rather than similarity-only.
   - Query responses always include citations and source text, with optional
     `document_type`, `evidence_role`, and `extraction_mode`.

## Data Flow

```text
PDF or sample JSON
  -> parser.parse_pdf()
  -> ParsedDocument
  -> MedicalSemanticChunker.chunk()
  -> Chunk records in SQLite
  -> EvidenceService.replace_document_evidence()
  -> embeddings.embed_texts()
  -> vector_store.upsert()
  -> RAGService.query()
  -> answer + citations
```

## Deployment Shape

The default deployment is a single FastAPI service with local SQLite and Chroma persistence. The same boundaries allow future deployment with a remote MinerU parser, external vector database, and managed LLM API.
