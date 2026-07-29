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
from app.services.document_service import DocumentService
from app.storage.file_handler import FileHandler

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
