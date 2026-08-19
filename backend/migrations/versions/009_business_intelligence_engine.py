"""Business Intelligence Engine schema

Revision ID: 009
Revises: 008
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Dashboards
    op.create_table(
        "dashboards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), server_default="general", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_public_for_tenant", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("allowed_roles", sa.Text(), nullable=True),
        sa.Column("layout_config", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Dashboard Widgets
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("dashboard_id", UUID(as_uuid=True), sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("widget_type", sa.String(64), nullable=False),
        sa.Column("metric_code", sa.String(128), nullable=True),
        sa.Column("query_config", sa.Text(), nullable=True),
        sa.Column("position_x", sa.Integer(), server_default="0", nullable=False),
        sa.Column("position_y", sa.Integer(), server_default="0", nullable=False),
        sa.Column("width", sa.Integer(), server_default="4", nullable=False),
        sa.Column("height", sa.Integer(), server_default="3", nullable=False),
        sa.Column("refresh_interval_sec", sa.Integer(), server_default="300", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. KPIs
    op.create_table(
        "kpis",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("code", sa.String(128), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(64), server_default="operations", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("calculation_type", sa.String(32), server_default="query", nullable=False),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("warning_threshold", sa.Float(), nullable=True),
        sa.Column("critical_threshold", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(32), server_default="", nullable=False),
        sa.Column("current_value", sa.Float(), server_default="0", nullable=False),
        sa.Column("previous_value", sa.Float(), nullable=True),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.Column("status", sa.String(32), server_default="healthy", nullable=False),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("formula_expression", sa.String(512), nullable=True),
        sa.Column("meta_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. KPI Logs
    op.create_table(
        "kpi_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("kpi_id", UUID(as_uuid=True), sa.ForeignKey("kpis.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("recorded_value", sa.Float(), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("status", sa.String(32), server_default="healthy", nullable=False),
        sa.Column("meta_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 5. BI Insights
    op.create_table(
        "bi_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(64), server_default="general", nullable=False),
        sa.Column("severity", sa.String(32), server_default="info", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("recommended_actions", sa.Text(), nullable=True),
        sa.Column("related_entity_type", sa.String(64), nullable=True),
        sa.Column("related_entity_id", sa.String(128), nullable=True),
        sa.Column("is_acknowledged", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("acknowledged_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 6. BI Forecasts
    op.create_table(
        "bi_forecasts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("metric_name", sa.String(128), nullable=False, index=True),
        sa.Column("target_period", sa.String(64), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="0.85", nullable=False),
        sa.Column("lower_bound", sa.Float(), nullable=True),
        sa.Column("upper_bound", sa.Float(), nullable=True),
        sa.Column("methodology", sa.String(64), server_default="linear_trend", nullable=False),
        sa.Column("historical_points_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("meta_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 7. BI Alert Rules
    op.create_table(
        "bi_alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kpi_code", sa.String(128), nullable=False, index=True),
        sa.Column("condition_operator", sa.String(32), server_default="lt", nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(32), server_default="warning", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_channels", sa.Text(), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 8. BI Alerts
    op.create_table(
        "bi_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rule_id", UUID(as_uuid=True), sa.ForeignKey("bi_alert_rules.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(32), server_default="warning", nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("triggered_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 9. Analytics Snapshots
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("snapshot_date", sa.String(32), nullable=False, index=True),
        sa.Column("metrics_data", sa.Text(), nullable=False),
        sa.Column("department_breakdown", sa.Text(), nullable=True),
        sa.Column("project_breakdown", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("analytics_snapshots")
    op.drop_table("bi_alerts")
    op.drop_table("bi_alert_rules")
    op.drop_table("bi_forecasts")
    op.drop_table("bi_insights")
    op.drop_table("kpi_logs")
    op.drop_table("kpis")
    op.drop_table("dashboard_widgets")
    op.drop_table("dashboards")
