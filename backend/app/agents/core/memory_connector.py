"""Connects agents to Cognitive Memory Engine (no direct DB in agents)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts.types import AgentContext, MemoryBundle
from app.cognitive.contracts.frames import ContextFrame
from app.cognitive.services.engines import MemoryEngine


class AgentMemoryConnector:
    """Facade used by agents to retrieve and persist memory."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.memory_engine = MemoryEngine(db)

    def _frame_from_context(self, context: AgentContext) -> ContextFrame:
        existing = context.extras.get("context_frame")
        if isinstance(existing, ContextFrame):
            return existing
        return ContextFrame(
            company_id=context.company_id,
            user_id=context.user_id,
            permissions=context.permissions,
            conversation_id=context.request.chat_id,
            active_document_ids=list(context.request.document_ids),
            project_id=context.project_id,
            department_id=context.department_id,
        )

    async def retrieve(self, context: AgentContext, query: str, top_k: int = 5) -> MemoryBundle:
        pack = await self.memory_engine.retrieve(self._frame_from_context(context), query, top_k=top_k)
        return MemoryBundle(
            items=pack.memory_items,
            graph_summary=pack.graph_summary,
            timeline=pack.timeline,
            decisions=pack.decisions,
            query=pack.query,
        )

    async def save_episode(
        self,
        context: AgentContext,
        agent_key: str,
        output: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return await self.memory_engine.save_episode(
            frame=self._frame_from_context(context),
            agent_key=agent_key,
            input_text=context.request.input,
            output_text=output,
            metadata=metadata,
        )
