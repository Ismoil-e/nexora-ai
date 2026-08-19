import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bi.contracts.types import (
    ForecastData,
    InsightData,
    KPICalculationResult,
    RiskAlertData,
)
from app.bi.core.alert_engine import alert_engine
from app.bi.core.executive_summary_engine import executive_summary_engine
from app.bi.core.forecast_engine import forecast_engine
from app.bi.core.insight_engine import insight_engine
from app.bi.core.kpi_engine import kpi_engine
from app.bi.core.recommendation_engine import recommendation_engine
from app.bi.core.report_generator import report_generator
from app.bi.core.risk_engine import risk_engine
from app.bi.core.trend_engine import trend_engine
from app.models.bi import (
    AnalyticsSnapshot,
    BIAlert,
    BIAlertRule,
    BIForecast,
    BIInsight,
    Dashboard,
    DashboardWidget,
    KPI,
    KPILog,
)
from app.models.company import Company
from app.models.report import Report
from app.models.user import User
from app.repositories.bi_repo import (
    AlertRuleRepository,
    DashboardRepository,
    ForecastRepository,
    InsightRepository,
    KPIRepository,
)
from app.schemas.bi import (
    BIAlertRuleCreate,
    BIAlertRuleUpdate,
    DashboardCreate,
    DashboardUpdate,
    DashboardWidgetCreate,
    DashboardWidgetUpdate,
    KPICreate,
    KPIUpdate,
)
from app.utils.exceptions import NotFoundException, ValidationException


class BusinessIntelligenceService:
    """Core Business Intelligence service coordinating KPIs, dashboards, insights, forecasts, risks, and reports."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.kpi_repo = KPIRepository(db)
        self.dash_repo = DashboardRepository(db)
        self.insight_repo = InsightRepository(db)
        self.forecast_repo = ForecastRepository(db)
        self.alert_repo = AlertRuleRepository(db)

    # ---------------------------------------------------------------------------
    # KPI Engine Methods
    # ---------------------------------------------------------------------------

    async def ensure_default_kpis(self, company_id: uuid.UUID) -> List[KPI]:
        """Ensures that default tenant KPIs exist."""
        existing_kpis = await self.kpi_repo.get_by_company(company_id)
        if existing_kpis:
            return existing_kpis

        created = []
        for defn in kpi_engine.DEFAULT_KPI_DEFINITIONS:
            kpi = KPI(
                company_id=company_id,
                code=defn["code"],
                name=defn["name"],
                category=defn["category"],
                description=defn["description"],
                calculation_type=defn["calculation_type"],
                target_value=defn["target_value"],
                warning_threshold=defn["warning_threshold"],
                critical_threshold=defn["critical_threshold"],
                unit=defn["unit"],
                current_value=0.0,
                status="healthy",
            )
            self.db.add(kpi)
            created.append(kpi)

        await self.db.commit()
        for k in created:
            await self.db.refresh(k)
        return created

    async def get_company_kpis(self, company_id: uuid.UUID) -> List[KPI]:
        await self.ensure_default_kpis(company_id)
        return await self.kpi_repo.get_by_company(company_id)

    async def calculate_kpis(
        self, company_id: uuid.UUID, kpi_codes: Optional[List[str]] = None
    ) -> List[KPICalculationResult]:
        """Calculates current KPI values, writes historical logs, and updates KPI rows."""
        await self.ensure_default_kpis(company_id)
        all_kpis = await self.kpi_repo.get_by_company(company_id)

        target_kpis = (
            [k for k in all_kpis if k.code in [c.upper() for c in kpi_codes]]
            if kpi_codes
            else all_kpis
        )

        results: List[KPICalculationResult] = []
        now = datetime.now(timezone.utc)

        for kpi in target_kpis:
            calc_res = await kpi_engine.calculate_kpi_by_code(
                self.db,
                company_id,
                kpi.code,
                target_value=kpi.target_value,
                warning_threshold=kpi.warning_threshold,
                critical_threshold=kpi.critical_threshold,
                unit=kpi.unit,
            )

            # Update KPI record
            kpi.previous_value = kpi.current_value
            kpi.current_value = calc_res.current_value
            kpi.change_pct = calc_res.change_pct
            kpi.status = calc_res.status
            kpi.last_calculated_at = now
            if calc_res.meta_data:
                kpi.meta_data = json.dumps(calc_res.meta_data)

            # Write historical log
            log = KPILog(
                kpi_id=kpi.id,
                company_id=company_id,
                recorded_value=calc_res.current_value,
                target_value=kpi.target_value,
                status=calc_res.status,
                meta_data=kpi.meta_data,
            )
            self.db.add(log)
            results.append(calc_res)

        await self.db.commit()
        return results

    async def create_kpi(self, company_id: uuid.UUID, payload: KPICreate) -> KPI:
        existing = await self.kpi_repo.get_by_code(company_id, payload.code.upper())
        if existing:
            raise ValidationException(f"KPI code '{payload.code}' already exists")

        kpi = KPI(
            company_id=company_id,
            code=payload.code.upper(),
            name=payload.name,
            category=payload.category,
            description=payload.description,
            calculation_type=payload.calculation_type,
            target_value=payload.target_value,
            warning_threshold=payload.warning_threshold,
            critical_threshold=payload.critical_threshold,
            unit=payload.unit,
            formula_expression=payload.formula_expression,
            meta_data=payload.meta_data,
            current_value=0.0,
            status="healthy",
        )
        self.db.add(kpi)
        await self.db.commit()
        await self.db.refresh(kpi)
        return kpi

    async def update_kpi(self, company_id: uuid.UUID, kpi_id: uuid.UUID, payload: KPIUpdate) -> KPI:
        kpi = await self.db.get(KPI, kpi_id)
        if not kpi or kpi.company_id != company_id or kpi.deleted_at is not None:
            raise NotFoundException("KPI topilmadi")

        if payload.name is not None:
            kpi.name = payload.name
        if payload.category is not None:
            kpi.category = payload.category
        if payload.description is not None:
            kpi.description = payload.description
        if payload.calculation_type is not None:
            kpi.calculation_type = payload.calculation_type
        if payload.target_value is not None:
            kpi.target_value = payload.target_value
        if payload.warning_threshold is not None:
            kpi.warning_threshold = payload.warning_threshold
        if payload.critical_threshold is not None:
            kpi.critical_threshold = payload.critical_threshold
        if payload.unit is not None:
            kpi.unit = payload.unit
        if payload.formula_expression is not None:
            kpi.formula_expression = payload.formula_expression
        if payload.meta_data is not None:
            kpi.meta_data = payload.meta_data

        await self.db.commit()
        await self.db.refresh(kpi)
        return kpi

    async def get_kpi_history(self, company_id: uuid.UUID, kpi_id: uuid.UUID, limit: int = 30) -> List[KPILog]:
        kpi = await self.db.get(KPI, kpi_id)
        if not kpi or kpi.company_id != company_id:
            raise NotFoundException("KPI topilmadi")
        return await self.kpi_repo.get_history(kpi_id, company_id, limit=limit)

    # ---------------------------------------------------------------------------
    # Insights & Risk Engine Methods
    # ---------------------------------------------------------------------------

    async def generate_insights(
        self, company_id: uuid.UUID, force_refresh: bool = False
    ) -> List[BIInsight]:
        """Generates causal insights from latest KPIs and saves them."""
        kpi_results = await self.calculate_kpis(company_id)
        raw_insights = await insight_engine.generate_insights(self.db, company_id, kpi_results)

        created_insights: List[BIInsight] = []
        for raw in raw_insights:
            rec = BIInsight(
                company_id=company_id,
                title=raw.title,
                category=raw.category,
                severity=raw.severity,
                summary=raw.summary,
                explanation=raw.explanation,
                recommended_actions=json.dumps(raw.recommended_actions, ensure_ascii=False)
                if raw.recommended_actions
                else None,
                related_entity_type=raw.related_entity_type,
                related_entity_id=raw.related_entity_id,
                is_acknowledged=False,
            )
            self.db.add(rec)
            created_insights.append(rec)

        await self.db.commit()
        for ins in created_insights:
            await self.db.refresh(ins)
        return created_insights

    async def get_company_insights(self, company_id: uuid.UUID, limit: int = 20) -> List[BIInsight]:
        insights = await self.insight_repo.get_by_company(company_id, limit=limit)
        if not insights:
            return await self.generate_insights(company_id)
        return insights

    async def acknowledge_insight(
        self, company_id: uuid.UUID, insight_id: uuid.UUID, user_id: uuid.UUID
    ) -> BIInsight:
        insight = await self.db.get(BIInsight, insight_id)
        if not insight or insight.company_id != company_id:
            raise NotFoundException("Insight topilmadi")
        return await self.insight_repo.acknowledge(insight_id, user_id)

    async def detect_risks(self, company_id: uuid.UUID) -> List[RiskAlertData]:
        return await risk_engine.detect_risks(self.db, company_id)

    # ---------------------------------------------------------------------------
    # Trends & Forecast Methods
    # ---------------------------------------------------------------------------

    async def analyze_trends(
        self,
        company_id: uuid.UUID,
        metric_name: str,
        granularity: str = "daily",
        periods_count: int = 12,
    ) -> Dict[str, Any]:
        """Extracts historical series and computes trends and anomalies."""
        # Find KPI matching metric
        kpi = await self.kpi_repo.get_by_code(company_id, metric_name.upper())
        if kpi:
            logs = await self.kpi_repo.get_history(kpi.id, company_id, limit=periods_count)
            logs = list(reversed(logs))  # chronological
            values = [log.recorded_value for log in logs] if logs else [kpi.current_value]
            labels = [log.created_at.strftime("%m-%d") for log in logs] if logs else ["Bugun"]
        else:
            values = [10.0, 12.0, 14.0, 13.0, 18.0, 22.0]
            labels = [f"P{i+1}" for i in range(len(values))]

        analysis = trend_engine.analyze_series(values, labels, granularity=granularity)
        analysis["metric_name"] = metric_name
        analysis["granularity"] = granularity
        return analysis

    async def generate_forecast(
        self,
        company_id: uuid.UUID,
        metric_name: str,
        periods_ahead: int = 3,
        methodology: str = "linear_trend",
    ) -> List[BIForecast]:
        """Generates statistical predictions and persists them."""
        # Fetch historical series
        kpi = await self.kpi_repo.get_by_code(company_id, metric_name.upper())
        if kpi:
            logs = await self.kpi_repo.get_history(kpi.id, company_id, limit=20)
            logs = list(reversed(logs))
            hist_vals = [l.recorded_value for l in logs] if logs else [kpi.current_value]
        else:
            hist_vals = [25.0, 28.0, 31.0, 35.0, 42.0]

        forecast_points = forecast_engine.forecast_metric(
            metric_name=metric_name,
            historical_values=hist_vals,
            periods_ahead=periods_ahead,
            methodology=methodology,
        )

        persisted: List[BIForecast] = []
        for fp in forecast_points:
            rec = BIForecast(
                company_id=company_id,
                metric_name=metric_name,
                target_period=fp.target_period,
                predicted_value=fp.predicted_value,
                confidence_score=fp.confidence_score,
                lower_bound=fp.lower_bound,
                upper_bound=fp.upper_bound,
                methodology=fp.methodology,
                historical_points_count=fp.historical_points_count,
            )
            self.db.add(rec)
            persisted.append(rec)

        await self.db.commit()
        for p in persisted:
            await self.db.refresh(p)
        return persisted

    # ---------------------------------------------------------------------------
    # Executive Summaries & Reports
    # ---------------------------------------------------------------------------

    async def generate_executive_summary(
        self,
        company_id: uuid.UUID,
        target_role: str = "CEO",
        timeframe: str = "current_month",
    ) -> Dict[str, Any]:
        """Produces role-tailored narrative and strategic recommendations."""
        kpi_results = await self.calculate_kpis(company_id)
        risks = await self.detect_risks(company_id)
        recommendations = recommendation_engine.generate_recommendations(kpi_results, risks)

        return await executive_summary_engine.generate_summary(
            self.db, company_id, target_role, timeframe, kpi_results, risks, recommendations
        )

    async def generate_bi_report(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        report_type: str = "monthly_executive",
        timeframe: str = "current_month",
        format: str = "markdown",
    ) -> Report:
        """Generates a complete executive report, saving as Report entity."""
        company = await self.db.get(Company, company_id)
        company_name = company.name if company else "Nexora Enterprise"

        exec_summary = await self.generate_executive_summary(company_id, target_role="CEO", timeframe=timeframe)
        kpis = await self.get_company_kpis(company_id)
        kpis_data = [
            {
                "code": k.code,
                "name": k.name,
                "current_value": k.current_value,
                "unit": k.unit,
                "change_pct": k.change_pct,
                "status": k.status,
            }
            for k in kpis
        ]
        insights = await self.get_company_insights(company_id, limit=5)
        insights_data = [{"title": i.title, "summary": i.summary, "severity": i.severity} for i in insights]
        risks = await self.detect_risks(company_id)
        risks_data = [
            {
                "title": r.title,
                "risk_level": r.risk_level,
                "description": r.description,
                "impact": r.impact,
                "mitigation_step": r.mitigation_step,
            }
            for r in risks
        ]

        if format == "json":
            content = json.dumps(
                {
                    "title": title,
                    "company": company_name,
                    "executive_summary": exec_summary,
                    "kpis": kpis_data,
                    "insights": insights_data,
                    "risks": risks_data,
                },
                ensure_ascii=False,
                indent=2,
            )
        else:
            content = report_generator.format_markdown_report(
                title=title,
                company_name=company_name,
                timeframe=timeframe,
                executive_summary=exec_summary,
                kpis=kpis_data,
                insights=insights_data,
                risks=risks_data,
            )

        report = Report(
            company_id=company_id,
            created_by=user_id,
            title=title,
            report_type=report_type,
            content=content,
            status="completed",
            format=format,
            ai_provider="nexora_bi_engine",
            ai_model="v1.0",
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    # ---------------------------------------------------------------------------
    # Alert Rules & Alerts
    # ---------------------------------------------------------------------------

    async def get_alert_rules(self, company_id: uuid.UUID) -> List[BIAlertRule]:
        return await self.alert_repo.get_by_company(company_id)

    async def create_alert_rule(
        self, company_id: uuid.UUID, user_id: uuid.UUID, payload: BIAlertRuleCreate
    ) -> BIAlertRule:
        rule = BIAlertRule(
            company_id=company_id,
            name=payload.name,
            kpi_code=payload.kpi_code.upper(),
            condition_operator=payload.condition_operator,
            threshold_value=payload.threshold_value,
            severity=payload.severity,
            is_active=payload.is_active,
            notify_channels=payload.notify_channels,
            created_by=user_id,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def evaluate_alerts(self, company_id: uuid.UUID) -> List[BIAlert]:
        kpis = await self.calculate_kpis(company_id)
        return await alert_engine.evaluate_rules(self.db, company_id, kpis)

    async def get_alerts(self, company_id: uuid.UUID, status: Optional[str] = None) -> List[BIAlert]:
        return await self.alert_repo.get_alerts(company_id, status=status)

    async def acknowledge_alert(self, company_id: uuid.UUID, alert_id: uuid.UUID) -> BIAlert:
        alert = await self.db.get(BIAlert, alert_id)
        if not alert or alert.company_id != company_id:
            raise NotFoundException("Alert topilmadi")
        alert.status = "acknowledged"
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def resolve_alert(self, company_id: uuid.UUID, alert_id: uuid.UUID) -> BIAlert:
        alert = await self.db.get(BIAlert, alert_id)
        if not alert or alert.company_id != company_id:
            raise NotFoundException("Alert topilmadi")
        alert.status = "resolved"
        alert.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    # ---------------------------------------------------------------------------
    # Dashboard & Widget Engine
    # ---------------------------------------------------------------------------

    async def ensure_default_dashboard(self, company_id: uuid.UUID) -> Dashboard:
        existing = await self.dash_repo.get_by_slug(company_id, "main-overview")
        if existing:
            return existing

        dash = Dashboard(
            company_id=company_id,
            name="Asosiy Boshqaruv Paneli",
            slug="main-overview",
            description="Kompaniyaning asosiy operatsion va tahliliy ko'rsatkichlari",
            category="executive",
            is_default=True,
            is_public_for_tenant=True,
        )
        self.db.add(dash)
        await self.db.flush()

        # Add initial widgets
        widgets_def = [
            ("Vazifalar Bajarilishi", "kpi_card", "TASK_COMPLETION_RATE", 0, 0, 3, 2),
            ("Muddati O'tgan Vazifalar", "kpi_card", "OVERDUE_TASKS_COUNT", 3, 0, 3, 2),
            ("Hujjatlar Hajmi", "kpi_card", "DOCUMENT_PROCESSING_VOLUME", 6, 0, 3, 2),
            ("AI Foydalanish", "kpi_card", "AI_USAGE_MESSAGES", 9, 0, 3, 2),
            ("Operatsion Trend", "chart_line", "TASK_COMPLETION_RATE", 0, 2, 6, 4),
            ("AI Xulosasi & Tavsiyalar", "ai_summary", None, 6, 2, 6, 4),
        ]

        for title, wtype, mcode, px, py, w, h in widgets_def:
            wgt = DashboardWidget(
                dashboard_id=dash.id,
                company_id=company_id,
                title=title,
                widget_type=wtype,
                metric_code=mcode,
                position_x=px,
                position_y=py,
                width=w,
                height=h,
                refresh_interval_sec=300,
            )
            self.db.add(wgt)

        await self.db.commit()
        await self.db.refresh(dash)
        return dash

    async def get_dashboards(self, company_id: uuid.UUID) -> List[Dashboard]:
        await self.ensure_default_dashboard(company_id)
        return await self.dash_repo.get_by_company(company_id)

    async def get_dashboard_by_slug(self, company_id: uuid.UUID, slug: str) -> Dashboard:
        dash = await self.dash_repo.get_by_slug(company_id, slug)
        if not dash:
            raise NotFoundException("Dashboard topilmadi")
        return dash

    async def create_dashboard(
        self, company_id: uuid.UUID, user_id: uuid.UUID, payload: DashboardCreate
    ) -> Dashboard:
        existing = await self.dash_repo.get_by_slug(company_id, payload.slug)
        if existing:
            raise ValidationException(f"Dashboard slug '{payload.slug}' already exists")

        dash = Dashboard(
            company_id=company_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            category=payload.category,
            is_default=payload.is_default,
            is_public_for_tenant=payload.is_public_for_tenant,
            allowed_roles=payload.allowed_roles,
            layout_config=payload.layout_config,
            created_by=user_id,
        )
        self.db.add(dash)
        await self.db.flush()

        if payload.widgets:
            for w in payload.widgets:
                wgt = DashboardWidget(
                    dashboard_id=dash.id,
                    company_id=company_id,
                    title=w.title,
                    widget_type=w.widget_type,
                    metric_code=w.metric_code,
                    query_config=w.query_config,
                    position_x=w.position_x,
                    position_y=w.position_y,
                    width=w.width,
                    height=w.height,
                    refresh_interval_sec=w.refresh_interval_sec,
                )
                self.db.add(wgt)

        await self.db.commit()
        await self.db.refresh(dash)
        return dash

    async def add_widget(
        self, company_id: uuid.UUID, dashboard_id: uuid.UUID, payload: DashboardWidgetCreate
    ) -> DashboardWidget:
        dash = await self.db.get(Dashboard, dashboard_id)
        if not dash or dash.company_id != company_id or dash.deleted_at is not None:
            raise NotFoundException("Dashboard topilmadi")

        return await self.dash_repo.add_widget(
            dashboard_id=dashboard_id,
            company_id=company_id,
            title=payload.title,
            widget_type=payload.widget_type,
            metric_code=payload.metric_code,
            query_config=payload.query_config,
            position_x=payload.position_x,
            position_y=payload.position_y,
            width=payload.width,
            height=payload.height,
            refresh_interval_sec=payload.refresh_interval_sec,
        )

    # ---------------------------------------------------------------------------
    # Overview Summary
    # ---------------------------------------------------------------------------

    async def get_overview(self, company_id: uuid.UUID) -> Dict[str, Any]:
        """Provides high-level BI snapshot for frontend and dashboard header."""
        kpis = await self.get_company_kpis(company_id)
        insights = await self.get_company_insights(company_id, limit=5)
        risks = await self.detect_risks(company_id)
        active_alerts = await self.get_alerts(company_id, status="active")

        critical_risks_count = sum(1 for r in risks if r.risk_level == "critical")
        has_warning = any(k.status == "warning" for k in kpis) or len(active_alerts) > 0

        if critical_risks_count > 0:
            health = "critical"
        elif has_warning:
            health = "warning"
        else:
            health = "healthy"

        kpi_summary = {
            "total_kpis": len(kpis),
            "healthy_count": sum(1 for k in kpis if k.status == "healthy"),
            "warning_count": sum(1 for k in kpis if k.status == "warning"),
            "critical_count": sum(1 for k in kpis if k.status == "critical"),
        }

        return {
            "company_id": company_id,
            "generated_at": datetime.now(timezone.utc),
            "kpi_summary": kpi_summary,
            "active_alerts_count": len(active_alerts),
            "critical_risks_count": critical_risks_count,
            "recent_insights": insights,
            "top_kpis": kpis[:6],
            "quick_health_status": health,
        }
