"""Approval Service — manages human approval for sensitive AI agent actions.

Flow:
1. Agent requests action
2. Policy evaluation → approval required
3. User/Admin approves/rejects
4. Tool executes (or is cancelled)
5. Audit event created
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Actions that require human approval
_APPROVAL_REQUIRED_ACTIONS: dict[str, dict[str, Any]] = {
    "delete_document": {"risk": RiskLevel.HIGH, "reason": "Hujjatni o'chirish"},
    "delete_data": {"risk": RiskLevel.CRITICAL, "reason": "Ma'lumotlarni o'chirish"},
    "send_email": {"risk": RiskLevel.MEDIUM, "reason": "Tashqi elektron pochta yuborish"},
    "send_telegram": {"risk": RiskLevel.MEDIUM, "reason": "Telegram xabar yuborish"},
    "send_notification": {"risk": RiskLevel.LOW, "reason": "Bildirishnoma yuborish"},
    "modify_workflow": {"risk": RiskLevel.HIGH, "reason": "Workflow konfiguratsiyasini o'zgartirish"},
    "export_sensitive": {"risk": RiskLevel.HIGH, "reason": "Hassas ma'lumotlarni eksport qilish"},
    "change_settings": {"risk": RiskLevel.MEDIUM, "reason": "Tizim sozlamalarini o'zgartirish"},
    "execute_connector": {"risk": RiskLevel.MEDIUM, "reason": "Tashqi tizimga so'rov yuborish"},
    "run_workflow": {"risk": RiskLevel.MEDIUM, "reason": "Workflow ishga tushirish"},
    "create_task": {"risk": RiskLevel.LOW, "reason": "Vazifa yaratish"},
    "query_database": {"risk": RiskLevel.HIGH, "reason": "Ma'lumotlar bazasiga so'rov"},
}


class ApprovalRequest:
    """In-memory approval request object."""

    def __init__(
        self,
        *,
        id: str | None = None,
        company_id: uuid.UUID,
        requested_by: uuid.UUID,
        agent_key: str,
        action: str,
        description: str,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout_minutes: int = 60,
    ):
        self.id = id or str(uuid.uuid4())
        self.company_id = company_id
        self.requested_by = requested_by
        self.agent_key = agent_key
        self.action = action
        self.description = description
        self.risk_level = risk_level
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.metadata = metadata or {}
        self.status = ApprovalStatus.PENDING
        self.decided_by: uuid.UUID | None = None
        self.decision_reason: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.decided_at: datetime.now(timezone.utc) | None = None
        self.timeout_minutes = timeout_minutes

    def approve(self, user_id: uuid.UUID, reason: str = "") -> None:
        self.status = ApprovalStatus.APPROVED
        self.decided_by = user_id
        self.decision_reason = reason
        self.decided_at = datetime.now(timezone.utc)

    def reject(self, user_id: uuid.UUID, reason: str = "") -> None:
        self.status = ApprovalStatus.REJECTED
        self.decided_by = user_id
        self.decision_reason = reason
        self.decided_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": str(self.company_id),
            "requested_by": str(self.requested_by),
            "agent_key": self.agent_key,
            "action": self.action,
            "description": self.description,
            "risk_level": self.risk_level.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "status": self.status.value,
            "decided_by": str(self.decided_by) if self.decided_by else None,
            "decision_reason": self.decision_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "timeout_minutes": self.timeout_minutes,
            "metadata": self.metadata,
        }


class ApprovalService:
    """Manages approval requests for sensitive AI actions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # In-memory store for pending approvals (production: use Redis or DB)
        self._pending: dict[str, ApprovalRequest] = {}
        self._all: dict[str, ApprovalRequest] = {}

    def requires_approval(self, action: str) -> bool:
        """Check if an action requires human approval."""
        return action in _APPROVAL_REQUIRED_ACTIONS

    def get_risk_level(self, action: str) -> RiskLevel:
        """Get the risk level for an action."""
        config = _APPROVAL_REQUIRED_ACTIONS.get(action, {})
        return config.get("risk", RiskLevel.MEDIUM)

    def create_request(
        self,
        *,
        company_id: uuid.UUID,
        requested_by: uuid.UUID,
        agent_key: str,
        action: str,
        description: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout_minutes: int = 60,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        risk = self.get_risk_level(action)
        req = ApprovalRequest(
            company_id=company_id,
            requested_by=requested_by,
            agent_key=agent_key,
            action=action,
            description=description,
            risk_level=risk,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
            timeout_minutes=timeout_minutes,
        )
        self._pending[req.id] = req
        self._all[req.id] = req
        return req

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID."""
        return self._all.get(request_id)

    def list_pending(
        self,
        company_id: uuid.UUID,
        agent_key: str | None = None,
    ) -> list[ApprovalRequest]:
        """List pending approval requests for a company."""
        results = []
        for req in self._pending.values():
            if req.company_id == company_id and req.status == ApprovalStatus.PENDING:
                if agent_key is None or req.agent_key == agent_key:
                    # Check timeout
                    if req.created_at:
                        elapsed = (datetime.now(timezone.utc) - req.created_at).total_seconds() / 60
                        if elapsed > req.timeout_minutes:
                            req.status = ApprovalStatus.EXPIRED
                            self._pending.pop(req.id, None)
                            continue
                    results.append(req)
        return sorted(results, key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc))

    def approve(
        self,
        request_id: str,
        user_id: uuid.UUID,
        reason: str = "",
    ) -> ApprovalRequest | None:
        """Approve a pending request."""
        req = self._pending.get(request_id)
        if not req or req.status != ApprovalStatus.PENDING:
            return None
        req.approve(user_id, reason)
        self._pending.pop(request_id, None)
        return req

    def reject(
        self,
        request_id: str,
        user_id: uuid.UUID,
        reason: str = "",
    ) -> ApprovalRequest | None:
        """Reject a pending request."""
        req = self._pending.get(request_id)
        if not req or req.status != ApprovalStatus.PENDING:
            return None
        req.reject(user_id, reason)
        self._pending.pop(request_id, None)
        return req

    def get_all_requests(
        self,
        company_id: uuid.UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get all approval requests for a company."""
        results = [
            req.to_dict() for req in self._all.values()
            if req.company_id == company_id
        ]
        return sorted(results, key=lambda r: r.get("created_at", ""), reverse=True)[:limit]
