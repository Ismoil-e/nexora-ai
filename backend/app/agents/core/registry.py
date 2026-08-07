"""Agent registry — pluggable catalog of capability agents."""

from __future__ import annotations

from typing import Type

from app.agents.interfaces.base_agent import BaseAgent


class AgentRegistry:
    """In-process registry for agent classes and instances.

    Future agents register via ``register`` / ``register_instance`` without
    modifying existing agent implementations (Open/Closed Principle).
    """

    def __init__(self) -> None:
        self._classes: dict[str, Type[BaseAgent]] = {}
        self._instances: dict[str, BaseAgent] = {}

    def register(self, agent_cls: Type[BaseAgent]) -> Type[BaseAgent]:
        """Register an agent class by its ``agent_key``."""
        key = getattr(agent_cls, "agent_key", None)
        if not key:
            raise ValueError(f"Agent class {agent_cls.__name__} missing agent_key")
        self._classes[key] = agent_cls
        return agent_cls

    def register_instance(self, agent: BaseAgent) -> None:
        """Register a pre-built agent instance."""
        self._instances[agent.agent_key] = agent
        self._classes.setdefault(agent.agent_key, agent.__class__)

    def get_class(self, agent_key: str) -> Type[BaseAgent] | None:
        return self._classes.get(agent_key)

    def create(self, agent_key: str) -> BaseAgent:
        if agent_key in self._instances:
            return self._instances[agent_key]
        agent_cls = self._classes.get(agent_key)
        if not agent_cls:
            raise KeyError(f"Agent '{agent_key}' is not registered")
        agent = agent_cls()
        self._instances[agent_key] = agent
        return agent

    def has(self, agent_key: str) -> bool:
        return agent_key in self._classes

    def list_catalog(self) -> list[dict]:
        catalog: list[dict] = []
        for key, cls in sorted(self._classes.items()):
            catalog.append({
                "agent_key": key,
                "display_name": getattr(cls, "display_name", key),
                "description": getattr(cls, "description", ""),
                "capabilities": list(getattr(cls, "capabilities", [])),
                "version": getattr(cls, "version", "1.0.0"),
            })
        return catalog

    def keys(self) -> list[str]:
        return sorted(self._classes.keys())


# Process-wide singleton used by bootstrap / DI
agent_registry = AgentRegistry()
