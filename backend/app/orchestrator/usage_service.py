"""AI Usage Service — tracks usage, cost, limits, and analytics for AI operations.

Tracks per-user, per-tenant, per-agent, per-workflow AI usage with:
- Token counts
- Estimated cost
- Provider/model usage
- Daily/monthly limits
- Configurable policies
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import AIUsageAuditLog


class AIUsageLimits:
    """Configurable usage limits."""

    def __init__(self, config: dict[str, Any] | None = None):
        cfg = config or {}
        self.daily_token_limit_per_user: int = cfg.get("daily_token_limit_per_user", 1_000_000)
        self.monthly_token_limit_per_user: int = cfg.get("monthly_token_limit_per_user", 30_000_000)
        self.daily_cost_limit_per_user: float = cfg.get("daily_cost_limit_per_user", 10.0)
        self.monthly_cost_limit_per_user: float = cfg.get("monthly_cost_limit_per_user", 200.0)
        self.daily_token_limit_per_tenant: int = cfg.get("daily_token_limit_per_tenant", 10_000_000)
        self.monthly_token_limit_per_tenant: int = cfg.get("monthly_token_limit_per_tenant", 300_000_000)
        self.daily_cost_limit_per_tenant: float = cfg.get("daily_cost_limit_per_tenant", 50.0)
        self.monthly_cost_limit_per_tenant: float = cfg.get("monthly_cost_limit_per_tenant", 1000.0)


class AIUsageService:
    """Tracks AI usage, enforces limits, and provides analytics."""

    def __init__(self, db: AsyncSession, limits: AIUsageLimits | None = None):
        self.db = db
        self.limits = limits or AIUsageLimits()

    async def record_usage(
        self,
        *,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        model: str,
        task_type: str = "chat",
        tokens_input: int = 0,
        tokens_output: int = 0,
        tokens_total: int = 0,
        estimated_cost: float = 0.0,
        duration_ms: int = 0,
        agent_key: str | None = None,
        workflow_id: uuid.UUID | None = None,
        request_id: str | None = None,
        success: bool = True,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a single AI usage event."""
        log = AIUsageAuditLog(
            company_id=company_id,
            user_id=user_id,
            provider=provider,
            model=model,
            task_type=task_type,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_total or (tokens_input + tokens_output),
            estimated_cost=estimated_cost,
            duration_ms=duration_ms,
            agent_key=agent_key,
            workflow_id=str(workflow_id) if workflow_id else None,
            request_id=request_id,
            success=success,
            error_message=error,
            metadata_json=str(metadata) if metadata else None,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        await self.db.flush()

    async def check_limits(
        self,
        *,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        estimated_tokens: int = 0,
        estimated_cost: float = 0.0,
    ) -> dict[str, Any]:
        """Check if the user/tenant has exceeded usage limits.

        Returns dict with:
        - allowed: bool
        - user_daily_tokens: int
        - user_monthly_tokens: int
        - tenant_daily_tokens: int
        - tenant_monthly_tokens: int
        - user_daily_cost: float
        - tenant_daily_cost: float
        - reason: str (if not allowed)
        """
        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = day_start.replace(day=1)

        # User daily
        user_daily = await self._get_usage_sum(
            company_id, user_id, day_start, now, "tokens_total"
        )
        # User monthly
        user_monthly = await self._get_usage_sum(
            company_id, user_id, month_start, now, "tokens_total"
        )
        # Tenant daily
        tenant_daily = await self._get_usage_sum(
            company_id, None, day_start, now, "tokens_total"
        )
        # Tenant monthly
        tenant_monthly = await self._get_usage_sum(
            company_id, None, month_start, now, "tokens_total"
        )

        # Cost
        user_daily_cost = await self._get_usage_sum(
            company_id, user_id, day_start, now, "estimated_cost"
        )
        tenant_daily_cost = await self._get_usage_sum(
            company_id, None, day_start, now, "estimated_cost"
        )

        result: dict[str, Any] = {
            "allowed": True,
            "user_daily_tokens": user_daily,
            "user_monthly_tokens": user_monthly,
            "tenant_daily_tokens": tenant_daily,
            "tenant_monthly_tokens": tenant_monthly,
            "user_daily_cost": round(user_daily_cost, 4),
            "tenant_daily_cost": round(tenant_daily_cost, 4),
            "daily_token_limit_user": self.limits.daily_token_limit_per_user,
            "monthly_token_limit_user": self.limits.monthly_token_limit_per_user,
            "daily_token_limit_tenant": self.limits.daily_token_limit_per_tenant,
            "monthly_token_limit_tenant": self.limits.monthly_token_limit_per_tenant,
        }

        # Check limits
        if user_daily + estimated_tokens > self.limits.daily_token_limit_per_user:
            result["allowed"] = False
            result["reason"] = "Daily user token limit exceeded"
        elif user_monthly + estimated_tokens > self.limits.monthly_token_limit_per_user:
            result["allowed"] = False
            result["reason"] = "Monthly user token limit exceeded"
        elif tenant_daily + estimated_tokens > self.limits.daily_token_limit_per_tenant:
            result["allowed"] = False
            result["reason"] = "Daily tenant token limit exceeded"
        elif tenant_monthly + estimated_tokens > self.limits.monthly_token_limit_per_tenant:
            result["allowed"] = False
            result["reason"] = "Monthly tenant token limit exceeded"
        elif user_daily_cost + estimated_cost > self.limits.daily_cost_limit_per_user:
            result["allowed"] = False
            result["reason"] = "Daily user cost limit exceeded"
        elif tenant_daily_cost + estimated_cost > self.limits.daily_cost_limit_per_tenant:
            result["allowed"] = False
            result["reason"] = "Daily tenant cost limit exceeded"

        return result

    async def get_usage_summary(
        self,
        company_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get usage summary for a tenant/user over a time period."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        total_tokens = await self._get_usage_sum(company_id, user_id, start, now, "tokens_total")
        total_cost = await self._get_usage_sum(company_id, user_id, start, now, "estimated_cost")
        request_count = await self._get_request_count(company_id, user_id, start, now)
        success_count = await self._get_request_count(
            company_id, user_id, start, now, success_only=True
        )

        # Breakdown by provider
        provider_breakdown = await self._get_breakdown(
            company_id, user_id, start, now, "provider"
        )
        model_breakdown = await self._get_breakdown(
            company_id, user_id, start, now, "model"
        )
        task_type_breakdown = await self._get_breakdown(
            company_id, user_id, start, now, "task_type"
        )

        # Daily trend
        daily_trend = await self._get_daily_trend(company_id, user_id, start, now)

        return {
            "period_days": days,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "request_count": request_count,
            "success_count": success_count,
            "success_rate": round(success_count / max(request_count, 1) * 100, 1),
            "avg_tokens_per_request": round(total_tokens / max(request_count, 1)),
            "avg_cost_per_request": round(total_cost / max(request_count, 1), 6),
            "by_provider": provider_breakdown,
            "by_model": model_breakdown,
            "by_task_type": task_type_breakdown,
            "daily_trend": daily_trend,
        }

    async def _get_usage_sum(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None,
        start: datetime,
        end: datetime,
        field_name: str,
    ) -> Any:
        """Sum a numeric field over a time range."""
        col = getattr(AIUsageAuditLog, field_name, None)
        if col is None:
            return 0

        stmt = select(func.coalesce(func.sum(col), 0)).where(
            and_(
                AIUsageAuditLog.company_id == company_id,
                AIUsageAuditLog.created_at >= start,
                AIUsageAuditLog.created_at <= end,
            )
        )
        if user_id:
            stmt = stmt.where(AIUsageAuditLog.user_id == user_id)

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _get_request_count(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None,
        start: datetime,
        end: datetime,
        success_only: bool = False,
    ) -> int:
        stmt = select(func.count()).where(
            and_(
                AIUsageAuditLog.company_id == company_id,
                AIUsageAuditLog.created_at >= start,
                AIUsageAuditLog.created_at <= end,
            )
        )
        if user_id:
            stmt = stmt.where(AIUsageAuditLog.user_id == user_id)
        if success_only:
            stmt = stmt.where(AIUsageAuditLog.success.is_(True))

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _get_breakdown(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None,
        start: datetime,
        end: datetime,
        group_by: str,
    ) -> list[dict[str, Any]]:
        """Group usage by a field and sum tokens."""
        col = getattr(AIUsageAuditLog, group_by, None)
        if col is None:
            return []

        stmt = (
            select(
                col.label("key"),
                func.sum(AIUsageAuditLog.tokens_total).label("tokens"),
                func.sum(AIUsageAuditLog.estimated_cost).label("cost"),
                func.count().label("count"),
            )
            .where(
                and_(
                    AIUsageAuditLog.company_id == company_id,
                    AIUsageAuditLog.created_at >= start,
                    AIUsageAuditLog.created_at <= end,
                )
            )
            .group_by(col)
        )
        if user_id:
            stmt = stmt.where(AIUsageAuditLog.user_id == user_id)

        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "key": row.key or "unknown",
                "tokens": int(row.tokens or 0),
                "cost": round(float(row.cost or 0), 4),
                "count": int(row.count or 0),
            }
            for row in rows
        ]

    async def _get_daily_trend(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Get daily usage trend."""
        from sqlalchemy import cast, Date

        stmt = (
            select(
                cast(AIUsageAuditLog.created_at, Date).label("date"),
                func.sum(AIUsageAuditLog.tokens_total).label("tokens"),
                func.sum(AIUsageAuditLog.estimated_cost).label("cost"),
                func.count().label("count"),
            )
            .where(
                and_(
                    AIUsageAuditLog.company_id == company_id,
                    AIUsageAuditLog.created_at >= start,
                    AIUsageAuditLog.created_at <= end,
                )
            )
            .group_by(cast(AIUsageAuditLog.created_at, Date))
            .order_by(cast(AIUsageAuditLog.created_at, Date))
        )
        if user_id:
            stmt = stmt.where(AIUsageAuditLog.user_id == user_id)

        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "date": str(row.date),
                "tokens": int(row.tokens or 0),
                "cost": round(float(row.cost or 0), 4),
                "count": int(row.count or 0),
            }
            for row in rows
        ]


def estimate_cost(provider: str, model: str, tokens_input: int, tokens_output: int) -> float:
    """Estimate cost based on provider/model pricing."""
    from app.orchestrator.model_router import model_router

    info = model_router.get_model_info(provider, model)
    if not info:
        return 0.0

    input_cost = (tokens_input / 1000) * info.cost_per_1k_input
    output_cost = (tokens_output / 1000) * info.cost_per_1k_output
    return round(input_cost + output_cost, 6)
