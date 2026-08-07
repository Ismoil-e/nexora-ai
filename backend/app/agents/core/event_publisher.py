"""Publishes agent lifecycle domain events."""

from __future__ import annotations

import uuid
from typing import Any

from app.agents.contracts.types import AgentContext, AgentResult
from app.core.events import DomainEvent, event_bus


class AgentEventPublisher:
    """Thin wrapper over the platform EventBus for agent events."""

    async def publish(
        self,
        event_type: str,
        context: AgentContext,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await event_bus.publish(
            DomainEvent(
                event_type=event_type,
                company_id=context.company_id,
                user_id=context.user_id,
                payload={
                    "resource_type": "agent",
                    "agent_key": context.request.agent_key,
                    **(payload or {}),
                },
            )
        )

    async def publish_completed(self, context: AgentContext, result: AgentResult) -> None:
        await self.publish(
            "agent.execution.completed",
            context,
            {
                "resource_id": str(result.execution_id) if result.execution_id else None,
                "success": result.success,
                "token_used": result.token_used,
                "duration_ms": result.duration_ms,
            },
        )

    async def publish_failed(
        self,
        context: AgentContext,
        error: str,
        execution_id: uuid.UUID | None = None,
    ) -> None:
        await self.publish(
            "agent.execution.failed",
            context,
            {
                "resource_id": str(execution_id) if execution_id else None,
                "error": error,
            },
        )
