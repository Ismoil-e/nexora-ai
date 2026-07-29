import uuid

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository
from app.utils.helpers import paginate


class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        stmt = select(User).where(User.google_id == google_id, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_company(self, company_id: uuid.UUID, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
        from sqlalchemy import func

        offset, limit = paginate(page, page_size)

        stmt = (
            select(User)
            .where(User.company_id == company_id, User.deleted_at.is_(None))
            .offset(offset).limit(limit)
            .order_by(User.created_at.desc())
        )
        result = await self.db.execute(stmt)
        users = list(result.scalars().all())

        count_stmt = select(func.count()).select_from(User).where(
            User.company_id == company_id, User.deleted_at.is_(None)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return users, total
