"""
E2E integration test for the full OAuth authorization code + PKCE flow.

Flow tested:
1. Client generates code_verifier + code_challenge (S256)
2. POST /oauth/consent-approval -> generates authorization code
3. POST /oauth/token with code + code_verifier -> returns JWT
4. JWT contains correct sub, aud, scope, grant_type claims
5. Expired code rejected
6. Reused code rejected
7. Wrong code_verifier rejected
8. Wrong redirect_uri rejected
9. Client credentials flow still works (regression)
"""

import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest

# ---------------------------------------------------------------------------
# In-memory repository stubs (no DB needed)
# ---------------------------------------------------------------------------


class InMemoryCodeRepository:
    """Dict-backed stand-in for AuthorizationCodeRepository."""

    def __init__(self):
        self._codes: Dict[str, Dict[str, Any]] = {}

    async def create_code(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        state: str,
        resource: Optional[str],
        scopes: List[str],
        user_id: str,
        organization_id: Optional[str],
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        code_value: str,
        expires_at: datetime,
        approved_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        code_id = str(uuid.uuid4())
        record = {
            "code_id": code_id,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "resource": resource,
            "scopes": scopes,
            "approved_scopes": approved_scopes or scopes,
            "user_id": user_id,
            "organization_id": organization_id,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "code_value": code_value,
            "is_used": False,
            "used_at": None,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
        }
        self._codes[code_value] = record
        return record

    async def get_code(self, code_value: str) -> Optional[Dict[str, Any]]:
        return self._codes.get(code_value)

    async def mark_used(self, code_id: str) -> bool:
        for record in self._codes.values():
            if record["code_id"] == code_id and not record["is_used"]:
                record["is_used"] = True
                record["used_at"] = datetime.now(timezone.utc)
                return True
        return False


class InMemoryClientRepository:
    """Dict-backed stand-in for OAuthClientRepository."""

    def __init__(self, clients: Optional[Dict[str, Dict[str, Any]]] = None):
        self._clients = clients or {}

    async def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        return self._clients.get(client_id)

    async def verify_client_credentials(
        self, client_id: str, client_secret: str
    ) -> Optional[Dict[str, Any]]:
        client = self._clients.get(client_id)
        if client and client.get("client_secret") == client_secret:
            return client
        return None


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


def generate_pkce():
    """Generate a PKCE code_verifier and S256 code_challenge pair."""
    code_verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# ---------------------------------------------------------------------------
# Fake JWT manager (returns deterministic tokens for assertions)
# ---------------------------------------------------------------------------


class FakeJWTManager:
    """Minimal JWTManager stand-in that returns inspectable tokens."""

    def __init__(self):
        self._last_claims = None

    def create_access_token(self, claims, expires_delta=None):
        self._last_claims = claims
        return f"fake-jwt-{claims.user_id}-{claims.audience}"

    def verify_token(self, token, expected_audience=None):
        return {"valid": True, "payload": {"type": "access"}}

    def create_token_pair(self, claims):
        return {
            "access_token": f"fake-access-{claims.user_id}",
            "refresh_token": f"fake-refresh-{claims.user_id}",
            "token_type": "Bearer",
            "expires_in": 3600,
        }


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

CLIENT_ID = "test-client-public"
CLIENT_SECRET = "super-secret"
REDIRECT_URI = "http://localhost:3000/oauth/callback"
USER_ID = "usr_test123"
SCOPE = "mcp:tools:execute mcp:tasks:read"


@pytest.fixture
def code_repo():
    return InMemoryCodeRepository()


@pytest.fixture
def client_repo():
    return InMemoryClientRepository(
        {
            CLIENT_ID: {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "client_type": "public",
                "require_pkce": True,
                "redirect_uris": [REDIRECT_URI],
                "allowed_scopes": ["mcp:tools:execute", "mcp:tasks:read"],
                "token_ttl_seconds": 3600,
            },
        }
    )


@pytest.fixture
def auth_code_service(code_repo, client_repo):
    from microservices.auth_service.authorization_code_service import (
        AuthorizationCodeService,
    )

    return AuthorizationCodeService(code_repo=code_repo, client_repo=client_repo)


@pytest.fixture
def jwt_manager():
    return FakeJWTManager()


@pytest.fixture
def auth_service(jwt_manager, auth_code_service, client_repo):
    from microservices.auth_service.auth_service import AuthenticationService

    return AuthenticationService(
        jwt_manager=jwt_manager,
        authorization_code_service=auth_code_service,
        oauth_client_repository=client_repo,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuthorizationCodeFlow:
    """Integration tests for the full authorization code + PKCE lifecycle."""

    @pytest.mark.asyncio
    async def test_full_pkce_flow_success(self, auth_code_service):
        """Generate verifier -> create authorization request -> consume code -> PKCE passes."""
        code_verifier, code_challenge = generate_pkce()

        # Create authorization request (simulates consent-approval)
        result = await auth_code_service.create_authorization_request(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            state="random-state",
            code_challenge=code_challenge,
            code_challenge_method="S256",
            resource=None,
            user_id=USER_ID,
        )

        assert "code" in result
        assert result["state"] == "random-state"
        assert result["redirect_uri"] == REDIRECT_URI

        # Consume the code with the correct verifier
        consumed = await auth_code_service.consume_authorization_code(
            code_value=result["code"],
            redirect_uri=REDIRECT_URI,
            code_verifier=code_verifier,
            client_id=CLIENT_ID,
        )

        assert consumed["user_id"] == USER_ID
        assert consumed["client_id"] == CLIENT_ID
        assert "mcp:tools:execute" in consumed["scopes"]

    @pytest.mark.asyncio
    async def test_full_token_issuance(self, auth_code_service, auth_service, jwt_manager):
        """Full flow through issue_authorization_code_token() -> JWT with correct claims."""
        code_verifier, code_challenge = generate_pkce()

        # Step 1 — create authorization code
        auth_result = await auth_code_service.create_authorization_request(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            state="state-xyz",
            code_challenge=code_challenge,
            code_challenge_method="S256",
            resource="https://mcp.example.com",
            user_id=USER_ID,
        )
        code = auth_result["code"]

        # Step 2 — exchange code for token
        token_result = await auth_service.issue_authorization_code_token(
            code=code,
            redirect_uri=REDIRECT_URI,
            code_verifier=code_verifier,
            client_id=CLIENT_ID,
        )

        assert token_result["success"] is True
        assert token_result["token_type"] == "Bearer"
        assert token_result["expires_in"] == 3600
        assert token_result["client_id"] == CLIENT_ID
        assert "access_token" in token_result

        # Verify JWT claims passed to manager
        claims = jwt_manager._last_claims
        assert claims is not None
        assert claims.user_id == USER_ID
        assert claims.audience == "https://mcp.example.com"
        assert claims.metadata["grant_type"] == "authorization_code"
        assert claims.metadata["client_id"] == CLIENT_ID

    @pytest.mark.asyncio
    async def test_expired_code_rejected(self, auth_code_service, code_repo, client_repo):
        """A code whose expires_at is in the past should be rejected."""
        code_verifier, code_challenge = generate_pkce()

        # Create a valid code first
        result = await auth_code_service.create_authorization_request(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            state="s",
            code_challenge=code_challenge,
            code_challenge_method="S256",
            resource=None,
            user_id=USER_ID,
        )

        # Manually expire the code in the in-memory store
        code_record = await code_repo.get_code(result["code"])
        code_record["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=10)

        with pytest.raises(ValueError, match="expired"):
            await auth_code_service.consume_authorization_code(
                code_value=result["code"],
                redirect_uri=REDIRECT_URI,
                code_verifier=code_verifier,
                client_id=CLIENT_ID,
            )

    @pytest.mark.asyncio
    async def test_reused_code_rejected(self, auth_code_service):
        """Using the same authorization code twice should fail on the second attempt."""
        code_verifier, code_challenge = generate_pkce()

        result = await auth_code_service.create_authorization_request(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            state="s",
            code_challenge=code_challenge,
            code_challenge_method="S256",
            resource=None,
            user_id=USER_ID,
        )

        # First use — should succeed
        await auth_code_service.consume_authorization_code(
            code_value=result["code"],
            redirect_uri=REDIRECT_URI,
            code_verifier=code_verifier,
            client_id=CLIENT_ID,
        )

        # Second use — should fail
        with pytest.raises(ValueError, match="already used"):
            await auth_code_service.consume_authorization_code(
                code_value=result["code"],
                redirect_uri=REDIRECT_URI,
                code_verifier=code_verifier,
                client_id=CLIENT_ID,
            )

    @pytest.mark.asyncio
    async def test_wrong_verifier_rejected(self, auth_code_service):
        """A wrong code_verifier should cause PKCE validation to fail."""
        code_verifier, code_challenge = generate_pkce()

        result = await auth_code_service.create_authorization_request(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            state="s",
            code_challenge=code_challenge,
            code_challenge_method="S256",
            resource=None,
            user_id=USER_ID,
        )

        with pytest.raises(ValueError, match="PKCE validation failed"):
            await auth_code_service.consume_authorization_code(
                code_value=result["code"],
                redirect_uri=REDIRECT_URI,
                code_verifier="totally-wrong-verifier",
                client_id=CLIENT_ID,
            )

    @pytest.mark.asyncio
    async def test_wrong_redirect_uri_rejected(self, auth_code_service):
        """Mismatched redirect_uri should be rejected."""
        code_verifier, code_challenge = generate_pkce()

        result = await auth_code_service.create_authorization_request(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            state="s",
            code_challenge=code_challenge,
            code_challenge_method="S256",
            resource=None,
            user_id=USER_ID,
        )

        with pytest.raises(ValueError, match="redirect_uri mismatch"):
            await auth_code_service.consume_authorization_code(
                code_value=result["code"],
                redirect_uri="http://evil.example.com/callback",
                code_verifier=code_verifier,
                client_id=CLIENT_ID,
            )

    @pytest.mark.asyncio
    async def test_wrong_client_id_rejected(self, auth_code_service):
        """A different client_id should be rejected."""
        code_verifier, code_challenge = generate_pkce()

        result = await auth_code_service.create_authorization_request(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            state="s",
            code_challenge=code_challenge,
            code_challenge_method="S256",
            resource=None,
            user_id=USER_ID,
        )

        with pytest.raises(ValueError, match="client_id mismatch"):
            await auth_code_service.consume_authorization_code(
                code_value=result["code"],
                redirect_uri=REDIRECT_URI,
                code_verifier=code_verifier,
                client_id="some-other-client",
            )

    @pytest.mark.asyncio
    async def test_client_credentials_still_works(self, auth_service):
        """Regression: client_credentials grant type should still work after auth code changes."""
        result = await auth_service.issue_client_credentials_token(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scope="mcp:tools:execute",
            resource="https://mcp.example.com",
        )

        assert result["success"] is True
        assert result["token_type"] == "Bearer"
        assert result["client_id"] == CLIENT_ID
        assert "access_token" in result
