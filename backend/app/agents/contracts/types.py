"""Shared contracts for the AI Agent Framework."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Lifecycle status for an agent execution."""

    PENDING = "pending"
    VALIDATING = "validating"
    BUILDING_CONTEXT = "building_context"
    RETRIEVING_MEMORY = "retrieving_memory"
    PLANNING = "planning"
    EXECUTING = "executing"
    POST_PROCESSING = "post_processing"
    SAVING_MEMORY = "saving_memory"
    PUBLISHING_EVENTS = "publishing_events"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"


class AgentCapability(str, Enum):
    """Capability tags used for routing and catalog discovery."""

    DOCUMENT = "document"
    CHAT = "chat"
    ANALYTICS = "analytics"
    MONITORING = "monitoring"
    TASK = "task"
    NOTIFICATION = "notification"
    KNOWLEDGE = "knowledge"
    SEARCH = "search"
    PLANNING = "planning"


@dataclass
class AgentIdentity:
    """Authenticated caller projected into the agent pipeline."""

    user_id: uuid.UUID
    company_id: uuid.UUID
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    department_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None


@dataclass
class AgentRequest:
    """Inbound request accepted by AgentManager."""

    agent_key: str
    input: str
    identity: AgentIdentity
    chat_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    async_mode: bool = False
    provider: str | None = None
    model: str | None = None


@dataclass
class AgentContext:
    """Assembled runtime context for a single agent run."""

    request: AgentRequest
    company_id: uuid.UUID
    user_id: uuid.UUID
    permissions: list[str] = field(default_factory=list)
    conversation_summary: str | None = None
    active_documents: list[dict[str, Any]] = field(default_factory=list)
    project_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    workflow_hints: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryBundle:
    """Evidence returned by the Hybrid Memory / Cognitive connectors."""

    items: list[dict[str, Any]] = field(default_factory=list)
    graph_summary: dict[str, Any] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    query: str = ""


@dataclass
class AgentPlan:
    """Structured plan produced before execution."""

    steps: list[dict[str, Any]] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    rationale: str = ""
    requires_async: bool = False


@dataclass
class AgentResult:
    """Normalized agent response returned to API / callers."""

    success: bool
    output: str
    agent_key: str
    execution_id: uuid.UUID | None = None
    status: AgentStatus = AgentStatus.COMPLETED
    plan: AgentPlan | None = None
    memory_refs: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    token_used: int = 0
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    async_task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "agent_key": self.agent_key,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "status": self.status.value,
            "plan": {
                "steps": self.plan.steps if self.plan else [],
                "tools": self.plan.tools if self.plan else [],
                "rationale": self.plan.rationale if self.plan else "",
            },
            "memory_refs": self.memory_refs,
            "citations": self.citations,
            "steps": self.steps,
            "token_used": self.token_used,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "error": self.error,
            "async_task_id": self.async_task_id,
        }
