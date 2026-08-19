"""Backward-compatible alias worker module for the Document Intelligence Engine."""

from app.workers.document_worker import enqueue_document_processing, process_document_job, run_document_pipeline


async def process_document(document_id: str):
    """Alias kept for backward compatibility. Prefer enqueue_document_processing()."""
    return await run_document_pipeline(document_id)


__all__ = [
    "process_document",
    "run_document_pipeline",
    "process_document_job",
    "enqueue_document_processing",
]
