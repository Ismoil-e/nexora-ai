from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowStepIn(BaseModel):
    name: str | None = None
    step_order: int | None = None
    action_key: str
    config: dict = Field(default_factory=dict)
    condition: dict | None = None
    on_failure: str = "stop"
    retry_limit: int = 0
    is_optional: bool = False
    timeout_seconds: int | None = None


class WorkflowTriggerIn(BaseModel):
    trigger_type: str
    config: dict = Field(default_factory=dict)
    is_active: bool = True


class WorkflowScheduleIn(BaseModel):
    cron_expression: str | None = None
    interval_seconds: int | None = None
    timezone: str = "Asia/Tashkent"


class WorkflowCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    workflow_type: str = "manual"
    status: str = "draft"
    version: str = "1.0.0"
    requires_approval: bool = False
    max_retries: int = 3
    timeout_seconds: int = 3600
    tags: list[str] = Field(default_factory=list)
    steps: list[WorkflowStepIn]
    triggers: list[WorkflowTriggerIn] | None = None
    schedule: WorkflowScheduleIn | None = None
    definition: dict | None = None


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    workflow_type: str | None = None
    status: str | None = None
    version: str | None = None
    requires_approval: bool | None = None
    max_retries: int | None = None
    timeout_seconds: int | None = None
    tags: list[str] | None = None
    steps: list[WorkflowStepIn] | None = None


class WorkflowExecuteRequest(BaseModel):
    payload: dict = Field(default_factory=dict)
    trigger_type: str = "user_request"
    async_mode: bool = False
    workflow_slug: str | None = None


class WorkflowTemplateInstallRequest(BaseModel):
    slug: str
    activate: bool = True
