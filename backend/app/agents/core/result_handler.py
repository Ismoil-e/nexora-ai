"""Normalizes and persists agent execution results."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts.types import AgentResult, AgentStatus
from app.repositories.agent_repo import AgentExecutionRepository


class AgentResultHandler:
    """Handles persistence and response shaping for agent runs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.execution_repo = AgentExecutionRepository(db)

    async def mark_processing(
        self,
        *,
        agent_id: uuid.UUID | None,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        agent_key: str,
        input_text: str,
    ) -> Any:
        """Create an AgentExecution row in processing state."""
        payload: dict[str, Any] = {
            "user_id": user_id,
            "input_data": input_text,
            "status": AgentStatus.EXECUTING.value,
        }
        # Extended columns are optional for backward-compatible DBs mid-migration
        model = self.execution_repo.model
        if hasattr(model, "company_id"):
            payload["company_id"] = company_id
        if hasattr(model, "agent_key"):
            payload["agent_key"] = agent_key

        if agent_id is not None:
            payload["agent_id"] = agent_id
            return await self.execution_repo.create(**payload)

        # Framework-only run without DB Agent row: attach to a system placeholder if required
        # Callers should ensure agent_id exists for FK integrity.
        raise ValueError("agent_id is required to persist AgentExecution")

    async def complete(
        self,
        execution_id: uuid.UUID,
        result: AgentResult,
    ) -> AgentResult:
        update_data: dict[str, Any] = {
            "output_data": json.dumps(result.to_dict(), ensure_ascii=False),
            "status": result.status.value if result.success else AgentStatus.FAILED.value,
            "token_used": result.token_used,
            "duration_ms": result.duration_ms,
        }
        if result.error:
            update_data["error_message"] = result.error
        await self.execution_repo.update(execution_id, **update_data)
        result.execution_id = execution_id
        return result

    async def fail(
        self,
        execution_id: uuid.UUID,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        await self.execution_repo.update(
            execution_id,
            status=AgentStatus.FAILED.value,
            error_message=error,
            duration_ms=duration_ms,
        )

    def shape(self, result: AgentResult) -> dict[str, Any]:
        return result.to_dict()
