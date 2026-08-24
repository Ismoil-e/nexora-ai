import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.audit import AuditLog
from app.models.security import (
    BreakGlassSession,
    DataRetentionPolicy,
    MFAConfiguration,
    MFARecoveryCode,
    SecurityEvent,
    SecurityPolicy,
)
from app.models.session import RefreshToken
from app.models.user import User
from app.repositories.security_repo import SecurityRepository
from app.repositories.user_repo import UserRepository
from app.schemas.security import (
    AuditSearchRequest,
    MFAEnrollResponse,
    MFAVerifyResponse,
    PasswordChangeRequest,
    RetentionPolicyCreate,
    SecurityPolicyCreate,
)
from app.security.core.audit_logger import audit_logger
from app.security.contracts.types import SecurityEventType, SecuritySeverity
from app.security.core.audit_logger import audit_logger
from app.security.core.break_glass import break_glass_manager
from app.security.core.mfa_manager import mfa_manager
from app.security.core.retention_engine import retention_engine
from app.security.core.security_monitor import security_monitor
from app.security.core.session_manager import session_manager
from app.utils.exceptions import NotFoundException, UnauthorizedException, ValidationException


class EnterpriseSecurityService:
    """Central service managing Enterprise Security, MFA, Sessions, Audit Search, and Governance."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sec_repo = SecurityRepository(db)
        self.user_repo = UserRepository(db)

    # ---------------------------------------------------------------------------
    # MFA Operations
    # ---------------------------------------------------------------------------

    async def enroll_mfa(
        self, user_id: uuid.UUID, company_id: uuid.UUID, email: str, company_name: str = "Nexora AI"
    ) -> MFAEnrollResponse:
        """Initiates TOTP MFA enrollment and stores hashed recovery codes."""
        enrollment = mfa_manager.enroll(email=email, company_name=company_name)

        hashed_codes = [mfa_manager.hash_recovery_code(c) for c in enrollment.recovery_codes]
        await self.sec_repo.save_mfa_config(
            user_id=user_id,
            company_id=company_id,
            secret_key=enrollment.secret,
            recovery_code_hashes=hashed_codes,
        )

        return MFAEnrollResponse(
            secret=enrollment.secret,
            provisioning_uri=enrollment.provisioning_uri,
            recovery_codes=enrollment.recovery_codes,
        )

    async def verify_and_enable_mfa(
        self, user_id: uuid.UUID, company_id: uuid.UUID, code: str
    ) -> MFAVerifyResponse:
        """Verifies initial 6-digit TOTP code and marks MFA enabled."""
        config = await self.sec_repo.get_mfa_config(user_id)
        if not config or not config.secret_key:
            raise ValidationException("MFA sozlamalari topilmadi. Avval ro'yxatdan o'ting.")

        is_valid = mfa_manager.verify_totp(config.secret_key, code)
        if not is_valid:
            # Check if recovery code matches
            code_hash = mfa_manager.hash_recovery_code(code)
            rec_code = await self.db.scalar(
                select(MFARecoveryCode).where(
                    MFARecoveryCode.mfa_config_id == config.id,
                    MFARecoveryCode.code_hash == code_hash,
                    MFARecoveryCode.is_used.is_(False),
                )
            )
            if rec_code:
                rec_code.is_used = True
                rec_code.used_at = datetime.now(timezone.utc)
                is_valid = True

        if not is_valid:
            raise UnauthorizedException("Kiritilgan MFA kodi noto'g'ri")

        config.is_enabled = True
        config.enrolled_at = datetime.now(timezone.utc)
        config.last_verified_at = datetime.now(timezone.utc)

        # Log security audit
        await audit_logger.log_event(
            self.db,
            action="security.mfa.enable",
            resource_type="MFAConfiguration",
            company_id=company_id,
            user_id=user_id,
            details={"mfa_type": "TOTP", "status": "enabled"},
        )

        event = SecurityEvent(
            company_id=company_id,
            user_id=user_id,
            event_type=SecurityEventType.MFA_ENROLLED.value,
            severity=SecuritySeverity.INFO.value,
            title="Ikki Bosqichli Himoya (MFA) Yoqildi",
            description="Foydalanuvchi akkauntida TOTP MFA muvaffaqiyatli faollashtirildi.",
        )
        self.db.add(event)

        await self.db.commit()
        return MFAVerifyResponse(
            success=True,
            message="MFA muvaffaqiyatli faollashtirildi",
            is_mfa_enabled=True,
        )

    async def disable_mfa(
        self, user_id: uuid.UUID, company_id: uuid.UUID, code: str, password: str
    ) -> bool:
        """Disables MFA after verifying password and TOTP code."""
        user = await self.user_repo.get(user_id)
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Parol noto'g'ri")

        config = await self.sec_repo.get_mfa_config(user_id)
        if not config or not config.is_enabled:
            return True

        if not mfa_manager.verify_totp(config.secret_key, code):
            raise UnauthorizedException("MFA kodi noto'g'ri")

        config.is_enabled = False
        await self.db.commit()

        await audit_logger.log_event(
            self.db,
            action="security.mfa.disable",
            resource_type="MFAConfiguration",
            company_id=company_id,
            user_id=user_id,
            details={"status": "disabled"},
        )
        return True

    # ---------------------------------------------------------------------------
    # Session Management & Password Changes
    # ---------------------------------------------------------------------------

    async def list_active_sessions(self, user_id: uuid.UUID) -> List[RefreshToken]:
        return await session_manager.list_active_sessions(self.db, user_id)

    async def revoke_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> bool:
        return await session_manager.revoke_session(self.db, user_id, session_id)

    async def revoke_all_sessions(self, user_id: uuid.UUID, company_id: uuid.UUID) -> int:
        return await session_manager.revoke_all_sessions(self.db, user_id, company_id=company_id)

    async def change_password(
        self, user_id: uuid.UUID, company_id: uuid.UUID, payload: PasswordChangeRequest
    ) -> bool:
        user = await self.user_repo.get(user_id)
        if not user or not user.password_hash:
            raise UnauthorizedException("Foydalanuvchi topilmadi")

        if not verify_password(payload.current_password, user.password_hash):
            raise UnauthorizedException("Joriy parol noto'g'ri")

        if len(payload.new_password) < 8:
            raise ValidationException("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak")

        user.password_hash = hash_password(payload.new_password)
        await self.db.commit()

        # Invalidate existing sessions for security
        await self.revoke_all_sessions(user_id, company_id=company_id)

        await audit_logger.log_event(
            self.db,
            action="security.password.change",
            resource_type="User",
            company_id=company_id,
            user_id=user_id,
            details={"status": "password_updated"},
        )
        return True

    # ---------------------------------------------------------------------------
    # Break-Glass Access
    # ---------------------------------------------------------------------------

    async def activate_break_glass(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        duration_minutes: int = 60,
        elevated_role: str = "super_admin",
    ) -> BreakGlassSession:
        return await break_glass_manager.activate_emergency_access(
            self.db,
            company_id=company_id,
            user_id=user_id,
            reason=reason,
            duration_minutes=duration_minutes,
            elevated_role=elevated_role,
        )

    # ---------------------------------------------------------------------------
    # Audit & Security Dashboard
    # ---------------------------------------------------------------------------

    async def search_audit_logs(
        self, company_id: uuid.UUID, search_req: AuditSearchRequest
    ) -> List[AuditLog]:
        return await self.sec_repo.search_audit_logs(
            company_id=company_id,
            action=search_req.action,
            resource_type=search_req.resource_type,
            user_id=search_req.user_id,
            status=search_req.status,
            date_from=search_req.date_from,
            date_to=search_req.date_to,
            limit=search_req.limit,
        )

    async def get_security_events(
        self,
        company_id: uuid.UUID,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[SecurityEvent]:
        return await self.sec_repo.get_events(
            company_id=company_id, severity=severity, event_type=event_type, limit=limit
        )

    async def get_security_dashboard(self, company_id: uuid.UUID) -> Dict[str, Any]:
        return await security_monitor.get_security_dashboard(self.db, company_id)

    # ---------------------------------------------------------------------------
    # Security Policies (ABAC)
    # ---------------------------------------------------------------------------

    async def list_security_policies(self, company_id: uuid.UUID) -> List[SecurityPolicy]:
        from sqlalchemy import select as sa_select
        res = await self.db.scalars(
            sa_select(SecurityPolicy)
            .where(SecurityPolicy.company_id == company_id, SecurityPolicy.is_active.is_(True))
            .order_by(SecurityPolicy.priority.desc())
        )
        return list(res.all())

    async def create_security_policy(
        self, company_id: uuid.UUID, user_id: uuid.UUID, payload: "SecurityPolicyCreate"
    ) -> SecurityPolicy:
        policy = SecurityPolicy(
            company_id=company_id,
            name=payload.name,
            policy_type=payload.policy_type,
            rule_definition=payload.rule_definition,
            is_active=payload.is_active,
            priority=payload.priority,
            created_by=user_id,
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)

        await audit_logger.log_event(
            self.db, action="security.policy.create", resource_type="SecurityPolicy",
            company_id=company_id, user_id=user_id,
            details={"policy_type": payload.policy_type, "name": payload.name},
        )
        return policy

    async def delete_security_policy(self, company_id: uuid.UUID, policy_id: uuid.UUID) -> bool:
        policy = await self.db.get(SecurityPolicy, policy_id)
        if not policy or policy.company_id != company_id:
            return False
        policy.is_active = False
        await self.db.commit()
        return True

    # ---------------------------------------------------------------------------
    # Data Retention Policies
    # ---------------------------------------------------------------------------

    async def list_retention_policies(self, company_id: uuid.UUID) -> List[DataRetentionPolicy]:
        from sqlalchemy import select as sa_select
        res = await self.db.scalars(
            sa_select(DataRetentionPolicy)
            .where(DataRetentionPolicy.company_id == company_id)
            .order_by(DataRetentionPolicy.resource_type)
        )
        return list(res.all())

    async def create_retention_policy(
        self, company_id: uuid.UUID, payload: "RetentionPolicyCreate"
    ) -> DataRetentionPolicy:
        policy = DataRetentionPolicy(
            company_id=company_id,
            resource_type=payload.resource_type,
            retention_days=payload.retention_days,
            action_type=payload.action_type,
            is_active=payload.is_active,
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy
