"""Celery worker for the Document Intelligence Engine pipeline.

The heavy document pipeline (OCR, parsing, chunking, embeddings, entity/relationship
extraction, Second Brain & Knowledge Graph updates) runs asynchronously so that
normal API requests are never blocked.
"""

import asyncio
import uuid
from typing import Any

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def run_document_pipeline(document_id: str) -> dict[str, Any]:
    """Execute the Document Intelligence pipeline for a single document."""
    from app.core.database import async_session_factory
    from app.intelligence.pipeline import DocumentIntelligencePipeline

    async with async_session_factory() as db:
        pipeline = DocumentIntelligencePipeline(db)
        result = await pipeline.process_document_id(document_id)
        logger.info(
            "document_intelligence_completed",
            document_id=document_id,
            chunks=len(result.chunks),
            entities=len(result.entities),
            relationships=len(result.relationships),
            type=result.detected_type,
        )
        return {
            "status": "completed",
            "document_id": str(result.document_id),
            "detected_type": result.detected_type,
            "chunk_count": len(result.chunks),
            "entity_count": len(result.entities),
            "relationship_count": len(result.relationships),
        }


async def mark_document_failed(document_id: str, error: str) -> None:
    from app.core.database import async_session_factory
    from app.repositories.document_repo import DocumentRepository

    try:
        async with async_session_factory() as db:
            doc_repo = DocumentRepository(db)
            doc = await doc_repo.get(uuid.UUID(str(document_id)))
            if doc:
                await doc_repo.update(doc.id, status="failed", error_message=str(error)[:4000])
    except Exception as exc:  # pragma: no cover - best-effort
        logger.error("document_failed_marker_error", document_id=document_id, error=str(exc))


@celery_app.task(
    bind=True,
    max_retries=3,
    acks_late=True,
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def process_document_job(self, document_id: str) -> dict[str, Any]:
    """Celery entrypoint wrapping the async pipeline."""
    try:
        return asyncio.run(run_document_pipeline(document_id))
    except Exception as exc:
        logger.error(
            "document_intelligence_failed",
            document_id=document_id,
            error=str(exc),
            attempts=self.request.retries + 1,
        )
        if self.request.retries >= self.max_retries:
            asyncio.run(mark_document_failed(document_id, str(exc)))
            raise
        raise self.retry(exc=exc, countdown=30)


def enqueue_document_processing(document_id: str) -> str:
    """Queue document processing on Celery; fall back to in-process background task.

    Returns one of: 'queued' (Celery), 'background' (in-process), 'deferred' (failed).
    """
    try:
        process_document_job.apply_async(args=[str(document_id)], retry=False)
        return "queued"
    except Exception as exc:
        logger.warning(
            "celery_unavailable_fallback_background",
            document_id=document_id,
            error=str(exc),
        )
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return "deferred"
        loop.create_task(run_document_pipeline(str(document_id)))
        return "background"
