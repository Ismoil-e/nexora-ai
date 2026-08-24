"""Task Planner — decomposes complex user requests into executable subtasks.

The planner analyzes a request and produces a structured execution plan with:
- Subtasks with dependencies
- Agent assignments per subtask
- Tool requirements
- Execution strategy (sequential, parallel, fallback)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionStrategy(str, Enum):
    """How subtasks are executed."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    DELEGATION = "delegation"
    AGGREGATION = "aggregation"
    FALLBACK = "fallback"


class SubtaskStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_TOOL = "waiting_for_tool"
    WAITING_FOR_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    RETRYING = "retrying"


@dataclass
class Subtask:
    """A single unit of work in the execution plan."""
    id: str
    description: str
    agent_key: str
    tools: list[str] = field(default_factory=list)
    input_template: str = ""
    depends_on: list[str] = field(default_factory=list)  # subtask IDs
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 2
    requires_approval: bool = False
    approval_type: str | None = None
    status: SubtaskStatus = SubtaskStatus.CREATED
    result: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """Complete execution plan for a complex request."""
    id: str
    original_request: str
    user_intent: str
    subtasks: list[Subtask] = field(default_factory=list)
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    context_sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    estimated_duration_ms: int = 0
    requires_human_approval: bool = False


# Intent patterns for subtask decomposition
_INTENT_PATTERNS: dict[str, dict[str, Any]] = {
    "analyze_and_report": {
        "keywords": ["tahlil", "hisobot", "report", "analyze", "analytics",
                      "sotish", "performance", "natija"],
        "subtasks": [
            {"desc": "Ma'lumotlarni yig'ish", "agent": "analytics", "tools": ["query_company_kpis", "get_business_insights"]},
            {"desc": "Tahlil qilish", "agent": "analytics", "tools": ["get_business_insights"]},
            {"desc": "Hisobot yaratish", "agent": "analytics", "tools": ["generate_executive_summary", "search_knowledge_base"]},
            {"desc": "Natijani xulosa qilish", "agent": "chat", "tools": []},
        ],
        "strategy": ExecutionStrategy.SEQUENTIAL,
    },
    "search_and_summarize": {
        "keywords": ["qidir", "search", "top", "find", "qisqacha", "summary"],
        "subtasks": [
            {"desc": "Bilim bazasidan qidirish", "agent": "search", "tools": ["search_knowledge_base"]},
            {"desc": "Hujjatlardan qidirish", "agent": "document", "tools": ["intelligence_search"]},
            {"desc": "Natijalarni xulosa qilish", "agent": "chat", "tools": []},
        ],
        "strategy": ExecutionStrategy.PARALLEL,
    },
    "plan_and_execute": {
        "keywords": ["reja", "plan", "bosqich", "step", "strategy", "qanday"],
        "subtasks": [
            {"desc": "Talablarni tahlil qilish", "agent": "planning", "tools": ["search_knowledge_base"]},
            {"desc": "Reja tuzish", "agent": "planning", "tools": []},
            {"desc": "Vazifalarni yaratish", "agent": "task", "tools": ["create_company_task"]},
        ],
        "strategy": ExecutionStrategy.SEQUENTIAL,
    },
    "risk_assessment": {
        "keywords": ["risk", "xatar", "anomaliya", "monitoring", "ogohlantirish"],
        "subtasks": [
            {"desc": "Operatsion xatarlarni aniqlash", "agent": "monitoring", "tools": ["detect_operational_risks"]},
            {"desc": "KPIlarni tekshirish", "agent": "analytics", "tools": ["query_company_kpis"]},
            {"desc": "Ogohlantirish yaratish", "agent": "notification", "tools": ["send_notification"]},
        ],
        "strategy": ExecutionStrategy.SEQUENTIAL,
    },
    "document_analysis": {
        "keywords": ["hujjat", "document", "pdf", "fayl", "file", "tahlil"],
        "subtasks": [
            {"desc": "Hujjatni tahlil qilish", "agent": "document", "tools": ["intelligence_search", "get_document_intelligence"]},
            {"desc": "Xulosani tayyorlash", "agent": "chat", "tools": []},
        ],
        "strategy": ExecutionStrategy.SEQUENTIAL,
    },
    "knowledge_query": {
        "keywords": ["bilim", "knowledge", "qonun", "qoida", "policy", "document"],
        "subtasks": [
            {"desc": "Bilim bazasidan izlash", "agent": "knowledge", "tools": ["search_knowledge_base"]},
            {"desc": "Knowledge Graph'dan izlash", "agent": "knowledge", "tools": ["intelligence_search"]},
            {"desc": "Javobni tayyorlash", "agent": "chat", "tools": []},
        ],
        "strategy": ExecutionStrategy.PARALLEL,
    },
}


def classify_intent(user_input: str) -> str:
    """Classify user intent from input text."""
    text = (user_input or "").lower()

    best_match = None
    best_score = 0

    for intent, pattern in _INTENT_PATTERNS.items():
        score = sum(1 for kw in pattern["keywords"] if kw in text)
        if score > best_score:
            best_score = score
            best_match = intent

    # Default to simple chat
    return best_match or "simple_chat"


class TaskPlanner:
    """Decomposes complex requests into executable subtask plans."""

    def __init__(self):
        self._complexity_threshold = 50  # chars — below this, single agent is enough

    def should_decompose(self, user_input: str, metadata: dict[str, Any] | None = None) -> bool:
        """Determine if a request should be decomposed into subtasks."""
        meta = metadata or {}

        # Explicit force
        if meta.get("force_orchestrate"):
            return True

        if meta.get("single_agent"):
            return False

        # Simple short queries
        if len(user_input.strip()) < self._complexity_threshold:
            return False

        # Check if intent matches a decomposition pattern
        intent = classify_intent(user_input)
        if intent != "simple_chat":
            return True

        # Complex indicators
        complex_indicators = [
            "va shuningdek", "and also", "keyin", "then",
            "birinchi", "first", "shundan keyin", "after that",
            "tahlil", "hisobot", "analyze", "report",
            "reja", "plan", "bosqich", "step",
        ]
        return any(ind in user_input.lower() for ind in complex_indicators)

    def plan(
        self,
        user_input: str,
        *,
        metadata: dict[str, Any] | None = None,
        company_id: uuid.UUID | None = None,
    ) -> ExecutionPlan:
        """Create an execution plan for the user request."""
        meta = metadata or {}
        intent = classify_intent(user_input)
        plan_id = str(uuid.uuid4())

        if intent == "simple_chat":
            # Single agent plan
            plan = ExecutionPlan(
                id=plan_id,
                original_request=user_input,
                user_intent=intent,
                subtasks=[
                    Subtask(
                        id="t1",
                        description="Suhbat javobi",
                        agent_key="chat",
                        tools=[],
                        strategy=ExecutionStrategy.SEQUENTIAL,
                    )
                ],
                strategy=ExecutionStrategy.SEQUENTIAL,
            )
        else:
            pattern = _INTENT_PATTERNS[intent]
            subtasks = []
            for i, st_def in enumerate(pattern["subtasks"]):
                subtask = Subtask(
                    id=f"t{i+1}",
                    description=st_def["desc"],
                    agent_key=st_def["agent"],
                    tools=st_def.get("tools", []),
                    depends_on=[f"t{j+1}" for j in range(i)]
                        if pattern["strategy"] == ExecutionStrategy.SEQUENTIAL else [],
                    strategy=pattern["strategy"],
                )
                subtasks.append(subtask)

            plan = ExecutionPlan(
                id=plan_id,
                original_request=user_input,
                user_intent=intent,
                subtasks=subtasks,
                strategy=pattern["strategy"],
                context_sources=["documents", "knowledge", "memory"],
                estimated_duration_ms=len(subtasks) * 2000,
            )

        plan.metadata = meta
        return plan

    def get_subtask_display(self, plan: ExecutionPlan) -> list[dict[str, Any]]:
        """Get a user-friendly display of the execution plan."""
        return [
            {
                "step": i + 1,
                "id": st.id,
                "description": st.description,
                "agent": st.agent_key,
                "tools": st.tools,
                "status": st.status.value,
                "depends_on": st.depends_on,
            }
            for i, st in enumerate(plan.subtasks)
        ]
