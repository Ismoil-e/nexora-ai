"""Celery worker for long-running / background workflow executions."""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger("nexora.workflow_worker")


async def _execute(payload: dict) -> dict:
    from app.core.database import async_session_factory
    from app.workflows.bootstrap import ensure_workflows_bootstrapped
    from app.workflows.contracts.types import WorkflowIdentity, WorkflowRunRequest
    from app.workflows.core.executor import WorkflowExecutor
    from app.repositories.workflow_repo import WorkflowExecutionRepository, WorkflowRepository

    ensure_workflows_bootstrapped()

    async with async_session_factory() as db:
        workflow_repo = WorkflowRepository(db)
        execution_repo = WorkflowExecutionRepository(db)
        workflow = await workflow_repo.get_with_steps(uuid.UUID(payload["workflow_id"]))
        execution = await execution_repo.get(uuid.UUID(payload["execution_id"]))
        if not workflow or not execution:
            return {"success": False, "error": "workflow_or_execution_not_found"}

        request = WorkflowRunRequest(
            workflow_id=workflow.id,
            identity=WorkflowIdentity(
                user_id=uuid.UUID(payload["user_id"]) if payload.get("user_id") else None,
                company_id=uuid.UUID(payload["company_id"]),
            ),
            trigger_type=payload.get("trigger_type") or "api",
            payload=payload.get("payload") or {},
            force_sync=True,
        )
        executor = WorkflowExecutor(db)
        result = await executor.run(
            workflow,
            request,
            execution=execution,
            resume_from_step=payload.get("resume_from_step"),
        )
        await db.commit()
        return result.to_dict()


@celery_app.task(name="workflows.run_workflow_job", bind=True, max_retries=2)
def run_workflow_job(self, **payload):
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = asyncio.run(_execute(payload))
            else:
                result = loop.run_until_complete(_execute(payload))
        except RuntimeError:
            result = asyncio.run(_execute(payload))
        logger.info("workflow_job_completed execution_id=%s", payload.get("execution_id"))
        return result
    except Exception as exc:
        logger.exception("workflow_job_failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)
