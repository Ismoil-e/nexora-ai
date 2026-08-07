"""Condition, approval, and retry helpers for workflows."""

from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Any

from app.workflows.contracts.types import ActionResult


OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "in": lambda a, b: a in b,
    "contains": lambda a, b: b in a if a is not None else False,
    "exists": lambda a, _b: a is not None,
    "truthy": lambda a, _b: bool(a),
}


class ConditionEngine:
    """Evaluates simple JSON conditions against shared workflow state."""

    def evaluate(self, condition: dict[str, Any] | None, state: dict[str, Any]) -> bool:
        if not condition:
            return True

        if "all" in condition:
            return all(self.evaluate(c, state) for c in condition["all"])
        if "any" in condition:
            return any(self.evaluate(c, state) for c in condition["any"])
        if "not" in condition:
            return not self.evaluate(condition["not"], state)

        field = condition.get("field")
        op_name = condition.get("op", "eq")
        expected = condition.get("value")
        actual = self._resolve(field, state)
        op = OPS.get(op_name)
        if not op:
            return False
        try:
            return bool(op(actual, expected))
        except Exception:
            return False

    def _resolve(self, field: str | None, state: dict[str, Any]) -> Any:
        if not field:
            return None
        cur: Any = state
        for part in field.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur


class ApprovalEngine:
    """Creates and resolves approval gates."""

    def needs_approval(self, requires_approval: bool, action_result: ActionResult | None = None) -> bool:
        if action_result and action_result.requires_approval:
            return True
        return bool(requires_approval)

    def approval_payload(
        self,
        *,
        requested_from: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "pending",
            "requested_from": requested_from,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


class RetryEngine:
    """Decides retry behavior for failed steps."""

    def should_retry(self, *, attempt: int, retry_limit: int, on_failure: str) -> bool:
        if on_failure != "retry":
            return False
        return attempt < max(retry_limit, 0)

    def next_delay_seconds(self, attempt: int, base: int = 5) -> int:
        return min(base * (2 ** max(attempt - 1, 0)), 300)
