import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Agent(BaseModel):
    __tablename__ = "agents"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str] = mapped_column(String(64), default="gemini", nullable=False)
    model: Mapped[str] = mapped_column(String(128), default="gemini-2.5-flash", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    capabilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Framework extensions (nullable for backward compatibility)
    agent_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    agent_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)

    company = relationship("Company", back_populates="agents")
    chats = relationship("Chat", back_populates="agent", lazy="selectin")
    executions = relationship(
        "AgentExecution",
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    configurations = relationship(
        "AgentConfiguration",
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    logs = relationship(
        "AgentLog",
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    memory_references = relationship(
        "AgentMemoryReference",
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    permissions = relationship(
        "AgentPermission",
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class AgentExecution(BaseModel):
    __tablename__ = "agent_executions"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    output_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Framework extensions
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    async_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    agent = relationship("Agent", back_populates="executions")
    user = relationship("User", back_populates="agent_executions")
    logs = relationship("AgentLog", back_populates="execution", lazy="selectin")


class AgentConfiguration(BaseModel):
    """Per-agent / per-company configuration overrides."""

    __tablename__ = "agent_configurations"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    config_key: Mapped[str] = mapped_column(String(128), nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    agent = relationship("Agent", back_populates="configurations")


class AgentLog(BaseModel):
    """Structured stage logs for agent pipeline observability."""

    __tablename__ = "agent_logs"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    agent = relationship("Agent", back_populates="logs")
    execution = relationship("AgentExecution", back_populates="logs")


class AgentMemoryReference(BaseModel):
    """Links agent executions to memory / document evidence refs."""

    __tablename__ = "agent_memory_references"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(64), default="episode", nullable=False)
    meta_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    agent = relationship("Agent", back_populates="memory_references")


class AgentPermission(BaseModel):
    """Maps RBAC permission codes to framework agent keys / agent rows."""

    __tablename__ = "agent_permissions"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    agent = relationship("Agent", back_populates="permissions")
