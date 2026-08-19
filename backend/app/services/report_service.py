import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportCreate, ReportGenerateRequest
from app.services.bi_service import BusinessIntelligenceService
from app.utils.exceptions import NotFoundException, ValidationException


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bi_service = BusinessIntelligenceService(db)

    async def list_reports(self, company_id: uuid.UUID, limit: int = 50) -> List[Report]:
        res = await self.db.scalars(
            select(Report)
            .where(Report.company_id == company_id, Report.deleted_at.is_(None))
            .order_by(desc(Report.created_at))
            .limit(limit)
        )
        return list(res.all())

    async def get_report_by_id(self, company_id: uuid.UUID, report_id: uuid.UUID) -> Report:
        report = await self.db.get(Report, report_id)
        if not report or report.company_id != company_id or report.deleted_at is not None:
            raise NotFoundException("Hisobot topilmadi")
        return report

    async def create_report(
        self, company_id: uuid.UUID, user_id: uuid.UUID, payload: ReportCreate
    ) -> Report:
        report = Report(
            company_id=company_id,
            created_by=user_id,
            title=payload.title,
            report_type=payload.report_type,
            content=payload.content,
            status="completed",
            format=payload.format,
            ai_provider=payload.ai_provider,
            ai_model=payload.ai_model,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def generate_report(
        self, company_id: uuid.UUID, user_id: uuid.UUID, payload: ReportGenerateRequest
    ) -> Report:
        return await self.bi_service.generate_bi_report(
            company_id=company_id,
            user_id=user_id,
            title=payload.title,
            report_type=payload.report_type,
            format=payload.format,
        )
