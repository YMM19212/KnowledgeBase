from backend.app.rag.embeddings import HashEmbeddingService
from backend.app.rag.service import RAGService
from backend.app.services.indexing_service import IndexingService
from backend.app.services.knowledge_base_service import KnowledgeBaseService


def test_query_returns_citations(db_session):
    embeddings = HashEmbeddingService()
    kb = KnowledgeBaseService(db_session).create("Query Test KB")
    IndexingService(db_session, embeddings=embeddings).ingest_pdf(kb.id)

    result = RAGService(db_session, embeddings=embeddings).query(
        kb.id,
        "What was the primary outcome at 24 weeks?",
        top_k=3,
    )

    assert result["citations"]
    assert "answer" in result
    assert result["citations"][0]["document_id"] == "demo-trial-001"
