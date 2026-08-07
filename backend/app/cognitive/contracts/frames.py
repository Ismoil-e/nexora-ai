"""Cognitive Core lightweight contracts used by the Agent Framework."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextFrame:
    """Minimal context frame assembled before agent reasoning."""

    company_id: uuid.UUID
    user_id: uuid.UUID
    permissions: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    department_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    active_document_ids: list[uuid.UUID] = field(default_factory=list)
    locale: str = "uz"
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidencePack:
    """Unified evidence handed to agents / reasoning."""

    query: str
    memory_items: list[dict[str, Any]] = field(default_factory=list)
    graph_summary: dict[str, Any] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
