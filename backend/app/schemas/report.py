from uuid import UUID

from pydantic import BaseModel


class ReportCreate(BaseModel):
    title: str
    report_type: str
    content: str | None = None
    format: str = "markdown"
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.5-flash"


class ReportResponse(BaseModel):
    id: UUID
    title: str
    report_type: str
    status: str
    format: str
    created_at: str
    file_url: str | None = None

    model_config = {"from_attributes": True}


class ReportGenerateRequest(BaseModel):
    title: str
    report_type: str
    description: str
    format: str = "markdown"
    include_charts: bool = False
