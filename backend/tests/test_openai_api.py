from fastapi.testclient import TestClient

from backend.app.api.deps import db_session as db_session_dep
from backend.app.main import app
from backend.app.rag.embeddings import HashEmbeddingService
from backend.app.services.indexing_service import IndexingService
from backend.app.services.knowledge_base_service import KnowledgeBaseService
from backend.app.services.settings_service import EMBEDDING_BACKEND_KEY, AppSettingsService


def test_openai_compatible_chat_completion(db_session):
    kb = KnowledgeBaseService(db_session).create("Benchmark KB")
    AppSettingsService(db_session).set(EMBEDDING_BACKEND_KEY, "hash")
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_pdf(kb.id)

    app.dependency_overrides[db_session_dep] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "knowledgebase-agent-v1",
                "messages": [
                    {"role": "user", "content": "What was the primary outcome at 24 weeks?"}
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["model"] == "knowledgebase-agent-v1"
    assert payload["choices"][0]["message"]["content"]
    assert "citations" in payload


def test_openai_models_endpoint():
    client = TestClient(app)
    response = client.get("/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert payload["data"][0]["id"] == "knowledgebase-agent-v1"
