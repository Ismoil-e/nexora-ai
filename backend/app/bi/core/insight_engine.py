import json
import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.bi.contracts.types import InsightData, KPICalculationResult, SeverityLevel
from app.bi.core.kpi_engine import kpi_engine


class InsightEngine:
    """Generates automated business insights with causality explanations ('Why' it happened)."""

    async def generate_insights(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        kpi_results: List[KPICalculationResult],
    ) -> List[InsightData]:
        """Analyzes calculated KPIs and operational health to produce causal insights."""
        insights: List[InsightData] = []

        for kpi in kpi_results:
            # 1. Overdue Tasks Analysis
            if kpi.code == "OVERDUE_TASKS_COUNT" and kpi.current_value > 0:
                severity = SeverityLevel.CRITICAL.value if kpi.current_value >= 10 else SeverityLevel.WARNING.value
                insights.append(
                    InsightData(
                        title=f"{int(kpi.current_value)} ta vazifa muddati o'tib ketgan",
                        category="operations",
                        severity=severity,
                        summary=f"Kompaniyada {int(kpi.current_value)} ta topshiriq belgilangan ijro muddatidan kechikmoqda.",
                        explanation=(
                            "Kechikishlar sababi: Asosiy topshiriqlar bo'yicha mas'ul xodimlar yuklamasining yuqoriligi "
                            "yoki zarur hujjatlar tasdig'ining o'z vaqtida yakunlanmaganligi bilan bog'liq."
                        ),
                        recommended_actions=[
                            "Muddati o'tgan vazifalarni zudlik bilan qayta ko'rib chiqish va mas'ullarni ogohlantirish",
                            "Yuklamani bo'limlar bo'yicha qayta taqsimlash",
                            "Avtomatik eslatma (Reminder) ish oqimini yoqish",
                        ],
                        related_entity_type="Task",
                    )
                )

            # 2. Task Completion Rate Drop
            elif kpi.code == "TASK_COMPLETION_RATE" and kpi.current_value < 75.0:
                insights.append(
                    InsightData(
                        title="Vazifalar bajarilish samaradorligi pasaydi",
                        category="operations",
                        severity=SeverityLevel.WARNING.value,
                        summary=f"Vazifalar yakunlanish foizi {kpi.current_value}% ga tushib, maqsadli {kpi.target_value}% dan past.",
                        explanation=(
                            "Sabab: Yangi kiritilgan loyihalar hajmi oshishi bilan mavjud xodimlarning "
                            "bir vaqtda bir nechta murakkab topshiriqlar bilan band bo'lib qolgani."
                        ),
                        recommended_actions=[
                            "Muhimlik darajasi yuqori (High Priority) vazifalarga ustuvorlik berish",
                            "Qo'shimcha resurs yoki subagentlarni jalb qilish",
                        ],
                        related_entity_type="Task",
                    )
                )

            # 3. Workflow Success Rate Issues
            elif kpi.code == "WORKFLOW_SUCCESS_RATE" and kpi.current_value < 95.0:
                insights.append(
                    InsightData(
                        title="Avtomatlashtirilgan jarayonlarda xatoliklar aniqlandi",
                        category="operations",
                        severity=SeverityLevel.WARNING.value,
                        summary=f"Ish oqimlari muvaffaqiyat ko'rsatkichi {kpi.current_value}% ni tashkil etmoqda.",
                        explanation=(
                            "Sabab: Tashqi integratsiya yoki qadamlar bajarilishida vaqtinchalik tarmoq "
                            "yoki ruxsat etilmagan ma'lumotlar bilan bog'liq xatolar yuz bergan."
                        ),
                        recommended_actions=[
                            "Ish oqimlari bajarilish jurnallari (Workflow Logs)ni tekshirish",
                            "Xatolik bergan integratsiya ulanishlarini sinovdan o'tkazish",
                        ],
                        related_entity_type="Workflow",
                    )
                )

            # 4. AI Adoption & High Usage
            elif kpi.code == "AI_USAGE_MESSAGES" and kpi.current_value > 50:
                insights.append(
                    InsightData(
                        title="Jamoaning AI yordamchisidan foydalanish faolligi yuqori",
                        category="ai",
                        severity=SeverityLevel.INFO.value,
                        summary=f"Xodimlar AI agentlari bilan {int(kpi.current_value)} marta muloqot qilgan.",
                        explanation=(
                            "Sabab: Hujjatlarni tahlil qilish va ma'lumot qidirish jarayonlarida "
                            "AI agentlarga talab ortib bormoqda, bu esa umumiy ish unumdorligini oshirmoqda."
                        ),
                        recommended_actions=[
                            "Eng ko'p foydalanilayotgan AI qobiliyatlarini o'rganish",
                            "Ko'p takrorlanadigan savollar uchun tayyor shablonlar (Prompts) yaratish",
                        ],
                        related_entity_type="Chat",
                    )
                )

        # If no critical or warning insights were triggered, output positive operational summary
        if len(insights) == 0:
            insights.append(
                InsightData(
                    title="Operatsion jarayonlar barqaror va maqsadli darajada",
                    category="operations",
                    severity=SeverityLevel.INFO.value,
                    summary="Barcha asosiy operatsion va hujjat ko'rsatkichlari me'yoriy chegarada ishlamoqda.",
                    explanation="Kompaniyaning joriy vazifalari va jarayonlari belgilangan muddatlar va mezonlarga mos bajarilmoqda.",
                    recommended_actions=[
                        "Mavjud barqarorlikni saqlab qolish",
                        "Keyingi oylik rejalarni shakllantirish",
                    ],
                )
            )

        return insights


insight_engine = InsightEngine()
