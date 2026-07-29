import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_db
from app.models.user import User
from app.repositories.base import BaseRepository
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.utils.helpers import paginate

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse)
async def create_task(
    body: TaskCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(Task, db)
    task = await repo.create(
        company_id=company_id,
        created_by=current_user.id,
        assigned_to=body.assigned_to,
        title=body.title,
        description=body.description,
        priority=body.priority,
    )
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assigned_to=task.assigned_to,
        created_by=task.created_by,
        due_date=task.due_date.isoformat() if task.due_date else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        is_ai_generated=task.is_ai_generated,
        created_at=task.created_at.isoformat(),
    )


@router.get("")
async def list_tasks(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, func

    repo = BaseRepository(Task, db)
    filters = [Task.company_id == company_id, Task.deleted_at.is_(None)]
    if status:
        filters.append(Task.status == status)

    offset, limit = paginate(page, page_size)
    stmt = select(Task).where(*filters).offset(offset).limit(limit).order_by(Task.created_at.desc())
    result = await db.execute(stmt)
    tasks = list(result.scalars().all())

    count_stmt = select(func.count()).select_from(Task).where(*filters)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "assigned_to": t.assigned_to,
            "created_by": t.created_by,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "is_ai_generated": t.is_ai_generated,
            "created_at": t.created_at.isoformat(),
        } for t in tasks],
    }


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(Task, db)
    task = await repo.update(task_id, **body.model_dump(exclude_none=True))
    if not task:
        raise HTTPException(status_code=404, detail="Task topilmadi")
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assigned_to=task.assigned_to,
        created_by=task.created_by,
        due_date=task.due_date.isoformat() if task.due_date else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        is_ai_generated=task.is_ai_generated,
        created_at=task.created_at.isoformat(),
    )


@router.delete("/{task_id}")
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = BaseRepository(Task, db)
    result = await repo.soft_delete(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task topilmadi")
    return {"message": "Task o'chirildi"}
