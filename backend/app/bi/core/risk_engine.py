import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bi.contracts.types import RiskAlertData, SeverityLevel
from app.models.document import Document
from app.models.task import Task
from app.models.workflow import WorkflowApproval, WorkflowExecution


class RiskDetectionEngine:
    """Detects operational, workflow, timeline, and document risks across the enterprise."""

    async def detect_risks(self, db: AsyncSession, company_id: uuid.UUID) -> List[RiskAlertData]:
        """Scans database and operational records to identify risks."""
        risks: List[RiskAlertData] = []
        now = datetime.now(timezone.utc)

        # 1. Check for severe overdue tasks (> 3 days overdue)
        three_days_ago = now - timedelta(days=3)
        severe_overdue_tasks = await db.scalar(
            select(func.count()).select_from(Task).where(
                Task.company_id == company_id,
                Task.status.in_(["todo", "in_progress"]),
                Task.due_date < three_days_ago,
                Task.deleted_at.is_(None),
            )
        ) or 0

        if severe_overdue_tasks > 0:
            risks.append(
                RiskAlertData(
                    category="operations",
                    risk_level=SeverityLevel.CRITICAL.value if severe_overdue_tasks >= 5 else SeverityLevel.WARNING.value,
                    title=f"{severe_overdue_tasks} ta vazifa 3 kundan ortiq muddatga kechikkan",
                    description="Belgilangan muddatidan 3 kundan ko'proq o'tib ketgan ammo yakunlanmagan vazifalar mavjud.",
                    impact="Loyiha muddatlarining buzilishi va mijozlar oldidagi majburiyatlarning kechikishi.",
                    mitigation_step="Mas'ul xodimlarga zudlik bilan ustuvorlik berish va yuklamani qayta ko'rib chiqish.",
                    source_entity="Task",
                )
            )

        # 2. Check for pending workflow approvals that are waiting
        pending_approvals = await db.scalar(
            select(func.count()).select_from(WorkflowApproval).where(
                WorkflowApproval.company_id == company_id,
                WorkflowApproval.status == "pending",
            )
        ) or 0

        if pending_approvals > 0:
            risks.append(
                RiskAlertData(
                    category="workflow",
                    risk_level=SeverityLevel.WARNING.value,
                    title=f"{pending_approvals} ta jarayon tasdiqlashni kutmoqda (Pending Approval)",
                    description="Avtomatlashtirilgan ish oqimlari inson tasdig'i (Approval) kutib to'xtab turibdi.",
                    impact="Ish jarayonlarining to'xtab qolishi va qaror qabul qilishning sekinlashishi.",
                    mitigation_step="Tasdiqlovchi mas'ul shaxslarga Telegram/In-App eslatma yuborish.",
                    source_entity="WorkflowApproval",
                )
            )

        # 3. Check for failed workflow executions in last 24 hours
        yesterday = now - timedelta(days=1)
        failed_workflows = await db.scalar(
            select(func.count()).select_from(WorkflowExecution).where(
                WorkflowExecution.company_id == company_id,
                WorkflowExecution.status == "failed",
                WorkflowExecution.created_at >= yesterday,
            )
        ) or 0

        if failed_workflows > 0:
            risks.append(
                RiskAlertData(
                    category="workflow",
                    risk_level=SeverityLevel.WARNING.value,
                    title=f"So'nggi 24 soatda {failed_workflows} ta ish oqimi xatolik bilan yakunlandi",
                    description="Avtomatlashtirilgan jarayonlarda bajarilish xatoliklari qayd etildi.",
                    impact="Muntazam operatsion hisobotlar va vazifalar uzatilishida uzilish xavfi.",
                    mitigation_step="Workflow loglarini tekshirib, xato bergan qadamlarni tuzatish.",
                    source_entity="WorkflowExecution",
                )
            )

        # 4. Check for unindexed documents
        unindexed_docs = await db.scalar(
            select(func.count()).select_from(Document).where(
                Document.company_id == company_id,
                Document.is_indexed.is_(False),
                Document.deleted_at.is_(None),
            )
        ) or 0

        if unindexed_docs > 0:
            risks.append(
                RiskAlertData(
                    category="documents",
                    risk_level=SeverityLevel.INFO.value,
                    title=f"{unindexed_docs} ta hujjat hali indekslanmagan (Unindexed Documents)",
                    description="Yuklangan hujjatlar RAG yoki bilimlar grafigiga kiritilishi kutilmoqda.",
                    impact="AI agentlar eng so'nggi hujjatlardagi ma'lumotlarni qidiruvda topa olmasligi mumkin.",
                    mitigation_step="Hujjatlarni qayta ishlash navbatini (Document Worker) ishga tushirish.",
                    source_entity="Document",
                )
            )

        return risks


risk_engine = RiskDetectionEngine()
