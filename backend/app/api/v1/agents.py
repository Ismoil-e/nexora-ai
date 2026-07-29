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
)
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["AI Agents"])


@router.post("", response_model=AgentResponse)
async def create_agent(
    body: AgentCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = AgentService(db)
    agent = await service.create_agent(company_id, body.model_dump())
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        ai_provider=agent.ai_provider,
        model=agent.model,
        is_active=agent.is_active,
        icon=agent.icon,
        color=agent.color,
        created_at=agent.created_at.isoformat(),
    )


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
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        ai_provider=agent.ai_provider,
        model=agent.model,
        is_active=agent.is_active,
        icon=agent.icon,
        color=agent.color,
        created_at=agent.created_at.isoformat(),
    )


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
