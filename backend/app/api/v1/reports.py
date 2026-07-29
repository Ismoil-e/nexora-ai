from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.report import ReportCreate, ReportGenerateRequest, ReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse)
async def create_report(body: ReportCreate, db: AsyncSession = Depends(get_db)):
    pass


@router.post("/generate")
async def generate_report(body: ReportGenerateRequest, db: AsyncSession = Depends(get_db)):
    pass


@router.get("")
async def list_reports(db: AsyncSession = Depends(get_db)):
    pass


@router.get("/{report_id}")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    pass
