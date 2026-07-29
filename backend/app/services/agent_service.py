import uuid
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.agent_repo import AgentExecutionRepository, AgentRepository
from app.services.ai_service import AIService


class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent_repo = AgentRepository(db)
        self.execution_repo = AgentExecutionRepository(db)
        self.ai_service = AIService(db)

    async def create_agent(self, company_id: uuid.UUID, data: dict):
        return await self.agent_repo.create(company_id=company_id, **data)

    async def get_agents(self, company_id: uuid.UUID, page: int = 1, page_size: int = 20) -> dict:
        agents, total = await self.agent_repo.get_by_company(company_id, page, page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [{
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "ai_provider": a.ai_provider,
                "model": a.model,
                "is_active": a.is_active,
                "icon": a.icon,
                "color": a.color,
                "created_at": a.created_at.isoformat(),
            } for a in agents],
        }

    async def execute_agent(self, agent_id: uuid.UUID, user_id: uuid.UUID, input_text: str) -> dict:
        agent = await self.agent_repo.get(agent_id)
        if not agent or not agent.is_active:
            return None

        start_time = time.perf_counter()

        execution = await self.execution_repo.create(
            agent_id=agent_id,
            user_id=user_id,
            input_data=input_text,
            status="processing",
        )

        try:
            response = await self.ai_service.chat(
                provider=agent.ai_provider,
                model=agent.model,
                messages=[{"role": "user", "content": input_text}],
                system_prompt=agent.system_prompt,
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            token_used = response.get("token_count", 0)

            await self.execution_repo.update(
                execution.id,
                output_data=response["content"],
                status="completed",
                token_used=token_used,
                duration_ms=duration_ms,
            )

            return {
                "output": response["content"],
                "execution_id": execution.id,
                "token_used": token_used,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            await self.execution_repo.update(
                execution.id,
                status="failed",
                error_message=str(e),
            )
            raise
