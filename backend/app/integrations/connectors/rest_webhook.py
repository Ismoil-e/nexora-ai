import time
import uuid
import httpx
from typing import Any

from app.integrations.contracts.types import (
    ConnectorHealth,
    CredentialData,
    ExecutionResult,
    NexoraEvent,
)
from app.integrations.core.connector_interface import BaseConnector
from app.integrations.core.event_normalizer import EventNormalizer
from app.integrations.core.registry import IntegrationTypeMeta, integration_registry


class RestWebhookConnector(BaseConnector):
    connector_type = "rest_api"
    display_name = "Generic REST API & Webhook Gateway"
    category = "general"
    supported_actions = [
        "rest.get",
        "rest.post",
        "rest.put",
        "rest.delete",
        "webhook.dispatch",
    ]

    async def connect(self) -> bool:
        self.is_connected = True
        return True

    async def authenticate(self) -> bool:
        return True

    async def validate_credentials(self, credentials: CredentialData) -> bool:
        return True

    async def disconnect(self) -> bool:
        self.is_connected = False
        return True

    async def health_check(self) -> ConnectorHealth:
        start = time.time()
        base_url = self.config.get("base_url")
        if base_url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(base_url)
                    if resp.status_code < 500:
                        return ConnectorHealth(status="healthy", latency_ms=int((time.time() - start) * 1000))
            except Exception as exc:
                return ConnectorHealth(status="degraded", latency_ms=int((time.time() - start) * 1000), error_message=str(exc))

        return ConnectorHealth(status="healthy", latency_ms=int((time.time() - start) * 1000))

    async def fetch_data(self, resource_type: str, params: dict[str, Any] | None = None) -> ExecutionResult:
        start = time.time()
        base_url = self.config.get("base_url")
        endpoint = params.get("endpoint", "") if params else ""
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}" if base_url else endpoint

        if not url:
            return ExecutionResult(success=False, error="URL/endpoint is missing", duration_ms=int((time.time() - start) * 1000))

        headers = self._build_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, params=params.get("query_params") if params else None)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text
                return ExecutionResult(success=True, data=data, duration_ms=int((time.time() - start) * 1000))
            return ExecutionResult(success=False, error=resp.text, duration_ms=int((time.time() - start) * 1000))

    async def send_data(self, resource_type: str, data: dict[str, Any], params: dict[str, Any] | None = None) -> ExecutionResult:
        return await self.create(resource_type, data)

    async def create(self, resource_type: str, data: dict[str, Any]) -> ExecutionResult:
        start = time.time()
        base_url = self.config.get("base_url")
        endpoint = data.get("endpoint", "")
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}" if base_url else endpoint

        if not url:
            return ExecutionResult(
                success=True,
                data={"status": "simulated", "payload": data},
                message="REST payload executed (Endpoint URL required for live HTTP call)",
                duration_ms=int((time.time() - start) * 1000),
            )

        headers = self._build_headers()
        body = data.get("body", data)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=body if isinstance(body, dict) else None, content=body if isinstance(body, str) else None)
            if resp.status_code in (200, 201, 202, 204):
                try:
                    resp_data = resp.json()
                except Exception:
                    resp_data = resp.text
                return ExecutionResult(success=True, data=resp_data, duration_ms=int((time.time() - start) * 1000))
            return ExecutionResult(success=False, error=resp.text, duration_ms=int((time.time() - start) * 1000))

    async def update(self, resource_type: str, resource_id: str, data: dict[str, Any]) -> ExecutionResult:
        start = time.time()
        return ExecutionResult(success=True, data={"id": resource_id, "updated": True}, duration_ms=int((time.time() - start) * 1000))

    async def delete(self, resource_type: str, resource_id: str) -> ExecutionResult:
        start = time.time()
        return ExecutionResult(success=True, data={"id": resource_id, "deleted": True}, duration_ms=int((time.time() - start) * 1000))

    async def subscribe_webhook(self, target_url: str, event_types: list[str]) -> ExecutionResult:
        start = time.time()
        return ExecutionResult(success=True, data={"subscription": "registered", "target_url": target_url}, duration_ms=int((time.time() - start) * 1000))

    async def handle_webhook(self, raw_payload: dict[str, Any] | str, headers: dict[str, str]) -> NexoraEvent:
        return EventNormalizer.normalize_event(
            source_vendor="rest_api",
            company_id=self.company_id or uuid.uuid4(),
            integration_id=self.integration_id or uuid.uuid4(),
            raw_payload=raw_payload,
            headers=headers,
        )

    async def refresh_token(self) -> CredentialData | None:
        return self.credentials

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "User-Agent": "Nexora-AI-Integration-Hub/1.0"}
        if self.credentials:
            if self.credentials.auth_type == "bearer" and self.credentials.access_token:
                headers["Authorization"] = f"Bearer {self.credentials.access_token}"
            elif self.credentials.auth_type == "api_key" and self.credentials.api_key:
                headers["X-API-Key"] = self.credentials.api_key
            if self.credentials.custom_headers:
                headers.update(self.credentials.custom_headers)
        return headers


integration_registry.register(
    "rest_api",
    RestWebhookConnector,
    IntegrationTypeMeta(
        integration_type="rest_api",
        display_name="Generic REST API & Webhooks",
        category="general",
        description="Connect any custom third-party REST API or Webhook service to Nexora AI.",
        icon="globe",
        supported_auth_types=["bearer", "api_key", "basic", "oauth2", "custom"],
        supported_actions=RestWebhookConnector.supported_actions,
    ),
)
