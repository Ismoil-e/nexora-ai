import uuid

from sqlalchemy import select

from app.models.role import Permission, Role, RolePermission
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db):
        super().__init__(Role, db)

    async def get_by_company(self, company_id: uuid.UUID) -> list[Role]:
        stmt = (
            select(Role)
            .where(Role.company_id == company_id, Role.deleted_at.is_(None))
            .order_by(Role.priority.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_with_permissions(self, role_id: uuid.UUID) -> Role | None:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Role)
            .where(Role.id == role_id, Role.deleted_at.is_(None))
            .options(selectinload(Role.permissions))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db):
        super().__init__(Permission, db)

    async def get_by_module(self, module: str) -> list[Permission]:
        stmt = select(Permission).where(Permission.module == module).order_by(Permission.code)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
