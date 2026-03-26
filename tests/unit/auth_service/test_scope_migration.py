"""
Unit tests for scope migration from a2a.* to mcp:* format.

Tests:
- _normalize_scopes maps a2a.* scopes to mcp:* equivalents
- _normalize_scopes preserves already-mcp scopes
- _normalize_scopes handles mixed old/new scopes
- Default client scopes use mcp:* format
- Well-known metadata advertises only mcp:* scopes

Covers: Phase 2 of OAuth RFC 8707 migration
"""

import os
import sys
import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

from microservices.auth_service.auth_service import _normalize_scopes, _SCOPE_MIGRATION_MAP

pytestmark = pytest.mark.unit


class TestNormalizeScopes:
    """Test the _normalize_scopes backward-compatibility mapper."""

    def test_maps_a2a_invoke_to_mcp_tools_execute(self):
        result = _normalize_scopes({"a2a.invoke"})
        assert result == {"mcp:tools:execute"}

    def test_maps_a2a_tasks_read(self):
        result = _normalize_scopes({"a2a.tasks.read"})
        assert result == {"mcp:tasks:read"}

    def test_maps_a2a_tasks_cancel(self):
        result = _normalize_scopes({"a2a.tasks.cancel"})
        assert result == {"mcp:tasks:cancel"}

    def test_preserves_mcp_scopes(self):
        scopes = {"mcp:tools:read", "mcp:tools:execute", "mcp:prompts:read"}
        result = _normalize_scopes(scopes)
        assert result == scopes

    def test_mixed_old_and_new_normalizes_correctly(self):
        scopes = {"a2a.invoke", "mcp:tools:read", "a2a.tasks.read"}
        result = _normalize_scopes(scopes)
        assert result == {"mcp:tools:execute", "mcp:tools:read", "mcp:tasks:read"}

    def test_empty_set(self):
        result = _normalize_scopes(set())
        assert result == set()

    def test_unknown_scope_passes_through(self):
        result = _normalize_scopes({"custom:scope"})
        assert result == {"custom:scope"}


class TestScopeMigrationMap:
    """Verify the migration map covers all a2a.* scopes."""

    def test_all_a2a_scopes_mapped(self):
        expected_keys = {"a2a.invoke", "a2a.tasks.read", "a2a.tasks.cancel"}
        assert set(_SCOPE_MIGRATION_MAP.keys()) == expected_keys

    def test_all_values_are_mcp_format(self):
        for value in _SCOPE_MIGRATION_MAP.values():
            assert value.startswith("mcp:"), f"Expected mcp:* format, got {value}"


class TestDefaultClientScopes:
    """Test that new OAuth clients get mcp:* scopes by default."""

    def test_default_client_scopes_use_mcp(self):
        from microservices.auth_service.main import OAuthClientCreateRequest

        client = OAuthClientCreateRequest(client_name="test")
        assert client.allowed_scopes == ["mcp:tools:execute"]
        # Ensure no a2a.* scopes in defaults
        for scope in client.allowed_scopes:
            assert not scope.startswith("a2a."), f"Legacy scope found in defaults: {scope}"


class TestWellKnownScopesAreMcpOnly:
    """Test that authorization server metadata only advertises mcp:* scopes."""

    @pytest.mark.asyncio
    async def test_wellknown_scopes_are_mcp_only(self):
        from microservices.auth_service.main import oauth_authorization_server_metadata

        metadata = await oauth_authorization_server_metadata()
        scopes = metadata["scopes_supported"]

        # All scopes should be mcp:* format
        for scope in scopes:
            assert scope.startswith("mcp:"), f"Non-mcp scope in metadata: {scope}"

        # No a2a.* scopes should be present
        a2a_scopes = [s for s in scopes if s.startswith("a2a.")]
        assert a2a_scopes == [], f"Legacy a2a scopes found: {a2a_scopes}"

        # Verify expected scopes are present
        assert "mcp:tools:read" in scopes
        assert "mcp:tools:execute" in scopes
        assert "mcp:prompts:read" in scopes
        assert "mcp:resources:read" in scopes
        assert "mcp:tasks:read" in scopes
        assert "mcp:tasks:cancel" in scopes
