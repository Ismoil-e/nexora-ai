import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Company(BaseModel):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscription_plan: Mapped[str] = mapped_column(String(64), default="free", nullable=False)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ai_credits: Mapped[int] = mapped_column(default=0, nullable=False)
    max_users: Mapped[int] = mapped_column(default=10, nullable=False)
    max_storage_gb: Mapped[int] = mapped_column(default=5, nullable=False)
    settings: Mapped[str | None] = mapped_column(Text, nullable=True)

    users = relationship("User", back_populates="company", lazy="selectin")
    roles = relationship("Role", back_populates="company", lazy="selectin")
    chats = relationship("Chat", back_populates="company", lazy="selectin")
    documents = relationship("Document", back_populates="company", lazy="selectin")
    agents = relationship("Agent", back_populates="company", lazy="selectin")
    tasks = relationship("Task", back_populates="company", lazy="selectin")
    notifications = relationship("Notification", back_populates="company", lazy="selectin")
    api_keys = relationship("ApiKey", back_populates="company", lazy="selectin")
    integrations = relationship("Integration", back_populates="company", lazy="selectin")

