import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_db, require_permission
from app.schemas.security import PermissionResponse, RoleCreate, RoleResponse, RoleUpdate
from app.security.contracts.types import SecurityContext
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["RBAC Roles & Permissions"])


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_current_company_id),
    _ctx: SecurityContext = Depends(require_permission("admin.manage")),
):
    """List all roles for the tenant. Requires admin.manage permission."""
    svc = RoleService(db)
    roles = await svc.list_roles(company_id)
    return roles


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    body: RoleCreate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_current_company_id),
    _ctx: SecurityContext = Depends(require_permission("admin.manage")),
):
    """Create a new role with optional permissions."""
    svc = RoleService(db)
    role = await svc.create_role(company_id, body)
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_current_company_id),
    _ctx: SecurityContext = Depends(require_permission("admin.manage")),
):
    """Update a role."""
    svc = RoleService(db)
    role = await svc.update_role(company_id, role_id, body)
    return role


@router.delete("/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_current_company_id),
    _ctx: SecurityContext = Depends(require_permission("admin.manage")),
):
    """Soft-delete a role (cannot delete system roles)."""
    svc = RoleService(db)
    success = await svc.delete_role(company_id, role_id)
    return {"success": success, "message": "Rol o'chirildi"}


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("admin.manage")),
):
    """List all available permission codes."""
    svc = RoleService(db)
    perms = await svc.list_permissions()
    return perms
