import uuid
from typing import Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import (
    Integration,
    IntegrationCredential,
    WebhookSubscription,
    IntegrationEvent,
    IntegrationExecution,
    IntegrationHealth,
)
from app.repositories.base import BaseRepository


class IntegrationRepository(BaseRepository[Integration]):
    def __init__(self, db: AsyncSession):
        super().__init__(Integration, db)

    async def get_by_company(self, company_id: uuid.UUID, page: int = 1, page_size: int = 50) -> list[Integration]:
        query = select(Integration).where(
            Integration.company_id == company_id,
            Integration.deleted_at.is_(None),
        ).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_slug(self, company_id: uuid.UUID, slug: str) -> Integration | None:
        query = select(Integration).where(
            Integration.company_id == company_id,
            Integration.slug == slug,
            Integration.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_credential(self, integration_id: uuid.UUID) -> IntegrationCredential | None:
        query = select(IntegrationCredential).where(
            IntegrationCredential.integration_id == integration_id,
            IntegrationCredential.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def save_credential(
        self,
        integration_id: uuid.UUID,
        company_id: uuid.UUID,
        auth_type: str,
        encrypted_data: str,
        scopes: str | None = None,
    ) -> IntegrationCredential:
        existing = await self.get_credential(integration_id)
        if existing:
            existing.auth_type = auth_type
            existing.encrypted_data = encrypted_data
            if scopes:
                existing.scopes = scopes
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        else:
            cred = IntegrationCredential(
                integration_id=integration_id,
                company_id=company_id,
                auth_type=auth_type,
                encrypted_data=encrypted_data,
                scopes=scopes,
            )
            self.db.add(cred)
            await self.db.commit()
            await self.db.refresh(cred)
            return cred

    async def log_event(
        self,
        integration_id: uuid.UUID,
        company_id: uuid.UUID,
        event_id: str,
        event_type: str,
        direction: str,
        status: str,
        payload_str: str,
        normalized_str: str | None = None,
        error_message: str | None = None,
    ) -> IntegrationEvent:
        event = IntegrationEvent(
            integration_id=integration_id,
            company_id=company_id,
            event_id=event_id,
            event_type=event_type,
            direction=direction,
            status=status,
            payload=payload_str,
            normalized_payload=normalized_str,
            error_message=error_message,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def log_execution(
        self,
        integration_id: uuid.UUID,
        company_id: uuid.UUID,
        action_name: str,
        status: str,
        params_str: str | None = None,
        response_str: str | None = None,
        error_details: str | None = None,
        duration_ms: int = 0,
        triggered_by_type: str = "system",
        triggered_by_id: uuid.UUID | None = None,
    ) -> IntegrationExecution:
        execution = IntegrationExecution(
            integration_id=integration_id,
            company_id=company_id,
            action_name=action_name,
            status=status,
            request_params=params_str,
            response_data=response_str,
            error_details=error_details,
            duration_ms=duration_ms,
            triggered_by_type=triggered_by_type,
            triggered_by_id=triggered_by_id,
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def update_health(
        self,
        integration_id: uuid.UUID,
        company_id: uuid.UUID,
        status: str,
        latency_ms: int,
    ) -> IntegrationHealth:
        query = select(IntegrationHealth).where(IntegrationHealth.integration_id == integration_id)
        result = await self.db.execute(query)
        record = result.scalar_one_or_none()
        if not record:
            record = IntegrationHealth(
                integration_id=integration_id,
                company_id=company_id,
                status=status,
                latency_ms=latency_ms,
            )
            self.db.add(record)
        else:
            record.status = status
            record.latency_ms = latency_ms

        await self.db.commit()
        await self.db.refresh(record)
        return record
