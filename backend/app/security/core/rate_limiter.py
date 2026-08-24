import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class InMemoryRateLimiter:
    """In-memory sliding window rate limiter (fallback when Redis unavailable)."""

    def __init__(self):
        self._requests: dict[str, list[float]] = {}

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        """Returns (is_limited, retry_after_seconds)."""
        now = time.time()
        window_start = now - window_seconds

        if key not in self._requests:
            self._requests[key] = []

        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if t > window_start]

        if len(self._requests[key]) >= max_requests:
            oldest = self._requests[key][0]
            retry_after = int(oldest + window_seconds - now) + 1
            return True, max(retry_after, 1)

        self._requests[key].append(now)
        return False, 0


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


# Rate limit configurations for sensitive endpoints
RATE_LIMIT_CONFIGS = {
    "/api/v1/auth/login": {"max_requests": 5, "window_seconds": 60},
    "/api/v1/auth/register": {"max_requests": 3, "window_seconds": 60},
    "/api/v1/auth/refresh": {"max_requests": 10, "window_seconds": 60},
    "/api/v1/security/mfa/verify": {"max_requests": 5, "window_seconds": 60},
    "/api/v1/security/password/change": {"max_requests": 3, "window_seconds": 300},
    "/api/v1/security/break-glass/activate": {"max_requests": 2, "window_seconds": 600},
}

# Default rate limit for all other endpoints
DEFAULT_RATE_LIMIT = {"max_requests": 60, "window_seconds": 60}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces per-IP rate limiting on sensitive endpoints."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks and docs
        path = request.url.path
        if path in ("/api/health", "/docs", "/redoc", "/api/openapi.json"):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        # Determine rate limit config
        config = RATE_LIMIT_CONFIGS.get(path, DEFAULT_RATE_LIMIT)
        max_requests = config["max_requests"]
        window = config["window_seconds"]

        # Create rate limit key: IP + path prefix
        path_prefix = "/".join(path.split("/")[:4])  # e.g., /api/v1/auth
        rate_key = f"{client_ip}:{path_prefix}"

        is_limited, retry_after = rate_limiter.is_rate_limited(rate_key, max_requests, window)

        if is_limited:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=path,
                max_requests=max_requests,
                window_seconds=window,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Juda ko'p so'rov. Iltimos, biroz kutib qayta urinib ko'ring.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        remaining = max_requests - len(rate_limiter._requests.get(rate_key, []))
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response
