"""Unit tests for Workflow Automation Engine."""

from __future__ import annotations

import uuid

import pytest

from app.workflows.bootstrap import bootstrap_workflows
from app.workflows.contracts.types import ActionContext
from app.workflows.core.builder import WorkflowBuilder, WorkflowValidator
from app.workflows.core.condition import ConditionEngine, RetryEngine
from app.workflows.core.registry import ActionRegistry, action_registry, trigger_registry, workflow_registry
from app.workflows.actions.builtin import CreateNotificationAction, DEFAULT_ACTIONS


def test_bootstrap_registers_actions_triggers_templates():
    bootstrap_workflows()
    assert len(action_registry.keys()) >= 20
    assert "user_request" in trigger_registry.list_types()
    assert "document_created" in trigger_registry.list_types()
    assert workflow_registry.get_template("document-ingest") is not None
    keys = {a.action_key for a in DEFAULT_ACTIONS}
    assert "trigger_ai_agent" in keys
    assert "generate_summary" in keys


def test_workflow_builder_and_validator():
    bootstrap_workflows()
    builder = WorkflowBuilder()
    validator = WorkflowValidator()
    definition = builder.build(
        name="Test Flow",
        slug="test-flow",
        workflow_type="manual",
        steps=[
            {"action_key": "create_notification", "name": "Notify", "config": {"title": "Hi", "body": "Test"}},
            {"action_key": "update_memory", "step_order": 2},
        ],
        triggers=[{"trigger_type": "user_request"}],
    )
    validator.validate_definition(definition)
    assert len(definition["steps"]) == 2


def test_validator_rejects_unknown_action():
    bootstrap_workflows()
    validator = WorkflowValidator()
    from app.utils.exceptions import ValidationException

    with pytest.raises(ValidationException):
        validator.validate_definition({
            "name": "Bad",
            "slug": "bad",
            "steps": [{"action_key": "does_not_exist", "step_order": 1}],
            "triggers": [{"trigger_type": "user_request"}],
        })


def test_condition_engine():
    engine = ConditionEngine()
    state = {"payload": {"status": "done"}, "last_output": {"count": 3}}
    assert engine.evaluate({"field": "payload.status", "op": "eq", "value": "done"}, state)
    assert engine.evaluate({
        "all": [
            {"field": "last_output.count", "op": "gte", "value": 2},
            {"field": "payload.status", "op": "ne", "value": "todo"},
        ]
    }, state)
    assert not engine.evaluate({"field": "payload.status", "op": "eq", "value": "todo"}, state)


def test_retry_engine():
    engine = RetryEngine()
    assert engine.should_retry(attempt=1, retry_limit=2, on_failure="retry")
    assert not engine.should_retry(attempt=2, retry_limit=2, on_failure="retry")
    assert not engine.should_retry(attempt=1, retry_limit=2, on_failure="stop")
    assert engine.next_delay_seconds(1) == 5
    assert engine.next_delay_seconds(3) == 20


def test_action_registry_is_pluggable():
    registry = ActionRegistry()
    action = CreateNotificationAction()
    registry.register(action)
    assert registry.require("create_notification").display_name == "Create Notification"

    class PluginAction(CreateNotificationAction):
        action_key = "custom_plugin_action"
        display_name = "Custom"

    registry.register(PluginAction())
    assert registry.get("custom_plugin_action") is not None
