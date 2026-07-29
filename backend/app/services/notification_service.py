import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import BaseRepository
from app.utils.helpers import paginate


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db):
        super().__init__(Notification, db)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_repo = NotificationRepository(db)

    async def create_notification(self, company_id: uuid.UUID, user_id: uuid.UUID | None,
                                    title: str, body: str, notification_type: str,
                                    reference_type: str | None = None,
                                    reference_id: uuid.UUID | None = None) -> Notification:
        return await self.notification_repo.create(
            company_id=company_id,
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            reference_type=reference_type,
            reference_id=reference_id,
        )

    async def get_user_notifications(self, user_id: uuid.UUID, company_id: uuid.UUID,
                                      page: int = 1, page_size: int = 20) -> dict:
        offset, limit = paginate(page, page_size)
        filters = [
            Notification.company_id == company_id,
            Notification.deleted_at.is_(None),
            ((Notification.user_id == user_id) | (Notification.is_global.is_(True))),
        ]

        stmt = (
            select(Notification).where(*filters)
            .offset(offset).limit(limit)
            .order_by(Notification.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        count_stmt = select(func.count()).select_from(Notification).where(*filters)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        unread_stmt = select(func.count()).select_from(Notification).where(
            *filters, Notification.is_read.is_(False)
        )
        unread_result = await self.db.execute(unread_stmt)
        unread_count = unread_result.scalar()

        return {
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size,
            "items": [{
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "notification_type": n.notification_type,
                "reference_type": n.reference_type,
                "reference_id": str(n.reference_id) if n.reference_id else None,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            } for n in items],
        }

    async def mark_as_read(self, notification_id: uuid.UUID) -> bool:
        result = await self.notification_repo.update(notification_id, is_read=True)
        return result is not None

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        from sqlalchemy import update

        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
