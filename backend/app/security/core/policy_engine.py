import json
from typing import Any, Dict, List, Optional
import uuid

from app.security.contracts.types import (
    PolicyEffect,
    PolicyEvaluationResult,
    SecurityContext,
    SensitivityLevel,
)


class PolicyEngine:
    """Enterprise ABAC and RBAC Policy Evaluation Engine."""

    def evaluate_resource_access(
        self,
        context: SecurityContext,
        action: str,  # e.g., "document.read", "document.write", "memory.read", "agent.execute"
        resource_type: str,  # "document", "memory", "report", "workflow", "integration"
        resource_tenant_id: uuid.UUID,
        resource_sensitivity: str = SensitivityLevel.INTERNAL.value,
        resource_department_id: Optional[str] = None,
        resource_project_id: Optional[str] = None,
        resource_owner_id: Optional[uuid.UUID] = None,
    ) -> PolicyEvaluationResult:
        """Evaluates whether the given SecurityContext is permitted to perform action on resource."""

        # 1. Multi-Tenant Boundary: Absolute Isolation
        if context.company_id != resource_tenant_id:
            return PolicyEvaluationResult(
                effect=PolicyEffect.DENY,
                reason="Cross-tenant access strictly forbidden.",
                matched_policy="TENANT_ISOLATION_RULE",
            )

        # 2. Break-Glass Override: Active emergency session allows access with audit flag
        if context.is_break_glass_active:
            return PolicyEvaluationResult(
                effect=PolicyEffect.ALLOW,
                reason="Access granted under active Emergency Break-Glass session.",
                matched_policy="BREAK_GLASS_OVERRIDE",
            )

        # 3. Super Admin Role
        if context.role_name in ["super_admin", "admin", "Owner"]:
            return PolicyEvaluationResult(
                effect=PolicyEffect.ALLOW,
                reason="Tenant administrator role access.",
                matched_policy="ADMIN_FULL_ACCESS",
            )

        # 4. Resource Ownership check (Owner can always read/write their own created items)
        if resource_owner_id and context.user_id == resource_owner_id:
            return PolicyEvaluationResult(
                effect=PolicyEffect.ALLOW,
                reason="Resource owner access granted.",
                matched_policy="OWNER_ACCESS_RULE",
            )

        # 5. Permission Code Check (RBAC)
        if action and context.permissions and action not in context.permissions:
            # Check wildcard module permission e.g., "document.*" or "admin.manage"
            module_name = action.split(".")[0] if "." in action else action
            wildcard = f"{module_name}.*"
            if wildcard not in context.permissions and "admin.manage" not in context.permissions:
                return PolicyEvaluationResult(
                    effect=PolicyEffect.DENY,
                    reason=f"User lacks required permission '{action}'.",
                    matched_policy="RBAC_PERMISSION_CHECK",
                )

        # 6. Sensitivity Level Check (ABAC)
        sens_upper = (resource_sensitivity or SensitivityLevel.INTERNAL.value).upper()
        if sens_upper == SensitivityLevel.RESTRICTED.value:
            if "sensitivity.restricted.read" not in context.permissions:
                return PolicyEvaluationResult(
                    effect=PolicyEffect.DENY,
                    reason="Access denied to RESTRICTED resource without explicit sensitivity clearance.",
                    matched_policy="RESTRICTED_SENSITIVITY_CLEARANCE",
                )
        elif sens_upper == SensitivityLevel.CONFIDENTIAL.value:
            if context.role_name not in ["manager", "director", "admin", "super_admin", "Owner"]:
                if "sensitivity.confidential.read" not in context.permissions:
                    return PolicyEvaluationResult(
                        effect=PolicyEffect.DENY,
                        reason="Access denied to CONFIDENTIAL resource for current role.",
                        matched_policy="CONFIDENTIAL_ROLE_CHECK",
                    )

        # 7. Departmental Boundary Check (ABAC)
        if resource_department_id and context.department_id:
            if resource_department_id != context.department_id and context.role_name not in ["admin", "super_admin", "executive"]:
                if "department.cross.read" not in context.permissions:
                    return PolicyEvaluationResult(
                        effect=PolicyEffect.DENY,
                        reason="Cross-department resource access denied.",
                        matched_policy="DEPARTMENT_ISOLATION_POLICY",
                    )

        # 8. Project Membership Check (ABAC)
        if resource_project_id and context.project_ids:
            if resource_project_id not in context.project_ids and context.role_name not in ["admin", "super_admin", "executive"]:
                if "project.cross.read" not in context.permissions:
                    return PolicyEvaluationResult(
                        effect=PolicyEffect.DENY,
                        reason="User is not a member of the required project.",
                        matched_policy="PROJECT_MEMBERSHIP_POLICY",
                    )

        # Default Allow when all security checks pass
        return PolicyEvaluationResult(
            effect=PolicyEffect.ALLOW,
            reason="All RBAC and ABAC policies satisfied.",
            matched_policy="DEFAULT_PERMISSIVE_IN_TENANT",
        )


policy_engine = PolicyEngine()
