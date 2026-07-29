from uuid import UUID

from pydantic import BaseModel


class ChatCreate(BaseModel):
    title: str = "New Chat"
    ai_provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    agent_id: UUID | None = None


class ChatResponse(BaseModel):
    id: UUID
    title: str
    ai_provider: str
    model: str
    token_count: int
    is_archived: bool
    created_at: str
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    role: str
    content: str
    token_count: int
    created_at: str

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str
    chat_id: UUID | None = None


class SendMessageResponse(BaseModel):
    message: ChatMessageResponse
    ai_message: ChatMessageResponse
    chat_id: UUID


class ChatUpdate(BaseModel):
    title: str | None = None
    is_archived: bool | None = None
