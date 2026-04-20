"""
Unit tests for core.role_events payload builders.

Ensures every service that emits role audit events produces an
identical canonical shape (epic #270, story #280).
"""

from datetime import datetime, timezone

import pytest

from core.role_events import (
    ROLE_ASSIGNED,
    ROLE_REVOKED,
    build_role_assigned_event,
    build_role_revoked_event,
)


class TestRoleAssignedPayload:
    def test_canonical_fields_present(self):
        ev = build_role_assigned_event(
            actor_user_id="u-actor",
            target_user_id="u-target",
            scope="organization",
            new_role="admin",
            org_id="org-1",
        )
        for key in (
            "actor_user_id", "target_user_id", "scope", "org_id",
            "app_id", "old_role", "new_role", "timestamp",
        ):
            assert key in ev, f"missing canonical key {key}"

    def test_new_role_set_and_old_role_none_by_default(self):
        ev = build_role_assigned_event(
            actor_user_id=None,
            target_user_id="u-target",
            scope="platform",
            new_role="billing_admin",
        )
        assert ev["new_role"] == "billing_admin"
        assert ev["old_role"] is None

    def test_actor_may_be_none_for_system_assignments(self):
        ev = build_role_assigned_event(
            actor_user_id=None,
            target_user_id="u-target",
            scope="organization",
            new_role="owner",
            org_id="org-1",
        )
        assert ev["actor_user_id"] is None

    def test_timestamp_is_iso_utc(self):
        ev = build_role_assigned_event(
            actor_user_id="u-a",
            target_user_id="u-b",
            scope="organization",
            new_role="member",
            org_id="org-1",
        )
        parsed = datetime.fromisoformat(ev["timestamp"])
        # tzinfo is UTC — may be datetime.timezone.utc or a compatible alias.
        assert parsed.tzinfo is not None
        assert parsed.tzinfo.utcoffset(parsed) == timezone.utc.utcoffset(parsed)

    def test_extra_merged(self):
        ev = build_role_assigned_event(
            actor_user_id="u-a",
            target_user_id="u-b",
            scope="organization",
            new_role="member",
            org_id="org-1",
            extra={"permissions": ["read", "write"], "invite_id": "inv-9"},
        )
        assert ev["permissions"] == ["read", "write"]
        assert ev["invite_id"] == "inv-9"

    @pytest.mark.parametrize("key", ["scope", "new_role", "target_user_id"])
    def test_extra_cannot_override_canonical_keys(self, key):
        with pytest.raises(ValueError) as info:
            build_role_assigned_event(
                actor_user_id="u-a",
                target_user_id="u-b",
                scope="organization",
                new_role="member",
                org_id="org-1",
                extra={key: "malicious"},
            )
        assert key in str(info.value)

    def test_app_scope_carries_app_id(self):
        ev = build_role_assigned_event(
            actor_user_id="u-org-admin",
            target_user_id="u-consumer",
            scope="app",
            new_role="consumer",
            org_id="org-owning-app",
            app_id="atlas",
        )
        assert ev["scope"] == "app"
        assert ev["app_id"] == "atlas"


class TestRoleRevokedPayload:
    def test_new_role_is_always_none(self):
        ev = build_role_revoked_event(
            actor_user_id="u-a",
            target_user_id="u-b",
            scope="organization",
            old_role="admin",
            org_id="org-1",
        )
        assert ev["new_role"] is None
        assert ev["old_role"] == "admin"

    def test_platform_revoke(self):
        ev = build_role_revoked_event(
            actor_user_id="u-super",
            target_user_id="u-target",
            scope="platform",
            old_role="compliance_admin",
        )
        assert ev["scope"] == "platform"
        assert ev["old_role"] == "compliance_admin"
        assert ev["new_role"] is None
        assert ev["org_id"] is None

    def test_extra_merged(self):
        ev = build_role_revoked_event(
            actor_user_id="u-a",
            target_user_id="u-b",
            scope="organization",
            old_role="member",
            org_id="org-1",
            extra={"reason": "suspended"},
        )
        assert ev["reason"] == "suspended"

    def test_extra_cannot_override_canonical_keys(self):
        with pytest.raises(ValueError):
            build_role_revoked_event(
                actor_user_id="u-a",
                target_user_id="u-b",
                scope="organization",
                old_role="member",
                org_id="org-1",
                extra={"old_role": "bogus"},
            )


class TestEventTypeConstants:
    def test_names_are_stable(self):
        # Other services import these strings. Changing them is a breaking
        # change for downstream consumers (audit_service, compliance exports).
        assert ROLE_ASSIGNED == "role.assigned"
        assert ROLE_REVOKED == "role.revoked"
