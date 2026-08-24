"""Execution Tracer — tracks orchestration execution with full visibility.

Records every step of the orchestration pipeline:
- Orchestrator start/end
- Task planning
- Agent selection
- Agent execution start/end
- Model calls
- Tool calls
- Retrieval
- Memory access
- Knowledge Graph queries
- Failures/retries
- Latency, token usage, cost
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TraceEventType(str, Enum):
    ORCHESTRATION_START = "orchestration_start"
    ORCHESTRATION_END = "orchestration_end"
    PLAN_CREATED = "plan_created"
    AGENT_SELECTED = "agent_selected"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_FAILED = "agent_failed"
    AGENT_RETRY = "agent_retry"
    MODEL_CALL_START = "model_call_start"
    MODEL_CALL_END = "model_call_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    TOOL_CALL_FAILED = "tool_call_failed"
    RETRIEVAL_START = "retrieval_start"
    RETRIEVAL_END = "retrieval_end"
    MEMORY_ACCESS = "memory_access"
    CONTEXT_ASSEMBLED = "context_assembled"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    SUBTASK_START = "subtask_start"
    SUBTASK_END = "subtask_end"
    SUBTASK_FAILED = "subtask_failed"
    FALLBACK_TRIGGERED = "fallback_triggered"
    ERROR = "error"


class TraceEventType_Overall(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # some subtasks succeeded, some failed


@dataclass
class TraceEvent:
    """A single trace event."""
    id: str
    event_type: TraceEventType
    timestamp: float
    duration_ms: int = 0
    agent_key: str | None = None
    tool_name: str | None = None
    model: str | None = None
    provider: str | None = None
    tokens: int = 0
    cost: float = 0.0
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "agent_key": self.agent_key,
            "tool_name": self.tool_name,
            "model": self.model,
            "provider": self.provider,
            "tokens": self.tokens,
            "cost": round(self.cost, 6),
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
            "parent_event_id": self.parent_event_id,
        }


@dataclass
class OrchestrationTrace:
    """Complete trace for an orchestration run."""
    id: str
    request_id: str
    company_id: uuid.UUID
    user_id: uuid.UUID
    user_input: str
    status: TraceEventType_Overall = TraceEventType_Overall.PENDING
    events: list[TraceEvent] = field(default_factory=list)
    plan_id: str | None = None
    plan_description: str | None = None
    final_output: str | None = None
    total_tokens: int = 0
    total_cost: float = 0.0
    started_at: float | None = None
    ended_at: float | None = None
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_event(self, event: TraceEvent) -> None:
        self.events.append(event)
        if event.tokens:
            self.total_tokens += event.tokens
        if event.cost:
            self.total_cost += event.cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "company_id": str(self.company_id),
            "user_id": str(self.user_id),
            "user_input": self.user_input[:500],
            "status": self.status.value,
            "events": [e.to_dict() for e in self.events],
            "plan_id": self.plan_id,
            "plan_description": self.plan_description,
            "final_output": (self.final_output[:1000] if self.final_output else None),
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

    def to_timeline(self) -> list[dict[str, Any]]:
        """Get a user-friendly timeline of the execution."""
        timeline = []
        for event in self.events:
            item: dict[str, Any] = {
                "type": event.event_type.value,
                "timestamp": event.timestamp,
                "duration_ms": event.duration_ms,
                "success": event.success,
            }

            # Human-readable descriptions
            if event.event_type == TraceEventType.ORCHESTRATION_START:
                item["label"] = "So'rov qabul qilindi"
                item["icon"] = "🎯"
            elif event.event_type == TraceEventType.PLAN_CREATED:
                item["label"] = "Reja tuzildi"
                item["icon"] = "📋"
                item["steps"] = event.metadata.get("steps", [])
            elif event.event_type == TraceEventType.AGENT_SELECTED:
                item["label"] = f"Agent tanlandi: {event.agent_key}"
                item["icon"] = "🤖"
                item["agent"] = event.agent_key
            elif event.event_type == TraceEventType.AGENT_START:
                item["label"] = f"Agent ishga tushdi: {event.agent_key}"
                item["icon"] = "▶️"
                item["agent"] = event.agent_key
            elif event.event_type == TraceEventType.AGENT_END:
                item["label"] = f"Agent tugadi: {event.agent_key}"
                item["icon"] = "✅"
                item["agent"] = event.agent_key
            elif event.event_type == TraceEventType.AGENT_FAILED:
                item["label"] = f"Agent xatosi: {event.agent_key}"
                item["icon"] = "❌"
                item["error"] = event.error
            elif event.event_type == TraceEventType.MODEL_CALL_START:
                item["label"] = f"AI model chaqirildi: {event.provider}/{event.model}"
                item["icon"] = "🧠"
            elif event.event_type == TraceEventType.MODEL_CALL_END:
                item["label"] = f"AI model javobi: {event.tokens} token"
                item["icon"] = "📊"
                item["tokens"] = event.tokens
                item["cost"] = event.cost
            elif event.event_type == TraceEventType.TOOL_CALL_START:
                item["label"] = f"Vosita ishlatildi: {event.tool_name}"
                item["icon"] = "🔧"
                item["tool"] = event.tool_name
            elif event.event_type == TraceEventType.TOOL_CALL_END:
                item["label"] = f"Vosita tugadi: {event.tool_name}"
                item["icon"] = "✔️"
            elif event.event_type == TraceEventType.TOOL_CALL_FAILED:
                item["label"] = f"Vosita xatosi: {event.tool_name}"
                item["icon"] = "⚠️"
                item["error"] = event.error
            elif event.event_type == TraceEventType.RETRIEVAL_START:
                item["label"] = "Ma'lumotlar qidirilmoqda..."
                item["icon"] = "🔍"
            elif event.event_type == TraceEventType.RETRIEVAL_END:
                item["label"] = f"Qidiruv tugadi: {event.metadata.get('count', 0)} natija"
                item["icon"] = "📄"
            elif event.event_type == TraceEventType.MEMORY_ACCESS:
                item["label"] = "Xotiradan ma'lumot olingan"
                item["icon"] = "🧠"
            elif event.event_type == TraceEventType.CONTEXT_ASSEMBLED:
                item["label"] = f"Kontekst tayyor: {event.metadata.get('tokens', 0)} token"
                item["icon"] = "📦"
            elif event.event_type == TraceEventType.APPROVAL_REQUESTED:
                item["label"] = "Tasdiqlash so'raldi"
                item["icon"] = "⏳"
            elif event.event_type == TraceEventType.FALLBACK_TRIGGERED:
                item["label"] = "Muqobil model ishlatildi"
                item["icon"] = "🔄"
            elif event.event_type == TraceEventType.ORCHESTRATION_END:
                item["label"] = "Tugadi"
                item["icon"] = "🏁"
            elif event.event_type == TraceEventType.ERROR:
                item["label"] = f"Xatolik: {event.error}"
                item["icon"] = "💥"

            timeline.append(item)

        return timeline


class ExecutionTracer:
    """Creates and manages orchestration traces."""

    def __init__(self):
        self._traces: dict[str, OrchestrationTrace] = {}

    def start_trace(
        self,
        *,
        request_id: str,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationTrace:
        """Start a new orchestration trace."""
        trace = OrchestrationTrace(
            id=str(uuid.uuid4()),
            request_id=request_id,
            company_id=company_id,
            user_id=user_id,
            user_input=user_input,
            started_at=time.time(),
            metadata=metadata or {},
        )
        self._traces[trace.id] = trace

        trace.add_event(TraceEvent(
            id=str(uuid.uuid4()),
            event_type=TraceEventType.ORCHESTRATION_START,
            timestamp=time.time(),
        ))
        return trace

    def end_trace(
        self,
        trace_id: str,
        *,
        status: TraceEventType_Overall = TraceEventType_Overall.COMPLETED,
        final_output: str | None = None,
    ) -> OrchestrationTrace | None:
        """End an orchestration trace."""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        trace.ended_at = time.time()
        trace.status = status
        trace.final_output = final_output
        trace.duration_ms = int((trace.ended_at - trace.started_at) * 1000)

        trace.add_event(TraceEvent(
            id=str(uuid.uuid4()),
            event_type=TraceEventType.ORCHESTRATION_END,
            timestamp=trace.ended_at,
            duration_ms=trace.duration_ms,
            metadata={"status": status.value, "total_tokens": trace.total_tokens},
        ))
        return trace

    def record_plan(
        self,
        trace_id: str,
        plan_id: str,
        steps: list[dict[str, Any]],
    ) -> None:
        """Record plan creation."""
        trace = self._traces.get(trace_id)
        if trace:
            trace.plan_id = plan_id
            trace.plan_description = f"{len(steps)} ta qadam"
            trace.add_event(TraceEvent(
                id=str(uuid.uuid4()),
                event_type=TraceEventType.PLAN_CREATED,
                timestamp=time.time(),
                metadata={"plan_id": plan_id, "steps": [s.get("description", s.get("desc", "")) for s in steps]},
            ))

    def record_agent_selected(
        self,
        trace_id: str,
        agent_key: str,
    ) -> None:
        """Record agent selection."""
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_event(TraceEvent(
                id=str(uuid.uuid4()),
                event_type=TraceEventType.AGENT_SELECTED,
                timestamp=time.time(),
                agent_key=agent_key,
            ))

    def record_agent_start(
        self,
        trace_id: str,
        agent_key: str,
    ) -> str:
        """Record agent execution start. Returns event ID for end recording."""
        event_id = str(uuid.uuid4())
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_event(TraceEvent(
                id=event_id,
                event_type=TraceEventType.AGENT_START,
                timestamp=time.time(),
                agent_key=agent_key,
            ))
        return event_id

    def record_agent_end(
        self,
        trace_id: str,
        agent_key: str,
        *,
        success: bool = True,
        tokens: int = 0,
        cost: float = 0.0,
        error: str | None = None,
        parent_event_id: str | None = None,
    ) -> None:
        """Record agent execution end."""
        event_type = TraceEventType.AGENT_END if success else TraceEventType.AGENT_FAILED
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_event(TraceEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=time.time(),
                agent_key=agent_key,
                tokens=tokens,
                cost=cost,
                success=success,
                error=error,
                parent_event_id=parent_event_id,
            ))

    def record_model_call(
        self,
        trace_id: str,
        *,
        provider: str,
        model: str,
        tokens: int = 0,
        cost: float = 0.0,
        duration_ms: int = 0,
        success: bool = True,
    ) -> None:
        """Record an AI model call."""
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_event(TraceEvent(
                id=str(uuid.uuid4()),
                event_type=TraceEventType.MODEL_CALL_END,
                timestamp=time.time(),
                duration_ms=duration_ms,
                provider=provider,
                model=model,
                tokens=tokens,
                cost=cost,
                success=success,
            ))

    def record_tool_call(
        self,
        trace_id: str,
        *,
        tool_name: str,
        duration_ms: int = 0,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Record a tool call."""
        event_type = TraceEventType.TOOL_CALL_END if success else TraceEventType.TOOL_CALL_FAILED
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_event(TraceEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=time.time(),
                duration_ms=duration_ms,
                tool_name=tool_name,
                success=success,
                error=error,
            ))

    def record_retrieval(
        self,
        trace_id: str,
        *,
        source_type: str,
        count: int = 0,
        duration_ms: int = 0,
    ) -> None:
        """Record a retrieval event."""
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_event(TraceEvent(
                id=str(uuid.uuid4()),
                event_type=TraceEventType.RETRIEVAL_END,
                timestamp=time.time(),
                duration_ms=duration_ms,
                metadata={"source_type": source_type, "count": count},
            ))

    def record_context_assembled(
        self,
        trace_id: str,
        *,
        tokens: int,
        source_count: int,
    ) -> None:
        """Record context assembly completion."""
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_event(TraceEvent(
                id=str(uuid.uuid4()),
                event_type=TraceEventType.CONTEXT_ASSEMBLED,
                timestamp=time.time(),
                metadata={"tokens": tokens, "source_count": source_count},
            ))

    def record_error(
        self,
        trace_id: str,
        error: str,
        *,
        agent_key: str | None = None,
    ) -> None:
        """Record an error event."""
        trace = self._traces.get(trace_id)
        if trace:
            trace.add_event(TraceEvent(
                id=str(uuid.uuid4()),
                event_type=TraceEventType.ERROR,
                timestamp=time.time(),
                agent_key=agent_key,
                error=error,
                success=False,
            ))

    def get_trace(self, trace_id: str) -> OrchestrationTrace | None:
        return self._traces.get(trace_id)

    def get_trace_as_dict(self, trace_id: str) -> dict[str, Any] | None:
        trace = self._traces.get(trace_id)
        return trace.to_dict() if trace else None

    def get_timeline(self, trace_id: str) -> list[dict[str, Any]]:
        trace = self._traces.get(trace_id)
        return trace.to_timeline() if trace else []

    def list_traces(
        self,
        company_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List recent traces, optionally filtered by company."""
        traces = list(self._traces.values())
        if company_id:
            traces = [t for t in traces if t.company_id == company_id]
        traces.sort(key=lambda t: t.started_at or 0, reverse=True)
        return [t.to_dict() for t in traces[:limit]]


# Process-wide singleton
execution_tracer = ExecutionTracer()
