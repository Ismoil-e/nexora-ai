"""Bootstrap: register all default agents into the global registry."""

from __future__ import annotations

from app.agents.core.registry import AgentRegistry, agent_registry
from app.agents.implementations.default_agents import DEFAULT_AGENT_CLASSES

_bootstrapped = False


def bootstrap_agents(registry: AgentRegistry | None = None) -> AgentRegistry:
    """Idempotently register default capability agents."""
    global _bootstrapped
    reg = registry or agent_registry
    for cls in DEFAULT_AGENT_CLASSES:
        if not reg.has(cls.agent_key):
            reg.register(cls)
    _bootstrapped = True
    return reg


def ensure_agents_bootstrapped() -> AgentRegistry:
    if not _bootstrapped or not agent_registry.keys():
        return bootstrap_agents()
    return agent_registry
