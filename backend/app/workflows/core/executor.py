"""Workflow execution engine — runs the automation pipeline."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import DomainEvent, event_bus
from app.models.workflow import (
    Workflow,
    WorkflowApproval,
    WorkflowExecution,
    WorkflowHistory,
    WorkflowLog,
    WorkflowStep,
)
from app.workflows.contracts.types import (
    ActionContext,
    ActionResult,
    ExecutionStatus,
    WorkflowRunRequest,
    WorkflowRunResult,
)
from app.workflows.core.builder import WorkflowValidator
from app.workflows.core.condition import ApprovalEngine, ConditionEngine, RetryEngine
from app.workflows.core.registry import action_registry
from app.utils.exceptions import AppException, NotFoundException, ValidationException


class WorkflowExecutor:
    """Executes workflow steps with conditions, retries, approvals, and audit logs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.validator = WorkflowValidator()
        self.conditions = ConditionEngine()
        self.approvals = ApprovalEngine()
        self.retries = RetryEngine()

    def build_services(self) -> dict[str, Any]:
        from app.cognitive.services.engines import MemoryEngine
        from app.services.agent_service import AgentService
        from app.services.ai_service import AIService
        from app.services.document_intelligence_service import DocumentIntelligenceService
        from app.services.document_service import DocumentService
        from app.services.notification_service import NotificationService

        return {
            "db": self.db,
            "document_service": DocumentService(self.db),
            "document_intelligence_service": DocumentIntelligenceService(self.db),
            "notification_service": NotificationService(self.db),
            "ai_service": AIService(self.db),
            "agent_service": AgentService(self.db),
            "memory_engine": MemoryEngine(self.db),
            "plugin_registry": {},
        }

    async def _log(
        self,
        execution: WorkflowExecution,
        stage: str,
        message: str,
        *,
        level: str = "info",
        details: dict | None = None,
    ) -> None:
        self.db.add(
            WorkflowLog(
                execution_id=execution.id,
                company_id=execution.company_id,
                level=level,
                stage=stage,
                message=message,
                details=json.dumps(details, ensure_ascii=False) if details else None,
            )
        )
        await self.db.flush()

    async def create_execution(
        self,
        workflow: Workflow,
        request: WorkflowRunRequest,
    ) -> WorkflowExecution:
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            company_id=workflow.company_id,
            triggered_by=request.identity.user_id if request.identity else None,
            trigger_type=request.trigger_type,
            status=ExecutionStatus.PENDING.value,
            input_payload=json.dumps(request.payload, ensure_ascii=False),
            current_step_order=0,
        )
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)
        return execution

    async def run(
        self,
        workflow: Workflow,
        request: WorkflowRunRequest,
        *,
        execution: WorkflowExecution | None = None,
        resume_from_step: int | None = None,
    ) -> WorkflowRunResult:
        self.validator.validate_for_execution(workflow.status, len(workflow.steps or []))

        if request.identity and request.identity.company_id != workflow.company_id:
            raise AppException(status_code=403, error="Forbidden", detail="Tenant isolation buzildi")

        started = time.perf_counter()
        execution = execution or await self.create_execution(workflow, request)

        # Async offload for long/background workflows
        if (request.async_mode or workflow.workflow_type in {"long_running", "background"}) and not request.force_sync:
            from app.workers.workflow_worker import run_workflow_job

            task = run_workflow_job.delay(
                execution_id=str(execution.id),
                workflow_id=str(workflow.id),
                company_id=str(workflow.company_id),
                user_id=str(request.identity.user_id) if request.identity and request.identity.user_id else None,
                payload=request.payload,
                trigger_type=request.trigger_type,
                resume_from_step=resume_from_step,
            )
            execution.status = ExecutionStatus.RUNNING.value
            execution.celery_task_id = task.id
            await self.db.flush()
            await self._log(execution, "queued", "Workflow Celery navbatiga qo'yildi", details={"task_id": task.id})
            return WorkflowRunResult(
                success=True,
                execution_id=execution.id,
                status=ExecutionStatus.RUNNING.value,
                celery_task_id=task.id,
            )

        execution.status = ExecutionStatus.RUNNING.value
        execution.started_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self._log(execution, "start", "Workflow execution boshlandi")

        shared_state: dict[str, Any] = {
            "payload": request.payload,
            "workflow_slug": workflow.slug,
            "steps": {},
        }
        services = self.build_services()
        steps = sorted(workflow.steps or [], key=lambda s: s.step_order)
        start_order = resume_from_step or 0
        completed = 0

        try:
            for step in steps:
                if step.step_order < start_order:
                    continue

                execution.current_step_order = step.step_order
                await self.db.flush()

                condition = json.loads(step.condition_json) if step.condition_json else None
                if not self.conditions.evaluate(condition, shared_state):
                    await self._record_history(
                        execution,
                        workflow,
                        step,
                        status="skipped",
                        input_data={"condition": condition},
                        output_data={"skipped": True},
                    )
                    await self._log(execution, "condition", f"Step {step.step_order} skip (condition false)")
                    continue

                config = json.loads(step.config_json) if step.config_json else {}
                action = action_registry.require(step.action_key)
                attempt = 1
                max_attempts = max(step.retry_limit, 0) + 1
                last_error = None
                result: ActionResult | None = None

                while attempt <= max_attempts:
                    ctx = ActionContext(
                        company_id=workflow.company_id,
                        user_id=request.identity.user_id if request.identity else None,
                        execution_id=execution.id,
                        workflow_id=workflow.id,
                        step_order=step.step_order,
                        action_key=step.action_key,
                        config=config,
                        payload=request.payload,
                        shared_state=shared_state,
                        services=services,
                    )
                    step_started = time.perf_counter()
                    try:
                        await action.validate(ctx)
                        result = await action.execute(ctx)
                        duration_ms = int((time.perf_counter() - step_started) * 1000)
                        await self._record_history(
                            execution,
                            workflow,
                            step,
                            status="completed" if result.success else "failed",
                            input_data={"config": config, "payload": request.payload},
                            output_data=result.to_dict(),
                            duration_ms=duration_ms,
                            attempt=attempt,
                            error=None if result.success else result.message,
                        )
                        if result.success:
                            shared_state["steps"][str(step.step_order)] = result.output
                            shared_state["last_output"] = result.output
                            completed += 1
                            await self._log(
                                execution,
                                "step",
                                f"Step {step.step_order} ({step.action_key}) completed",
                                details=result.output,
                            )
                            break

                        last_error = result.message or "Action failed"
                    except Exception as exc:
                        last_error = str(exc)
                        duration_ms = int((time.perf_counter() - step_started) * 1000)
                        await self._record_history(
                            execution,
                            workflow,
                            step,
                            status="failed",
                            input_data={"config": config},
                            output_data={},
                            duration_ms=duration_ms,
                            attempt=attempt,
                            error=last_error,
                        )

                    if self.retries.should_retry(
                        attempt=attempt,
                        retry_limit=step.retry_limit,
                        on_failure=step.on_failure,
                    ):
                        attempt += 1
                        execution.retry_count += 1
                        await self._log(execution, "retry", f"Retry step {step.step_order} attempt={attempt}")
                        continue

                    if step.on_failure == "continue" or step.is_optional:
                        await self._log(
                            execution,
                            "continue",
                            f"Step {step.step_order} failed but continuing",
                            level="warning",
                            details={"error": last_error},
                        )
                        result = ActionResult(success=False, message=last_error or "")
                        break

                    raise RuntimeError(last_error or f"Step {step.step_order} failed")

                if result and result.requires_approval:
                    approval = WorkflowApproval(
                        execution_id=execution.id,
                        workflow_id=workflow.id,
                        company_id=workflow.company_id,
                        requested_from=uuid.UUID(str(result.output["requested_from"]))
                        if result.output.get("requested_from")
                        else None,
                        status="pending",
                        reason=result.output.get("reason"),
                    )
                    self.db.add(approval)
                    execution.status = ExecutionStatus.WAITING_APPROVAL.value
                    await self.db.flush()
                    await self._log(execution, "approval", "Approval kutulmoqda")
                    await event_bus.publish(
                        DomainEvent(
                            event_type="workflow.waiting_approval",
                            company_id=workflow.company_id,
                            user_id=request.identity.user_id if request.identity else None,
                            payload={
                                "resource_type": "workflow_execution",
                                "resource_id": str(execution.id),
                            },
                        )
                    )
                    return WorkflowRunResult(
                        success=True,
                        execution_id=execution.id,
                        status=ExecutionStatus.WAITING_APPROVAL.value,
                        output=shared_state,
                        steps_completed=completed,
                    )

                if result and result.should_stop and not result.success:
                    raise RuntimeError(result.message or "Workflow stopped by action")

            duration_ms = int((time.perf_counter() - started) * 1000)
            execution.status = ExecutionStatus.COMPLETED.value
            execution.finished_at = datetime.now(timezone.utc)
            execution.duration_ms = duration_ms
            execution.output_payload = json.dumps(shared_state, ensure_ascii=False, default=str)
            await self.db.flush()
            await self._log(execution, "complete", "Workflow muvaffaqiyatli yakunlandi")
            await event_bus.publish(
                DomainEvent(
                    event_type="workflow.completed",
                    company_id=workflow.company_id,
                    user_id=request.identity.user_id if request.identity else None,
                    payload={
                        "resource_type": "workflow_execution",
                        "resource_id": str(execution.id),
                        "steps_completed": completed,
                    },
                )
            )
            return WorkflowRunResult(
                success=True,
                execution_id=execution.id,
                status=ExecutionStatus.COMPLETED.value,
                output=shared_state,
                steps_completed=completed,
            )

        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            execution.status = ExecutionStatus.FAILED.value
            execution.error_message = str(exc)
            execution.finished_at = datetime.now(timezone.utc)
            execution.duration_ms = duration_ms
            await self.db.flush()
            await self._log(execution, "failed", str(exc), level="error")
            await event_bus.publish(
                DomainEvent(
                    event_type="workflow.failed",
                    company_id=workflow.company_id,
                    user_id=request.identity.user_id if request.identity else None,
                    payload={
                        "resource_type": "workflow_execution",
                        "resource_id": str(execution.id),
                        "error": str(exc),
                    },
                )
            )
            return WorkflowRunResult(
                success=False,
                execution_id=execution.id,
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                steps_completed=completed,
            )

    async def _record_history(
        self,
        execution: WorkflowExecution,
        workflow: Workflow,
        step: WorkflowStep,
        *,
        status: str,
        input_data: dict,
        output_data: dict,
        duration_ms: int | None = None,
        attempt: int = 1,
        error: str | None = None,
    ) -> None:
        self.db.add(
            WorkflowHistory(
                execution_id=execution.id,
                workflow_id=workflow.id,
                company_id=workflow.company_id,
                step_id=step.id,
                step_order=step.step_order,
                action_key=step.action_key,
                status=status,
                input_json=json.dumps(input_data, ensure_ascii=False, default=str),
                output_json=json.dumps(output_data, ensure_ascii=False, default=str),
                error_message=error,
                duration_ms=duration_ms,
                attempt=attempt,
            )
        )
        await self.db.flush()
