"""Pipeline executor — runs the full BaseAgent lifecycle."""

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts.types import AgentRequest, AgentResult, AgentStatus
from app.agents.core.context_builder import AgentContextBuilder
from app.agents.core.event_publisher import AgentEventPublisher
from app.agents.core.memory_connector import AgentMemoryConnector
from app.agents.core.result_handler import AgentResultHandler
from app.agents.interfaces.base_agent import BaseAgent
from app.cognitive.services.engines import PlanningEngine


class AgentPipelineExecutor:
    """Executes: validate → context → memory → plan → execute → post → memory → events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.context_builder = AgentContextBuilder(db)
        self.memory_connector = AgentMemoryConnector(db)
        self.planning_engine = PlanningEngine()
        self.result_handler = AgentResultHandler(db)
        self.event_publisher = AgentEventPublisher()

    def build_service_bag(self) -> dict[str, Any]:
        """Shared services injected into agents (never raw repositories for agents)."""
        from app.services.ai_service import AIService
        from app.services.chat_service import ChatService
        from app.services.document_service import DocumentService
        from app.services.notification_service import NotificationService

        return {
            "db_session_forbidden": True,  # documentation flag — agents must not use DB
            "ai_service": AIService(self.db),
            "document_service": DocumentService(self.db),
            "chat_service": ChatService(self.db),
            "notification_service": NotificationService(self.db),
            "memory_connector": self.memory_connector,
            "context_builder": self.context_builder,
            "planning_engine": self.planning_engine,
            "event_publisher": self.event_publisher,
        }

    async def run(
        self,
        agent: BaseAgent,
        request: AgentRequest,
        *,
        db_agent_id: uuid.UUID | None = None,
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        started = time.perf_counter()
        execution = None
        context = None

        try:
            await agent.initialize(self.build_service_bag())
            await agent.validate(request)

            if db_agent_id is not None:
                execution = await self.result_handler.mark_processing(
                    agent_id=db_agent_id,
                    user_id=request.identity.user_id,
                    company_id=request.identity.company_id,
                    agent_key=agent.agent_key,
                    input_text=request.input,
                )

            context = await agent.build_context(request)
            if config:
                context.config.update(config)

            memory = await agent.retrieve_memory(context)
            plan = await agent.plan(context, memory)

            if (plan.requires_async or request.async_mode) and not request.metadata.get("force_sync"):
                # Defer heavy work to Celery
                from app.workers.agent_worker import run_agent_job

                task = run_agent_job.delay(
                    agent_key=agent.agent_key,
                    company_id=str(request.identity.company_id),
                    user_id=str(request.identity.user_id),
                    input_text=request.input,
                    chat_id=str(request.chat_id) if request.chat_id else None,
                    document_ids=[str(d) for d in request.document_ids],
                    metadata={**(request.metadata or {}), "force_sync": True},
                    execution_id=str(execution.id) if execution else None,
                    db_agent_id=str(db_agent_id) if db_agent_id else None,
                    permissions=list(request.identity.permissions or []),
                    roles=list(request.identity.roles or []),
                )
                result = AgentResult(
                    success=True,
                    output="Agent ishi fon rejimida bajarilmoqda.",
                    agent_key=agent.agent_key,
                    execution_id=execution.id if execution else None,
                    status=AgentStatus.EXECUTING,
                    plan=plan,
                    async_task_id=task.id,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
                if execution:
                    await self.result_handler.complete(execution.id, result)
                return await agent.return_response(result)

            result = await agent.execute(context, memory, plan)
            result = await agent.post_process(context, result)
            memory_refs = await agent.save_memory(context, result)
            result.memory_refs = memory_refs
            await agent.publish_events(context, result)
            result.duration_ms = result.duration_ms or int((time.perf_counter() - started) * 1000)
            result.status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED

            if execution:
                result = await self.result_handler.complete(execution.id, result)

            await self.event_publisher.publish_completed(context, result)
            return await agent.return_response(result)

        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            if execution:
                await self.result_handler.fail(execution.id, str(exc), duration_ms=duration_ms)
            if context is not None:
                await self.event_publisher.publish_failed(
                    context,
                    str(exc),
                    execution_id=execution.id if execution else None,
                )
            return AgentResult(
                success=False,
                output="",
                agent_key=agent.agent_key,
                execution_id=execution.id if execution else None,
                status=AgentStatus.FAILED,
                error=str(exc),
                duration_ms=duration_ms,
            )
