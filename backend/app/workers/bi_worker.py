import asyncio
import uuid
from typing import Dict, Optional

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.services.bi_service import BusinessIntelligenceService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.bi_worker.calculate_company_kpis_task")
def calculate_company_kpis_task(company_id_str: str) -> Dict:
    """Celery background worker for asynchronous KPI calculation."""
    company_id = uuid.UUID(company_id_str)

    async def _run():
        async with async_session_factory() as db:
            svc = BusinessIntelligenceService(db)
            res = await svc.calculate_kpis(company_id)
            return {"success": True, "calculated_count": len(res)}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("bi_kpi_calculation_error", error=str(exc), company_id=company_id_str)
        return {"success": False, "error": str(exc)}


@celery_app.task(name="app.workers.bi_worker.generate_company_insights_task")
def generate_company_insights_task(company_id_str: str) -> Dict:
    """Celery background worker for automated insight generation."""
    company_id = uuid.UUID(company_id_str)

    async def _run():
        async with async_session_factory() as db:
            svc = BusinessIntelligenceService(db)
            res = await svc.generate_insights(company_id, force_refresh=True)
            return {"success": True, "insights_generated": len(res)}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("bi_insight_generation_error", error=str(exc), company_id=company_id_str)
        return {"success": False, "error": str(exc)}


@celery_app.task(name="app.workers.bi_worker.evaluate_alert_rules_task")
def evaluate_alert_rules_task(company_id_str: str) -> Dict:
    """Celery background worker for threshold and anomaly alert evaluation."""
    company_id = uuid.UUID(company_id_str)

    async def _run():
        async with async_session_factory() as db:
            svc = BusinessIntelligenceService(db)
            res = await svc.evaluate_alerts(company_id)
            return {"success": True, "alerts_triggered": len(res)}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("bi_alert_evaluation_error", error=str(exc), company_id=company_id_str)
        return {"success": False, "error": str(exc)}


@celery_app.task(name="app.workers.bi_worker.generate_scheduled_report_task")
def generate_scheduled_report_task(
    company_id_str: str,
    user_id_str: str,
    title: str,
    timeframe: str = "current_month",
    format: str = "markdown",
) -> Dict:
    """Celery background worker for scheduled executive report generation."""
    company_id = uuid.UUID(company_id_str)
    user_id = uuid.UUID(user_id_str)

    async def _run():
        async with async_session_factory() as db:
            svc = BusinessIntelligenceService(db)
            report = await svc.generate_bi_report(
                company_id=company_id,
                user_id=user_id,
                title=title,
                timeframe=timeframe,
                format=format,
            )
            return {"success": True, "report_id": str(report.id), "title": report.title}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("bi_report_generation_error", error=str(exc), company_id=company_id_str)
        return {"success": False, "error": str(exc)}
