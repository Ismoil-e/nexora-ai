# =============================================================================
# Nexora AI — Production Dockerfile
# Multi-stage build for optimized production image
# =============================================================================

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --prefix=/install \
    "fastapi>=0.100.0" \
    "uvicorn[standard]>=0.20.0" \
    uvloop \
    httptools \
    "sqlalchemy>=2.0.0" \
    "alembic>=1.10.0" \
    "asyncpg>=0.28.0" \
    "psycopg2-binary>=2.9.0" \
    "pydantic[email]>=2.0.0" \
    "pydantic-settings>=2.0.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "python-multipart>=0.0.5" \
    "redis>=4.5.0" \
    "minio>=7.0.0" \
    "structlog>=23.0.0" \
    "httpx>=0.24.0" \
    "pdfplumber>=0.7.0" \
    "python-docx>=0.8.11" \
    "openpyxl>=3.0.0" \
    "pillow>=10.0.0" \
    "tenacity>=8.0.0" \
    "prometheus-client>=0.17.0" \
    "celery>=5.3.0" \
    "kombu>=5.3.0" \
    "openai>=1.0.0"

# Stage 2: Production image
FROM python:3.11-slim AS production

RUN groupadd -r nexora && useradd -r -g nexora -d /app -s /sbin/nologin nexora

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY backend/ /app/backend/

RUN mkdir -p /app/data /app/logs /app/storage \
    && chown -R nexora:nexora /app

USER nexora

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/live || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
