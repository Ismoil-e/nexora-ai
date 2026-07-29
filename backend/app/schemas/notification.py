from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: UUID
    title: str
    body: str
    notification_type: str
    reference_type: str | None = None
    reference_id: UUID | None = None
    is_read: bool
    created_at: str

    model_config = {"from_attributes": True}


class NotificationList(BaseModel):
    total: int
    unread_count: int
    items: list[NotificationResponse]
