import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EntityResponse(BaseModel):
    id: uuid.UUID
    entity_name: str
    entity_type: str
    confidence: float
    chunk_id: uuid.UUID | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class RelationshipResponse(BaseModel):
    id: uuid.UUID
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relationship_type: str
    confidence: float
    context_snippet: str | None = None


class VersionResponse(BaseModel):
    id: uuid.UUID
    version_number: int
    parent_version_id: uuid.UUID | None = None
    stored_path: str
    file_size: int | None = None
    change_summary: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime | None = None


class ProcessingJobResponse(BaseModel):
    id: uuid.UUID
    status: str
    pipeline_version: str | None = None
    processing_time_ms: int | None = None
    ocr_duration_ms: int | None = None
    embedding_duration_ms: int | None = None
    extraction_duration_ms: int | None = None
    chunk_count: int | None = None
    entity_count: int | None = None
    relationship_count: int | None = None
    retry_count: int | None = None
    error_details: str | None = None
    created_at: datetime | None = None


class ChunkSourceResponse(BaseModel):
    chunk_id: uuid.UUID
    chunk_index: int | None = None
    content: str | None = None
    token_count: int | None = None
    page_number: int | None = None
    section_title: str | None = None
    chunk_type: str | None = None
    citation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntelligenceResponse(BaseModel):
    document: dict[str, Any]
    entity_count: int
    relationship_count: int
    chunk_count: int
    entities: list[EntityResponse]
    relationships: list[RelationshipResponse]
    chunks: list[ChunkSourceResponse]
    processing_jobs: list[ProcessingJobResponse]


class KnowledgeGraphNode(BaseModel):
    name: str
    type: str
    document_count: int
    document_ids: list[str] = Field(default_factory=list)


class KnowledgeGraphEdge(BaseModel):
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relationship_type: str
    confidence: float | None = None
    occurrence_count: int | None = None
    source_document_id: str | None = None
    source_document: str | None = None


class KnowledgeGraphResponse(BaseModel):
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]
    node_count: int
    edge_count: int


class IntelligenceSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic + full-text search query")
    top_k: int = Field(5, ge=1, le=20)
    document_type: str | None = None
    department_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    source_system: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class IntelligenceSearchResultDocument(BaseModel):
    original_filename: str | None = None
    detected_type: str | None = None
    language: str | None = None
    department_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    source_system: str | None = None


class IntelligenceSearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int | None = None
    content: str | None = None
    score: float
    document: IntelligenceSearchResultDocument = Field(default_factory=IntelligenceSearchResultDocument)
    citations: list[str] = Field(default_factory=list)


class IntelligenceSearchResponse(BaseModel):
    query: str
    total: int
    results: list[IntelligenceSearchResult]


class ReindexResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    reindexed_chunks: int
    embedding_model: str | None = None
    embedding_version: str | None = None


class DocumentStatsResponse(BaseModel):
    total_documents: int
    completed_documents: int
    failed_documents: int
    queued_documents: int
    processing_documents: int
