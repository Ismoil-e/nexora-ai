from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task
def send_notification(user_id: str, title: str, body: str, notification_type: str):
    logger.info("sending_notification", user_id=user_id, type=notification_type)
    pass
