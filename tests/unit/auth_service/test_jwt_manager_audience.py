"""
Unit tests for JWT Manager audience (aud) claim support.

Tests:
- TokenClaims accepts audience field
- create_access_token includes aud in payload when audience is set
- create_access_token omits aud when audience is None
- verify_token succeeds for tokens with aud claim
- Backward compat: tokens without aud still verify correctly

Covers: #153 — Move aud from metadata to standard JWT claim
"""

import os
import sys
import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

from core.jwt_manager import JWTManager, TokenClaims, TokenScope, TokenType

pytestmark = pytest.mark.unit


@pytest.fixture
def jwt_manager():
    """Create a JWTManager with a fixed secret for deterministic tests."""
    return JWTManager(secret_key="test-secret-key-for-unit-tests")


@pytest.fixture
def base_claims():
    """Base TokenClaims for client_credentials tokens."""
    return TokenClaims(
        user_id="client:test-client",
        email=None,
        scope=TokenScope.SERVICE,
        token_type=TokenType.ACCESS,
        permissions=["mcp:tools:execute"],
        metadata={
            "client_id": "test-client",
            "client_name": "Test Client",
            "grant_type": "client_credentials",
            "aud": "a2a",
        },
    )


class TestTokenClaimsAudience:
    """Test that TokenClaims supports the audience field."""

    def test_audience_defaults_to_none(self):
        claims = TokenClaims(user_id="usr_1")
        assert claims.audience is None

    def test_audience_can_be_set(self):
        claims = TokenClaims(user_id="usr_1", audience="https://api.example.com")
        assert claims.audience == "https://api.example.com"

    def test_audience_with_a2a_default(self):
        claims = TokenClaims(user_id="client:x", audience="a2a")
        assert claims.audience == "a2a"


class TestCreateAccessTokenAudience:
    """Test that create_access_token includes aud as a standard JWT claim."""

    def test_aud_included_when_audience_set(self, jwt_manager, base_claims):
        base_claims.audience = "https://mcp.example.com"
        token = jwt_manager.create_access_token(base_claims)

        # Decode without verification to inspect payload
        payload = jwt_manager._decode_without_verification(token)
        assert payload["aud"] == "https://mcp.example.com"

    def test_aud_set_to_a2a_by_default(self, jwt_manager, base_claims):
        base_claims.audience = "a2a"
        token = jwt_manager.create_access_token(base_claims)

        payload = jwt_manager._decode_without_verification(token)
        assert payload["aud"] == "a2a"

    def test_aud_omitted_when_audience_none(self, jwt_manager):
        claims = TokenClaims(
            user_id="usr_1",
            email="test@example.com",
            scope=TokenScope.USER,
            token_type=TokenType.ACCESS,
        )
        token = jwt_manager.create_access_token(claims)

        payload = jwt_manager._decode_without_verification(token)
        assert "aud" not in payload

    def test_aud_and_metadata_aud_both_present(self, jwt_manager, base_claims):
        """Backward compat: both standard aud claim and metadata.aud coexist."""
        base_claims.audience = "https://resource.example.com"
        base_claims.metadata["aud"] = "https://resource.example.com"
        token = jwt_manager.create_access_token(base_claims)

        payload = jwt_manager._decode_without_verification(token)
        # Standard claim
        assert payload["aud"] == "https://resource.example.com"
        # Metadata (backward compat)
        assert payload["metadata"]["aud"] == "https://resource.example.com"


class TestVerifyTokenWithAudience:
    """Test that verify_token works for tokens with aud claim."""

    def test_verify_token_with_aud(self, jwt_manager, base_claims):
        base_claims.audience = "a2a"
        token = jwt_manager.create_access_token(base_claims)

        result = jwt_manager.verify_token(token)
        assert result["valid"] is True
        assert result["user_id"] == "client:test-client"
        assert result["payload"]["aud"] == "a2a"

    def test_verify_token_with_resource_aud(self, jwt_manager, base_claims):
        base_claims.audience = "https://mcp.example.com"
        token = jwt_manager.create_access_token(base_claims)

        result = jwt_manager.verify_token(token)
        assert result["valid"] is True
        assert result["payload"]["aud"] == "https://mcp.example.com"

    def test_verify_token_without_aud_still_works(self, jwt_manager):
        """Backward compat: tokens without aud still verify."""
        claims = TokenClaims(
            user_id="usr_1",
            email="test@example.com",
            scope=TokenScope.USER,
            token_type=TokenType.ACCESS,
        )
        token = jwt_manager.create_access_token(claims)

        result = jwt_manager.verify_token(token)
        assert result["valid"] is True
        assert "aud" not in result["payload"]


class TestVerifyTokenAudienceEnforcement:
    """Test that verify_token enforces aud when expected_audience is provided."""

    def test_matching_audience_passes(self, jwt_manager, base_claims):
        """Token with correct aud passes when expected_audience matches."""
        base_claims.audience = "https://mcp.isa.io"
        token = jwt_manager.create_access_token(base_claims)

        result = jwt_manager.verify_token(token, expected_audience="https://mcp.isa.io")
        assert result["valid"] is True

    def test_wrong_audience_fails(self, jwt_manager, base_claims):
        """Token with wrong aud fails when expected_audience doesn't match."""
        base_claims.audience = "https://mcp.isa.io"
        token = jwt_manager.create_access_token(base_claims)

        result = jwt_manager.verify_token(token, expected_audience="https://other.isa.io")
        assert result["valid"] is False
        assert "audience" in result["error"].lower() or "aud" in result["error"].lower()

    def test_no_audience_in_token_with_expected_audience_fails(self, jwt_manager):
        """Token without aud fails when expected_audience is specified (no metadata fallback)."""
        claims = TokenClaims(
            user_id="usr_1",
            scope=TokenScope.USER,
            token_type=TokenType.ACCESS,
        )
        token = jwt_manager.create_access_token(claims)

        result = jwt_manager.verify_token(token, expected_audience="https://mcp.isa.io")
        assert result["valid"] is False

    def test_metadata_aud_fallback(self, jwt_manager):
        """Backward compat: token with aud only in metadata still passes."""
        # Simulate legacy token: aud in metadata but not as root claim
        claims = TokenClaims(
            user_id="client:legacy",
            scope=TokenScope.SERVICE,
            token_type=TokenType.ACCESS,
            metadata={"aud": "https://mcp.isa.io"},
        )
        # No audience field → no root aud claim
        token = jwt_manager.create_access_token(claims)

        # Without expected_audience, should pass (no enforcement)
        result = jwt_manager.verify_token(token)
        assert result["valid"] is True

    def test_no_expected_audience_skips_check(self, jwt_manager, base_claims):
        """Without expected_audience, any aud (or none) is accepted."""
        base_claims.audience = "https://mcp.isa.io"
        token = jwt_manager.create_access_token(base_claims)

        # No expected_audience → no enforcement
        result = jwt_manager.verify_token(token)
        assert result["valid"] is True

    def test_a2a_audience_enforcement(self, jwt_manager, base_claims):
        """Legacy a2a audience works with enforcement."""
        base_claims.audience = "a2a"
        token = jwt_manager.create_access_token(base_claims)

        result = jwt_manager.verify_token(token, expected_audience="a2a")
        assert result["valid"] is True

        # Wrong audience should fail
        result = jwt_manager.verify_token(token, expected_audience="https://mcp.isa.io")
        assert result["valid"] is False
