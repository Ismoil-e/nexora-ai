import uuid

from sqlalchemy import func, select

from app.models.agent import Agent, AgentExecution
from app.repositories.base import BaseRepository
from app.utils.helpers import paginate


class AgentRepository(BaseRepository[Agent]):
    def __init__(self, db):
        super().__init__(Agent, db)

    async def get_by_company(self, company_id: uuid.UUID, page: int = 1, page_size: int = 20) -> tuple[list[Agent], int]:
        offset, limit = paginate(page, page_size)
        filters = [Agent.company_id == company_id, Agent.deleted_at.is_(None)]

        stmt = (
            select(Agent).where(*filters)
            .offset(offset).limit(limit)
            .order_by(Agent.created_at.desc())
        )
        result = await self.db.execute(stmt)
        agents = list(result.scalars().all())

        count_stmt = select(func.count()).select_from(Agent).where(*filters)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return agents, total

    async def get_active_by_company(self, company_id: uuid.UUID) -> list[Agent]:
        stmt = select(Agent).where(
            Agent.company_id == company_id,
            Agent.is_active.is_(True),
            Agent.deleted_at.is_(None),
        ).order_by(Agent.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class AgentExecutionRepository(BaseRepository[AgentExecution]):
    def __init__(self, db):
        super().__init__(AgentExecution, db)
