"""Document Intelligence Engine schema

Revision ID: 007
Revises: 006
Create Date: 2026-08-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to documents table
    op.add_column("documents", sa.Column("content_hash", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("detected_type", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("language", sa.String(16), nullable=True))
    op.add_column("documents", sa.Column("department_id", UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("project_id", UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("is_duplicate", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("documents", sa.Column("duplicate_of_id", UUID(as_uuid=True), nullable=True))

    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_detected_type", "documents", ["detected_type"])
    op.create_index("ix_documents_department_id", "documents", ["department_id"])
    op.create_index("ix_documents_project_id", "documents", ["project_id"])

    # 1. document_versions
    op.create_table(
        "document_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("parent_version_id", UUID(as_uuid=True), nullable=True),
        sa.Column("stored_path", sa.String(1024), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_company_id", "document_versions", ["company_id"])

    # 2. document_entities
    op.create_table(
        "document_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=True), sa.ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_name", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("attributes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_document_entities_document_id", "document_entities", ["document_id"])
    op.create_index("ix_document_entities_company_id", "document_entities", ["company_id"])
    op.create_index("ix_document_entities_entity_name", "document_entities", ["entity_name"])
    op.create_index("ix_document_entities_entity_type", "document_entities", ["entity_type"])

    # 3. document_relationships
    op.create_table(
        "document_relationships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_entity_id", UUID(as_uuid=True), sa.ForeignKey("document_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_entity_id", UUID(as_uuid=True), sa.ForeignKey("document_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(128), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("context_snippet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_document_relationships_document_id", "document_relationships", ["document_id"])
    op.create_index("ix_document_relationships_company_id", "document_relationships", ["company_id"])
    op.create_index("ix_document_relationships_relationship_type", "document_relationships", ["relationship_type"])

    # 4. document_processing_jobs
    op.create_table(
        "document_processing_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("pipeline_version", sa.String(32), server_default="2.0.0", nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ocr_duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("embedding_duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("extraction_duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("entity_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("relationship_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_document_processing_jobs_document_id", "document_processing_jobs", ["document_id"])
    op.create_index("ix_document_processing_jobs_company_id", "document_processing_jobs", ["company_id"])
    op.create_index("ix_document_processing_jobs_status", "document_processing_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("document_processing_jobs")
    op.drop_table("document_relationships")
    op.drop_table("document_entities")
    op.drop_table("document_versions")

    op.drop_column("documents", "duplicate_of_id")
    op.drop_column("documents", "is_duplicate")
    op.drop_column("documents", "project_id")
    op.drop_column("documents", "department_id")
    op.drop_column("documents", "language")
    op.drop_column("documents", "detected_type")
    op.drop_column("documents", "summary")
    op.drop_column("documents", "content_hash")
