"""Lightweight in-process scheduler facade for workflow schedules.

Celery beat / external cron can call ``due_schedules`` consumers.
This module stores schedule intent and computes next-run hints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class WorkflowScheduler:
    """Schedule helper — does not replace Celery Beat, complements it."""

    def compute_next_run(
        self,
        *,
        cron_expression: str | None = None,
        interval_seconds: int | None = None,
        from_time: datetime | None = None,
    ) -> datetime | None:
        now = from_time or datetime.now(timezone.utc)
        if interval_seconds and interval_seconds > 0:
            return now + timedelta(seconds=interval_seconds)
        if cron_expression:
            # Minimal cron support: treat as daily interval placeholder when complex parsing unavailable
            return now + timedelta(hours=24)
        return None

    def is_due(self, next_run_at: datetime | None, now: datetime | None = None) -> bool:
        if not next_run_at:
            return False
        current = now or datetime.now(timezone.utc)
        if next_run_at.tzinfo is None:
            next_run_at = next_run_at.replace(tzinfo=timezone.utc)
        return next_run_at <= current

    def describe(self, schedule: dict[str, Any]) -> str:
        if schedule.get("cron_expression"):
            return f"cron:{schedule['cron_expression']}"
        if schedule.get("interval_seconds"):
            return f"interval:{schedule['interval_seconds']}s"
        return "unscheduled"
