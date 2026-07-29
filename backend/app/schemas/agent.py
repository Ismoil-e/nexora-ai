from uuid import UUID

from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str | None = None
    ai_provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 4096
    capabilities: str | None = None
    tools_config: str | None = None
    icon: str | None = None
    color: str | None = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    ai_provider: str
    model: str
    is_active: bool
    icon: str | None = None
    color: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    ai_provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    is_active: bool | None = None
    capabilities: str | None = None
    tools_config: str | None = None
    icon: str | None = None
    color: str | None = None


class AgentExecuteRequest(BaseModel):
    input: str
    chat_id: UUID | None = None


class AgentExecuteResponse(BaseModel):
    output: str
    execution_id: UUID
    token_used: int
    duration_ms: int
