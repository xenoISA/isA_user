"""
Role Validator

Canonical role-taxonomy enforcement for authorization_service.

Encodes the unified role hierarchy defined in:
    docs/guidance/role-taxonomy.md

Until the shared `@isa/core` types (#272) land, this module is the source of
truth for role-string validation and scope-aware assignment rules inside
authorization_service.

Four archetypes (see role-taxonomy.md §"The four archetypes"):
    - Platform admin: super_admin, billing_admin, product_admin,
      support_admin, compliance_admin.
    - Org admin: owner, admin.
    - Org user: member, viewer, guest (guest is legacy, treated like viewer
      for new code).
    - c-user: consumer end-user of a consuming app — not directly assignable
      through isA_Console role management; tracked here only so callers can
      recognize the string.

The authorization_service-specific legacy role strings (`editor`, `service`)
are accepted as *aliases* during the transition:
    - `editor` is aliased onto `member` (see taxonomy table for
      `authorization_service.RoleEnum.editor` → Org user).
    - `service` is a machine principal, not a human archetype — it is
      recognized but cannot be assigned by any human role.

Assignment rules (org scope, see role-taxonomy.md):
    - `owner` may assign:  owner | admin | member | viewer | guest
    - `admin` may assign:  member | viewer | guest
    - `member | viewer | guest`: cannot assign any role
    - `service` (machine): cannot assign any role

Platform scope:
    - Only `super_admin` may assign platform-admin roles (see
      role-taxonomy.md §Platform admin: "Only super_admin can grant admin
      roles.").

App scope:
    - c-users are minted by the consuming app's signup flow (see
      role-taxonomy.md §c-user Lifecycle). Human admins inside
      isA_Console never hand out the `consumer` role; this module denies all
      such assignments.
"""
from __future__ import annotations

import logging
from typing import Literal, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical role strings — mirror docs/guidance/role-taxonomy.md tables.
# ---------------------------------------------------------------------------

PLATFORM_ADMIN_ROLES: Tuple[str, ...] = (
    "super_admin",
    "billing_admin",
    "product_admin",
    "support_admin",
    "compliance_admin",
)

ORG_ADMIN_ROLES: Tuple[str, ...] = ("owner", "admin")

# Canonical org-user roles. `guest` is legacy but still accepted per the
# taxonomy mapping table ("treated as viewer for new code").
ORG_USER_ROLES: Tuple[str, ...] = ("member", "viewer", "guest")

# c-user archetype — consumer end-user of a consuming app. Included for
# completeness; not assignable through this service.
APP_USER_ROLES: Tuple[str, ...] = ("consumer",)

# Machine-principal role — recognized but not human-assignable.
SERVICE_ROLES: Tuple[str, ...] = ("service",)

# Legacy `authorization_service.RoleEnum` alias → canonical role.
#   editor → member  (see taxonomy row: "editor — Org user; approx. member")
LEGACY_ORG_ROLE_ALIASES = {
    "editor": "member",
}

# Full set of canonical org-scope role strings (post-alias) that may appear
# on a role-assignment or permission-check payload.
_CANONICAL_ORG_ROLES: Tuple[str, ...] = tuple(set(
    ORG_ADMIN_ROLES + ORG_USER_ROLES
))

# Full set of strings *accepted* as org-scope role inputs (canonical +
# legacy aliases). Service / platform / app roles are excluded.
_ACCEPTED_ORG_ROLE_INPUTS: Tuple[str, ...] = tuple(set(
    _CANONICAL_ORG_ROLES + tuple(LEGACY_ORG_ROLE_ALIASES.keys())
))

Scope = Literal["platform", "organization", "app"]

# CanonicalRole is the union of every canonical role string recognized
# by the unified taxonomy (post-alias). `service` and `consumer` are
# included so callers can recognize them but they are never valid
# assignees from a human principal.
CanonicalRole = Literal[
    "super_admin",
    "billing_admin",
    "product_admin",
    "support_admin",
    "compliance_admin",
    "owner",
    "admin",
    "member",
    "viewer",
    "guest",
    "consumer",
    "service",
]


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def is_valid_platform_role(s: str) -> bool:
    """Return True if `s` is one of the five platform-admin roles."""
    if not isinstance(s, str):
        return False
    return s in PLATFORM_ADMIN_ROLES


def is_valid_org_role(s: str) -> bool:
    """
    Return True if `s` is a valid org-scope role input.

    Accepts canonical org roles (owner, admin, member, viewer, guest) and
    legacy aliases (editor). Rejects platform-admin roles, c-user roles,
    and the `service` machine principal — those are not legal on org-scope
    role-assignment endpoints.
    """
    if not isinstance(s, str):
        return False
    return s in _ACCEPTED_ORG_ROLE_INPUTS


def normalize_org_role(s: str) -> str:
    """
    Resolve legacy aliases to their canonical role string.

    Callers that want to persist only canonical strings should run every
    accepted role input through this helper. Raises ValueError for
    unknown inputs.
    """
    if not is_valid_org_role(s):
        raise ValueError(f"not a valid org role: {s!r}")
    return LEGACY_ORG_ROLE_ALIASES.get(s, s)


# ---------------------------------------------------------------------------
# Assignment rules
# ---------------------------------------------------------------------------

def _org_can_assign(assigner: str, assignee_canonical: str) -> bool:
    """
    Org-scope assignment lattice (see module docstring).

        owner  -> {owner, admin, member, viewer, guest}
        admin  -> {member, viewer, guest}
        member -> {}
        viewer -> {}
        guest  -> {}
    """
    if assigner == "owner":
        return assignee_canonical in {"owner", "admin", "member", "viewer", "guest"}
    if assigner == "admin":
        return assignee_canonical in {"member", "viewer", "guest"}
    # member / viewer / guest / anything else: no authority
    return False


def can_assign_role(
    assigner: str,
    assignee: str,
    scope: Scope,
) -> bool:
    """
    Return True iff `assigner` may grant `assignee` at the given `scope`.

    Rules are drawn from docs/guidance/role-taxonomy.md:

    Org scope:
        - owner                       -> any org role (owner, admin, member,
                                         viewer, guest).
        - admin                       -> member, viewer, guest.
        - member / viewer / guest     -> nothing.
        - service (machine principal) -> nothing.

    Platform scope:
        - super_admin                 -> any platform-admin role.
        - every other platform admin  -> nothing (role management is
                                         super_admin-only per taxonomy).

    App scope:
        - c-user roles (`consumer`) are minted by the consuming app's
          signup flow, not assigned through this service. Always denied.
    """
    # Normalize legacy aliases first so assigner/assignee compare uniformly.
    assigner_norm = LEGACY_ORG_ROLE_ALIASES.get(assigner, assigner) \
        if isinstance(assigner, str) else assigner
    assignee_norm = LEGACY_ORG_ROLE_ALIASES.get(assignee, assignee) \
        if isinstance(assignee, str) else assignee

    if not isinstance(assigner_norm, str) or not isinstance(assignee_norm, str):
        return False

    # Machine principals never grant human roles.
    if assigner_norm in SERVICE_ROLES:
        return False

    if scope == "organization":
        # Both sides must be org-scope canonical roles.
        if assignee_norm not in _CANONICAL_ORG_ROLES:
            return False
        if assigner_norm not in _CANONICAL_ORG_ROLES:
            return False
        return _org_can_assign(assigner_norm, assignee_norm)

    if scope == "platform":
        # Only super_admin grants platform-admin roles.
        if assignee_norm not in PLATFORM_ADMIN_ROLES:
            return False
        return assigner_norm == "super_admin"

    if scope == "app":
        # c-users are minted by the consuming app, not by this service.
        return False

    return False


# ---------------------------------------------------------------------------
# Denial logging helper
# ---------------------------------------------------------------------------

def log_assignment_denied(
    rule: str,
    assigner: str,
    assignee: str,
    scope: Scope,
) -> None:
    """
    Emit a structured warning line for a denied role assignment.

    Keeping this in one place guarantees every denial carries the same
    `extra` keys so log aggregators can filter on rule name.
    """
    logger.warning(
        "role assignment denied",
        extra={
            "rule": rule,
            "assigner": assigner,
            "assignee": assignee,
            "scope": scope,
        },
    )
