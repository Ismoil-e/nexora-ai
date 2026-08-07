"""Unit tests for the AI Agent Framework registry and lifecycle contracts."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.bootstrap import bootstrap_agents
from app.agents.contracts.types import (
    AgentContext,
    AgentIdentity,
    AgentPlan,
    AgentRequest,
    AgentResult,
    AgentStatus,
    MemoryBundle,
)
from app.agents.core.registry import AgentRegistry
from app.agents.implementations.default_agents import DEFAULT_AGENT_CLASSES, ChatAgent
from app.agents.interfaces.base_agent import BaseAgent


def test_bootstrap_registers_all_default_agents():
    registry = AgentRegistry()
    bootstrap_agents(registry)
    keys = registry.keys()
    expected = {cls.agent_key for cls in DEFAULT_AGENT_CLASSES}
    assert expected.issubset(set(keys))
    assert len(keys) >= 9


def test_registry_is_pluggable_without_changing_existing_agents():
    registry = AgentRegistry()
    bootstrap_agents(registry)

    class CustomAgent(BaseAgent):
        agent_key = "custom_future"
        display_name = "Custom"
        description = "Future module agent"
        capabilities = ["custom"]

        async def validate(self, request: AgentRequest) -> None:
            return None

        async def build_context(self, request: AgentRequest) -> AgentContext:
            return AgentContext(
                request=request,
                company_id=request.identity.company_id,
                user_id=request.identity.user_id,
            )

        async def retrieve_memory(self, context: AgentContext) -> MemoryBundle:
            return MemoryBundle()

        async def plan(self, context: AgentContext, memory: MemoryBundle) -> AgentPlan:
            return AgentPlan(rationale="custom")

        async def execute(
            self,
            context: AgentContext,
            memory: MemoryBundle,
            plan: AgentPlan,
        ) -> AgentResult:
            return AgentResult(success=True, output="ok", agent_key=self.agent_key)

    registry.register(CustomAgent)
    assert registry.has("custom_future")
    assert registry.has("chat")
    agent = registry.create("custom_future")
    assert agent.agent_key == "custom_future"


def test_chat_agent_validate_rejects_empty_input():
    async def _run():
        agent = ChatAgent()
        await agent.initialize({})
        request = AgentRequest(
            agent_key="chat",
            input="   ",
            identity=AgentIdentity(user_id=uuid.uuid4(), company_id=uuid.uuid4()),
        )
        with pytest.raises(Exception):
            await agent.validate(request)

    asyncio.run(_run())


def test_chat_agent_lifecycle_with_mocked_services():
    async def _run():
        agent = ChatAgent()
        identity = AgentIdentity(user_id=uuid.uuid4(), company_id=uuid.uuid4())
        request = AgentRequest(agent_key="chat", input="Salom", identity=identity)

        context_builder = MagicMock()
        context_builder.build = AsyncMock(
            return_value=AgentContext(
                request=request,
                company_id=identity.company_id,
                user_id=identity.user_id,
                extras={},
            )
        )
        memory_connector = MagicMock()
        memory_connector.retrieve = AsyncMock(return_value=MemoryBundle(items=[], query="Salom"))
        memory_connector.save_episode = AsyncMock(return_value="episode:1")

        planning_engine = MagicMock()
        planning_engine.plan = AsyncMock(
            return_value={
                "steps": [{"step": 1, "action": "answer"}],
                "tools": [],
                "rationale": "simple",
                "requires_async": False,
            }
        )

        ai_service = MagicMock()
        ai_service.chat = AsyncMock(return_value={"content": "Salom!", "token_count": 12})
        ai_service.db = MagicMock()

        event_publisher = MagicMock()
        event_publisher.publish_completed = AsyncMock()

        await agent.initialize({
            "context_builder": context_builder,
            "memory_connector": memory_connector,
            "planning_engine": planning_engine,
            "ai_service": ai_service,
            "event_publisher": event_publisher,
        })

        await agent.validate(request)
        context = await agent.build_context(request)
        memory = await agent.retrieve_memory(context)
        plan = await agent.plan(context, memory)
        result = await agent.execute(context, memory, plan)
        result = await agent.post_process(context, result)
        refs = await agent.save_memory(context, result)
        await agent.publish_events(context, result)
        final = await agent.return_response(result)

        assert final.success is True
        assert final.output == "Salom!"
        assert final.status == AgentStatus.COMPLETED
        assert refs == ["episode:1"]
        ai_service.chat.assert_awaited()

    asyncio.run(_run())
