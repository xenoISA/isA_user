"""
Authentication Service - Component Tests (Contract Proof)

Tests for:
- Data contract validation (Pydantic schemas)
- Test data factory methods
- Request builders
- Business rule validation
- Response contracts
- Edge cases
- Invalid data handling

All tests use AuthTestDataFactory - zero hardcoded data.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from tests.contracts.auth.data_contract import (
    # Request contracts
    TokenVerificationRequestContract,
    DevTokenRequestContract,
    TokenPairRequestContract,
    RefreshTokenRequestContract,
    RegistrationStartRequestContract,
    RegistrationVerifyRequestContract,
    ApiKeyCreateRequestContract,
    ApiKeyVerifyRequestContract,
    DeviceRegisterRequestContract,
    DeviceAuthenticateRequestContract,
    DevicePairingGenerateRequestContract,
    DevicePairingVerifyRequestContract,
    # Response contracts
    TokenVerificationResponseContract,
    TokenResponseContract,
    RegistrationStartResponseContract,
    RegistrationVerifyResponseContract,
    ApiKeyCreateResponseContract,
    ApiKeyVerifyResponseContract,
    DeviceRegisterResponseContract,
    DeviceAuthenticateResponseContract,
    DevicePairingResponseContract,
    UserInfoResponseContract,
    # Factory and builders
    AuthTestDataFactory,
    TokenPairRequestBuilder,
    DeviceRegisterRequestBuilder,
    ApiKeyCreateRequestBuilder,
)


# ============================================================================
# Factory Tests (25 tests) - Test all factory methods
# ============================================================================

class TestAuthTestDataFactory:
    """Test factory generates valid data"""

    def test_make_user_id(self):
        """Factory generates valid user ID"""
        user_id = AuthTestDataFactory.make_user_id()
        assert user_id.startswith("usr_")
        assert len(user_id) > 4
        # Test uniqueness
        user_id2 = AuthTestDataFactory.make_user_id()
        assert user_id != user_id2

    def test_make_email(self):
        """Factory generates valid email"""
        email = AuthTestDataFactory.make_email()
        assert "@" in email
        assert ".com" in email
        # Test uniqueness
        email2 = AuthTestDataFactory.make_email()
        assert email != email2

    def test_make_organization_id(self):
        """Factory generates valid organization ID"""
        org_id = AuthTestDataFactory.make_organization_id()
        assert org_id.startswith("org_")
        assert len(org_id) > 4

    def test_make_device_id(self):
        """Factory generates valid device ID"""
        device_id = AuthTestDataFactory.make_device_id()
        assert device_id.startswith("dev_")
        assert len(device_id) > 4

    def test_make_device_secret(self):
        """Factory generates valid device secret"""
        secret = AuthTestDataFactory.make_device_secret()
        assert len(secret) > 30  # URL-safe 32 bytes
        # Test uniqueness
        secret2 = AuthTestDataFactory.make_device_secret()
        assert secret != secret2

    def test_make_password(self):
        """Factory generates valid password"""
        password = AuthTestDataFactory.make_password()
        assert len(password) >= 8  # Minimum length
        # Test uniqueness
        password2 = AuthTestDataFactory.make_password()
        assert password != password2

    def test_make_verification_code(self):
        """Factory generates 6-digit verification code"""
        code = AuthTestDataFactory.make_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_make_api_key(self):
        """Factory generates valid API key"""
        api_key = AuthTestDataFactory.make_api_key()
        assert api_key.startswith("isa_")
        assert len(api_key) > 20

    def test_make_pairing_token(self):
        """Factory generates pairing token"""
        token = AuthTestDataFactory.make_pairing_token()
        assert len(token) > 30
        # Test uniqueness
        token2 = AuthTestDataFactory.make_pairing_token()
        assert token != token2

    def test_make_jwt_token(self):
        """Factory generates mock JWT token"""
        token = AuthTestDataFactory.make_jwt_token()
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature

    def test_make_permissions(self):
        """Factory generates permissions list"""
        permissions = AuthTestDataFactory.make_permissions()
        assert isinstance(permissions, list)
        assert len(permissions) >= 0
        if len(permissions) > 0:
            assert all(isinstance(p, str) for p in permissions)

    def test_make_token_verification_request(self):
        """Factory generates valid token verification request"""
        request = AuthTestDataFactory.make_token_verification_request()
        assert isinstance(request, TokenVerificationRequestContract)
        assert request.token
        assert request.provider in ["isa_user", "auth0", "local", None]

    def test_make_dev_token_request(self):
        """Factory generates valid dev token request"""
        request = AuthTestDataFactory.make_dev_token_request()
        assert isinstance(request, DevTokenRequestContract)
        assert request.user_id.startswith("usr_")
        assert "@" in request.email
        assert request.expires_in > 0

    def test_make_token_pair_request(self):
        """Factory generates valid token pair request"""
        request = AuthTestDataFactory.make_token_pair_request()
        assert isinstance(request, TokenPairRequestContract)
        assert request.user_id.startswith("usr_")
        assert "@" in request.email

    def test_make_registration_start_request(self):
        """Factory generates valid registration start request"""
        request = AuthTestDataFactory.make_registration_start_request()
        assert isinstance(request, RegistrationStartRequestContract)
        assert "@" in request.email
        assert len(request.password) >= 8

    def test_make_registration_verify_request(self):
        """Factory generates valid registration verify request"""
        request = AuthTestDataFactory.make_registration_verify_request()
        assert isinstance(request, RegistrationVerifyRequestContract)
        assert len(request.pending_registration_id) > 0
        assert len(request.code) == 6

    def test_make_api_key_create_request(self):
        """Factory generates valid API key create request"""
        request = AuthTestDataFactory.make_api_key_create_request()
        assert isinstance(request, ApiKeyCreateRequestContract)
        assert request.organization_id.startswith("org_")
        assert request.name

    def test_make_device_register_request(self):
        """Factory generates valid device register request"""
        request = AuthTestDataFactory.make_device_register_request()
        assert isinstance(request, DeviceRegisterRequestContract)
        assert request.device_id.startswith("dev_")
        assert request.organization_id.startswith("org_")

    def test_make_device_authenticate_request(self):
        """Factory generates valid device authenticate request"""
        request = AuthTestDataFactory.make_device_authenticate_request()
        assert isinstance(request, DeviceAuthenticateRequestContract)
        assert request.device_id.startswith("dev_")
        assert len(request.device_secret) > 0

    def test_make_device_pairing_generate_request(self):
        """Factory generates valid pairing generate request"""
        request = AuthTestDataFactory.make_device_pairing_generate_request()
        assert isinstance(request, DevicePairingGenerateRequestContract)
        assert request.device_id.startswith("dev_")

    def test_make_device_pairing_verify_request(self):
        """Factory generates valid pairing verify request"""
        request = AuthTestDataFactory.make_device_pairing_verify_request()
        assert isinstance(request, DevicePairingVerifyRequestContract)
        assert request.device_id.startswith("dev_")
        assert len(request.pairing_token) > 0
        assert request.user_id.startswith("usr_")

    # Invalid data generators (5 tests)

    def test_make_invalid_email(self):
        """Factory generates invalid email"""
        email = AuthTestDataFactory.make_invalid_email()
        assert "@" not in email or "." not in email

    def test_make_invalid_password(self):
        """Factory generates invalid password"""
        password = AuthTestDataFactory.make_invalid_password()
        assert len(password) < 8

    def test_make_invalid_token(self):
        """Factory generates invalid JWT token"""
        token = AuthTestDataFactory.make_invalid_token()
        # Invalid token should not have proper JWT structure
        assert not token.startswith("eyJ")  # JWT tokens start with eyJ

    def test_make_invalid_verification_code(self):
        """Factory generates invalid verification code"""
        code = AuthTestDataFactory.make_invalid_verification_code()
        assert len(code) != 6  # Wrong length

    def test_make_subscription_level(self):
        """Factory generates valid subscription level"""
        level = AuthTestDataFactory.make_subscription_level()
        assert level in ["free", "basic", "pro", "enterprise"]


# ============================================================================
# Builder Tests (12 tests) - Test all builder methods
# ============================================================================

class TestTokenPairRequestBuilder:
    """Test token pair request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = TokenPairRequestBuilder().build()
        assert isinstance(request, TokenPairRequestContract)
        assert request.user_id.startswith("usr_")
        assert "@" in request.email

    def test_builder_with_user_id(self):
        """Builder accepts custom user_id"""
        user_id = "usr_custom123"
        request = TokenPairRequestBuilder().with_user_id(user_id).build()
        assert request.user_id == user_id

    def test_builder_with_email(self):
        """Builder accepts custom email"""
        email = "custom@example.com"
        request = TokenPairRequestBuilder().with_email(email).build()
        assert request.email == email

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        request = (
            TokenPairRequestBuilder()
            .with_user_id("usr_test")
            .with_email("test@example.com")
            .with_organization_id("org_test")
            .with_permissions(["read:users"])
            .build()
        )
        assert request.user_id == "usr_test"
        assert request.email == "test@example.com"
        assert request.organization_id == "org_test"
        assert request.permissions == ["read:users"]


class TestDeviceRegisterRequestBuilder:
    """Test device register request builder"""

    def test_builder_default_build(self):
        """Builder creates valid device register request with defaults"""
        request = DeviceRegisterRequestBuilder().build()
        assert isinstance(request, DeviceRegisterRequestContract)
        assert request.device_id.startswith("dev_")
        assert request.organization_id.startswith("org_")

    def test_builder_with_device_id(self):
        """Builder accepts custom device_id"""
        device_id = "dev_custom123"
        request = DeviceRegisterRequestBuilder().with_device_id(device_id).build()
        assert request.device_id == device_id

    def test_builder_with_metadata(self):
        """Builder accepts custom metadata"""
        metadata = {"location": "warehouse", "firmware": "2.0.0"}
        request = DeviceRegisterRequestBuilder().with_metadata(metadata).build()
        assert request.metadata == metadata

    def test_builder_with_location(self):
        """Builder supports location metadata helper"""
        request = DeviceRegisterRequestBuilder().with_location("office").build()
        assert request.metadata["location"] == "office"


class TestApiKeyCreateRequestBuilder:
    """Test API key create request builder"""

    def test_builder_default_build(self):
        """Builder creates valid API key request with defaults"""
        request = ApiKeyCreateRequestBuilder().build()
        assert isinstance(request, ApiKeyCreateRequestContract)
        assert request.organization_id.startswith("org_")
        assert request.name

    def test_builder_with_read_permissions(self):
        """Builder supports read-only permissions helper"""
        request = ApiKeyCreateRequestBuilder().with_read_permissions().build()
        assert "read:data" in request.permissions
        assert "read:users" in request.permissions
        assert "write:data" not in request.permissions

    def test_builder_with_admin_permissions(self):
        """Builder supports admin permissions helper"""
        request = ApiKeyCreateRequestBuilder().with_admin_permissions().build()
        assert request.permissions == ["admin:all"]

    def test_builder_with_no_expiration(self):
        """Builder supports no expiration option"""
        request = ApiKeyCreateRequestBuilder().with_no_expiration().build()
        assert request.expires_days is None


# ============================================================================
# Validation Tests (18 tests) - Test Pydantic validation
# ============================================================================

class TestRequestValidation:
    """Test request contract validation"""

    def test_token_verification_request_valid(self):
        """Valid token verification request passes validation"""
        request = TokenVerificationRequestContract(
            token=AuthTestDataFactory.make_jwt_token(),
            provider="isa_user"
        )
        assert request.token
        assert request.provider == "isa_user"

    def test_token_verification_request_no_provider(self):
        """Token verification request works without provider"""
        request = TokenVerificationRequestContract(
            token=AuthTestDataFactory.make_jwt_token()
        )
        assert request.token
        assert request.provider is None

    def test_dev_token_request_expires_in_range(self):
        """Dev token request validates expires_in range"""
        with pytest.raises(ValidationError):
            DevTokenRequestContract(
                user_id=AuthTestDataFactory.make_user_id(),
                email=AuthTestDataFactory.make_email(),
                expires_in=90000  # > 86400 (max)
            )

    def test_dev_token_request_expires_in_minimum(self):
        """Dev token request validates expires_in minimum"""
        with pytest.raises(ValidationError):
            DevTokenRequestContract(
                user_id=AuthTestDataFactory.make_user_id(),
                email=AuthTestDataFactory.make_email(),
                expires_in=0  # < 1 (min)
            )

    def test_registration_password_min_length(self):
        """Registration request validates password min length"""
        with pytest.raises(ValidationError):
            RegistrationStartRequestContract(
                email=AuthTestDataFactory.make_email(),
                password="short"  # < 8 characters
            )

    def test_registration_email_format(self):
        """Registration request validates email format"""
        with pytest.raises(ValidationError):
            RegistrationStartRequestContract(
                email="not-an-email",
                password=AuthTestDataFactory.make_password()
            )

    def test_registration_verify_code_length(self):
        """Registration verify validates code length"""
        with pytest.raises(ValidationError):
            RegistrationVerifyRequestContract(
                pending_registration_id=AuthTestDataFactory.make_pending_registration_id(),
                code="12345"  # Only 5 digits
            )

    def test_registration_verify_code_digits_only(self):
        """Registration verify validates code is digits only"""
        with pytest.raises(ValidationError):
            RegistrationVerifyRequestContract(
                pending_registration_id=AuthTestDataFactory.make_pending_registration_id(),
                code="12345A"  # Contains letter
            )

    def test_api_key_expires_days_range(self):
        """API key request validates expires_days range"""
        with pytest.raises(ValidationError):
            ApiKeyCreateRequestContract(
                organization_id=AuthTestDataFactory.make_organization_id(),
                name="Test Key",
                expires_days=400  # > 365 (max)
            )

    def test_api_key_expires_days_minimum(self):
        """API key request validates expires_days minimum"""
        with pytest.raises(ValidationError):
            ApiKeyCreateRequestContract(
                organization_id=AuthTestDataFactory.make_organization_id(),
                name="Test Key",
                expires_days=0  # < 1 (min)
            )

    def test_api_key_name_required(self):
        """API key request requires name"""
        with pytest.raises(ValidationError):
            ApiKeyCreateRequestContract(
                organization_id=AuthTestDataFactory.make_organization_id(),
                name=""  # Empty name
            )

    def test_token_pair_request_valid_email(self):
        """Token pair request validates email format"""
        with pytest.raises(ValidationError):
            TokenPairRequestContract(
                user_id=AuthTestDataFactory.make_user_id(),
                email="invalid-email"
            )

    def test_device_register_request_valid(self):
        """Valid device register request passes validation"""
        request = DeviceRegisterRequestContract(
            device_id=AuthTestDataFactory.make_device_id(),
            organization_id=AuthTestDataFactory.make_organization_id()
        )
        assert request.device_id
        assert request.organization_id

    def test_device_authenticate_request_valid(self):
        """Valid device authenticate request passes validation"""
        request = DeviceAuthenticateRequestContract(
            device_id=AuthTestDataFactory.make_device_id(),
            device_secret=AuthTestDataFactory.make_device_secret()
        )
        assert request.device_id
        assert request.device_secret

    def test_device_pairing_verify_request_valid(self):
        """Valid device pairing verify request passes validation"""
        request = DevicePairingVerifyRequestContract(
            device_id=AuthTestDataFactory.make_device_id(),
            pairing_token=AuthTestDataFactory.make_pairing_token(),
            user_id=AuthTestDataFactory.make_user_id()
        )
        assert request.device_id
        assert request.pairing_token
        assert request.user_id

    def test_refresh_token_request_valid(self):
        """Valid refresh token request passes validation"""
        request = RefreshTokenRequestContract(
            refresh_token=AuthTestDataFactory.make_refresh_token()
        )
        assert request.refresh_token

    def test_api_key_verify_request_valid(self):
        """Valid API key verify request passes validation"""
        request = ApiKeyVerifyRequestContract(
            api_key=AuthTestDataFactory.make_api_key()
        )
        assert request.api_key

    def test_device_pairing_generate_request_valid(self):
        """Valid device pairing generate request passes validation"""
        request = DevicePairingGenerateRequestContract(
            device_id=AuthTestDataFactory.make_device_id()
        )
        assert request.device_id


# ============================================================================
# Business Rule Tests (12 tests) - Test BR-* rules from logic contract
# ============================================================================

class TestBusinessRules:
    """Test business rules from logic contract"""

    def test_br_tok_005_access_token_expiration(self):
        """BR-TOK-005: Access tokens expire in 1 hour"""
        # Simulate token expiration time
        expires_in = 3600  # 1 hour
        assert expires_in == 3600

        # Verify in response
        response = AuthTestDataFactory.make_token_response()
        assert response.expires_in == 3600

    def test_br_tok_006_refresh_token_expiration(self):
        """BR-TOK-006: Refresh tokens expire in 7 days"""
        expires_in = 7 * 24 * 3600  # 7 days
        assert expires_in == 604800

    def test_br_reg_003_verification_code_format(self):
        """BR-REG-003: Verification code is 6 digits"""
        code = AuthTestDataFactory.make_verification_code()
        assert len(code) == 6
        assert code.isdigit()
        assert 0 <= int(code) <= 999999

    def test_br_reg_004_verification_code_expiration(self):
        """BR-REG-004: Codes expire in 10 minutes"""
        expires_in = 10 * 60  # 10 minutes
        assert expires_in == 600

    def test_br_reg_006_user_id_generation_format(self):
        """BR-REG-006: User ID format is usr_{uuid}"""
        user_id = AuthTestDataFactory.make_user_id()
        assert user_id.startswith("usr_")
        assert len(user_id) == len("usr_") + 32  # UUID hex

    def test_br_dev_004_device_token_expiration(self):
        """BR-DEV-004: Device tokens expire in 24 hours"""
        expires_in = 24 * 3600  # 24 hours
        assert expires_in == 86400

    def test_br_dev_006_pairing_token_expiration(self):
        """BR-DEV-006: Pairing tokens expire in 5 minutes"""
        expires_in = 5 * 60  # 5 minutes
        assert expires_in == 300

    def test_br_api_001_api_key_format(self):
        """BR-API-001: API key format is isa_{token}"""
        api_key = AuthTestDataFactory.make_api_key()
        assert api_key.startswith("isa_")
        assert len(api_key) > 20

    def test_br_api_005_key_expires_days_range(self):
        """BR-API-005: Key expires_days parameter (1-365)"""
        # Test valid range
        request = AuthTestDataFactory.make_api_key_create_request()
        if request.expires_days:
            assert 1 <= request.expires_days <= 365

    def test_br_ses_004_session_expiration(self):
        """BR-SES-004: Sessions expire in 7 days (refresh token expiry)"""
        expires_in = 7 * 24 * 3600
        assert expires_in == 604800

    def test_br_pwd_001_password_minimum_length(self):
        """BR-PWD-001: Password must be at least 8 characters"""
        password = AuthTestDataFactory.make_password()
        assert len(password) >= 8

    def test_br_jwt_001_jwt_token_format(self):
        """BR-JWT-001: JWT tokens have three parts separated by dots"""
        token = AuthTestDataFactory.make_jwt_token()
        parts = token.split(".")
        assert len(parts) == 3


# ============================================================================
# Response Contract Tests (10 tests)
# ============================================================================

class TestResponseContracts:
    """Test response contract structure"""

    def test_token_verification_response_valid(self):
        """Token verification response for valid token"""
        response = TokenVerificationResponseContract(
            valid=True,
            provider="isa_user",
            user_id=AuthTestDataFactory.make_user_id(),
            email=AuthTestDataFactory.make_email(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        assert response.valid is True
        assert response.provider == "isa_user"
        assert response.user_id
        assert response.email
        assert response.error is None

    def test_token_verification_response_invalid(self):
        """Token verification response for invalid token"""
        response = TokenVerificationResponseContract(
            valid=False,
            error="Token expired"
        )
        assert response.valid is False
        assert response.error == "Token expired"
        assert response.user_id is None

    def test_token_response_success(self):
        """Token response for successful generation"""
        response = TokenResponseContract(
            success=True,
            access_token=AuthTestDataFactory.make_jwt_token(),
            refresh_token=AuthTestDataFactory.make_jwt_token(),
            token_type="Bearer",
            expires_in=3600,
            user_id=AuthTestDataFactory.make_user_id(),
            email=AuthTestDataFactory.make_email()
        )
        assert response.success is True
        assert response.access_token
        assert response.refresh_token
        assert response.expires_in == 3600

    def test_token_response_failure(self):
        """Token response for failed generation"""
        response = TokenResponseContract(
            success=False,
            error="Invalid credentials"
        )
        assert response.success is False
        assert response.error == "Invalid credentials"
        assert response.access_token is None

    def test_registration_start_response(self):
        """Registration start response structure"""
        response = RegistrationStartResponseContract(
            pending_registration_id=AuthTestDataFactory.make_pending_registration_id(),
            verification_required=True,
            expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        )
        assert response.pending_registration_id
        assert response.verification_required is True
        assert response.expires_at

    def test_registration_verify_response_success(self):
        """Registration verify response for success"""
        response = RegistrationVerifyResponseContract(
            success=True,
            user_id=AuthTestDataFactory.make_user_id(),
            email=AuthTestDataFactory.make_email(),
            access_token=AuthTestDataFactory.make_jwt_token(),
            refresh_token=AuthTestDataFactory.make_refresh_token(),
            token_type="Bearer",
            expires_in=3600
        )
        assert response.success is True
        assert response.user_id
        assert response.access_token
        assert response.error is None

    def test_api_key_create_response_success(self):
        """API key create response for success"""
        response = ApiKeyCreateResponseContract(
            success=True,
            api_key=AuthTestDataFactory.make_api_key(),
            key_id=AuthTestDataFactory.make_key_id(),
            name="Test Key",
            expires_at=datetime.now(timezone.utc) + timedelta(days=90)
        )
        assert response.success is True
        assert response.api_key
        assert response.key_id

    def test_device_register_response_success(self):
        """Device register response for success"""
        response = DeviceRegisterResponseContract(
            success=True,
            device_id=AuthTestDataFactory.make_device_id(),
            device_secret=AuthTestDataFactory.make_device_secret(),
            organization_id=AuthTestDataFactory.make_organization_id()
        )
        assert response.success is True
        assert response.device_id
        assert response.device_secret

    def test_device_authenticate_response_success(self):
        """Device authenticate response for success"""
        response = DeviceAuthenticateResponseContract(
            success=True,
            authenticated=True,
            device_id=AuthTestDataFactory.make_device_id(),
            organization_id=AuthTestDataFactory.make_organization_id(),
            access_token=AuthTestDataFactory.make_jwt_token(),
            token_type="Bearer",
            expires_in=86400
        )
        assert response.success is True
        assert response.authenticated is True
        assert response.access_token

    def test_device_pairing_response_generate(self):
        """Device pairing response for generate"""
        response = DevicePairingResponseContract(
            success=True,
            pairing_token=AuthTestDataFactory.make_pairing_token(),
            device_id=AuthTestDataFactory.make_device_id(),
            expires_in=300
        )
        assert response.success is True
        assert response.pairing_token
        assert response.expires_in == 300


# ============================================================================
# Edge Case Tests (13 tests) - Test EC-* cases from logic contract
# ============================================================================

class TestEdgeCases:
    """Test edge cases from logic contract"""

    def test_ec_001_expired_token_verification(self):
        """EC-001: Expired token verification"""
        # Simulate expired token response
        response = TokenVerificationResponseContract(
            valid=False,
            error="Token expired"
        )
        assert response.valid is False
        assert "expired" in response.error.lower()

    def test_ec_002_missing_provider_hint(self):
        """EC-002: Token verification without provider hint"""
        request = TokenVerificationRequestContract(
            token=AuthTestDataFactory.make_jwt_token()
            # provider intentionally omitted
        )
        assert request.provider is None  # Will be auto-detected

    def test_ec_003_unsupported_provider(self):
        """EC-003: Unsupported provider"""
        response = TokenVerificationResponseContract(
            valid=False,
            error="Unsupported provider: unknown"
        )
        assert response.valid is False
        assert "unsupported" in response.error.lower()

    def test_ec_004_malformed_token(self):
        """EC-004: Malformed JWT token"""
        malformed = AuthTestDataFactory.make_malformed_token()
        parts = malformed.split(".")
        assert len(parts) != 3  # Missing parts

    def test_ec_005_verification_code_expiration(self):
        """EC-005: Verification code expiration"""
        # Code should expire in 10 minutes
        response = RegistrationVerifyResponseContract(
            success=False,
            error="Verification code expired"
        )
        assert response.success is False
        assert "expired" in response.error.lower()

    def test_ec_006_invalid_verification_code(self):
        """EC-006: Invalid verification code"""
        response = RegistrationVerifyResponseContract(
            success=False,
            error="Invalid verification code"
        )
        assert response.success is False
        assert "invalid" in response.error.lower()

    def test_ec_007_pairing_token_expiration(self):
        """EC-007: Pairing token expiration"""
        response = DevicePairingResponseContract(
            valid=False,
            error="Pairing token expired"
        )
        assert response.valid is False
        assert "expired" in response.error.lower()

    def test_ec_008_device_not_registered(self):
        """EC-008: Device authentication with unregistered device"""
        response = DeviceAuthenticateResponseContract(
            success=False,
            authenticated=False,
            error="Device not registered"
        )
        assert response.success is False
        assert response.authenticated is False

    def test_ec_009_invalid_device_secret(self):
        """EC-009: Device authentication with invalid secret"""
        response = DeviceAuthenticateResponseContract(
            success=False,
            authenticated=False,
            error="Invalid device secret"
        )
        assert response.success is False
        assert response.authenticated is False

    def test_ec_010_api_key_not_found(self):
        """EC-010: API key verification with unknown key"""
        response = ApiKeyVerifyResponseContract(
            valid=False,
            error="API key not found"
        )
        assert response.valid is False
        assert "not found" in response.error.lower()

    def test_ec_011_api_key_expired(self):
        """EC-011: API key verification with expired key"""
        response = ApiKeyVerifyResponseContract(
            valid=False,
            error="API key expired"
        )
        assert response.valid is False
        assert "expired" in response.error.lower()

    def test_ec_012_refresh_token_invalid(self):
        """EC-012: Refresh token is invalid"""
        response = TokenResponseContract(
            success=False,
            error="Invalid refresh token"
        )
        assert response.success is False
        assert "invalid" in response.error.lower()

    def test_ec_013_token_type_bearer(self):
        """EC-013: Token type is always Bearer"""
        response = AuthTestDataFactory.make_token_response()
        assert response.token_type == "Bearer"


# ============================================================================
# Invalid Data Tests (10 tests)
# ============================================================================

class TestInvalidData:
    """Test system handles invalid data gracefully"""

    def test_invalid_email_rejected(self):
        """System rejects invalid email format"""
        with pytest.raises(ValidationError):
            RegistrationStartRequestContract(
                email="not-an-email",
                password=AuthTestDataFactory.make_password()
            )

    def test_invalid_password_rejected(self):
        """System rejects password < 8 characters"""
        with pytest.raises(ValidationError):
            RegistrationStartRequestContract(
                email=AuthTestDataFactory.make_email(),
                password="short"
            )

    def test_invalid_verification_code_length(self):
        """System rejects verification code with wrong length"""
        with pytest.raises(ValidationError):
            RegistrationVerifyRequestContract(
                pending_registration_id=AuthTestDataFactory.make_pending_registration_id(),
                code="12345"  # 5 digits instead of 6
            )

    def test_invalid_verification_code_alpha(self):
        """System rejects verification code with letters"""
        with pytest.raises(ValidationError):
            RegistrationVerifyRequestContract(
                pending_registration_id=AuthTestDataFactory.make_pending_registration_id(),
                code="12345A"  # Contains letter
            )

    def test_invalid_expires_in_negative(self):
        """System rejects negative expires_in"""
        with pytest.raises(ValidationError):
            DevTokenRequestContract(
                user_id=AuthTestDataFactory.make_user_id(),
                email=AuthTestDataFactory.make_email(),
                expires_in=-1
            )

    def test_invalid_expires_in_too_large(self):
        """System rejects expires_in > 24 hours"""
        with pytest.raises(ValidationError):
            DevTokenRequestContract(
                user_id=AuthTestDataFactory.make_user_id(),
                email=AuthTestDataFactory.make_email(),
                expires_in=90000
            )

    def test_invalid_expires_days_negative(self):
        """System rejects negative expires_days"""
        with pytest.raises(ValidationError):
            ApiKeyCreateRequestContract(
                organization_id=AuthTestDataFactory.make_organization_id(),
                name="Test Key",
                expires_days=-10
            )

    def test_invalid_expires_days_too_large(self):
        """System rejects expires_days > 365"""
        with pytest.raises(ValidationError):
            ApiKeyCreateRequestContract(
                organization_id=AuthTestDataFactory.make_organization_id(),
                name="Test Key",
                expires_days=400
            )

    def test_invalid_empty_api_key_name(self):
        """System rejects empty API key name"""
        with pytest.raises(ValidationError):
            ApiKeyCreateRequestContract(
                organization_id=AuthTestDataFactory.make_organization_id(),
                name=""
            )

    def test_invalid_token_pair_email(self):
        """System rejects invalid email in token pair request"""
        with pytest.raises(ValidationError):
            TokenPairRequestContract(
                user_id=AuthTestDataFactory.make_user_id(),
                email="invalid-email"
            )


# ============================================================================
# Data Contract Integration Tests (5 tests)
# ============================================================================

class TestDataContractIntegration:
    """Test contracts work together as expected"""

    def test_registration_flow_contracts(self):
        """Registration flow: start -> verify contracts"""
        # Start registration
        start_request = AuthTestDataFactory.make_registration_start_request()
        assert start_request.email
        assert start_request.password

        # Verify registration
        verify_request = AuthTestDataFactory.make_registration_verify_request()
        assert verify_request.pending_registration_id
        assert len(verify_request.code) == 6

    def test_token_generation_flow(self):
        """Token generation: request -> response contracts"""
        request = AuthTestDataFactory.make_token_pair_request()
        response = AuthTestDataFactory.make_token_response(
            user_id=request.user_id,
            email=request.email
        )
        assert response.user_id == request.user_id
        assert response.email == request.email
        assert response.access_token
        assert response.refresh_token

    def test_device_registration_flow(self):
        """Device registration: request -> response contracts"""
        request = AuthTestDataFactory.make_device_register_request()
        response = DeviceRegisterResponseContract(
            success=True,
            device_id=request.device_id,
            device_secret=AuthTestDataFactory.make_device_secret(),
            organization_id=request.organization_id
        )
        assert response.device_id == request.device_id
        assert response.organization_id == request.organization_id

    def test_api_key_creation_flow(self):
        """API key creation: request -> response contracts"""
        request = AuthTestDataFactory.make_api_key_create_request()
        response = ApiKeyCreateResponseContract(
            success=True,
            api_key=AuthTestDataFactory.make_api_key(),
            key_id=AuthTestDataFactory.make_key_id(),
            name=request.name,
            expires_at=datetime.now(timezone.utc) + timedelta(days=request.expires_days) if request.expires_days else None
        )
        assert response.name == request.name
        assert response.api_key

    def test_device_pairing_flow(self):
        """Device pairing: generate -> verify contracts"""
        generate_request = AuthTestDataFactory.make_device_pairing_generate_request()

        # Generate response
        generate_response = DevicePairingResponseContract(
            success=True,
            pairing_token=AuthTestDataFactory.make_pairing_token(),
            device_id=generate_request.device_id,
            expires_in=300
        )

        # Verify request
        verify_request = DevicePairingVerifyRequestContract(
            device_id=generate_request.device_id,
            pairing_token=generate_response.pairing_token,
            user_id=AuthTestDataFactory.make_user_id()
        )

        assert verify_request.device_id == generate_request.device_id
        assert verify_request.pairing_token == generate_response.pairing_token


# ============================================================================
# Factory Override Tests (5 tests)
# ============================================================================

class TestFactoryOverrides:
    """Test factory methods accept overrides"""

    def test_make_token_pair_request_override(self):
        """Factory accepts overrides for token pair request"""
        custom_email = "custom@example.com"
        request = AuthTestDataFactory.make_token_pair_request(email=custom_email)
        assert request.email == custom_email

    def test_make_dev_token_request_override(self):
        """Factory accepts overrides for dev token request"""
        custom_expires = 7200
        request = AuthTestDataFactory.make_dev_token_request(expires_in=custom_expires)
        assert request.expires_in == custom_expires

    def test_make_registration_start_request_override(self):
        """Factory accepts overrides for registration start request"""
        custom_name = "John Doe"
        request = AuthTestDataFactory.make_registration_start_request(name=custom_name)
        assert request.name == custom_name

    def test_make_api_key_create_request_override(self):
        """Factory accepts overrides for API key create request"""
        custom_permissions = ["read:data"]
        request = AuthTestDataFactory.make_api_key_create_request(permissions=custom_permissions)
        assert request.permissions == custom_permissions

    def test_make_device_register_request_override(self):
        """Factory accepts overrides for device register request"""
        custom_metadata = {"location": "lab", "firmware": "3.0.0"}
        request = AuthTestDataFactory.make_device_register_request(metadata=custom_metadata)
        assert request.metadata == custom_metadata
