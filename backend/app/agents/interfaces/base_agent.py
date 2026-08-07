"""Base agent interface every Nexora capability agent must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.agents.contracts.types import (
    AgentContext,
    AgentPlan,
    AgentRequest,
    AgentResult,
    MemoryBundle,
)


class BaseAgent(ABC):
    """Lifecycle contract for modular AI agents.

    Agents must not access the database directly. They communicate through
    injected services and Cognitive Core connectors.
    """

    agent_key: str
    display_name: str
    description: str
    capabilities: list[str]
    version: str = "1.0.0"

    def __init__(self) -> None:
        self._initialized = False
        self._services: dict[str, Any] = {}

    async def initialize(self, services: dict[str, Any] | None = None) -> None:
        """Inject services and mark agent ready."""
        self._services = services or {}
        self._initialized = True

    @abstractmethod
    async def validate(self, request: AgentRequest) -> None:
        """Validate request payload and permissions. Raise on failure."""

    @abstractmethod
    async def build_context(self, request: AgentRequest) -> AgentContext:
        """Build agent-specific context frame."""

    @abstractmethod
    async def retrieve_memory(self, context: AgentContext) -> MemoryBundle:
        """Retrieve hybrid memory evidence via connectors/services."""

    @abstractmethod
    async def plan(self, context: AgentContext, memory: MemoryBundle) -> AgentPlan:
        """Produce an execution plan before calling providers/tools."""

    @abstractmethod
    async def execute(
        self,
        context: AgentContext,
        memory: MemoryBundle,
        plan: AgentPlan,
    ) -> AgentResult:
        """Execute the plan (sync path). Long jobs should set async flags."""

    async def post_process(
        self,
        context: AgentContext,
        result: AgentResult,
    ) -> AgentResult:
        """Optional cleanup / formatting hook."""
        return result

    async def save_memory(
        self,
        context: AgentContext,
        result: AgentResult,
    ) -> list[str]:
        """Persist episodic / organizational memory writeback refs."""
        return []

    async def publish_events(
        self,
        context: AgentContext,
        result: AgentResult,
    ) -> None:
        """Publish domain events for audit and downstream workers."""
        return None

    async def return_response(self, result: AgentResult) -> AgentResult:
        """Final response shaping hook."""
        return result

    def require_service(self, name: str) -> Any:
        """Fetch an injected service or raise."""
        if name not in self._services:
            raise RuntimeError(f"Service '{name}' is not injected into agent '{self.agent_key}'")
        return self._services[name]
