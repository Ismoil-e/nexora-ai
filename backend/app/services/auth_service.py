import secrets
import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.company import Company
from app.models.security import SecurityEvent
from app.models.session import RefreshToken
from app.models.user import User
from app.repositories.company_repo import CompanyRepository
from app.repositories.user_repo import UserRepository
from app.security.contracts.types import SecurityEventType, SecuritySeverity
from app.security.core.audit_logger import audit_logger
from app.security.core.mfa_manager import mfa_manager
from app.security.core.security_monitor import security_monitor
from app.security.core.session_manager import session_manager
from app.utils.exceptions import ConflictException, UnauthorizedException, ValidationException
from app.utils.helpers import generate_slug


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.company_repo = CompanyRepository(db)

    async def register(self, email: str, password: str, first_name: str,
                        last_name: str, company_name: str) -> tuple[str, str, User]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictException("Bu email bilan profil allaqachon mavjud")

        # Password strength validation
        if len(password) < 8:
            raise ValidationException("Parol kamida 8 ta belgidan iborat bo'lishi kerak")
        if not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
            raise ValidationException("Parol kamida 1 ta katta harf va 1 ta raqamdan iborat bo'lishi kerak")

        slug = generate_slug(company_name)
        existing_company = await self.company_repo.get_by_slug(slug)
        if existing_company:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        company = await self.company_repo.create(
            name=company_name,
            slug=slug,
        )

        password_hash = hash_password(password)
        user = await self.user_repo.create(
            company_id=company.id,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )

        access_token = create_access_token(str(user.id), {
            "company_id": str(company.id),
            "email": user.email,
        })
        refresh_token = create_refresh_token(str(user.id))

        await self._save_refresh_token(user.id, refresh_token)

        await audit_logger.log_event(
            self.db, action="auth.register", resource_type="User",
            company_id=company.id, user_id=user.id,
            details={"email": email}, status="success",
        )

        return access_token, refresh_token, user

    async def login(self, email: str, password: str, ip_address: str = None,
                     user_agent: str = None) -> tuple[str, str, User, bool]:
        """
        Login with account lockout detection and MFA check.
        Returns (access_token, refresh_token, user, requires_mfa).
        """
        user = await self.user_repo.get_by_email(email)

        if not user:
            # Still record failed attempt for unknown emails for monitoring
            await security_monitor.record_login_attempt(
                self.db, company_id=uuid.uuid4(), user_id=None,
                email=email, success=False, ip_address=ip_address, user_agent=user_agent,
            )
            raise UnauthorizedException("Email yoki parol noto'g'ri")

        # Check account lockout
        from sqlalchemy import func, select
        from app.models.security import SecurityEvent
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        lockout_window = now - timedelta(minutes=15)
        failed_count = await self.db.scalar(
            select(func.count()).select_from(SecurityEvent).where(
                SecurityEvent.user_id == user.id,
                SecurityEvent.event_type == SecurityEventType.LOGIN_FAILED.value,
                SecurityEvent.created_at >= lockout_window,
            )
        ) or 0
        if failed_count >= 5:
            raise UnauthorizedException("Akkaunt vaqtincha bloklandi. 15 daqiqadan keyin qayta urinib ko'ring.")

        if not user.password_hash:
            raise UnauthorizedException("Bu akkaunt Google orqali yaratilgan")

        if not verify_password(password, user.password_hash):
            await security_monitor.record_login_attempt(
                self.db, company_id=user.company_id, user_id=user.id,
                email=email, success=False, ip_address=ip_address, user_agent=user_agent,
            )
            raise UnauthorizedException("Email yoki parol noto'g'ri")

        if not user.is_active:
            raise UnauthorizedException("Akkaunt faol emas")

        # Record successful login
        await security_monitor.record_login_attempt(
            self.db, company_id=user.company_id, user_id=user.id,
            email=email, success=True, ip_address=ip_address, user_agent=user_agent,
        )

        # Check if MFA is enabled
        from sqlalchemy import select as sa_select
        from app.models.security import MFAConfiguration
        mfa_config = await self.db.scalar(
            sa_select(MFAConfiguration).where(
                MFAConfiguration.user_id == user.id,
                MFAConfiguration.is_enabled.is_(True),
            )
        )
        if mfa_config:
            # Don't issue tokens yet — client must verify MFA
            temp_token = create_access_token(str(user.id), {
                "company_id": str(user.company_id),
                "email": user.email,
                "mfa_pending": True,
            }, )
            return temp_token, "", user, True

        access_token = create_access_token(str(user.id), {
            "company_id": str(user.company_id),
            "email": user.email,
        })
        refresh_token = create_refresh_token(str(user.id))
        await self._save_refresh_token(user.id, refresh_token)

        return access_token, refresh_token, user, False

    async def verify_mfa_login(self, user_id: uuid.UUID, code: str) -> tuple[str, str, User]:
        """Verifies MFA code after password login and issues full tokens."""
        from sqlalchemy import select as sa_select
        from app.models.security import MFAConfiguration, MFARecoveryCode

        user = await self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("Foydalanuvchi topilmadi")

        config = await self.db.scalar(
            sa_select(MFAConfiguration).where(MFAConfiguration.user_id == user_id)
        )
        if not config or not config.is_enabled:
            raise UnauthorizedException("MFA sozlanmagan")

        is_valid = mfa_manager.verify_totp(config.secret_key, code)
        if not is_valid:
            # Check recovery codes
            code_hash = mfa_manager.hash_recovery_code(code)
            rec_code = await self.db.scalar(
                sa_select(MFARecoveryCode).where(
                    MFARecoveryCode.mfa_config_id == config.id,
                    MFARecoveryCode.code_hash == code_hash,
                    MFARecoveryCode.is_used.is_(False),
                )
            )
            if rec_code:
                rec_code.is_used = True
                rec_code.used_at = datetime.now(timezone.utc)
                is_valid = True
            else:
                await audit_logger.log_event(
                    self.db, action="auth.mfa.failed", resource_type="User",
                    company_id=user.company_id, user_id=user.id,
                    details={"email": user.email}, status="failure", severity="WARNING",
                )
                raise UnauthorizedException("MFA kodi noto'g'ri")

        config.last_verified_at = datetime.now(timezone.utc)
        await self.db.flush()

        await audit_logger.log_event(
            self.db, action="auth.mfa.verified", resource_type="User",
            company_id=user.company_id, user_id=user.id,
            details={"email": user.email}, status="success",
        )

        access_token = create_access_token(str(user.id), {
            "company_id": str(user.company_id),
            "email": user.email,
        })
        refresh_token = create_refresh_token(str(user.id))
        await self._save_refresh_token(user.id, refresh_token)

        return access_token, refresh_token, user

    async def logout(self, user_id: uuid.UUID, company_id: uuid.UUID) -> int:
        """Logs out user by revoking all active sessions."""
        count = await session_manager.revoke_all_sessions(self.db, user_id, company_id=company_id)
        await audit_logger.log_event(
            self.db, action="auth.logout", resource_type="User",
            company_id=company_id, user_id=user_id,
            details={"revoked_sessions": count}, status="success",
        )
        return count

    async def request_password_reset(self, email: str) -> str | None:
        """Generates a password reset token (returns token, email sent separately)."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal whether email exists
            return None

        reset_token = secrets.token_urlsafe(32)
        token_hash = sha256(reset_token.encode()).hexdigest()

        # Store as refresh token with short expiry for reset
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        stmt = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info="password_reset",
        )
        self.db.add(stmt)
        await self.db.flush()

        await audit_logger.log_event(
            self.db, action="auth.password_reset_request", resource_type="User",
            company_id=user.company_id, user_id=user.id,
            details={"email": email}, status="success",
        )

        return reset_token

    async def confirm_password_reset(self, token: str, new_password: str) -> bool:
        """Confirms password reset with token."""
        token_hash = sha256(token.encode()).hexdigest()
        now = datetime.now(timezone.utc)

        from sqlalchemy import select as sa_select
        token_record = await self.db.scalar(
            sa_select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.device_info == "password_reset",
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > now,
            )
        )
        if not token_record:
            raise UnauthorizedException("Yaroqsiz yoki muddati tugagan token")

        if len(new_password) < 8:
            raise ValidationException("Parol kamida 8 ta belgidan iborat bo'lishi kerak")

        user = await self.user_repo.get(token_record.user_id)
        if not user:
            raise UnauthorizedException("Foydalanuvchi topilmadi")

        user.password_hash = hash_password(new_password)
        token_record.is_revoked = True
        await self.db.flush()

        # Invalidate all sessions for security
        await session_manager.revoke_all_sessions(self.db, user.id, company_id=user.company_id)

        await audit_logger.log_event(
            self.db, action="auth.password_reset_confirm", resource_type="User",
            company_id=user.company_id, user_id=user.id,
            details={"status": "password_reset"}, status="success",
        )
        return True

    async def google_login(self, email: str, google_id: str, display_name: str | None = None,
                            photo_url: str | None = None) -> tuple[str, str, User]:
        user = await self.user_repo.get_by_google_id(google_id)
        if not user:
            user = await self.user_repo.get_by_email(email)

        if not user:
            slug = generate_slug(f"{display_name or email}-company")
            company = await self.company_repo.create(
                name=f"{display_name or email}'s Company",
                slug=slug,
            )

            name_parts = (display_name or email).split()
            user = await self.user_repo.create(
                company_id=company.id,
                email=email,
                google_id=google_id,
                first_name=name_parts[0] if name_parts else "User",
                last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "User",
                avatar_url=photo_url or "",
                is_verified=True,
            )
        else:
            if not user.google_id:
                await self.user_repo.update(user.id, google_id=google_id)
            if photo_url and not user.avatar_url:
                await self.user_repo.update(user.id, avatar_url=photo_url)

        access_token = create_access_token(str(user.id), {
            "company_id": str(user.company_id),
            "email": user.email,
        })
        refresh_token = create_refresh_token(str(user.id))

        await self._save_refresh_token(user.id, refresh_token)

        return access_token, refresh_token, user

    async def refresh_token(self, token: str, ip_address: str = None, user_agent: str = None) -> tuple[str, str]:
        """Refresh token with rotation and replay detection."""
        payload = decode_token(token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Yaroqsiz refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Token noto'g'ri")

        uid = uuid.UUID(user_id)
        user = await self.user_repo.get(uid)
        if not user or not user.is_active:
            raise UnauthorizedException("Foydalanuvchi topilmadi")

        # Validate and rotate via session manager (replay detection)
        is_valid = await session_manager.validate_and_rotate_refresh_token(
            self.db, uid, user.company_id, token, ip_address=ip_address, user_agent=user_agent,
        )
        if not is_valid:
            raise UnauthorizedException("Refresh token yaroqsiz yoki qayta ishlatilgan")

        new_access = create_access_token(user_id, {
            "company_id": str(user.company_id),
            "email": user.email,
        })
        new_refresh = create_refresh_token(user_id)
        await self._save_refresh_token(user.id, new_refresh)

        return new_access, new_refresh

    async def _save_refresh_token(self, user_id: uuid.UUID, token: str):
        from hashlib import sha256

        token_hash = sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        stmt = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(stmt)
        await self.db.flush()
