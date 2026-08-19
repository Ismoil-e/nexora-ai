import uuid
from typing import Any
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.integrations.core.registry import integration_registry
from app.models.user import User
from app.schemas.integration import (
    IntegrationCreateSchema,
    IntegrationExecuteSchema,
    IntegrationMetaResponseSchema,
    IntegrationResponseSchema,
)
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/integrations", tags=["Enterprise Integration Hub"])


@router.get("/catalog", response_model=list[IntegrationMetaResponseSchema])
async def list_integration_catalog(
    current_user: User = Depends(get_current_user),
):
    """Lists all available integration types and metadata supported by Nexora Integration Hub."""
    return integration_registry.list_all()


@router.get("", response_model=list[IntegrationResponseSchema])
async def list_tenant_integrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 50,
):
    """Lists configured integrations for the current tenant company."""
    service = IntegrationService(db)
    return await service.list_integrations(current_user.company_id, page=page, page_size=page_size)


@router.post("", response_model=IntegrationResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_integration(
    payload: IntegrationCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Connects a new external integration for the tenant."""
    service = IntegrationService(db)
    return await service.create_integration(
        company_id=current_user.company_id,
        name=payload.name,
        integration_type=payload.integration_type,
        category=payload.category,
        config=payload.config,
        credentials=payload.credentials,
        auth_type=payload.auth_type,
    )


@router.get("/{integration_id}", response_model=IntegrationResponseSchema)
async def get_integration_details(
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves single integration details by ID."""
    service = IntegrationService(db)
    return await service.get_integration(integration_id, current_user.company_id)


@router.post("/{integration_id}/test")
async def test_integration_connection(
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Performs real-time health and credential check on an integration."""
    service = IntegrationService(db)
    return await service.test_connection(integration_id, current_user.company_id)


@router.post("/{integration_id}/execute")
async def execute_integration_action(
    integration_id: uuid.UUID,
    payload: IntegrationExecuteSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes an action directly through the Integration Hub."""
    service = IntegrationService(db)
    res = await service.execute_action(
        integration_id=integration_id,
        company_id=current_user.company_id,
        action_name=payload.action_name,
        params=payload.params,
        data=payload.data,
        triggered_by_type="user",
        triggered_by_id=current_user.id,
    )
    return res.model_dump()


@router.post("/webhooks/incoming/{vendor}/{integration_id}")
async def receive_inbound_webhook(
    vendor: str,
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public Inbound Webhook Listener for external vendor webhooks (Slack, GitHub, Telegram, etc.)."""
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        payload = raw_body.decode("utf-8", errors="ignore")

    headers = dict(request.headers)

    # Resolve tenant company_id from integration
    from app.repositories.integration_repo import IntegrationRepository
    repo = IntegrationRepository(db)
    integration = await repo.get_by_id(integration_id)
    if not integration or integration.deleted_at:
        return {"status": "error", "message": "Integration endpoint not found"}

    service = IntegrationService(db)
    return await service.process_inbound_webhook(
        vendor=vendor,
        raw_payload=payload,
        headers=headers,
        company_id=integration.company_id,
        integration_id=integration.id,
    )
