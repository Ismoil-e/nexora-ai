from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    file_size: int
    file_extension: str
    category: str | None = None
    status: str
    page_count: int | None = None
    created_at: str
    uploaded_by: UUID

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    id: UUID
    original_filename: str
    status: str
    message: str


class DocumentChunkResponse(BaseModel):
    id: UUID
    chunk_index: int
    content: str
    token_count: int

    model_config = {"from_attributes": True}


class RAGQueryRequest(BaseModel):
    query: str
    document_ids: list[UUID] | None = None
    top_k: int = 5


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    token_used: int
