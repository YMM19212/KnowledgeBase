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
    assert result["evidence_units"]
    assert result["evidence_sufficiency"] in {"sufficient", "partial"}
    assert "answer" in result
    assert result["citations"][0]["document_id"] == "demo-trial-001"


def test_query_prefers_primary_endpoint_evidence_for_broad_trial_question(db_session):
    embeddings = HashEmbeddingService()
    kb = KnowledgeBaseService(db_session).create("Broad Trial Query KB")
    IndexingService(db_session, embeddings=embeddings).ingest_pdf(kb.id)

    result = RAGService(db_session, embeddings=embeddings).query(
        kb.id,
        "主要结局是什么",
        top_k=3,
    )

    assert result["answer_mode"] != "guard-reject"
    assert result["citations"]
    assert result["citations"][0]["evidence_role"] in {
        "primary_endpoint_result",
        "primary_endpoint_definition",
    }


def test_query_prefers_abstract_results_for_abstract_request(db_session):
    embeddings = HashEmbeddingService()
    kb = KnowledgeBaseService(db_session).create("Abstract Query KB")
    IndexingService(db_session, embeddings=embeddings).ingest_pdf(kb.id)

    result = RAGService(db_session, embeddings=embeddings).query(
        kb.id,
        "请提取摘要中的 Results 部分内容",
        top_k=3,
    )

    assert result["citations"]
    assert result["citations"][0]["evidence_role"] == "abstract_result"
