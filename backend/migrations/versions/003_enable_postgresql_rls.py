"""Enable PostgreSQL Row-Level Security (RLS) policies for Multi-Tenancy

Revision ID: 003
Revises: 002
Create Date: 2026-08-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = [
    "users",
    "documents",
    "chats",
    "tasks",
    "notifications",
    "agents",
    "reports",
]


def upgrade() -> None:
    for table in TENANT_TABLES:
        # Enable RLS on the table
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")

        # Create policy guaranteeing tenant isolation via current_setting('app.current_tenant_id')
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation_policy ON {table} "
            f"FOR ALL USING ("
            f"  current_setting('app.current_tenant_id', true) IS NULL OR "
            f"  company_id::text = current_setting('app.current_tenant_id', true)"
            f");"
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation_policy ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
