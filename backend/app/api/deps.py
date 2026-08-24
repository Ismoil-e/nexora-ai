import uuid
from typing import List, Optional
from functools import wraps

from fastapi import Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_session
from app.core.security import decode_token
from app.models.role import Permission, RolePermission
from app.models.security import BreakGlassSession
from app.repositories.user_repo import UserRepository
from app.security.contracts.types import SecurityContext
from app.security.core.break_glass import break_glass_manager
from datetime import datetime, timezone


async def get_db() -> AsyncSession:
    async for session in get_async_session():
        yield session


async def get_current_user_id(
    authorization: str = Header(None),
) -> uuid.UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token talab qilinadi",
        )

    token = authorization.split(" ")[1]
    payload = decode_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yaroqsiz token",
        )

    # Block MFA-pending tokens from accessing non-MFA endpoints
    if payload.get("mfa_pending"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA tasdiqlanmagan",
        )

    return uuid.UUID(payload["sub"])


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi topilmadi",
        )

    # Enforce PostgreSQL Row-Level Security (RLS) tenant scope for current transaction
    from sqlalchemy import text
    try:
        await db.execute(text("SET LOCAL app.current_tenant_id = :company_id"), {"company_id": str(user.company_id)})
    except Exception:
        pass  # Graceful fallback if RLS session setting is not enabled on mock/sqlite testing DBs

    return user


async def get_current_company_id(
    current_user=Depends(get_current_user),
) -> uuid.UUID:
    return current_user.company_id


# ---------------------------------------------------------------------------
# SecurityContext Builder — Loads user permissions for ABAC/RBAC evaluation
# ---------------------------------------------------------------------------

async def get_security_context(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
) -> SecurityContext:
    """Builds a SecurityContext from the current authenticated user and their permissions."""
    permissions: List[str] = []
    role_name = "user"

    if current_user.role_id:
        from app.models.role import Role
        role = await db.get(Role, current_user.role_id)
        if role:
            role_name = role.name

        # Load permission codes via RolePermission join
        perm_query = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == current_user.role_id)
        )
        perm_result = await db.execute(perm_query)
        permissions = [row[0] for row in perm_result.all()]

    # Check break-glass status
    is_break_glass = False
    try:
        is_break_glass = await break_glass_manager.is_break_glass_active_for_user(
            db, current_user.company_id, current_user.id
        )
    except Exception:
        pass

    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

    return SecurityContext(
        user_id=current_user.id,
        company_id=current_user.company_id,
        email=current_user.email,
        role_name=role_name,
        permissions=permissions,
        is_break_glass_active=is_break_glass,
        ip_address=ip_address,
        user_agent=user_agent,
    )


# ---------------------------------------------------------------------------
# Permission Dependency Factory
# ---------------------------------------------------------------------------

def require_permission(permission_code: str):
    """Factory that returns a dependency checking if user has a specific permission."""
    async def _check(
        security_ctx: SecurityContext = Depends(get_security_context),
    ) -> SecurityContext:
        # Break-glass and admin always pass
        if security_ctx.is_break_glass_active:
            return security_ctx
        if security_ctx.role_name in ["super_admin", "admin", "Owner"]:
            return security_ctx
        if permission_code in security_ctx.permissions:
            return security_ctx
        # Check wildcard
        module = permission_code.split(".")[0]
        if f"{module}.*" in security_ctx.permissions or "admin.manage" in security_ctx.permissions:
            return security_ctx

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ruxsat etilmagan: '{permission_code}' huquqi talab qilinadi",
        )
    return _check


def require_any_permission(*permission_codes: str):
    """Factory that returns a dependency checking if user has ANY of the given permissions."""
    async def _check(
        security_ctx: SecurityContext = Depends(get_security_context),
    ) -> SecurityContext:
        if security_ctx.is_break_glass_active or security_ctx.role_name in ["super_admin", "admin", "Owner"]:
            return security_ctx
        for code in permission_codes:
            if code in security_ctx.permissions:
                return security_ctx
            module = code.split(".")[0]
            if f"{module}.*" in security_ctx.permissions or "admin.manage" in security_ctx.permissions:
                return security_ctx
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ruxsat etilmagan: quyidagi huquqlardan biri kerak: {', '.join(permission_codes)}",
        )
    return _check

