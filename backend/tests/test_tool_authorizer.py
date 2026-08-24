"""Tests for AI Tool Authorizer — verifies tool calls are properly gated."""
import uuid
import pytest
from app.security.core.tool_authorizer import tool_authorizer
from app.security.contracts.types import PolicyEffect, SecurityContext


def _ctx(role="user", perms=None, break_glass=False):
    return SecurityContext(
        user_id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        email="test@test.com",
        role_name=role,
        permissions=perms or [],
        is_break_glass_active=break_glass,
    )


class TestToolAuthorizer:
    def test_break_glass_allows_any_tool(self):
        ctx = _ctx(break_glass=True, role="user", perms=[])
        result = tool_authorizer.authorize_tool_call("search_knowledge_base", ctx)
        assert result.effect == PolicyEffect.ALLOW

    def test_admin_allows_any_tool(self):
        ctx = _ctx(role="admin", perms=[])
        result = tool_authorizer.authorize_tool_call("create_company_task", ctx)
        assert result.effect == PolicyEffect.ALLOW

    def test_agent_scope_blocks_unknown_tool(self):
        ctx = _ctx(perms=["document.read"])
        result = tool_authorizer.authorize_tool_call(
            "search_knowledge_base", ctx, agent_allowed_tools=["create_company_task"]
        )
        assert result.effect == PolicyEffect.DENY
        assert "scope" in result.reason.lower() or "not permitted" in result.reason.lower()

    def test_agent_scope_allows_known_tool(self):
        ctx = _ctx(perms=["document.read"])
        result = tool_authorizer.authorize_tool_call(
            "search_knowledge_base", ctx, agent_allowed_tools=["search_knowledge_base"]
        )
        assert result.effect == PolicyEffect.ALLOW

    def test_missing_user_permission_denied(self):
        ctx = _ctx(role="user", perms=["chat.read"])  # Missing document.read
        result = tool_authorizer.authorize_tool_call("search_knowledge_base", ctx)
        assert result.effect == PolicyEffect.DENY

    def test_wildcard_permission_allows(self):
        ctx = _ctx(role="user", perms=["document.*"])
        result = tool_authorizer.authorize_tool_call("search_knowledge_base", ctx)
        assert result.effect == PolicyEffect.ALLOW

    def test_admin_manage_allows_all(self):
        ctx = _ctx(role="user", perms=["admin.manage"])
        result = tool_authorizer.authorize_tool_call("query_company_kpis", ctx)
        assert result.effect == PolicyEffect.ALLOW
