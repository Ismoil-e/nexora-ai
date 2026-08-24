"""AI Orchestrator — central intelligence layer for Nexora AI.

This is the heart of the system. It coordinates:
- Multiple AI models via Model Router
- Multiple specialized agents via Agent Registry
- Tools via Tool Authorization
- Memory, Knowledge Graph, RAG via Context Engine
- Human Approval for sensitive actions
- Execution tracing for full observability
- AI usage tracking and cost control

Flow:
User → Orchestrator → Intent Understanding → Task Planning → Context Retrieval
→ Agent Selection → Tool Selection → Agent Execution → Result Validation
→ Memory Update → Final Response
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts.types import (
    AgentContext,
    AgentIdentity,
    AgentPlan,
    AgentRequest,
    AgentResult,
    AgentStatus,
    MemoryBundle,
)
from app.agents.core.manager import AgentManager
from app.orchestrator.approval_service import ApprovalService
from app.orchestrator.context_engine import ContextEngine
from app.orchestrator.execution_tracer import (
    ExecutionTracer,
    OrchestrationTrace,
    TraceEventType_Overall,
    execution_tracer,
)
from app.orchestrator.model_router import ModelRouter, TaskType, classify_task_type, model_router
from app.orchestrator.task_planner import ExecutionPlan, TaskPlanner
from app.orchestrator.usage_service import AIUsageService, estimate_cost
from app.security.core.audit_logger import audit_logger
from app.utils.exceptions import AppException


class OrchestratorResult:
    """Final result of orchestration."""

    def __init__(
        self,
        *,
        success: bool,
        output: str,
        request_id: str,
        trace_id: str | None = None,
        agent_key: str | None = None,
        plan: ExecutionPlan | None = None,
        citations: list[dict[str, Any]] | None = None,
        timeline: list[dict[str, Any]] | None = None,
        tokens_used: int = 0,
        cost: float = 0.0,
        duration_ms: int = 0,
        error: str | None = None,
    ):
        self.success = success
        self.output = output
        self.request_id = request_id
        self.trace_id = trace_id
        self.agent_key = agent_key
        self.plan = plan
        self.citations = citations or []
        self.timeline = timeline or []
        self.tokens_used = tokens_used
        self.cost = cost
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "agent_key": self.agent_key,
            "plan": {
                "id": self.plan.id if self.plan else None,
                "intent": self.plan.user_intent if self.plan else None,
                "subtasks": [
                    {"id": s.id, "description": s.description, "agent": s.agent_key, "status": s.status.value}
                    for s in (self.plan.subtasks if self.plan else [])
                ],
            } if self.plan else None,
            "citations": self.citations,
            "timeline": self.timeline,
            "tokens_used": self.tokens_used,
            "cost": round(self.cost, 6),
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class Orchestrator:
    """Central AI Orchestrator — coordinates all AI operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.model_router = model_router
        self.task_planner = TaskPlanner()
        self.context_engine = ContextEngine(db)
        self.approval_service = ApprovalService(db)
        self.usage_service = AIUsageService(db)
        self.tracer = execution_tracer
        self.agent_manager = AgentManager(db)

    async def orchestrate(
        self,
        *,
        user_input: str,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        chat_id: uuid.UUID | None = None,
        document_ids: list[uuid.UUID] | None = None,
        permissions: list[str] | None = None,
        roles: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestratorResult:
        """Main orchestration entry point.

        Analyzes the user request, plans execution, selects agents,
        assembles context, executes, and returns the result.
        """
        meta = metadata or {}
        request_id = str(uuid.uuid4())
        started = time.time()

        # 1. Check usage limits
        limit_check = await self.usage_service.check_limits(
            company_id=company_id,
            user_id=user_id,
            estimated_tokens=1000,
        )
        if not limit_check["allowed"]:
            return OrchestratorResult(
                success=False,
                output=f"Usage limit exceeded: {limit_check.get('reason', 'Unknown')}",
                request_id=request_id,
                error=limit_check.get("reason"),
            )

        # 2. Start trace
        trace = self.tracer.start_trace(
            request_id=request_id,
            company_id=company_id,
            user_id=user_id,
            user_input=user_input,
            metadata=meta,
        )

        try:
            # 3. Classify intent
            task_type = classify_task_type(user_input, meta)

            # 4. Should we decompose into subtasks?
            should_decompose = self.task_planner.should_decompose(user_input, meta)

            if should_decompose:
                # Multi-agent orchestration
                result = await self._orchestrate_multi_agent(
                    user_input=user_input,
                    company_id=company_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    document_ids=document_ids or [],
                    permissions=permissions or [],
                    roles=roles or [],
                    metadata=meta,
                    trace=trace,
                    task_type=task_type,
                )
            else:
                # Single agent orchestration
                result = await self._orchestrate_single_agent(
                    user_input=user_input,
                    company_id=company_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    document_ids=document_ids or [],
                    permissions=permissions or [],
                    roles=roles or [],
                    metadata=meta,
                    trace=trace,
                    task_type=task_type,
                )

            # 5. Record usage
            duration_ms = int((time.time() - started) * 1000)
            await self.usage_service.record_usage(
                company_id=company_id,
                user_id=user_id,
                provider=result.get("provider", "unknown"),
                model=result.get("model", "unknown"),
                task_type=task_type.value if isinstance(task_type, TaskType) else str(task_type),
                tokens_total=result.get("tokens_used", 0),
                estimated_cost=result.get("cost", 0.0),
                duration_ms=duration_ms,
                agent_key=result.get("agent_key"),
                request_id=request_id,
                success=True,
            )

            # 6. Audit log
            await audit_logger.log_event(
                self.db,
                action="orchestrator.request_completed",
                resource_type="Orchestration",
                company_id=company_id,
                user_id=user_id,
                details={
                    "request_id": request_id,
                    "task_type": task_type.value if isinstance(task_type, TaskType) else str(task_type),
                    "agent_key": result.get("agent_key"),
                    "tokens": result.get("tokens_used", 0),
                    "cost": result.get("cost", 0),
                    "duration_ms": duration_ms,
                },
            )

            # 7. End trace
            final_trace = self.tracer.end_trace(
                trace.id,
                status=TraceEventType_Overall.COMPLETED,
                final_output=result.get("output", ""),
            )

            return OrchestratorResult(
                success=True,
                output=result.get("output", ""),
                request_id=request_id,
                trace_id=trace.id,
                agent_key=result.get("agent_key"),
                plan=result.get("plan"),
                citations=result.get("citations", []),
                timeline=final_trace.to_timeline() if final_trace else [],
                tokens_used=result.get("tokens_used", 0),
                cost=result.get("cost", 0.0),
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = int((time.time() - started) * 1000)
            self.tracer.record_error(trace.id, str(exc))
            self.tracer.end_trace(
                trace.id,
                status=TraceEventType_Overall.FAILED,
                final_output=None,
            )
            return OrchestratorResult(
                success=False,
                output="",
                request_id=request_id,
                trace_id=trace.id,
                duration_ms=duration_ms,
                error=str(exc),
            )

    async def _orchestrate_single_agent(
        self,
        *,
        user_input: str,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        chat_id: uuid.UUID | None,
        document_ids: list[uuid.UUID],
        permissions: list[str],
        roles: list[str],
        metadata: dict[str, Any],
        trace: OrchestrationTrace,
        task_type: TaskType | str,
    ) -> dict[str, Any]:
        """Single-agent orchestration path."""

        # Route to optimal model
        routing = self.model_router.route(
            task_type=task_type,
            user_input=user_input,
            metadata=metadata,
        )

        # Select the best agent for this task
        agent_key = self._select_agent_for_task(task_type, user_input)
        self.tracer.record_agent_selected(trace.id, agent_key)

        # Build context
        context = await self.context_engine.assemble(
            company_id=company_id,
            user_id=user_id,
            user_input=user_input,
            permissions=permissions,
            chat_id=chat_id,
            document_ids=document_ids,
            agent_key=agent_key,
            metadata={**metadata, "system_prompt": metadata.get("system_prompt", "")},
        )
        self.tracer.record_context_assembled(
            trace.id,
            tokens=context.total_tokens_estimate,
            source_count=len(context.sources),
        )

        # Run agent through the existing pipeline
        identity = AgentIdentity(
            user_id=user_id,
            company_id=company_id,
            permissions=permissions,
            roles=roles,
        )
        request = AgentRequest(
            agent_key=agent_key,
            input=user_input,
            identity=identity,
            chat_id=chat_id,
            document_ids=document_ids,
            metadata={
                **metadata,
                "routing_provider": routing.provider,
                "routing_model": routing.model,
                "orchestrator_trace_id": trace.id,
            },
        )

        event_id = self.tracer.record_agent_start(trace.id, agent_key)

        try:
            result = await self.agent_manager.run_ephemeral_with_system_agent(request)

            self.tracer.record_agent_end(
                trace.id,
                agent_key,
                success=result.success,
                tokens=result.token_used,
                cost=estimate_cost(routing.provider, routing.model, result.token_used, 0),
            )

            self.tracer.record_model_call(
                trace.id,
                provider=routing.provider,
                model=routing.model,
                tokens=result.token_used,
                duration_ms=result.duration_ms,
                success=result.success,
            )

            return {
                "output": result.output,
                "agent_key": agent_key,
                "tokens_used": result.token_used,
                "cost": estimate_cost(routing.provider, routing.model, result.token_used, 0),
                "provider": routing.provider,
                "model": routing.model,
                "citations": result.citations,
                "plan": None,
            }
        except Exception as exc:
            self.tracer.record_agent_end(
                trace.id, agent_key, success=False, error=str(exc),
            )
            raise

    async def _orchestrate_multi_agent(
        self,
        *,
        user_input: str,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        chat_id: uuid.UUID | None,
        document_ids: list[uuid.UUID],
        permissions: list[str],
        roles: list[str],
        metadata: dict[str, Any],
        trace: OrchestrationTrace,
        task_type: TaskType | str,
    ) -> dict[str, Any]:
        """Multi-agent orchestration with task decomposition."""

        # Create execution plan
        plan = self.task_planner.plan(user_input, metadata=metadata, company_id=company_id)
        self.tracer.record_plan(trace.id, plan.id, [
            {"description": s.description, "agent": s.agent_key}
            for s in plan.subtasks
        ])

        all_citations: list[dict[str, Any]] = []
        accumulated_output_parts: list[str] = []
        total_tokens = 0
        total_cost = 0.0
        last_agent_key = None

        # Execute subtasks based on strategy
        if plan.strategy.value == "parallel" and len(plan.subtasks) > 1:
            # Parallel execution
            tasks = []
            for subtask in plan.subtasks:
                tasks.append(
                    self._execute_subtask(
                        subtask=subtask,
                        user_input=user_input,
                        company_id=company_id,
                        user_id=user_id,
                        chat_id=chat_id,
                        permissions=permissions,
                        roles=roles,
                        trace=trace,
                    )
                )
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    plan.subtasks[i].status = "failed"
                    plan.subtasks[i].error = str(result)
                else:
                    accumulated_output_parts.append(result.get("output", ""))
                    all_citations.extend(result.get("citations", []))
                    total_tokens += result.get("tokens_used", 0)
                    total_cost += result.get("cost", 0.0)
                    last_agent_key = result.get("agent_key")
                    plan.subtasks[i].status = "completed"
                    plan.subtasks[i].result = result.get("output", "")
        else:
            # Sequential execution
            for subtask in plan.subtasks:
                self.tracer.record_agent_selected(trace.id, subtask.agent_key)
                subtask.status = "running"
                try:
                    result = await self._execute_subtask(
                        subtask=subtask,
                        user_input=user_input,
                        company_id=company_id,
                        user_id=user_id,
                        chat_id=chat_id,
                        permissions=permissions,
                        roles=roles,
                        trace=trace,
                    )
                    accumulated_output_parts.append(result.get("output", ""))
                    all_citations.extend(result.get("citations", []))
                    total_tokens += result.get("tokens_used", 0)
                    total_cost += result.get("cost", 0.0)
                    last_agent_key = result.get("agent_key")
                    subtask.status = "completed"
                    subtask.result = result.get("output", "")
                except Exception as exc:
                    subtask.status = "failed"
                    subtask.error = str(exc)
                    # Don't stop on failure — continue with other subtasks
                    continue

        # Aggregate results
        final_output = "\n\n".join(accumulated_output_parts) if accumulated_output_parts else "Natija topilmadi"

        return {
            "output": final_output,
            "agent_key": last_agent_key,
            "tokens_used": total_tokens,
            "cost": total_cost,
            "provider": "multi",
            "model": "multi",
            "citations": all_citations,
            "plan": plan,
        }

    async def _execute_subtask(
        self,
        *,
        subtask: Any,
        user_input: str,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        chat_id: uuid.UUID | None,
        permissions: list[str],
        roles: list[str],
        trace: OrchestrationTrace,
    ) -> dict[str, Any]:
        """Execute a single subtask."""
        # Route to model
        routing = self.model_router.route(
            user_input=subtask.description,
            metadata={"task_type": subtask.agent_key},
        )

        # Build context
        context = await self.context_engine.assemble(
            company_id=company_id,
            user_id=user_id,
            user_input=subtask.description,
            permissions=permissions,
            chat_id=chat_id,
            agent_key=subtask.agent_key,
        )

        # Check for approval requirement
        for tool in subtask.tools:
            if self.approval_service.requires_approval(tool):
                approval_req = self.approval_service.create_request(
                    company_id=company_id,
                    requested_by=user_id,
                    agent_key=subtask.agent_key,
                    action=tool,
                    description=f"Agent '{subtask.agent_key}' '{tool}' amalini bajarishni so'raydi",
                    metadata={"subtask_id": subtask.id, "original_request": user_input[:200]},
                )
                self.tracer.record_agent_end(
                    trace.id,
                    subtask.agent_key,
                    success=True,
                    metadata={"approval_required": True, "approval_id": approval_req.id},
                )
                # Return pending status — the approval must be handled externally
                return {
                    "output": f"Tasdiqlash kerak: {tool} — {approval_req.description}",
                    "agent_key": subtask.agent_key,
                    "tokens_used": 0,
                    "cost": 0.0,
                    "citations": [],
                }

        # Run agent
        identity = AgentIdentity(
            user_id=user_id,
            company_id=company_id,
            permissions=permissions,
            roles=roles,
        )
        request = AgentRequest(
            agent_key=subtask.agent_key,
            input=subtask.description + "\n\nAsl so'rov: " + user_input[:500],
            identity=identity,
            chat_id=chat_id,
            metadata={
                "routing_provider": routing.provider,
                "routing_model": routing.model,
                "subtask_id": subtask.id,
                "orchestrator_trace_id": trace.id,
            },
        )

        event_id = self.tracer.record_agent_start(trace.id, subtask.agent_key)

        try:
            result = await self.agent_manager.run_ephemeral_with_system_agent(request)

            self.tracer.record_agent_end(
                trace.id,
                subtask.agent_key,
                success=result.success,
                tokens=result.token_used,
                cost=estimate_cost(routing.provider, routing.model, result.token_used, 0),
                parent_event_id=event_id,
            )

            self.tracer.record_model_call(
                trace.id,
                provider=routing.provider,
                model=routing.model,
                tokens=result.token_used,
                duration_ms=result.duration_ms,
                success=result.success,
            )

            return {
                "output": result.output,
                "agent_key": subtask.agent_key,
                "tokens_used": result.token_used,
                "cost": estimate_cost(routing.provider, routing.model, result.token_used, 0),
                "citations": result.citations,
            }
        except Exception as exc:
            self.tracer.record_agent_end(
                trace.id, subtask.agent_key, success=False, error=str(exc),
            )
            raise

    def _select_agent_for_task(
        self,
        task_type: TaskType | str,
        user_input: str,
    ) -> str:
        """Select the most appropriate agent for a task type."""
        _TASK_AGENT_MAP: dict[str, str] = {
            "chat": "chat",
            "reasoning": "chat",
            "document_analysis": "document",
            "summarization": "document",
            "extraction": "document",
            "classification": "analytics",
            "search": "search",
            "analytics": "analytics",
            "forecasting": "analytics",
            "report_generation": "analytics",
            "planning": "planning",
            "code": "chat",
            "tool_execution": "chat",
            "agent_coordination": "planning",
            "embedding": "search",
            "multimodal": "document",
        }

        if isinstance(task_type, TaskType):
            key = task_type.value
        else:
            key = str(task_type)

        return _TASK_AGENT_MAP.get(key, "chat")

    def get_catalog(self) -> list[dict[str, Any]]:
        """Get the agent catalog."""
        return self.agent_manager.catalog()

    def get_model_routing(
        self,
        task_type: str | None = None,
        user_input: str = "",
    ) -> dict[str, Any]:
        """Get model routing decision for a given task."""
        routing = self.model_router.route(
            task_type=task_type,
            user_input=user_input,
        )
        return {
            "provider": routing.provider,
            "model": routing.model,
            "temperature": routing.temperature,
            "max_tokens": routing.max_tokens,
            "reasoning": routing.reasoning,
            "alternatives": routing.alternatives,
        }
