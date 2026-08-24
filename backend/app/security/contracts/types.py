import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SecuritySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SensitivityLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class PolicyEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class SecurityEventType(str, Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    ACCOUNT_LOCKOUT = "ACCOUNT_LOCKOUT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    MFA_ENROLLED = "MFA_ENROLLED"
    MFA_VERIFIED = "MFA_VERIFIED"
    MFA_DISABLED = "MFA_DISABLED"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    SUSPICIOUS_TOKEN_REPLAY = "SUSPICIOUS_TOKEN_REPLAY"
    UNAUTHORIZED_ACCESS_ATTEMPT = "UNAUTHORIZED_ACCESS_ATTEMPT"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    TOOL_UNAUTHORIZED = "TOOL_UNAUTHORIZED"
    BREAK_GLASS_ACTIVATED = "BREAK_GLASS_ACTIVATED"
    BREAK_GLASS_EXPIRED = "BREAK_GLASS_EXPIRED"
    DATA_RETENTION_PURGED = "DATA_RETENTION_PURGED"


@dataclass
class SecurityContext:
    user_id: uuid.UUID
    company_id: uuid.UUID
    email: str
    role_name: str
    permissions: List[str] = field(default_factory=list)
    department_id: Optional[str] = None
    project_ids: List[str] = field(default_factory=list)
    is_mfa_authenticated: bool = False
    is_break_glass_active: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class MFAEnrollmentResult:
    secret: str
    provisioning_uri: str
    recovery_codes: List[str]


@dataclass
class PolicyEvaluationResult:
    effect: PolicyEffect
    reason: str
    matched_policy: Optional[str] = None


@dataclass
class AIUsageMetrics:
    company_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    estimated_cost_usd: float
    execution_duration_ms: int
    sensitivity_level: str = SensitivityLevel.INTERNAL.value
    agent_id: Optional[str] = None
    workflow_id: Optional[uuid.UUID] = None
