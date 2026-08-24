"""Tests for DocumentPermissionService — document-level access control."""
import json
import uuid
import pytest
from unittest.mock import MagicMock
from app.security.core.document_permissions import document_permissions
from app.security.contracts.types import PolicyEffect, SecurityContext, SensitivityLevel


def _ctx(role="user", perms=None, break_glass=False, company_id=None, dept_id=None):
    cid = company_id or uuid.uuid4()
    return SecurityContext(
        user_id=uuid.uuid4(),
        company_id=cid,
        email="test@test.com",
        role_name=role,
        permissions=perms or [],
        department_id=dept_id,
        is_break_glass_active=break_glass,
    )


def _doc(company_id=None, sensitivity="INTERNAL", access_level="company",
         uploaded_by=None, department_id=None, allowed_users=None):
    doc = MagicMock()
    doc.company_id = company_id or uuid.uuid4()
    doc.sensitivity_level = sensitivity
    doc.access_level = access_level
    doc.uploaded_by = uploaded_by
    doc.department_id = department_id
    doc.allowed_user_ids = json.dumps(allowed_users) if allowed_users else None
    return doc


class TestTenantIsolation:
    def test_cross_tenant_denied(self):
        ctx = _ctx()
        doc = _doc(company_id=uuid.uuid4())  # Different tenant
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.DENY


class TestBreakGlass:
    def test_break_glass_allows(self):
        ctx = _ctx(break_glass=True)
        doc = _doc(company_id=ctx.company_id)
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.ALLOW


class TestAdminAccess:
    @pytest.mark.parametrize("role", ["super_admin", "admin", "Owner"])
    def test_admin_bypasses(self, role):
        ctx = _ctx(role=role)
        doc = _doc(company_id=ctx.company_id, sensitivity="RESTRICTED")
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.ALLOW


class TestOwnerAccess:
    def test_owner_always_allowed(self):
        uid = uuid.uuid4()
        ctx = _ctx()
        ctx.user_id = uid
        doc = _doc(company_id=ctx.company_id, uploaded_by=uid)
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.ALLOW


class TestSensitivityLevel:
    def test_restricted_needs_clearance(self):
        ctx = _ctx(role="user", perms=["document.read"])
        doc = _doc(company_id=ctx.company_id, sensitivity="RESTRICTED")
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.DENY

    def test_restricted_with_clearance(self):
        ctx = _ctx(role="user", perms=["document.read", "sensitivity.restricted.read"])
        doc = _doc(company_id=ctx.company_id, sensitivity="RESTRICTED")
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.ALLOW

    def test_confidential_needs_role(self):
        ctx = _ctx(role="user", perms=["document.read"])
        doc = _doc(company_id=ctx.company_id, sensitivity="CONFIDENTIAL")
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.DENY

    def test_confidential_manager_allowed(self):
        ctx = _ctx(role="manager", perms=["document.read"])
        doc = _doc(company_id=ctx.company_id, sensitivity="CONFIDENTIAL")
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.ALLOW


class TestAccessLevel:
    def test_team_access_allowed_for_member(self):
        uid = uuid.uuid4()
        ctx = _ctx(perms=["document.read"])
        ctx.user_id = uid
        doc = _doc(company_id=ctx.company_id, access_level="team", allowed_users=[str(uid)])
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.ALLOW

    def test_team_access_denied_for_non_member(self):
        ctx = _ctx(perms=["document.read"])
        doc = _doc(company_id=ctx.company_id, access_level="team",
                   allowed_users=[str(uuid.uuid4())])  # Different user
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.DENY

    def test_restricted_access_denied_for_non_member(self):
        ctx = _ctx(perms=["document.read"])
        doc = _doc(company_id=ctx.company_id, access_level="restricted",
                   allowed_users=[str(uuid.uuid4())])
        result = document_permissions.check_document_access(ctx, doc)
        assert result.effect == PolicyEffect.DENY


class TestFilterDocuments:
    def test_filter_removes_inaccessible(self):
        tenant = uuid.uuid4()
        ctx = _ctx(company_id=tenant, perms=["document.read"])
        accessible_doc = _doc(company_id=tenant, access_level="company")
        inaccessible_doc = _doc(company_id=uuid.uuid4())  # Different tenant
        result = document_permissions.filter_documents_by_access(ctx, [accessible_doc, inaccessible_doc])
        assert len(result) == 1
        assert result[0] == accessible_doc

    def test_classifications_endpoint(self):
        classifications = document_permissions.get_document_classifications()
        assert "sensitivity_levels" in classifications
        assert "access_levels" in classifications
        assert len(classifications["sensitivity_levels"]) == 4
