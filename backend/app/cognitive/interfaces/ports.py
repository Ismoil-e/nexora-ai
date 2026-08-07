"""Ports for Cognitive Core engines consumed by agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.agents.contracts.types import AgentIdentity, AgentRequest
from app.cognitive.contracts.frames import ContextFrame, EvidencePack


class ContextEnginePort(ABC):
    """Builds identity-aware context frames."""

    @abstractmethod
    async def build(self, identity: AgentIdentity, request: AgentRequest) -> ContextFrame:
        raise NotImplementedError


class MemoryEnginePort(ABC):
    """Retrieves hybrid memory evidence without direct DB access from agents."""

    @abstractmethod
    async def retrieve(self, frame: ContextFrame, query: str, top_k: int = 5) -> EvidencePack:
        raise NotImplementedError

    @abstractmethod
    async def save_episode(
        self,
        frame: ContextFrame,
        agent_key: str,
        input_text: str,
        output_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError


class PlanningEnginePort(ABC):
    """Produces high-level plans for agent execution."""

    @abstractmethod
    async def plan(
        self,
        frame: ContextFrame,
        evidence: EvidencePack,
        agent_key: str,
        intent: str,
    ) -> dict[str, Any]:
        raise NotImplementedError
