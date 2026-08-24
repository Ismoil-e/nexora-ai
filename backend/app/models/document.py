import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Document(BaseModel):
    __tablename__ = "documents"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Document Intelligence extensions
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # Contract, Invoice, Report, etc.
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_system: Mapped[str] = mapped_column(String(32), default="user", nullable=False, index=True)  # user, integration, api, workflow
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Enterprise Security: Document-level classification and access control
    sensitivity_level: Mapped[str] = mapped_column(String(32), default="INTERNAL", nullable=False, index=True)
    access_level: Mapped[str] = mapped_column(String(32), default="owner", nullable=False)  # owner, team, department, company, restricted
    allowed_user_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of user UUIDs for restricted docs
    classification_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    company = relationship("Company", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", lazy="selectin", cascade="all, delete-orphan")
    versions = relationship("DocumentVersion", back_populates="document", lazy="selectin", cascade="all, delete-orphan")
    entities = relationship("DocumentEntity", back_populates="document", lazy="selectin", cascade="all, delete-orphan")
    relationships = relationship("DocumentRelationship", back_populates="document", lazy="selectin", cascade="all, delete-orphan")
    processing_jobs = relationship("DocumentProcessingJob", back_populates="document", lazy="selectin", cascade="all, delete-orphan")



class DocumentChunk(BaseModel):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_data: Mapped[str | None] = mapped_column(nullable=True)

    document = relationship("Document", back_populates="chunks")
