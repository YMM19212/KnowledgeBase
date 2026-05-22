from backend.app.rag.embeddings import HashEmbeddingService
from backend.app.rag.query_guard import QueryGuard
from backend.app.rag.service import RAGService
from backend.app.services.indexing_service import IndexingService
from backend.app.services.knowledge_base_service import KnowledgeBaseService


class FakeClassifierLLM:
    configured = True

    def __init__(self, response: str) -> None:
        self.response = response

    def chat(self, messages, temperature=0.1, max_tokens=None):  # noqa: ANN001, ANN201
        return self.response


def test_query_guard_rejects_greeting(db_session):
    kb = KnowledgeBaseService(db_session).create("Guard KB")
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_pdf(kb.id)

    decision = QueryGuard(db_session).evaluate(kb.id, "你好")

    assert decision.action == "reject"
    assert decision.reason == "greeting"


def test_query_guard_allows_broad_medical_scope_query(db_session):
    kb = KnowledgeBaseService(db_session).create("Guard Scope KB")
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_pdf(kb.id)

    decision = QueryGuard(db_session).evaluate(kb.id, "主要结局是什么")

    assert decision.action in {"defer", "retrieve"}


def test_query_guard_llm_marks_needs_hint(db_session):
    kb = KnowledgeBaseService(db_session).create("Guard LLM KB")
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_pdf(kb.id)
    llm = FakeClassifierLLM('{"label":"NEEDS_DOCUMENT_HINT","reason":"broad_without_anchor"}')

    decision = QueryGuard(db_session, llm=llm).evaluate(
        kb.id, "What was the primary outcome at 24 weeks?"
    )

    assert decision.action == "needs_hint"
    assert decision.reason == "broad_without_anchor"


def test_rag_query_returns_guard_message(db_session):
    kb = KnowledgeBaseService(db_session).create("Guard Query KB")
    IndexingService(db_session, embeddings=HashEmbeddingService()).ingest_pdf(kb.id)

    result = RAGService(db_session, embeddings=HashEmbeddingService()).query(kb.id, "你好", top_k=3)

    assert result["answer_mode"] == "guard-reject"
    assert not result["citations"]
    assert "知识库证据" in result["answer"]
