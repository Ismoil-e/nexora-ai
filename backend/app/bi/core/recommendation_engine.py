from typing import Any, Dict, List

from app.bi.contracts.types import KPICalculationResult, RiskAlertData


class RecommendationEngine:
    """Generates decision intelligence and proactive recommendations based on KPIs and risks."""

    def generate_recommendations(
        self,
        kpi_results: List[KPICalculationResult],
        risks: List[RiskAlertData],
    ) -> List[Dict[str, Any]]:
        """Produces prioritized actionable recommendations."""
        recommendations: List[Dict[str, Any]] = []

        # Process risks into recommendations
        for risk in risks:
            if risk.risk_level == "critical":
                recommendations.append({
                    "action": f"Favqulodda chora: {risk.title}",
                    "priority": "high",
                    "rationale": risk.description,
                    "expected_impact": "Operatsion xavflarni va muddat buzilishini oldini oladi.",
                    "mitigation": risk.mitigation_step,
                    "target_module": risk.category,
                })
            elif risk.risk_level == "warning":
                recommendations.append({
                    "action": f"Ko'rib chiqish: {risk.title}",
                    "priority": "medium",
                    "rationale": risk.description,
                    "expected_impact": "Ish jarayonlari tezligi va samaradorligini oshiradi.",
                    "mitigation": risk.mitigation_step,
                    "target_module": risk.category,
                })

        # Process KPI bottlenecks
        for kpi in kpi_results:
            if kpi.status == "critical":
                recommendations.append({
                    "action": f"{kpi.name} ko'rsatkichini me'yorga qaytarish",
                    "priority": "high",
                    "rationale": f"Joriy qiymat ({kpi.current_value}{kpi.unit}) kritik chegaradan ({kpi.critical_threshold}{kpi.unit}) chetga chiqqan.",
                    "expected_impact": f"{kpi.name} bo'yicha barqarorlikni tiklash.",
                    "mitigation": "Tegishli bo'lim rahbari bilan tezkor yig'ilish o'tkazish.",
                    "target_module": kpi.category,
                })

        # If everything is optimal, provide strategic growth recommendations
        if len(recommendations) == 0:
            recommendations.append({
                "action": "AI agentlar avtomatlashtirish qamrovini kengaytirish",
                "priority": "low",
                "rationale": "Kompaniya operatsion ko'rsatkichlari barqaror, yangi avtomatlashtirish imkoniyatlari mavjud.",
                "expected_impact": "Xodimlarning vaqtini strategik vazifalarga bo'shatish.",
                "mitigation": "Yangi ish oqimlari (Workflows) va hisobot shablonlarini joriy etish.",
                "target_module": "operations",
            })

        return recommendations


recommendation_engine = RecommendationEngine()
