"""Document Ingestion API -- Wave 5, Epic W5-0
(`TECHNICAL-DESIGN-W5-0-DOCUMENT-INGESTION.md`).

Exclusively Knowledge Platform (Founder Decision — Technical Design W5-0,
ponto 1): this module never imports `Evidence`, `AdvisorFramework`, or
anything from `src.agents` -- the Document Advisor (W5-1) is a separate,
not-yet-authorized Epic.

RBAC + organization scope, same seam every other Enterprise Domain route
module uses: `knowledge.write` for upload/reindex, `knowledge.read` for
status/listing. `organization_id`/`user_id` always come from
`RequestContext` (`get_request_context`), never from the request body.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.api.authorization import require_permission
from src.api.dependencies import build_repository
from src.api.identity_context import get_request_context
from src.api.rate_limiter import enforce_rate_limit
from src.api.routes.intelligence import build_knowledge_repository
from src.api.security import verify_api_key
from src.database.repository import AnalysisRepository
from src.services.identity.models import RequestContext
from src.services.knowledge_platform.document_ingestion_service import (
    DocumentIndexingError,
    DocumentIngestionService,
)
from src.services.knowledge_platform.knowledge_repository import KnowledgeRepository
from src.services.knowledge_platform.types import IngestedDocument

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])


def build_document_ingestion_service(
    repository: AnalysisRepository = Depends(build_repository),
    knowledge_repository: KnowledgeRepository = Depends(build_knowledge_repository),
) -> DocumentIngestionService:
    return DocumentIngestionService(knowledge_repository, repository)


class DocumentResponse(BaseModel):
    document_id: int
    source_name: str
    project_id: int | None
    version_id: int
    chunk_count: int
    status: str
    created_at: datetime


class DocumentVersionResponse(BaseModel):
    version_id: int
    chunk_count: int
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    versions: list[DocumentVersionResponse]


def _to_response(document: IngestedDocument, status: str) -> DocumentResponse:
    return DocumentResponse(
        document_id=document.id,
        source_name=document.source_name,
        project_id=document.project_id,
        version_id=document.version_id,
        chunk_count=document.chunk_count,
        status=status,
        created_at=document.created_at,
    )


def _indexing_error_detail(exc: DocumentIndexingError) -> dict:
    return {
        "document_id": exc.document_id,
        "version_id": exc.version_id,
        "status": "failed",
        "detail": "Indexação falhou; documento foi criado e pode ser reindexado via /reindex",
    }


@router.post("/documents", response_model=DocumentResponse, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    source_name: str | None = Form(None),
    project_id: int | None = Form(None),
    context: RequestContext = Depends(get_request_context),
    service: DocumentIngestionService = Depends(build_document_ingestion_service),
    _permission: None = Depends(require_permission("knowledge.write")),
) -> DocumentResponse:
    raw_bytes = file.file.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=422, detail="File must be UTF-8 encoded text/markdown"
        ) from exc
    if not text.strip():
        raise HTTPException(status_code=422, detail="File is empty")

    name = source_name or file.filename or "documento"
    try:
        document = service.upload(
            context.organization.organization_id,
            context.user.user_id,
            name,
            text,
            correlation_id=context.request_id,
            project_id=project_id,
        )
    except DocumentIndexingError as exc:
        raise HTTPException(status_code=502, detail=_indexing_error_detail(exc)) from exc

    status = service.get_status(context.organization.organization_id, document.id)
    return _to_response(document, status)


@router.post("/documents/{document_id}/reindex", response_model=DocumentResponse)
def reindex_document(
    document_id: int,
    context: RequestContext = Depends(get_request_context),
    service: DocumentIngestionService = Depends(build_document_ingestion_service),
    _permission: None = Depends(require_permission("knowledge.write")),
) -> DocumentResponse:
    existing = service.get_document(context.organization.organization_id, document_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        document = service.reindex(
            context.organization.organization_id,
            context.user.user_id,
            document_id,
            correlation_id=context.request_id,
        )
    except DocumentIndexingError as exc:
        raise HTTPException(status_code=502, detail=_indexing_error_detail(exc)) from exc

    status = service.get_status(context.organization.organization_id, document_id)
    return _to_response(document, status)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    project_id: int | None = None,
    context: RequestContext = Depends(get_request_context),
    service: DocumentIngestionService = Depends(build_document_ingestion_service),
    _permission: None = Depends(require_permission("knowledge.read")),
) -> list[DocumentResponse]:
    organization_id = context.organization.organization_id
    documents = service.list_documents(organization_id, project_id)
    return [
        _to_response(document, service.get_status(organization_id, document.id))
        for document in documents
    ]


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: int,
    context: RequestContext = Depends(get_request_context),
    service: DocumentIngestionService = Depends(build_document_ingestion_service),
    _permission: None = Depends(require_permission("knowledge.read")),
) -> DocumentDetailResponse:
    organization_id = context.organization.organization_id
    document = service.get_document(organization_id, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    status = service.get_status(organization_id, document_id)
    versions = service.list_versions(organization_id, document_id)
    base = _to_response(document, status)
    return DocumentDetailResponse(
        **base.model_dump(),
        versions=[
            DocumentVersionResponse(
                version_id=v.id, chunk_count=v.chunk_count, created_at=v.created_at
            )
            for v in versions
        ],
    )
