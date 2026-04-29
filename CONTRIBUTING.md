# Contributing

Thanks for contributing to MinerU Medical RAG.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
make install
make test
```

Use focused pull requests. Keep parser adapters, chunking logic, vector stores, and API schemas modular so downstream teams can replace components without broad rewrites.

