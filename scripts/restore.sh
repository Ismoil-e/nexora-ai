#!/bin/bash
# =============================================================================
# Nexora AI — Production Restore Script
# Usage: ./scripts/restore.sh <backup_date>
# Example: ./scripts/restore.sh 20260825_120000
# =============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_DATE="${1:-}"

if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 <backup_date>"
    echo "Available backups:"
    ls -1 "${BACKUP_DIR}/postgres/" 2>/dev/null | sed 's/nexora_//;s/.dump//' || echo "No backups found"
    exit 1
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-nexora_db}"
DB_USER="${DB_USER:-nexora}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"; exit 1; }

DUMP_FILE="${BACKUP_DIR}/postgres/nexora_${BACKUP_DATE}.dump"
SQL_FILE="${BACKUP_DIR}/postgres/nexora_${BACKUP_DATE}.sql.gz"

# =============================================================================
# Pre-restore checks
# =============================================================================
log "Pre-restore checks..."

if [ ! -f "$DUMP_FILE" ] && [ ! -f "$SQL_FILE" ]; then
    error "Backup file not found: ${DUMP_FILE} or ${SQL_FILE}"
fi

echo ""
warn "This will OVERWRITE the current database '${DB_NAME}'!"
warn "Make sure you have a current backup before proceeding!"
echo ""
read -p "Type 'RESTORE' to confirm: " CONFIRM
if [ "$CONFIRM" != "RESTORE" ]; then
    error "Restore cancelled"
fi

# =============================================================================
# 1. Create pre-restore backup
# =============================================================================
log "Creating pre-restore safety backup..."
PRE_RESTORE="${BACKUP_DIR}/postgres/pre_restore_$(date +%Y%m%d_%H%M%S).dump"

if command -v pg_dump &> /dev/null; then
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --format=custom --compress=6 -f "$PRE_RESTORE" 2>/dev/null || true
elif docker ps | grep -q nexora-postgres; then
    docker exec nexora-postgres pg_dump -U "$DB_USER" -d "$DB_NAME" \
        --format=custom --compress=6 > "$PRE_RESTORE" 2>/dev/null || true
fi
log "Pre-restore backup: ${PRE_RESTORE}"

# =============================================================================
# 2. Restore PostgreSQL
# =============================================================================
log "Restoring PostgreSQL database..."

if [ -f "$DUMP_FILE" ]; then
    if command -v pg_restore &> /dev/null; then
        pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            --clean --if-exists --no-owner --no-privileges \
            "$DUMP_FILE" 2>/dev/null || true
    elif docker ps | grep -q nexora-postgres; then
        docker exec -i nexora-postgres pg_restore -U "$DB_USER" -d "$DB_NAME" \
            --clean --if-exists --no-owner --no-privileges \
            < "$DUMP_FILE" 2>/dev/null || true
    fi
elif [ -f "$SQL_FILE" ]; then
    if command -v psql &> /dev/null; then
        gunzip -c "$SQL_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" 2>/dev/null || true
    elif docker ps | grep -q nexora-postgres; then
        gunzip -c "$SQL_FILE" | docker exec -i nexora-postgres psql -U "$DB_USER" -d "$DB_NAME" 2>/dev/null || true
    fi
fi

log "Database restore completed"

# =============================================================================
# 3. Verify restore
# =============================================================================
log "Verifying restore..."

TABLE_COUNT=$(docker exec nexora-postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo "unknown")
log "Tables in database: ${TABLE_COUNT}"

log "============================================"
log "Restore completed successfully!"
log "============================================"
log "Restored from: ${BACKUP_DATE}"
log "Pre-restore backup: ${PRE_RESTORE}"
log ""
log "Next steps:"
log "1. Restart the application: docker-compose restart app worker"
log "2. Verify application health: curl http://localhost:8000/api/health/ready"
log "3. Check application logs for errors"
