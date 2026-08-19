import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_db
from app.models.chat import Chat, ChatMessage
from app.models.document import Document
from app.models.notification import Notification
from app.models.task import Task
from app.schemas.bi import DashboardDetailResponse
from app.services.bi_service import BusinessIntelligenceService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    chat_count = await db.scalar(
        select(func.count()).select_from(Chat).where(Chat.company_id == company_id, Chat.deleted_at.is_(None))
    )

    doc_count = await db.scalar(
        select(func.count()).select_from(Document).where(Document.company_id == company_id, Document.deleted_at.is_(None))
    )

    task_count = await db.scalar(
        select(func.count()).select_from(Task).where(Task.company_id == company_id, Task.deleted_at.is_(None))
    )

    pending_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(
            Task.company_id == company_id,
            Task.status.in_(["todo", "in_progress"]),
            Task.deleted_at.is_(None),
        )
    )

    unread_notifications = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.company_id == company_id,
            Notification.is_read.is_(False),
        )
    )

    total_messages = await db.scalar(
        select(func.count())
        .select_from(ChatMessage)
        .join(Chat)
        .where(Chat.company_id == company_id, Chat.deleted_at.is_(None))
    )

    return {
        "chats": chat_count or 0,
        "documents": doc_count or 0,
        "tasks": task_count or 0,
        "pending_tasks": pending_tasks or 0,
        "unread_notifications": unread_notifications or 0,
        "total_messages": total_messages or 0,
    }


@router.get("/main", response_model=DashboardDetailResponse)
async def get_main_dashboard(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns the primary tenant dashboard with its widgets."""
    svc = BusinessIntelligenceService(db)
    dash = await svc.ensure_default_dashboard(company_id)
    return dash
