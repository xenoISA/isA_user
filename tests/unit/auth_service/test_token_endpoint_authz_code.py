"""
Unit tests for authorization_code grant on the token endpoint.

Tests:
- issue_authorization_code_token success (valid code + verifier -> JWT)
- issue_authorization_code_token with invalid code -> error
- Confidential client requires client_secret
- Public client without secret succeeds
- client_credentials grant still works (regression)

All repository/service calls are mocked -- no real DB needed.

Covers: xenoISA/isA_user#164
"""

import base64
import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from microservices.auth_service.auth_service import AuthenticationService

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_code_challenge(verifier: str) -> str:
    """Compute S256 code_challenge from a code_verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _make_jwt_manager():
    """Create a mock JWT manager that returns a deterministic token."""
    jwt_mgr = MagicMock()
    jwt_mgr.create_access_token.return_value = "mock-jwt-token"
    return jwt_mgr


def _make_oauth_client_repo(client_type="public", allowed_scopes=None):
    """Create a mock OAuth client repository."""
    repo = MagicMock()
    repo.get_client = AsyncMock(return_value={
        "client_id": "test-client",
        "client_name": "Test Client",
        "client_type": client_type,
        "allowed_scopes": allowed_scopes or ["mcp:tools:execute"],
        "token_ttl_seconds": 3600,
    })
    repo.verify_client_credentials = AsyncMock(return_value={
        "client_id": "test-client",
        "client_name": "Test Client",
        "client_type": client_type,
        "allowed_scopes": allowed_scopes or ["mcp:tools:execute"],
        "token_ttl_seconds": 3600,
    })
    return repo


def _make_auth_code_service(
    user_id="usr_abc123",
    scopes=None,
    resource="https://mcp.example.com",
    raise_error=None,
):
    """Create a mock AuthorizationCodeService."""
    svc = MagicMock()
    if raise_error:
        svc.consume_authorization_code = AsyncMock(side_effect=raise_error)
    else:
        svc.consume_authorization_code = AsyncMock(return_value={
            "user_id": user_id,
            "organization_id": "org_1",
            "scopes": scopes or ["mcp:tools:execute"],
            "resource": resource,
            "client_id": "test-client",
        })
    return svc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def jwt_manager():
    return _make_jwt_manager()


@pytest.fixture
def oauth_repo():
    return _make_oauth_client_repo(client_type="public")


@pytest.fixture
def auth_code_service():
    return _make_auth_code_service()


@pytest.fixture
def service(jwt_manager, oauth_repo, auth_code_service):
    return AuthenticationService(
        jwt_manager=jwt_manager,
        oauth_client_repository=oauth_repo,
        authorization_code_service=auth_code_service,
    )


# ---------------------------------------------------------------------------
# Tests: issue_authorization_code_token
# ---------------------------------------------------------------------------

class TestIssueAuthorizationCodeToken:
    @pytest.mark.asyncio
    async def test_success(self, service, jwt_manager, auth_code_service):
        """Valid code + verifier returns a JWT access token."""
        result = await service.issue_authorization_code_token(
            code="valid-auth-code",
            redirect_uri="https://example.com/callback",
            code_verifier="my-verifier",
            client_id="test-client",
        )

        assert result["success"] is True
        assert result["access_token"] == "mock-jwt-token"
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert "mcp:tools:execute" in result["scope"]
        assert result["client_id"] == "test-client"

        # Verify consume was called with correct args
        auth_code_service.consume_authorization_code.assert_awaited_once_with(
            code_value="valid-auth-code",
            redirect_uri="https://example.com/callback",
            code_verifier="my-verifier",
            client_id="test-client",
        )

        # Verify JWT was created
        jwt_manager.create_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_code(self, jwt_manager, oauth_repo):
        """Bad authorization code returns an error."""
        auth_code_svc = _make_auth_code_service(
            raise_error=ValueError("invalid_grant: Authorization code not found")
        )
        svc = AuthenticationService(
            jwt_manager=jwt_manager,
            oauth_client_repository=oauth_repo,
            authorization_code_service=auth_code_svc,
        )

        result = await svc.issue_authorization_code_token(
            code="bad-code",
            redirect_uri="https://example.com/callback",
            code_verifier="my-verifier",
            client_id="test-client",
        )

        assert result["success"] is False
        assert result["error_code"] == "invalid_grant"
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_confidential_client_needs_secret(self, jwt_manager, auth_code_service):
        """Confidential client without client_secret fails."""
        oauth_repo = _make_oauth_client_repo(client_type="confidential")
        svc = AuthenticationService(
            jwt_manager=jwt_manager,
            oauth_client_repository=oauth_repo,
            authorization_code_service=auth_code_service,
        )

        result = await svc.issue_authorization_code_token(
            code="valid-auth-code",
            redirect_uri="https://example.com/callback",
            code_verifier="my-verifier",
            client_id="test-client",
            client_secret=None,
        )

        assert result["success"] is False
        assert result["error_code"] == "invalid_client"
        assert "secret" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_public_client_no_secret_ok(self, service):
        """Public client without client_secret succeeds."""
        result = await service.issue_authorization_code_token(
            code="valid-auth-code",
            redirect_uri="https://example.com/callback",
            code_verifier="my-verifier",
            client_id="test-client",
            client_secret=None,
        )

        assert result["success"] is True
        assert result["access_token"] == "mock-jwt-token"

    @pytest.mark.asyncio
    async def test_confidential_client_with_valid_secret(self, jwt_manager, auth_code_service):
        """Confidential client with valid secret succeeds."""
        oauth_repo = _make_oauth_client_repo(client_type="confidential")
        svc = AuthenticationService(
            jwt_manager=jwt_manager,
            oauth_client_repository=oauth_repo,
            authorization_code_service=auth_code_service,
        )

        result = await svc.issue_authorization_code_token(
            code="valid-auth-code",
            redirect_uri="https://example.com/callback",
            code_verifier="my-verifier",
            client_id="test-client",
            client_secret="valid-secret",
        )

        assert result["success"] is True
        assert result["access_token"] == "mock-jwt-token"
        oauth_repo.verify_client_credentials.assert_awaited_once_with(
            "test-client", "valid-secret"
        )

    @pytest.mark.asyncio
    async def test_confidential_client_invalid_secret(self, jwt_manager, auth_code_service):
        """Confidential client with bad secret fails."""
        oauth_repo = _make_oauth_client_repo(client_type="confidential")
        oauth_repo.verify_client_credentials = AsyncMock(return_value=None)
        svc = AuthenticationService(
            jwt_manager=jwt_manager,
            oauth_client_repository=oauth_repo,
            authorization_code_service=auth_code_service,
        )

        result = await svc.issue_authorization_code_token(
            code="valid-auth-code",
            redirect_uri="https://example.com/callback",
            code_verifier="my-verifier",
            client_id="test-client",
            client_secret="wrong-secret",
        )

        assert result["success"] is False
        assert result["error_code"] == "invalid_client"

    @pytest.mark.asyncio
    async def test_resource_becomes_audience(self, jwt_manager, oauth_repo, auth_code_service):
        """Resource indicator from code_data becomes JWT audience."""
        svc = AuthenticationService(
            jwt_manager=jwt_manager,
            oauth_client_repository=oauth_repo,
            authorization_code_service=auth_code_service,
        )

        result = await svc.issue_authorization_code_token(
            code="valid-auth-code",
            redirect_uri="https://example.com/callback",
            code_verifier="my-verifier",
            client_id="test-client",
        )

        assert result["success"] is True
        # Verify TokenClaims was created with the resource as audience
        call_args = jwt_manager.create_access_token.call_args
        claims = call_args[0][0]
        assert claims.audience == "https://mcp.example.com"


# ---------------------------------------------------------------------------
# Regression: client_credentials still works
# ---------------------------------------------------------------------------

class TestClientCredentialsRegression:
    @pytest.mark.asyncio
    async def test_client_credentials_still_works(self):
        """client_credentials grant continues to work after adding authorization_code."""
        jwt_mgr = _make_jwt_manager()
        oauth_repo = _make_oauth_client_repo(client_type="confidential")

        svc = AuthenticationService(
            jwt_manager=jwt_mgr,
            oauth_client_repository=oauth_repo,
        )

        result = await svc.issue_client_credentials_token(
            client_id="test-client",
            client_secret="test-secret",
            scope="mcp:tools:execute",
            resource="https://mcp.example.com",
        )

        assert result["success"] is True
        assert result["access_token"] == "mock-jwt-token"
        assert result["token_type"] == "Bearer"
        assert "mcp:tools:execute" in result["scope"]
