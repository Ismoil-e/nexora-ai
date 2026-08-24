import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_company_id, get_current_user, get_current_user_id, get_db, require_permission
from app.models.user import User
from app.schemas.security import (
    AuditLogResponse,
    AuditSearchRequest,
    BreakGlassActivateRequest,
    BreakGlassSessionResponse,
    MFADisableRequest,
    MFAEnrollResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    PasswordChangeRequest,
    RetentionPolicyCreate,
    RetentionPolicyResponse,
    SecurityDashboardResponse,
    SecurityEventResponse,
    SecurityPolicyCreate,
    SecurityPolicyResponse,
    SessionResponse,
)
from app.security.contracts.types import SecurityContext
from app.services.security_service import EnterpriseSecurityService

router = APIRouter(prefix="/security", tags=["Enterprise Security & Governance"])


# ---------------------------------------------------------------------------
# MFA Endpoints
# ---------------------------------------------------------------------------

@router.post("/mfa/enroll", response_model=MFAEnrollResponse)
async def enroll_mfa(
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Initiates TOTP MFA enrollment and generates recovery backup codes."""
    svc = EnterpriseSecurityService(db)
    return await svc.enroll_mfa(
        user_id=current_user.id,
        company_id=company_id,
        email=current_user.email,
        company_name=current_user.company.name if current_user.company else "Nexora AI",
    )


@router.post("/mfa/verify", response_model=MFAVerifyResponse)
async def verify_mfa(
    body: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Verifies TOTP or recovery code to enable Multi-Factor Authentication."""
    svc = EnterpriseSecurityService(db)
    return await svc.verify_and_enable_mfa(
        user_id=current_user.id, company_id=company_id, code=body.code
    )


@router.post("/mfa/disable")
async def disable_mfa(
    body: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Disables MFA after validating current password and verification code."""
    svc = EnterpriseSecurityService(db)
    success = await svc.disable_mfa(
        user_id=current_user.id,
        company_id=company_id,
        code=body.code,
        password=body.password,
    )
    return {"success": success, "message": "MFA muvaffaqiyatli o'chirildi"}


# ---------------------------------------------------------------------------
# Session & Password Management
# ---------------------------------------------------------------------------

@router.get("/sessions", response_model=List[SessionResponse])
async def list_active_sessions(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists all active login sessions and devices for the current user."""
    svc = EnterpriseSecurityService(db)
    return await svc.list_active_sessions(user_id)


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Revokes a specific session."""
    svc = EnterpriseSecurityService(db)
    success = await svc.revoke_session(user_id, session_id)
    return {"success": success, "message": "Sessiya bekor qilindi"}


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    user_id: uuid.UUID = Depends(get_current_user_id),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Logs out user from all active devices and revokes all refresh tokens."""
    svc = EnterpriseSecurityService(db)
    count = await svc.revoke_all_sessions(user_id, company_id)
    return {"success": True, "revoked_sessions_count": count}


@router.post("/password/change")
async def change_password(
    body: PasswordChangeRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Updates user password and invalidates all existing sessions."""
    svc = EnterpriseSecurityService(db)
    success = await svc.change_password(user_id, company_id, body)
    return {"success": success, "message": "Parol muvaffaqiyatli yangilandi"}


# ---------------------------------------------------------------------------
# Break-Glass Emergency Access
# ---------------------------------------------------------------------------

@router.post("/break-glass/activate", response_model=BreakGlassSessionResponse)
async def activate_break_glass(
    body: BreakGlassActivateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Activates an emergency break-glass elevated access session with mandatory auditing."""
    svc = EnterpriseSecurityService(db)
    return await svc.activate_break_glass(
        company_id=company_id,
        user_id=user_id,
        reason=body.reason,
        duration_minutes=body.duration_minutes,
        elevated_role=body.elevated_role,
    )


# ---------------------------------------------------------------------------
# Security Dashboard & Events
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=SecurityDashboardResponse)
async def get_security_dashboard(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Admin Security Dashboard summarizing posture score, sessions, alerts, and failed logins."""
    svc = EnterpriseSecurityService(db)
    return await svc.get_security_dashboard(company_id)


@router.get("/events", response_model=List[SecurityEventResponse])
async def get_security_events(
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists categorized security events for the tenant."""
    svc = EnterpriseSecurityService(db)
    return await svc.get_security_events(
        company_id=company_id, severity=severity, event_type=event_type, limit=limit
    )


# ---------------------------------------------------------------------------
# Audit Search
# ---------------------------------------------------------------------------

@router.post("/audit/search", response_model=List[AuditLogResponse])
async def search_audit_logs(
    body: AuditSearchRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("security.manage")),
):
    """Searches immutable tenant audit logs with filtering and date ranges."""
    svc = EnterpriseSecurityService(db)
    return await svc.search_audit_logs(company_id, body)


# ---------------------------------------------------------------------------
# Security Policies (ABAC) Management
# ---------------------------------------------------------------------------

@router.get("/policies", response_model=List[SecurityPolicyResponse])
async def list_security_policies(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("security.manage")),
):
    """Lists all active security policies for the tenant."""
    svc = EnterpriseSecurityService(db)
    return await svc.list_security_policies(company_id)


@router.post("/policies", response_model=SecurityPolicyResponse, status_code=201)
async def create_security_policy(
    body: SecurityPolicyCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("security.manage")),
):
    """Creates a new ABAC security policy."""
    svc = EnterpriseSecurityService(db)
    return await svc.create_security_policy(company_id, user_id, body)


@router.delete("/policies/{policy_id}")
async def delete_security_policy(
    policy_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("security.manage")),
):
    """Deactivates a security policy."""
    svc = EnterpriseSecurityService(db)
    success = await svc.delete_security_policy(company_id, policy_id)
    return {"success": success, "message": "Siyosat o'chirildi"}


# ---------------------------------------------------------------------------
# Data Retention Policies
# ---------------------------------------------------------------------------

@router.get("/retention", response_model=List[RetentionPolicyResponse])
async def list_retention_policies(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("security.manage")),
):
    """Lists all data retention policies for the tenant."""
    svc = EnterpriseSecurityService(db)
    return await svc.list_retention_policies(company_id)


@router.post("/retention", response_model=RetentionPolicyResponse, status_code=201)
async def create_retention_policy(
    body: RetentionPolicyCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("security.manage")),
):
    """Creates a new data retention policy."""
    svc = EnterpriseSecurityService(db)
    return await svc.create_retention_policy(company_id, body)


@router.post("/retention/execute")
async def execute_retention_policy(
    resource_type: str,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("security.manage")),
):
    """Manually executes a retention policy for a resource type."""
    from app.security.core.retention_engine import retention_engine
    result = await retention_engine.execute_retention_policy(db, company_id, resource_type)
    return result


# ---------------------------------------------------------------------------
# Data Export & Deletion (GDPR)
# ---------------------------------------------------------------------------

class DataExportRequest(BaseModel):
    user_id: uuid.UUID | None = None  # Export specific user data or self


class AccountDeletionRequest(BaseModel):
    password: str
    confirmation: str  # Must be "DELETE_MY_ACCOUNT"


@router.post("/data/export")
async def export_user_data(
    body: DataExportRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _ctx: SecurityContext = Depends(require_permission("security.manage")),
):
    """Exports user data for GDPR compliance."""
    from app.security.core.retention_engine import retention_engine
    target_user_id = body.user_id or current_user.id
    data = await retention_engine.export_user_data(db, company_id, target_user_id)
    return data


@router.post("/data/delete-account")
async def request_account_deletion(
    body: AccountDeletionRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Requests account deletion with password confirmation."""
    from app.core.security import verify_password
    from app.security.core.audit_logger import audit_logger
    from datetime import datetime, timezone

    if body.confirmation != "DELETE_MY_ACCOUNT":
        return {"success": False, "error": "Tasdiqlash matni noto'g'ri"}

    if not current_user.password_hash or not verify_password(body.password, current_user.password_hash):
        return {"success": False, "error": "Parol noto'g'ri"}

    # Soft-delete: deactivate user
    current_user.is_active = False
    await db.flush()

    # Revoke all sessions
    from app.security.core.session_manager import session_manager
    await session_manager.revoke_all_sessions(db, current_user.id, company_id=company_id,
                                               reason="Account deletion requested")

    await audit_logger.log_event(
        db, action="security.account_deletion_requested", resource_type="User",
        company_id=company_id, user_id=current_user.id,
        details={"status": "deactivated"}, severity="HIGH",
    )

    return {"success": True, "message": "Akkaunt o'chirish so'rovi qabul qilindi"}


# ---------------------------------------------------------------------------
# Document Classifications
# ---------------------------------------------------------------------------

@router.get("/document-classifications")
async def get_document_classifications():
    """Returns available document sensitivity levels and access levels."""
    from app.security.core.document_permissions import document_permissions
    return document_permissions.get_document_classifications()
