import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document_repo import DocumentChunkRepository, DocumentRepository
from app.storage.file_handler import FileHandler
from app.storage.minio_client import MinioClient


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
        self.file_handler = FileHandler()
        self.minio = MinioClient()

    async def upload_document(self, company_id: uuid.UUID, user_id: uuid.UUID,
                               file_content: bytes, filename: str, mime_type: str) -> dict:
        from app.models.document import Document
        import os

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        file_size = len(file_content)

        stored_path = await self.minio.upload_file(
            bucket="nexora-documents",
            file_data=file_content,
            filename=filename,
            content_type=mime_type,
        )

        doc = await self.doc_repo.create(
            company_id=company_id,
            uploaded_by=user_id,
            original_filename=filename,
            stored_path=stored_path,
            mime_type=mime_type,
            file_size=file_size,
            file_extension=ext,
            category=self._guess_category(ext),
            status="processing",
        )

        from app.workers.embedding_worker import process_document
        await process_document(str(doc.id))

        return {
            "id": doc.id,
            "original_filename": doc.original_filename,
            "status": "processing",
            "message": "Hujjat qabul qilindi va qayta ishlanmoqda",
        }

    async def get_documents(self, company_id: uuid.UUID, page: int = 1, page_size: int = 20) -> dict:
        docs, total = await self.doc_repo.get_by_company(company_id, page, page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [{
                "id": d.id,
                "original_filename": d.original_filename,
                "mime_type": d.mime_type,
                "file_size": d.file_size,
                "file_extension": d.file_extension,
                "category": d.category,
                "status": d.status,
                "page_count": d.page_count,
                "created_at": d.created_at.isoformat(),
                "uploaded_by": str(d.uploaded_by),
            } for d in docs],
        }

    async def delete_document(self, document_id: uuid.UUID) -> bool:
        doc = await self.doc_repo.get(document_id)
        if not doc:
            return False

        await self.minio.delete_file(doc.stored_path)
        await self.doc_repo.hard_delete(document_id)
        return True

    async def search_rag(self, company_id: uuid.UUID, query: str,
                          document_ids: list[uuid.UUID] | None = None, top_k: int = 5) -> dict:
        from app.services.ai_service import AIService

        ai_service = AIService(self.db)
        query_embedding = await ai_service.create_embedding(query)

        chunks = await self.chunk_repo.search_hybrid(
            query_text=query,
            embedding=query_embedding,
            company_id=company_id,
            top_k=top_k,
        )

        if document_ids:
            chunks = [c for c in chunks if str(c.document_id if hasattr(c, "document_id") else c["document_id"]) in [str(d) for d in document_ids]]

        context = "\n\n".join([c.content if hasattr(c, "content") else c["content"] for c in chunks])

        response = await ai_service.chat(
            provider="gemini",
            model="gemini-2.5-flash",
            messages=[{
                "role": "user",
                "content": f"Quyidagi kontekst asosida savolga javob ber:\n\nKontekst:\n{context}\n\nSavol: {query}",
            }],
            system_prompt="Sen hujjatlar asosida savollarga javob beradigan AI yordamchisan.",
        )

        sources = []
        for c in chunks:
            doc_id = str(c.document_id if hasattr(c, "document_id") else c["document_id"])
            content_snippet = (c.content if hasattr(c, "content") else c["content"])[:200]
            sources.append({"document_id": doc_id, "content": content_snippet})

        return {
            "answer": response["content"],
            "sources": sources,
            "token_used": response.get("token_count", 0),
        }

    def _guess_category(self, ext: str) -> str:
        categories = {
            "pdf": "document",
            "docx": "document",
            "doc": "document",
            "xlsx": "spreadsheet",
            "csv": "spreadsheet",
            "txt": "text",
            "png": "image",
            "jpg": "image",
            "jpeg": "image",
            "webp": "image",
        }
        return categories.get(ext, "other")
