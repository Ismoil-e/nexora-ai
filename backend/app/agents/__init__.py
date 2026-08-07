"""AI Agent Framework package."""

from app.agents.bootstrap import bootstrap_agents, ensure_agents_bootstrapped
from app.agents.core.manager import AgentManager
from app.agents.core.registry import agent_registry

__all__ = [
    "AgentManager",
    "agent_registry",
    "bootstrap_agents",
    "ensure_agents_bootstrapped",
]
