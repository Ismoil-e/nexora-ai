import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.role import Role, RolePermission
from app.models.security import BreakGlassSession, MFAConfiguration, SecurityEvent
from app.models.session import RefreshToken
from app.security.contracts.types import SecurityEventType, SecuritySeverity


class SecurityMonitor:
    """Security Monitoring, Anomaly Detection, and Admin Security Dashboard Aggregator."""

    MAX_FAILED_LOGINS = 5
    LOCKOUT_WINDOW_MINUTES = 15

    async def record_login_attempt(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        email: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Records a login attempt and enforces automatic lockout on threshold breach."""
        now = datetime.now(timezone.utc)

        if success:
            event = SecurityEvent(
                company_id=company_id,
                user_id=user_id,
                event_type=SecurityEventType.LOGIN_SUCCESS.value,
                severity=SecuritySeverity.INFO.value,
                title="Muvaffaqiyatli Kirish",
                description=f"Foydalanuvchi {email} tizimga kirdi.",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(event)
            await db.commit()
            return

        # Record failed login
        event = SecurityEvent(
            company_id=company_id,
            user_id=user_id,
            event_type=SecurityEventType.LOGIN_FAILED.value,
            severity=SecuritySeverity.WARNING.value,
            title="Muvaffaqiyatsiz Kirish Urinishi",
            description=f"{email} uchun noto'g'ri parol yoki ma'lumotlar kiritildi.",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(event)

        # Check failed attempts in recent window
        window_start = now - timedelta(minutes=self.LOCKOUT_WINDOW_MINUTES)
        failed_count = await db.scalar(
            select(func.count()).select_from(SecurityEvent).where(
                SecurityEvent.company_id == company_id,
                SecurityEvent.event_type == SecurityEventType.LOGIN_FAILED.value,
                SecurityEvent.created_at >= window_start,
                SecurityEvent.description.like(f"%{email}%"),
            )
        ) or 0

        if failed_count >= self.MAX_FAILED_LOGINS:
            lockout_event = SecurityEvent(
                company_id=company_id,
                user_id=user_id,
                event_type=SecurityEventType.ACCOUNT_LOCKOUT.value,
                severity=SecuritySeverity.HIGH.value,
                title="Akkaunt Vaqtincha Bloklandi (Brute-Force Himoyasi)",
                description=f"{email} uchun {failed_count} marta xato urinish qayd etildi. Kirish {self.LOCKOUT_WINDOW_MINUTES} daqiqaga cheklandi.",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(lockout_event)

        await db.commit()

    async def get_security_dashboard(
        self, db: AsyncSession, company_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Synthesizes comprehensive Admin Security Dashboard metrics."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # 1. Active sessions
        active_sessions = await db.scalar(
            select(func.count()).select_from(RefreshToken).join(RefreshToken.user).where(
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > now,
            )
        ) or 0

        # 2. Failed logins in last 24 hours
        failed_logins_24h = await db.scalar(
            select(func.count()).select_from(SecurityEvent).where(
                SecurityEvent.company_id == company_id,
                SecurityEvent.event_type == SecurityEventType.LOGIN_FAILED.value,
                SecurityEvent.created_at >= yesterday,
            )
        ) or 0

        # 3. High & Critical severity events
        critical_events = await db.scalar(
            select(func.count()).select_from(SecurityEvent).where(
                SecurityEvent.company_id == company_id,
                SecurityEvent.severity.in_([SecuritySeverity.HIGH.value, SecuritySeverity.CRITICAL.value]),
                SecurityEvent.is_resolved.is_(False),
            )
        ) or 0

        # 4. MFA adoption count
        mfa_enabled_count = await db.scalar(
            select(func.count()).select_from(MFAConfiguration).where(
                MFAConfiguration.company_id == company_id,
                MFAConfiguration.is_enabled.is_(True),
            )
        ) or 0

        # 5. Active break-glass sessions
        active_break_glass = await db.scalar(
            select(func.count()).select_from(BreakGlassSession).where(
                BreakGlassSession.company_id == company_id,
                BreakGlassSession.is_active.is_(True),
                BreakGlassSession.expires_at > now,
            )
        ) or 0

        # 6. Recent security events
        recent_events_res = await db.scalars(
            select(SecurityEvent)
            .where(SecurityEvent.company_id == company_id)
            .order_by(desc(SecurityEvent.created_at))
            .limit(10)
        )
        recent_events = list(recent_events_res.all())

        # Posture score computation
        score = 100
        score -= min(30, critical_events * 10)
        score -= min(20, failed_logins_24h * 2)
        if active_break_glass > 0:
            score -= 10
        security_posture_score = max(20, score)

        return {
            "company_id": company_id,
            "generated_at": now,
            "security_posture_score": security_posture_score,
            "active_sessions_count": active_sessions,
            "failed_logins_24h": failed_logins_24h,
            "critical_events_count": critical_events,
            "mfa_enabled_users_count": mfa_enabled_count,
            "active_break_glass_count": active_break_glass,
            "recent_events": [
                {
                    "id": str(e.id),
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "title": e.title,
                    "description": e.description,
                    "is_resolved": e.is_resolved,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in recent_events
            ],
        }


security_monitor = SecurityMonitor()
