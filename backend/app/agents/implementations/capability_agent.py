"""Shared capability agent helpers using services + Cognitive connectors only."""

from __future__ import annotations

import json
from typing import Any

from app.agents.contracts.types import (
    AgentContext,
    AgentPlan,
    AgentRequest,
    AgentResult,
    AgentStatus,
    MemoryBundle,
)
from app.agents.interfaces.base_agent import BaseAgent
from app.utils.exceptions import AppException, ValidationException


class CapabilityAgent(BaseAgent):
    """Base implementation wiring Cognitive connectors and AIService."""

    system_prompt: str = "Sen Nexora AI agentisan. Korxona kontekstida aniq va foydali javob ber."
    default_tools: list[str] = []
    required_permission: str | None = None

    async def validate(self, request: AgentRequest) -> None:
        if not request.input or not request.input.strip():
            raise ValidationException(detail="Agent input bo'sh bo'lishi mumkin emas")
        if self.required_permission and request.identity.permissions:
            perms = set(request.identity.permissions)
            if (
                self.required_permission not in perms
                and "agent.execute" not in perms
                and "admin" not in perms
                and "*" not in perms
            ):
                raise AppException(
                    status_code=403,
                    error="Forbidden",
                    detail=f"'{self.required_permission}' ruxsati talab qilinadi",
                )

    async def build_context(self, request: AgentRequest) -> AgentContext:
        builder = self.require_service("context_builder")
        return await builder.build(request, config={})

    async def retrieve_memory(self, context: AgentContext) -> MemoryBundle:
        connector = self.require_service("memory_connector")
        return await connector.retrieve(context, context.request.input, top_k=5)

    async def plan(self, context: AgentContext, memory: MemoryBundle) -> AgentPlan:
        planning = self.require_service("planning_engine")
        frame = context.extras.get("context_frame")
        if frame is None:
            from app.cognitive.contracts.frames import ContextFrame

            frame = ContextFrame(
                company_id=context.company_id,
                user_id=context.user_id,
                permissions=context.permissions,
                conversation_id=context.request.chat_id,
                active_document_ids=list(context.request.document_ids),
                project_id=context.project_id,
                department_id=context.department_id,
            )
        from app.cognitive.contracts.frames import EvidencePack

        evidence = EvidencePack(
            query=memory.query or context.request.input,
            memory_items=memory.items,
            graph_summary=memory.graph_summary,
            timeline=memory.timeline,
            decisions=memory.decisions,
        )
        raw = await planning.plan(
            frame=frame,
            evidence=evidence,
            agent_key=self.agent_key,
            intent=context.request.input,
        )
        tools = list(raw.get("tools") or self.default_tools)
        return AgentPlan(
            steps=list(raw.get("steps") or []),
            tools=tools,
            rationale=str(raw.get("rationale") or ""),
            requires_async=bool(raw.get("requires_async")),
        )

    def _compose_prompt(self, context: AgentContext, memory: MemoryBundle, plan: AgentPlan) -> str:
        evidence_lines = []
        for item in memory.items[:8]:
            content = str(item.get("content") or "")[:500]
            evidence_lines.append(f"- ({item.get('type')}) {content}")
        evidence_block = "\n".join(evidence_lines) if evidence_lines else "- (evidence yok)"
        docs = ", ".join(d.get("filename", "") for d in context.active_documents) or "yok"
        conversation = context.conversation_summary or "yok"
        parts = [
            f"Agent: {self.display_name}",
            f"Reja: {plan.rationale}",
            f"Faol hujjatlar: {docs}",
            f"Suhbat: {conversation}",
            "",
            "Dalillar:",
            evidence_block,
            "",
            "Foydalanuvchi sorovi:",
            context.request.input,
        ]
        return "\n".join(parts)

    async def execute(
        self,
        context: AgentContext,
        memory: MemoryBundle,
        plan: AgentPlan,
    ) -> AgentResult:
        """Default execute path: AIService chat with evidence-augmented prompt.

        Agents that need tool-calling can override and use the existing ReAct executor.
        """
        ai_service = self.require_service("ai_service")
        provider = context.config.get("provider")
        model = context.config.get("model")
        temperature = float(context.config.get("temperature") or 0.4)
        max_tokens = int(context.config.get("max_tokens") or 4096)
        system_prompt = context.config.get("system_prompt") or self.system_prompt

        user_content = self._compose_prompt(context, memory, plan)
        response = await ai_service.chat(
            provider=provider,
            model=model,
            messages=[{"role": "user", "content": user_content}],
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        citations = [
            {
                "document_id": item.get("document_id"),
                "type": item.get("type"),
            }
            for item in memory.items
            if item.get("document_id")
        ]
        return AgentResult(
            success=True,
            output=response.get("content", ""),
            agent_key=self.agent_key,
            status=AgentStatus.COMPLETED,
            plan=plan,
            citations=citations,
            steps=[{"type": "llm", "provider": provider, "model": model}],
            token_used=int(response.get("token_count") or 0),
            metadata={"tools_planned": plan.tools},
        )

    async def execute_with_tools(
        self,
        context: AgentContext,
        memory: MemoryBundle,
        plan: AgentPlan,
    ) -> AgentResult:
        """Optional ReAct path reusing existing app.ai.agents.AgentExecutor."""
        from app.ai.agents.agent_executor import AgentExecutor
        from app.ai.agents.tools import ToolExecutionContext

        # Tool layer currently receives db via ToolExecutionContext (legacy).
        # Capability agents themselves do not query repositories directly.
        ai_service = self.require_service("ai_service")
        db = ai_service.db
        tool_ctx = ToolExecutionContext(
            db=db,
            company_id=context.company_id,
            user_id=context.user_id,
        )
        executor = AgentExecutor(db)
        system_prompt = context.config.get("system_prompt") or self.system_prompt
        enriched = self._compose_prompt(context, memory, plan)
        res = await executor.run(
            provider=context.config.get("provider") or "gemini",
            model=context.config.get("model") or "gemini-2.5-flash",
            system_prompt=system_prompt,
            user_input=enriched,
            context=tool_ctx,
            allowed_tools=plan.tools or self.default_tools or None,
        )
        return AgentResult(
            success=True,
            output=res.output,
            agent_key=self.agent_key,
            status=AgentStatus.COMPLETED,
            plan=plan,
            steps=res.steps,
            token_used=res.total_tokens,
            duration_ms=res.duration_ms,
        )

    async def save_memory(self, context: AgentContext, result: AgentResult) -> list[str]:
        connector = self.require_service("memory_connector")
        ref = await connector.save_episode(
            context,
            self.agent_key,
            result.output,
            metadata={"citations": result.citations},
        )
        return [ref]

    async def publish_events(self, context: AgentContext, result: AgentResult) -> None:
        publisher = self.require_service("event_publisher")
        await publisher.publish_completed(context, result)

    async def return_response(self, result: AgentResult) -> AgentResult:
        if result.output and not result.output.endswith("\n"):
            result.metadata.setdefault("trimmed", False)
        return result
