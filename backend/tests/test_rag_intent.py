from backend.app.rag.service import RAGService


def test_rerank_prefers_exact_table_reference(db_session):
    service = RAGService(db_session)
    reranked = service._rerank(
        "请提取 Table 1 的表格数据",
        [
            {
                "chunk_id": "c-text",
                "document_id": "doc",
                "document_title": "Trial paper",
                "source_text": "Primary outcome improved.",
                "score": 0.60,
                "section_path": "Results",
                "page_start": 2,
                "page_end": 2,
                "content_type": "text",
                "citation_text": "Results (p.2)",
                "metadata": {"evidence_type": "text_evidence"},
            },
            {
                "chunk_id": "c-table",
                "document_id": "doc",
                "document_title": "Trial paper",
                "source_text": "<table><tr><td>Arm A</td></tr></table>",
                "score": 0.45,
                "section_path": "Results",
                "page_start": 3,
                "page_end": 3,
                "content_type": "table",
                "citation_text": "Results (p.3, T1)",
                "metadata": {"evidence_type": "table_evidence", "table_id": "T1"},
            },
        ],
    )

    assert reranked[0]["chunk_id"] == "c-table"


def test_rerank_prefers_question_and_page_hints(db_session):
    service = RAGService(db_session)
    reranked = service._rerank(
        "请回答第6页的问题八",
        [
            {
                "chunk_id": "c-other",
                "document_id": "doc",
                "document_title": "Consensus",
                "source_text": "General background paragraph.",
                "score": 0.62,
                "section_path": "Introduction",
                "page_start": 1,
                "page_end": 1,
                "content_type": "text",
                "citation_text": "Introduction (p.1)",
                "metadata": {"evidence_type": "text_evidence"},
            },
            {
                "chunk_id": "c-question",
                "document_id": "doc",
                "document_title": "Consensus",
                "source_text": "问题八相关内容。",
                "score": 0.41,
                "section_path": "问题八、超声检查评估 准确性如何? 存在哪些局限性?",
                "page_start": 6,
                "page_end": 6,
                "content_type": "text",
                "citation_text": "问题八 (p.6)",
                "metadata": {"evidence_type": "clinical_question_answer"},
            },
        ],
    )

    assert reranked[0]["chunk_id"] == "c-question"
