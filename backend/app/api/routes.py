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
from backend.app.parsers.mineru import MinerUParserAdapter
from backend.app.parsers.mock import MockParser
from backend.app.parsers.remote_mineru import RemoteMinerUParserAdapter
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
    MinerUPipelineIngestResponse,
    MinerUPipelineRunRead,
    MinerURemoteSettingsRead,
    MinerURemoteSettingsUpdate,
    MinerUSettingsRead,
    MinerUSettingsUpdate,
    MinerUSourceExample,
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
    MINERU_API_URL_KEY,
    MINERU_REMOTE_HOST_KEY,
    MINERU_REMOTE_KEY_PATH_KEY,
    MINERU_REMOTE_OUTPUT_DIR_KEY,
    MINERU_REMOTE_PASSWORD_KEY,
    MINERU_REMOTE_PORT_KEY,
    MINERU_REMOTE_USER_KEY,
    MINERU_REMOTE_WORK_DIR_KEY,
    MINERU_SOURCE_KEY,
    AppSettingsService,
)

router = APIRouter()

MINERU_SOURCE_OPTIONS = {"mock", "local-cli", "remote-ssh", "remote-api"}


def _mineru_examples() -> list[MinerUSourceExample]:
    return [
        MinerUSourceExample(
            source="local-cli",
            label="Local MinerU CLI",
            description=(
                "Run `mineru -p <input_path> -o <output_path> -b pipeline` "
                "on the same machine as the API service."
            ),
            example_config={
                "mineru_source": "local-cli",
                "mineru_cli_command": "mineru",
                "notes": [
                    "Suitable when MinerU is installed locally.",
                    (
                        "The upload endpoint will save the PDF locally, run "
                        "MinerU, then ingest parsed output into the knowledge base."
                    ),
                ],
            },
        ),
        MinerUSourceExample(
            source="remote-ssh",
            label="Remote MinerU Server (SSH)",
            description=(
                "Upload the PDF to a remote Linux server over SSH, run "
                "MinerU there, download artifacts, then ingest them."
            ),
            example_config={
                "mineru_source": "remote-ssh",
                "mineru_remote_host": "172.31.22.13",
                "mineru_remote_port": 22,
                "mineru_remote_user": "root",
                "mineru_remote_work_dir": "/tmp/medrag_mineru",
                "mineru_remote_output_dir": "./data/mineru_remote_outputs",
                "notes": [
                    "Use password or key-based SSH authentication.",
                    "Recommended when MinerU only exists on a GPU or Linux server.",
                ],
            },
        ),
        MinerUSourceExample(
            source="remote-api",
            label="Remote MinerU HTTP API",
            description=(
                "Call a remote MinerU-compatible HTTP service that accepts "
                "PDF upload and returns normalized artifacts."
            ),
            example_config={
                "mineru_source": "remote-api",
                "mineru_api_url": "https://mineru.example.com/api",
                "notes": [
                    (
                        "The upload endpoint will forward the PDF to the "
                        "remote MinerU API, then ingest the returned result."
                    ),
                    (
                        "This requires the remote API to expose `/parse` and "
                        "`/parse/{task_id}` style endpoints."
                    ),
                ],
            },
        ),
        MinerUSourceExample(
            source="mock",
            label="Mock Parser",
            description=(
                "Use bundled sample MinerU JSON for development and API smoke "
                "tests without running MinerU."
            ),
            example_config={
                "mineru_source": "mock",
                "notes": [
                    "Useful for local development and demo fallback.",
                    "The upload endpoint can skip the real MinerU step in this mode.",
                ],
            },
        ),
    ]


def _build_mineru_settings_read(service: AppSettingsService) -> MinerUSettingsRead:
    payload = service.all_public_settings()
    return MinerUSettingsRead(
        **payload,
        examples=_mineru_examples(),
        recommended_upload_endpoint="/api/v1/knowledge-bases/{kb_id}/documents/ingest",
    )


async def _save_uploaded_file(file: UploadFile) -> Path:
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    saved_path = settings.storage_dir / file.filename
    saved_path.write_bytes(await file.read())
    return saved_path


def _pipeline_run_for_api(
    source: str,
    parser_name: str,
    input_file: str | None,
    mineru_api_url: str | None,
) -> MinerUPipelineRunRead:
    return MinerUPipelineRunRead(
        source=source,
        parser=parser_name,
        status="completed",
        input_file=input_file,
        mineru_api_url=mineru_api_url,
    )


def _pipeline_run_for_local(source: str, input_file: str | None, run: LocalMinerURunRead):
    return MinerUPipelineRunRead(
        source=source,
        parser="local-cli",
        status="completed",
        input_file=input_file,
        command=run.command,
        output_dir=run.output_dir,
        artifacts=run.artifacts,
        stdout=run.stdout,
        stderr=run.stderr,
        duration_seconds=run.duration_seconds,
    )


def _pipeline_run_for_remote(
    source: str,
    input_file: str | None,
    remote_host: str | None,
    run: LocalMinerURunRead,
):
    return MinerUPipelineRunRead(
        source=source,
        parser="remote-ssh",
        status="completed",
        input_file=input_file,
        command=run.command,
        output_dir=run.output_dir,
        artifacts=run.artifacts,
        stdout=run.stdout,
        stderr=run.stderr,
        duration_seconds=run.duration_seconds,
        remote_host=remote_host,
    )


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


@router.get("/mineru/remote/status", response_model=LocalMinerUStatus)
def remote_mineru_status(db: Session = Depends(db_session)):
    remote_settings = AppSettingsService(db).effective_mineru_remote_settings()
    status = RemoteMinerUParserAdapter(remote_settings=remote_settings).check_status()
    return LocalMinerUStatus(
        available=status.available,
        command=f"ssh {status.user}@{status.host or '<not-configured>'} {status.command}",
        version=status.version,
        error=status.error,
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
    "/knowledge-bases/{kb_id}/documents/ingest",
    response_model=MinerUPipelineIngestResponse,
)
async def ingest_document_with_mineru_pipeline(
    kb_id: int,
    file: UploadFile | None = File(default=None),
    source_override: str | None = Form(default=None),
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

    app_settings = AppSettingsService(db)
    mineru_settings = app_settings.effective_mineru_settings()
    source = (source_override or mineru_settings.source).strip().lower()
    if source not in MINERU_SOURCE_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported MinerU source '{source}'.",
        )
    if source != "mock" and file is None:
        raise HTTPException(
            status_code=400,
            detail="A PDF file is required unless mineru_source is 'mock'.",
        )

    saved_path = await _save_uploaded_file(file) if file else None

    if source == "local-cli":
        settings = get_settings()
        settings.mineru_local_output_dir.mkdir(parents=True, exist_ok=True)
        output_dir = settings.mineru_local_output_dir / (saved_path.stem if saved_path else "input")
        parser = LocalMinerUParserAdapter(
            output_dir=output_dir,
            method=method,
            lang=lang,
            formula=formula,
            table=table,
        )
        document = IndexingService(db, parser=parser).ingest_pdf(kb_id, saved_path)
        if parser.last_run is None:
            raise HTTPException(status_code=500, detail="MinerU did not produce run metadata")
        pipeline = _pipeline_run_for_local(
            source,
            str(saved_path) if saved_path else None,
            LocalMinerURunRead(**parser.last_run.__dict__),
        )
    elif source == "remote-ssh":
        remote_settings = mineru_settings.remote
        remote_settings.output_dir.mkdir(parents=True, exist_ok=True)
        parser = RemoteMinerUParserAdapter(
            method=method,
            lang=lang,
            formula=formula,
            table=table,
            remote_settings=remote_settings,
        )
        document = IndexingService(db, parser=parser).ingest_pdf(kb_id, saved_path)
        if parser.last_run is None:
            raise HTTPException(
                status_code=500, detail="Remote MinerU did not produce run metadata"
            )
        pipeline = _pipeline_run_for_remote(
            source,
            str(saved_path) if saved_path else None,
            remote_settings.host,
            LocalMinerURunRead(**parser.last_run.__dict__),
        )
    elif source == "remote-api":
        parser = MinerUParserAdapter(mineru_api_url=mineru_settings.api_url)
        document = IndexingService(db, parser=parser).ingest_pdf(kb_id, saved_path)
        pipeline = _pipeline_run_for_api(
            source,
            "remote-api",
            str(saved_path) if saved_path else None,
            mineru_settings.api_url,
        )
    else:
        parser = MockParser()
        document = IndexingService(db, parser=parser).ingest_pdf(kb_id, saved_path)
        pipeline = _pipeline_run_for_api(
            source,
            "mock",
            str(saved_path) if saved_path else None,
            None,
        )

    return MinerUPipelineIngestResponse(
        document=DocumentRead(**document_to_dict(document)),
        pipeline=pipeline,
    )


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


@router.post(
    "/knowledge-bases/{kb_id}/documents/mineru-remote",
    response_model=LocalMinerUIngestResponse,
)
async def upload_document_with_remote_mineru(
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
    remote_settings = AppSettingsService(db).effective_mineru_remote_settings()
    remote_settings.output_dir.mkdir(parents=True, exist_ok=True)
    saved_path = settings.storage_dir / file.filename
    saved_path.write_bytes(await file.read())
    parser = RemoteMinerUParserAdapter(
        method=method,
        lang=lang,
        formula=formula,
        table=table,
        remote_settings=remote_settings,
    )
    try:
        document = IndexingService(db, parser=parser).ingest_pdf(kb_id, saved_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if parser.last_run is None:
        raise HTTPException(status_code=500, detail="Remote MinerU did not produce run metadata")
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
        "mineru_source": app_settings["mineru_source"],
        "mineru_source_origin": app_settings["mineru_source_origin"],
        "mineru_api_url": app_settings["mineru_api_url"],
        "mineru_cli_command": app_settings["mineru_cli_command"],
        "mineru_local_output_dir": app_settings["mineru_local_output_dir"],
        "mineru_remote_host": app_settings["mineru_remote_host"],
        "mineru_remote_port": app_settings["mineru_remote_port"],
        "mineru_remote_user": app_settings["mineru_remote_user"],
        "mineru_remote_key_path": app_settings["mineru_remote_key_path"],
        "mineru_remote_work_dir": app_settings["mineru_remote_work_dir"],
        "mineru_remote_output_dir": app_settings["mineru_remote_output_dir"],
        "mineru_remote_source": app_settings["mineru_remote_source"],
        "mineru_remote_password_configured": app_settings["mineru_remote_password_configured"],
        "mineru_remote_password_masked": app_settings["mineru_remote_password_masked"],
        "mineru_remote_configured": app_settings["mineru_remote_configured"],
        "parser_mode": (
            app_settings["mineru_source"]
        ),
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


@router.get("/settings/mineru", response_model=MinerUSettingsRead)
def get_mineru_settings(db: Session = Depends(db_session)):
    return _build_mineru_settings_read(AppSettingsService(db))


@router.put("/settings/mineru", response_model=MinerUSettingsRead)
def update_mineru_settings(payload: MinerUSettingsUpdate, db: Session = Depends(db_session)):
    service = AppSettingsService(db)
    if payload.mineru_source is not None:
        source = payload.mineru_source.strip().lower()
        if source not in MINERU_SOURCE_OPTIONS:
            raise HTTPException(status_code=400, detail="Unsupported MinerU source")
        service.set(MINERU_SOURCE_KEY, source)
    if payload.mineru_api_url is not None:
        service.set(MINERU_API_URL_KEY, payload.mineru_api_url.strip())
    if payload.mineru_remote_host is not None:
        service.set(MINERU_REMOTE_HOST_KEY, payload.mineru_remote_host.strip())
    if payload.mineru_remote_port is not None:
        service.set(MINERU_REMOTE_PORT_KEY, str(payload.mineru_remote_port))
    if payload.mineru_remote_user is not None:
        service.set(MINERU_REMOTE_USER_KEY, payload.mineru_remote_user.strip())
    if payload.mineru_remote_password is not None:
        password = payload.mineru_remote_password.strip()
        if password and not password.startswith("***"):
            service.set(MINERU_REMOTE_PASSWORD_KEY, password)
    if payload.mineru_remote_key_path is not None:
        service.set(MINERU_REMOTE_KEY_PATH_KEY, payload.mineru_remote_key_path.strip())
    if payload.mineru_remote_work_dir is not None:
        service.set(MINERU_REMOTE_WORK_DIR_KEY, payload.mineru_remote_work_dir.strip())
    if payload.mineru_remote_output_dir is not None:
        service.set(MINERU_REMOTE_OUTPUT_DIR_KEY, payload.mineru_remote_output_dir.strip())
    return _build_mineru_settings_read(service)


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


@router.get("/settings/mineru-remote", response_model=MinerURemoteSettingsRead)
def get_mineru_remote_settings(db: Session = Depends(db_session)):
    return MinerURemoteSettingsRead(**AppSettingsService(db).all_public_settings())


@router.put("/settings/mineru-remote", response_model=MinerURemoteSettingsRead)
def update_mineru_remote_settings(
    payload: MinerURemoteSettingsUpdate,
    db: Session = Depends(db_session),
):
    service = AppSettingsService(db)
    if payload.mineru_remote_host is not None:
        host = payload.mineru_remote_host.strip()
        if host:
            service.set(MINERU_REMOTE_HOST_KEY, host)
    if payload.mineru_remote_port is not None:
        service.set(MINERU_REMOTE_PORT_KEY, str(payload.mineru_remote_port))
    if payload.mineru_remote_user is not None:
        user = payload.mineru_remote_user.strip()
        if user:
            service.set(MINERU_REMOTE_USER_KEY, user)
    if payload.mineru_remote_password is not None:
        password = payload.mineru_remote_password.strip()
        if password and not password.startswith("***"):
            service.set(MINERU_REMOTE_PASSWORD_KEY, password)
    if payload.mineru_remote_key_path is not None:
        key_path = payload.mineru_remote_key_path.strip()
        service.set(MINERU_REMOTE_KEY_PATH_KEY, key_path)
    if payload.mineru_remote_work_dir is not None:
        work_dir = payload.mineru_remote_work_dir.strip().rstrip("/")
        if work_dir:
            service.set(MINERU_REMOTE_WORK_DIR_KEY, work_dir)
    if payload.mineru_remote_output_dir is not None:
        output_dir = payload.mineru_remote_output_dir.strip()
        if output_dir:
            service.set(MINERU_REMOTE_OUTPUT_DIR_KEY, output_dir)
    return MinerURemoteSettingsRead(**service.all_public_settings())
