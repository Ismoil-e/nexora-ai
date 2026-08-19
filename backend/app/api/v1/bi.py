import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user_id, get_db
from app.schemas.bi import (
    BIAlertResponse,
    BIAlertRuleCreate,
    BIAlertRuleResponse,
    BIForecastRequest,
    BIForecastResponse,
    BIInsightGenerateRequest,
    BIInsightResponse,
    CompanyBIOverviewResponse,
    DashboardCreate,
    DashboardDetailResponse,
    DashboardResponse,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    ExecutiveSummaryRequest,
    ExecutiveSummaryResponse,
    KPICalculateRequest,
    KPICalculateResponse,
    KPICreate,
    KPILogResponse,
    KPIResponse,
    KPIUpdate,
    RiskAnalysisResponse,
    TrendAnalysisRequest,
    TrendAnalysisResponse,
)
from app.services.bi_service import BusinessIntelligenceService

router = APIRouter(prefix="/bi", tags=["Business Intelligence"])


@router.get("/overview", response_model=CompanyBIOverviewResponse)
async def get_company_bi_overview(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns a full executive BI overview including health score, top KPIs, risks, and insights."""
    svc = BusinessIntelligenceService(db)
    return await svc.get_overview(company_id)


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

@router.get("/kpis", response_model=List[KPIResponse])
async def list_company_kpis(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns all configured KPIs for the tenant."""
    svc = BusinessIntelligenceService(db)
    return await svc.get_company_kpis(company_id)


@router.post("/kpis", response_model=KPIResponse)
async def create_custom_kpi(
    body: KPICreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new custom KPI."""
    svc = BusinessIntelligenceService(db)
    return await svc.create_kpi(company_id, body)


@router.put("/kpis/{kpi_id}", response_model=KPIResponse)
async def update_kpi(
    kpi_id: uuid.UUID,
    body: KPIUpdate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Updates an existing KPI threshold or definition."""
    svc = BusinessIntelligenceService(db)
    return await svc.update_kpi(company_id, kpi_id, body)


@router.post("/kpis/calculate", response_model=KPICalculateResponse)
async def calculate_kpis(
    body: KPICalculateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Forces real-time recalculation of tenant KPIs and records historical logs."""
    svc = BusinessIntelligenceService(db)
    results = await svc.calculate_kpis(company_id, kpi_codes=body.kpi_codes)
    kpis = await svc.get_company_kpis(company_id)
    return KPICalculateResponse(
        success=True,
        calculated_count=len(results),
        results=[KPIResponse.model_validate(k) for k in kpis],
    )


@router.get("/kpis/{kpi_id}/history", response_model=List[KPILogResponse])
async def get_kpi_history(
    kpi_id: uuid.UUID,
    limit: int = Query(30, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns historical logs for a specific KPI."""
    svc = BusinessIntelligenceService(db)
    return await svc.get_kpi_history(company_id, kpi_id, limit=limit)


# ---------------------------------------------------------------------------
# Dashboards & Widgets
# ---------------------------------------------------------------------------

@router.get("/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists all dashboards for the company."""
    svc = BusinessIntelligenceService(db)
    return await svc.get_dashboards(company_id)


@router.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    body: DashboardCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new customizable dashboard."""
    svc = BusinessIntelligenceService(db)
    return await svc.create_dashboard(company_id, user_id, body)


@router.get("/dashboards/{slug}", response_model=DashboardDetailResponse)
async def get_dashboard_by_slug(
    slug: str,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Gets full dashboard structure and its widgets by slug."""
    svc = BusinessIntelligenceService(db)
    return await svc.get_dashboard_by_slug(company_id, slug)


@router.post("/dashboards/{dashboard_id}/widgets", response_model=DashboardWidgetResponse)
async def add_widget_to_dashboard(
    dashboard_id: uuid.UUID,
    body: DashboardWidgetCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Adds a new widget to an existing dashboard."""
    svc = BusinessIntelligenceService(db)
    return await svc.add_widget(company_id, dashboard_id, body)


# ---------------------------------------------------------------------------
# Insights & Risks
# ---------------------------------------------------------------------------

@router.get("/insights", response_model=List[BIInsightResponse])
async def list_insights(
    limit: int = Query(20, ge=1, le=50),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns AI-generated insights with root-cause explanations."""
    svc = BusinessIntelligenceService(db)
    return await svc.get_company_insights(company_id, limit=limit)


@router.post("/insights/generate", response_model=List[BIInsightResponse])
async def generate_insights(
    body: BIInsightGenerateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Forces generation of new automated insights."""
    svc = BusinessIntelligenceService(db)
    return await svc.generate_insights(company_id, force_refresh=body.force_refresh)


@router.post("/insights/{insight_id}/acknowledge", response_model=BIInsightResponse)
async def acknowledge_insight(
    insight_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Marks an insight as acknowledged."""
    svc = BusinessIntelligenceService(db)
    return await svc.acknowledge_insight(company_id, insight_id, user_id)


@router.get("/risks", response_model=RiskAnalysisResponse)
async def detect_operational_risks(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Scans operations, workflows, tasks, and documents for risks and bottlenecks."""
    svc = BusinessIntelligenceService(db)
    risks = await svc.detect_risks(company_id)
    crit_count = sum(1 for r in risks if r.risk_level == "critical")
    return RiskAnalysisResponse(
        company_id=company_id,
        evaluated_at=uuid.uuid4(),  # placeholder timestamp handled in serializer
        total_risks_detected=len(risks),
        critical_risks_count=crit_count,
        risks=[
            {
                "category": r.category,
                "risk_level": r.risk_level,
                "title": r.title,
                "description": r.description,
                "impact": r.impact,
                "mitigation_step": r.mitigation_step,
                "source_entity": r.source_entity,
            }
            for r in risks
        ],
    )


# ---------------------------------------------------------------------------
# Trends & Forecasts
# ---------------------------------------------------------------------------

@router.get("/trends", response_model=TrendAnalysisResponse)
async def analyze_trends(
    metric_name: str = Query("TASK_COMPLETION_RATE"),
    granularity: str = Query("daily"),
    periods_count: int = Query(12, ge=2, le=50),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Computes time series trends, growth rates, and anomalies."""
    svc = BusinessIntelligenceService(db)
    return await svc.analyze_trends(
        company_id, metric_name=metric_name, granularity=granularity, periods_count=periods_count
    )


@router.post("/forecasts", response_model=List[BIForecastResponse])
async def generate_metric_forecast(
    body: BIForecastRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Generates future projections with confidence bounds."""
    svc = BusinessIntelligenceService(db)
    return await svc.generate_forecast(
        company_id,
        metric_name=body.metric_name,
        periods_ahead=body.periods_ahead,
        methodology=body.methodology,
    )


# ---------------------------------------------------------------------------
# Executive Summary
# ---------------------------------------------------------------------------

@router.post("/executive-summary", response_model=ExecutiveSummaryResponse)
async def generate_executive_summary(
    body: ExecutiveSummaryRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Generates a leadership summary with narrative, key insights, and strategic recommendations."""
    svc = BusinessIntelligenceService(db)
    return await svc.generate_executive_summary(
        company_id, target_role=body.target_role, timeframe=body.timeframe
    )


# ---------------------------------------------------------------------------
# Alerts & Alert Rules
# ---------------------------------------------------------------------------

@router.get("/alerts/rules", response_model=List[BIAlertRuleResponse])
async def list_alert_rules(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists configured alert rules."""
    svc = BusinessIntelligenceService(db)
    return await svc.get_alert_rules(company_id)


@router.post("/alerts/rules", response_model=BIAlertRuleResponse)
async def create_alert_rule(
    body: BIAlertRuleCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new threshold alert rule."""
    svc = BusinessIntelligenceService(db)
    return await svc.create_alert_rule(company_id, user_id, body)


@router.get("/alerts", response_model=List[BIAlertResponse])
async def list_alerts(
    status: Optional[str] = Query(None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists triggered BI alerts."""
    svc = BusinessIntelligenceService(db)
    return await svc.get_alerts(company_id, status=status)


@router.post("/alerts/evaluate", response_model=List[BIAlertResponse])
async def evaluate_alerts(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Evaluates rules against current metric values and triggers alerts."""
    svc = BusinessIntelligenceService(db)
    return await svc.evaluate_alerts(company_id)


@router.post("/alerts/{alert_id}/acknowledge", response_model=BIAlertResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledges an active alert."""
    svc = BusinessIntelligenceService(db)
    return await svc.acknowledge_alert(company_id, alert_id)


@router.post("/alerts/{alert_id}/resolve", response_model=BIAlertResponse)
async def resolve_alert(
    alert_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Resolves an alert."""
    svc = BusinessIntelligenceService(db)
    return await svc.resolve_alert(company_id, alert_id)
