import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.models.document_intelligence import (
    DocumentEntity,
    DocumentProcessingJob,
    DocumentRelationship,
    DocumentVersion,
)
from app.repositories.base import BaseRepository


class DocumentIntelligenceRepository:
    """Repository for Document Intelligence derived data (entities, relationships,
    versions, jobs, knowledge graph) and filtered hybrid search."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.entity_repo = BaseRepository(DocumentEntity, db)
        self.relationship_repo = BaseRepository(DocumentRelationship, db)
        self.version_repo = BaseRepository(DocumentVersion, db)
        self.job_repo = BaseRepository(DocumentProcessingJob, db)

    # ---- Document derived data -------------------------------------------

    async def get_entities_by_document(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[DocumentEntity]:
        stmt = (
            select(DocumentEntity)
            .join(Document, Document.id == DocumentEntity.document_id)
            .where(
                DocumentEntity.document_id == document_id,
                Document.company_id == company_id,
                DocumentEntity.deleted_at.is_(None),
            )
            .order_by(DocumentEntity.confidence.desc(), DocumentEntity.entity_type.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_relationships_by_document(
        self, company_id: uuid.UUID, document_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT dr.id, dr.relationship_type, dr.confidence, dr.context_snippet,
                   se.entity_name AS source_name, se.entity_type AS source_type,
                   te.entity_name AS target_name, te.entity_type AS target_type
            FROM document_relationships dr
            JOIN document_entities se ON se.id = dr.source_entity_id
            JOIN document_entities te ON te.id = dr.target_entity_id
            JOIN documents d ON d.id = dr.document_id
            WHERE dr.document_id = :document_id
              AND d.company_id = :company_id
              AND dr.deleted_at IS NULL
            ORDER BY dr.confidence DESC
        """)
        result = await self.db.execute(stmt, {"document_id": str(document_id), "company_id": str(company_id)})
        return [dict(r) for r in result.mappings().all()]

    async def get_versions_by_document(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(
                DocumentVersion.document_id == document_id,
                Document.company_id == company_id,
                DocumentVersion.deleted_at.is_(None),
            )
            .order_by(DocumentVersion.version_number.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_jobs_by_document(self, company_id: uuid.UUID, document_id: uuid.UUID) -> list[DocumentProcessingJob]:
        stmt = (
            select(DocumentProcessingJob)
            .join(Document, Document.id == DocumentProcessingJob.document_id)
            .where(
                DocumentProcessingJob.document_id == document_id,
                Document.company_id == company_id,
            )
            .order_by(DocumentProcessingJob.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_knowledge_sources(self, company_id: uuid.UUID, document_id: uuid.UUID, top_k: int = 50) -> list[dict[str, Any]]:
        """Traceable knowledge sources: chunk-level citations with page references."""
        stmt = text("""
            SELECT dc.id AS chunk_id, dc.chunk_index, dc.content, dc.token_count, dc.meta_data
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.document_id = :document_id
              AND d.company_id = :company_id
              AND dc.deleted_at IS NULL
            ORDER BY dc.chunk_index ASC
            LIMIT :top_k
        """)
        result = await self.db.execute(stmt, {"document_id": str(document_id), "company_id": str(company_id), "top_k": top_k})
        return [dict(r) for r in result.mappings().all()]

    # ---- Knowledge Graph ---------------------------------------------------

    async def get_knowledge_graph(self, company_id: uuid.UUID, node_limit: int = 200) -> dict[str, Any]:
        """Company-level interconnected graph built from document entities & relationships.

        Nodes are deduplicated by (name, type) across all tenant documents; edges carry
        source document references so knowledge stays traceable.
        """
        nodes_stmt = text("""
            SELECT de.entity_name, de.entity_type,
                   COUNT(DISTINCT de.document_id) AS document_count,
                   array_agg(DISTINCT de.document_id::text) AS document_ids
            FROM document_entities de
            JOIN documents d ON d.id = de.document_id
            WHERE d.company_id = :company_id AND d.deleted_at IS NULL AND de.deleted_at IS NULL
            GROUP BY de.entity_name, de.entity_type
            ORDER BY document_count DESC
            LIMIT :node_limit
        """)
        nodes_result = await self.db.execute(
            nodes_stmt, {"company_id": str(company_id), "node_limit": node_limit}
        )
        nodes = []
        for r in nodes_result.mappings().all():
            nodes.append({
                "name": r["entity_name"],
                "type": r["entity_type"],
                "document_count": r["document_count"],
                "document_ids": list(r["document_ids"] or []),
            })

        edges_stmt = text("""
            SELECT se.entity_name AS source_name, se.entity_type AS source_type,
                   te.entity_name AS target_name, te.entity_type AS target_type,
                   dr.relationship_type, MAX(dr.confidence) AS confidence,
                   COUNT(DISTINCT dr.document_id) AS occurrence_count,
                   MIN(dr.document_id::text) AS source_document_id,
                   (SELECT original_filename FROM documents dd WHERE dd.id = dr.document_id) AS source_document
            FROM document_relationships dr
            JOIN document_entities se ON se.id = dr.source_entity_id
            JOIN document_entities te ON te.id = dr.target_entity_id
            JOIN documents d ON d.id = dr.document_id
            WHERE d.company_id = :company_id AND d.deleted_at IS NULL AND dr.deleted_at IS NULL
            GROUP BY se.entity_name, se.entity_type, te.entity_name, te.entity_type,
                     dr.relationship_type, dr.document_id
            ORDER BY occurrence_count DESC
            LIMIT :edge_limit
        """)
        edges_result = await self.db.execute(edges_stmt, {"company_id": str(company_id), "edge_limit": node_limit * 2})
        edges = [dict(r) for r in edges_result.mappings().all()]

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # ---- Filtered hybrid search ---------------------------------------------

    async def search_filtered(
        self,
        query_text: str,
        embedding: list[float],
        company_id: uuid.UUID,
        top_k: int = 5,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        document_type: str | None = None,
        department_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source_system: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = "d.company_id = :company_id AND d.deleted_at IS NULL"
        params: dict[str, Any] = {
            "embedding": str(embedding),
            "query_text": query_text,
            "company_id": str(company_id),
            "limit_pool": top_k * 4,
            "top_k": top_k,
            "vector_weight": vector_weight,
            "text_weight": text_weight,
        }

        if document_type:
            filters += " AND d.detected_type = :document_type"
            params["document_type"] = document_type
        if department_id:
            filters += " AND d.department_id = :department_id"
            params["department_id"] = str(department_id)
        if project_id:
            filters += " AND d.project_id = :project_id"
            params["project_id"] = str(project_id)
        if source_system:
            filters += " AND d.source_system = :source_system"
            params["source_system"] = source_system
        if date_from:
            filters += " AND d.created_at >= :date_from"
            params["date_from"] = date_from
        if date_to:
            filters += " AND d.created_at <= :date_to"
            params["date_to"] = date_to

        query = text(f"""
            WITH vector_matches AS (
                SELECT dc.id,
                       ROW_NUMBER() OVER (ORDER BY dc.embedding <=> :embedding::vector ASC) AS vec_rank
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE {filters} AND dc.embedding IS NOT NULL
                LIMIT :limit_pool
            ),
            text_matches AS (
                SELECT dc.id,
                       ROW_NUMBER() OVER (ORDER BY ts_rank_cd(to_tsvector('simple', dc.content), plainto_tsquery('simple', :query_text)) DESC) AS text_rank
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE {filters}
                  AND to_tsvector('simple', dc.content) @@ plainto_tsquery('simple', :query_text)
                LIMIT :limit_pool
            )
            SELECT dc.id AS chunk_id, dc.document_id, dc.chunk_index, dc.content, dc.token_count,
                   dc.meta_data,
                   d.original_filename, d.detected_type, d.language, d.department_id, d.project_id,
                   d.source_system,
                   (COALESCE(1.0 / (60 + vm.vec_rank), 0.0) * :vector_weight +
                    COALESCE(1.0 / (60 + tm.text_rank), 0.0) * :text_weight) AS combined_score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            LEFT JOIN vector_matches vm ON dc.id = vm.id
            LEFT JOIN text_matches tm ON dc.id = tm.id
            WHERE vm.id IS NOT NULL OR tm.id IS NOT NULL
            ORDER BY combined_score DESC
            LIMIT :top_k
        """)
        result = await self.db.execute(query, params)
        return [dict(r) for r in result.mappings().all()]

    async def count_documents(self, company_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Document).where(
            Document.company_id == company_id,
            Document.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def count_documents_by_status(self, company_id: uuid.UUID, status: str) -> int:
        stmt = select(func.count()).select_from(Document).where(
            Document.company_id == company_id,
            Document.status == status,
            Document.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
