import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


AuthType = Literal["oauth2", "api_key", "bearer", "service_account", "basic", "custom"]
IntegrationCategory = Literal["workspace", "messaging", "dev_tools", "crm_erp", "database", "general"]
EventDirection = Literal["inbound", "outbound"]
EventStatus = Literal["pending", "processed", "failed", "dead_letter"]


class NexoraEvent(BaseModel):
    """Normalized event format across all external systems"""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: uuid.UUID
    integration_id: uuid.UUID
    source_vendor: str  # e.g., 'google', 'microsoft', 'telegram', 'slack', 'github', 'jira', 'sap'
    event_type: str  # e.g., 'document.created', 'message.received', 'issue.opened'
    resource_type: str  # e.g., 'file', 'email', 'message', 'task', 'pull_request'
    resource_id: str | None = None
    actor_id: str | None = None
    actor_email: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str | None = None
    content_summary: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] | str = Field(default_factory=dict)
    is_important: bool = False
    requires_memory_ingestion: bool = False


class ConnectorHealth(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy", "unknown"] = "healthy"
    latency_ms: int = 0
    error_message: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CredentialData(BaseModel):
    auth_type: AuthType
    api_key: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    service_account_json: dict[str, Any] | None = None
    username: str | None = None
    password: str | None = None
    custom_headers: dict[str, str] = Field(default_factory=dict)
    extra_params: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class ExecutionResult(BaseModel):
    success: bool
    data: Any = None
    message: str = "Execution completed"
    error: str | None = None
    duration_ms: int = 0
    raw_response: Any = None
