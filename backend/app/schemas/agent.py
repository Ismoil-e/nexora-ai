from uuid import UUID

from pydantic import BaseModel, Field


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
    agent_key: str | None = None
    agent_type: str | None = None
    version: str = "1.0.0"


class AgentResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    ai_provider: str
    model: str
    is_active: bool
    icon: str | None = None
    color: str | None = None
    agent_key: str | None = None
    agent_type: str | None = None
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
    agent_key: str | None = None
    agent_type: str | None = None
    version: str | None = None


class AgentExecuteRequest(BaseModel):
    input: str
    chat_id: UUID | None = None


class AgentExecuteResponse(BaseModel):
    output: str
    execution_id: UUID | None = None
    token_used: int = 0
    duration_ms: int = 0
    agent_key: str | None = None
    steps: list[dict] | None = None


class FrameworkAgentRunRequest(BaseModel):
    input: str
    chat_id: UUID | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    async_mode: bool = False
    provider: str | None = None
    model: str | None = None


class FrameworkAgentRunResponse(BaseModel):
    success: bool
    output: str
    agent_key: str
    execution_id: UUID | None = None
    status: str
    token_used: int = 0
    duration_ms: int = 0
    citations: list[dict] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    async_task_id: str | None = None
    error: str | None = None
    steps: list[dict] = Field(default_factory=list)
