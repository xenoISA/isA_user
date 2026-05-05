"""
Unit tests for JupyterHub OAuth client registration support (#788).

These tests stay at the model/service boundary: no real database, no live
auth_service, and no Kubernetes dependencies.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from microservices.auth_service.auth_service import AuthenticationService
from microservices.auth_service.main import OAuthClientCreateRequest

pytestmark = pytest.mark.unit


def test_oauth_client_create_request_accepts_authorization_code_metadata():
    request = OAuthClientCreateRequest(
        client_name="jupyterhub-local",
        organization_id="org_local",
        allowed_scopes=["openid", "profile", "email", "roles"],
        token_ttl_seconds=3600,
        client_type="confidential",
        redirect_uris=["http://localhost:18000/hub/oauth_callback"],
        require_pkce=False,
    )

    assert request.client_type == "confidential"
    assert request.redirect_uris == ["http://localhost:18000/hub/oauth_callback"]
    assert request.require_pkce is False


@pytest.mark.asyncio
async def test_dev_bypass_login_can_mint_admin_token_for_allowlisted_admin():
    jwt_manager = MagicMock()
    jwt_manager.create_access_token.return_value = "admin-dev-token"

    auth_repository = MagicMock()
    auth_repository.get_user_by_email = AsyncMock(
        return_value={
            "user_id": "usr_admin",
            "email": "admin@example.com",
            "name": "Admin User",
        }
    )

    service = AuthenticationService(
        jwt_manager=jwt_manager,
        auth_repository=auth_repository,
    )

    result = await service.dev_bypass_login(
        email="admin@example.com",
        expires_in=3600,
        permissions=["auth.admin"],
        metadata={"dev_admin": True},
    )

    assert result["success"] is True
    assert result["token"] == "admin-dev-token"
    claims = jwt_manager.create_access_token.call_args.args[0]
    assert claims.permissions == ["auth.admin"]
    assert claims.metadata["dev_admin"] is True
