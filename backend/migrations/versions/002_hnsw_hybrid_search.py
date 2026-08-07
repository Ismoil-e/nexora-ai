"""HNSW Vector index and Full-Text search index migration

Revision ID: 002
Revises: 001
Create Date: 2026-08-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. HNSW index for sub-millisecond vector similarity search
    op.execute(
        "CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )

    # 2. GIN index for full-text lexical search
    op.execute(
        "CREATE INDEX IF NOT EXISTS document_chunks_content_fts_idx "
        "ON document_chunks USING gin (to_tsvector('simple', content));"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS document_chunks_embedding_hnsw_idx;")
    op.execute("DROP INDEX IF EXISTS document_chunks_content_fts_idx;")
