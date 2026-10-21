"""Health check endpoints for production deployment.

Endpoints:
- /health — basic health check (always 200 if running)
- /health/live — liveness probe (is the process alive?)
- /health/ready — readiness probe (is the service ready to accept traffic?)
- /health/database — database connectivity check
- /health/redis — Redis connectivity check
- /health/ai — AI provider availability check
- /health/components — detailed component status
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter(tags=["Health Checks"])


def _check_database() -> dict[str, Any]:
    """Check PostgreSQL connectivity."""
    try:
        from app.core.database import async_session_factory
        import asyncio

        async def _check():
            async with async_session_factory() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1

        ok = asyncio.get_event_loop().run_until_complete(_check())
        return {"status": "healthy" if ok else "unhealthy", "latency_ms": 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:200]}


def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        import redis
        from app.core.config import settings

        start = time.perf_counter()
        client = redis.from_url(settings.redis_url, socket_timeout=5)
        client.ping()
        latency = round((time.perf_counter() - start) * 1000, 2)
        client.close()
        return {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:200]}


def _check_ai_providers() -> dict[str, Any]:
    """Check AI provider availability."""
    from app.core.config import settings

    providers = {}
    if settings.openai_api_key and not settings.openai_api_key.startswith("sk-your"):
        providers["openai"] = "configured"
    if settings.gemini_api_key and not settings.gemini_api_key.startswith("your-"):
        providers["gemini"] = "configured"
    if settings.openrouter_api_key and not settings.openrouter_api_key.startswith("sk-or-your"):
        providers["openrouter"] = "configured"

    return {
        "status": "healthy" if providers else "degraded",
        "configured_providers": list(providers.keys()),
    }


def _check_disk() -> dict[str, Any]:
    """Check disk space."""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        return {
            "status": "healthy" if free > 1024 * 1024 * 100 else "warning",  # >100MB free
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "usage_percent": round(used / total * 100, 1),
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/api/health")
async def health():
    """Basic health check — returns 200 if the process is running."""
    return {
        "status": "ok",
        "service": "nexora-ai",
        "version": settings.app_version,
        "timestamp": time.time(),
    }


@router.get("/api/health/live")
async def liveness():
    """Liveness probe — is the process alive?"""
    return {
        "status": "alive",
        "timestamp": time.time(),
        "uptime_seconds": time.time(),
    }


@router.get("/api/health/ready")
async def readiness():
    """Readiness probe — is the service ready to accept traffic?

    Checks:
    - Database connectivity
    - Redis connectivity
    - AI provider configuration
    """
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "ai_providers": _check_ai_providers(),
    }

    all_healthy = all(c["status"] in ("healthy", "degraded") for c in checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "timestamp": time.time(),
            "checks": checks,
        },
    )


@router.get("/api/health/database")
async def health_database():
    """Database connectivity check."""
    return _check_database()


@router.get("/api/health/redis")
async def health_redis():
    """Redis connectivity check."""
    return _check_redis()


@router.get("/api/health/components")
async def health_components():
    """Detailed component status for monitoring."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "components": {
            "database": _check_database(),
            "redis": _check_redis(),
            "ai_providers": _check_ai_providers(),
            "disk": _check_disk(),
        },
    }
