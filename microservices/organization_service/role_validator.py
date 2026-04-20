"""
Organization role validator.

Validates org-scoped role strings and role-assignment permissions against the
canonical role taxonomy defined in ``docs/guidance/role-taxonomy.md`` and
tracked by epic #270.

Two archetypes live inside an organization:

* **Org admin** — ``owner`` (exactly one per org) and ``admin`` (multiple allowed).
  They can manage members, billing, and settings.
* **Org user** — ``member`` (read/write), ``viewer`` (read-only), and
  ``guest`` (legacy; treated as ``viewer`` for new code).

Assignment rules (``scope: organization``):

* ``owner`` can assign: ``owner | admin | member | viewer | guest``.
* ``admin`` can assign: ``member | viewer | guest``.
* ``member | viewer | guest`` cannot assign any role.

The ``service`` role from ``authorization_service.RoleEnum`` and the platform
admin roles (``super_admin`` etc.) are NOT org roles — this module rejects
them on every endpoint.

See also: ``docs/prd/organization_service.md`` and
``docs/prd/authorization_service.md``.
"""

from __future__ import annotations

from typing import FrozenSet, Set

# ----------------------------------------------------------------------------
# Canonical role constants
# ----------------------------------------------------------------------------

# Org-admin archetype — can manage other members.
ORG_ADMIN_ROLES: FrozenSet[str] = frozenset({"owner", "admin"})

# Org-user archetype — no administrative authority.
# ``guest`` is legacy and is treated as ``viewer`` for new code.
ORG_USER_ROLES: FrozenSet[str] = frozenset({"member", "viewer", "guest"})

# Combined set of every role string this service will accept on org endpoints.
VALID_ORG_ROLES: FrozenSet[str] = ORG_ADMIN_ROLES | ORG_USER_ROLES

# Assignment matrix: who each role is allowed to assign.
# Source of truth: role-taxonomy.md > "Assignment rules".
_ASSIGNMENT_MATRIX: dict[str, FrozenSet[str]] = {
    "owner": frozenset({"owner", "admin", "member", "viewer", "guest"}),
    "admin": frozenset({"member", "viewer", "guest"}),
    "member": frozenset(),
    "viewer": frozenset(),
    "guest": frozenset(),
}


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


def is_valid_org_role(role: str) -> bool:
    """Return True iff ``role`` is one of the canonical org role strings.

    Rejects empty strings, ``None``-like inputs, platform admin role strings,
    and the ``service`` machine principal. Matching is case-sensitive — the
    taxonomy stores all role strings in lowercase.
    """
    if not isinstance(role, str) or not role:
        return False
    return role in VALID_ORG_ROLES


def can_assign_org_role(assigner: str, assignee: str) -> bool:
    """Return True iff a member with role ``assigner`` may assign role ``assignee``.

    Both arguments must themselves be canonical org role strings — an invalid
    assigner or assignee always returns False (fail closed). Callers should
    first validate the target string with :func:`is_valid_org_role` so the
    400 vs 403 error paths stay distinct.
    """
    if not is_valid_org_role(assigner) or not is_valid_org_role(assignee):
        return False
    return assignee in _ASSIGNMENT_MATRIX[assigner]


def sorted_valid_roles() -> list[str]:
    """Stable, deterministic list of valid roles — useful for error payloads."""
    # Fixed order matches the taxonomy doc's presentation: admins first, then users.
    return ["owner", "admin", "member", "viewer", "guest"]


# ----------------------------------------------------------------------------
# Rule names — used in structured logs and error messages so downstream
# tooling can assert on a stable string.
# ----------------------------------------------------------------------------


class RoleAssignmentRule:
    """Named rules from the taxonomy. Exposed so log/error strings are stable."""

    INVALID_ROLE = "invalid_org_role"
    ADMIN_CANNOT_ASSIGN_ADMIN_OR_OWNER = "admin_cannot_assign_admin_or_owner"
    NON_ADMIN_CANNOT_ASSIGN = "non_admin_cannot_assign"
    UNKNOWN_ASSIGNER_ROLE = "unknown_assigner_role"


def violated_assignment_rule(assigner: str, assignee: str) -> str:
    """Classify *why* an assignment is rejected. Returns a RoleAssignmentRule constant.

    Intended for use after :func:`can_assign_org_role` has already returned False.
    """
    if not is_valid_org_role(assignee):
        return RoleAssignmentRule.INVALID_ROLE
    if not is_valid_org_role(assigner):
        return RoleAssignmentRule.UNKNOWN_ASSIGNER_ROLE
    if assigner == "admin" and assignee in ORG_ADMIN_ROLES:
        return RoleAssignmentRule.ADMIN_CANNOT_ASSIGN_ADMIN_OR_OWNER
    if assigner in ORG_USER_ROLES:
        return RoleAssignmentRule.NON_ADMIN_CANNOT_ASSIGN
    # Fallback — should never happen if the matrix and the helpers agree.
    return RoleAssignmentRule.UNKNOWN_ASSIGNER_ROLE


__all__ = [
    "ORG_ADMIN_ROLES",
    "ORG_USER_ROLES",
    "VALID_ORG_ROLES",
    "RoleAssignmentRule",
    "can_assign_org_role",
    "is_valid_org_role",
    "sorted_valid_roles",
    "violated_assignment_rule",
]
