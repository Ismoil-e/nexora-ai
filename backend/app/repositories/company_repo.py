import uuid

from sqlalchemy import select

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db):
        super().__init__(Company, db)

    async def get_by_slug(self, slug: str) -> Company | None:
        stmt = select(Company).where(Company.slug == slug, Company.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_count(self, company_id: uuid.UUID) -> int:
        from app.models.user import User
        from sqlalchemy import func

        stmt = select(func.count()).select_from(User).where(
            User.company_id == company_id, User.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
