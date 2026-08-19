from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bi.contracts.types import KPICalculationResult, RiskAlertData
from app.models.company import Company
from app.models.document import Document
from app.models.task import Task


class ExecutiveSummaryEngine:
    """Generates role-tailored executive summaries integrating metrics, risks, and organizational context."""

    async def generate_summary(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        target_role: str,
        timeframe: str,
        kpi_results: List[KPICalculationResult],
        risks: List[RiskAlertData],
        recommendations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Synthesizes executive brief for a leadership role."""
        company = await db.get(Company, company_id)
        company_name = company.name if company else "Kompaniya"

        now = datetime.now(timezone.utc)

        # Classify overall health
        has_critical_kpi = any(k.status == "critical" for k in kpi_results)
        has_critical_risk = any(r.risk_level == "critical" for r in risks)
        has_warning = any(k.status == "warning" for k in kpi_results) or any(r.risk_level == "warning" for r in risks)

        if has_critical_kpi or has_critical_risk:
            overall_health = "critical"
        elif has_warning:
            overall_health = "warning"
        else:
            overall_health = "good"

        # Build metrics summary dict
        metrics_summary = {
            k.code: {
                "name": k.name,
                "value": k.current_value,
                "unit": k.unit,
                "status": k.status,
                "change_pct": k.change_pct,
            }
            for k in kpi_results
        }

        # Synthesize role-specific narrative
        role_upper = (target_role or "CEO").upper()
        if "CFO" in role_upper or "FINANCE" in role_upper:
            narrative = (
                f"{company_name} moliyaviy va resurs samaradorligi tahlili ({timeframe}): "
                f"Tizimda hujjatlar va ish oqimlari operatsion xarajatlarni optimallashtirishga xizmat qilmoqda. "
                f"Umumiy holat: {overall_health.upper()}."
            )
        elif "COO" in role_upper or "OPERATIONS" in role_upper:
            narrative = (
                f"{company_name} operatsion holati ({timeframe}): "
                f"Vazifalar ijrosi va jarayonlar monitoringi tahlil qilindi. "
                f"Aniqlangan operatsion xatarlar soni: {len(risks)} ta. "
                f"Umumiy operatsion holat: {overall_health.upper()}."
            )
        elif "HR" in role_upper:
            narrative = (
                f"{company_name} inson resurslari va jamoa faolligi sharhi ({timeframe}): "
                f"Xodimlarning tizimdagi faolligi va vazifalarga bo'lgan yuklamasi baholandi. "
                f"Faoliyat barqarorligi: {overall_health.upper()}."
            )
        else:
            # Default CEO Summary
            narrative = (
                f"{company_name} Boshqaruv Kengashi uchun Tezkor Ijroiy Hisobot ({timeframe}): "
                f"Barcha asosiy biznes ko'rsatkichlari (KPI), hujjatlar aylanishi va avtomatlashtirilgan "
                f"jarayonlar holati tahlil qilindi. Tizimning umumiy holati '{overall_health.upper()}' darajasida baholandi. "
                f"Hozirda {len(risks)} ta e'tibor talab qiluvchi xatar va {len(recommendations)} ta strategik tavsiya shakllantirildi."
            )

        key_insights = [
            f"Vazifalar bajarilishi: {metrics_summary.get('TASK_COMPLETION_RATE', {}).get('value', 0)}% (Maqsad: 90%)",
            f"Muddati o'tgan vazifalar: {metrics_summary.get('OVERDUE_TASKS_COUNT', {}).get('value', 0)} ta",
            f"Hujjatlar intellekti hajmi: {metrics_summary.get('DOCUMENT_PROCESSING_VOLUME', {}).get('value', 0)} ta hujjat indekslangan",
        ]

        critical_risks = [f"[{r.risk_level.upper()}] {r.title}: {r.mitigation_step}" for r in risks]

        # Citations
        citations = [
            {"source_type": "database_kpi", "title": "Nexora KPI Engine", "timestamp": str(now)},
            {"source_type": "system_operations", "title": "Nexora Workflow & Task Engine", "timestamp": str(now)},
        ]

        return {
            "target_role": target_role,
            "timeframe": timeframe,
            "generated_at": now,
            "overall_health": overall_health,
            "key_metrics_summary": metrics_summary,
            "executive_narrative": narrative,
            "key_insights": key_insights,
            "critical_risks": critical_risks,
            "actionable_recommendations": recommendations,
            "source_citations": citations,
        }


executive_summary_engine = ExecutiveSummaryEngine()
