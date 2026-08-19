import json
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.contracts.types import NexoraEvent
from app.services.document_service import DocumentService


class IntegrationMemoryRouter:
    """Routes external Integration Hub events into Nexora Second Brain & Knowledge Graph."""

    @staticmethod
    async def route_event_to_memory(db: AsyncSession, event: NexoraEvent) -> dict[str, Any]:
        if not event.requires_memory_ingestion or not event.is_important:
            return {"status": "skipped", "reason": "Event does not require memory ingestion"}

        # Filter noise or sensitive keys
        clean_content = f"{event.title or ''}\n{event.content_summary or ''}"
        if len(clean_content.strip()) < 10:
            return {"status": "skipped", "reason": "Content too short for memory indexing"}

        # Ingest document/knowledge memory using DocumentService
        doc_service = DocumentService(db)
        doc = await doc_service.create_document(
            company_id=event.company_id,
            uploaded_by=None,
            filename=f"Integration_{event.source_vendor}_{event.event_type}_{event.event_id[:8]}.txt",
            original_name=event.title or f"{event.source_vendor} event",
            file_type="integration_memory",
            mime_type="text/plain",
            file_size=len(clean_content.encode()),
            storage_path=f"integrations/{event.company_id}/{event.event_id}.txt",
            tags=f"integration,{event.source_vendor},{event.event_type}",
            metadata_json=json.dumps({
                "integration_id": str(event.integration_id),
                "source_vendor": event.source_vendor,
                "event_id": event.event_id,
                "actor_email": event.actor_email,
                "resource_type": event.resource_type,
            }),
        )

        return {
            "status": "ingested",
            "document_id": str(doc.id),
            "memory_type": "second_brain",
        }


memory_router = IntegrationMemoryRouter()
