import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def get(self, id: uuid.UUID) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id, self.model.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many(
        self,
        *filters,
        offset: int = 0,
        limit: int = 20,
        order_by: Any | None = None,
    ) -> list[ModelType]:
        stmt = select(self.model).where(self.model.deleted_at.is_(), *filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self.model.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, **kwargs) -> ModelType | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id, self.model.deleted_at.is_(None))
            .values(**{k: v for k, v in kwargs.items() if v is not None})
            .returning(self.model)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def soft_delete(self, id: uuid.UUID) -> bool:
        from datetime import datetime, timezone
        stmt = (
            update(self.model)
            .where(self.model.id == id, self.model.deleted_at.is_(None))
            .values(deleted_at=datetime.now(timezone.utc))
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    async def hard_delete(self, id: uuid.UUID) -> bool:
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    async def count(self, *filters) -> int:
        stmt = select(self.model).where(self.model.deleted_at.is_(), *filters)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def exists(self, id: uuid.UUID) -> bool:
        return await self.get(id) is not None
