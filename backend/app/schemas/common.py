from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list


class StandardResponse(BaseModel):
    success: bool = True
    message: str | None = None
    data: dict | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: str | None = None
    request_id: str | None = None
