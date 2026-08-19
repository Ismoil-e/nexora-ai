import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bi.contracts.types import KPICalculationResult, KPICategory, KPIStatus
from app.models.chat import Chat, ChatMessage
from app.models.document import Document
from app.models.document_intelligence import DocumentProcessingJob
from app.models.task import Task
from app.models.user import User
from app.models.workflow import WorkflowExecution


class KPIEngine:
    """Calculates, evaluates, and logs key performance indicators across tenant operations."""

    DEFAULT_KPI_DEFINITIONS = [
        {
            "code": "TASK_COMPLETION_RATE",
            "name": "Vazifalar Bajarilish Ko'rsatkichi",
            "category": KPICategory.OPERATIONS.value,
            "description": "Barcha vazifalarning muvaffaqiyatli bajarilganlik foizi",
            "calculation_type": "query",
            "target_value": 90.0,
            "warning_threshold": 75.0,
            "critical_threshold": 60.0,
            "unit": "%",
        },
        {
            "code": "OVERDUE_TASKS_COUNT",
            "name": "Muddati O'tgan Vazifalar",
            "category": KPICategory.OPERATIONS.value,
            "description": "Muddati o'tib ketgan ammo yakunlanmagan topshiriqlar soni",
            "calculation_type": "query",
            "target_value": 0.0,
            "warning_threshold": 5.0,
            "critical_threshold": 10.0,
            "unit": "ta",
        },
        {
            "code": "PENDING_TASKS_COUNT",
            "name": "Jarayondagi Vazifalar",
            "category": KPICategory.OPERATIONS.value,
            "description": "Hozirda ijroda bo'lgan vazifalar umumiy soni",
            "calculation_type": "query",
            "target_value": 20.0,
            "warning_threshold": 50.0,
            "critical_threshold": 100.0,
            "unit": "ta",
        },
        {
            "code": "DOCUMENT_PROCESSING_VOLUME",
            "name": "Qayta Ishlangan Hujjatlar Hajmi",
            "category": KPICategory.DOCUMENTS.value,
            "description": "Tizimda muvaffaqiyatli indekslangan va qayta ishlangan hujjatlar soni",
            "calculation_type": "query",
            "target_value": 50.0,
            "warning_threshold": 10.0,
            "critical_threshold": 2.0,
            "unit": "ta",
        },
        {
            "code": "AI_USAGE_MESSAGES",
            "name": "AI Yordamchi Foydalanish Hajmi",
            "category": KPICategory.AI.value,
            "description": "Xodimlar tomonidan AI agentlar bilan almashilgan xabarlar soni",
            "calculation_type": "query",
            "target_value": 100.0,
            "warning_threshold": 20.0,
            "critical_threshold": 5.0,
            "unit": "ta",
        },
        {
            "code": "WORKFLOW_SUCCESS_RATE",
            "name": "Ish Oqimlari Muvaffaqiyat Foizi",
            "category": KPICategory.OPERATIONS.value,
            "description": "Avtomatlashtirilgan jarayonlarning xatosiz yakunlanish foizi",
            "calculation_type": "query",
            "target_value": 98.0,
            "warning_threshold": 90.0,
            "critical_threshold": 80.0,
            "unit": "%",
        },
        {
            "code": "ACTIVE_USERS_RATIO",
            "name": "Faol Xodimlar Nisbati",
            "category": KPICategory.HR.value,
            "description": "Kompaniyadagi umumiy foydalanuvchilarga nisbatan faol foydalanuvchilar foizi",
            "calculation_type": "query",
            "target_value": 85.0,
            "warning_threshold": 60.0,
            "critical_threshold": 40.0,
            "unit": "%",
        },
    ]

    async def calculate_kpi_by_code(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        code: str,
        target_value: Optional[float] = None,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        unit: str = "",
    ) -> KPICalculationResult:
        """Calculates value for a specific KPI code."""
        code_upper = code.upper()

        if code_upper == "TASK_COMPLETION_RATE":
            return await self._calculate_task_completion_rate(
                db, company_id, target_value, warning_threshold, critical_threshold
            )
        elif code_upper == "OVERDUE_TASKS_COUNT":
            return await self._calculate_overdue_tasks(
                db, company_id, target_value, warning_threshold, critical_threshold
            )
        elif code_upper == "PENDING_TASKS_COUNT":
            return await self._calculate_pending_tasks(
                db, company_id, target_value, warning_threshold, critical_threshold
            )
        elif code_upper == "DOCUMENT_PROCESSING_VOLUME":
            return await self._calculate_doc_volume(
                db, company_id, target_value, warning_threshold, critical_threshold
            )
        elif code_upper == "AI_USAGE_MESSAGES":
            return await self._calculate_ai_messages(
                db, company_id, target_value, warning_threshold, critical_threshold
            )
        elif code_upper == "WORKFLOW_SUCCESS_RATE":
            return await self._calculate_workflow_success_rate(
                db, company_id, target_value, warning_threshold, critical_threshold
            )
        elif code_upper == "ACTIVE_USERS_RATIO":
            return await self._calculate_active_users_ratio(
                db, company_id, target_value, warning_threshold, critical_threshold
            )
        else:
            # Fallback for custom / unhandled KPI
            return KPICalculationResult(
                code=code,
                name=code,
                category=KPICategory.CUSTOM.value,
                current_value=0.0,
                previous_value=None,
                change_pct=None,
                status=KPIStatus.HEALTHY.value,
                unit=unit or "",
                target_value=target_value,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
            )

    async def _calculate_task_completion_rate(
        self, db: AsyncSession, company_id: uuid.UUID, target: Optional[float], warn: Optional[float], crit: Optional[float]
    ) -> KPICalculationResult:
        total_tasks = await db.scalar(
            select(func.count()).select_from(Task).where(Task.company_id == company_id, Task.deleted_at.is_(None))
        ) or 0

        completed_tasks = await db.scalar(
            select(func.count()).select_from(Task).where(
                Task.company_id == company_id, Task.status == "completed", Task.deleted_at.is_(None)
            )
        ) or 0

        rate = (completed_tasks / total_tasks * 100.0) if total_tasks > 0 else 100.0
        rate = round(rate, 2)

        # Status determination (higher is better)
        target = target if target is not None else 90.0
        warn = warn if warn is not None else 75.0
        crit = crit if crit is not None else 60.0

        if rate < crit:
            status = KPIStatus.CRITICAL.value
        elif rate < warn:
            status = KPIStatus.WARNING.value
        else:
            status = KPIStatus.HEALTHY.value

        return KPICalculationResult(
            code="TASK_COMPLETION_RATE",
            name="Vazifalar Bajarilish Ko'rsatkichi",
            category=KPICategory.OPERATIONS.value,
            current_value=rate,
            previous_value=85.0,  # Benchmark
            change_pct=round(((rate - 85.0) / 85.0 * 100.0), 2),
            status=status,
            unit="%",
            target_value=target,
            warning_threshold=warn,
            critical_threshold=crit,
            meta_data={"total_tasks": total_tasks, "completed_tasks": completed_tasks},
        )

    async def _calculate_overdue_tasks(
        self, db: AsyncSession, company_id: uuid.UUID, target: Optional[float], warn: Optional[float], crit: Optional[float]
    ) -> KPICalculationResult:
        now = datetime.now(timezone.utc)
        overdue_count = await db.scalar(
            select(func.count()).select_from(Task).where(
                Task.company_id == company_id,
                Task.status.in_(["todo", "in_progress"]),
                Task.due_date < now,
                Task.deleted_at.is_(None),
            )
        ) or 0

        target = target if target is not None else 0.0
        warn = warn if warn is not None else 5.0
        crit = crit if crit is not None else 10.0

        # Lower is better
        if overdue_count >= crit:
            status = KPIStatus.CRITICAL.value
        elif overdue_count >= warn:
            status = KPIStatus.WARNING.value
        else:
            status = KPIStatus.HEALTHY.value

        return KPICalculationResult(
            code="OVERDUE_TASKS_COUNT",
            name="Muddati O'tgan Vazifalar",
            category=KPICategory.OPERATIONS.value,
            current_value=float(overdue_count),
            previous_value=0.0,
            change_pct=None,
            status=status,
            unit="ta",
            target_value=target,
            warning_threshold=warn,
            critical_threshold=crit,
            meta_data={"overdue_count": overdue_count},
        )

    async def _calculate_pending_tasks(
        self, db: AsyncSession, company_id: uuid.UUID, target: Optional[float], warn: Optional[float], crit: Optional[float]
    ) -> KPICalculationResult:
        pending_count = await db.scalar(
            select(func.count()).select_from(Task).where(
                Task.company_id == company_id,
                Task.status.in_(["todo", "in_progress"]),
                Task.deleted_at.is_(None),
            )
        ) or 0

        target = target if target is not None else 20.0
        warn = warn if warn is not None else 50.0
        crit = crit if crit is not None else 100.0

        if pending_count >= crit:
            status = KPIStatus.CRITICAL.value
        elif pending_count >= warn:
            status = KPIStatus.WARNING.value
        else:
            status = KPIStatus.HEALTHY.value

        return KPICalculationResult(
            code="PENDING_TASKS_COUNT",
            name="Jarayondagi Vazifalar",
            category=KPICategory.OPERATIONS.value,
            current_value=float(pending_count),
            previous_value=15.0,
            change_pct=round(((pending_count - 15.0) / 15.0 * 100.0), 2) if 15.0 > 0 else 0.0,
            status=status,
            unit="ta",
            target_value=target,
            warning_threshold=warn,
            critical_threshold=crit,
            meta_data={"pending_count": pending_count},
        )

    async def _calculate_doc_volume(
        self, db: AsyncSession, company_id: uuid.UUID, target: Optional[float], warn: Optional[float], crit: Optional[float]
    ) -> KPICalculationResult:
        doc_count = await db.scalar(
            select(func.count()).select_from(Document).where(
                Document.company_id == company_id, Document.deleted_at.is_(None)
            )
        ) or 0

        target = target if target is not None else 50.0
        warn = warn if warn is not None else 10.0
        crit = crit if crit is not None else 2.0

        status = KPIStatus.HEALTHY.value

        return KPICalculationResult(
            code="DOCUMENT_PROCESSING_VOLUME",
            name="Qayta Ishlangan Hujjatlar Hajmi",
            category=KPICategory.DOCUMENTS.value,
            current_value=float(doc_count),
            previous_value=float(doc_count),
            change_pct=0.0,
            status=status,
            unit="ta",
            target_value=target,
            warning_threshold=warn,
            critical_threshold=crit,
            meta_data={"doc_count": doc_count},
        )

    async def _calculate_ai_messages(
        self, db: AsyncSession, company_id: uuid.UUID, target: Optional[float], warn: Optional[float], crit: Optional[float]
    ) -> KPICalculationResult:
        total_messages = await db.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .join(Chat)
            .where(Chat.company_id == company_id, Chat.deleted_at.is_(None))
        ) or 0

        target = target if target is not None else 100.0
        status = KPIStatus.HEALTHY.value if total_messages > 0 else KPIStatus.WARNING.value

        return KPICalculationResult(
            code="AI_USAGE_MESSAGES",
            name="AI Yordamchi Foydalanish Hajmi",
            category=KPICategory.AI.value,
            current_value=float(total_messages),
            previous_value=None,
            change_pct=None,
            status=status,
            unit="ta",
            target_value=target,
            warning_threshold=warn or 20.0,
            critical_threshold=crit or 5.0,
            meta_data={"total_messages": total_messages},
        )

    async def _calculate_workflow_success_rate(
        self, db: AsyncSession, company_id: uuid.UUID, target: Optional[float], warn: Optional[float], crit: Optional[float]
    ) -> KPICalculationResult:
        total_runs = await db.scalar(
            select(func.count()).select_from(WorkflowExecution).where(WorkflowExecution.company_id == company_id)
        ) or 0

        successful_runs = await db.scalar(
            select(func.count()).select_from(WorkflowExecution).where(
                WorkflowExecution.company_id == company_id, WorkflowExecution.status == "completed"
            )
        ) or 0

        rate = (successful_runs / total_runs * 100.0) if total_runs > 0 else 100.0
        rate = round(rate, 2)

        target = target if target is not None else 98.0
        warn = warn if warn is not None else 90.0
        crit = crit if crit is not None else 80.0

        if rate < crit:
            status = KPIStatus.CRITICAL.value
        elif rate < warn:
            status = KPIStatus.WARNING.value
        else:
            status = KPIStatus.HEALTHY.value

        return KPICalculationResult(
            code="WORKFLOW_SUCCESS_RATE",
            name="Ish Oqimlari Muvaffaqiyat Foizi",
            category=KPICategory.OPERATIONS.value,
            current_value=rate,
            previous_value=100.0,
            change_pct=round(rate - 100.0, 2),
            status=status,
            unit="%",
            target_value=target,
            warning_threshold=warn,
            critical_threshold=crit,
            meta_data={"total_runs": total_runs, "successful_runs": successful_runs},
        )

    async def _calculate_active_users_ratio(
        self, db: AsyncSession, company_id: uuid.UUID, target: Optional[float], warn: Optional[float], crit: Optional[float]
    ) -> KPICalculationResult:
        total_users = await db.scalar(
            select(func.count()).select_from(User).where(User.company_id == company_id, User.deleted_at.is_(None))
        ) or 0

        active_users = await db.scalar(
            select(func.count()).select_from(User).where(
                User.company_id == company_id, User.is_active.is_(True), User.deleted_at.is_(None)
            )
        ) or 0

        ratio = (active_users / total_users * 100.0) if total_users > 0 else 100.0
        ratio = round(ratio, 2)

        target = target if target is not None else 85.0
        warn = warn if warn is not None else 60.0
        crit = crit if crit is not None else 40.0

        if ratio < crit:
            status = KPIStatus.CRITICAL.value
        elif ratio < warn:
            status = KPIStatus.WARNING.value
        else:
            status = KPIStatus.HEALTHY.value

        return KPICalculationResult(
            code="ACTIVE_USERS_RATIO",
            name="Faol Xodimlar Nisbati",
            category=KPICategory.HR.value,
            current_value=ratio,
            previous_value=100.0,
            change_pct=round(ratio - 100.0, 2),
            status=status,
            unit="%",
            target_value=target,
            warning_threshold=warn,
            critical_threshold=crit,
            meta_data={"total_users": total_users, "active_users": active_users},
        )


kpi_engine = KPIEngine()
