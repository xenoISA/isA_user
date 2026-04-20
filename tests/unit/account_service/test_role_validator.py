"""
Unit tests for ``microservices.account_service.role_validator`` (#275).

Covers:
- ``is_valid_platform_role`` accepts the five canonical roles and rejects
  unknown strings, empty strings, None, and non-string inputs.
- ``can_assign_platform_role`` truth table:
    * super_admin + valid assignee_role  → True
    * scoped admin + valid assignee_role → False
    * empty/None assigner roles          → False
    * super_admin + unknown assignee_role → False (invalid role short-circuits)
- ``PLATFORM_ADMIN_ROLES`` is the canonical list from the taxonomy doc.
- ``models.ADMIN_ROLES`` is an alias for ``PLATFORM_ADMIN_ROLES``.

Pure function tests — no I/O, no mocks.
"""
import pytest

from microservices.account_service.role_validator import (
    PLATFORM_ADMIN_ROLES,
    can_assign_platform_role,
    is_valid_platform_role,
)

pytestmark = [pytest.mark.unit]


# =============================================================================
# PLATFORM_ADMIN_ROLES constant
# =============================================================================


class TestPlatformAdminRolesConstant:
    """The constant must match the taxonomy doc verbatim."""

    def test_exactly_five_canonical_roles(self):
        assert set(PLATFORM_ADMIN_ROLES) == {
            "super_admin",
            "billing_admin",
            "product_admin",
            "support_admin",
            "compliance_admin",
        }

    def test_models_alias_matches(self):
        """``models.ADMIN_ROLES`` must be an alias (same identity)."""
        from microservices.account_service.models import ADMIN_ROLES

        assert ADMIN_ROLES is PLATFORM_ADMIN_ROLES


# =============================================================================
# is_valid_platform_role
# =============================================================================


class TestIsValidPlatformRole:
    """Happy-path and reject-path coverage for the role-string check."""

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
    def test_canonical_roles_accepted(self, role):
        assert is_valid_platform_role(role) is True

    @pytest.mark.parametrize(
        "role",
        [
            "totally_made_up",
            "admin",
            "SUPER_ADMIN",  # case-sensitive
            "super-admin",  # hyphen instead of underscore
            "super_admin ",  # trailing whitespace
            " super_admin",  # leading whitespace
            "owner",  # org role, not platform
            "member",
            "viewer",
            "service",
            "consumer",
        ],
    )
    def test_unknown_strings_rejected(self, role):
        assert is_valid_platform_role(role) is False

    @pytest.mark.parametrize("bad", [None, "", 0, 1, [], {}, ("super_admin",)])
    def test_non_string_or_empty_rejected(self, bad):
        assert is_valid_platform_role(bad) is False


# =============================================================================
# can_assign_platform_role
# =============================================================================


class TestCanAssignPlatformRole:
    """Truth-table coverage for the assignment-authority check."""

    # --- super_admin assigner → allowed for any valid target role ---

    @pytest.mark.parametrize("target", PLATFORM_ADMIN_ROLES)
    def test_super_admin_can_assign_any_valid_role(self, target):
        assert can_assign_platform_role(["super_admin"], target) is True

    def test_super_admin_with_additional_roles_still_allowed(self):
        """Extra scoped roles don't strip the super_admin capability."""
        assigner = ["super_admin", "billing_admin", "compliance_admin"]
        assert can_assign_platform_role(assigner, "product_admin") is True

    # --- scoped admin assigners → denied even for valid target roles ---

    @pytest.mark.parametrize(
        "scoped_role",
        ["billing_admin", "product_admin", "support_admin", "compliance_admin"],
    )
    def test_scoped_admin_cannot_assign(self, scoped_role):
        assert can_assign_platform_role([scoped_role], "billing_admin") is False

    def test_multiple_scoped_roles_cannot_compose_into_super(self):
        """Holding every scoped role still doesn't grant assignment authority."""
        assigner = [
            "billing_admin",
            "product_admin",
            "support_admin",
            "compliance_admin",
        ]
        assert can_assign_platform_role(assigner, "support_admin") is False

    # --- empty / None assigners → denied ---

    @pytest.mark.parametrize("assigner", [None, [], (), set()])
    def test_empty_assigner_denied(self, assigner):
        assert can_assign_platform_role(assigner, "support_admin") is False

    # --- invalid target role short-circuits even for super_admin ---

    @pytest.mark.parametrize(
        "target",
        ["totally_made_up", "", "SUPER_ADMIN", "owner", None],
    )
    def test_invalid_target_role_rejected_even_for_super_admin(self, target):
        assert can_assign_platform_role(["super_admin"], target) is False

    # --- accepts any iterable, not just list ---

    def test_tuple_assigner_accepted(self):
        assert can_assign_platform_role(("super_admin",), "billing_admin") is True

    def test_set_assigner_accepted(self):
        assert can_assign_platform_role({"super_admin"}, "billing_admin") is True

    def test_non_iterable_assigner_rejected(self):
        """A bare int (not iterable) must not crash; it should just deny."""
        assert can_assign_platform_role(42, "super_admin") is False
