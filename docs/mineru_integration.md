# MinerU Integration

The project is MinerU-ready but does not require MinerU in the current mock phase.

## Current Mock Phase

- `MockParser` reads `examples/sample_mineru_output.json`.
- API ingestion and CLI scripts use this parser by default.
- `MinerUParserAdapter` returns mock data when `MEDRAG_MINERU_API_URL` is empty.

## Local MinerU Pipeline

When MinerU is installed locally, the project can run:

```bash
mineru -p <input_path> -o <output_path> -b pipeline -m auto -l ch -f True -t True
```

Use the API endpoint:

`POST /api/v1/knowledge-bases/{kb_id}/documents/mineru-local`

Multipart fields:

- `file`: PDF/image file
- `method`: `auto`, `txt`, or `ocr`
- `lang`: MinerU OCR language code
- `formula`: boolean
- `table`: boolean

The local adapter first looks for `content_list.json`, then other JSON files, then Markdown. It maps the artifact into `ParsedDocument`, and the existing chunking/indexing/RAG pipeline handles the rest.

## Pre-cleaned MinerU Artifacts

When MinerU outputs are already available, import them directly without running the CLI:

```bash
python scripts/ingest_mineru_outputs.py --input-dir CompetitionMinerU
```

The script scans for `*_content_list.json` under each `auto/` directory and calls `LocalMinerUParserAdapter.parse_output_dir()`.

## Remote SSH MinerU

When MinerU runs on a remote server, configure SSH access:

```bash
MEDRAG_MINERU_REMOTE_HOST=172.31.22.13
MEDRAG_MINERU_REMOTE_PORT=22
MEDRAG_MINERU_REMOTE_USER=root
MEDRAG_MINERU_REMOTE_PASSWORD=...
MEDRAG_MINERU_REMOTE_WORK_DIR=/tmp/medrag_mineru
MEDRAG_MINERU_REMOTE_OUTPUT_DIR=./data/mineru_remote_outputs
```

Remote flow:

```text
Frontend uploads PDF
  -> backend saves file locally
  -> backend uploads PDF over SFTP
  -> backend runs remote mineru pipeline through SSH
  -> backend downloads remote output artifacts
  -> LocalMinerU normalizer maps artifacts to ParsedDocument
  -> semantic chunking, evidence units, vectors, and RAG indexing continue locally
```

API:

- `GET /api/v1/mineru/remote/status`
- `POST /api/v1/knowledge-bases/{kb_id}/documents/mineru-remote`

## Functions to Implement

`MinerUParserAdapter.submit_parse_task(pdf_path)`

- Upload PDF to the MinerU service.
- Return a stable `task_id`.
- Attach request metadata such as document language, OCR mode, and table extraction options if MinerU supports them.

`MinerUParserAdapter.get_parse_result(task_id)`

- Poll or fetch the parse result.
- Handle pending, failed, and completed states.
- Return the raw MinerU JSON payload.

`MinerUParserAdapter.parse_pdf(pdf_path)`

- Submit task.
- Wait for completion or use callback state.
- Fetch result.
- Call `normalize_mineru_json()`.

`MinerUParserAdapter.normalize_mineru_json(raw_mineru_json)`

- Map MinerU blocks into `ParsedDocument`.
- Preserve page numbers, section hierarchy, tables, figure captions, bounding boxes, and raw JSON.
- Keep table markdown or structured table cells when available.

## Contract

Downstream code consumes only `ParsedDocument`. Keep that schema stable to avoid changes in chunking, indexing, retrieval, and API responses.

## Recommended MinerU Metadata

- `page_number`
- `bounding_box`
- layout block type
- section title and heading level
- table id, caption, markdown or cells
- figure id and caption
- references and cross-reference anchors
