from typing import List, Optional
import uuid

from app.security.contracts.types import PolicyEffect, PolicyEvaluationResult, SecurityContext


class ToolAuthorizer:
    """Gatekeeper authorizing tool calls executed by AI agents."""

    TOOL_PERMISSION_MAP = {
        "search_knowledge_base": "document.read",
        "search_document_intelligence": "document.read",
        "get_document_intelligence": "document.read",
        "get_document_knowledge_graph": "document.read",
        "create_company_task": "task.create",
        "send_notification": "notification.send",
        "execute_enterprise_connector": "integration.execute",
        "execute_integration_action": "integration.execute",
        "query_company_kpis": "bi.read",
        "get_business_insights": "bi.read",
        "generate_executive_summary": "bi.read",
        "detect_operational_risks": "bi.read",
    }

    def authorize_tool_call(
        self,
        tool_name: str,
        context: SecurityContext,
        agent_allowed_tools: Optional[List[str]] = None,
    ) -> PolicyEvaluationResult:
        """Verifies agent and user permissions before executing an AI tool."""

        # 1. Break-Glass override
        if context.is_break_glass_active:
            return PolicyEvaluationResult(
                effect=PolicyEffect.ALLOW,
                reason="Tool authorized under active Break-Glass session.",
                matched_policy="BREAK_GLASS_TOOL_OVERRIDE",
            )

        # 2. Agent Scope Check
        if agent_allowed_tools is not None and tool_name not in agent_allowed_tools:
            return PolicyEvaluationResult(
                effect=PolicyEffect.DENY,
                reason=f"Tool '{tool_name}' is not permitted in the active agent's tool capability scope.",
                matched_policy="AGENT_TOOL_SCOPE_CHECK",
            )

        # 3. Super Admin bypass
        if context.role_name in ["super_admin", "admin", "Owner"]:
            return PolicyEvaluationResult(
                effect=PolicyEffect.ALLOW,
                reason="Administrator role authorized for all tools.",
                matched_policy="ADMIN_TOOL_PERMISSIVE",
            )

        # 4. User Permission Check
        required_perm = self.TOOL_PERMISSION_MAP.get(tool_name)
        if required_perm and context.permissions:
            module = required_perm.split(".")[0]
            if required_perm not in context.permissions and f"{module}.*" not in context.permissions and "admin.manage" not in context.permissions:
                return PolicyEvaluationResult(
                    effect=PolicyEffect.DENY,
                    reason=f"Current user lacks required permission '{required_perm}' for tool '{tool_name}'.",
                    matched_policy="USER_TOOL_RBAC_CHECK",
                )

        return PolicyEvaluationResult(
            effect=PolicyEffect.ALLOW,
            reason="Tool authorization granted.",
            matched_policy="DEFAULT_TOOL_ALLOW",
        )


tool_authorizer = ToolAuthorizer()
