#!/bin/bash
# =============================================================================
# Nexora AI — Production Backup Script
# Usage: ./scripts/backup.sh [daily|weekly|manual]
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_TYPE="${1:-manual}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Database
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-nexora_db}"
DB_USER="${DB_USER:-nexora}"

# MinIO
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-nexora_access}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-nexora_secret}"
MINIO_BUCKET="${MINIO_BUCKET:-nexora-storage}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"; exit 1; }

# Create backup directory
mkdir -p "${BACKUP_DIR}/postgres"
mkdir -p "${BACKUP_DIR}/minio"
mkdir -p "${BACKUP_DIR}/config"

# =============================================================================
# 1. PostgreSQL Backup
# =============================================================================
log "Starting PostgreSQL backup..."

PG_BACKUP_FILE="${BACKUP_DIR}/postgres/nexora_${DATE}.sql.gz"

if command -v pg_dump &> /dev/null; then
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --format=custom \
        --compress=6 \
        --verbose \
        -f "${BACKUP_DIR}/postgres/nexora_${DATE}.dump" 2>/dev/null

    # Also create plain SQL backup
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --format=plain \
        | gzip > "$PG_BACKUP_FILE"

    log "PostgreSQL backup completed: ${PG_BACKUP_FILE}"
    log "PostgreSQL custom dump: ${BACKUP_DIR}/postgres/nexora_${DATE}.dump"
else
    # Try Docker-based backup
    if docker ps | grep -q nexora-postgres; then
        docker exec nexora-postgres pg_dump -U "$DB_USER" -d "$DB_NAME" \
            --format=custom --compress=6 \
            > "${BACKUP_DIR}/postgres/nexora_${DATE}.dump"
        log "PostgreSQL backup completed via Docker"
    else
        warn "PostgreSQL backup skipped — pg_dump not available and container not running"
    fi
fi

# =============================================================================
# 2. MinIO Backup (bucket metadata)
# =============================================================================
log "Starting MinIO backup..."

if command -v mc &> /dev/null; then
    mc alias set nexora-backup "http://${MINIO_ENDPOINT}" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>/dev/null
    mc mirror "nexora-backup/${MINIO_BUCKET}" "${BACKUP_DIR}/minio/${DATE}/" 2>/dev/null
    log "MinIO backup completed: ${BACKUP_DIR}/minio/${DATE}/"
else
    warn "MinIO backup skipped — mc client not installed"
fi

# =============================================================================
# 3. Configuration Backup
# =============================================================================
log "Backing up configuration..."

CONFIG_FILE="${BACKUP_DIR}/config/config_${DATE}.tar.gz"
tar -czf "$CONFIG_FILE" \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.pyc' \
    docker-compose.yml \
    docker/ \
    .env.example \
    backend/pyproject.toml \
    2>/dev/null || true

log "Configuration backup completed: ${CONFIG_FILE}"

# =============================================================================
# 4. Cleanup Old Backups
# =============================================================================
log "Cleaning up backups older than ${RETENTION_DAYS} days..."

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.dump" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

log "Cleanup completed"

# =============================================================================
# 5. Summary
# =============================================================================
echo ""
log "============================================"
log "Backup Summary"
log "============================================"
log "Type: ${BACKUP_TYPE}"
log "Date: ${DATE}"
log "Directory: ${BACKUP_DIR}"
log ""

# List backup files
ls -lh "${BACKUP_DIR}/postgres/"*${DATE}* 2>/dev/null || true
ls -lh "${BACKUP_DIR}/config/"*${DATE}* 2>/dev/null || true

echo ""
log "Backup completed successfully!"
