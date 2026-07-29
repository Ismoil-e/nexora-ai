from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_ocr(self, file_path: str, document_id: str):
    logger.info("processing_ocr", document_id=document_id, file_path=file_path)
    try:
        pass
    except Exception as e:
        logger.error("ocr_failed", document_id=document_id, error=str(e))
        raise self.retry(exc=e, countdown=60)
