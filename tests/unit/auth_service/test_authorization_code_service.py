"""
Unit tests for AuthorizationCodeService.

Tests:
- PKCE S256 validation (correct verifier, wrong verifier, plain rejected)
- create_authorization_request (success, invalid client, missing PKCE)
- consume_authorization_code (success, expired, already used, wrong redirect, wrong verifier)

All repository calls are mocked — no real PostgreSQL needed.

Covers: xenoISA/isA_user#163
"""

import base64
import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from microservices.auth_service.authorization_code_service import (
    AuthorizationCodeService,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_code_challenge(verifier: str) -> str:
    """Compute S256 code_challenge from a code_verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_code_repo():
    repo = MagicMock()
    repo.create_code = AsyncMock(return_value={"code_id": "test-code-id"})
    repo.get_code = AsyncMock()
    repo.mark_used = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_client_repo():
    repo = MagicMock()
    repo.get_client = AsyncMock(return_value={
        "client_id": "test-client",
        "client_name": "Test Client",
        "client_type": "public",
        "require_pkce": True,
        "redirect_uris": ["https://example.com/callback"],
        "allowed_scopes": ["mcp:tools:execute"],
    })
    return repo


@pytest.fixture
def service(mock_code_repo, mock_client_repo):
    return AuthorizationCodeService(
        code_repo=mock_code_repo,
        client_repo=mock_client_repo,
    )


# ---------------------------------------------------------------------------
# PKCE validation tests
# ---------------------------------------------------------------------------

class TestValidatePKCE:
    def test_validate_pkce_s256_correct(self):
        """Valid code_verifier passes S256 validation."""
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        challenge = _make_code_challenge(verifier)
        assert AuthorizationCodeService._validate_pkce(verifier, challenge, "S256") is True

    def test_validate_pkce_s256_wrong_verifier(self):
        """Wrong code_verifier fails S256 validation."""
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        challenge = _make_code_challenge(verifier)
        assert AuthorizationCodeService._validate_pkce("wrong-verifier", challenge, "S256") is False

    def test_validate_pkce_plain_rejected(self):
        """Plain method is rejected (only S256 supported)."""
        assert AuthorizationCodeService._validate_pkce("verifier", "verifier", "plain") is False


# ---------------------------------------------------------------------------
# create_authorization_request tests
# ---------------------------------------------------------------------------

class TestCreateAuthorizationRequest:
    @pytest.mark.asyncio
    async def test_create_authorization_request_success(self, service, mock_code_repo):
        """Successful authorization request returns code + state."""
        verifier = "test-verifier-for-challenge"
        challenge = _make_code_challenge(verifier)

        result = await service.create_authorization_request(
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            scope="mcp:tools:execute",
            state="random-state",
            code_challenge=challenge,
            code_challenge_method="S256",
            resource="https://mcp.example.com",
            user_id="usr_abc123",
        )

        assert "code" in result
        assert result["state"] == "random-state"
        assert result["redirect_uri"] == "https://example.com/callback"
        mock_code_repo.create_code.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_authorization_request_invalid_client(
        self, service, mock_client_repo
    ):
        """Invalid client_id raises ValueError."""
        mock_client_repo.get_client.return_value = None

        with pytest.raises(ValueError, match="invalid_client"):
            await service.create_authorization_request(
                client_id="nonexistent",
                redirect_uri="https://example.com/callback",
                scope="mcp:tools:execute",
                state="s",
                code_challenge="abc",
                code_challenge_method="S256",
                resource=None,
                user_id="usr_abc123",
            )

    @pytest.mark.asyncio
    async def test_create_authorization_request_missing_pkce_for_public(
        self, service
    ):
        """Public client without code_challenge raises ValueError."""
        with pytest.raises(ValueError, match="code_challenge required"):
            await service.create_authorization_request(
                client_id="test-client",
                redirect_uri="https://example.com/callback",
                scope="mcp:tools:execute",
                state="s",
                code_challenge=None,
                code_challenge_method=None,
                resource=None,
                user_id="usr_abc123",
            )


# ---------------------------------------------------------------------------
# consume_authorization_code tests
# ---------------------------------------------------------------------------

class TestConsumeAuthorizationCode:
    @pytest.mark.asyncio
    async def test_consume_code_success(self, service, mock_code_repo):
        """Successful code consumption returns user data."""
        verifier = "my-secret-verifier"
        challenge = _make_code_challenge(verifier)

        mock_code_repo.get_code.return_value = {
            "code_id": "uuid-1",
            "client_id": "test-client",
            "redirect_uri": "https://example.com/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "user_id": "usr_abc123",
            "organization_id": "org_1",
            "approved_scopes": ["mcp:tools:execute"],
            "resource": "https://mcp.example.com",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "is_used": False,
        }

        result = await service.consume_authorization_code(
            code_value="the-code",
            redirect_uri="https://example.com/callback",
            code_verifier=verifier,
            client_id="test-client",
        )

        assert result["user_id"] == "usr_abc123"
        assert result["organization_id"] == "org_1"
        assert result["scopes"] == ["mcp:tools:execute"]
        assert result["resource"] == "https://mcp.example.com"
        assert result["client_id"] == "test-client"
        mock_code_repo.mark_used.assert_awaited_once_with("uuid-1")

    @pytest.mark.asyncio
    async def test_consume_code_expired(self, service, mock_code_repo):
        """Expired authorization code raises ValueError."""
        mock_code_repo.get_code.return_value = {
            "code_id": "uuid-1",
            "client_id": "test-client",
            "redirect_uri": "https://example.com/callback",
            "code_challenge": None,
            "user_id": "usr_abc123",
            "expires_at": datetime.now(timezone.utc) - timedelta(minutes=1),
            "is_used": False,
        }

        with pytest.raises(ValueError, match="expired"):
            await service.consume_authorization_code(
                code_value="the-code",
                redirect_uri="https://example.com/callback",
                code_verifier=None,
                client_id="test-client",
            )

    @pytest.mark.asyncio
    async def test_consume_code_already_used(self, service, mock_code_repo):
        """Already-used authorization code raises ValueError."""
        mock_code_repo.get_code.return_value = {
            "code_id": "uuid-1",
            "client_id": "test-client",
            "redirect_uri": "https://example.com/callback",
            "code_challenge": None,
            "user_id": "usr_abc123",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "is_used": True,
        }

        with pytest.raises(ValueError, match="already used"):
            await service.consume_authorization_code(
                code_value="the-code",
                redirect_uri="https://example.com/callback",
                code_verifier=None,
                client_id="test-client",
            )

    @pytest.mark.asyncio
    async def test_consume_code_wrong_redirect(self, service, mock_code_repo):
        """Mismatched redirect_uri raises ValueError."""
        mock_code_repo.get_code.return_value = {
            "code_id": "uuid-1",
            "client_id": "test-client",
            "redirect_uri": "https://example.com/callback",
            "code_challenge": None,
            "user_id": "usr_abc123",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "is_used": False,
        }

        with pytest.raises(ValueError, match="redirect_uri mismatch"):
            await service.consume_authorization_code(
                code_value="the-code",
                redirect_uri="https://evil.com/steal",
                code_verifier=None,
                client_id="test-client",
            )

    @pytest.mark.asyncio
    async def test_consume_code_wrong_verifier(self, service, mock_code_repo):
        """Wrong PKCE verifier raises ValueError."""
        verifier = "correct-verifier"
        challenge = _make_code_challenge(verifier)

        mock_code_repo.get_code.return_value = {
            "code_id": "uuid-1",
            "client_id": "test-client",
            "redirect_uri": "https://example.com/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "user_id": "usr_abc123",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "is_used": False,
        }

        with pytest.raises(ValueError, match="PKCE validation failed"):
            await service.consume_authorization_code(
                code_value="the-code",
                redirect_uri="https://example.com/callback",
                code_verifier="wrong-verifier",
                client_id="test-client",
            )
