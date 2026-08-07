"""Celery worker for long-running agent framework jobs."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger("nexora.agent_worker")


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _execute_agent_job(payload: dict) -> dict:
    from app.agents.bootstrap import ensure_agents_bootstrapped
    from app.agents.contracts.types import AgentIdentity, AgentRequest
    from app.agents.core.manager import AgentManager
    from app.core.database import async_session_factory

    ensure_agents_bootstrapped()

    async with async_session_factory() as db:
        manager = AgentManager(db)
        identity = AgentIdentity(
            user_id=uuid.UUID(payload["user_id"]),
            company_id=uuid.UUID(payload["company_id"]),
            permissions=list(payload.get("permissions") or []),
            roles=list(payload.get("roles") or []),
        )
        request = AgentRequest(
            agent_key=payload["agent_key"],
            input=payload["input_text"],
            identity=identity,
            chat_id=uuid.UUID(payload["chat_id"]) if payload.get("chat_id") else None,
            document_ids=[uuid.UUID(d) for d in payload.get("document_ids") or []],
            metadata=payload.get("metadata") or {},
            async_mode=False,  # already inside async worker
        )
        agent_id = uuid.UUID(payload["db_agent_id"]) if payload.get("db_agent_id") else None
        result = await manager.run(request, agent_id=agent_id)
        await db.commit()
        return result.to_dict()


@celery_app.task(name="agents.run_agent_job", bind=True, max_retries=2)
def run_agent_job(self, **payload):
    """Background execution for heavy agent workloads."""
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Celery prefork typically has no running loop
                result = asyncio.run(_execute_agent_job(payload))
            else:
                result = loop.run_until_complete(_execute_agent_job(payload))
        except RuntimeError:
            result = asyncio.run(_execute_agent_job(payload))
        logger.info("agent_job_completed", extra={"agent_key": payload.get("agent_key")})
        return result
    except Exception as exc:
        logger.exception("agent_job_failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)
