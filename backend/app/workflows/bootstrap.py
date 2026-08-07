"""Bootstrap action, trigger, and workflow template registries."""

from __future__ import annotations

from app.workflows.actions.builtin import DEFAULT_ACTIONS
from app.workflows.contracts.types import TriggerType
from app.workflows.core.registry import action_registry, trigger_registry, workflow_registry
from app.workflows.definitions.templates import default_workflow_templates

_bootstrapped = False


def bootstrap_workflows() -> None:
    global _bootstrapped
    if _bootstrapped and action_registry.keys():
        return

    for action in DEFAULT_ACTIONS:
        if action_registry.get(action.action_key) is None:
            action_registry.register(action)

    for t in TriggerType:
        trigger_registry.register_type(t.value)

    for template in default_workflow_templates():
        workflow_registry.register_template(template["slug"], template)

    _bootstrapped = True


def ensure_workflows_bootstrapped() -> None:
    if not _bootstrapped or not action_registry.keys():
        bootstrap_workflows()
