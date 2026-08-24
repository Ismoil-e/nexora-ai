# =============================================================================
# Nexora AI — Production Dockerfile
# Multi-stage build for optimized production image
# =============================================================================

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY backend/pyproject.toml backend/ /app/

# Install Python dependencies
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Production image
FROM python:3.11-slim AS production

# Security: Create non-root user
RUN groupadd -r nexora && useradd -r -g nexora -d /app -s /sbin/nologin nexora

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY backend/ /app/backend/

# Create required directories
RUN mkdir -p /app/data /app/logs /app/storage \
    && chown -R nexora:nexora /app

# Switch to non-root user
USER nexora

# Environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/live || exit 1

EXPOSE 8000

# Run with uvicorn for production
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
