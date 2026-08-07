"""Builds AgentContext using Cognitive Context Engine + domain services."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts.types import AgentContext, AgentRequest
from app.cognitive.services.engines import ContextEngine


class AgentContextBuilder:
    """Context builder shared by the agent pipeline."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.context_engine = ContextEngine(db)

    async def build(
        self,
        request: AgentRequest,
        config: dict[str, Any] | None = None,
    ) -> AgentContext:
        frame = await self.context_engine.build(request.identity, request)

        active_documents: list[dict] = []
        if request.document_ids:
            from app.repositories.document_repo import DocumentRepository

            repo = DocumentRepository(self.db)
            for doc_id in request.document_ids:
                doc = await repo.get(doc_id)
                if doc and doc.company_id == request.identity.company_id:
                    active_documents.append({
                        "id": str(doc.id),
                        "filename": doc.original_filename,
                        "status": doc.status,
                        "category": doc.category,
                    })

        conversation_summary = None
        if request.chat_id:
            from app.repositories.chat_repo import ChatRepository

            chat_repo = ChatRepository(self.db)
            chat = await chat_repo.get(request.chat_id)
            if chat and chat.company_id == request.identity.company_id:
                conversation_summary = chat.title

        return AgentContext(
            request=request,
            company_id=frame.company_id,
            user_id=frame.user_id,
            permissions=frame.permissions,
            conversation_summary=conversation_summary,
            active_documents=active_documents,
            project_id=frame.project_id,
            department_id=frame.department_id,
            workflow_hints=list(request.metadata.get("workflow_hints", [])),
            config=config or {},
            extras={"context_frame": frame},
        )
