from uuid import UUID

from pydantic import BaseModel


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: str | None = None
    description: str | None = None
    industry: str | None = None
    size: str | None = None
    is_active: bool
    subscription_plan: str
    ai_credits: int
    max_users: int
    created_at: str

    model_config = {"from_attributes": True}


class CompanyUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    description: str | None = None
    industry: str | None = None
    size: str | None = None
    website: str | None = None
    settings: str | None = None
