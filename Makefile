.PHONY: install install-rag dev test lint format ingest-sample rebuild-index query clean

install:
	python -m pip install -e ".[dev]"

install-rag:
	python -m pip install -e ".[rag,dev]"

dev:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest

lint:
	ruff check backend scripts

format:
	black backend scripts
	ruff check --fix backend scripts

ingest-sample:
	python scripts/ingest_sample.py --kb-name "Demo Medical KB"

ingest-competition:
	python scripts/ingest_mineru_outputs.py --input-dir CompetitionMinerU --kb-name "Competition Medical Literature KB"

rebuild-index:
	python scripts/rebuild_index.py --kb-id 1

query:
	python scripts/query.py --kb-id 1 --query "What was the primary outcome?"

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__
