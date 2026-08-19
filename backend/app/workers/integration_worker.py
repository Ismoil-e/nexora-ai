import asyncio
import uuid
from typing import Any

from app.workers.celery_app import celery_app


@celery_app.task(name="sync_integration_task")
def sync_integration_task(integration_id: str, company_id: str, resource_type: str):
    """Background task for heavy synchronization jobs (e.g. Google Drive, OneDrive, Email ingestion)."""
    from app.core.database import async_session_factory
    from app.services.integration_service import IntegrationService

    async def _run():
        async with async_session_factory() as db:
            svc = IntegrationService(db)
            return await svc.execute_action(
                integration_id=uuid.UUID(integration_id),
                company_id=uuid.UUID(company_id),
                action_name=f"fetch_{resource_type}",
                triggered_by_type="celery_worker",
            )

    return asyncio.run(_run())


@celery_app.task(name="deliver_outbound_webhook_task", bind=True, max_retries=3, default_retry_delay=10)
def deliver_outbound_webhook_task(self, target_url: str, secret: str | None, event_dict: dict[str, Any]):
    """Background task for dispatching outbound webhooks with exponential backoff retries."""
    from app.integrations.contracts.types import NexoraEvent
    from app.integrations.core.webhook_manager import webhook_manager

    async def _run():
        event = NexoraEvent(**event_dict)
        return await webhook_manager.deliver_outbound_webhook(target_url, secret, event)

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(name="health_check_all_integrations_task")
def health_check_all_integrations_task():
    """Periodic health check task across all tenant integrations."""
    from app.core.database import async_session_factory
    from app.repositories.integration_repo import IntegrationRepository
    from app.services.integration_service import IntegrationService
    from sqlalchemy import select
    from app.models.integration import Integration

    async def _run():
        async with async_session_factory() as db:
            result = await db.execute(select(Integration).where(Integration.deleted_at.is_(None)))
            integrations = result.scalars().all()
            svc = IntegrationService(db)
            for item in integrations:
                try:
                    await svc.test_connection(item.id, item.company_id)
                except Exception:
                    pass

    return asyncio.run(_run())
