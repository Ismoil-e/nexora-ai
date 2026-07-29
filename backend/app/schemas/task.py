from uuid import UUID

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "medium"
    assigned_to: UUID | None = None
    due_date: str | None = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    status: str
    priority: str
    assigned_to: UUID | None = None
    created_by: UUID
    due_date: str | None = None
    completed_at: str | None = None
    is_ai_generated: bool
    created_at: str

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: UUID | None = None
    due_date: str | None = None
