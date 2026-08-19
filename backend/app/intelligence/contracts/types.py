import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field


DocumentCategory = Literal[
    "Contract",
    "Invoice",
    "Report",
    "Policy",
    "Meeting Notes",
    "Proposal",
    "Financial Document",
    "HR Document",
    "Technical Document",
    "Government Document",
    "Logistics Document",
    "Manufacturing Document",
    "Research Document",
    "Other",
]


class ExtractedChunk(BaseModel):
    chunk_index: int
    content: str
    token_count: int = 0
    page_number: int | None = None
    section_title: str | None = None
    chunk_type: str = "text"  # text, table, heading, code, image_caption
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedEntity(BaseModel):
    entity_name: str
    entity_type: str  # Person, Company, Department, Project, Contract, Invoice, Location, Metric, Task, Decision
    confidence: float = 1.0
    attributes: dict[str, Any] = Field(default_factory=dict)
    chunk_index: int | None = None


class ExtractedRelationship(BaseModel):
    source_entity_name: str
    target_entity_name: str
    relationship_type: str  # WORKS_FOR, MEMBER_OF, BELONGS_TO, SIGNED_BY, AFFECTS, DESCRIBES
    confidence: float = 1.0
    context_snippet: str | None = None


class StructuredDocument(BaseModel):
    document_id: uuid.UUID
    original_filename: str
    file_extension: str
    detected_type: DocumentCategory = "Other"
    language: str = "en"
    title: str | None = None
    author: str | None = None
    organization: str | None = None
    summary: str | None = None
    content_hash: str
    is_duplicate: bool = False
    duplicate_of_id: uuid.UUID | None = None
    page_count: int = 1
    chunks: list[ExtractedChunk] = Field(default_factory=list)
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
