import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import RefreshToken
from app.models.security import SecurityEvent
from app.security.contracts.types import SecurityEventType, SecuritySeverity


class SessionManager:
    """Manages active user sessions, token rotation, revocation, and replay detection."""

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def list_active_sessions(self, db: AsyncSession, user_id: uuid.UUID) -> List[RefreshToken]:
        now = datetime.now(timezone.utc)
        res = await db.scalars(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > now,
            )
            .order_by(desc(RefreshToken.created_at))
        )
        return list(res.all())

    async def revoke_session(self, db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> bool:
        session = await db.get(RefreshToken, session_id)
        if not session or session.user_id != user_id:
            return False
        session.is_revoked = True
        await db.commit()
        return True

    async def revoke_all_sessions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        company_id: Optional[uuid.UUID] = None,
        reason: str = "User initiated logout from all devices",
    ) -> int:
        """Revokes all active sessions for a user."""
        res = await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True)
        )
        count = res.rowcount

        if company_id:
            event = SecurityEvent(
                company_id=company_id,
                user_id=user_id,
                event_type=SecurityEventType.TOKEN_REVOKED.value,
                severity=SecuritySeverity.INFO.value,
                title="Barcha Sessiyalar Bekor Qilindi",
                description=f"{user_id} foydalanuvchining barcha {count} ta faol sessiyasi bekor qilindi. Sabab: {reason}",
            )
            db.add(event)

        await db.commit()
        return count

    async def validate_and_rotate_refresh_token(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Validates refresh token and detects token replay attacks."""
        token_hash = self.hash_token(token)
        now = datetime.now(timezone.utc)

        token_record = await db.scalar(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.token_hash == token_hash,
            )
        )

        if not token_record:
            return False

        if token_record.is_revoked:
            # Token replay attack detected! An attacker or compromised client is reusing an old token
            await self.revoke_all_sessions(
                db,
                user_id=user_id,
                company_id=company_id,
                reason="Suspicious token replay detected - all sessions revoked for security",
            )
            event = SecurityEvent(
                company_id=company_id,
                user_id=user_id,
                event_type=SecurityEventType.SUSPICIOUS_TOKEN_REPLAY.value,
                severity=SecuritySeverity.CRITICAL.value,
                title="Shubhali Token Qayta Ishlatilishi (Token Replay Attack)",
                description=f"Bekor qilingan token qayta taqdim etildi. Foydalanuvchining barcha sessiyalari avtomatik to'xtatildi.",
                ip_address=ip_address,
                user_agent=device_info,
            )
            db.add(event)
            await db.commit()
            return False

        if token_record.expires_at <= now:
            return False

        # Invalidate current token (Rotation)
        token_record.is_revoked = True
        token_record.last_used_at = now
        await db.flush()
        return True


session_manager = SessionManager()
