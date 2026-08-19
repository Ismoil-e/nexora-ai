import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_db
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentUploadResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.schemas.document_intelligence import (
    ChunkSourceResponse,
    DocumentStatsResponse,
    EntityResponse,
    IntelligenceResponse,
    IntelligenceSearchRequest,
    IntelligenceSearchResponse,
    KnowledgeGraphResponse,
    ProcessingJobResponse,
    ReindexResponse,
    RelationshipResponse,
    VersionResponse,
)
from app.services.document_intelligence_service import DocumentIntelligenceService
from app.services.document_service import DocumentService
from app.storage.file_handler import FileHandler
from app.utils.exceptions import NotFoundException
from app.workers.document_worker import enqueue_document_processing

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_handler = FileHandler()
    content = await file.read()

    file_handler.validate_file(file.filename, len(content))

    service = DocumentService(db)
    return await service.upload_document(
        company_id=company_id,
        user_id=current_user.id,
        file_content=content,
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
    )


@router.get("")
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.get_documents(company_id, page, page_size)


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    result = await service.delete_document(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Hujjat topilmadi")
    return {"message": "Hujjat o'chirildi"}


@router.post("/rag", response_model=RAGQueryResponse)
async def query_rag(
    body: RAGQueryRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.search_rag(
        company_id=company_id,
        query=body.query,
        document_ids=body.document_ids,
        top_k=body.top_k,
    )


# ---- Document Intelligence endpoints ----------------------------------------


@router.get("/stats", response_model=DocumentStatsResponse)
async def document_stats(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.get_stats(company_id)


@router.post("/intelligence/search", response_model=IntelligenceSearchResponse)
async def intelligence_search(
    body: IntelligenceSearchRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.search(
        company_id=company_id,
        query=body.query,
        top_k=body.top_k,
        document_type=body.document_type,
        department_id=body.department_id,
        project_id=body.project_id,
        source_system=body.source_system,
        date_from=body.date_from,
        date_to=body.date_to,
    )


@router.get("/knowledge-graph", response_model=KnowledgeGraphResponse)
async def knowledge_graph(
    node_limit: int = Query(200, ge=1, le=1000),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.get_knowledge_graph(company_id, node_limit=node_limit)


@router.get("/{document_id}/intelligence", response_model=IntelligenceResponse)
async def document_intelligence(
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    try:
        return await service.get_intelligence(company_id, document_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=404, detail=exc.detail)


@router.get("/{document_id}/chunks", response_model=list[ChunkSourceResponse])
async def document_chunks(
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.get_chunks(company_id, document_id)


@router.get("/{document_id}/entities", response_model=list[EntityResponse])
async def document_entities(
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.get_entities(company_id, document_id)


@router.get("/{document_id}/relationships", response_model=list[RelationshipResponse])
async def document_relationships(
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.get_relationships(company_id, document_id)


@router.get("/{document_id}/versions", response_model=list[VersionResponse])
async def document_versions(
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.get_versions(company_id, document_id)


@router.get("/{document_id}/jobs", response_model=list[ProcessingJobResponse])
async def document_jobs(
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.get_jobs(company_id, document_id)


@router.post("/{document_id}/reprocess")
async def document_reprocess(
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    await service.assert_document_exists(company_id, document_id)
    mode = enqueue_document_processing(str(document_id))
    return {
        "document_id": str(document_id),
        "status": mode,
        "message": "Qayta ishlash navbatga qo'shildi",
    }


@router.post("/{document_id}/reindex", response_model=ReindexResponse)
async def document_reindex(
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentIntelligenceService(db)
    return await service.reindex_document(company_id, document_id)
