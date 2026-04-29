import json
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import db_session
from backend.app.core.config import get_settings
from backend.app.models.db import (
    ChunkRecord,
    DocumentRecord,
    EvidenceUnit,
    KnowledgeBase,
    QueryLog,
    VectorEntry,
)
from backend.app.parsers.local_mineru import LocalMinerUParserAdapter
from backend.app.parsers.mock import MockParser
from backend.app.rag.service import RAGService
from backend.app.schemas.api import (
    ChunkRead,
    DocumentRead,
    EmbeddingSettingsRead,
    EmbeddingSettingsUpdate,
    EvidenceUnitRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    LLMSettingsRead,
    LLMSettingsUpdate,
    LocalMinerUIngestResponse,
    LocalMinerURunRead,
    LocalMinerUStatus,
    MockParseRequest,
    QueryRequest,
    QueryResponse,
)
from backend.app.services.evidence_service import EvidenceService, evidence_unit_to_dict
from backend.app.services.indexing_service import IndexingService
from backend.app.services.knowledge_base_service import (
    DocumentService,
    KnowledgeBaseService,
    document_to_dict,
)
from backend.app.services.settings_service import (
    EMBEDDING_BACKEND_KEY,
    EMBEDDING_MODEL_KEY,
    JINA_API_KEY_KEY,
    LLM_API_KEY_KEY,
    LLM_BASE_URL_KEY,
    LLM_MODEL_KEY,
    LLM_PROVIDER_KEY,
    AppSettingsService,
)

router = APIRouter()


@router.post("/knowledge-bases", response_model=KnowledgeBaseRead)
def create_knowledge_base(payload: KnowledgeBaseCreate, db: Session = Depends(db_session)):
    kb = KnowledgeBaseService(db).create(payload.name, payload.description)
    return KnowledgeBaseRead(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=0,
        chunk_count=0,
        created_at=kb.created_at.isoformat() if kb.created_at else None,
    )


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseRead])
def list_knowledge_bases(db: Session = Depends(db_session)):
    return [
        KnowledgeBaseRead(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            document_count=doc_count,
            chunk_count=chunk_count,
            created_at=kb.created_at.isoformat() if kb.created_at else None,
        )
        for kb, doc_count, chunk_count in KnowledgeBaseService(db).list()
    ]


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseRead)
def get_knowledge_base(kb_id: int, db: Session = Depends(db_session)):
    kb = KnowledgeBaseService(db).get(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    document_count = db.scalar(
        select(func.count(DocumentRecord.id)).where(DocumentRecord.knowledge_base_id == kb_id)
    )
    chunk_count = db.scalar(
        select(func.count(ChunkRecord.id)).where(ChunkRecord.knowledge_base_id == kb_id)
    )
    return KnowledgeBaseRead(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=document_count or 0,
        chunk_count=chunk_count or 0,
        created_at=kb.created_at.isoformat() if kb.created_at else None,
    )


@router.delete("/knowledge-bases/{kb_id}")
def delete_knowledge_base(kb_id: int, db: Session = Depends(db_session)):
    if not KnowledgeBaseService(db).delete(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return {"deleted": True}


@router.get("/mineru/local/status", response_model=LocalMinerUStatus)
def local_mineru_status():
    settings = get_settings()
    try:
        completed = subprocess.run(
            [settings.mineru_cli_command, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:
        return LocalMinerUStatus(
            available=False,
            command=settings.mineru_cli_command,
            error=str(exc),
        )
    output = (completed.stdout or completed.stderr).strip()
    return LocalMinerUStatus(
        available=completed.returncode == 0,
        command=settings.mineru_cli_command,
        version=output or None,
        error=None if completed.returncode == 0 else output,
    )


@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentRead)
async def upload_document(
    kb_id: int,
    file: UploadFile | None = File(default=None),
    db: Session = Depends(db_session),
):
    if not KnowledgeBaseService(db).get(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    saved_path: Path | None = None
    if file:
        settings = get_settings()
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        saved_path = settings.storage_dir / file.filename
        saved_path.write_bytes(await file.read())
    document = IndexingService(db).ingest_pdf(kb_id, saved_path)
    return DocumentRead(**document_to_dict(document))


@router.post(
    "/knowledge-bases/{kb_id}/documents/mineru-local",
    response_model=LocalMinerUIngestResponse,
)
async def upload_document_with_local_mineru(
    kb_id: int,
    file: UploadFile = File(...),
    method: str = Form(default="auto"),
    lang: str = Form(default="ch"),
    formula: bool = Form(default=True),
    table: bool = Form(default=True),
    db: Session = Depends(db_session),
):
    if not KnowledgeBaseService(db).get(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if method not in {"auto", "txt", "ocr"}:
        raise HTTPException(status_code=400, detail="Unsupported MinerU method")
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.mineru_local_output_dir.mkdir(parents=True, exist_ok=True)
    saved_path = settings.storage_dir / file.filename
    saved_path.write_bytes(await file.read())
    output_dir = settings.mineru_local_output_dir / saved_path.stem
    parser = LocalMinerUParserAdapter(
        output_dir=output_dir,
        method=method,
        lang=lang,
        formula=formula,
        table=table,
    )
    try:
        document = IndexingService(db, parser=parser).ingest_pdf(kb_id, saved_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if parser.last_run is None:
        raise HTTPException(status_code=500, detail="MinerU did not produce run metadata")
    return LocalMinerUIngestResponse(
        document=DocumentRead(**document_to_dict(document)),
        mineru=LocalMinerURunRead(**parser.last_run.__dict__),
    )


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentRead])
def list_documents(kb_id: int, db: Session = Depends(db_session)):
    if not KnowledgeBaseService(db).get(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return [DocumentRead(**document_to_dict(doc)) for doc in DocumentService(db).list_by_kb(kb_id)]


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(db_session)):
    document = DocumentService(db).get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentRead(**document_to_dict(document))


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, db: Session = Depends(db_session)):
    if not DocumentService(db).delete(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkRead])
def list_chunks(document_id: str, db: Session = Depends(db_session)):
    if not DocumentService(db).get(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = DocumentService(db).list_chunks(document_id)
    return [
        ChunkRead(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            content=chunk.content,
            section_path=chunk.section_path,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            content_type=chunk.content_type,
            metadata=json.loads(chunk.metadata_json or "{}"),
        )
        for chunk in chunks
    ]


@router.get("/documents/{document_id}/evidence-units", response_model=list[EvidenceUnitRead])
def list_document_evidence_units(document_id: str, db: Session = Depends(db_session)):
    if not DocumentService(db).get(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return [
        EvidenceUnitRead(**evidence_unit_to_dict(unit))
        for unit in EvidenceService(db).list_by_document(document_id)
    ]


@router.get(
    "/knowledge-bases/{kb_id}/evidence-units", response_model=list[EvidenceUnitRead]
)
def list_kb_evidence_units(kb_id: int, db: Session = Depends(db_session)):
    if not KnowledgeBaseService(db).get(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return [
        EvidenceUnitRead(**evidence_unit_to_dict(unit))
        for unit in EvidenceService(db).list_by_knowledge_base(kb_id)
    ]


@router.post("/knowledge-bases/{kb_id}/evidence/rebuild")
def rebuild_evidence_units(kb_id: int, db: Session = Depends(db_session)):
    if not KnowledgeBaseService(db).get(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    count = EvidenceService(db).rebuild_knowledge_base(kb_id)
    return {"evidence_units": count}


@router.post("/knowledge-bases/{kb_id}/index/rebuild")
def rebuild_index(kb_id: int, db: Session = Depends(db_session)):
    if not KnowledgeBaseService(db).get(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    count = IndexingService(db).rebuild_index(kb_id)
    return {"indexed_chunks": count}


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, db: Session = Depends(db_session)):
    if not KnowledgeBaseService(db).get(payload.knowledge_base_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    result = RAGService(db).query(
        knowledge_base_id=payload.knowledge_base_id,
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
    )
    db.add(
        QueryLog(
            knowledge_base_id=payload.knowledge_base_id,
            query=payload.query,
            top_k=payload.top_k,
            retrieved_count=len(result.get("retrieved_chunks", [])),
        )
    )
    db.commit()
    return result


@router.post("/parse/mock")
def parse_mock(payload: MockParseRequest, db: Session = Depends(db_session)):
    parsed = MockParser().parse_pdf()
    if payload.knowledge_base_id is not None:
        if not KnowledgeBaseService(db).get(payload.knowledge_base_id):
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        document = IndexingService(db).ingest_parsed_document(payload.knowledge_base_id, parsed)
        return {"document_id": document.id, "ingested": True}
    return parsed.model_dump()


@router.get("/stats")
def stats(db: Session = Depends(db_session)):
    recent_documents = db.scalars(
        select(DocumentRecord).order_by(DocumentRecord.created_at.desc()).limit(6)
    ).all()
    query_count = db.scalar(select(func.count(QueryLog.id))) or 0
    return {
        "knowledge_bases": db.scalar(select(func.count(KnowledgeBase.id))) or 0,
        "documents": db.scalar(select(func.count(DocumentRecord.id))) or 0,
        "chunks": db.scalar(select(func.count(ChunkRecord.id))) or 0,
        "evidence_units": db.scalar(select(func.count(EvidenceUnit.id))) or 0,
        "vectors_sqlite": db.scalar(select(func.count(VectorEntry.id))) or 0,
        "index_status": "ready",
        "query_count": query_count,
        "answer_count": query_count,
        "recent_documents": [document_to_dict(document) for document in recent_documents],
    }


@router.get("/config")
def public_config(db: Session = Depends(db_session)):
    settings = get_settings()
    app_settings = AppSettingsService(db).all_public_settings()
    return {
        "app_name": settings.app_name,
        "env": settings.env,
        "api_prefix": settings.api_prefix,
        "embedding_backend": app_settings["embedding_backend"],
        "embedding_model": app_settings["embedding_model"],
        "embedding_source": app_settings["embedding_source"],
        "jina_api_key_configured": app_settings["jina_api_key_configured"],
        "jina_api_key_masked": app_settings["jina_api_key_masked"],
        "vector_store": settings.vector_store,
        "mineru_api_url": settings.mineru_api_url,
        "mineru_cli_command": settings.mineru_cli_command,
        "mineru_local_output_dir": str(settings.mineru_local_output_dir),
        "parser_mode": "remote-mineru" if settings.mineru_api_url else "mock/local-mineru",
        "llm_provider": app_settings["llm_provider"],
        "llm_base_url": app_settings["llm_base_url"],
        "llm_model": app_settings["llm_model"],
        "llm_source": app_settings["llm_source"],
        "llm_api_key_configured": app_settings["llm_api_key_configured"],
        "llm_api_key_masked": app_settings["llm_api_key_masked"],
        "llm_configured": bool(
            app_settings["llm_api_key_configured"] and app_settings["llm_model"]
        ),
    }


@router.get("/settings/embedding", response_model=EmbeddingSettingsRead)
def get_embedding_settings(db: Session = Depends(db_session)):
    return EmbeddingSettingsRead(**AppSettingsService(db).all_public_settings())


@router.put("/settings/embedding", response_model=EmbeddingSettingsRead)
def update_embedding_settings(
    payload: EmbeddingSettingsUpdate,
    db: Session = Depends(db_session),
):
    service = AppSettingsService(db)
    if payload.embedding_backend is not None:
        backend = payload.embedding_backend.strip()
        supported_backends = {
            "hash",
            "jina",
            "auto",
            "sentence-transformers",
            "sentence_transformers",
        }
        if backend not in supported_backends:
            raise HTTPException(status_code=400, detail="Unsupported embedding backend")
        service.set(EMBEDDING_BACKEND_KEY, backend)
    if payload.embedding_model is not None:
        model = payload.embedding_model.strip()
        if model:
            service.set(EMBEDDING_MODEL_KEY, model)
    if payload.jina_api_key is not None:
        api_key = payload.jina_api_key.strip()
        if api_key and not api_key.startswith("***"):
            service.set(JINA_API_KEY_KEY, api_key)
    return EmbeddingSettingsRead(**service.all_public_settings())


@router.get("/settings/llm", response_model=LLMSettingsRead)
def get_llm_settings(db: Session = Depends(db_session)):
    return LLMSettingsRead(**AppSettingsService(db).all_public_settings())


@router.put("/settings/llm", response_model=LLMSettingsRead)
def update_llm_settings(payload: LLMSettingsUpdate, db: Session = Depends(db_session)):
    service = AppSettingsService(db)
    if payload.llm_provider is not None:
        provider = payload.llm_provider.strip().lower()
        if provider not in {"none", "moonshot", "kimi", "openai-compatible"}:
            raise HTTPException(status_code=400, detail="Unsupported LLM provider")
        service.set(LLM_PROVIDER_KEY, provider)
    if payload.llm_base_url is not None:
        base_url = payload.llm_base_url.strip()
        if base_url:
            service.set(LLM_BASE_URL_KEY, base_url)
    if payload.llm_model is not None:
        model = payload.llm_model.strip()
        if model:
            service.set(LLM_MODEL_KEY, model)
    if payload.llm_api_key is not None:
        api_key = payload.llm_api_key.strip()
        if api_key and not api_key.startswith("***"):
            service.set(LLM_API_KEY_KEY, api_key)
    return LLMSettingsRead(**service.all_public_settings())
