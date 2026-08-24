import json
import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.security.contracts.types import (
    PolicyEffect,
    PolicyEvaluationResult,
    SecurityContext,
    SensitivityLevel,
)


class DocumentPermissionService:
    """Enforces document-level access control including sensitivity and per-user permissions."""

    def check_document_access(
        self,
        context: SecurityContext,
        document: Document,
        action: str = "document.read",
    ) -> PolicyEvaluationResult:
        """
        Check if the security context can perform the given action on the document.
        """
        # 1. Tenant isolation — absolute
        if context.company_id != document.company_id:
            return PolicyEvaluationResult(
                effect=PolicyEffect.DENY,
                reason="Cross-tenant document access forbidden.",
                matched_policy="TENANT_ISOLATION",
            )

        # 2. Break-glass override
        if context.is_break_glass_active:
            return PolicyEvaluationResult(
                effect=PolicyEffect.ALLOW,
                reason="Break-glass emergency access.",
                matched_policy="BREAK_GLASS_OVERRIDE",
            )

        # 3. Admin roles bypass
        if context.role_name in ["super_admin", "admin", "Owner"]:
            return PolicyEvaluationResult(
                effect=PolicyEffect.ALLOW,
                reason="Admin role full access.",
                matched_policy="ADMIN_FULL_ACCESS",
            )

        # 4. Owner always has access
        if document.uploaded_by and document.uploaded_by == context.user_id:
            return PolicyEvaluationResult(
                effect=PolicyEffect.ALLOW,
                reason="Document owner access.",
                matched_policy="DOCUMENT_OWNER",
            )

        # 5. Access level check
        access_level = document.access_level or "owner"

        if access_level == "company":
            # All company members can access
            pass  # Allow below

        elif access_level == "department":
            # Check department membership
            if document.department_id and context.department_id:
                if str(document.department_id) != context.department_id:
                    return PolicyEvaluationResult(
                        effect=PolicyEffect.DENY,
                        reason="Cross-department document access denied.",
                        matched_policy="DEPARTMENT_DOCUMENT_ISOLATION",
                    )

        elif access_level == "team":
            # Check if user is in allowed_user_ids
            allowed = self._get_allowed_users(document)
            if allowed and str(context.user_id) not in allowed:
                return PolicyEvaluationResult(
                    effect=PolicyEffect.DENY,
                    reason="User is not in the allowed team for this document.",
                    matched_policy="TEAM_DOCUMENT_ISOLATION",
                )

        elif access_level == "restricted":
            # Must have explicit permission or be in allowed list
            allowed = self._get_allowed_users(document)
            if allowed and str(context.user_id) not in allowed:
                if "sensitivity.restricted.read" not in context.permissions:
                    return PolicyEvaluationResult(
                        effect=PolicyEffect.DENY,
                        reason="RESTRICTED document requires explicit access.",
                        matched_policy="RESTRICTED_DOCUMENT_ACCESS",
                    )

        # 6. Sensitivity level check
        sensitivity = (document.sensitivity_level or "INTERNAL").upper()
        if sensitivity == SensitivityLevel.RESTRICTED.value:
            if "sensitivity.restricted.read" not in context.permissions:
                return PolicyEvaluationResult(
                    effect=PolicyEffect.DENY,
                    reason="RESTRICTED sensitivity clearance required.",
                    matched_policy="SENSITIVITY_RESTRICTED",
                )
        elif sensitivity == SensitivityLevel.CONFIDENTIAL.value:
            if context.role_name not in ["manager", "director", "admin", "super_admin", "Owner"]:
                if "sensitivity.confidential.read" not in context.permissions:
                    return PolicyEvaluationResult(
                        effect=PolicyEffect.DENY,
                        reason="CONFIDENTIAL sensitivity clearance required.",
                        matched_policy="SENSITIVITY_CONFIDENTIAL",
                    )

        # 7. RBAC permission check
        if action and context.permissions:
            if action not in context.permissions:
                module = action.split(".")[0]
                if f"{module}.*" not in context.permissions and "admin.manage" not in context.permissions:
                    return PolicyEvaluationResult(
                        effect=PolicyEffect.DENY,
                        reason=f"Missing permission '{action}'.",
                        matched_policy="RBAC_PERMISSION_CHECK",
                    )

        return PolicyEvaluationResult(
            effect=PolicyEffect.ALLOW,
            reason="All document access policies satisfied.",
            matched_policy="DOCUMENT_ACCESS_ALLOW",
        )

    def filter_documents_by_access(
        self,
        context: SecurityContext,
        documents: List[Document],
    ) -> List[Document]:
        """Filters a list of documents, returning only those the context can access."""
        accessible = []
        for doc in documents:
            result = self.check_document_access(context, doc)
            if result.effect == PolicyEffect.ALLOW:
                accessible.append(doc)
        return accessible

    def _get_allowed_users(self, document: Document) -> List[str]:
        """Parses the allowed_user_ids JSON field."""
        if not document.allowed_user_ids:
            return []
        try:
            return json.loads(document.allowed_user_ids)
        except (json.JSONDecodeError, TypeError):
            return []

    def get_document_classifications(self) -> dict:
        """Returns available document classifications for the UI."""
        return {
            "sensitivity_levels": [
                {"value": "PUBLIC", "label": "Ommaviy", "description": "Hammaga ko'rinadi"},
                {"value": "INTERNAL", "label": "Ichki", "description": "Tashkilot ichida"},
                {"value": "CONFIDENTIAL", "label": "Maxfiy", "description": "Faqat ruxsat etilgan shaxslarga"},
                {"value": "RESTRICTED", "label": "Qat'iyan maxfiy", "description": "Faqat ma'lum bir shaxslarga"},
            ],
            "access_levels": [
                {"value": "owner", "label": "Faqat egasi"},
                {"value": "team", "label": "Jamoa"},
                {"value": "department", "label": "Bo'lim"},
                {"value": "company", "label": "Butun tashkilot"},
                {"value": "restricted", "label": "Cheklangan"},
            ],
        }


document_permissions = DocumentPermissionService()
