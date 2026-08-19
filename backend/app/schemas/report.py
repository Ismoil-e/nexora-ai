from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    title: str
    report_type: str = "monthly_executive"
    content: Optional[str] = None
    format: str = "markdown"
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.5-flash"


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    report_type: str
    status: str
    format: str
    created_at: datetime
    file_url: Optional[str] = None


class ReportDetailResponse(ReportResponse):
    content: Optional[str] = None
    ai_provider: str
    ai_model: str
    error_message: Optional[str] = None


class ReportGenerateRequest(BaseModel):
    title: str
    report_type: str = "monthly_executive"
    description: Optional[str] = None
    format: str = "markdown"
    include_charts: bool = False
