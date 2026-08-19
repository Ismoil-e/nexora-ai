import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bi.contracts.types import (
    ForecastData,
    InsightData,
    KPICalculationResult,
    KPICategory,
    KPIStatus,
    RiskAlertData,
    SeverityLevel,
    TrendDirection,
)
from app.bi.core.alert_engine import AlertEngine
from app.bi.core.executive_summary_engine import ExecutiveSummaryEngine
from app.bi.core.forecast_engine import ForecastEngine
from app.bi.core.insight_engine import InsightEngine
from app.bi.core.kpi_engine import KPIEngine
from app.bi.core.recommendation_engine import RecommendationEngine
from app.bi.core.report_generator import BIReportGenerator
from app.bi.core.risk_engine import RiskDetectionEngine
from app.bi.core.trend_engine import TrendEngine
from app.workflows.contracts.types import ActionContext


def test_trend_engine_analysis_growing_and_anomalies():
    engine = TrendEngine()
    # Steady growth with one outlier spike
    values = [10.0, 12.0, 14.0, 16.0, 18.0, 95.0, 22.0]
    labels = [f"Day {i+1}" for i in range(len(values))]

    res = engine.analyze_series(values, labels, granularity="daily", anomaly_threshold_std=1.5)
    assert res["trend_direction"] in [TrendDirection.GROWING.value, TrendDirection.VOLATILE.value]
    assert res["average_value"] > 0
    assert res["anomalies_detected"] >= 1
    assert len(res["series"]) == len(values)
    assert res["growth_rate_pct"] > 0


def test_trend_engine_stable_series():
    engine = TrendEngine()
    values = [50.0, 50.2, 49.8, 50.1, 50.0]
    labels = ["P1", "P2", "P3", "P4", "P5"]

    res = engine.analyze_series(values, labels)
    assert res["trend_direction"] == TrendDirection.STABLE.value
    assert res["anomalies_detected"] == 0
    assert abs(res["growth_rate_pct"]) < 1.0


def test_forecast_engine_linear_trend():
    engine = ForecastEngine()
    historical = [10.0, 20.0, 30.0, 40.0, 50.0]
    forecasts = engine.forecast_metric(
        metric_name="workload",
        historical_values=historical,
        periods_ahead=3,
        methodology="linear_trend",
    )

    assert len(forecasts) == 3
    # Step 1 should be approx 60.0, Step 2 approx 70.0
    assert forecasts[0].predicted_value >= 55.0
    assert forecasts[1].predicted_value >= forecasts[0].predicted_value
    assert forecasts[0].confidence_score > 0.5
    assert forecasts[0].lower_bound is not None
    assert forecasts[0].upper_bound is not None
    assert forecasts[0].lower_bound <= forecasts[0].predicted_value <= forecasts[0].upper_bound


def test_forecast_engine_empty_history_fallback():
    engine = ForecastEngine()
    forecasts = engine.forecast_metric(metric_name="tasks", historical_values=[], periods_ahead=2)
    assert len(forecasts) == 2
    assert forecasts[0].predicted_value > 0


def test_insight_engine_generates_causality():
    engine = InsightEngine()
    kpi_results = [
        KPICalculationResult(
            code="OVERDUE_TASKS_COUNT",
            name="Muddati O'tgan Vazifalar",
            category=KPICategory.OPERATIONS.value,
            current_value=12.0,
            previous_value=0.0,
            change_pct=None,
            status=KPIStatus.CRITICAL.value,
            unit="ta",
            target_value=0.0,
            warning_threshold=5.0,
            critical_threshold=10.0,
        ),
        KPICalculationResult(
            code="TASK_COMPLETION_RATE",
            name="Vazifalar Bajarilish Ko'rsatkichi",
            category=KPICategory.OPERATIONS.value,
            current_value=68.0,
            previous_value=85.0,
            change_pct=-20.0,
            status=KPIStatus.WARNING.value,
            unit="%",
            target_value=90.0,
            warning_threshold=75.0,
            critical_threshold=60.0,
        ),
    ]

    mock_db = MagicMock()
    insights = asyncio_run(engine.generate_insights(mock_db, uuid.uuid4(), kpi_results))

    assert len(insights) >= 2
    critical_insights = [i for i in insights if i.severity == SeverityLevel.CRITICAL.value]
    assert len(critical_insights) >= 1
    assert "vazifa muddati o'tib ketgan" in critical_insights[0].title
    assert "Kechikishlar sababi" in critical_insights[0].explanation
    assert len(critical_insights[0].recommended_actions) > 0


def test_recommendation_engine_maps_risks_and_kpis():
    engine = RecommendationEngine()
    kpi_results = [
        KPICalculationResult(
            code="WORKFLOW_SUCCESS_RATE",
            name="Ish Oqimlari Muvaffaqiyat Foizi",
            category=KPICategory.OPERATIONS.value,
            current_value=72.0,
            previous_value=100.0,
            change_pct=-28.0,
            status="critical",
            unit="%",
            critical_threshold=80.0,
        )
    ]
    risks = [
        RiskAlertData(
            category="operations",
            risk_level="critical",
            title="Kechikkan muhim shartnomalar",
            description="5 ta yirik shartnoma tasdig'i kechikmoqda",
            impact="Kompaniyaga jarima xavfi",
            mitigation_step="Yuristlar bilan tezkor ko'rib chiqish",
        )
    ]

    recs = engine.generate_recommendations(kpi_results, risks)
    assert len(recs) == 2
    high_pri = [r for r in recs if r["priority"] == "high"]
    assert len(high_pri) == 2
    assert "Favqulodda chora" in high_pri[0]["action"]


def test_report_generator_markdown_formatting():
    gen = BIReportGenerator()
    exec_summary = {
        "overall_health": "good",
        "executive_narrative": "Kompaniya ko'rsatkichlari barqaror o'smoqda.",
        "key_insights": ["Vazifalar 95% bajarildi", "Hujjatlar intellekti muvaffaqiyatli indekslandi"],
        "actionable_recommendations": [
            {"action": "AI Agent qamrovini kengaytirish", "priority": "high", "rationale": "Ish tezligini oshiradi"}
        ],
        "source_citations": [
            {"title": "Nexora KPI Engine", "source_type": "database", "timestamp": "2026-08-20"}
        ],
    }
    kpis = [
        {"code": "TASK_COMPLETION_RATE", "name": "Vazifalar Bajarilishi", "current_value": 95.0, "unit": "%", "status": "healthy", "change_pct": 5.0}
    ]
    insights = [{"title": "Yuqori unumdorlik", "summary": "Xodimlar faolligi oshgan", "severity": "info"}]
    risks = []

    md = gen.format_markdown_report(
        title="Oylik Boshqaruv Hisoboti",
        company_name="Nexora Enterprise",
        timeframe="2026-August",
        executive_summary=exec_summary,
        kpis=kpis,
        insights=insights,
        risks=risks,
    )

    assert "# 📊 Oylik Boshqaruv Hisoboti" in md
    assert "Nexora Enterprise" in md
    assert "TASK_COMPLETION_RATE" in md
    assert "AI Agent qamrovini kengaytirish" in md
    assert "Nexora KPI Engine" in md


def test_bi_tools_registry():
    from app.ai.agents.tools import ToolRegistry

    registry = ToolRegistry()
    assert registry.get_tool("query_company_kpis") is not None
    assert registry.get_tool("get_business_insights") is not None
    assert registry.get_tool("generate_executive_summary") is not None
    assert registry.get_tool("detect_operational_risks") is not None


def test_bi_workflow_actions_registered():
    from app.workflows.actions.builtin import DEFAULT_ACTIONS

    action_keys = {a.action_key for a in DEFAULT_ACTIONS}
    assert "calculate_kpis" in action_keys
    assert "generate_insights" in action_keys
    assert "evaluate_alert_rules" in action_keys
    assert "generate_executive_summary" in action_keys
    assert "generate_bi_report" in action_keys


def asyncio_run(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
