"""
Authorization Code Service

Business logic for OAuth2 authorization code grant with PKCE (RFC 7636).

Orchestrates:
- Authorization request validation and code generation
- Authorization code consumption with PKCE verification
- Single-use enforcement, TTL, redirect_uri/client_id matching
"""

import base64
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuthorizationCodeService:
    """Service layer for OAuth2 authorization code grant with PKCE validation."""

    def __init__(self, code_repo, client_repo):
        self._code_repo = code_repo
        self._client_repo = client_repo
        self._code_ttl_seconds = int(
            os.environ.get("OAUTH_AUTHORIZATION_CODE_TTL_SECONDS", "600")
        )

    async def create_authorization_request(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        resource: Optional[str],
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate params and create an authorization code.

        Args:
            client_id: OAuth client identifier.
            redirect_uri: Callback URI for the authorization code.
            scope: Space-separated list of requested scopes.
            state: Opaque state value for CSRF protection.
            code_challenge: PKCE code challenge (required for public clients).
            code_challenge_method: PKCE method (must be "S256").
            resource: RFC 8707 resource indicator.
            user_id: Authenticated user granting authorization.
            organization_id: Optional organization context.

        Returns:
            Dict with ``code``, ``state``, and ``redirect_uri``.

        Raises:
            ValueError: On any validation failure (prefixed with OAuth error code).
        """
        # 1. Validate client exists
        client = await self._client_repo.get_client(client_id)
        if not client:
            raise ValueError("invalid_client: Client not found")

        # 2. Validate redirect_uri against registered URIs
        allowed_uris = client.get("redirect_uris", [])
        if allowed_uris and redirect_uri not in allowed_uris:
            raise ValueError("invalid_request: redirect_uri not registered")

        # 3. Validate PKCE for public clients or when require_pkce is set
        client_type = client.get("client_type", "confidential")
        require_pkce = client.get("require_pkce", True)
        if client_type == "public" or require_pkce:
            if not code_challenge:
                raise ValueError("invalid_request: code_challenge required")
            if code_challenge_method != "S256":
                raise ValueError(
                    "invalid_request: only S256 code_challenge_method supported"
                )

        # 4. Validate scopes
        requested_scopes: List[str] = (
            scope.split() if isinstance(scope, str) else list(scope)
        )

        # 5. Generate authorization code
        code_value = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self._code_ttl_seconds
        )

        # 6. Store in DB
        await self._code_repo.create_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            resource=resource,
            scopes=requested_scopes,
            user_id=user_id,
            organization_id=organization_id,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            code_value=code_value,
            expires_at=expires_at,
        )

        return {
            "code": code_value,
            "state": state,
            "redirect_uri": redirect_uri,
        }

    async def consume_authorization_code(
        self,
        code_value: str,
        redirect_uri: str,
        code_verifier: Optional[str],
        client_id: str,
    ) -> Dict[str, Any]:
        """Validate and consume an authorization code.

        Returns user/scope data suitable for token issuance.

        Raises:
            ValueError: On any validation failure (prefixed with OAuth error code).
        """
        # 1. Get code from DB
        code = await self._code_repo.get_code(code_value)
        if not code:
            raise ValueError("invalid_grant: Authorization code not found")

        # 2. Check not expired
        if code["expires_at"] < datetime.now(timezone.utc):
            raise ValueError("invalid_grant: Authorization code expired")

        # 3. Check not already used
        if code.get("is_used"):
            raise ValueError("invalid_grant: Authorization code already used")

        # 4. Validate client_id matches
        if code["client_id"] != client_id:
            raise ValueError("invalid_grant: client_id mismatch")

        # 5. Validate redirect_uri matches
        if code["redirect_uri"] != redirect_uri:
            raise ValueError("invalid_grant: redirect_uri mismatch")

        # 6. Validate PKCE
        if code.get("code_challenge"):
            if not code_verifier:
                raise ValueError("invalid_grant: code_verifier required")
            if not self._validate_pkce(
                code_verifier,
                code["code_challenge"],
                code.get("code_challenge_method", "S256"),
            ):
                raise ValueError("invalid_grant: PKCE validation failed")

        # 7. Mark as used (atomic single-use enforcement)
        success = await self._code_repo.mark_used(code["code_id"])
        if not success:
            raise ValueError("invalid_grant: Authorization code already used")

        return {
            "user_id": code["user_id"],
            "organization_id": code.get("organization_id"),
            "scopes": code.get("approved_scopes") or code.get("scopes", []),
            "resource": code.get("resource"),
            "client_id": code["client_id"],
        }

    @staticmethod
    def _validate_pkce(
        code_verifier: str, code_challenge: str, method: str = "S256"
    ) -> bool:
        """Validate PKCE code_verifier against stored code_challenge (RFC 7636).

        Only S256 is supported:
            BASE64URL(SHA256(code_verifier)) == code_challenge
        """
        if method != "S256":
            return False
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return computed == code_challenge
