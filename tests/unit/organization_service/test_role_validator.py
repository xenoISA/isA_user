"""
Unit tests for organization role validator.

Exercises the canonical role taxonomy (`docs/guidance/role-taxonomy.md`,
tracked by epic #270) and its assignment matrix. Pure functions, no I/O.

Usage:
    pytest tests/unit/organization_service/test_role_validator.py -v
"""

import pytest

from microservices.organization_service.role_validator import (
    ORG_ADMIN_ROLES,
    ORG_USER_ROLES,
    VALID_ORG_ROLES,
    RoleAssignmentRule,
    can_assign_org_role,
    is_valid_org_role,
    sorted_valid_roles,
    violated_assignment_rule,
)

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Role-set constants
# ---------------------------------------------------------------------------


class TestRoleSets:
    """Canonical role sets match the taxonomy doc exactly."""

    def test_admin_roles_are_owner_and_admin(self):
        assert ORG_ADMIN_ROLES == frozenset({"owner", "admin"})

    def test_user_roles_are_member_viewer_guest(self):
        assert ORG_USER_ROLES == frozenset({"member", "viewer", "guest"})

    def test_valid_set_is_union(self):
        assert VALID_ORG_ROLES == ORG_ADMIN_ROLES | ORG_USER_ROLES

    def test_admin_and_user_sets_disjoint(self):
        assert not (ORG_ADMIN_ROLES & ORG_USER_ROLES)

    def test_sorted_list_is_stable(self):
        assert sorted_valid_roles() == ["owner", "admin", "member", "viewer", "guest"]


# ---------------------------------------------------------------------------
# is_valid_org_role
# ---------------------------------------------------------------------------


class TestIsValidOrgRole:
    @pytest.mark.parametrize(
        "role", ["owner", "admin", "member", "viewer", "guest"]
    )
    def test_accepts_canonical_roles(self, role):
        assert is_valid_org_role(role) is True

    @pytest.mark.parametrize(
        "role",
        [
            "super_admin",          # platform admin, not an org role
            "billing_admin",
            "product_admin",
            "support_admin",
            "compliance_admin",
            "service",              # authorization_service machine principal
            "editor",               # authorization_service enum, not an org role
            "consumer",              # future c-user role
            "Owner",                # case-sensitive
            "ADMIN",
            "",
            "   ",
            "unknown",
        ],
    )
    def test_rejects_non_org_strings(self, role):
        assert is_valid_org_role(role) is False

    @pytest.mark.parametrize("value", [None, 0, 1, 3.14, [], {}, object()])
    def test_rejects_non_string_types(self, value):
        assert is_valid_org_role(value) is False


# ---------------------------------------------------------------------------
# can_assign_org_role — full truth table
# ---------------------------------------------------------------------------

# Source of truth: role-taxonomy.md "Assignment rules".
# Rows: assigner role. Columns: assignee role. True = allowed.
_TRUTH_TABLE = {
    "owner":  {"owner": True,  "admin": True,  "member": True,  "viewer": True,  "guest": True},
    "admin":  {"owner": False, "admin": False, "member": True,  "viewer": True,  "guest": True},
    "member": {"owner": False, "admin": False, "member": False, "viewer": False, "guest": False},
    "viewer": {"owner": False, "admin": False, "member": False, "viewer": False, "guest": False},
    "guest":  {"owner": False, "admin": False, "member": False, "viewer": False, "guest": False},
}


class TestCanAssignOrgRoleTruthTable:
    """Full 5x5 matrix. If this table disagrees with role-taxonomy.md, fix
    the code — not the table."""

    @pytest.mark.parametrize(
        ("assigner", "assignee", "expected"),
        [
            (assigner, assignee, allowed)
            for assigner, row in _TRUTH_TABLE.items()
            for assignee, allowed in row.items()
        ],
    )
    def test_matrix(self, assigner, assignee, expected):
        assert can_assign_org_role(assigner, assignee) is expected

    def test_owner_can_assign_every_canonical_role(self):
        for role in sorted_valid_roles():
            assert can_assign_org_role("owner", role) is True

    def test_admin_cannot_assign_any_admin_tier(self):
        for role in ORG_ADMIN_ROLES:
            assert can_assign_org_role("admin", role) is False

    def test_admin_can_assign_every_user_tier(self):
        for role in ORG_USER_ROLES:
            assert can_assign_org_role("admin", role) is True

    @pytest.mark.parametrize("assigner", ["member", "viewer", "guest"])
    @pytest.mark.parametrize("assignee", ["owner", "admin", "member", "viewer", "guest"])
    def test_non_admin_cannot_assign_anything(self, assigner, assignee):
        assert can_assign_org_role(assigner, assignee) is False


class TestCanAssignOrgRoleDefensive:
    """Invalid inputs fail closed."""

    @pytest.mark.parametrize(
        "assigner",
        ["super_admin", "service", "", "UNKNOWN", None],
    )
    def test_unknown_assigner_is_rejected(self, assigner):
        assert can_assign_org_role(assigner, "member") is False

    @pytest.mark.parametrize(
        "assignee",
        ["super_admin", "service", "", "UNKNOWN", None],
    )
    def test_unknown_assignee_is_rejected(self, assignee):
        # Even owner cannot mint a non-org role.
        assert can_assign_org_role("owner", assignee) is False


# ---------------------------------------------------------------------------
# violated_assignment_rule — error classification
# ---------------------------------------------------------------------------


class TestViolatedAssignmentRule:
    def test_invalid_target_classified_first(self):
        assert violated_assignment_rule("owner", "super_admin") == (
            RoleAssignmentRule.INVALID_ROLE
        )

    def test_unknown_assigner_when_target_is_valid(self):
        assert violated_assignment_rule("super_admin", "member") == (
            RoleAssignmentRule.UNKNOWN_ASSIGNER_ROLE
        )

    def test_admin_escalating_to_admin(self):
        assert violated_assignment_rule("admin", "admin") == (
            RoleAssignmentRule.ADMIN_CANNOT_ASSIGN_ADMIN_OR_OWNER
        )

    def test_admin_escalating_to_owner(self):
        assert violated_assignment_rule("admin", "owner") == (
            RoleAssignmentRule.ADMIN_CANNOT_ASSIGN_ADMIN_OR_OWNER
        )

    @pytest.mark.parametrize("assigner", ["member", "viewer", "guest"])
    def test_non_admin_classified_as_non_admin(self, assigner):
        assert violated_assignment_rule(assigner, "member") == (
            RoleAssignmentRule.NON_ADMIN_CANNOT_ASSIGN
        )
