import uuid

from sqlalchemy import func, select

from app.models.document import Document, DocumentChunk
from app.repositories.base import BaseRepository
from app.utils.helpers import paginate


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db):
        super().__init__(Document, db)

    async def get_by_company(self, company_id: uuid.UUID, page: int = 1, page_size: int = 20) -> tuple[list[Document], int]:
        offset, limit = paginate(page, page_size)
        filters = [Document.company_id == company_id, Document.deleted_at.is_(None)]

        stmt = (
            select(Document)
            .where(*filters)
            .offset(offset).limit(limit)
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(stmt)
        docs = list(result.scalars().all())

        count_stmt = select(func.count()).select_from(Document).where(*filters)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return docs, total

    async def get_by_status(self, company_id: uuid.UUID, status: str) -> list[Document]:
        stmt = select(Document).where(
            Document.company_id == company_id,
            Document.status == status,
            Document.deleted_at.is_(None),
        ).order_by(Document.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, db):
        super().__init__(DocumentChunk, db)

    async def get_by_document(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_similar(self, embedding: list[float], company_id: uuid.UUID, top_k: int = 5) -> list[DocumentChunk]:
        from sqlalchemy import text

        query = text("""
            SELECT dc.id, dc.document_id, dc.chunk_index, dc.content, dc.token_count,
                   dc.embedding <=> :embedding::vector AS distance
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.company_id = :company_id AND d.deleted_at IS NULL
            ORDER BY distance ASC
            LIMIT :top_k
        """)

        result = await self.db.execute(query, {
            "embedding": str(embedding),
            "company_id": str(company_id),
            "top_k": top_k,
        })
        return list(result.mappings().all())

    async def search_hybrid(
        self,
        query_text: str,
        embedding: list[float],
        company_id: uuid.UUID,
        top_k: int = 5,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> list[dict]:
        from sqlalchemy import text

        query = text("""
            WITH vector_matches AS (
                SELECT dc.id,
                       ROW_NUMBER() OVER (ORDER BY dc.embedding <=> :embedding::vector ASC) AS vec_rank
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE d.company_id = :company_id AND d.deleted_at IS NULL AND dc.embedding IS NOT NULL
                LIMIT :limit_pool
            ),
            text_matches AS (
                SELECT dc.id,
                       ROW_NUMBER() OVER (ORDER BY ts_rank_cd(to_tsvector('simple', dc.content), plainto_tsquery('simple', :query_text)) DESC) AS text_rank
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE d.company_id = :company_id AND d.deleted_at IS NULL
                  AND to_tsvector('simple', dc.content) @@ plainto_tsquery('simple', :query_text)
                LIMIT :limit_pool
            )
            SELECT dc.id, dc.document_id, dc.chunk_index, dc.content, dc.token_count,
                   (COALESCE(1.0 / (60 + vm.vec_rank), 0.0) * :vector_weight +
                    COALESCE(1.0 / (60 + tm.text_rank), 0.0) * :text_weight) AS combined_score
            FROM document_chunks dc
            LEFT JOIN vector_matches vm ON dc.id = vm.id
            LEFT JOIN text_matches tm ON dc.id = tm.id
            WHERE vm.id IS NOT NULL OR tm.id IS NOT NULL
            ORDER BY combined_score DESC
            LIMIT :top_k
        """)

        result = await self.db.execute(query, {
            "embedding": str(embedding),
            "query_text": query_text,
            "company_id": str(company_id),
            "limit_pool": top_k * 4,
            "top_k": top_k,
            "vector_weight": vector_weight,
            "text_weight": text_weight,
        })
        mappings = list(result.mappings().all())
        if mappings:
            return mappings

        return await self.search_similar(embedding, company_id, top_k)

