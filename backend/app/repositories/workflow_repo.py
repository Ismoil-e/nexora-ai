"""Repositories for workflow automation entities."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.workflow import (
    Workflow,
    WorkflowApproval,
    WorkflowExecution,
    WorkflowHistory,
    WorkflowLog,
    WorkflowSchedule,
    WorkflowStep,
    WorkflowTrigger,
)
from app.repositories.base import BaseRepository
from app.utils.helpers import paginate


class WorkflowRepository(BaseRepository[Workflow]):
    def __init__(self, db):
        super().__init__(Workflow, db)

    async def get_with_steps(self, workflow_id: uuid.UUID) -> Workflow | None:
        stmt = (
            select(Workflow)
            .where(Workflow.id == workflow_id, Workflow.deleted_at.is_(None))
            .options(
                selectinload(Workflow.steps),
                selectinload(Workflow.triggers),
                selectinload(Workflow.schedules),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, company_id: uuid.UUID, slug: str) -> Workflow | None:
        stmt = (
            select(Workflow)
            .where(
                Workflow.company_id == company_id,
                Workflow.slug == slug,
                Workflow.deleted_at.is_(None),
            )
            .options(selectinload(Workflow.steps), selectinload(Workflow.triggers))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_company(
        self,
        company_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Workflow], int]:
        offset, limit = paginate(page, page_size)
        filters = [Workflow.company_id == company_id, Workflow.deleted_at.is_(None)]
        if status:
            filters.append(Workflow.status == status)
        stmt = (
            select(Workflow)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(Workflow.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        count_stmt = select(func.count()).select_from(Workflow).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        return items, total


class WorkflowStepRepository(BaseRepository[WorkflowStep]):
    def __init__(self, db):
        super().__init__(WorkflowStep, db)


class WorkflowExecutionRepository(BaseRepository[WorkflowExecution]):
    def __init__(self, db):
        super().__init__(WorkflowExecution, db)

    async def get_with_details(self, execution_id: uuid.UUID) -> WorkflowExecution | None:
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id, WorkflowExecution.deleted_at.is_(None))
            .options(
                selectinload(WorkflowExecution.logs),
                selectinload(WorkflowExecution.history),
                selectinload(WorkflowExecution.approvals),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workflow(
        self,
        workflow_id: uuid.UUID,
        company_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WorkflowExecution], int]:
        offset, limit = paginate(page, page_size)
        filters = [
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.company_id == company_id,
            WorkflowExecution.deleted_at.is_(None),
        ]
        stmt = (
            select(WorkflowExecution)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(WorkflowExecution.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        total = (await self.db.execute(select(func.count()).select_from(WorkflowExecution).where(*filters))).scalar() or 0
        return items, total


class WorkflowLogRepository(BaseRepository[WorkflowLog]):
    def __init__(self, db):
        super().__init__(WorkflowLog, db)

    async def list_by_execution(self, execution_id: uuid.UUID) -> list[WorkflowLog]:
        stmt = (
            select(WorkflowLog)
            .where(WorkflowLog.execution_id == execution_id, WorkflowLog.deleted_at.is_(None))
            .order_by(WorkflowLog.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class WorkflowHistoryRepository(BaseRepository[WorkflowHistory]):
    def __init__(self, db):
        super().__init__(WorkflowHistory, db)


class WorkflowApprovalRepository(BaseRepository[WorkflowApproval]):
    def __init__(self, db):
        super().__init__(WorkflowApproval, db)


class WorkflowTriggerRepository(BaseRepository[WorkflowTrigger]):
    def __init__(self, db):
        super().__init__(WorkflowTrigger, db)


class WorkflowScheduleRepository(BaseRepository[WorkflowSchedule]):
    def __init__(self, db):
        super().__init__(WorkflowSchedule, db)
