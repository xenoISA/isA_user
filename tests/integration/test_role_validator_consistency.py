"""
Cross-service role-validator consistency tests (L3 integration).

Each of authorization_service, organization_service, and account_service
keeps its own Python copy of the role taxonomy (they cannot import from
``@isa/core``, which is TypeScript). This test suite asserts the three
copies answer the same question the same way for every scope they
share.

If this test fails, you probably updated one service's role handling
without updating the others. The fix is to bring all three into sync
with ``docs/guidance/role-taxonomy.md`` — that doc is the single source
of truth.

Taxonomy: docs/guidance/role-taxonomy.md  ·  Tracked by epic #270.
"""

from typing import Set

import pytest

from microservices.account_service import role_validator as acct
from microservices.authorization_service import role_validator as authz
from microservices.organization_service import role_validator as org


# ----------------------------------------------------------------------
# Role-set parity
# ----------------------------------------------------------------------


def _as_set(values) -> Set[str]:
    """Normalize tuple/list/frozenset into a set for comparison."""
    return set(values)


class TestRoleSetsAgree:
    def test_platform_admin_roles_match_between_authz_and_account(self):
        assert _as_set(authz.PLATFORM_ADMIN_ROLES) == _as_set(acct.PLATFORM_ADMIN_ROLES)

    def test_org_admin_roles_match_between_authz_and_org(self):
        assert _as_set(authz.ORG_ADMIN_ROLES) == _as_set(org.ORG_ADMIN_ROLES)

    def test_org_user_roles_match_between_authz_and_org(self):
        assert _as_set(authz.ORG_USER_ROLES) == _as_set(org.ORG_USER_ROLES)

    def test_canonical_platform_admin_role_names(self):
        # Pin the exact names to catch accidental additions/removals that
        # pass the above parity checks if both files change together but
        # drift from the taxonomy spec.
        expected = {
            "super_admin",
            "billing_admin",
            "product_admin",
            "support_admin",
            "compliance_admin",
        }
        assert _as_set(authz.PLATFORM_ADMIN_ROLES) == expected
        assert _as_set(acct.PLATFORM_ADMIN_ROLES) == expected

    def test_canonical_org_role_names(self):
        assert _as_set(authz.ORG_ADMIN_ROLES) == {"owner", "admin"}
        assert _as_set(authz.ORG_USER_ROLES) == {"member", "viewer", "guest"}
        assert _as_set(org.ORG_ADMIN_ROLES) == {"owner", "admin"}
        assert _as_set(org.ORG_USER_ROLES) == {"member", "viewer", "guest"}


# ----------------------------------------------------------------------
# is_valid_* parity
# ----------------------------------------------------------------------


PLATFORM_ROLE_SAMPLES = [
    "super_admin", "billing_admin", "product_admin", "support_admin",
    "compliance_admin",
    "owner", "admin", "member", "viewer", "guest",  # org roles — should NOT be valid platform
    "", "nonsense", "SUPER_ADMIN",  # invalid
]

ORG_ROLE_SAMPLES = [
    "owner", "admin", "member", "viewer", "guest",
    "super_admin", "billing_admin",  # platform roles — should NOT be valid org
    "", "nonsense", "OWNER",  # invalid
]


class TestIsValidPlatformRoleAgrees:
    @pytest.mark.parametrize("role", PLATFORM_ROLE_SAMPLES)
    def test_authz_and_account_agree(self, role):
        assert authz.is_valid_platform_role(role) == acct.is_valid_platform_role(role)


class TestIsValidOrgRoleAgrees:
    @pytest.mark.parametrize("role", ORG_ROLE_SAMPLES)
    def test_authz_and_org_agree(self, role):
        assert authz.is_valid_org_role(role) == org.is_valid_org_role(role)


# ----------------------------------------------------------------------
# Org-scope can_assign parity
# ----------------------------------------------------------------------
# authz exposes can_assign_role(assigner, assignee, scope) — pass scope="organization".
# org exposes can_assign_org_role(assigner, assignee).
# For every (assigner, assignee) pair across the org lattice, they must agree.

ORG_ROLES_FOR_MATRIX = ["owner", "admin", "member", "viewer", "guest"]

ORG_ASSIGNMENT_MATRIX = [
    (a, e)
    for a in ORG_ROLES_FOR_MATRIX
    for e in ORG_ROLES_FOR_MATRIX
]


class TestOrgAssignmentRulesAgree:
    @pytest.mark.parametrize("assigner,assignee", ORG_ASSIGNMENT_MATRIX)
    def test_authz_and_org_agree_on_org_scope(self, assigner, assignee):
        authz_decision = authz.can_assign_role(assigner, assignee, scope="organization")
        org_decision = org.can_assign_org_role(assigner, assignee)
        assert authz_decision == org_decision, (
            f"disagreement on ({assigner} -> {assignee}): "
            f"authz={authz_decision}, org={org_decision}"
        )

    def test_owner_can_assign_every_org_role(self):
        for assignee in ORG_ROLES_FOR_MATRIX:
            assert authz.can_assign_role("owner", assignee, scope="organization") is True
            assert org.can_assign_org_role("owner", assignee) is True

    def test_admin_cannot_assign_owner_or_admin(self):
        # Historical note: org_service's legacy rule also blocks admin→admin.
        # We assert the canonical rule — admin can assign {member, viewer, guest} only.
        assert authz.can_assign_role("admin", "owner", scope="organization") is False
        assert org.can_assign_org_role("admin", "owner") is False
        assert authz.can_assign_role("admin", "admin", scope="organization") is False
        assert org.can_assign_org_role("admin", "admin") is False
        for lower in ("member", "viewer", "guest"):
            assert authz.can_assign_role("admin", lower, scope="organization") is True
            assert org.can_assign_org_role("admin", lower) is True

    @pytest.mark.parametrize("assigner", ["member", "viewer", "guest"])
    def test_non_admin_roles_cannot_assign_anything(self, assigner):
        for assignee in ORG_ROLES_FOR_MATRIX:
            assert authz.can_assign_role(assigner, assignee, scope="organization") is False
            assert org.can_assign_org_role(assigner, assignee) is False


# ----------------------------------------------------------------------
# Platform-scope can_assign parity
# ----------------------------------------------------------------------
# authz exposes can_assign_role(..., scope="platform") — accepts a single
# assigner role string. account exposes can_assign_platform_role(assigner_admin_roles: list, assignee).
# Reconcile: a caller with a single admin_role in a list should match the authz scalar decision.


class TestPlatformAssignmentRulesAgree:
    @pytest.mark.parametrize("assigner", list(authz.PLATFORM_ADMIN_ROLES))
    @pytest.mark.parametrize("assignee", list(authz.PLATFORM_ADMIN_ROLES))
    def test_authz_and_account_agree_on_platform_scope(self, assigner, assignee):
        authz_decision = authz.can_assign_role(assigner, assignee, scope="platform")
        acct_decision = acct.can_assign_platform_role([assigner], assignee)
        assert authz_decision == acct_decision, (
            f"platform-scope disagreement on ({assigner} -> {assignee}): "
            f"authz={authz_decision}, account={acct_decision}"
        )

    def test_only_super_admin_can_grant_platform_roles(self):
        for assignee in authz.PLATFORM_ADMIN_ROLES:
            assert authz.can_assign_role("super_admin", assignee, scope="platform") is True
            assert acct.can_assign_platform_role(["super_admin"], assignee) is True
        for assigner in ("billing_admin", "product_admin", "support_admin", "compliance_admin"):
            for assignee in authz.PLATFORM_ADMIN_ROLES:
                assert authz.can_assign_role(assigner, assignee, scope="platform") is False
                assert acct.can_assign_platform_role([assigner], assignee) is False
