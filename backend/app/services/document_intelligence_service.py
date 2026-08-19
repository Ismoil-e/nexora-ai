import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EmbeddingService
from app.models.document import Document, DocumentChunk
from app.models.document_intelligence import DocumentProcessingJob
from app.repositories.document_intelligence_repo import DocumentIntelligenceRepository
from app.repositories.document_repo import DocumentRepository
from app.utils.exceptions import NotFoundException, ValidationException


class DocumentIntelligenceService:
    """High-level service exposing Document Intelligence read/action operations.

    All access is tenant-scoped: every query filters by company_id so a user can
    never read a document from another tenant.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.repo = DocumentIntelligenceRepository(db)
        self.embedding_service = EmbeddingService()

    async def _get_document(self, company_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc or doc.company_id != company_id or doc.deleted_at:
            raise NotFoundException(detail="Document not found or access denied")
        return doc

    async def assert_document_exists(self, company_id: uuid.UUID, document_id: uuid.UUID) -> None:
        await self._get_document(company_id, document_id)

    async def get_stats(self, company_id: uuid.UUID) -> dict[str, Any]:
        return {
            "total_documents": await self.repo.count_documents(company_id),
            "completed_documents": await self.repo.count_documents_by_status(company_id, "completed"),
            "failed_documents": await self.repo.count_documents_by_status(company_id, "failed"),
            "queued_documents": await self.repo.count_documents_by_status(company_id, "queued"),
            "processing_documents": await self.repo.count_documents_by_status(company_id, "processing"),
        }

    # ---- Intelligence view -------------------------------------------------

    async def get_intelligence(self, company_id: uuid.UUID, document_id: uuid.UUID) -> dict[str, Any]:
        doc = await self._get_document(company_id, document_id)
        entities = await self.repo.get_entities_by_document(company_id, document_id)
        relationships = await self.repo.get_relationships_by_document(company_id, document_id)
        chunks = await self.repo.get_knowledge_sources(company_id, document_id, top_k=200)
        jobs = await self.repo.get_jobs_by_document(company_id, document_id)

        return {
            "document": {
                "id": str(doc.id),
                "original_filename": doc.original_filename,
                "file_extension": doc.file_extension,
                "mime_type": doc.mime_type,
                "file_size": doc.file_size,
                "category": doc.category,
                "status": doc.status,
                "detected_type": doc.detected_type,
                "language": doc.language,
                "title": doc.title,
                "author": doc.author,
                "summary": doc.summary,
                "page_count": doc.page_count,
                "is_duplicate": doc.is_duplicate,
                "duplicate_of_id": str(doc.duplicate_of_id) if doc.duplicate_of_id else None,
                "source_system": doc.source_system,
                "embedding_model": doc.embedding_model,
                "embedding_version": doc.embedding_version,
                "embedding_dimensions": doc.embedding_dimensions,
                "department_id": str(doc.department_id) if doc.department_id else None,
                "project_id": str(doc.project_id) if doc.project_id else None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
            },
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "chunk_count": len(chunks),
            "entities": [self._serialize_entity(e) for e in entities],
            "relationships": relationships,
            "chunks": [self._serialize_chunk_source(c) for c in chunks],
            "processing_jobs": [self._serialize_job(j) for j in jobs[:20]],
        }

    # ---- Chunks / entities / relationships / versions / jobs ---------------

    async def get_chunks(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[dict[str, Any]]:
        await self._get_document(company_id, document_id)
        sources = await self.repo.get_knowledge_sources(company_id, document_id, top_k=1000)
        return [self._serialize_chunk_source(c) for c in sources]

    async def get_entities(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[dict[str, Any]]:
        await self._get_document(company_id, document_id)
        entities = await self.repo.get_entities_by_document(company_id, document_id)
        return [self._serialize_entity(e) for e in entities]

    async def get_relationships(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[dict[str, Any]]:
        await self._get_document(company_id, document_id)
        return await self.repo.get_relationships_by_document(company_id, document_id)

    async def get_versions(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[dict[str, Any]]:
        await self._get_document(company_id, document_id)
        versions = await self.repo.get_versions_by_document(company_id, document_id)
        return [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "parent_version_id": str(v.parent_version_id) if v.parent_version_id else None,
                "stored_path": v.stored_path,
                "file_size": v.file_size,
                "change_summary": v.change_summary,
                "created_by": str(v.created_by) if v.created_by else None,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def get_jobs(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[dict[str, Any]]:
        await self._get_document(company_id, document_id)
        jobs = await self.repo.get_jobs_by_document(company_id, document_id)
        return [self._serialize_job(j) for j in jobs]

    async def get_knowledge_sources(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[dict[str, Any]]:
        await self._get_document(company_id, document_id)
        return await self.repo.get_knowledge_sources(company_id, document_id)

    # ---- Knowledge graph ----------------------------------------------------

    async def get_knowledge_graph(self, company_id: uuid.UUID, node_limit: int = 200) -> dict[str, Any]:
        return await self.repo.get_knowledge_graph(company_id, node_limit=node_limit)

    # ---- Search --------------------------------------------------------------

    async def search(
        self,
        company_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        document_type: str | None = None,
        department_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source_system: str | None = None,
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise ValidationException(detail="Qidiruv matni (query) talab qilinadi")

        query_embedding = await self.embedding_service.create_embedding(query)
        results = await self.repo.search_filtered(
            query_text=query,
            embedding=query_embedding,
            company_id=company_id,
            top_k=top_k,
            document_type=document_type,
            department_id=department_id,
            project_id=project_id,
            date_from=date_from,
            date_to=date_to,
            source_system=source_system,
        )

        return {
            "query": query,
            "total": len(results),
            "results": [
                {
                    "chunk_id": r["chunk_id"],
                    "document_id": str(r["document_id"]),
                    "chunk_index": r["chunk_index"],
                    "content": r["content"],
                    "score": round(float(r["combined_score"]), 6),
                    "document": {
                        "original_filename": r["original_filename"],
                        "detected_type": r["detected_type"],
                        "language": r["language"],
                        "department_id": str(r["department_id"]) if r["department_id"] else None,
                        "project_id": str(r["project_id"]) if r["project_id"] else None,
                        "source_system": r["source_system"],
                    },
                    "citations": self._extract_citations(r),
                }
                for r in results
            ],
        }

    # ---- Reindex ---------------------------------------------------------------

    async def reindex_document(self, company_id: uuid.UUID, document_id: uuid.UUID) -> dict[str, Any]:
        doc = await self._get_document(company_id, document_id)

        stmt = (
            update(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id, DocumentChunk.deleted_at.is_(None))
            .values(embedding=None)
        )
        await self.db.execute(stmt)

        chunks = await self.doc_chunks_for_reindex(doc.id)
        embedding_info = await self.embedding_service.get_embedding_info()
        reindexed = 0

        for chunk in chunks:
            try:
                emb = await self.embedding_service.create_embedding(chunk.content)
            except Exception:
                emb = []

            meta = {}
            if chunk.meta_data:
                try:
                    meta = json.loads(chunk.meta_data)
                except (TypeError, ValueError):
                    meta = {}
            meta["embedding_model"] = embedding_info.get("model")
            meta["embedding_version"] = embedding_info.get("version")

            chunk.embedding = emb or None
            chunk.meta_data = json.dumps(meta, ensure_ascii=False)
            if emb:
                reindexed += 1
                doc.embedding_dimensions = len(emb)

        doc.embedding_model = embedding_info.get("model")
        doc.embedding_version = embedding_info.get("version")
        await self.db.commit()

        return {
            "document_id": str(doc.id),
            "status": "reindexed",
            "reindexed_chunks": reindexed,
            "embedding_model": embedding_info.get("model"),
            "embedding_version": embedding_info.get("version"),
        }

    async def doc_chunks_for_reindex(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        from sqlalchemy import select

        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id, DocumentChunk.deleted_at.is_(None))
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---- Serializers ------------------------------------------------------------

    @staticmethod
    def _serialize_entity(e) -> dict[str, Any]:
        attributes = {}
        if e.attributes:
            try:
                attributes = json.loads(e.attributes)
            except (TypeError, ValueError):
                attributes = {}
        return {
            "id": str(e.id),
            "entity_name": e.entity_name,
            "entity_type": e.entity_type,
            "confidence": e.confidence,
            "chunk_id": str(e.chunk_id) if e.chunk_id else None,
            "attributes": attributes,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }

    @staticmethod
    def _serialize_chunk_source(c: dict[str, Any]) -> dict[str, Any]:
        meta = {}
        if c.get("meta_data"):
            try:
                meta = json.loads(c["meta_data"])
            except (TypeError, ValueError):
                meta = {}
        return {
            "chunk_id": c["chunk_id"],
            "chunk_index": c.get("chunk_index"),
            "content": c.get("content"),
            "token_count": c.get("token_count"),
            "page_number": meta.get("page_number") or meta.get("page"),
            "section_title": meta.get("section_title"),
            "chunk_type": meta.get("chunk_type", "text"),
            "citation": meta.get("citation") or (f"Page {meta.get('page')}" if meta.get("page") else None),
            "metadata": meta,
        }

    @staticmethod
    def _serialize_job(j: DocumentProcessingJob) -> dict[str, Any]:
        return {
            "id": str(j.id),
            "status": j.status,
            "pipeline_version": j.pipeline_version,
            "processing_time_ms": j.processing_time_ms,
            "ocr_duration_ms": j.ocr_duration_ms,
            "embedding_duration_ms": j.embedding_duration_ms,
            "extraction_duration_ms": j.extraction_duration_ms,
            "chunk_count": j.chunk_count,
            "entity_count": j.entity_count,
            "relationship_count": j.relationship_count,
            "retry_count": j.retry_count,
            "error_details": j.error_details,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }

    @staticmethod
    def _extract_citations(r: dict[str, Any]) -> list[str]:
        citations = []
        meta = {}
        if r.get("meta_data"):
            try:
                meta = json.loads(r["meta_data"])
            except (TypeError, ValueError):
                meta = {}
        if meta.get("page") is not None:
            citations.append(f"Page {meta['page']}")
        elif meta.get("page_number") is not None:
            citations.append(f"Page {meta['page_number']}")
        if meta.get("section_title"):
            citations.append(meta["section_title"])
        if not citations and r.get("original_filename"):
            citations.append(r["original_filename"])
        return citations
