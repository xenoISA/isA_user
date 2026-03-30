"""
Unit tests for admin JWT generation and verification.

Tests:
- Admin access token has correct claims (scope=admin, admin_roles in metadata)
- Admin access token expires in 4 hours
- Admin refresh token expires in 24 hours
- Token includes required claims: user_id, email, scope, admin_roles
- ADMIN_ROLES constant contains expected role names

Covers: Issue #189 — Admin authentication with scoped JWT
"""

import os
import sys
import pytest
import jwt
from datetime import timedelta

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

from core.jwt_manager import JWTManager, TokenClaims, TokenScope, TokenType
from microservices.auth_service.models import ADMIN_ROLES

pytestmark = pytest.mark.unit


class TestAdminRolesConstant:
    """Test the ADMIN_ROLES constant from auth_service models."""

    def test_contains_super_admin(self):
        assert "super_admin" in ADMIN_ROLES

    def test_contains_billing_admin(self):
        assert "billing_admin" in ADMIN_ROLES

    def test_contains_product_admin(self):
        assert "product_admin" in ADMIN_ROLES

    def test_contains_support_admin(self):
        assert "support_admin" in ADMIN_ROLES

    def test_contains_compliance_admin(self):
        assert "compliance_admin" in ADMIN_ROLES

    def test_has_five_roles(self):
        assert len(ADMIN_ROLES) == 5


class TestAdminJWTGeneration:
    """Test admin JWT token generation with correct claims."""

    @pytest.fixture
    def jwt_manager(self):
        return JWTManager(
            secret_key="test-admin-secret-key-for-unit-tests",
            algorithm="HS256",
            issuer="isA_user",
            access_token_expiry=3600,
            refresh_token_expiry=604800,
        )

    @pytest.fixture
    def admin_claims(self):
        return TokenClaims(
            user_id="usr_admin123",
            email="admin@example.com",
            organization_id=None,
            scope=TokenScope.ADMIN,
            token_type=TokenType.ACCESS,
            permissions=[],
            metadata={
                "admin_roles": ["super_admin", "billing_admin"],
                "login_method": "admin_email_password",
            },
        )

    def test_admin_access_token_has_admin_scope(self, jwt_manager, admin_claims):
        """Admin token must have scope=admin."""
        token = jwt_manager.create_access_token(
            admin_claims,
            expires_delta=timedelta(hours=4),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        assert payload["scope"] == "admin"

    def test_admin_access_token_has_admin_roles_in_metadata(self, jwt_manager, admin_claims):
        """Admin token must include admin_roles in metadata."""
        token = jwt_manager.create_access_token(
            admin_claims,
            expires_delta=timedelta(hours=4),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        metadata = payload.get("metadata", {})
        assert "admin_roles" in metadata
        assert metadata["admin_roles"] == ["super_admin", "billing_admin"]

    def test_admin_access_token_has_correct_user_id(self, jwt_manager, admin_claims):
        """Admin token sub claim must be the user_id."""
        token = jwt_manager.create_access_token(
            admin_claims,
            expires_delta=timedelta(hours=4),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        assert payload["sub"] == "usr_admin123"

    def test_admin_access_token_has_email(self, jwt_manager, admin_claims):
        """Admin token must include email claim."""
        token = jwt_manager.create_access_token(
            admin_claims,
            expires_delta=timedelta(hours=4),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        assert payload["email"] == "admin@example.com"

    def test_admin_access_token_has_type_access(self, jwt_manager, admin_claims):
        """Admin token must have type=access."""
        token = jwt_manager.create_access_token(
            admin_claims,
            expires_delta=timedelta(hours=4),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        assert payload["type"] == "access"

    def test_admin_access_token_expires_in_4_hours(self, jwt_manager, admin_claims):
        """Admin access token must expire in ~4 hours (14400 seconds)."""
        token = jwt_manager.create_access_token(
            admin_claims,
            expires_delta=timedelta(hours=4),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        ttl = payload["exp"] - payload["iat"]
        assert ttl == 4 * 3600  # 14400 seconds

    def test_admin_refresh_token_expires_in_24_hours(self, jwt_manager, admin_claims):
        """Admin refresh token must expire in ~24 hours."""
        token = jwt_manager.create_refresh_token(
            admin_claims,
            expires_delta=timedelta(hours=24),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        ttl = payload["exp"] - payload["iat"]
        assert ttl == 24 * 3600  # 86400 seconds

    def test_admin_token_has_issuer(self, jwt_manager, admin_claims):
        """Admin token must have iss=isA_user."""
        token = jwt_manager.create_access_token(
            admin_claims,
            expires_delta=timedelta(hours=4),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        assert payload["iss"] == "isA_user"

    def test_admin_token_has_jti(self, jwt_manager, admin_claims):
        """Admin token must have a unique jti claim."""
        token = jwt_manager.create_access_token(
            admin_claims,
            expires_delta=timedelta(hours=4),
        )
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_two_admin_tokens_have_different_jti(self, jwt_manager, admin_claims):
        """Each admin token must have a unique jti."""
        token1 = jwt_manager.create_access_token(admin_claims, expires_delta=timedelta(hours=4))
        token2 = jwt_manager.create_access_token(admin_claims, expires_delta=timedelta(hours=4))
        payload1 = jwt.decode(token1, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        payload2 = jwt.decode(token2, jwt_manager.secret_key, algorithms=["HS256"], options={"verify_aud": False})
        assert payload1["jti"] != payload2["jti"]


class TestAdminJWTVerification:
    """Test admin JWT verification via JWTManager.verify_token."""

    @pytest.fixture
    def jwt_manager(self):
        return JWTManager(
            secret_key="test-admin-secret-key-for-unit-tests",
            algorithm="HS256",
            issuer="isA_user",
        )

    def test_verify_valid_admin_token(self, jwt_manager):
        """A freshly-minted admin token must verify successfully."""
        claims = TokenClaims(
            user_id="usr_admin456",
            email="admin2@example.com",
            scope=TokenScope.ADMIN,
            token_type=TokenType.ACCESS,
            metadata={"admin_roles": ["super_admin"]},
        )
        token = jwt_manager.create_access_token(claims, expires_delta=timedelta(hours=4))
        result = jwt_manager.verify_token(token)
        assert result["valid"] is True
        assert result["user_id"] == "usr_admin456"

    def test_verify_admin_token_returns_scope(self, jwt_manager):
        """Verified admin token must return scope=admin."""
        claims = TokenClaims(
            user_id="usr_admin456",
            email="admin2@example.com",
            scope=TokenScope.ADMIN,
            token_type=TokenType.ACCESS,
            metadata={"admin_roles": ["super_admin"]},
        )
        token = jwt_manager.create_access_token(claims, expires_delta=timedelta(hours=4))
        result = jwt_manager.verify_token(token)
        assert result["valid"] is True
        payload = result.get("payload", {})
        assert payload.get("scope") == "admin"

    def test_verify_admin_token_has_admin_roles_in_metadata(self, jwt_manager):
        """Verified admin token payload must contain admin_roles."""
        claims = TokenClaims(
            user_id="usr_admin456",
            email="admin2@example.com",
            scope=TokenScope.ADMIN,
            token_type=TokenType.ACCESS,
            metadata={"admin_roles": ["product_admin", "support_admin"]},
        )
        token = jwt_manager.create_access_token(claims, expires_delta=timedelta(hours=4))
        result = jwt_manager.verify_token(token)
        payload = result.get("payload", {})
        metadata = payload.get("metadata", {})
        assert metadata.get("admin_roles") == ["product_admin", "support_admin"]
