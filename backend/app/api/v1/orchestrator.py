"""Orchestrator API endpoints.

Endpoints:
- POST /orchestrate — main orchestration request
- GET /orchestrate/trace/{trace_id} — get execution trace
- GET /orchestrate/trace/{trace_id}/timeline — get execution timeline
- POST /orchestrate/approve/{request_id} — approve an action
- POST /orchestrate/reject/{request_id} — reject an action
- GET /orchestrate/approvals — list pending approvals
- GET /orchestrate/models — list available models
- POST /orchestrate/route — get model routing decision
- GET /orchestrate/usage — get AI usage summary
- GET /orchestrate/catalog — list agent catalog
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_current_user_id, get_db
from app.models.user import User
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.execution_tracer import execution_tracer
from app.orchestrator.approval_service import ApprovalService
from app.orchestrator.usage_service import AIUsageService
from app.orchestrator.model_router import model_router

router = APIRouter(prefix="/orchestrator", tags=["AI Orchestrator"])


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class OrchestratorRequest(BaseModel):
    message: str
    chat_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestratorResponse(BaseModel):
    success: bool
    output: str
    request_id: str
    trace_id: str | None = None
    agent_key: str | None = None
    plan: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    tokens_used: int = 0
    cost: float = 0.0
    duration_ms: int = 0
    error: str | None = None


class ModelRoutingRequest(BaseModel):
    task_type: str | None = None
    user_input: str = ""


class ApprovalDecisionRequest(BaseModel):
    reason: str = ""


class UsageSummaryResponse(BaseModel):
    period_days: int
    total_tokens: int
    total_cost: float
    request_count: int
    success_count: int
    success_rate: float
    by_provider: list[dict[str, Any]]
    by_model: list[dict[str, Any]]
    daily_trend: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Main Orchestration Endpoint
# ---------------------------------------------------------------------------

@router.post("/orchestrate", response_model=OrchestratorResponse)
async def orchestrate(
    body: OrchestratorRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Main orchestration endpoint — processes complex AI requests.

    The orchestrator will:
    1. Classify intent
    2. Create execution plan
    3. Route to optimal model
    4. Select and run agents
    5. Assemble context
    6. Execute with tools
    7. Return traced result
    """
    orch = Orchestrator(db)

    result = await orch.orchestrate(
        user_input=body.message,
        company_id=company_id,
        user_id=current_user.id,
        chat_id=body.chat_id,
        document_ids=body.document_ids,
        permissions=[],
        roles=[],
        metadata=body.metadata,
    )

    return OrchestratorResponse(**result.to_dict())


# ---------------------------------------------------------------------------
# Execution Tracing
# ---------------------------------------------------------------------------

@router.get("/orchestrate/trace/{trace_id}")
async def get_trace(
    trace_id: str,
    company_id: uuid.UUID = Depends(get_current_company_id),
):
    """Get full execution trace for an orchestration run."""
    trace = execution_tracer.get_trace_as_dict(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace topilmadi")
    if trace.get("company_id") != str(company_id):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")
    return trace


@router.get("/orchestrate/trace/{trace_id}/timeline")
async def get_trace_timeline(
    trace_id: str,
    company_id: uuid.UUID = Depends(get_current_company_id),
):
    """Get user-friendly execution timeline."""
    timeline = execution_tracer.get_timeline(trace_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Trace topilmadi")
    return {"trace_id": trace_id, "timeline": timeline}


@router.get("/orchestrate/traces")
async def list_traces(
    limit: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
):
    """List recent orchestration traces."""
    return execution_tracer.list_traces(company_id=company_id, limit=limit)


# ---------------------------------------------------------------------------
# Human Approval
# ---------------------------------------------------------------------------

@router.get("/orchestrate/approvals")
async def list_pending_approvals(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """List pending approval requests for the company."""
    svc = ApprovalService(db)
    pending = svc.list_pending(company_id)
    return {"items": [r.to_dict() for r in pending]}


@router.post("/orchestrate/approve/{request_id}")
async def approve_action(
    request_id: str,
    body: ApprovalDecisionRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending AI action."""
    svc = ApprovalService(db)
    req = svc.approve(request_id, current_user.id, body.reason)
    if not req:
        raise HTTPException(status_code=404, detail="Tasdiqlash so'rovi topilmadi yoki allaqachon hal qilinigan")
    return {"success": True, "message": "Amal tasdiqlandi", "request": req.to_dict()}


@router.post("/orchestrate/reject/{request_id}")
async def reject_action(
    request_id: str,
    body: ApprovalDecisionRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending AI action."""
    svc = ApprovalService(db)
    req = svc.reject(request_id, current_user.id, body.reason)
    if not req:
        raise HTTPException(status_code=404, detail="Tasdiqlash so'rovi topilmadi yoki allaqachon hal qilinigan")
    return {"success": True, "message": "Amal rad etildi", "request": req.to_dict()}


# ---------------------------------------------------------------------------
# Model Routing
# ---------------------------------------------------------------------------

@router.get("/orchestrate/models")
async def list_available_models(
    provider: str | None = Query(None),
):
    """List available AI models and their capabilities."""
    return {"models": model_router.list_models(provider=provider)}


@router.post("/orchestrate/route")
async def get_model_routing(
    body: ModelRoutingRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
):
    """Get model routing decision for a given task."""
    decision = model_router.route(
        task_type=body.task_type,
        user_input=body.user_input,
    )
    return {
        "provider": decision.provider,
        "model": decision.model,
        "temperature": decision.temperature,
        "max_tokens": decision.max_tokens,
        "reasoning": decision.reasoning,
        "alternatives": decision.alternatives,
    }


# ---------------------------------------------------------------------------
# AI Usage
# ---------------------------------------------------------------------------

@router.get("/orchestrate/usage")
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Get AI usage summary for the company."""
    svc = AIUsageService(db)
    return await svc.get_usage_summary(company_id, days=days)


# ---------------------------------------------------------------------------
# Agent Catalog
# ---------------------------------------------------------------------------

@router.get("/orchestrate/catalog")
async def get_agent_catalog(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """List available agents and their capabilities."""
    orch = Orchestrator(db)
    return {"agents": orch.get_catalog()}
