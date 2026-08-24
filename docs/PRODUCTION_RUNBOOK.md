# Nexora AI — Production Runbook

## Table of Contents
1. [Deployment](#deployment)
2. [Rollback](#rollback)
3. [Backup & Restore](#backup--restore)
4. [Health Checks](#health-checks)
5. [Monitoring](#monitoring)
6. [Secrets Management](#secrets-management)
7. [Scaling](#scaling)
8. [Incident Response](#incident-response)
9. [Troubleshooting](#troubleshooting)

---

## Deployment

### Initial Deployment
```bash
# 1. Clone repository
git clone https://github.com/Ismoil-e/nexora-ai.git
cd nexora-ai

# 2. Configure environment
cp .env.example .env
# Edit .env with production values

# 3. Start all services
docker-compose up -d

# 4. Run database migrations
docker-compose exec app alembic upgrade head

# 5. Verify health
curl http://localhost:8000/api/health/ready
```

### Update Deployment
```bash
# 1. Pull latest changes
git pull origin main

# 2. Build new images
docker-compose build --no-cache

# 3. Run database migrations
docker-compose exec app alembic upgrade head

# 4. Restart services (rolling update)
docker-compose up -d --force-recreate app worker

# 5. Verify health
curl http://localhost:8000/api/health/ready
```

---

## Rollback

### Application Rollback
```bash
# 1. Check previous git commit
git log --oneline -5

# 2. Checkout previous version
git checkout <previous-commit-hash>

# 3. Rebuild and restart
docker-compose build --no-cache
docker-compose up -d --force-recreate app worker

# 4. Verify
curl http://localhost:8000/api/health/ready
```

### Database Migration Rollback
**WARNING**: Database rollback can cause data loss. Only use if absolutely necessary.

```bash
# Check current migration
docker-compose exec app alembic current

# Rollback one step
docker-compose exec app alembic downgrade -1

# Rollback to specific revision
docker-compose exec app alembic downgrade <revision-id>
```

---

## Backup & Restore

### Manual Backup
```bash
./scripts/backup.sh manual
```

### Automated Backup (Cron)
```bash
# Add to crontab
# Daily backup at 2 AM
0 2 * * * /path/to/nexora-ai/scripts/backup.sh daily >> /var/log/nexora-backup.log 2>&1

# Weekly full backup on Sunday at 3 AM
0 3 * * 0 /path/to/nexora-ai/scripts/backup.sh weekly >> /var/log/nexora-backup.log 2>&1
```

### Restore
```bash
# List available backups
ls -la backups/postgres/

# Restore specific backup
./scripts/restore.sh 20260825_020000
```

### Backup Retention
- Daily backups: retained for 30 days
- Weekly backups: retained for 90 days
- Configured via `RETENTION_DAYS` environment variable

---

## Health Checks

### Endpoints
| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `/api/health` | Basic health | 200 OK |
| `/api/health/live` | Liveness probe | 200 OK |
| `/api/health/ready` | Readiness probe | 200 OK (all components healthy) |
| `/api/health/database` | Database check | 200 OK |
| `/api/health/redis` | Redis check | 200 OK |
| `/api/health/components` | Full status | 200 OK |
| `/metrics` | Prometheus metrics | 200 OK |

### Kubernetes Probes
```yaml
livenessProbe:
  httpGet:
    path: /api/health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 3
```

---

## Monitoring

### Prometheus Metrics
- `/metrics` endpoint exposes application metrics
- HTTP request count, latency, errors
- AI request count, latency, tokens, cost
- Celery task metrics
- Database query metrics

### Key Metrics to Watch
| Metric | Warning | Critical |
|--------|---------|----------|
| HTTP error rate | > 1% | > 5% |
| P95 latency | > 2s | > 5s |
| AI failure rate | > 5% | > 20% |
| DB connection pool | > 80% | > 95% |
| Redis memory | > 80% | > 95% |
| Disk usage | > 80% | > 90% |

### Logs
```bash
# Application logs
docker-compose logs -f app

# Worker logs
docker-compose logs -f worker

# All services
docker-compose logs -f

# PostgreSQL logs
docker-compose logs -f postgres

# Filter by level
docker-compose logs app | grep '"level":"error"'
```

---

## Secrets Management

### Environment Variables
- Use `.env` file (never commit to git)
- Use Docker secrets for production
- Use cloud secrets manager for production (AWS Secrets Manager, GCP Secret Manager)

### Key Rotation
```bash
# 1. Generate new JWT secret
openssl rand -hex 32

# 2. Update .env
SECRET_KEY=<new-secret>

# 3. Restart services
docker-compose restart app worker

# 4. All existing tokens will be invalidated
```

### Required Secrets
| Secret | Purpose | Rotation |
|--------|---------|----------|
| `SECRET_KEY` | JWT signing | Every 90 days |
| `DATABASE_URL` | Database connection | On DB password change |
| `OPENAI_API_KEY` | OpenAI API | As needed |
| `GEMINI_API_KEY` | Gemini API | As needed |
| `MINIO_SECRET_KEY` | Object storage | Every 90 days |

---

## Scaling

### Vertical Scaling
```yaml
# docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: "4.0"  # Increase CPU
          memory: 2G   # Increase memory
```

### Horizontal Scaling
```bash
# Scale API replicas
docker-compose up -d --scale app=3

# Scale workers
docker-compose up -d --scale worker=4
```

### Celery Worker Scaling
```bash
# Increase worker concurrency
docker-compose exec worker celery -A app.workers.celery_app worker \
    --concurrency=8 \
    --pool=prefork
```

---

## Incident Response

### Severity Levels
| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 | Complete outage | 15 minutes |
| P2 | Major feature broken | 1 hour |
| P3 | Minor feature broken | 4 hours |
| P4 | Non-urgent issue | 24 hours |

### Incident Steps
1. **Detect**: Monitor alerts, health checks
2. **Triage**: Determine severity and impact
3. **Mitigate**: Rollback if needed
4. **Resolve**: Fix the root cause
5. **Post-mortem**: Document and prevent recurrence

---

## Troubleshooting

### Common Issues

**Application won't start**
```bash
docker-compose logs app | tail -20
# Check database connection, missing env vars
```

**Database connection refused**
```bash
docker-compose exec postgres pg_isready -U nexora
# Check if postgres is running and healthy
```

**Redis connection refused**
```bash
docker-compose exec redis redis-cli ping
# Should return PONG
```

**Worker not processing tasks**
```bash
docker-compose logs worker | tail -20
# Check Celery broker connection
docker-compose exec worker celery -A app.workers.celery_app inspect active
```

**High memory usage**
```bash
docker stats
# Check which container is using most memory
# Consider increasing limits or scaling
```

**Slow API responses**
```bash
# Check database queries
docker-compose exec postgres psql -U nexora -d nexora_db -c \
  "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```
