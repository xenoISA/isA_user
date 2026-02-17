"""
Auth Models Golden Tests

🔒 GOLDEN: These tests document CURRENT behavior of auth models.
   DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions
- Document what code currently does
- All tests should PASS (they describe existing behavior)

Usage:
    pytest tests/unit/golden -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.auth_service.models import (
    AuthProvider,
    AuthUser,
    AuthSession,
    TokenVerificationRequest,
    DevTokenRequest,
    TokenPairRequest,
    RefreshTokenRequest,
    RegistrationRequest,
    RegistrationVerifyRequest,
    TokenVerificationResponse,
    TokenResponse,
    RegistrationStartResponse,
    RegistrationVerifyResponse,
    UserInfoResponse,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# AuthProvider Enum - Current Behavior
# =============================================================================

class TestAuthProviderEnum:
    """Characterization: AuthProvider enum current behavior"""

    def test_all_auth_providers_defined(self):
        """CHAR: All expected auth providers are defined"""
        expected_providers = {"auth0", "isa_user", "local"}
        actual_providers = {ap.value for ap in AuthProvider}
        assert actual_providers == expected_providers

    def test_auth_provider_values(self):
        """CHAR: Auth provider values are correct"""
        assert AuthProvider.AUTH0.value == "auth0"
        assert AuthProvider.ISA_USER.value == "isa_user"
        assert AuthProvider.LOCAL.value == "local"


# =============================================================================
# AuthUser - Current Behavior
# =============================================================================

class TestAuthUserChar:
    """Characterization: AuthUser model current behavior"""

    def test_accepts_minimal_auth_user(self):
        """CHAR: Minimal auth user is accepted"""
        user = AuthUser(
            user_id="user_123"
        )
        assert user.user_id == "user_123"
        assert user.email is None  # Default
        assert user.name is None  # Default
        assert user.is_active is True  # Default

    def test_accepts_full_auth_user(self):
        """CHAR: Full auth user with all fields is accepted"""
        now = datetime.now(timezone.utc)
        user = AuthUser(
            user_id="user_123",
            email="test@example.com",
            name="Test User",
            subscription_status="premium",
            is_active=True,
            created_at=now,
            updated_at=now
        )
        assert user.user_id == "user_123"
        assert user.email == "test@example.com"
        assert user.subscription_status == "premium"
        assert user.created_at == now

    def test_default_values(self):
        """CHAR: Default field values are correct"""
        user = AuthUser(user_id="test")
        assert user.is_active is True  # Default
        assert user.email is None  # Default
        assert user.name is None  # Default
        assert user.subscription_status is None  # Default
        assert user.created_at is None  # Default


# =============================================================================
# AuthSession - Current Behavior
# =============================================================================

class TestAuthSessionChar:
    """Characterization: AuthSession model current behavior"""

    def test_accepts_minimal_session(self):
        """CHAR: Minimal session is accepted"""
        session = AuthSession(
            session_id="sess_123",
            user_id="user_123"
        )
        assert session.session_id == "sess_123"
        assert session.user_id == "user_123"
        assert session.is_active is True  # Default

    def test_accepts_full_session(self):
        """CHAR: Full session with all fields is accepted"""
        now = datetime.now(timezone.utc)
        session = AuthSession(
            session_id="sess_123",
            user_id="user_123",
            access_token="token_123",
            refresh_token="refresh_123",
            expires_at=now + timedelta(hours=1),
            is_active=True,
            created_at=now,
            last_activity=now,
            invalidated_at=None
        )
        assert session.session_id == "sess_123"
        assert session.access_token == "token_123"
        assert session.expires_at == now + timedelta(hours=1)

    def test_optional_fields_can_be_none(self):
        """CHAR: Optional fields can be None"""
        session = AuthSession(
            session_id="sess_123",
            user_id="user_123"
        )
        assert session.access_token is None  # Default
        assert session.refresh_token is None  # Default
        assert session.expires_at is None  # Default
        assert session.created_at is None  # Default
        assert session.invalidated_at is None  # Default


# =============================================================================
# TokenVerificationRequest - Current Behavior
# =============================================================================

class TestTokenVerificationRequestChar:
    """Characterization: TokenVerificationRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal verification request is accepted"""
        request = TokenVerificationRequest(token="jwt_token_123")
        assert request.token == "jwt_token_123"
        assert request.provider is None  # Default

    def test_accepts_request_with_provider(self):
        """CHAR: Request with provider is accepted"""
        request = TokenVerificationRequest(
            token="jwt_token_123",
            provider="auth0"
        )
        assert request.token == "jwt_token_123"
        assert request.provider == "auth0"

    def test_token_is_required(self):
        """CHAR: token field is required"""
        with pytest.raises(ValidationError):
            TokenVerificationRequest()


# =============================================================================
# DevTokenRequest - Current Behavior
# =============================================================================

class TestDevTokenRequestChar:
    """Characterization: DevTokenRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal dev token request is accepted"""
        request = DevTokenRequest(
            user_id="user_123",
            email="test@example.com"
        )
        assert request.user_id == "user_123"
        assert request.email == "test@example.com"
        assert request.expires_in == 3600  # Default
        assert request.subscription_level == "free"  # Default

    def test_accepts_full_request(self):
        """CHAR: Full dev token request with all fields is accepted"""
        request = DevTokenRequest(
            user_id="user_123",
            email="test@example.com",
            expires_in=7200,
            subscription_level="premium",
            organization_id="org_123",
            permissions=["read", "write"],
            metadata={"role": "developer"}
        )
        assert request.user_id == "user_123"
        assert request.expires_in == 7200
        assert request.subscription_level == "premium"
        assert request.organization_id == "org_123"
        assert request.permissions == ["read", "write"]
        assert request.metadata["role"] == "developer"

    def test_expires_in_validation(self):
        """CHAR: expires_in validation range is 1-86400"""
        # Valid minimum
        request_min = DevTokenRequest(
            user_id="user_123",
            email="test@example.com",
            expires_in=1
        )
        assert request_min.expires_in == 1

        # Valid maximum
        request_max = DevTokenRequest(
            user_id="user_123",
            email="test@example.com",
            expires_in=86400
        )
        assert request_max.expires_in == 86400

        # Below minimum
        with pytest.raises(ValidationError):
            DevTokenRequest(
                user_id="user_123",
                email="test@example.com",
                expires_in=0
            )

        # Above maximum
        with pytest.raises(ValidationError):
            DevTokenRequest(
                user_id="user_123",
                email="test@example.com",
                expires_in=86401
            )

    def test_email_validation(self):
        """CHAR: Email field must be valid"""
        # Valid email
        request_valid = DevTokenRequest(
            user_id="user_123",
            email="user@example.com"
        )
        assert request_valid.email == "user@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            DevTokenRequest(
                user_id="user_123",
                email="invalid-email"
            )


# =============================================================================
# TokenPairRequest - Current Behavior
# =============================================================================

class TestTokenPairRequestChar:
    """Characterization: TokenPairRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal token pair request is accepted"""
        request = TokenPairRequest(
            user_id="user_123",
            email="test@example.com"
        )
        assert request.user_id == "user_123"
        assert request.email == "test@example.com"
        assert request.organization_id is None  # Default
        assert request.permissions is None  # Default

    def test_accepts_full_request(self):
        """CHAR: Full token pair request with all fields is accepted"""
        request = TokenPairRequest(
            user_id="user_123",
            email="test@example.com",
            organization_id="org_123",
            permissions=["read", "write"],
            metadata={"role": "user"}
        )
        assert request.user_id == "user_123"
        assert request.organization_id == "org_123"
        assert request.permissions == ["read", "write"]
        assert request.metadata["role"] == "user"


# =============================================================================
# RefreshTokenRequest - Current Behavior
# =============================================================================

class TestRefreshTokenRequestChar:
    """Characterization: RefreshTokenRequest current behavior"""

    def test_accepts_request(self):
        """CHAR: Valid refresh token request is accepted"""
        request = RefreshTokenRequest(refresh_token="refresh_token_123")
        assert request.refresh_token == "refresh_token_123"

    def test_refresh_token_is_required(self):
        """CHAR: refresh_token field is required"""
        with pytest.raises(ValidationError):
            RefreshTokenRequest()


# =============================================================================
# RegistrationRequest - Current Behavior
# =============================================================================

class TestRegistrationRequestChar:
    """Characterization: RegistrationRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal registration request is accepted"""
        request = RegistrationRequest(
            email="test@example.com",
            password="password123"
        )
        assert request.email == "test@example.com"
        assert request.password == "password123"
        assert request.name is None  # Default

    def test_accepts_request_with_name(self):
        """CHAR: Registration request with name is accepted"""
        request = RegistrationRequest(
            email="test@example.com",
            password="password123",
            name="Test User"
        )
        assert request.name == "Test User"

    def test_email_validation(self):
        """CHAR: Email field must be valid"""
        # Valid email
        request_valid = RegistrationRequest(
            email="user@example.com",
            password="password123"
        )
        assert request_valid.email == "user@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="invalid-email",
                password="password123"
            )

    def test_password_validation(self):
        """CHAR: Password must be at least 8 characters"""
        # Valid minimum length
        request_valid = RegistrationRequest(
            email="test@example.com",
            password="12345678"
        )
        assert request_valid.password == "12345678"

        # Too short
        with pytest.raises(ValidationError):
            RegistrationRequest(
                email="test@example.com",
                password="1234567"  # 7 characters
            )

    def test_required_fields(self):
        """CHAR: Email and password are required"""
        # Missing email
        with pytest.raises(ValidationError):
            RegistrationRequest(password="password123")

        # Missing password
        with pytest.raises(ValidationError):
            RegistrationRequest(email="test@example.com")


# =============================================================================
# RegistrationVerifyRequest - Current Behavior
# =============================================================================

class TestRegistrationVerifyRequestChar:
    """Characterization: RegistrationVerifyRequest current behavior"""

    def test_accepts_request(self):
        """CHAR: Valid verification request is accepted"""
        request = RegistrationVerifyRequest(
            pending_registration_id="reg_123",
            code="123456"
        )
        assert request.pending_registration_id == "reg_123"
        assert request.code == "123456"

    def test_required_fields(self):
        """CHAR: Both fields are required"""
        # Missing pending_registration_id
        with pytest.raises(ValidationError):
            RegistrationVerifyRequest(code="123456")

        # Missing code
        with pytest.raises(ValidationError):
            RegistrationVerifyRequest(pending_registration_id="reg_123")


# =============================================================================
# TokenVerificationResponse - Current Behavior
# =============================================================================

class TestTokenVerificationResponseChar:
    """Characterization: TokenVerificationResponse current behavior"""

    def test_accepts_valid_response(self):
        """CHAR: Valid verification response is accepted"""
        now = datetime.now(timezone.utc)
        response = TokenVerificationResponse(
            valid=True,
            provider="isa_user",
            user_id="user_123",
            email="test@example.com",
            subscription_level="premium",
            organization_id="org_123",
            expires_at=now
        )
        assert response.valid is True
        assert response.provider == "isa_user"
        assert response.user_id == "user_123"

    def test_invalid_response(self):
        """CHAR: Invalid response with error"""
        response = TokenVerificationResponse(
            valid=False,
            error="Token expired"
        )
        assert response.valid is False
        assert response.error == "Token expired"
        assert response.user_id is None  # Default when invalid
        assert response.email is None  # Default when invalid

    def test_optional_fields_can_be_none(self):
        """CHAR: Optional fields can be None"""
        response = TokenVerificationResponse(valid=True)
        assert response.provider is None
        assert response.user_id is None
        assert response.email is None
        assert response.subscription_level is None
        assert response.organization_id is None
        assert response.expires_at is None


# =============================================================================
# TokenResponse - Current Behavior
# =============================================================================

class TestTokenResponseChar:
    """Characterization: TokenResponse current behavior"""

    def test_accepts_success_response(self):
        """CHAR: Successful token response is accepted"""
        response = TokenResponse(
            success=True,
            token="jwt_token_123",
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            expires_in=3600,
            user_id="user_123",
            email="test@example.com",
            provider="isa_user"
        )
        assert response.success is True
        assert response.token == "jwt_token_123"
        assert response.access_token == "access_token_123"
        assert response.token_type == "Bearer"  # Default

    def test_accepts_failure_response(self):
        """CHAR: Failed token response is accepted"""
        response = TokenResponse(
            success=False,
            error="Invalid credentials"
        )
        assert response.success is False
        assert response.error == "Invalid credentials"
        assert response.token is None  # Default when failed
        assert response.access_token is None  # Default when failed

    def test_default_token_type(self):
        """CHAR: Default token type is Bearer"""
        response = TokenResponse(success=True)
        assert response.token_type == "Bearer"


# =============================================================================
# RegistrationStartResponse - Current Behavior
# =============================================================================

class TestRegistrationStartResponseChar:
    """Characterization: RegistrationStartResponse current behavior"""

    def test_accepts_response(self):
        """CHAR: Valid registration start response is accepted"""
        response = RegistrationStartResponse(
            pending_registration_id="reg_123",
            verification_required=True,
            expires_at="2024-01-01T00:00:00Z"
        )
        assert response.pending_registration_id == "reg_123"
        assert response.verification_required is True  # Default
        assert response.expires_at == "2024-01-01T00:00:00Z"

    def test_defaults(self):
        """CHAR: Default values are correct"""
        response = RegistrationStartResponse(
            pending_registration_id="reg_123",
            expires_at="2024-01-01T00:00:00Z"  # Required field
        )
        assert response.verification_required is True  # Default


# =============================================================================
# RegistrationVerifyResponse - Current Behavior
# =============================================================================

class TestRegistrationVerifyResponseChar:
    """Characterization: RegistrationVerifyResponse current behavior"""

    def test_accepts_success_response(self):
        """CHAR: Successful verification response is accepted"""
        response = RegistrationVerifyResponse(
            success=True,
            user_id="user_123",
            email="test@example.com",
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            token_type="Bearer",
            expires_in=3600
        )
        assert response.success is True
        assert response.user_id == "user_123"
        assert response.access_token == "access_token_123"

    def test_accepts_failure_response(self):
        """CHAR: Failed verification response is accepted"""
        response = RegistrationVerifyResponse(
            success=False,
            error="Invalid code"
        )
        assert response.success is False
        assert response.error == "Invalid code"
        assert response.user_id is None  # Default when failed

    def test_optional_fields_can_be_none(self):
        """CHAR: Optional fields can be None"""
        response = RegistrationVerifyResponse(success=True)
        assert response.access_token is None
        assert response.refresh_token is None
        assert response.token_type is None
        assert response.expires_in is None


# =============================================================================
# UserInfoResponse - Current Behavior
# =============================================================================

class TestUserInfoResponseChar:
    """Characterization: UserInfoResponse current behavior"""

    def test_accepts_minimal_info(self):
        """CHAR: Minimal user info is accepted"""
        info = UserInfoResponse(
            user_id="user_123",
            email="test@example.com",
            provider="isa_user"
        )
        assert info.user_id == "user_123"
        assert info.email == "test@example.com"
        assert info.permissions == []  # Default
        assert info.organization_id is None  # Default
        assert info.expires_at is None  # Default

    def test_accepts_full_info(self):
        """CHAR: Full user info with all fields is accepted"""
        now = datetime.now(timezone.utc)
        info = UserInfoResponse(
            user_id="user_123",
            email="test@example.com",
            organization_id="org_123",
            permissions=["read", "write"],
            provider="auth0",
            expires_at=now
        )
        assert info.organization_id == "org_123"
        assert info.permissions == ["read", "write"]
        assert info.provider == "auth0"
        assert info.expires_at == now

    def test_default_permissions(self):
        """CHAR: Default permissions is empty list"""
        info = UserInfoResponse(
            user_id="user_123",
            email="test@example.com",
            provider="isa_user"
        )
        assert info.permissions == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
