"""
Canonical role audit events — shared across services.

Every service that mutates a role (authorization_service,
organization_service, account_service) emits role.assigned or
role.revoked events through the NATS event bus via these helpers so the
payload shape stays identical across services. Downstream consumers
(audit_service, compliance reports, alerting) rely on the shape.

Taxonomy: docs/guidance/role-taxonomy.md
Tracked by: epic #270, story #280.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

ROLE_ASSIGNED = "role.assigned"
ROLE_REVOKED = "role.revoked"

RoleScope = Literal["platform", "organization", "app"]


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def build_role_assigned_event(
    *,
    actor_user_id: Optional[str],
    target_user_id: str,
    scope: RoleScope,
    new_role: str,
    old_role: Optional[str] = None,
    org_id: Optional[str] = None,
    app_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the canonical payload for a role.assigned event.

    Args:
        actor_user_id: Who granted the role. ``None`` for system-originated
            assignments (e.g. initial org owner on org creation).
        target_user_id: Who received the role.
        scope: ``'platform'`` | ``'organization'`` | ``'app'``.
        new_role: The role string just granted.
        old_role: The role the target held before this change (``None`` for a
            fresh assignment, some value when a role was promoted / changed).
        org_id: Required when ``scope == 'organization'``.
        app_id: Required when ``scope == 'app'`` (c-user registration).
        extra: Additional fields to merge in (permissions list, invite id, etc.).
            Must not collide with the canonical keys.
    """
    payload: Dict[str, Any] = {
        "actor_user_id": actor_user_id,
        "target_user_id": target_user_id,
        "scope": scope,
        "org_id": org_id,
        "app_id": app_id,
        "old_role": old_role,
        "new_role": new_role,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        overlap = set(payload).intersection(extra)
        if overlap:
            raise ValueError(
                f"extra may not override canonical keys: {sorted(overlap)}"
            )
        payload.update(extra)
    return payload


def build_role_revoked_event(
    *,
    actor_user_id: Optional[str],
    target_user_id: str,
    scope: RoleScope,
    old_role: str,
    org_id: Optional[str] = None,
    app_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the canonical payload for a role.revoked event.

    Mirrors :func:`build_role_assigned_event` but with ``new_role = None``
    — the role is no longer held by the target.
    """
    payload: Dict[str, Any] = {
        "actor_user_id": actor_user_id,
        "target_user_id": target_user_id,
        "scope": scope,
        "org_id": org_id,
        "app_id": app_id,
        "old_role": old_role,
        "new_role": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        overlap = set(payload).intersection(extra)
        if overlap:
            raise ValueError(
                f"extra may not override canonical keys: {sorted(overlap)}"
            )
        payload.update(extra)
    return payload
