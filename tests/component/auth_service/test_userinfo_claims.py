"""
Component tests for canonical auth userinfo claims.

Covers: #366 — userinfo claims consumed by JupyterHub and model services.
"""

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from core.jwt_manager import JWTManager, TokenClaims, TokenScope, TokenType
from microservices.auth_service.auth_service import AuthenticationService

pytestmark = pytest.mark.component


@pytest.fixture
def jwt_manager():
    return JWTManager(
        secret_key="test-userinfo-claims-secret-32bytes",
        algorithm="HS256",
        issuer="isA_user",
        access_token_expiry=3600,
        refresh_token_expiry=604800,
    )


@pytest.fixture
def auth_service(jwt_manager):
    return AuthenticationService(jwt_manager=jwt_manager)


def _token(
    jwt_manager,
    *,
    user_id="usr_userinfo_001",
    email="user@example.com",
    org_id="org_claims_001",
    scope=TokenScope.USER,
    permissions=None,
    metadata=None,
):
    claims = TokenClaims(
        user_id=user_id,
        email=email,
        organization_id=org_id,
        scope=scope,
        token_type=TokenType.ACCESS,
        permissions=permissions or [],
        metadata=metadata or {},
    )
    return jwt_manager.create_access_token(claims)


@pytest.mark.asyncio
async def test_userinfo_returns_canonical_oauth_claims_for_non_admin(auth_service, jwt_manager):
    token = _token(
        jwt_manager,
        permissions=["features.read"],
        metadata={"name": "Model User", "roles": ["member"]},
    )

    result = await auth_service.get_user_info_from_token(token)

    assert result["success"] is True
    assert result["sub"] == "usr_userinfo_001"
    assert result["user_id"] == "usr_userinfo_001"
    assert result["email"] == "user@example.com"
    assert result["preferred_username"] == "user"
    assert result["name"] == "Model User"
    assert result["organization_id"] == "org_claims_001"
    assert result["tenant_id"] == "org_claims_001"
    assert result["roles"] == ["member"]
    assert result["permissions"] == ["features.read"]
    assert result["provider"] == "isa_user"


@pytest.mark.asyncio
async def test_userinfo_returns_admin_role_from_admin_scope(auth_service, jwt_manager):
    token = _token(
        jwt_manager,
        user_id="usr_admin_claims",
        email="admin@example.com",
        org_id=None,
        scope=TokenScope.ADMIN,
        permissions=["auth.admin"],
        metadata={"admin_roles": ["super_admin"]},
    )

    result = await auth_service.get_user_info_from_token(token)

    assert result["success"] is True
    assert result["sub"] == "usr_admin_claims"
    assert result["organization_id"] is None
    assert result["tenant_id"] is None
    assert result["roles"] == ["admin"]
    assert result["admin_roles"] == ["super_admin"]
    assert result["permissions"] == ["auth.admin"]


@pytest.mark.asyncio
async def test_userinfo_missing_org_context_has_stable_empty_tenant_claims(
    auth_service, jwt_manager
):
    token = _token(
        jwt_manager,
        email="solo@example.com",
        org_id=None,
        metadata={},
    )

    result = await auth_service.get_user_info_from_token(token)

    assert result["success"] is True
    assert result["organization_id"] is None
    assert result["tenant_id"] is None
    assert result["roles"] == []
    assert result["permissions"] == []
    assert result["preferred_username"] == "solo"


@pytest.mark.asyncio
async def test_userinfo_adds_dev_bypass_admin_claims_only_when_enabled(
    auth_service, jwt_manager, monkeypatch
):
    token = _token(
        jwt_manager,
        email="admin@example.com",
        org_id=None,
        metadata={"dev_bypass": True},
    )

    monkeypatch.setenv("AUTH_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEV_BYPASS_ADMINS", "admin@example.com")
    enabled = await auth_service.get_user_info_from_token(token)

    assert enabled["roles"] == ["admin"]
    assert enabled["permissions"] == ["auth.admin"]

    monkeypatch.setenv("AUTH_DEV_BYPASS_ENABLED", "false")
    disabled = await auth_service.get_user_info_from_token(token)

    assert disabled["roles"] == []
    assert disabled["permissions"] == []
