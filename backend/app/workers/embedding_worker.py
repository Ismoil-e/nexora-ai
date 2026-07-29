import json
from app.core.logging import get_logger

logger = get_logger(__name__)


async def process_document(document_id: str):
    logger.info("processing_document", document_id=document_id)
    try:
        from app.core.database import async_session_factory
        from app.models.document import Document, DocumentChunk
        from app.repositories.document_repo import DocumentRepository, DocumentChunkRepository
        from app.storage.file_handler import FileHandler
        from app.storage.minio_client import MinioClient
        from app.ai.embeddings import EmbeddingService
        from app.core.config import settings

        async with async_session_factory() as db:
            doc_repo = DocumentRepository(db)
            chunk_repo = DocumentChunkRepository(db)
            file_handler = FileHandler()
            minio_client = MinioClient()
            embedding_service = EmbeddingService()

            doc = await doc_repo.get_by_id(document_id)
            if not doc:
                logger.error("document_not_found", document_id=document_id)
                return

            file_data = await minio_client.get_file(doc.stored_path)
            if not file_data:
                await doc_repo.update(doc.id, status="error", error_message="Fayl topilmadi")
                return

            text = await file_handler.extract_text(file_data, doc.original_filename)

            if not text.strip():
                await doc_repo.update(doc.id, status="error", error_message="Matn ajratib olinmadi")
                return

            chunks = await file_handler.chunk_text(text)

            for idx, chunk_text in enumerate(chunks):
                try:
                    embedding = await embedding_service.create_embedding(chunk_text)
                except Exception as e:
                    logger.warning("embedding_failed", chunk_index=idx, error=str(e))
                    embedding = []

                await chunk_repo.create(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk_text,
                    embedding=embedding,
                    token_count=len(chunk_text.split()),
                    metadata=json.dumps({"source": doc.original_filename, "chunk": idx}),
                )

            page_count = None
            if doc.file_extension == "pdf":
                import pdfplumber
                import io
                with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                    page_count = len(pdf.pages)

            await doc_repo.update(
                doc.id,
                status="completed",
                page_count=page_count,
                ocr_text=text[:1000],
            )

            logger.info("document_processed", document_id=document_id, chunks=len(chunks))

    except Exception as e:
        logger.error("document_processing_failed", document_id=document_id, error=str(e))
        from app.core.database import async_session_factory
        from app.repositories.document_repo import DocumentRepository
        async with async_session_factory() as db:
            doc_repo = DocumentRepository(db)
            await doc_repo.update(document_id, status="error", error_message=str(e))
