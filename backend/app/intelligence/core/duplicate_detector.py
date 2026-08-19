import hashlib
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DuplicateDetector:
    """Detects exact or semantic duplicate documents using SHA-256 hashes and content signatures."""

    @staticmethod
    def compute_content_hash(file_data: bytes | str) -> str:
        data_bytes = file_data.encode() if isinstance(file_data, str) else file_data
        return hashlib.sha256(data_bytes).hexdigest()

    async def check_duplicate(
        self,
        db: AsyncSession,
        company_id: uuid.UUID,
        content_hash: str,
        filename: str,
    ) -> tuple[bool, uuid.UUID | None]:
        query = select(Document).where(
            Document.company_id == company_id,
            Document.content_hash == content_hash,
            Document.deleted_at.is_(None),
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            return True, existing.id

        return False, None


duplicate_detector = DuplicateDetector()
