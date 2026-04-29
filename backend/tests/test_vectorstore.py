from backend.app.vectorstores.base import VectorDocument
from backend.app.vectorstores.sqlite import SQLiteVectorStore


def test_sqlite_vectorstore_similarity_search(db_session):
    store = SQLiteVectorStore(db_session)
    store.upsert(
        [
            VectorDocument(
                knowledge_base_id=1,
                document_id="doc",
                chunk_id="c1",
                content="primary outcome improved",
                embedding=[1.0, 0.0],
                metadata={"section_path": "Results > Primary outcome"},
            ),
            VectorDocument(
                knowledge_base_id=1,
                document_id="doc",
                chunk_id="c2",
                content="adverse events",
                embedding=[0.0, 1.0],
                metadata={"section_path": "Results > Adverse events"},
            ),
        ]
    )

    results = store.similarity_search(1, [1.0, 0.0], top_k=1)

    assert results[0].chunk_id == "c1"
    assert results[0].score > 0.9
