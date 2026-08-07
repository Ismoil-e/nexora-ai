"""Cognitive Core service stubs integrated with existing domain services."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts.types import AgentIdentity, AgentRequest
from app.cognitive.contracts.frames import ContextFrame, EvidencePack
from app.cognitive.interfaces.ports import ContextEnginePort, MemoryEnginePort, PlanningEnginePort


class ContextEngine(ContextEnginePort):
    """Assembles ContextFrame from auth identity and request hints."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build(self, identity: AgentIdentity, request: AgentRequest) -> ContextFrame:
        department_id = identity.department_id
        project_id = identity.project_id
        raw_dept = request.metadata.get("department_id")
        raw_project = request.metadata.get("project_id")
        if department_id is None and raw_dept:
            try:
                department_id = uuid.UUID(str(raw_dept))
            except (TypeError, ValueError):
                department_id = None
        if project_id is None and raw_project:
            try:
                project_id = uuid.UUID(str(raw_project))
            except (TypeError, ValueError):
                project_id = None

        return ContextFrame(
            company_id=identity.company_id,
            user_id=identity.user_id,
            permissions=list(identity.permissions),
            roles=list(identity.roles),
            department_id=department_id,
            project_id=project_id,
            conversation_id=request.chat_id,
            active_document_ids=list(request.document_ids),
            extras={
                "agent_key": request.agent_key,
                "metadata": request.metadata,
            },
        )


class MemoryEngine(MemoryEnginePort):
    """Hybrid-memory facade over DocumentService + ChatMemory until full HMS lands."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def retrieve(self, frame: ContextFrame, query: str, top_k: int = 5) -> EvidencePack:
        from app.services.document_service import DocumentService

        doc_service = DocumentService(self.db)
        rag = await doc_service.search_rag(frame.company_id, query, top_k=top_k)

        memory_items: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        for source in rag.get("sources", []) or []:
            item = {
                "type": "document_chunk",
                "content": source.get("content") or source.get("text") or "",
                "document_id": source.get("document_id"),
                "score": source.get("score"),
            }
            memory_items.append(item)
            citations.append({
                "document_id": source.get("document_id"),
                "snippet": (item["content"] or "")[:240],
            })

        if rag.get("answer"):
            memory_items.insert(0, {
                "type": "rag_summary",
                "content": rag["answer"],
            })

        # Lightweight conversation memory if chat is present
        if frame.conversation_id:
            from app.models.chat import ChatMemory
            from sqlalchemy import select

            stmt = (
                select(ChatMemory)
                .where(
                    ChatMemory.chat_id == frame.conversation_id,
                    ChatMemory.deleted_at.is_(None),
                )
                .order_by(ChatMemory.created_at.desc())
                .limit(5)
            )
            result = await self.db.execute(stmt)
            for mem in result.scalars().all():
                memory_items.append({
                    "type": "chat_memory",
                    "content": mem.value,
                    "key": mem.key,
                    "summary": mem.summary,
                })

        return EvidencePack(
            query=query,
            memory_items=memory_items,
            graph_summary={"status": "stub", "message": "Knowledge Graph connector pending full HMS"},
            timeline=[],
            decisions=[],
            citations=citations,
        )

    async def save_episode(
        self,
        frame: ContextFrame,
        agent_key: str,
        input_text: str,
        output_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Persist episode via ChatMemory when conversation exists; otherwise return synthetic ref."""
        ref = f"episode:{agent_key}:{uuid.uuid4()}"
        if not frame.conversation_id:
            return ref

        from app.models.chat import ChatMemory

        payload = {
            "agent_key": agent_key,
            "input": input_text[:2000],
            "output": output_text[:4000],
            "metadata": metadata or {},
        }
        mem = ChatMemory(
            chat_id=frame.conversation_id,
            key=f"agent_episode:{agent_key}",
            value=json.dumps(payload, ensure_ascii=False),
            summary=f"{agent_key} episode",
        )
        self.db.add(mem)
        await self.db.flush()
        return str(mem.id)


class PlanningEngine(PlanningEnginePort):
    """Deterministic planning stub used before agent execute()."""

    async def plan(
        self,
        frame: ContextFrame,
        evidence: EvidencePack,
        agent_key: str,
        intent: str,
    ) -> dict[str, Any]:
        steps = [
            {"step": 1, "action": "collect_evidence", "count": len(evidence.memory_items)},
            {"step": 2, "action": "reason_with_context", "agent_key": agent_key},
            {"step": 3, "action": "generate_response"},
        ]
        tools: list[str] = []
        if agent_key in {"document", "knowledge", "search"}:
            tools.append("search_knowledge_base")
        if agent_key == "task":
            tools.append("create_company_task")
        if agent_key == "notification":
            tools.append("send_notification")
        if agent_key == "analytics":
            tools.append("execute_enterprise_connector")

        return {
            "steps": steps,
            "tools": tools,
            "rationale": f"Plan for '{agent_key}' intent: {intent[:180]}",
            "requires_async": agent_key in {"document", "analytics", "monitoring"} and len(intent) > 2000,
            "frame_company_id": str(frame.company_id),
        }
