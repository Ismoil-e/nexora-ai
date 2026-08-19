import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EmbeddingService
from app.intelligence.contracts.types import ExtractedChunk, StructuredDocument
from app.intelligence.core.classifier import classifier
from app.intelligence.core.duplicate_detector import duplicate_detector
from app.intelligence.core.entity_relationship_extractor import EntityRelationshipExtractor
from app.intelligence.core.intelligent_chunker import intelligent_chunker
from app.intelligence.core.language import detect_language
from app.intelligence.extractors.csv_extractor import CsvIntelligenceExtractor
from app.intelligence.extractors.docx_extractor import DocxIntelligenceExtractor
from app.intelligence.extractors.excel_extractor import ExcelIntelligenceExtractor
from app.intelligence.extractors.image_ocr_extractor import ImageOcrExtractor
from app.intelligence.extractors.pdf_extractor import PdfIntelligenceExtractor
from app.models.document import Document, DocumentChunk
from app.models.document_intelligence import (
    DocumentEntity,
    DocumentProcessingJob,
    DocumentRelationship,
    DocumentVersion,
)
from app.repositories.document_repo import DocumentChunkRepository, DocumentRepository

PIPELINE_VERSION = "2.1.0"

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif"}
DOCX_LIKE = {"docx", "doc"}
XLSX_LIKE = {"xlsx", "xls"}
TEXT_LIKE = {"txt", "json", "md", "log", "csv"}


class DocumentIntelligencePipeline:
    """End-to-End Orchestrator for Nexora AI Document Intelligence Engine."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
        self.pdf_extractor = PdfIntelligenceExtractor()
        self.docx_extractor = DocxIntelligenceExtractor()
        self.excel_extractor = ExcelIntelligenceExtractor()
        self.csv_extractor = CsvIntelligenceExtractor()
        self.ocr_extractor = ImageOcrExtractor()

    async def process_document_id(self, document_id: uuid.UUID | str) -> StructuredDocument:
        start_time = time.time()
        doc_id = uuid.UUID(str(document_id))
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Track observability job record
        job = await self._create_job(doc.id, doc.company_id)

        try:
            return await self._process(doc, job, start_time)
        except Exception as exc:
            await self._mark_failed(doc, job, exc)
            raise

    async def _create_job(self, document_id: uuid.UUID, company_id: uuid.UUID) -> DocumentProcessingJob:
        previous_failures = select(func.count()).select_from(DocumentProcessingJob).where(
            DocumentProcessingJob.document_id == document_id,
            DocumentProcessingJob.status == "failed",
        )
        result = await self.db.execute(previous_failures)
        retry_count = result.scalar() or 0

        job = DocumentProcessingJob(
            document_id=document_id,
            company_id=company_id,
            status="retrying" if retry_count else "processing",
            pipeline_version=PIPELINE_VERSION,
            retry_count=retry_count,
        )
        self.db.add(job)
        await self.db.commit()
        return job

    async def _mark_failed(self, doc: Document, job: DocumentProcessingJob, exc: Exception) -> None:
        try:
            job.status = "failed"
            job.error_details = str(exc)[:4000]
            doc.status = "failed"
            doc.error_message = str(exc)[:4000]
            await self.db.commit()
        except Exception:  # pragma: no cover - best effort
            await self.db.rollback()

    async def _process(self, doc: Document, job: DocumentProcessingJob, start_time: float) -> StructuredDocument:
        # Fetch file data from MinIO
        from app.storage.minio_client import MinioClient

        minio_client = MinioClient()
        file_data = await minio_client.get_file(doc.stored_path)
        if not file_data:
            raise ValueError(f"File data for document {doc.id} not found in MinIO")

        # Step 1: Duplicate Detection
        content_hash = duplicate_detector.compute_content_hash(file_data)
        is_dup, dup_id = await duplicate_detector.check_duplicate(
            self.db, doc.company_id, content_hash, doc.original_filename
        )
        doc.content_hash = content_hash
        doc.is_duplicate = is_dup
        doc.duplicate_of_id = dup_id

        # Step 2: Format Extraction & OCR
        ext = (doc.file_extension or "").lower().lstrip(".")
        ocr_start = time.time()
        extracted = await self._extract(file_data, ext, doc.original_filename)
        ocr_duration_ms = int((time.time() - ocr_start) * 1000)

        full_text = extracted.get("full_text", "") or ""
        raw_chunks = extracted.get("chunks", []) or []
        extracted_meta = extracted.get("metadata", {}) or {}

        # Step 3: Document Understanding — classification, language, metadata
        detected_type = classifier.classify(full_text, filename=doc.original_filename)
        language = detect_language(full_text) if full_text else None

        doc.detected_type = detected_type
        doc.category = detected_type.lower()
        doc.language = language or doc.language
        doc.page_count = extracted.get("page_count", 1)
        doc.title = extracted_meta.get("title") or doc.title or doc.original_filename
        doc.author = extracted_meta.get("author") or doc.author
        doc.summary = (full_text[:500] if full_text else "No text extracted")
        doc.ocr_text = full_text[:1000]
        doc.processed_at = datetime.now(timezone.utc)

        # Step 4: Intelligent Chunking
        processed_chunks = intelligent_chunker.process_chunks(raw_chunks)

        # Step 5: Embeddings Generation (idempotent — derived data is replaced on reprocess)
        emb_start = time.time()
        embedding_service = EmbeddingService()
        embedding_info = await embedding_service.get_embedding_info()
        doc.embedding_model = embedding_info.get("model")
        doc.embedding_version = embedding_info.get("version")

        await self._replace_derived_data(doc.id)

        chunk_id_by_index: dict[int, uuid.UUID] = {}
        for chunk_data in processed_chunks:
            try:
                emb = await embedding_service.create_embedding(chunk_data.content)
            except Exception:
                emb = []

            if emb:
                doc.embedding_dimensions = len(emb)

            chunk_meta = {
                "source": doc.original_filename,
                "chunk_index": chunk_data.chunk_index,
                "page_number": chunk_data.page_number,
                "section_title": chunk_data.section_title,
                "chunk_type": chunk_data.chunk_type,
                "detected_type": detected_type,
                "document_id": str(doc.id),
                "embedding_model": embedding_info.get("model"),
                "embedding_version": embedding_info.get("version"),
                **chunk_data.metadata,
            }

            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk_data.chunk_index,
                content=chunk_data.content,
                embedding=emb,
                token_count=chunk_data.token_count,
                meta_data=json.dumps(chunk_meta, ensure_ascii=False),
            )
            self.db.add(db_chunk)
            await self.db.flush()
            chunk_id_by_index[chunk_data.chunk_index] = db_chunk.id

        await self.db.commit()
        embedding_duration_ms = int((time.time() - emb_start) * 1000)

        # Step 6: Entity & Relationship Extraction
        ext_start = time.time()
        entity_extractor = EntityRelationshipExtractor(self.db)
        extracted_entities, extracted_rels = await entity_extractor.extract_from_chunks(
            processed_chunks, document_title=doc.original_filename
        )

        entity_db_map: dict[tuple[str, str], uuid.UUID] = {}
        seen_entities: set[tuple[str, str]] = set()
        for ent in extracted_entities:
            key = (ent.entity_name.strip().lower(), ent.entity_type.lower())
            if key in seen_entities:
                continue
            seen_entities.add(key)

            db_ent = DocumentEntity(
                document_id=doc.id,
                company_id=doc.company_id,
                chunk_id=chunk_id_by_index.get(ent.chunk_index) if ent.chunk_index is not None else None,
                entity_name=ent.entity_name,
                entity_type=ent.entity_type,
                confidence=ent.confidence,
                attributes=json.dumps(ent.attributes, ensure_ascii=False),
            )
            self.db.add(db_ent)
            await self.db.flush()
            entity_db_map[(ent.entity_name.strip().lower(), ent.entity_type.lower())] = db_ent.id

        relationship_count = 0
        for rel in extracted_rels:
            src_id = self._resolve_entity_id(rel.source_entity_name, entity_db_map)
            tgt_id = self._resolve_entity_id(rel.target_entity_name, entity_db_map)
            if src_id and tgt_id and src_id != tgt_id:
                db_rel = DocumentRelationship(
                    document_id=doc.id,
                    company_id=doc.company_id,
                    source_entity_id=src_id,
                    target_entity_id=tgt_id,
                    relationship_type=rel.relationship_type,
                    confidence=rel.confidence,
                    context_snippet=rel.context_snippet,
                )
                self.db.add(db_rel)
                relationship_count += 1

        await self.db.commit()
        extraction_duration_ms = int((time.time() - ext_start) * 1000)

        # Step 7: Second Brain update (skipped for documents already ingested from integrations)
        if doc.source_system != "integration" and len(full_text.strip()) > 20:
            from app.integrations.contracts.types import NexoraEvent
            from app.integrations.memory_router import memory_router

            memory_event = NexoraEvent(
                company_id=doc.company_id,
                integration_id=doc.id,
                source_vendor="document_intelligence",
                event_type="document.processed",
                resource_type=detected_type,
                resource_id=str(doc.id),
                title=doc.original_filename,
                content_summary=full_text[:500],
                is_important=True,
                requires_memory_ingestion=True,
            )
            await memory_router.route_event_to_memory(self.db, memory_event)

        # Finalize status & job metrics
        total_time_ms = int((time.time() - start_time) * 1000)
        doc.status = "completed"
        doc.error_message = None

        job.status = "completed"
        job.processing_time_ms = total_time_ms
        job.ocr_duration_ms = ocr_duration_ms
        job.embedding_duration_ms = embedding_duration_ms
        job.extraction_duration_ms = extraction_duration_ms
        job.chunk_count = len(processed_chunks)
        job.entity_count = len(seen_entities)
        job.relationship_count = relationship_count

        await self.db.commit()
        await self.db.refresh(doc)

        return StructuredDocument(
            document_id=doc.id,
            original_filename=doc.original_filename,
            file_extension=doc.file_extension,
            detected_type=detected_type,
            language=language or "und",
            title=doc.title,
            author=doc.author,
            summary=doc.summary,
            content_hash=content_hash,
            is_duplicate=is_dup,
            duplicate_of_id=dup_id,
            page_count=doc.page_count or 1,
            chunks=processed_chunks,
            entities=extracted_entities,
            relationships=extracted_rels,
            metadata={
                "embedding_model": embedding_info.get("model"),
                "embedding_version": embedding_info.get("version"),
                "pipeline_version": PIPELINE_VERSION,
            },
        )

    async def _extract(self, file_data: bytes, ext: str, filename: str) -> dict[str, Any]:
        if ext == "pdf":
            return await self.pdf_extractor.extract(file_data)
        if ext in DOCX_LIKE:
            return await self.docx_extractor.extract(file_data)
        if ext in XLSX_LIKE:
            return await self.excel_extractor.extract(file_data)
        if ext == "csv":
            return await self.csv_extractor.extract(file_data)
        if ext in IMAGE_EXTENSIONS:
            return await self.ocr_extractor.extract(file_data, filename=filename)
        if ext in TEXT_LIKE:
            try:
                text = file_data.decode("utf-8", errors="replace")
            except Exception:
                text = ""
            text = text.strip()
            return {
                "full_text": text,
                "page_count": 1,
                "chunks": [
                    ExtractedChunk(
                        chunk_index=0,
                        content=text,
                        token_count=len(text.split()),
                        page_number=1,
                        section_title=None,
                        chunk_type="text",
                        metadata={},
                    )
                ]
                if text
                else [],
                "metadata": {},
            }
        # Unknown / binary format: graceful fallback with a clear notice
        notice = f"[UNSUPPORTED FORMAT .{ext}]\nFile: {filename}\nNotice: Format not recognized by Document Intelligence extractors."
        return {
            "full_text": notice,
            "page_count": 1,
            "chunks": [],
            "metadata": {},
        }

    async def _replace_derived_data(self, document_id: uuid.UUID) -> None:
        """Removes previously derived chunks/entities/relationships before reprocessing.

        Ensures retries and reprocessing never duplicate knowledge.
        """
        await self.db.execute(delete(DocumentRelationship).where(DocumentRelationship.document_id == document_id))
        await self.db.execute(delete(DocumentEntity).where(DocumentEntity.document_id == document_id))
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        await self.db.commit()

    @staticmethod
    def _resolve_entity_id(name: str, entity_db_map: dict[tuple[str, str], uuid.UUID]) -> uuid.UUID | None:
        name_lower = (name or "").strip().lower()
        for (n, _t), eid in entity_db_map.items():
            if n == name_lower:
                return eid
        return None
