"""Enterprise Integration Hub schema

Revision ID: 006
Revises: 005
Create Date: 2026-08-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. integrations
    op.create_table(
        "integrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("integration_type", sa.String(64), nullable=False),
        sa.Column("category", sa.String(64), server_default="general", nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("health_status", sa.String(32), server_default="healthy", nullable=False),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_integrations_company_id", "integrations", ["company_id"])
    op.create_index("ix_integrations_slug", "integrations", ["slug"])
    op.create_index("ix_integrations_integration_type", "integrations", ["integration_type"])
    op.create_index("ix_integrations_category", "integrations", ["category"])
    op.create_index("ix_integrations_status", "integrations", ["status"])

    # 2. integration_credentials
    op.create_table(
        "integration_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("integration_id", UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("auth_type", sa.String(32), server_default="api_key", nullable=False),
        sa.Column("encrypted_data", sa.Text(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_integration_credentials_integration_id", "integration_credentials", ["integration_id"])
    op.create_index("ix_integration_credentials_company_id", "integration_credentials", ["company_id"])

    # 3. webhook_subscriptions
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("integration_id", UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(128), server_default="*", nullable=False),
        sa.Column("target_url", sa.String(1024), nullable=False),
        sa.Column("secret_hash", sa.String(255), nullable=True),
        sa.Column("headers", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_inbound", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhook_subscriptions_integration_id", "webhook_subscriptions", ["integration_id"])
    op.create_index("ix_webhook_subscriptions_company_id", "webhook_subscriptions", ["company_id"])
    op.create_index("ix_webhook_subscriptions_event_type", "webhook_subscriptions", ["event_type"])

    # 4. integration_events
    op.create_table(
        "integration_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("integration_id", UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("direction", sa.String(16), server_default="inbound", nullable=False),
        sa.Column("status", sa.String(32), server_default="processed", nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("normalized_payload", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_integration_events_integration_id", "integration_events", ["integration_id"])
    op.create_index("ix_integration_events_company_id", "integration_events", ["company_id"])
    op.create_index("ix_integration_events_event_id", "integration_events", ["event_id"])
    op.create_index("ix_integration_events_event_type", "integration_events", ["event_type"])
    op.create_index("ix_integration_events_status", "integration_events", ["status"])

    # 5. integration_executions
    op.create_table(
        "integration_executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("integration_id", UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), server_default="success", nullable=False),
        sa.Column("request_params", sa.Text(), nullable=True),
        sa.Column("response_data", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("triggered_by_type", sa.String(32), server_default="system", nullable=False),
        sa.Column("triggered_by_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_integration_executions_integration_id", "integration_executions", ["integration_id"])
    op.create_index("ix_integration_executions_company_id", "integration_executions", ["company_id"])
    op.create_index("ix_integration_executions_status", "integration_executions", ["status"])

    # 6. integration_health
    op.create_table(
        "integration_health",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("integration_id", UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), server_default="healthy", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_rate_24h", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("total_requests_24h", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_integration_health_integration_id", "integration_health", ["integration_id"])
    op.create_index("ix_integration_health_company_id", "integration_health", ["company_id"])


def downgrade() -> None:
    op.drop_table("integration_health")
    op.drop_table("integration_executions")
    op.drop_table("integration_events")
    op.drop_table("webhook_subscriptions")
    op.drop_table("integration_credentials")
    op.drop_table("integrations")
