import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.chat import Chat, ChatMessage
from app.models.document import Document
from app.models.report import Report
from app.models.security import DataRetentionPolicy, SecurityEvent
from app.security.contracts.types import SecurityEventType, SecuritySeverity


class DataRetentionEngine:
    """Manages tenant-aware data retention policies, automated cleanup, and GDPR-compliant data export."""

    async def execute_retention_policy(
        self, db: AsyncSession, company_id: uuid.UUID, resource_type: str
    ) -> Dict[str, Any]:
        """Purges or archives expired records according to the active tenant policy."""
        policy = await db.scalar(
            select(DataRetentionPolicy).where(
                DataRetentionPolicy.company_id == company_id,
                DataRetentionPolicy.resource_type == resource_type,
                DataRetentionPolicy.is_active.is_(True),
            )
        )

        if not policy:
            return {"status": "no_active_policy", "purged_count": 0}

        cutoff = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        purged_count = 0

        if resource_type == "audit_logs":
            res = await db.execute(
                delete(AuditLog).where(
                    AuditLog.company_id == str(company_id),
                    AuditLog.created_at < cutoff,
                )
            )
            purged_count = res.rowcount

        elif resource_type == "reports":
            res = await db.execute(
                delete(Report).where(
                    Report.company_id == company_id,
                    Report.created_at < cutoff,
                )
            )
            purged_count = res.rowcount

        policy.last_executed_at = datetime.now(timezone.utc)

        # Log security audit of the purge
        event = SecurityEvent(
            company_id=company_id,
            event_type=SecurityEventType.DATA_RETENTION_PURGED.value,
            severity=SecuritySeverity.INFO.value,
            title="Ma'lumotlarni Saqlash Muddati Bo'yicha Tozalash (Data Retention)",
            description=f"'{resource_type}' resursi bo'yicha {policy.retention_days} kundan eski {purged_count} ta yozuv tozalandi.",
        )
        db.add(event)

        await db.commit()
        return {"status": "success", "resource_type": resource_type, "purged_count": purged_count}

    async def export_user_data(
        self, db: AsyncSession, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Generates a complete portable export of user-associated data for compliance/GDPR."""
        chats_res = await db.scalars(
            select(Chat).where(Chat.company_id == company_id, Chat.user_id == user_id)
        )
        chats = list(chats_res.all())

        docs_res = await db.scalars(
            select(Document).where(Document.company_id == company_id, Document.uploaded_by == user_id)
        )
        docs = list(docs_res.all())

        reports_res = await db.scalars(
            select(Report).where(Report.company_id == company_id, Report.created_by == user_id)
        )
        reports = list(reports_res.all())

        return {
            "user_id": str(user_id),
            "company_id": str(company_id),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "chat_sessions_count": len(chats),
            "uploaded_documents_count": len(docs),
            "generated_reports_count": len(reports),
            "documents": [{"id": str(d.id), "title": d.title, "filename": d.original_name} for d in docs],
            "reports": [{"id": str(r.id), "title": r.title, "type": r.report_type} for r in reports],
        }


retention_engine = DataRetentionEngine()
