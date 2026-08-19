import time
import uuid
from datetime import datetime, timezone

from app.integrations.contracts.types import ConnectorHealth


class IntegrationHealthMonitor:
    """Tracks latency, request counters, error rates, and health status."""

    def __init__(self):
        self._metrics: dict[str, dict] = {}

    def record_execution(self, integration_id: uuid.UUID, success: bool, latency_ms: int):
        key = str(integration_id)
        if key not in self._metrics:
            self._metrics[key] = {
                "total_requests": 0,
                "failed_requests": 0,
                "latencies": [],
                "last_success_at": None,
                "last_failure_at": None,
            }

        m = self._metrics[key]
        m["total_requests"] += 1
        m["latencies"].append(latency_ms)
        if len(m["latencies"]) > 100:
            m["latencies"] = m["latencies"][-50:]

        now = datetime.now(timezone.utc)
        if success:
            m["last_success_at"] = now
        else:
            m["failed_requests"] += 1
            m["last_failure_at"] = now

    def get_health_summary(self, integration_id: uuid.UUID) -> ConnectorHealth:
        key = str(integration_id)
        m = self._metrics.get(key)
        if not m or m["total_requests"] == 0:
            return ConnectorHealth(status="unknown", latency_ms=0)

        total = m["total_requests"]
        failed = m["failed_requests"]
        error_rate = failed / total
        avg_latency = sum(m["latencies"]) // len(m["latencies"]) if m["latencies"] else 0

        status = "healthy"
        if error_rate > 0.5:
            status = "unhealthy"
        elif error_rate > 0.1 or avg_latency > 5000:
            status = "degraded"

        return ConnectorHealth(
            status=status,
            latency_ms=avg_latency,
            error_message=f"Error rate: {error_rate:.1%}" if error_rate > 0 else None,
        )


health_monitor = IntegrationHealthMonitor()
