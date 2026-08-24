from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# MFA Schemas
# ---------------------------------------------------------------------------

class MFAEnrollResponse(BaseModel):
    secret: str
    provisioning_uri: str
    recovery_codes: List[str]


class MFAVerifyRequest(BaseModel):
    code: str  # 6-digit TOTP or recovery code


class MFAVerifyResponse(BaseModel):
    success: bool
    message: str
    is_mfa_enabled: bool


class MFADisableRequest(BaseModel):
    code: str
    password: str


# ---------------------------------------------------------------------------
# Session & Password Schemas
# ---------------------------------------------------------------------------

class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    last_used_at: Optional[datetime] = None
    expires_at: datetime
    is_revoked: bool
    created_at: datetime


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


# ---------------------------------------------------------------------------
# Break-Glass Schemas
# ---------------------------------------------------------------------------

class BreakGlassActivateRequest(BaseModel):
    reason: str
    duration_minutes: int = 60
    elevated_role: str = "super_admin"


class BreakGlassSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    reason: str
    elevated_role: str
    is_active: bool
    duration_minutes: int
    expires_at: datetime
    created_at: datetime


# ---------------------------------------------------------------------------
# Security Event & Audit Schemas
# ---------------------------------------------------------------------------

class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    severity: str
    title: str
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_resolved: bool
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str
    created_at: datetime


class AuditSearchRequest(BaseModel):
    action: Optional[str] = None
    resource_type: Optional[str] = None
    user_id: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 50


class SecurityDashboardResponse(BaseModel):
    company_id: UUID
    generated_at: datetime
    security_posture_score: int
    active_sessions_count: int
    failed_logins_24h: int
    critical_events_count: int
    mfa_enabled_users_count: int
    active_break_glass_count: int
    recent_events: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Policy & Governance Schemas
# ---------------------------------------------------------------------------

class SecurityPolicyCreate(BaseModel):
    name: str
    policy_type: str
    rule_definition: str  # JSON
    is_active: bool = True
    priority: int = 10


class SecurityPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    policy_type: str
    rule_definition: str
    is_active: bool
    priority: int
    created_at: datetime


class RetentionPolicyCreate(BaseModel):
    resource_type: str  # documents, chats, audit_logs, reports
    retention_days: int = 365
    action_type: str = "delete"
    is_active: bool = True


class RetentionPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource_type: str
    retention_days: int
    action_type: str
    is_active: bool
    last_executed_at: Optional[datetime] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# RBAC Schemas
# ---------------------------------------------------------------------------

class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    module: str


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permission_ids: Optional[List[UUID]] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[UUID]] = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    is_system: bool
    created_at: datetime
    permissions: List[PermissionResponse] = []
