import pytest
from app.ai.agents.tools import ToolRegistry, RAGSearchTool, CreateTaskTool, SendNotificationTool


def test_tool_registry():
    registry = ToolRegistry()
    assert registry.get_tool("search_knowledge_base") is not None
    assert registry.get_tool("create_company_task") is not None
    assert registry.get_tool("send_notification") is not None

    prompt = registry.get_tools_prompt()
    assert "search_knowledge_base" in prompt
    assert "create_company_task" in prompt
