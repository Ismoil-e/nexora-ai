import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Integration(BaseModel):
    __tablename__ = "integrations"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    integration_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), default="general", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    health_status: Mapped[str] = mapped_column(String(32), default="healthy", nullable=False)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    company = relationship("Company", back_populates="integrations")
    credentials = relationship(
        "IntegrationCredential",
        back_populates="integration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    webhook_subscriptions = relationship(
        "WebhookSubscription",
        back_populates="integration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events = relationship(
        "IntegrationEvent",
        back_populates="integration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    executions = relationship(
        "IntegrationExecution",
        back_populates="integration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    health_records = relationship(
        "IntegrationHealth",
        back_populates="integration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class IntegrationCredential(BaseModel):
    __tablename__ = "integration_credentials"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auth_type: Mapped[str] = mapped_column(String(32), default="api_key", nullable=False)
    encrypted_data: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    integration = relationship("Integration", back_populates="credentials")


class WebhookSubscription(BaseModel):
    __tablename__ = "webhook_subscriptions"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(128), default="*", nullable=False, index=True)
    target_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    secret_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_inbound: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    integration = relationship("Integration", back_populates="webhook_subscriptions")


class IntegrationEvent(BaseModel):
    __tablename__ = "integration_events"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16), default="inbound", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="processed", nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    integration = relationship("Integration", back_populates="events")


class IntegrationExecution(BaseModel):
    __tablename__ = "integration_executions"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="success", nullable=False, index=True)
    request_params: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    triggered_by_type: Mapped[str] = mapped_column(String(32), default="system", nullable=False)
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    integration = relationship("Integration", back_populates="executions")


class IntegrationHealth(BaseModel):
    __tablename__ = "integration_health"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="healthy", nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_rate_24h: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_requests_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    integration = relationship("Integration", back_populates="health_records")
