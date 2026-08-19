import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user_id, get_db
from app.schemas.report import ReportCreate, ReportDetailResponse, ReportGenerateRequest, ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse)
async def create_report(
    body: ReportCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new report record."""
    svc = ReportService(db)
    return await svc.create_report(company_id, user_id, body)


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    body: ReportGenerateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generates an automated executive report using BI insights, KPIs, and metrics."""
    svc = ReportService(db)
    return await svc.generate_report(company_id, user_id, body)


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    limit: int = Query(50, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists generated reports for the tenant."""
    svc = ReportService(db)
    return await svc.list_reports(company_id, limit=limit)


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full content and metadata of a specific report."""
    svc = ReportService(db)
    return await svc.get_report_by_id(company_id, report_id)
