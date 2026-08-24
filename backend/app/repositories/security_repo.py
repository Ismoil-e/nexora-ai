import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.security import (
    BreakGlassSession,
    DataRetentionPolicy,
    MFAConfiguration,
    MFARecoveryCode,
    SecurityEvent,
    SecurityPolicy,
)
from app.repositories.base import BaseRepository


class SecurityRepository(BaseRepository[SecurityEvent]):
    def __init__(self, db: AsyncSession):
        super().__init__(SecurityEvent, db)

    # ---------------------------------------------------------------------------
    # MFA
    # ---------------------------------------------------------------------------
    async def get_mfa_config(self, user_id: uuid.UUID) -> Optional[MFAConfiguration]:
        return await self.db.scalar(
            select(MFAConfiguration).where(MFAConfiguration.user_id == user_id)
        )

    async def save_mfa_config(
        self,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        secret_key: str,
        recovery_code_hashes: List[str],
    ) -> MFAConfiguration:
        config = await self.get_mfa_config(user_id)
        if not config:
            config = MFAConfiguration(
                user_id=user_id,
                company_id=company_id,
                secret_key=secret_key,
                is_enabled=False,
            )
            self.db.add(config)
            await self.db.flush()
        else:
            config.secret_key = secret_key
            config.is_enabled = False

        # Replace recovery codes
        for code_hash in recovery_code_hashes:
            rec = MFARecoveryCode(
                mfa_config_id=config.id,
                code_hash=code_hash,
                is_used=False,
            )
            self.db.add(rec)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    # ---------------------------------------------------------------------------
    # Security Events
    # ---------------------------------------------------------------------------
    async def get_events(
        self,
        company_id: uuid.UUID,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[SecurityEvent]:
        query = select(SecurityEvent).where(SecurityEvent.company_id == company_id)
        if severity:
            query = query.where(SecurityEvent.severity == severity.upper())
        if event_type:
            query = query.where(SecurityEvent.event_type == event_type.upper())
        query = query.order_by(desc(SecurityEvent.created_at)).limit(limit)

        res = await self.db.scalars(query)
        return list(res.all())

    # ---------------------------------------------------------------------------
    # Audit Search
    # ---------------------------------------------------------------------------
    async def search_audit_logs(
        self,
        company_id: uuid.UUID,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[AuditLog]:
        query = select(AuditLog).where(AuditLog.company_id == str(company_id))

        if action:
            query = query.where(AuditLog.action.ilike(f"%{action}%"))
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if status:
            query = query.where(AuditLog.status == status)
        if date_from:
            query = query.where(AuditLog.created_at >= date_from)
        if date_to:
            query = query.where(AuditLog.created_at <= date_to)

        query = query.order_by(desc(AuditLog.created_at)).limit(limit)
        res = await self.db.scalars(query)
        return list(res.all())
