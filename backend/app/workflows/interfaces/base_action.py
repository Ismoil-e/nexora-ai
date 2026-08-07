"""Base action interface for workflow automation plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.workflows.contracts.types import ActionContext, ActionResult


class BaseAction(ABC):
    """Every automation action implements this contract.

    Actions must not open DB sessions themselves. They use injected services.
    """

    action_key: str
    display_name: str
    description: str
    category: str = "general"
    version: str = "1.0.0"

    @abstractmethod
    async def validate(self, context: ActionContext) -> None:
        """Validate config/payload before execution."""

    @abstractmethod
    async def execute(self, context: ActionContext) -> ActionResult:
        """Perform the action."""

    async def compensate(self, context: ActionContext, result: ActionResult) -> None:
        """Optional rollback hook for failed multi-step workflows."""
        return None
