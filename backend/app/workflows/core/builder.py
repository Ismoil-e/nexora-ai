"""Workflow builder and validator."""

from __future__ import annotations

import json
from typing import Any

from app.workflows.core.registry import action_registry, trigger_registry
from app.utils.exceptions import ValidationException


class WorkflowBuilder:
    """Builds normalized workflow definitions from API / AI / templates."""

    def build(
        self,
        *,
        name: str,
        slug: str,
        workflow_type: str = "manual",
        description: str | None = None,
        steps: list[dict[str, Any]] | None = None,
        triggers: list[dict[str, Any]] | None = None,
        requires_approval: bool = False,
        max_retries: int = 3,
        timeout_seconds: int = 3600,
        tags: list[str] | None = None,
        definition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_steps = []
        for idx, step in enumerate(steps or [], start=1):
            normalized_steps.append({
                "name": step.get("name") or f"Step {idx}",
                "step_order": int(step.get("step_order") or idx),
                "action_key": step["action_key"],
                "config": step.get("config") or {},
                "condition": step.get("condition"),
                "on_failure": step.get("on_failure") or "stop",
                "retry_limit": int(step.get("retry_limit") or 0),
                "is_optional": bool(step.get("is_optional") or False),
                "timeout_seconds": step.get("timeout_seconds"),
            })

        normalized_triggers = []
        for trigger in triggers or [{"trigger_type": "user_request"}]:
            normalized_triggers.append({
                "trigger_type": trigger["trigger_type"],
                "config": trigger.get("config") or {},
                "is_active": trigger.get("is_active", True),
            })

        built = {
            "name": name,
            "slug": slug,
            "description": description,
            "workflow_type": workflow_type,
            "requires_approval": requires_approval,
            "max_retries": max_retries,
            "timeout_seconds": timeout_seconds,
            "tags": tags or [],
            "steps": sorted(normalized_steps, key=lambda s: s["step_order"]),
            "triggers": normalized_triggers,
            "definition": definition or {},
        }
        return built

    def from_template(self, template: dict[str, Any]) -> dict[str, Any]:
        return self.build(
            name=template["name"],
            slug=template["slug"],
            workflow_type=template.get("workflow_type", "manual"),
            description=template.get("description"),
            steps=template.get("steps"),
            triggers=template.get("triggers"),
            requires_approval=bool(template.get("requires_approval")),
            max_retries=int(template.get("max_retries") or 3),
            timeout_seconds=int(template.get("timeout_seconds") or 3600),
            tags=template.get("tags"),
            definition=template.get("definition"),
        )

    @staticmethod
    def dumps(definition: dict[str, Any]) -> str:
        return json.dumps(definition, ensure_ascii=False)


class WorkflowValidator:
    """Validates workflow definitions before persistence or execution."""

    def validate_definition(self, definition: dict[str, Any]) -> None:
        if not definition.get("name"):
            raise ValidationException(detail="Workflow name talab qilinadi")
        if not definition.get("slug"):
            raise ValidationException(detail="Workflow slug talab qilinadi")
        steps = definition.get("steps") or []
        if not steps:
            raise ValidationException(detail="Kamida bitta workflow step kerak")

        seen_orders: set[int] = set()
        for step in steps:
            action_key = step.get("action_key")
            if not action_key:
                raise ValidationException(detail="Har bir stepda action_key bo'lishi shart")
            if action_registry.get(action_key) is None:
                raise ValidationException(detail=f"Noma'lum action: {action_key}")
            order = int(step.get("step_order") or 0)
            if order in seen_orders:
                raise ValidationException(detail=f"Takroriy step_order: {order}")
            seen_orders.add(order)
            on_failure = step.get("on_failure") or "stop"
            if on_failure not in {"stop", "continue", "retry"}:
                raise ValidationException(detail=f"Noto'g'ri on_failure: {on_failure}")

        for trigger in definition.get("triggers") or []:
            ttype = trigger.get("trigger_type")
            if not ttype:
                raise ValidationException(detail="trigger_type talab qilinadi")
            if not trigger_registry.has(ttype):
                raise ValidationException(detail=f"Noma'lum trigger turi: {ttype}")

    def validate_for_execution(self, workflow_status: str, steps_count: int) -> None:
        if workflow_status == "archived":
            raise ValidationException(detail="Archived workflow bajarilmaydi")
        if workflow_status == "draft":
            raise ValidationException(detail="Draft workflow avval active qilinishi kerak")
        if steps_count <= 0:
            raise ValidationException(detail="Workflowda step yo'q")
