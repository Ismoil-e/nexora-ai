import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_profile(self, user_id: uuid.UUID) -> dict:
        user = await self.user_repo.get(user_id)
        if not user:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "position": user.position,
            "phone": user.phone,
            "company_id": user.company_id,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }

    async def update_profile(self, user_id: uuid.UUID, data: dict) -> dict:
        user = await self.user_repo.update(user_id, **data)
        return await self.get_profile(user_id)

    async def get_company_users(self, company_id: uuid.UUID, page: int = 1, page_size: int = 20) -> dict:
        users, total = await self.user_repo.get_by_company(company_id, page, page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [{
                "id": u.id,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "avatar_url": u.avatar_url,
                "position": u.position,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            } for u in users],
        }
