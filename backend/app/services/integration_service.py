import json
import time
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.contracts.types import CredentialData, ExecutionResult
from app.integrations.core.connector_manager import connector_manager
from app.integrations.core.health_monitor import health_monitor
from app.integrations.core.rate_limiter import rate_limit_manager, retry_manager
from app.integrations.core.webhook_manager import webhook_manager
from app.integrations.memory_router import memory_router
from app.integrations.security.encryption import credential_encryption
from app.models.integration import Integration
from app.repositories.integration_repo import IntegrationRepository
from app.utils.exceptions import NotFoundException, ValidationException


class IntegrationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = IntegrationRepository(db)

    async def list_integrations(self, company_id: uuid.UUID, page: int = 1, page_size: int = 50) -> list[Integration]:
        return await self.repo.get_by_company(company_id, page=page, page_size=page_size)

    async def get_integration(self, integration_id: uuid.UUID, company_id: uuid.UUID) -> Integration:
        integration = await self.repo.get_by_id(integration_id)
        if not integration or integration.company_id != company_id or integration.deleted_at:
            raise NotFoundException(detail="Integration not found or access denied")
        return integration

    async def create_integration(
        self,
        company_id: uuid.UUID,
        name: str,
        integration_type: str,
        category: str = "general",
        config: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        auth_type: str = "api_key",
    ) -> Integration:
        slug = f"{integration_type}-{uuid.uuid4().hex[:6]}"
        config_str = json.dumps(config) if config else None

        integration = await self.repo.create(
            company_id=company_id,
            name=name,
            slug=slug,
            integration_type=integration_type,
            category=category,
            status="active",
            health_status="healthy",
            config=config_str,
        )

        if credentials:
            encrypted = credential_encryption.encrypt_data(credentials)
            await self.repo.save_credential(
                integration_id=integration.id,
                company_id=company_id,
                auth_type=auth_type,
                encrypted_data=encrypted,
            )

        return integration

    async def test_connection(self, integration_id: uuid.UUID, company_id: uuid.UUID) -> dict[str, Any]:
        integration = await self.get_integration(integration_id, company_id)
        cred = await self.repo.get_credential(integration.id)

        connector = connector_manager.build_connector(
            integration_id=integration.id,
            company_id=company_id,
            integration_type=integration.integration_type,
            config_json=integration.config,
            encrypted_credentials=cred.encrypted_data if cred else None,
            auth_type=cred.auth_type if cred else "api_key",
        )

        health = await connector.health_check()
        await self.repo.update_health(
            integration_id=integration.id,
            company_id=company_id,
            status=health.status,
            latency_ms=health.latency_ms,
        )

        integration.health_status = health.status
        if health.error_message:
            integration.error_message = health.error_message
        await self.db.commit()

        return health.model_dump()

    async def execute_action(
        self,
        integration_id: uuid.UUID,
        company_id: uuid.UUID,
        action_name: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        triggered_by_type: str = "system",
        triggered_by_id: uuid.UUID | None = None,
    ) -> ExecutionResult:
        params = params or {}
        data = data or {}
        integration = await self.get_integration(integration_id, company_id)

        # Rate Limiting Check
        rate_key = f"{company_id}:{integration_id}"
        if not rate_limit_manager.check_rate_limit(rate_key):
            raise ValidationException(detail="Rate limit exceeded for this integration")

        cred = await self.repo.get_credential(integration.id)
        connector = await connector_manager.get_and_connect(
            integration_id=integration.id,
            company_id=company_id,
            integration_type=integration.integration_type,
            config_json=integration.config,
            encrypted_credentials=cred.encrypted_data if cred else None,
            auth_type=cred.auth_type if cred else "api_key",
        )

        start_time = time.time()
        try:
            # Route action execution through RetryManager
            if action_name.startswith("fetch_"):
                res_type = action_name.replace("fetch_", "")
                result = await retry_manager.execute_with_retry(
                    rate_key, connector.fetch_data, resource_type=res_type, params=params
                )
            elif action_name.startswith("send_"):
                res_type = action_name.replace("send_", "")
                result = await retry_manager.execute_with_retry(
                    rate_key, connector.send_data, resource_type=res_type, data=data, params=params
                )
            elif action_name.startswith("create_"):
                res_type = action_name.replace("create_", "")
                result = await retry_manager.execute_with_retry(
                    rate_key, connector.create, resource_type=res_type, data=data
                )
            else:
                # Default creation / sending fallback
                result = await retry_manager.execute_with_retry(
                    rate_key, connector.send_data, resource_type=action_name, data=data, params=params
                )
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            health_monitor.record_execution(integration.id, success=False, latency_ms=duration_ms)
            await self.repo.log_execution(
                integration_id=integration.id,
                company_id=company_id,
                action_name=action_name,
                status="failed",
                params_str=json.dumps(params),
                error_details=str(exc),
                duration_ms=duration_ms,
                triggered_by_type=triggered_by_type,
                triggered_by_id=triggered_by_id,
            )
            return ExecutionResult(success=False, error=str(exc), duration_ms=duration_ms)

        duration_ms = int((time.time() - start_time) * 1000)
        health_monitor.record_execution(integration.id, success=result.success, latency_ms=duration_ms)

        await self.repo.log_execution(
            integration_id=integration.id,
            company_id=company_id,
            action_name=action_name,
            status="success" if result.success else "failed",
            params_str=json.dumps(params),
            response_str=json.dumps(result.data) if result.data else None,
            error_details=result.error,
            duration_ms=duration_ms,
            triggered_by_type=triggered_by_type,
            triggered_by_id=triggered_by_id,
        )

        return result

    async def process_inbound_webhook(
        self,
        vendor: str,
        raw_payload: dict[str, Any] | str,
        headers: dict[str, str],
        company_id: uuid.UUID,
        integration_id: uuid.UUID,
    ) -> dict[str, Any]:
        # Webhook signature verification
        integration = await self.get_integration(integration_id, company_id)
        cred = await self.repo.get_credential(integration.id)

        secret = None
        if cred:
            decrypted = credential_encryption.decrypt_data(cred.encrypted_data)
            if isinstance(decrypted, dict):
                secret = decrypted.get("webhook_secret") or decrypted.get("client_secret") or decrypted.get("api_key")

        if not webhook_manager.verify_signature(vendor, secret or "", raw_payload, headers):
            raise ValidationException(detail="Invalid webhook signature")

        # Normalize Event
        event = connector_manager.build_connector(
            integration_id=integration.id,
            company_id=company_id,
            integration_type=integration.integration_type,
            config_json=integration.config,
        )
        nexora_event = await event.handle_webhook(raw_payload, headers)

        # Idempotency check
        if webhook_manager.is_duplicate_event(nexora_event.event_id):
            return {"status": "ignored", "reason": "Duplicate event ID"}

        # Log event to DB
        await self.repo.log_event(
            integration_id=integration.id,
            company_id=company_id,
            event_id=nexora_event.event_id,
            event_type=nexora_event.event_type,
            direction="inbound",
            status="processed",
            payload_str=json.dumps(raw_payload) if isinstance(raw_payload, dict) else str(raw_payload),
            normalized_str=nexora_event.model_dump_json(),
        )

        # Route to Second Brain Memory if important
        memory_result = await memory_router.route_event_to_memory(self.db, nexora_event)

        return {
            "status": "processed",
            "event_id": nexora_event.event_id,
            "event_type": nexora_event.event_type,
            "memory_routing": memory_result,
        }
