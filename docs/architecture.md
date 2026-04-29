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
   - `max_tokens` and `overlap_tokens` are fallback controls for unusually long sections.
   - Tables and figure captions become first-class chunks.

4. Storage layer
   - SQLite stores KB metadata, document metadata, chunks, and fallback vectors.
   - Chroma is the production local vector store adapter.

5. RAG layer
   - Embeddings are provided by sentence-transformers when available.
   - Hash embeddings allow offline deterministic tests and demos.
   - Query responses always include citations and source text.

## Data Flow

```text
PDF or sample JSON
  -> parser.parse_pdf()
  -> ParsedDocument
  -> MedicalSemanticChunker.chunk()
  -> Chunk records in SQLite
  -> embeddings.embed_texts()
  -> vector_store.upsert()
  -> RAGService.query()
  -> answer + citations
```

## Deployment Shape

The default deployment is a single FastAPI service with local SQLite and Chroma persistence. The same boundaries allow future deployment with a remote MinerU parser, external vector database, and managed LLM API.

