"""
Canonical platform-admin role validation for account_service.

This module owns ``PLATFORM_ADMIN_ROLES`` — the single source of truth for the
five named platform-admin role strings inside account_service. See
``docs/guidance/role-taxonomy.md`` for the full archetype definition
(platform-admin / org-admin / org-user / c-user) and the permission matrix.
Epic #270 tracks taxonomy alignment across services; this story is #275.

Rules encoded here (see the taxonomy doc, "Platform admin" section):

- Valid platform-admin role strings are exactly the five in
  ``PLATFORM_ADMIN_ROLES``. Any other string is invalid.
- Only ``super_admin`` can grant (or revoke) platform-admin roles. A scoped
  admin (``billing_admin``, ``product_admin``, ``support_admin``,
  ``compliance_admin``) cannot promote anyone — they have domain-scoped
  authority, not assignment authority.

Note on duplication: ``auth_service/models.py`` carries a parallel
``ADMIN_ROLES`` constant with the same five strings. Unifying the two lives
into one shared module is cross-service refactoring beyond #275 and is tracked
as a follow-up.
"""

from __future__ import annotations

from typing import Iterable, List, Optional


# Canonical list of platform-admin roles. Order is significant only for stable
# display / error messages — semantics are set membership.
PLATFORM_ADMIN_ROLES: List[str] = [
    "super_admin",
    "billing_admin",
    "product_admin",
    "support_admin",
    "compliance_admin",
]

# Role allowed to grant / revoke platform-admin roles.
_ASSIGNER_ROLE = "super_admin"


def is_valid_platform_role(role: str) -> bool:
    """Return True if ``role`` is one of the five canonical platform-admin roles.

    Args:
        role: A role string from a JWT claim, request body, or stored record.

    Returns:
        ``True`` iff ``role`` appears verbatim in ``PLATFORM_ADMIN_ROLES``.
        ``None``, non-string, and empty inputs return ``False`` rather than
        raising — callers doing structural validation should check shape first.
    """
    if not isinstance(role, str) or not role:
        return False
    return role in PLATFORM_ADMIN_ROLES


def can_assign_platform_role(
    assigner_admin_roles: Optional[Iterable[str]],
    assignee_role: str,
) -> bool:
    """Return True if the assigner is authorised to grant ``assignee_role``.

    Encodes the rule "only super_admin can grant platform admin roles" from the
    role taxonomy. A scoped admin trying to promote a user (or themselves) is
    rejected, as is anyone without admin roles at all.

    Args:
        assigner_admin_roles: The caller's admin_roles claim (list / tuple /
            None). A caller without this claim has no assignment authority.
        assignee_role: The role string the caller wants to assign. Must itself
            be a valid platform-admin role for this check to succeed — we do
            not let super_admin assign a typo'd role string.

    Returns:
        ``True`` only when *both* (a) ``assignee_role`` is a valid platform
        role and (b) ``assigner_admin_roles`` contains ``super_admin``.
    """
    if not is_valid_platform_role(assignee_role):
        return False
    if not assigner_admin_roles:
        return False
    # Tolerate list, tuple, set, generator.
    try:
        return _ASSIGNER_ROLE in set(assigner_admin_roles)
    except TypeError:
        return False


__all__ = [
    "PLATFORM_ADMIN_ROLES",
    "is_valid_platform_role",
    "can_assign_platform_role",
]
