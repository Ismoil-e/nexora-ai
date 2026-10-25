from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


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
    attachment_name: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str
    chat_id: UUID | None = None
    attachment_name: str | None = None


class LegacyChatMessage(BaseModel):
    id: str
    role: Literal["user", "ai", "assistant"]
    text: str
    timestamp: str | None = None
    attachment_name: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class ImportChatHistoryRequest(BaseModel):
    messages: list[LegacyChatMessage] = Field(max_length=5000)


class SendMessageResponse(BaseModel):
    message: ChatMessageResponse
    ai_message: ChatMessageResponse
    chat_id: UUID


class ChatUpdate(BaseModel):
    title: str | None = None
    is_archived: bool | None = None
