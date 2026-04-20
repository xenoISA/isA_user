"""
Unit tests for authorization_service.role_validator.

Covers the canonical role-taxonomy vocabulary, validator predicates, and
the can_assign_role lattice described in
docs/guidance/role-taxonomy.md.

Issue: xenoISA/isA_user#273 (parent epic #270).
"""
from __future__ import annotations

import logging
import os
import sys

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from microservices.authorization_service.role_validator import (
    APP_USER_ROLES,
    LEGACY_ORG_ROLE_ALIASES,
    ORG_ADMIN_ROLES,
    ORG_USER_ROLES,
    PLATFORM_ADMIN_ROLES,
    SERVICE_ROLES,
    can_assign_role,
    is_valid_org_role,
    is_valid_platform_role,
    log_assignment_denied,
    normalize_org_role,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestCanonicalConstants:
    """The public role-string tuples match the taxonomy doc exactly."""

    def test_platform_admin_roles(self):
        assert set(PLATFORM_ADMIN_ROLES) == {
            "super_admin",
            "billing_admin",
            "product_admin",
            "support_admin",
            "compliance_admin",
        }

    def test_org_admin_roles(self):
        assert set(ORG_ADMIN_ROLES) == {"owner", "admin"}

    def test_org_user_roles(self):
        assert set(ORG_USER_ROLES) == {"member", "viewer", "guest"}

    def test_app_user_roles(self):
        assert set(APP_USER_ROLES) == {"consumer"}

    def test_service_roles(self):
        assert set(SERVICE_ROLES) == {"service"}

    def test_legacy_editor_aliased_to_member(self):
        assert LEGACY_ORG_ROLE_ALIASES["editor"] == "member"


# ---------------------------------------------------------------------------
# is_valid_platform_role
# ---------------------------------------------------------------------------

class TestIsValidPlatformRole:
    @pytest.mark.parametrize(
        "role",
        [
            "super_admin",
            "billing_admin",
            "product_admin",
            "support_admin",
            "compliance_admin",
        ],
    )
    def test_accepts_every_platform_admin(self, role):
        assert is_valid_platform_role(role) is True

    @pytest.mark.parametrize(
        "role",
        ["owner", "admin", "member", "viewer", "guest", "editor", "consumer", "service"],
    )
    def test_rejects_non_platform_roles(self, role):
        assert is_valid_platform_role(role) is False

    @pytest.mark.parametrize("bogus", ["", "SUPER_ADMIN", "random", None, 42])
    def test_rejects_garbage(self, bogus):
        assert is_valid_platform_role(bogus) is False


# ---------------------------------------------------------------------------
# is_valid_org_role
# ---------------------------------------------------------------------------

class TestIsValidOrgRole:
    @pytest.mark.parametrize(
        "role", ["owner", "admin", "member", "viewer", "guest", "editor"]
    )
    def test_accepts_canonical_and_legacy(self, role):
        assert is_valid_org_role(role) is True

    @pytest.mark.parametrize(
        "role",
        ["super_admin", "billing_admin", "consumer", "service", "", "VIEWER", None, 7],
    )
    def test_rejects_non_org_inputs(self, role):
        assert is_valid_org_role(role) is False


# ---------------------------------------------------------------------------
# normalize_org_role
# ---------------------------------------------------------------------------

class TestNormalizeOrgRole:
    def test_editor_normalizes_to_member(self):
        assert normalize_org_role("editor") == "member"

    @pytest.mark.parametrize(
        "role", ["owner", "admin", "member", "viewer", "guest"]
    )
    def test_canonical_roles_are_identity(self, role):
        assert normalize_org_role(role) == role

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            normalize_org_role("super_admin")


# ---------------------------------------------------------------------------
# can_assign_role — full truth table for org scope
# ---------------------------------------------------------------------------

# All org-scope role strings recognized as input (canonical + legacy aliases)
ORG_SCOPE_INPUTS = ["owner", "admin", "member", "viewer", "guest", "editor"]

# Expected assignment lattice, expressed in canonical form:
#   owner  -> {owner, admin, member, viewer, guest}
#   admin  -> {member, viewer, guest}
#   member -> {}
#   viewer -> {}
#   guest  -> {}
# "editor" is aliased to "member" on both sides before the lattice fires.
ORG_EXPECTED: dict[str, set[str]] = {
    "owner": {"owner", "admin", "member", "viewer", "guest"},
    "admin": {"member", "viewer", "guest"},
    "member": set(),
    "viewer": set(),
    "guest": set(),
    "editor": set(),  # aliased to member ⇒ same empty set
}


def _canon(role: str) -> str:
    return LEGACY_ORG_ROLE_ALIASES.get(role, role)


@pytest.mark.parametrize("assigner", ORG_SCOPE_INPUTS)
@pytest.mark.parametrize("assignee", ORG_SCOPE_INPUTS)
def test_can_assign_role_org_truth_table(assigner, assignee):
    """
    Full truth table: (assigner × assignee) at organization scope.

    Asserts the outcome matches the canonical lattice after alias
    normalization on both sides.
    """
    expected = _canon(assignee) in ORG_EXPECTED[assigner]
    assert can_assign_role(assigner, assignee, "organization") is expected


def test_service_principal_never_assigns_any_org_role():
    for assignee in ORG_SCOPE_INPUTS:
        assert can_assign_role("service", assignee, "organization") is False


def test_org_admin_cannot_assign_owner():
    """Explicit callout from taxonomy: admin's ceiling is below owner."""
    assert can_assign_role("admin", "owner", "organization") is False


def test_member_cannot_assign_anything():
    for assignee in ORG_SCOPE_INPUTS:
        assert can_assign_role("member", assignee, "organization") is False


def test_platform_role_rejected_at_org_scope():
    for assigner in ("owner", "admin"):
        assert can_assign_role(assigner, "super_admin", "organization") is False


# ---------------------------------------------------------------------------
# can_assign_role — platform scope
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "assignee",
    PLATFORM_ADMIN_ROLES,
)
def test_super_admin_can_assign_any_platform_role(assignee):
    assert can_assign_role("super_admin", assignee, "platform") is True


@pytest.mark.parametrize(
    "assigner",
    [r for r in PLATFORM_ADMIN_ROLES if r != "super_admin"],
)
def test_non_super_platform_admin_cannot_assign(assigner):
    for assignee in PLATFORM_ADMIN_ROLES:
        assert can_assign_role(assigner, assignee, "platform") is False


def test_org_admin_cannot_assign_platform_role():
    for assigner in ("owner", "admin"):
        assert (
            can_assign_role(assigner, "super_admin", "platform") is False
        )


def test_platform_scope_rejects_non_platform_assignee():
    assert can_assign_role("super_admin", "owner", "platform") is False


# ---------------------------------------------------------------------------
# can_assign_role — app scope
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "assigner",
    ["owner", "admin", "super_admin", "service", "member"],
)
def test_app_scope_never_assignable(assigner):
    """
    c-user roles are provisioned by the consuming app's signup flow, never
    through this service — see role-taxonomy.md §c-user Lifecycle.
    """
    assert can_assign_role(assigner, "consumer", "app") is False


# ---------------------------------------------------------------------------
# log_assignment_denied
# ---------------------------------------------------------------------------

def test_log_assignment_denied_structured(caplog):
    """
    Emits a WARNING with the canonical `extra` keys so aggregators can
    filter by rule name.
    """
    with caplog.at_level(logging.WARNING):
        log_assignment_denied(
            rule="assigner_not_authorized",
            assigner="usr_admin_1",
            assignee="usr_target_2",
            scope="organization",
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    assert record.message == "role assignment denied"
    assert record.rule == "assigner_not_authorized"
    assert record.assigner == "usr_admin_1"
    assert record.assignee == "usr_target_2"
    assert record.scope == "organization"
