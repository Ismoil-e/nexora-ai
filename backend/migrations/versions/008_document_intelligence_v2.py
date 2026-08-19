"""Document Intelligence Engine v2 schema

Revision ID: 008
Revises: 007
Create Date: 2026-08-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Allow system-generated documents (integration memory ingestion) without a user owner
    op.alter_column("documents", "uploaded_by", existing_type=UUID(as_uuid=True), nullable=True)

    op.add_column("documents", sa.Column("title", sa.String(512), nullable=True))
    op.add_column("documents", sa.Column("author", sa.String(255), nullable=True))
    op.add_column("documents", sa.Column("source_system", sa.String(32), server_default="user", nullable=False))
    op.add_column("documents", sa.Column("embedding_model", sa.String(128), nullable=True))
    op.add_column("documents", sa.Column("embedding_version", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("embedding_dimensions", sa.Integer(), nullable=True))

    op.create_index("ix_documents_source_system", "documents", ["source_system"])
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])


def downgrade() -> None:
    op.drop_index("ix_documents_uploaded_by", table_name="documents")
    op.drop_index("ix_documents_source_system", table_name="documents")

    op.drop_column("documents", "embedding_dimensions")
    op.drop_column("documents", "embedding_version")
    op.drop_column("documents", "embedding_model")
    op.drop_column("documents", "source_system")
    op.drop_column("documents", "author")
    op.drop_column("documents", "title")

    op.alter_column("documents", "uploaded_by", existing_type=UUID(as_uuid=True), nullable=False)
