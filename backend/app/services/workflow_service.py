"""Domain service for Workflow Automation Engine."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowSchedule, WorkflowStep, WorkflowTrigger
from app.repositories.workflow_repo import (
    WorkflowApprovalRepository,
    WorkflowExecutionRepository,
    WorkflowLogRepository,
    WorkflowRepository,
    WorkflowScheduleRepository,
    WorkflowStepRepository,
    WorkflowTriggerRepository,
)
from app.utils.exceptions import AppException, NotFoundException, ValidationException
from app.workflows.bootstrap import ensure_workflows_bootstrapped
from app.workflows.contracts.types import (
    ExecutionStatus,
    WorkflowIdentity,
    WorkflowRunRequest,
    WorkflowStatus,
)
from app.workflows.core.builder import WorkflowBuilder, WorkflowValidator
from app.workflows.core.executor import WorkflowExecutor
from app.workflows.core.registry import action_registry, trigger_registry, workflow_registry
from app.workflows.core.scheduler import WorkflowScheduler


class WorkflowService:
    """CRUD + execute/pause/resume for tenant workflows."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        ensure_workflows_bootstrapped()
        self.workflow_repo = WorkflowRepository(db)
        self.step_repo = WorkflowStepRepository(db)
        self.trigger_repo = WorkflowTriggerRepository(db)
        self.schedule_repo = WorkflowScheduleRepository(db)
        self.execution_repo = WorkflowExecutionRepository(db)
        self.log_repo = WorkflowLogRepository(db)
        self.approval_repo = WorkflowApprovalRepository(db)
        self.builder = WorkflowBuilder()
        self.validator = WorkflowValidator()
        self.executor = WorkflowExecutor(db)
        self.scheduler = WorkflowScheduler()

    def catalog(self) -> dict[str, Any]:
        return {
            "actions": action_registry.list_catalog(),
            "triggers": trigger_registry.list_types(),
            "templates": workflow_registry.list_templates(),
        }

    async def create_workflow(
        self,
        *,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None,
        data: dict[str, Any],
    ) -> Workflow:
        definition = self.builder.build(
            name=data["name"],
            slug=data["slug"],
            workflow_type=data.get("workflow_type") or "manual",
            description=data.get("description"),
            steps=data.get("steps") or [],
            triggers=data.get("triggers"),
            requires_approval=bool(data.get("requires_approval")),
            max_retries=int(data.get("max_retries") or 3),
            timeout_seconds=int(data.get("timeout_seconds") or 3600),
            tags=data.get("tags"),
            definition=data.get("definition"),
        )
        self.validator.validate_definition(definition)

        existing = await self.workflow_repo.get_by_slug(company_id, definition["slug"])
        if existing:
            raise ValidationException(detail=f"Slug band: {definition['slug']}")

        workflow = await self.workflow_repo.create(
            company_id=company_id,
            created_by=user_id,
            name=definition["name"],
            slug=definition["slug"],
            description=definition.get("description"),
            workflow_type=definition["workflow_type"],
            status=data.get("status") or WorkflowStatus.DRAFT.value,
            version=data.get("version") or "1.0.0",
            definition_json=self.builder.dumps(definition),
            is_system=bool(data.get("is_system")),
            requires_approval=definition["requires_approval"],
            max_retries=definition["max_retries"],
            timeout_seconds=definition["timeout_seconds"],
            tags=",".join(definition.get("tags") or []),
        )

        for step in definition["steps"]:
            await self.step_repo.create(
                workflow_id=workflow.id,
                company_id=company_id,
                name=step["name"],
                step_order=step["step_order"],
                action_key=step["action_key"],
                config_json=json.dumps(step.get("config") or {}, ensure_ascii=False),
                condition_json=json.dumps(step["condition"], ensure_ascii=False) if step.get("condition") else None,
                on_failure=step.get("on_failure") or "stop",
                retry_limit=int(step.get("retry_limit") or 0),
                is_optional=bool(step.get("is_optional")),
                timeout_seconds=step.get("timeout_seconds"),
            )

        for trigger in definition["triggers"]:
            await self.trigger_repo.create(
                workflow_id=workflow.id,
                company_id=company_id,
                trigger_type=trigger["trigger_type"],
                config_json=json.dumps(trigger.get("config") or {}, ensure_ascii=False),
                is_active=bool(trigger.get("is_active", True)),
            )

        schedule = data.get("schedule")
        if schedule:
            next_run = self.scheduler.compute_next_run(
                cron_expression=schedule.get("cron_expression"),
                interval_seconds=schedule.get("interval_seconds"),
            )
            await self.schedule_repo.create(
                workflow_id=workflow.id,
                company_id=company_id,
                cron_expression=schedule.get("cron_expression"),
                interval_seconds=schedule.get("interval_seconds"),
                timezone=schedule.get("timezone") or "Asia/Tashkent",
                next_run_at=next_run,
                is_active=True,
            )

        return await self.workflow_repo.get_with_steps(workflow.id)

    async def install_template(
        self,
        *,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None,
        slug: str,
        activate: bool = True,
    ) -> Workflow:
        template = workflow_registry.get_template(slug)
        if not template:
            raise NotFoundException(resource="WorkflowTemplate", detail=f"Template '{slug}' topilmadi")
        definition = self.builder.from_template(template)
        payload = {
            **definition,
            "status": WorkflowStatus.ACTIVE.value if activate else WorkflowStatus.DRAFT.value,
            "is_system": True,
        }
        existing = await self.workflow_repo.get_by_slug(company_id, slug)
        if existing:
            return existing
        return await self.create_workflow(company_id=company_id, user_id=user_id, data=payload)

    async def update_workflow(
        self,
        workflow_id: uuid.UUID,
        company_id: uuid.UUID,
        data: dict[str, Any],
    ) -> Workflow:
        workflow = await self.workflow_repo.get_with_steps(workflow_id)
        if not workflow or workflow.company_id != company_id:
            raise NotFoundException(resource="Workflow")

        update_fields = {
            k: v
            for k, v in data.items()
            if k in {
                "name",
                "description",
                "workflow_type",
                "status",
                "version",
                "requires_approval",
                "max_retries",
                "timeout_seconds",
                "tags",
            }
            and v is not None
        }
        if "tags" in update_fields and isinstance(update_fields["tags"], list):
            update_fields["tags"] = ",".join(update_fields["tags"])

        if data.get("steps") is not None:
            definition = self.builder.build(
                name=update_fields.get("name") or workflow.name,
                slug=workflow.slug,
                workflow_type=update_fields.get("workflow_type") or workflow.workflow_type,
                description=update_fields.get("description") or workflow.description,
                steps=data["steps"],
                triggers=[{"trigger_type": t.trigger_type, "config": json.loads(t.config_json or "{}")} for t in (workflow.triggers or [])],
                requires_approval=update_fields.get("requires_approval", workflow.requires_approval),
                max_retries=update_fields.get("max_retries", workflow.max_retries),
                timeout_seconds=update_fields.get("timeout_seconds", workflow.timeout_seconds),
            )
            self.validator.validate_definition(definition)
            # Replace steps
            for step in list(workflow.steps or []):
                await self.step_repo.soft_delete(step.id)
            for step in definition["steps"]:
                await self.step_repo.create(
                    workflow_id=workflow.id,
                    company_id=company_id,
                    name=step["name"],
                    step_order=step["step_order"],
                    action_key=step["action_key"],
                    config_json=json.dumps(step.get("config") or {}, ensure_ascii=False),
                    condition_json=json.dumps(step["condition"], ensure_ascii=False) if step.get("condition") else None,
                    on_failure=step.get("on_failure") or "stop",
                    retry_limit=int(step.get("retry_limit") or 0),
                    is_optional=bool(step.get("is_optional")),
                    timeout_seconds=step.get("timeout_seconds"),
                )
            update_fields["definition_json"] = self.builder.dumps(definition)

        if update_fields:
            await self.workflow_repo.update(workflow_id, **update_fields)
        return await self.workflow_repo.get_with_steps(workflow_id)

    async def delete_workflow(self, workflow_id: uuid.UUID, company_id: uuid.UUID) -> bool:
        workflow = await self.workflow_repo.get(workflow_id)
        if not workflow or workflow.company_id != company_id:
            return False
        return await self.workflow_repo.soft_delete(workflow_id)

    async def list_workflows(self, company_id: uuid.UUID, page: int = 1, page_size: int = 20, status: str | None = None):
        items, total = await self.workflow_repo.list_by_company(company_id, page=page, page_size=page_size, status=status)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_workflow(w) for w in items],
        }

    async def get_workflow(self, workflow_id: uuid.UUID, company_id: uuid.UUID) -> dict:
        workflow = await self.workflow_repo.get_with_steps(workflow_id)
        if not workflow or workflow.company_id != company_id:
            raise NotFoundException(resource="Workflow")
        return self._serialize_workflow(workflow, detailed=True)

    async def execute(
        self,
        *,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None,
        workflow_id: uuid.UUID | None = None,
        workflow_slug: str | None = None,
        payload: dict | None = None,
        trigger_type: str = "user_request",
        async_mode: bool = False,
        permissions: list[str] | None = None,
    ) -> dict:
        if workflow_id:
            workflow = await self.workflow_repo.get_with_steps(workflow_id)
        elif workflow_slug:
            workflow = await self.workflow_repo.get_by_slug(company_id, workflow_slug)
        else:
            raise ValidationException(detail="workflow_id yoki workflow_slug talab qilinadi")

        if not workflow or workflow.company_id != company_id:
            raise NotFoundException(resource="Workflow")

        if workflow.status == WorkflowStatus.PAUSED.value:
            raise ValidationException(detail="Workflow paused holatida")

        # Soft activate draft on explicit execute if desired? Keep strict.
        if workflow.status == WorkflowStatus.DRAFT.value:
            raise ValidationException(detail="Draft workflowni avval active qiling")

        request = WorkflowRunRequest(
            workflow_id=workflow.id,
            workflow_slug=workflow.slug,
            identity=WorkflowIdentity(
                user_id=user_id,
                company_id=company_id,
                permissions=permissions or [],
            ),
            trigger_type=trigger_type,
            payload=payload or {},
            async_mode=async_mode or workflow.workflow_type in {"long_running", "background"},
        )
        result = await self.executor.run(workflow, request)
        return result.to_dict()

    async def pause(self, execution_id: uuid.UUID, company_id: uuid.UUID) -> dict:
        execution = await self.execution_repo.get(execution_id)
        if not execution or execution.company_id != company_id:
            raise NotFoundException(resource="WorkflowExecution")
        if execution.status not in {ExecutionStatus.RUNNING.value, ExecutionStatus.PENDING.value}:
            raise ValidationException(detail="Faqat running/pending execution pause qilinadi")
        await self.execution_repo.update(execution_id, status=ExecutionStatus.PAUSED.value)
        return {"execution_id": str(execution_id), "status": ExecutionStatus.PAUSED.value}

    async def resume(
        self,
        execution_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        execution = await self.execution_repo.get_with_details(execution_id)
        if not execution or execution.company_id != company_id:
            raise NotFoundException(resource="WorkflowExecution")
        if execution.status not in {
            ExecutionStatus.PAUSED.value,
            ExecutionStatus.WAITING_APPROVAL.value,
        }:
            raise ValidationException(detail="Execution resume qilinmaydi")

        workflow = await self.workflow_repo.get_with_steps(execution.workflow_id)
        if not workflow:
            raise NotFoundException(resource="Workflow")

        # Mark approvals approved when resuming from waiting_approval
        if execution.status == ExecutionStatus.WAITING_APPROVAL.value:
            for approval in execution.approvals or []:
                if approval.status == "pending":
                    await self.approval_repo.update(
                        approval.id,
                        status="approved",
                        decided_by=user_id,
                        decided_at=datetime.now(timezone.utc),
                    )

        request = WorkflowRunRequest(
            workflow_id=workflow.id,
            identity=WorkflowIdentity(user_id=user_id, company_id=company_id),
            trigger_type=execution.trigger_type,
            payload=json.loads(execution.input_payload or "{}"),
            force_sync=True,
        )
        resume_from = int(execution.current_step_order or 0) + 1
        result = await self.executor.run(
            workflow,
            request,
            execution=execution,
            resume_from_step=resume_from,
        )
        return result.to_dict()

    async def history(
        self,
        workflow_id: uuid.UUID,
        company_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        workflow = await self.workflow_repo.get(workflow_id)
        if not workflow or workflow.company_id != company_id:
            raise NotFoundException(resource="Workflow")
        items, total = await self.execution_repo.list_by_workflow(workflow_id, company_id, page=page, page_size=page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_execution(e) for e in items],
        }

    async def status(self, execution_id: uuid.UUID, company_id: uuid.UUID) -> dict:
        execution = await self.execution_repo.get(execution_id)
        if not execution or execution.company_id != company_id:
            raise NotFoundException(resource="WorkflowExecution")
        return self._serialize_execution(execution)

    async def logs(self, execution_id: uuid.UUID, company_id: uuid.UUID) -> dict:
        execution = await self.execution_repo.get(execution_id)
        if not execution or execution.company_id != company_id:
            raise NotFoundException(resource="WorkflowExecution")
        logs = await self.log_repo.list_by_execution(execution_id)
        return {
            "execution_id": str(execution_id),
            "items": [
                {
                    "id": str(log.id),
                    "level": log.level,
                    "stage": log.stage,
                    "message": log.message,
                    "details": log.details,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
        }

    def _serialize_workflow(self, workflow: Workflow, detailed: bool = False) -> dict:
        data = {
            "id": str(workflow.id),
            "name": workflow.name,
            "slug": workflow.slug,
            "description": workflow.description,
            "workflow_type": workflow.workflow_type,
            "status": workflow.status,
            "version": workflow.version,
            "requires_approval": workflow.requires_approval,
            "is_system": workflow.is_system,
            "created_at": workflow.created_at.isoformat(),
        }
        if detailed:
            data["steps"] = [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "step_order": s.step_order,
                    "action_key": s.action_key,
                    "config": json.loads(s.config_json or "{}"),
                    "on_failure": s.on_failure,
                    "retry_limit": s.retry_limit,
                }
                for s in (workflow.steps or [])
            ]
            data["triggers"] = [
                {
                    "id": str(t.id),
                    "trigger_type": t.trigger_type,
                    "is_active": t.is_active,
                    "config": json.loads(t.config_json or "{}"),
                }
                for t in (workflow.triggers or [])
            ]
        return data

    def _serialize_execution(self, execution) -> dict:
        return {
            "id": str(execution.id),
            "workflow_id": str(execution.workflow_id),
            "status": execution.status,
            "trigger_type": execution.trigger_type,
            "current_step_order": execution.current_step_order,
            "error_message": execution.error_message,
            "celery_task_id": execution.celery_task_id,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
            "duration_ms": execution.duration_ms,
            "created_at": execution.created_at.isoformat(),
        }
