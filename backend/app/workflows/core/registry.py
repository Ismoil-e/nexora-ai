"""Registries for workflows, actions, and triggers."""

from __future__ import annotations

from typing import Any, Callable, Type

from app.workflows.interfaces.base_action import BaseAction


class ActionRegistry:
    """Pluggable catalog of workflow actions."""

    def __init__(self) -> None:
        self._actions: dict[str, BaseAction] = {}

    def register(self, action: BaseAction) -> None:
        self._actions[action.action_key] = action

    def get(self, action_key: str) -> BaseAction | None:
        return self._actions.get(action_key)

    def require(self, action_key: str) -> BaseAction:
        action = self.get(action_key)
        if not action:
            raise KeyError(f"Action '{action_key}' is not registered")
        return action

    def list_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "action_key": a.action_key,
                "display_name": a.display_name,
                "description": a.description,
                "category": a.category,
                "version": a.version,
            }
            for a in sorted(self._actions.values(), key=lambda x: x.action_key)
        ]

    def keys(self) -> list[str]:
        return sorted(self._actions.keys())


class TriggerRegistry:
    """Catalog of supported trigger types + optional handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._types: set[str] = set()

    def register_type(self, trigger_type: str, handler: Callable[..., Any] | None = None) -> None:
        self._types.add(trigger_type)
        if handler:
            self._handlers[trigger_type] = handler

    def has(self, trigger_type: str) -> bool:
        return trigger_type in self._types

    def list_types(self) -> list[str]:
        return sorted(self._types)

    def get_handler(self, trigger_type: str) -> Callable[..., Any] | None:
        return self._handlers.get(trigger_type)


class WorkflowRegistry:
    """In-memory templates for system/default workflows (slug → definition)."""

    def __init__(self) -> None:
        self._templates: dict[str, dict[str, Any]] = {}

    def register_template(self, slug: str, definition: dict[str, Any]) -> None:
        self._templates[slug] = definition

    def get_template(self, slug: str) -> dict[str, Any] | None:
        return self._templates.get(slug)

    def list_templates(self) -> list[dict[str, Any]]:
        return [
            {"slug": slug, **{k: v for k, v in defn.items() if k != "steps"}}
            for slug, defn in sorted(self._templates.items())
        ]


action_registry = ActionRegistry()
trigger_registry = TriggerRegistry()
workflow_registry = WorkflowRegistry()
