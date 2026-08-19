import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bi.contracts.types import KPICalculationResult
from app.models.bi import BIAlert, BIAlertRule
from app.models.notification import Notification


class AlertEngine:
    """Evaluates business alert rules and creates alert signals / notifications."""

    async def evaluate_rules(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        kpi_results: List[KPICalculationResult],
    ) -> List[BIAlert]:
        """Evaluates active alert rules for a tenant and triggers new alerts if thresholds are breached."""
        # Fetch active rules for this tenant
        rules_res = await db.scalars(
            select(BIAlertRule).where(
                BIAlertRule.company_id == company_id,
                BIAlertRule.is_active.is_(True),
                BIAlertRule.deleted_at.is_(None),
            )
        )
        rules = list(rules_res.all())

        kpi_map = {k.code: k for k in kpi_results}
        triggered_alerts: List[BIAlert] = []
        now = datetime.now(timezone.utc)

        for rule in rules:
            kpi = kpi_map.get(rule.kpi_code)
            if not kpi:
                continue

            val = kpi.current_value
            threshold = rule.threshold_value
            op = rule.condition_operator
            breached = False

            if op == "gt" and val > threshold:
                breached = True
            elif op == "lt" and val < threshold:
                breached = True
            elif op == "gte" and val >= threshold:
                breached = True
            elif op == "lte" and val <= threshold:
                breached = True
            elif op == "eq" and abs(val - threshold) < 1e-6:
                breached = True
            elif op == "neq" and abs(val - threshold) >= 1e-6:
                breached = True
            elif op == "drop_pct" and kpi.change_pct is not None and kpi.change_pct < -abs(threshold):
                breached = True
            elif op == "spike_pct" and kpi.change_pct is not None and kpi.change_pct > abs(threshold):
                breached = True

            if breached:
                msg = (
                    f"Ogohlantirish: '{rule.name}' qoidasi bo'yicha {kpi.name} ko'rsatkichi "
                    f"joriy qiymati ({val}{kpi.unit}) belgilangan chegara ({threshold}{kpi.unit}) dan o'tdi."
                )

                alert = BIAlert(
                    company_id=company_id,
                    rule_id=rule.id,
                    title=f"KPI Chegarasi Buzildi: {rule.name}",
                    message=msg,
                    severity=rule.severity,
                    status="active",
                    triggered_value=val,
                    threshold_value=threshold,
                    triggered_at=now,
                )
                db.add(alert)
                triggered_alerts.append(alert)

                rule.last_triggered_at = now

                # Also create an in-app notification if configured
                notif = Notification(
                    company_id=company_id,
                    user_id=rule.created_by,
                    title=alert.title,
                    message=alert.message,
                    type="alert",
                    is_read=False,
                )
                db.add(notif)

        if triggered_alerts:
            await db.commit()

        return triggered_alerts


alert_engine = AlertEngine()
