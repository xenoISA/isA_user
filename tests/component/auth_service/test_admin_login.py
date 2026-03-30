"""
Component tests for admin login service logic.

Tests the AuthenticationService.admin_login() and admin_verify() methods
with mocked dependencies (auth_repository, jwt_manager).

Covers: Issue #189 — Admin authentication with scoped JWT
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import timedelta

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

from core.jwt_manager import JWTManager, TokenScope
from microservices.auth_service.auth_service import AuthenticationService

pytestmark = pytest.mark.component


@pytest.fixture
def jwt_manager():
    """Real JWT manager with test secret for token generation/verification."""
    return JWTManager(
        secret_key="test-component-secret-key",
        algorithm="HS256",
        issuer="isA_user",
        access_token_expiry=3600,
        refresh_token_expiry=604800,
    )


@pytest.fixture
def mock_auth_repo():
    """Mock auth repository."""
    repo = AsyncMock()
    repo.update_last_login = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def auth_service(jwt_manager, mock_auth_repo):
    """AuthenticationService with real JWT manager and mocked repository."""
    return AuthenticationService(
        jwt_manager=jwt_manager,
        auth_repository=mock_auth_repo,
    )


def _make_admin_user(admin_roles=None, is_active=True, password_hash=None):
    """Helper to build a user record from the mock repo."""
    if password_hash is None:
        from microservices.auth_service.password_utils import hash_password
        password_hash = hash_password("Admin#Secure123")

    return {
        "user_id": "usr_admin_001",
        "email": "admin@example.com",
        "name": "Admin User",
        "password_hash": password_hash,
        "email_verified": True,
        "is_active": is_active,
        "admin_roles": admin_roles,
    }


class TestAdminLogin:
    """Test admin_login service method."""

    @pytest.mark.asyncio
    async def test_successful_admin_login(self, auth_service, mock_auth_repo):
        """Admin login returns tokens when credentials and roles are valid."""
        mock_auth_repo.get_user_for_login = AsyncMock(
            return_value=_make_admin_user(admin_roles=["super_admin"])
        )

        result = await auth_service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )

        assert result["success"] is True
        assert result["user_id"] == "usr_admin_001"
        assert result["email"] == "admin@example.com"
        assert result["admin_roles"] == ["super_admin"]
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["expires_in"] == 4 * 3600
        assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_admin_login_wrong_password(self, auth_service, mock_auth_repo):
        """Admin login fails with wrong password."""
        mock_auth_repo.get_user_for_login = AsyncMock(
            return_value=_make_admin_user(admin_roles=["super_admin"])
        )

        result = await auth_service.admin_login(
            email="admin@example.com",
            password="WrongPassword123",
        )

        assert result["success"] is False
        assert "Invalid email or password" in result["error"]

    @pytest.mark.asyncio
    async def test_admin_login_user_not_found(self, auth_service, mock_auth_repo):
        """Admin login fails when user does not exist."""
        mock_auth_repo.get_user_for_login = AsyncMock(return_value=None)

        result = await auth_service.admin_login(
            email="nobody@example.com",
            password="SomePassword1",
        )

        assert result["success"] is False
        assert "Invalid email or password" in result["error"]

    @pytest.mark.asyncio
    async def test_admin_login_no_admin_roles(self, auth_service, mock_auth_repo):
        """Admin login fails when user has no admin roles."""
        mock_auth_repo.get_user_for_login = AsyncMock(
            return_value=_make_admin_user(admin_roles=None)
        )

        result = await auth_service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )

        assert result["success"] is False
        assert "Insufficient admin privileges" in result["error"]

    @pytest.mark.asyncio
    async def test_admin_login_empty_admin_roles(self, auth_service, mock_auth_repo):
        """Admin login fails when admin_roles is an empty list."""
        mock_auth_repo.get_user_for_login = AsyncMock(
            return_value=_make_admin_user(admin_roles=[])
        )

        result = await auth_service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )

        assert result["success"] is False
        assert "Insufficient admin privileges" in result["error"]

    @pytest.mark.asyncio
    async def test_admin_login_disabled_account(self, auth_service, mock_auth_repo):
        """Admin login fails when account is disabled."""
        mock_auth_repo.get_user_for_login = AsyncMock(
            return_value=_make_admin_user(admin_roles=["super_admin"], is_active=False)
        )

        result = await auth_service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )

        assert result["success"] is False
        assert "Account is disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_admin_login_no_password_set(self, auth_service, mock_auth_repo):
        """Admin login fails when user has no password hash."""
        user = _make_admin_user(admin_roles=["super_admin"])
        user["password_hash"] = None
        mock_auth_repo.get_user_for_login = AsyncMock(return_value=user)

        result = await auth_service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )

        assert result["success"] is False
        assert "Invalid email or password" in result["error"]

    @pytest.mark.asyncio
    async def test_admin_login_token_has_admin_scope(self, auth_service, mock_auth_repo, jwt_manager):
        """Admin login token must have scope=admin."""
        mock_auth_repo.get_user_for_login = AsyncMock(
            return_value=_make_admin_user(admin_roles=["super_admin", "billing_admin"])
        )

        result = await auth_service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )

        import jwt as pyjwt
        payload = pyjwt.decode(
            result["access_token"],
            jwt_manager.secret_key,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        assert payload["scope"] == "admin"
        assert payload["metadata"]["admin_roles"] == ["super_admin", "billing_admin"]

    @pytest.mark.asyncio
    async def test_admin_login_updates_last_login(self, auth_service, mock_auth_repo):
        """Admin login should update last_login timestamp."""
        mock_auth_repo.get_user_for_login = AsyncMock(
            return_value=_make_admin_user(admin_roles=["super_admin"])
        )

        await auth_service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )

        mock_auth_repo.update_last_login.assert_called_once_with("usr_admin_001")

    @pytest.mark.asyncio
    async def test_admin_login_no_repo(self, jwt_manager):
        """Admin login fails gracefully when no auth repository."""
        service = AuthenticationService(jwt_manager=jwt_manager, auth_repository=None)

        result = await service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )

        assert result["success"] is False
        assert "Auth repository not available" in result["error"]


class TestAdminVerify:
    """Test admin_verify service method."""

    @pytest.mark.asyncio
    async def test_verify_valid_admin_token(self, auth_service, mock_auth_repo, jwt_manager):
        """admin_verify returns valid=True for a valid admin token."""
        # First login to get a real admin token
        mock_auth_repo.get_user_for_login = AsyncMock(
            return_value=_make_admin_user(admin_roles=["super_admin"])
        )
        login_result = await auth_service.admin_login(
            email="admin@example.com",
            password="Admin#Secure123",
        )
        assert login_result["success"] is True

        # Now verify the token
        verify_result = await auth_service.admin_verify(login_result["access_token"])

        assert verify_result["valid"] is True
        assert verify_result["user_id"] == "usr_admin_001"
        assert verify_result["admin_roles"] == ["super_admin"]
        assert verify_result["scope"] == "admin"

    @pytest.mark.asyncio
    async def test_verify_non_admin_token_fails(self, auth_service, jwt_manager):
        """admin_verify rejects tokens with scope != admin."""
        from core.jwt_manager import TokenClaims, TokenType

        # Create a regular user token (scope=user)
        claims = TokenClaims(
            user_id="usr_regular",
            email="user@example.com",
            scope=TokenScope.USER,
            token_type=TokenType.ACCESS,
            metadata={},
        )
        token = jwt_manager.create_access_token(claims, expires_delta=timedelta(hours=1))

        result = await auth_service.admin_verify(token)

        assert result["valid"] is False
        assert "Not an admin token" in result["error"]

    @pytest.mark.asyncio
    async def test_verify_invalid_token_fails(self, auth_service):
        """admin_verify rejects invalid/malformed tokens."""
        result = await auth_service.admin_verify("not.a.real.token")

        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_verify_admin_token_without_roles_fails(self, auth_service, jwt_manager):
        """admin_verify rejects admin-scoped token with empty admin_roles."""
        from core.jwt_manager import TokenClaims, TokenType

        claims = TokenClaims(
            user_id="usr_no_roles",
            email="noroles@example.com",
            scope=TokenScope.ADMIN,
            token_type=TokenType.ACCESS,
            metadata={"admin_roles": []},
        )
        token = jwt_manager.create_access_token(claims, expires_delta=timedelta(hours=4))

        result = await auth_service.admin_verify(token)

        assert result["valid"] is False
        assert "No admin roles" in result["error"]
