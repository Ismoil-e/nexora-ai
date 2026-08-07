"""Agent framework schema extensions

Revision ID: 004
Revises: 003
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("agent_key", sa.String(64), nullable=True))
    op.add_column("agents", sa.Column("agent_type", sa.String(64), nullable=True))
    op.add_column(
        "agents",
        sa.Column("version", sa.String(32), server_default="1.0.0", nullable=False),
    )
    op.create_index("ix_agents_agent_key", "agents", ["agent_key"])
    op.create_index("ix_agents_agent_type", "agents", ["agent_type"])

    op.add_column(
        "agent_executions",
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column("agent_executions", sa.Column("agent_key", sa.String(64), nullable=True))
    op.add_column("agent_executions", sa.Column("request_id", sa.String(64), nullable=True))
    op.add_column("agent_executions", sa.Column("stage", sa.String(64), nullable=True))
    op.add_column("agent_executions", sa.Column("context_snapshot", sa.Text(), nullable=True))
    op.add_column("agent_executions", sa.Column("async_task_id", sa.String(128), nullable=True))
    op.create_index("ix_agent_executions_company_id", "agent_executions", ["company_id"])
    op.create_index("ix_agent_executions_agent_key", "agent_executions", ["agent_key"])

    op.create_table(
        "agent_configurations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("config_key", sa.String(128), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_configurations_agent_id", "agent_configurations", ["agent_id"])
    op.create_index("ix_agent_configurations_company_id", "agent_configurations", ["company_id"])

    op.create_table(
        "agent_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=True),
        sa.Column(
            "execution_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agent_executions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("level", sa.String(16), server_default="info", nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_logs_agent_id", "agent_logs", ["agent_id"])
    op.create_index("ix_agent_logs_execution_id", "agent_logs", ["execution_id"])
    op.create_index("ix_agent_logs_company_id", "agent_logs", ["company_id"])

    op.create_table(
        "agent_memory_references",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=True),
        sa.Column(
            "execution_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agent_executions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_ref", sa.String(255), nullable=False),
        sa.Column("ref_type", sa.String(64), server_default="episode", nullable=False),
        sa.Column("meta_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_memory_references_agent_id", "agent_memory_references", ["agent_id"])
    op.create_index("ix_agent_memory_references_execution_id", "agent_memory_references", ["execution_id"])
    op.create_index("ix_agent_memory_references_company_id", "agent_memory_references", ["company_id"])

    op.create_table(
        "agent_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_key", sa.String(64), nullable=False),
        sa.Column("permission_code", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_permissions_agent_id", "agent_permissions", ["agent_id"])
    op.create_index("ix_agent_permissions_company_id", "agent_permissions", ["company_id"])
    op.create_index("ix_agent_permissions_agent_key", "agent_permissions", ["agent_key"])
    op.create_index("ix_agent_permissions_permission_code", "agent_permissions", ["permission_code"])


def downgrade() -> None:
    op.drop_table("agent_permissions")
    op.drop_table("agent_memory_references")
    op.drop_table("agent_logs")
    op.drop_table("agent_configurations")

    op.drop_index("ix_agent_executions_agent_key", table_name="agent_executions")
    op.drop_index("ix_agent_executions_company_id", table_name="agent_executions")
    op.drop_column("agent_executions", "async_task_id")
    op.drop_column("agent_executions", "context_snapshot")
    op.drop_column("agent_executions", "stage")
    op.drop_column("agent_executions", "request_id")
    op.drop_column("agent_executions", "agent_key")
    op.drop_column("agent_executions", "company_id")

    op.drop_index("ix_agents_agent_type", table_name="agents")
    op.drop_index("ix_agents_agent_key", table_name="agents")
    op.drop_column("agents", "version")
    op.drop_column("agents", "agent_type")
    op.drop_column("agents", "agent_key")
