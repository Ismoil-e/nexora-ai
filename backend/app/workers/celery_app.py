from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "nexora",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=[
        "app.workers.ocr_worker",
        "app.workers.embedding_worker",
        "app.workers.notification_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_max_tasks_per_child=100,
)
