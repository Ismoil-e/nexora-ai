from celery import Celery
from kombu import Exchange, Queue
from app.core.config import settings

# ---------------------------------------------------------------------------
# Queue definitions
# ---------------------------------------------------------------------------

default_exchange = Exchange("default", type="direct")
ai_exchange = Exchange("ai", type="direct")
ocr_exchange = Exchange("ocr", type="direct")
document_exchange = Exchange("document", type="direct")
report_exchange = Exchange("report", type="direct")

QUEUES = {
    "default": Queue("default", default_exchange, routing_key="default"),
    "ai": Queue("ai", ai_exchange, routing_key="ai", queue_arguments={"x-max-priority": 10}),
    "ocr": Queue("ocr", ocr_exchange, routing_key="ocr"),
    "document": Queue("document", document_exchange, routing_key="document"),
    "report": Queue("report", report_exchange, routing_key="report"),
}

# Task routing — which tasks go to which queue
TASK_ROUTES = {
    # AI-heavy tasks → ai queue (higher concurrency possible)
    "app.workers.agent_worker.*": {"queue": "ai"},
    "app.workers.embedding_worker.*": {"queue": "ai"},
    # OCR tasks → ocr queue (CPU-intensive)
    "app.workers.ocr_worker.*": {"queue": "ocr"},
    # Document processing → document queue
    "app.workers.document_worker.*": {"queue": "document"},
    "app.workers.integration_worker.*": {"queue": "document"},
    # Report/BI tasks → report queue
    "app.workers.bi_worker.*": {"queue": "report"},
    # Workflow tasks stay in default queue
    "app.workers.workflow_worker.*": {"queue": "default"},
    "app.workers.notification_worker.*": {"queue": "default"},
}

# ---------------------------------------------------------------------------
# Celery app
# ---------------------------------------------------------------------------

celery_app = Celery(
    "nexora",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=[
        "app.workers.ocr_worker",
        "app.workers.embedding_worker",
        "app.workers.document_worker",
        "app.workers.notification_worker",
        "app.workers.agent_worker",
        "app.workers.workflow_worker",
        "app.workers.integration_worker",
        "app.workers.bi_worker",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="Asia/Tashkent",
    enable_utc=True,
    # Task behavior
    task_track_started=True,
    task_time_limit=3600,          # Hard limit: 1 hour per task
    task_soft_time_limit=3000,     # Soft limit: 50 minutes (raises SoftTimeLimitExceeded)
    task_acks_late=True,           # Ack after execution (prevents task loss on worker crash)
    task_reject_on_worker_lost=True,
    # Retry policy (default for all tasks)
    task_default_retry_delay=60,   # 1 minute between retries
    task_max_retries=3,
    # Worker behavior
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,  # Fair scheduling for long-running tasks
    worker_cancel_long_running_tasks_on_connection_loss=True,
    # Queues and routing
    task_queues=QUEUES,
    task_routes=TASK_ROUTES,
    task_default_queue="default",
    # Result backend
    result_expires=3600,           # Results expire after 1 hour
    # Rate limiting
    worker_disable_rate_limits=False,
    # Connection retry
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=5,
)
