"""Tests for the ABAC/RBAC Policy Engine."""
import uuid
import pytest
from app.security.core.policy_engine import policy_engine
from app.security.contracts.types import (
    PolicyEffect,
    SecurityContext,
    SensitivityLevel,
)


def _make_context(
    role_name="user",
    permissions=None,
    company_id=None,
    department_id=None,
    project_ids=None,
    is_break_glass=False,
) -> SecurityContext:
    return SecurityContext(
        user_id=uuid.uuid4(),
        company_id=company_id or uuid.uuid4(),
        email="test@example.com",
        role_name=role_name,
        permissions=permissions or [],
        department_id=department_id,
        project_ids=project_ids or [],
        is_break_glass_active=is_break_glass,
    )


class TestTenantIsolation:
    """Tests for absolute multi-tenant boundary enforcement."""

    def test_cross_tenant_access_denied(self):
        ctx = _make_context(company_id=uuid.uuid4())
        other_tenant = uuid.uuid4()
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=other_tenant,
        )
        assert result.effect == PolicyEffect.DENY
        assert "tenant" in result.reason.lower() or "Tenant" in result.reason

    def test_same_tenant_access_proceeds(self):
        tenant = uuid.uuid4()
        ctx = _make_context(company_id=tenant, role_name="admin")
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=tenant,
        )
        assert result.effect == PolicyEffect.ALLOW


class TestBreakGlass:
    """Tests for break-glass emergency override."""

    def test_break_glass_overrides_all(self):
        ctx = _make_context(is_break_glass=True, role_name="user", permissions=[])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.delete", resource_type="document",
            resource_tenant_id=ctx.company_id,
        )
        assert result.effect == PolicyEffect.ALLOW


class TestAdminAccess:
    """Tests for admin role full access."""

    @pytest.mark.parametrize("role", ["super_admin", "admin", "Owner"])
    def test_admin_bypasses_rbac(self, role):
        ctx = _make_context(role_name=role, permissions=[])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
        )
        assert result.effect == PolicyEffect.ALLOW


class TestOwnerAccess:
    """Tests for resource owner access."""

    def test_owner_can_access_own_resource(self):
        owner_id = uuid.uuid4()
        ctx = _make_context(role_name="user", permissions=[], company_id=uuid.uuid4())
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.write", resource_type="document",
            resource_tenant_id=ctx.company_id, resource_owner_id=owner_id,
        )
        # ctx.user_id != owner_id, so it should proceed to permission check
        # Owner match is when ctx.user_id == resource_owner_id
        ctx2 = _make_context(role_name="user", permissions=[])
        ctx2.user_id = owner_id
        result2 = policy_engine.evaluate_resource_access(
            context=ctx2, action="document.write", resource_type="document",
            resource_tenant_id=ctx2.company_id, resource_owner_id=owner_id,
        )
        assert result2.effect == PolicyEffect.ALLOW


class TestRBACPermissions:
    """Tests for RBAC permission code checking."""

    def test_exact_permission_match(self):
        ctx = _make_context(role_name="user", permissions=["document.read"])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
        )
        assert result.effect == PolicyEffect.ALLOW

    def test_wildcard_permission_match(self):
        ctx = _make_context(role_name="user", permissions=["document.*"])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
        )
        assert result.effect == PolicyEffect.ALLOW

    def test_missing_permission_denied(self):
        ctx = _make_context(role_name="user", permissions=["chat.read"])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.delete", resource_type="document",
            resource_tenant_id=ctx.company_id,
        )
        assert result.effect == PolicyEffect.DENY


class TestSensitivityABAC:
    """Tests for sensitivity-level ABAC checks."""

    def test_restricted_requires_clearance(self):
        ctx = _make_context(role_name="user", permissions=["document.read"])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
            resource_sensitivity=SensitivityLevel.RESTRICTED.value,
        )
        assert result.effect == PolicyEffect.DENY

    def test_restricted_with_clearance_allowed(self):
        ctx = _make_context(role_name="user", permissions=["document.read", "sensitivity.restricted.read"])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
            resource_sensitivity=SensitivityLevel.RESTRICTED.value,
        )
        assert result.effect == PolicyEffect.ALLOW

    def test_confidential_requires_manager_plus(self):
        ctx = _make_context(role_name="user", permissions=["document.read"])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
            resource_sensitivity=SensitivityLevel.CONFIDENTIAL.value,
        )
        assert result.effect == PolicyEffect.DENY

    def test_confidential_manager_allowed(self):
        ctx = _make_context(role_name="manager", permissions=["document.read"])
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
            resource_sensitivity=SensitivityLevel.CONFIDENTIAL.value,
        )
        assert result.effect == PolicyEffect.ALLOW


class TestDepartmentIsolation:
    """Tests for department-level ABAC checks."""

    def test_cross_department_denied(self):
        ctx = _make_context(role_name="user", permissions=["document.read"], department_id="dept-1")
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
            resource_department_id="dept-2",
        )
        assert result.effect == PolicyEffect.DENY

    def test_same_department_allowed(self):
        ctx = _make_context(role_name="user", permissions=["document.read"], department_id="dept-1")
        result = policy_engine.evaluate_resource_access(
            context=ctx, action="document.read", resource_type="document",
            resource_tenant_id=ctx.company_id,
            resource_department_id="dept-1",
        )
        assert result.effect == PolicyEffect.ALLOW
