from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# KPI Schemas
# ---------------------------------------------------------------------------

class KPICreate(BaseModel):
    code: str
    name: str
    category: str = "operations"  # finance, operations, hr, documents, ai, custom
    description: Optional[str] = None
    calculation_type: str = "query"  # query, formula, external, manual
    target_value: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    unit: str = ""
    formula_expression: Optional[str] = None
    meta_data: Optional[str] = None


class KPIUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    calculation_type: Optional[str] = None
    target_value: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    unit: Optional[str] = None
    formula_expression: Optional[str] = None
    meta_data: Optional[str] = None


class KPILogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kpi_id: UUID
    recorded_value: float
    target_value: Optional[float] = None
    status: str
    created_at: datetime


class KPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    category: str
    description: Optional[str] = None
    calculation_type: str
    target_value: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    unit: str
    current_value: float
    previous_value: Optional[float] = None
    change_pct: Optional[float] = None
    status: str
    last_calculated_at: Optional[datetime] = None
    formula_expression: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class KPICalculateRequest(BaseModel):
    kpi_codes: Optional[List[str]] = None  # None means calculate all tenant KPIs


class KPICalculateResponse(BaseModel):
    success: bool
    calculated_count: int
    results: List[KPIResponse]


# ---------------------------------------------------------------------------
# Dashboard & Widget Schemas
# ---------------------------------------------------------------------------

class DashboardWidgetCreate(BaseModel):
    title: str
    widget_type: str  # kpi_card, chart_line, chart_bar, chart_pie, table, heatmap, activity_feed, ai_summary, alert_list, forecast_chart
    metric_code: Optional[str] = None
    query_config: Optional[str] = None
    position_x: int = 0
    position_y: int = 0
    width: int = 4
    height: int = 3
    refresh_interval_sec: int = 300


class DashboardWidgetUpdate(BaseModel):
    title: Optional[str] = None
    widget_type: Optional[str] = None
    metric_code: Optional[str] = None
    query_config: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    refresh_interval_sec: Optional[int] = None


class DashboardWidgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dashboard_id: UUID
    title: str
    widget_type: str
    metric_code: Optional[str] = None
    query_config: Optional[str] = None
    position_x: int
    position_y: int
    width: int
    height: int
    refresh_interval_sec: int
    created_at: datetime
    updated_at: datetime


class DashboardCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    category: str = "general"
    is_default: bool = False
    is_public_for_tenant: bool = True
    allowed_roles: Optional[str] = None
    layout_config: Optional[str] = None
    widgets: Optional[List[DashboardWidgetCreate]] = None


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_default: Optional[bool] = None
    is_public_for_tenant: Optional[bool] = None
    allowed_roles: Optional[str] = None
    layout_config: Optional[str] = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    category: str
    is_default: bool
    is_public_for_tenant: bool
    allowed_roles: Optional[str] = None
    layout_config: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DashboardDetailResponse(DashboardResponse):
    widgets: List[DashboardWidgetResponse] = []


# ---------------------------------------------------------------------------
# Insight Schemas
# ---------------------------------------------------------------------------

class BIInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    category: str
    severity: str
    summary: str
    explanation: str
    recommended_actions: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    is_acknowledged: bool
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime


class BIInsightGenerateRequest(BaseModel):
    categories: Optional[List[str]] = None
    force_refresh: bool = False


# ---------------------------------------------------------------------------
# Forecast Schemas
# ---------------------------------------------------------------------------

class BIForecastRequest(BaseModel):
    metric_name: str  # workload, document_volume, task_completion, revenue, expenses, active_users
    periods_ahead: int = 3
    methodology: str = "linear_trend"  # linear_trend, moving_avg, exponential, hybrid_llm


class BIForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_name: str
    target_period: str
    predicted_value: float
    confidence_score: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    methodology: str
    historical_points_count: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Alert Rule & Alerts Schemas
# ---------------------------------------------------------------------------

class BIAlertRuleCreate(BaseModel):
    name: str
    kpi_code: str
    condition_operator: str = "lt"  # gt, lt, gte, lte, eq, neq, drop_pct, spike_pct
    threshold_value: float
    severity: str = "warning"
    is_active: bool = True
    notify_channels: Optional[str] = None  # JSON array: ["in_app", "telegram", "email"]


class BIAlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    condition_operator: Optional[str] = None
    threshold_value: Optional[float] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None
    notify_channels: Optional[str] = None


class BIAlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kpi_code: str
    condition_operator: str
    threshold_value: float
    severity: str
    is_active: bool
    notify_channels: Optional[str] = None
    last_triggered_at: Optional[datetime] = None
    created_at: datetime


class BIAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: Optional[UUID] = None
    title: str
    message: str
    severity: str
    status: str
    triggered_value: Optional[float] = None
    threshold_value: Optional[float] = None
    triggered_at: datetime
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Executive Summary & Risk Schemas
# ---------------------------------------------------------------------------

class ExecutiveSummaryRequest(BaseModel):
    target_role: str = "CEO"  # CEO, CFO, COO, HR_Director, Project_Manager
    timeframe: str = "current_month"  # current_week, current_month, current_quarter, year_to_date
    include_recommendations: bool = True
    include_risks: bool = True


class ExecutiveSummaryResponse(BaseModel):
    target_role: str
    timeframe: str
    generated_at: datetime
    overall_health: str  # excellent, good, warning, critical
    key_metrics_summary: dict
    executive_narrative: str
    key_insights: List[str]
    critical_risks: List[str]
    actionable_recommendations: List[dict]
    source_citations: List[dict]


class RiskItem(BaseModel):
    category: str
    risk_level: str  # low, medium, high, critical
    title: str
    description: str
    impact: str
    mitigation_step: str
    source_entity: Optional[str] = None


class RiskAnalysisResponse(BaseModel):
    company_id: UUID
    evaluated_at: datetime
    total_risks_detected: int
    critical_risks_count: int
    risks: List[RiskItem]


class TrendPoint(BaseModel):
    period: str
    value: float
    change_pct: Optional[float] = None
    is_anomaly: bool = False


class TrendAnalysisRequest(BaseModel):
    metric_name: str
    granularity: str = "daily"  # daily, weekly, monthly
    periods_count: int = 12


class TrendAnalysisResponse(BaseModel):
    metric_name: str
    granularity: str
    trend_direction: str  # growing, declining, stable, volatile
    average_value: float
    growth_rate_pct: float
    anomalies_detected: int
    series: List[TrendPoint]


class CompanyBIOverviewResponse(BaseModel):
    company_id: UUID
    generated_at: datetime
    kpi_summary: dict
    active_alerts_count: int
    critical_risks_count: int
    recent_insights: List[BIInsightResponse]
    top_kpis: List[KPIResponse]
    quick_health_status: str
