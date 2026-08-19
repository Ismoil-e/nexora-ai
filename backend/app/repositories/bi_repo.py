import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.repositories.base import BaseRepository


class KPIRepository(BaseRepository[KPI]):
    def __init__(self, db: AsyncSession):
        super().__init__(KPI, db)

    async def get_by_company(self, company_id: uuid.UUID) -> List[KPI]:
        res = await self.db.scalars(
            select(KPI).where(KPI.company_id == company_id, KPI.deleted_at.is_(None)).order_by(KPI.name)
        )
        return list(res.all())

    async def get_by_code(self, company_id: uuid.UUID, code: str) -> Optional[KPI]:
        return await self.db.scalar(
            select(KPI).where(
                KPI.company_id == company_id,
                KPI.code == code,
                KPI.deleted_at.is_(None),
            )
        )

    async def log_value(
        self,
        kpi_id: uuid.UUID,
        company_id: uuid.UUID,
        value: float,
        target_value: Optional[float],
        status: str,
        meta_data: Optional[str] = None,
    ) -> KPILog:
        log = KPILog(
            kpi_id=kpi_id,
            company_id=company_id,
            recorded_value=value,
            target_value=target_value,
            status=status,
            meta_data=meta_data,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_history(self, kpi_id: uuid.UUID, company_id: uuid.UUID, limit: int = 30) -> List[KPILog]:
        res = await self.db.scalars(
            select(KPILog)
            .where(KPILog.kpi_id == kpi_id, KPILog.company_id == company_id)
            .order_by(desc(KPILog.created_at))
            .limit(limit)
        )
        return list(res.all())


class DashboardRepository(BaseRepository[Dashboard]):
    def __init__(self, db: AsyncSession):
        super().__init__(Dashboard, db)

    async def get_by_company(self, company_id: uuid.UUID) -> List[Dashboard]:
        res = await self.db.scalars(
            select(Dashboard)
            .where(Dashboard.company_id == company_id, Dashboard.deleted_at.is_(None))
            .order_by(desc(Dashboard.is_default), Dashboard.name)
        )
        return list(res.all())

    async def get_by_slug(self, company_id: uuid.UUID, slug: str) -> Optional[Dashboard]:
        return await self.db.scalar(
            select(Dashboard).where(
                Dashboard.company_id == company_id,
                Dashboard.slug == slug,
                Dashboard.deleted_at.is_(None),
            )
        )

    async def add_widget(
        self,
        dashboard_id: uuid.UUID,
        company_id: uuid.UUID,
        title: str,
        widget_type: str,
        metric_code: Optional[str] = None,
        query_config: Optional[str] = None,
        position_x: int = 0,
        position_y: int = 0,
        width: int = 4,
        height: int = 3,
        refresh_interval_sec: int = 300,
    ) -> DashboardWidget:
        widget = DashboardWidget(
            dashboard_id=dashboard_id,
            company_id=company_id,
            title=title,
            widget_type=widget_type,
            metric_code=metric_code,
            query_config=query_config,
            position_x=position_x,
            position_y=position_y,
            width=width,
            height=height,
            refresh_interval_sec=refresh_interval_sec,
        )
        self.db.add(widget)
        await self.db.flush()
        return widget


class InsightRepository(BaseRepository[BIInsight]):
    def __init__(self, db: AsyncSession):
        super().__init__(BIInsight, db)

    async def get_by_company(self, company_id: uuid.UUID, limit: int = 20) -> List[BIInsight]:
        res = await self.db.scalars(
            select(BIInsight)
            .where(BIInsight.company_id == company_id, BIInsight.deleted_at.is_(None))
            .order_by(desc(BIInsight.created_at))
            .limit(limit)
        )
        return list(res.all())

    async def acknowledge(self, insight_id: uuid.UUID, user_id: uuid.UUID) -> Optional[BIInsight]:
        insight = await self.db.get(BIInsight, insight_id)
        if insight:
            insight.is_acknowledged = True
            insight.acknowledged_by = user_id
            insight.acknowledged_at = datetime.now(timezone.utc)
            await self.db.flush()
        return insight


class ForecastRepository(BaseRepository[BIForecast]):
    def __init__(self, db: AsyncSession):
        super().__init__(BIForecast, db)

    async def get_latest(self, company_id: uuid.UUID, metric_name: str) -> List[BIForecast]:
        res = await self.db.scalars(
            select(BIForecast)
            .where(
                BIForecast.company_id == company_id,
                BIForecast.metric_name == metric_name,
                BIForecast.deleted_at.is_(None),
            )
            .order_by(desc(BIForecast.created_at))
            .limit(10)
        )
        return list(res.all())


class AlertRuleRepository(BaseRepository[BIAlertRule]):
    def __init__(self, db: AsyncSession):
        super().__init__(BIAlertRule, db)

    async def get_by_company(self, company_id: uuid.UUID) -> List[BIAlertRule]:
        res = await self.db.scalars(
            select(BIAlertRule)
            .where(BIAlertRule.company_id == company_id, BIAlertRule.deleted_at.is_(None))
            .order_by(BIAlertRule.name)
        )
        return list(res.all())

    async def get_alerts(self, company_id: uuid.UUID, status: Optional[str] = None, limit: int = 50) -> List[BIAlert]:
        query = select(BIAlert).where(BIAlert.company_id == company_id, BIAlert.deleted_at.is_(None))
        if status:
            query = query.where(BIAlert.status == status)
        query = query.order_by(desc(BIAlert.triggered_at)).limit(limit)
        res = await self.db.scalars(query)
        return list(res.all())
