"""Middleware that records HTTP metrics for Prometheus monitoring."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION, ACTIVE_REQUESTS


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records HTTP request metrics for Prometheus."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Skip metrics for health/metrics endpoints to avoid noise
        path = request.url.path
        if path.startswith("/api/health") or path == "/metrics":
            return await call_next(request)

        ACTIVE_REQUESTS.inc()
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=self._normalize_path(path),
                status="500",
            ).inc()
            raise
        finally:
            ACTIVE_REQUESTS.dec()

        duration = time.perf_counter() - start

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=self._normalize_path(path),
            status=str(response.status_code),
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=self._normalize_path(path),
        ).observe(duration)

        return response

    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality.

        /api/v1/agents/123 → /api/v1/agents/:id
        /api/v1/orchestrate/trace/abc → /api/v1/orchestrate/trace/:id
        """
        parts = path.strip("/").split("/")
        normalized = []
        for i, part in enumerate(parts):
            # Skip UUIDs and numeric IDs
            if len(part) > 20 and ("-" in part or part.isalnum()):
                normalized.append(":id")
            elif part.isdigit():
                normalized.append(":id")
            else:
                normalized.append(part)
        return "/" + "/".join(normalized)
