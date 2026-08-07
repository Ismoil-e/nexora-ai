"""Shared contracts for the Workflow Automation Engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkflowType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    APPROVAL = "approval"
    AI_GENERATED = "ai_generated"
    MULTI_STEP = "multi_step"
    LONG_RUNNING = "long_running"
    BACKGROUND = "background"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(str, Enum):
    USER_REQUEST = "user_request"
    API = "api"
    WEBHOOK = "webhook"
    CRON = "cron"
    DB_EVENT = "db_event"
    FILE_UPLOAD = "file_upload"
    DOCUMENT_CREATED = "document_created"
    TASK_COMPLETED = "task_completed"
    MEETING_FINISHED = "meeting_finished"
    AI_DECISION = "ai_decision"
    IOT_EVENT = "iot_event"


@dataclass
class WorkflowIdentity:
    user_id: uuid.UUID | None
    company_id: uuid.UUID
    permissions: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)


@dataclass
class WorkflowRunRequest:
    workflow_id: uuid.UUID | None = None
    workflow_slug: str | None = None
    identity: WorkflowIdentity | None = None
    trigger_type: str = TriggerType.USER_REQUEST.value
    payload: dict[str, Any] = field(default_factory=dict)
    async_mode: bool = False
    force_sync: bool = False


@dataclass
class ActionContext:
    """Runtime context passed into every action (no direct DB for action plugins)."""

    company_id: uuid.UUID
    user_id: uuid.UUID | None
    execution_id: uuid.UUID
    workflow_id: uuid.UUID
    step_order: int
    action_key: str
    config: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    shared_state: dict[str, Any] = field(default_factory=dict)
    services: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    should_stop: bool = False
    requires_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "message": self.message,
            "should_stop": self.should_stop,
            "requires_approval": self.requires_approval,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowRunResult:
    success: bool
    execution_id: uuid.UUID | None
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    celery_task_id: str | None = None
    steps_completed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "celery_task_id": self.celery_task_id,
            "steps_completed": self.steps_completed,
        }
