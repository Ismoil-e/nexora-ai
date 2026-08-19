import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DocumentVersion(BaseModel):
    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    document = relationship("Document", back_populates="versions")


class DocumentEntity(BaseModel):
    __tablename__ = "document_entities"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # Person, Company, Contract, Financial, etc.
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    attributes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON metadata

    document = relationship("Document", back_populates="entities")


class DocumentRelationship(BaseModel):
    __tablename__ = "document_relationships"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # WORKS_FOR, SIGNED_BY, BELONGS_TO
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    context_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    document = relationship("Document", back_populates="relationships")


class DocumentProcessingJob(BaseModel):
    __tablename__ = "document_processing_jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)  # pending, processing, completed, failed
    pipeline_version: Mapped[str] = mapped_column(String(32), default="2.0.0", nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ocr_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extraction_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relationship_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    document = relationship("Document", back_populates="processing_jobs")
