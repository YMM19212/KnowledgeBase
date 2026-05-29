from fastapi.testclient import TestClient

from backend.app.api.deps import db_session as db_session_dep
from backend.app.main import app
from backend.app.services.knowledge_base_service import KnowledgeBaseService


def test_get_mineru_settings_includes_examples(db_session):
    app.dependency_overrides[db_session_dep] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.get("/api/v1/settings/mineru")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_upload_endpoint"].endswith("/documents/ingest")
    assert any(item["source"] == "local-cli" for item in payload["examples"])
    assert any(item["source"] == "remote-ssh" for item in payload["examples"])


def test_unified_ingest_endpoint_supports_mock_source(db_session):
    kb = KnowledgeBaseService(db_session).create("MinerU Pipeline KB")

    app.dependency_overrides[db_session_dep] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/knowledge-bases/{kb.id}/documents/ingest",
            data={"source_override": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["knowledge_base_id"] == kb.id
    assert payload["pipeline"]["source"] == "mock"
    assert payload["pipeline"]["parser"] == "mock"


def test_remote_mineru_key_path_directory_like_value_is_cleared(db_session):
    app.dependency_overrides[db_session_dep] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.put(
            "/api/v1/settings/mineru-remote",
            json={
                "mineru_remote_host": "172.31.22.13",
                "mineru_remote_user": "root",
                "mineru_remote_password": "secret",
                "mineru_remote_key_path": ".",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["mineru_remote_key_path"] is None
    assert payload["mineru_remote_password_configured"] is True
