import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import BreakGlassSession, SecurityEvent
from app.security.contracts.types import SecurityEventType, SecuritySeverity
from app.utils.exceptions import UnauthorizedException, ValidationException


class BreakGlassManager:
    """Manages emergency Break-Glass elevated access sessions with strict auditing."""

    async def activate_emergency_access(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        duration_minutes: int = 60,
        elevated_role: str = "super_admin",
        approved_by: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> BreakGlassSession:
        """Activates an emergency break-glass session."""
        if not reason or len(reason.strip()) < 15:
            raise ValidationException("Break-Glass faollashtirish uchun batafsil sabab (kamida 15 belgi) ko'rsatilishi shart.")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=min(duration_minutes, 240))  # Maximum 4 hours

        session = BreakGlassSession(
            company_id=company_id,
            user_id=user_id,
            approved_by=approved_by,
            reason=reason.strip(),
            elevated_role=elevated_role,
            is_active=True,
            duration_minutes=duration_minutes,
            expires_at=expires_at,
        )
        db.add(session)

        # Log CRITICAL security event
        event = SecurityEvent(
            company_id=company_id,
            user_id=user_id,
            event_type=SecurityEventType.BREAK_GLASS_ACTIVATED.value,
            severity=SecuritySeverity.CRITICAL.value,
            title="Favqulodda Break-Glass Ruxsati Faollashtirildi",
            description=f"Foydalanuvchi {user_id} {duration_minutes} daqiqa muddatga '{elevated_role}' huquqiga ko'tarildi. Sabab: {reason}",
            ip_address=ip_address,
        )
        db.add(event)

        await db.commit()
        await db.refresh(session)
        return session

    async def is_break_glass_active_for_user(
        self, db: AsyncSession, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Checks whether the user has an active, non-expired emergency session."""
        now = datetime.now(timezone.utc)
        session = await db.scalar(
            select(BreakGlassSession).where(
                BreakGlassSession.company_id == company_id,
                BreakGlassSession.user_id == user_id,
                BreakGlassSession.is_active.is_(True),
                BreakGlassSession.expires_at > now,
            )
        )
        return session is not None

    async def revoke_emergency_access(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        session_id: uuid.UUID,
        revoked_by: uuid.UUID,
    ) -> BreakGlassSession:
        """Revokes an active break-glass session."""
        session = await db.get(BreakGlassSession, session_id)
        if not session or session.company_id != company_id:
            raise ValidationException("Break-Glass sessiyasi topilmadi")

        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
        session.revoked_by = revoked_by
        await db.commit()
        await db.refresh(session)
        return session

    async def get_active_sessions(
        self, db: AsyncSession, company_id: uuid.UUID
    ) -> List[BreakGlassSession]:
        now = datetime.now(timezone.utc)
        res = await db.scalars(
            select(BreakGlassSession)
            .where(
                BreakGlassSession.company_id == company_id,
                BreakGlassSession.is_active.is_(True),
                BreakGlassSession.expires_at > now,
            )
            .order_by(desc(BreakGlassSession.created_at))
        )
        return list(res.all())


break_glass_manager = BreakGlassManager()
