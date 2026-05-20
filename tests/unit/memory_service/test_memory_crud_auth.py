"""Tests for memory CRUD API auth + ownership enforcement (#485).

The CRUD endpoints (GET list / GET one / PUT / DELETE) already existed but
trusted ``user_id`` as a query param. #485 hardens them: the user_id now comes
from ``require_auth_or_internal_service`` and a per-user ownership check
(``_enforce_memory_owner``) rejects cross-user access.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from microservices.memory_service.main import _enforce_memory_owner


class TestEnforceMemoryOwner:
    def test_authed_user_accessing_own_memories(self):
        # Requested == authed → allowed, returns that user.
        assert _enforce_memory_owner("usr_1", "usr_1") == "usr_1"

    def test_missing_requested_defaults_to_authed(self):
        # No explicit user_id → defaults to the authenticated identity.
        assert _enforce_memory_owner("usr_1", None) == "usr_1"

    def test_authed_user_accessing_other_user_is_forbidden(self):
        with pytest.raises(HTTPException) as exc:
            _enforce_memory_owner("usr_1", "usr_2")
        assert exc.value.status_code == 403
        assert "your own memories" in exc.value.detail

    def test_internal_service_may_target_any_user(self):
        # Service-to-service: internal marker can act on any user.
        assert _enforce_memory_owner("internal-service", "usr_99") == "usr_99"

    def test_internal_service_without_target_returns_marker(self):
        # Internal call with no explicit target → marker passes through.
        assert _enforce_memory_owner("internal-service", None) == "internal-service"
