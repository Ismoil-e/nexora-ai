import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_db
from app.models.user import User
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowExecuteRequest,
    WorkflowTemplateInstallRequest,
    WorkflowUpdate,
)
from app.services.workflow_service import WorkflowService
from app.utils.exceptions import AppException

router = APIRouter(prefix="/workflows", tags=["Workflow Automation"])


def _http_from_app_exc(exc: Exception) -> HTTPException:
    status = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", str(exc))
    return HTTPException(status_code=status, detail=detail)


@router.get("/catalog")
async def workflow_catalog(db: AsyncSession = Depends(get_db)):
    service = WorkflowService(db)
    return service.catalog()


@router.post("/templates/install")
async def install_template(
    body: WorkflowTemplateInstallRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        workflow = await service.install_template(
            company_id=company_id,
            user_id=current_user.id,
            slug=body.slug,
            activate=body.activate,
        )
        return await service.get_workflow(workflow.id, company_id)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.post("")
async def create_workflow(
    body: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        workflow = await service.create_workflow(
            company_id=company_id,
            user_id=current_user.id,
            data=body.model_dump(),
        )
        return await service.get_workflow(workflow.id, company_id)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.get("")
async def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    return await service.list_workflows(company_id, page=page, page_size=page_size, status=status)


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        return await service.get_workflow(workflow_id, company_id)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowUpdate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        workflow = await service.update_workflow(workflow_id, company_id, body.model_dump(exclude_none=True))
        return await service.get_workflow(workflow.id, company_id)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    ok = await service.delete_workflow(workflow_id, company_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow topilmadi")
    return {"message": "Workflow o'chirildi"}


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        return await service.execute(
            company_id=company_id,
            user_id=current_user.id,
            workflow_id=workflow_id,
            payload=body.payload,
            trigger_type=body.trigger_type,
            async_mode=body.async_mode,
        )
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.post("/execute-by-slug")
async def execute_workflow_by_slug(
    body: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    if not body.workflow_slug:
        raise HTTPException(status_code=422, detail="workflow_slug talab qilinadi")
    service = WorkflowService(db)
    try:
        return await service.execute(
            company_id=company_id,
            user_id=current_user.id,
            workflow_slug=body.workflow_slug,
            payload=body.payload,
            trigger_type=body.trigger_type,
            async_mode=body.async_mode,
        )
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.post("/executions/{execution_id}/pause")
async def pause_execution(
    execution_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        return await service.pause(execution_id, company_id)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.post("/executions/{execution_id}/resume")
async def resume_execution(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        return await service.resume(execution_id, company_id, user_id=current_user.id)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.get("/{workflow_id}/history")
async def workflow_history(
    workflow_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        return await service.history(workflow_id, company_id, page=page, page_size=page_size)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.get("/executions/{execution_id}/status")
async def execution_status(
    execution_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        return await service.status(execution_id, company_id)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc


@router.get("/executions/{execution_id}/logs")
async def execution_logs(
    execution_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        return await service.logs(execution_id, company_id)
    except AppException as exc:
        raise _http_from_app_exc(exc) from exc
