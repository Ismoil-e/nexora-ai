"""Application metrics for Prometheus monitoring.

Metrics exposed:
- HTTP request count, latency, errors
- AI request count, latency, tokens, cost
- Celery task count, duration
- Database query latency
- Active connections
- System resource usage
"""

from __future__ import annotations

import time
from typing import Any

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Summary,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# ---------------------------------------------------------------------------
# HTTP Metrics
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    HTTP_REQUESTS_TOTAL = Counter(
        "nexora_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )

    HTTP_REQUEST_DURATION = Histogram(
        "nexora_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    # ---------------------------------------------------------------------------
    # AI Metrics
    # ---------------------------------------------------------------------------

    AI_REQUESTS_TOTAL = Counter(
        "nexora_ai_requests_total",
        "Total AI provider requests",
        ["provider", "model", "task_type", "success"],
    )

    AI_REQUEST_DURATION = Histogram(
        "nexora_ai_request_duration_seconds",
        "AI request duration in seconds",
        ["provider", "model"],
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )

    AI_TOKENS_TOTAL = Counter(
        "nexora_ai_tokens_total",
        "Total AI tokens consumed",
        ["provider", "model", "direction"],  # direction: input/output
    )

    AI_COST_TOTAL = Counter(
        "nexora_ai_cost_dollars_total",
        "Total estimated AI cost in dollars",
        ["provider", "model"],
    )

    # ---------------------------------------------------------------------------
    # Agent Metrics
    # ---------------------------------------------------------------------------

    AGENT_EXECUTIONS_TOTAL = Counter(
        "nexora_agent_executions_total",
        "Total agent executions",
        ["agent_key", "status"],
    )

    AGENT_EXECUTION_DURATION = Histogram(
        "nexora_agent_execution_duration_seconds",
        "Agent execution duration",
        ["agent_key"],
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    )

    # ---------------------------------------------------------------------------
    # Database Metrics
    # ---------------------------------------------------------------------------

    DB_QUERY_DURATION = Histogram(
        "nexora_db_query_duration_seconds",
        "Database query duration",
        ["operation"],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    )

    DB_CONNECTIONS = Gauge(
        "nexora_db_connections",
        "Active database connections",
        ["state"],  # active/idle
    )

    # ---------------------------------------------------------------------------
    # System Metrics
    # ---------------------------------------------------------------------------

    APP_UPTIME = Gauge(
        "nexora_app_uptime_seconds",
        "Application uptime in seconds",
    )

    ACTIVE_REQUESTS = Gauge(
        "nexora_active_requests",
        "Number of currently active requests",
    )

    CELERY_TASKS_TOTAL = Counter(
        "nexora_celery_tasks_total",
        "Total Celery tasks executed",
        ["task_name", "status"],
    )

    CELERY_TASK_DURATION = Histogram(
        "nexora_celery_task_duration_seconds",
        "Celery task execution duration",
        ["task_name"],
        buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
    )

else:
    # Stubs when prometheus_client is not installed
    class _Stub:
        def __getattr__(self, name: str):
            return lambda *a, **kw: None
        def labels(self, *a, **kw):
            return self
        def observe(self, *a, **kw):
            pass
        def inc(self, *a, **kw):
            pass
        def set(self, *a, **kw):
            pass

    HTTP_REQUESTS_TOTAL = _Stub()
    HTTP_REQUEST_DURATION = _Stub()
    AI_REQUESTS_TOTAL = _Stub()
    AI_REQUEST_DURATION = _Stub()
    AI_TOKENS_TOTAL = _Stub()
    AI_COST_TOTAL = _Stub()
    AGENT_EXECUTIONS_TOTAL = _Stub()
    AGENT_EXECUTION_DURATION = _Stub()
    DB_QUERY_DURATION = _Stub()
    DB_CONNECTIONS = _Stub()
    APP_UPTIME = _Stub()
    ACTIVE_REQUESTS = _Stub()
    CELERY_TASKS_TOTAL = _Stub()
    CELERY_TASK_DURATION = _Stub()


# ---------------------------------------------------------------------------
# Middleware for HTTP metrics
# ---------------------------------------------------------------------------

_START_TIME = time.time()


def get_metrics() -> bytes:
    """Generate Prometheus metrics."""
    if PROMETHEUS_AVAILABLE:
        APP_UPTIME.set(time.time() - _START_TIME)
        return generate_latest()
    return b"# prometheus_client not installed\n"


def get_metrics_content_type() -> str:
    if PROMETHEUS_AVAILABLE:
        return CONTENT_TYPE_LATEST
    return "text/plain"
