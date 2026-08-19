import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class IntegrationCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    integration_type: str = Field(..., max_length=64)
    category: str = Field("general", max_length=64)
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    auth_type: str = Field("api_key", max_length=32)


class IntegrationUpdateSchema(BaseModel):
    name: str | None = None
    status: str | None = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    auth_type: str | None = None


class IntegrationExecuteSchema(BaseModel):
    action_name: str = Field(..., max_length=128)
    params: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)


class IntegrationResponseSchema(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    slug: str
    integration_type: str
    category: str
    status: str
    health_status: str
    last_health_check_at: datetime | None = None
    error_message: str | None = None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationMetaResponseSchema(BaseModel):
    integration_type: str
    display_name: str
    category: str
    description: str
    icon: str | None = None
    supported_auth_types: list[str]
    supported_actions: list[str]
    requires_credentials: bool


class WebhookSubscriptionCreateSchema(BaseModel):
    integration_id: uuid.UUID
    event_type: str = Field("*", max_length=128)
    target_url: str = Field(..., max_length=1024)
    secret: str | None = None
    headers: dict[str, str] | None = None
