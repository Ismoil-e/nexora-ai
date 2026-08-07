import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_db
from app.models.user import User
from app.schemas.agent import (
    AgentCreate,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentResponse,
    AgentUpdate,
    FrameworkAgentRunRequest,
    FrameworkAgentRunResponse,
)
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["AI Agents"])


def _to_agent_response(agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        ai_provider=agent.ai_provider,
        model=agent.model,
        is_active=agent.is_active,
        icon=agent.icon,
        color=agent.color,
        agent_key=getattr(agent, "agent_key", None),
        agent_type=getattr(agent, "agent_type", None),
        created_at=agent.created_at.isoformat(),
    )


@router.get("/framework/catalog")
async def framework_catalog(db: AsyncSession = Depends(get_db)):
    """List registered pluggable framework agents."""
    service = AgentService(db)
    return {"items": service.list_framework_catalog()}


@router.post("/framework/{agent_key}/run", response_model=FrameworkAgentRunResponse)
async def run_framework_agent(
    agent_key: str,
    body: FrameworkAgentRunRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Run a registered capability agent through the Cognitive pipeline."""
    service = AgentService(db)
    try:
        result = await service.run_framework_agent(
            agent_key=agent_key,
            user_id=current_user.id,
            company_id=company_id,
            input_text=body.input,
            chat_id=body.chat_id,
            document_ids=body.document_ids,
            metadata=body.metadata,
            async_mode=body.async_mode,
            provider=body.provider,
            model=body.model,
        )
    except HTTPException:
        raise
    except Exception as exc:
        status = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        raise HTTPException(status_code=status, detail=detail) from exc

    return FrameworkAgentRunResponse(
        success=bool(result.get("success")),
        output=result.get("output") or "",
        agent_key=result.get("agent_key") or agent_key,
        execution_id=result.get("execution_id"),
        status=result.get("status") or "completed",
        token_used=int(result.get("token_used") or 0),
        duration_ms=int(result.get("duration_ms") or 0),
        citations=result.get("citations") or [],
        memory_refs=result.get("memory_refs") or [],
        async_task_id=result.get("async_task_id"),
        error=result.get("error"),
        steps=result.get("steps") or [],
    )


@router.post("", response_model=AgentResponse)
async def create_agent(
    body: AgentCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = AgentService(db)
    agent = await service.create_agent(company_id, body.model_dump())
    return _to_agent_response(agent)


@router.get("")
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = AgentService(db)
    return await service.get_agents(company_id, page, page_size)


@router.post("/{agent_id}/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    agent_id: uuid.UUID,
    body: AgentExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentService(db)
    result = await service.execute_agent(agent_id, current_user.id, body.input)
    if not result:
        raise HTTPException(status_code=404, detail="Agent topilmadi yoki faol emas")
    return result


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    db: AsyncSession = Depends(get_db),
):
    from app.repositories.agent_repo import AgentRepository

    repo = AgentRepository(db)
    agent = await repo.update(agent_id, **body.model_dump(exclude_none=True))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent topilmadi")
    return _to_agent_response(agent)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.repositories.agent_repo import AgentRepository

    repo = AgentRepository(db)
    result = await repo.soft_delete(agent_id)
    if not result:
        raise HTTPException(status_code=404, detail="Agent topilmadi")
    return {"message": "Agent o'chirildi"}
