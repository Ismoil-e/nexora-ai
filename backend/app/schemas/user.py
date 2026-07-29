from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    avatar_url: str | None = None
    position: str | None = None
    is_active: bool
    is_verified: bool
    company_id: UUID
    role_id: UUID | None = None
    created_at: str

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    avatar_url: str | None = None
    preferences: str | None = None


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    avatar_url: str | None = None
    position: str | None = None
    phone: str | None = None
    company_name: str
    company_id: UUID
    role_name: str | None = None
    is_verified: bool
    created_at: str
