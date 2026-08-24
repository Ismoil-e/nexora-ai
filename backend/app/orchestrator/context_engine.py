"""Context Engine — assembles, ranks, deduplicates, and prioritizes context for AI operations.

Priority model:
1. System instructions
2. Security policies
3. User permissions
4. Current task
5. Relevant organizational knowledge
6. Retrieved documents
7. Memory
8. External information
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ContextSource:
    """A single context item from any source."""
    source_type: str  # "system", "policy", "task", "document", "memory", "knowledge", "rag", "external"
    content: str
    priority: int = 5  # 1=highest, 10=lowest
    relevance_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0
    source_id: str | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AssembledContext:
    """Final assembled context for AI processing."""
    sources: list[ContextSource] = field(default_factory=list)
    total_tokens_estimate: int = 0
    truncated: bool = False
    primary_sources: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)


# Priority constants
PRIORITY_SYSTEM = 1
PRIORITY_SECURITY = 2
PRIORITY_PERMISSIONS = 3
PRIORITY_TASK = 4
PRIORITY_ORG_KNOWLEDGE = 5
PRIORITY_DOCUMENTS = 6
PRIORITY_MEMORY = 7
PRIORITY_EXTERNAL = 8

# Approximate tokens per character
CHARS_PER_TOKEN = 4


class ContextEngine:
    """Assembles and prioritizes context from multiple sources."""

    def __init__(self, db: AsyncSession, max_context_tokens: int = 32000):
        self.db = db
        self.max_context_tokens = max_context_tokens

    async def assemble(
        self,
        *,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        user_input: str,
        permissions: list[str] | None = None,
        chat_id: uuid.UUID | None = None,
        document_ids: list[uuid.UUID] | None = None,
        agent_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AssembledContext:
        """Assemble context from all available sources."""
        meta = metadata or {}
        sources: list[ContextSource] = []

        # 1. System instructions (always first)
        system_prompt = meta.get("system_prompt", "Sen Nexora AI yordamchisisan.")
        sources.append(ContextSource(
            source_type="system",
            content=system_prompt,
            priority=PRIORITY_SYSTEM,
            relevance_score=1.0,
        ))

        # 2. Security policies
        if permissions:
            sources.append(ContextSource(
                source_type="policy",
                content=f"User permissions: {', '.join(permissions)}",
                priority=PRIORITY_SECURITY,
                relevance_score=0.9,
                metadata={"permission_count": len(permissions)},
            ))

        # 3. Task context
        if user_input:
            sources.append(ContextSource(
                source_type="task",
                content=user_input,
                priority=PRIORITY_TASK,
                relevance_score=1.0,
            ))

        # 4. Document context (from specified documents)
        if document_ids:
            doc_sources = await self._retrieve_documents(company_id, document_ids, user_input)
            sources.extend(doc_sources)

        # 5. RAG retrieval (semantic search)
        rag_sources = await self._retrieve_rag(company_id, user_input, top_k=5)
        sources.extend(rag_sources)

        # 6. Memory context (conversation history)
        if chat_id:
            memory_sources = await self._retrieve_conversation_memory(chat_id)
            sources.extend(memory_sources)

        # 7. Knowledge Graph context
        kg_sources = await self._retrieve_knowledge_graph(company_id, user_input)
        sources.extend(kg_sources)

        # Rank, deduplicate, and compress
        ranked = self._rank_sources(sources)
        deduped = self._deduplicate(ranked)
        truncated, total_tokens = self._compress_to_limit(deduped)

        # Build citations
        citations = []
        for src in truncated:
            if src.citations:
                citations.extend(src.citations)
            elif src.source_id:
                citations.append({
                    "source_type": src.source_type,
                    "source_id": src.source_id,
                    "snippet": src.content[:200],
                })

        primary_sources = list({s.source_type for s in truncated if s.source_type in ("document", "rag", "knowledge", "memory")})

        return AssembledContext(
            sources=truncated,
            total_tokens_estimate=total_tokens,
            truncated=total_tokens >= self.max_context_tokens,
            primary_sources=primary_sources,
            citations=citations,
        )

    async def _retrieve_documents(
        self,
        company_id: uuid.UUID,
        document_ids: list[uuid.UUID],
        query: str,
    ) -> list[ContextSource]:
        """Retrieve context from specified documents."""
        from app.repositories.document_repo import DocumentRepository

        sources = []
        repo = DocumentRepository(self.db)
        for doc_id in document_ids:
            doc = await repo.get(doc_id)
            if doc and doc.company_id == company_id:
                content = doc.description or doc.original_filename or ""
                if hasattr(doc, "ocr_text") and doc.ocr_text:
                    content = doc.ocr_text[:2000]
                sources.append(ContextSource(
                    source_type="document",
                    content=content,
                    priority=PRIORITY_DOCUMENTS,
                    relevance_score=0.8,
                    source_id=str(doc.id),
                    metadata={"filename": doc.original_filename, "category": getattr(doc, "category", None)},
                ))
        return sources

    async def _retrieve_rag(
        self,
        company_id: uuid.UUID,
        query: str,
        top_k: int = 5,
    ) -> list[ContextSource]:
        """Retrieve context from RAG (vector search)."""
        from app.services.document_service import DocumentService

        sources = []
        try:
            doc_service = DocumentService(self.db)
            rag = await doc_service.search_rag(company_id, query, top_k=top_k)

            for item in (rag.get("sources") or []):
                content = item.get("content") or item.get("text") or ""
                sources.append(ContextSource(
                    source_type="rag",
                    content=content,
                    priority=PRIORITY_DOCUMENTS,
                    relevance_score=float(item.get("score", 0)),
                    source_id=item.get("document_id"),
                    token_estimate=len(content) // CHARS_PER_TOKEN,
                ))

            # Include RAG summary as high-priority context
            if rag.get("answer"):
                sources.insert(0, ContextSource(
                    source_type="rag",
                    content=f"RAG Summary: {rag['answer']}",
                    priority=PRIORITY_ORG_KNOWLEDGE,
                    relevance_score=0.85,
                    token_estimate=len(rag["answer"]) // CHARS_PER_TOKEN,
                ))
        except Exception:
            pass  # RAG unavailable — continue with other sources

        return sources

    async def _retrieve_conversation_memory(
        self,
        chat_id: uuid.UUID,
    ) -> list[ContextSource]:
        """Retrieve conversation history from chat memory."""
        from app.models.chat import ChatMemory, ChatMessage
        from sqlalchemy import select

        sources = []

        # Recent messages
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())

        if messages:
            content = "\n".join(
                f"{'Foydalanuvchi' if m.role == 'user' else 'AI'}: {m.content[:300]}"
                for m in reversed(messages)
            )
            sources.append(ContextSource(
                source_type="memory",
                content=content,
                priority=PRIORITY_MEMORY,
                relevance_score=0.6,
                token_estimate=len(content) // CHARS_PER_TOKEN,
            ))

        return sources

    async def _retrieve_knowledge_graph(
        self,
        company_id: uuid.UUID,
        query: str,
    ) -> list[ContextSource]:
        """Retrieve context from Knowledge Graph (if available)."""
        # Placeholder — KG integration point
        return []

    def _rank_sources(self, sources: list[ContextSource]) -> list[ContextSource]:
        """Rank sources by priority and relevance."""
        return sorted(sources, key=lambda s: (s.priority, -s.relevance_score))

    def _deduplicate(self, sources: list[ContextSource]) -> list[ContextSource]:
        """Remove near-duplicate content from sources."""
        seen_content: set[str] = set()
        unique = []
        for src in sources:
            # Simple dedup by first 200 chars
            key = src.content[:200].lower().strip()
            if key not in seen_content:
                seen_content.add(key)
                unique.append(src)
        return unique

    def _compress_to_limit(
        self,
        sources: list[ContextSource],
    ) -> tuple[list[ContextSource], int]:
        """Trim sources to fit within token budget."""
        remaining = self.max_context_tokens
        included = []
        total = 0

        for src in sources:
            tokens = src.token_estimate or (len(src.content) // CHARS_PER_TOKEN)
            if tokens <= remaining:
                included.append(src)
                remaining -= tokens
                total += tokens
            else:
                # Truncate this source to fit
                if remaining > 100:
                    truncated_content = src.content[: remaining * CHARS_PER_TOKEN]
                    truncated_src = ContextSource(
                        source_type=src.source_type,
                        content=truncated_content,
                        priority=src.priority,
                        relevance_score=src.relevance_score,
                        metadata=src.metadata,
                        token_estimate=remaining,
                        source_id=src.source_id,
                        citations=src.citations,
                    )
                    included.append(truncated_src)
                    total += remaining
                break

        return included, total

    def format_context_for_llm(self, context: AssembledContext) -> str:
        """Format assembled context into a string for LLM consumption."""
        parts = []
        for src in context.sources:
            label = {
                "system": "System",
                "policy": "Security Policy",
                "permissions": "Permissions",
                "task": "Task",
                "document": "Document",
                "rag": "Knowledge Base",
                "memory": "Conversation History",
                "knowledge": "Knowledge Graph",
                "external": "External Source",
            }.get(src.source_type, src.source_type)

            parts.append(f"[{label}]\n{src.content}\n")

        return "\n---\n".join(parts)
