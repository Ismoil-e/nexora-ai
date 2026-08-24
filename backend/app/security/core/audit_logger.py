import json
import re
from typing import Any, Dict, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditLogger:
    """Enterprise Audit Logging service with automated secret sanitization and immutable recording."""

    REDACT_KEYS = {"password", "secret", "token", "access_token", "refresh_token", "api_key", "secret_key", "credentials", "authorization"}

    def sanitize_payload(self, data: Any) -> Any:
        """Recursively sanitizes sensitive credential fields."""
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(red in k.lower() for red in self.REDACT_KEYS):
                    sanitized[k] = "[REDACTED_SECRET]"
                else:
                    sanitized[k] = self.sanitize_payload(v)
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_payload(item) for item in data]
        elif isinstance(data, str):
            # Mask potential JWT or Bearer tokens in text
            if len(data) > 60 and ("Bearer " in data or "eyJ" in data):
                return "[REDACTED_TOKEN_STRING]"
            return data
        return data

    async def log_event(
        self,
        db: AsyncSession,
        action: str,
        resource_type: str,
        company_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        severity: str = "INFO",
    ) -> AuditLog:
        """Creates and stores a sanitized audit log record."""
        sanitized_details = self.sanitize_payload(details) if details else None
        details_str = json.dumps(sanitized_details, ensure_ascii=False) if sanitized_details else None

        audit = AuditLog(
            company_id=company_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details_str,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            severity=severity,
        )
        db.add(audit)
        await db.flush()
        await db.refresh(audit)
        return audit


audit_logger = AuditLogger()
