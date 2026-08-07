"""Agent Manager — primary entry point for running registered agents."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts.types import AgentRequest, AgentResult
from app.agents.core.executor import AgentPipelineExecutor
from app.agents.core.registry import AgentRegistry, agent_registry
from app.repositories.agent_repo import AgentRepository
from app.utils.exceptions import AppException


class AgentManager:
    """Coordinates registry lookup, permission checks, and pipeline execution."""

    def __init__(
        self,
        db: AsyncSession,
        registry: AgentRegistry | None = None,
    ) -> None:
        self.db = db
        self.registry = registry or agent_registry
        self.executor = AgentPipelineExecutor(db)
        self.agent_repo = AgentRepository(db)

    def catalog(self) -> list[dict[str, Any]]:
        return self.registry.list_catalog()

    async def ensure_permission(self, request: AgentRequest) -> None:
        """RBAC gate — require agent.execute or agent-specific permission when present."""
        perms = set(request.identity.permissions or [])
        if not perms:
            # Soft-allow when permission list is not projected yet (backward compatible)
            return
        needed = {f"agent.{request.agent_key}.execute", "agent.execute", "agents.execute"}
        if perms.isdisjoint(needed) and "admin" not in perms and "*" not in perms:
            # Also allow if any permission starts with agents.
            if not any(p.startswith("agent") for p in perms):
                raise AppException(
                    status_code=403,
                    error="Forbidden",
                    detail=f"Agent '{request.agent_key}' uchun ruxsat yo'q",
                )

    async def resolve_db_agent(
        self,
        company_id: uuid.UUID,
        agent_key: str,
        agent_id: uuid.UUID | None = None,
    ) -> Any | None:
        if agent_id:
            agent = await self.agent_repo.get(agent_id)
            if agent and agent.company_id == company_id and agent.is_active:
                return agent
            return None

        # Prefer company agent row bound to framework key when available
        by_key = await self.agent_repo.get_by_agent_key(company_id, agent_key)
        if by_key and by_key.is_active:
            return by_key
        return None

    async def run(
        self,
        request: AgentRequest,
        *,
        agent_id: uuid.UUID | None = None,
    ) -> AgentResult:
        if not self.registry.has(request.agent_key):
            raise AppException(
                status_code=404,
                error="Agent not found",
                detail=f"Agent '{request.agent_key}' topilmadi",
            )

        await self.ensure_permission(request)
        agent = self.registry.create(request.agent_key)
        db_agent = await self.resolve_db_agent(
            request.identity.company_id,
            request.agent_key,
            agent_id=agent_id,
        )

        config: dict[str, Any] = {}
        if db_agent:
            config = {
                "provider": request.provider or db_agent.ai_provider,
                "model": request.model or db_agent.model,
                "temperature": db_agent.temperature,
                "max_tokens": db_agent.max_tokens,
                "system_prompt": db_agent.system_prompt,
                "tools_config": db_agent.tools_config,
            }
        else:
            config = {
                "provider": request.provider,
                "model": request.model,
            }

        # Persist execution only when a DB agent row exists (FK). Otherwise run ephemeral.
        return await self.executor.run(
            agent,
            request,
            db_agent_id=db_agent.id if db_agent else None,
            config=config,
        )

    async def run_ephemeral_with_system_agent(
        self,
        request: AgentRequest,
    ) -> AgentResult:
        """Ensure a company-scoped DB agent exists for FK logging, then run."""
        db_agent = await self.resolve_db_agent(request.identity.company_id, request.agent_key)
        if db_agent is None:
            create_kwargs: dict[str, Any] = {
                "company_id": request.identity.company_id,
                "name": request.agent_key.replace("_", " ").title(),
                "description": f"Auto-provisioned framework agent: {request.agent_key}",
                "is_active": True,
            }
            if hasattr(self.agent_repo.model, "agent_key"):
                create_kwargs["agent_key"] = request.agent_key
            db_agent = await self.agent_repo.create(**create_kwargs)
        return await self.run(request, agent_id=db_agent.id)
