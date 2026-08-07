import uuid
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.bootstrap import ensure_agents_bootstrapped
from app.agents.contracts.types import AgentIdentity, AgentRequest
from app.agents.core.manager import AgentManager
from app.repositories.agent_repo import AgentExecutionRepository, AgentRepository
from app.services.ai_service import AIService


class AgentService:
    """Domain service for company Agent CRUD + framework execution."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent_repo = AgentRepository(db)
        self.execution_repo = AgentExecutionRepository(db)
        self.ai_service = AIService(db)
        ensure_agents_bootstrapped()
        self.manager = AgentManager(db)

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
                "agent_key": getattr(a, "agent_key", None),
                "agent_type": getattr(a, "agent_type", None),
                "created_at": a.created_at.isoformat(),
            } for a in agents],
        }

    def list_framework_catalog(self) -> list[dict]:
        return self.manager.catalog()

    async def run_framework_agent(
        self,
        *,
        agent_key: str,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        input_text: str,
        chat_id: uuid.UUID | None = None,
        document_ids: list[uuid.UUID] | None = None,
        metadata: dict | None = None,
        async_mode: bool = False,
        provider: str | None = None,
        model: str | None = None,
        permissions: list[str] | None = None,
        roles: list[str] | None = None,
        provision_db_agent: bool = True,
    ) -> dict:
        """Execute a registered framework agent by key."""
        identity = AgentIdentity(
            user_id=user_id,
            company_id=company_id,
            permissions=permissions or [],
            roles=roles or [],
        )
        request = AgentRequest(
            agent_key=agent_key,
            input=input_text,
            identity=identity,
            chat_id=chat_id,
            document_ids=document_ids or [],
            metadata=metadata or {},
            async_mode=async_mode,
            provider=provider,
            model=model,
        )
        if provision_db_agent:
            result = await self.manager.run_ephemeral_with_system_agent(request)
        else:
            result = await self.manager.run(request)
        return result.to_dict()

    async def execute_agent(self, agent_id: uuid.UUID, user_id: uuid.UUID, input_text: str) -> dict:
        """Backward-compatible execution for company Agent rows.

        If the row is linked to a framework ``agent_key``, prefer AgentManager.
        Otherwise keep the legacy ReAct tool executor path.
        """
        agent = await self.agent_repo.get(agent_id)
        if not agent or not agent.is_active:
            return None

        agent_key = getattr(agent, "agent_key", None)
        if agent_key and self.manager.registry.has(agent_key):
            identity = AgentIdentity(user_id=user_id, company_id=agent.company_id)
            request = AgentRequest(
                agent_key=agent_key,
                input=input_text,
                identity=identity,
                provider=agent.ai_provider,
                model=agent.model,
            )
            managed = await self.manager.run(request, agent_id=agent.id)
            payload = managed.to_dict()
            return {
                "output": payload.get("output", ""),
                "execution_id": managed.execution_id,
                "steps": payload.get("steps", []),
                "token_used": payload.get("token_used", 0),
                "duration_ms": payload.get("duration_ms", 0),
                "agent_key": agent_key,
            }

        from app.ai.agents.agent_executor import AgentExecutor
        from app.ai.agents.tools import ToolExecutionContext

        execution = await self.execution_repo.create(
            agent_id=agent_id,
            user_id=user_id,
            input_data=input_text,
            status="processing",
        )

        context = ToolExecutionContext(db=self.db, company_id=agent.company_id, user_id=user_id)
        executor = AgentExecutor(self.db)

        allowed_tools = None
        if agent.tools_config:
            try:
                tools_data = json.loads(agent.tools_config)
                if isinstance(tools_data, list):
                    allowed_tools = tools_data
            except Exception:
                pass

        try:
            res = await executor.run(
                provider=agent.ai_provider,
                model=agent.model,
                system_prompt=agent.system_prompt,
                user_input=input_text,
                context=context,
                allowed_tools=allowed_tools,
            )

            await self.execution_repo.update(
                execution.id,
                output_data=json.dumps(res.to_dict(), ensure_ascii=False),
                status="completed",
                token_used=res.total_tokens,
                duration_ms=res.duration_ms,
            )

            return {
                "output": res.output,
                "execution_id": execution.id,
                "steps": res.steps,
                "token_used": res.total_tokens,
                "duration_ms": res.duration_ms,
            }

        except Exception as e:
            await self.execution_repo.update(
                execution.id,
                status="failed",
                error_message=str(e),
            )
            raise
