"""
Auth Service API Contract Tests (Layer 1)

RED PHASE: Define what the API should return before implementation.
These tests define the HTTP contracts for the Auth service.

Usage:
    pytest tests/api/services/auth -v                    # Run all auth API tests
    pytest tests/api/services/auth -v -k "token"         # Run token endpoint tests
    pytest tests/api/services/auth -v --tb=short         # Short traceback
"""
import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def auth_api(http_client):
    """Auth service API client"""
    from tests.api.conftest import APIClient
    return APIClient(http_client, "auth", "/api/v1/auth")


# =============================================================================
# Dev Token Endpoint Tests
# =============================================================================

class TestAuthDevTokenEndpoint:
    """
    POST /api/v1/auth/dev-token

    Generate development/test access token.
    """

    async def test_generate_dev_token(self, auth_api, api_assert):
        """RED: Dev token should be generated with user info"""
        from tests.fixtures.auth_fixtures import make_dev_token_request

        request = make_dev_token_request()

        response = await auth_api.post("/dev-token", json=request)

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "success", "token", "expires_in", "token_type", "user_id", "email"
        ])
        assert data["success"] is True
        assert data["token_type"] == "Bearer"
        assert len(data["token"]) > 0

    async def test_generate_dev_token_validates_required(self, auth_api, api_assert):
        """RED: Missing required fields should return 422"""
        # Missing user_id
        response = await auth_api.post("/dev-token", json={
            "email": "test@example.com",
            "expires_in": 3600
        })
        api_assert.assert_validation_error(response)

        # Missing email
        response = await auth_api.post("/dev-token", json={
            "user_id": "usr_123",
            "expires_in": 3600
        })
        api_assert.assert_validation_error(response)

    async def test_dev_token_with_permissions(self, auth_api, api_assert):
        """RED: Dev token with permissions should be accepted"""
        from tests.fixtures.auth_fixtures import make_dev_token_request

        request = make_dev_token_request(
            permissions=["read:photos", "write:photos"]
        )

        response = await auth_api.post("/dev-token", json=request)

        api_assert.assert_success(response)


# =============================================================================
# Token Pair Endpoint Tests
# =============================================================================

class TestAuthTokenPairEndpoint:
    """
    POST /api/v1/auth/token-pair

    Generate access and refresh token pair.
    """

    async def test_generate_token_pair(self, auth_api, api_assert):
        """RED: Token pair should include access and refresh tokens"""
        from tests.fixtures.auth_fixtures import make_token_pair_request

        request = make_token_pair_request()

        response = await auth_api.post("/token-pair", json=request)

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "success", "access_token", "refresh_token",
            "token_type", "expires_in", "user_id", "email"
        ])
        assert data["success"] is True
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    async def test_token_pair_validates_required(self, auth_api, api_assert):
        """RED: Missing user_id/email should return 422"""
        response = await auth_api.post("/token-pair", json={
            "email": "test@example.com"
        })
        api_assert.assert_validation_error(response)


# =============================================================================
# Token Verification Endpoint Tests
# =============================================================================

class TestAuthVerifyTokenEndpoint:
    """
    POST /api/v1/auth/verify-token

    Verify JWT token validity.
    """

    async def test_verify_valid_token(self, auth_api, api_assert):
        """RED: Valid token should return verification success"""
        from tests.fixtures.auth_fixtures import make_dev_token_request, make_token_verification_request

        # First generate a token
        token_request = make_dev_token_request()
        token_response = await auth_api.post("/dev-token", json=token_request)
        token = token_response.json().get("token")

        # Verify the token
        verify_request = make_token_verification_request(token=token)
        response = await auth_api.post("/verify-token", json=verify_request)

        api_assert.assert_success(response)
        data = response.json()

        assert data["valid"] is True
        assert data["user_id"] == token_request["user_id"]

    async def test_verify_invalid_token(self, auth_api, api_assert):
        """RED: Invalid token should return valid=false"""
        from tests.fixtures.auth_fixtures import make_token_verification_request

        request = make_token_verification_request(token="invalid_token_here")
        response = await auth_api.post("/verify-token", json=request)

        api_assert.assert_success(response)
        data = response.json()

        assert data["valid"] is False
        assert "error" in data


# =============================================================================
# Token Refresh Endpoint Tests
# =============================================================================

class TestAuthRefreshEndpoint:
    """
    POST /api/v1/auth/refresh

    Refresh access token using refresh token.
    """

    async def test_refresh_token(self, auth_api, api_assert):
        """RED: Valid refresh token should return new access token"""
        from tests.fixtures.auth_fixtures import make_token_pair_request

        # First generate token pair
        token_request = make_token_pair_request()
        token_response = await auth_api.post("/token-pair", json=token_request)
        refresh_token = token_response.json().get("refresh_token")

        # Refresh the token
        response = await auth_api.post("/refresh", json={
            "refresh_token": refresh_token
        })

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "success", "access_token", "token_type", "expires_in"
        ])
        assert data["success"] is True

    async def test_refresh_invalid_token_returns_401(self, auth_api, api_assert):
        """RED: Invalid refresh token should return 401"""
        response = await auth_api.post("/refresh", json={
            "refresh_token": "invalid_refresh_token"
        })

        api_assert.assert_unauthorized(response)


# =============================================================================
# User Info Endpoint Tests
# =============================================================================

class TestAuthUserInfoEndpoint:
    """
    GET /api/v1/auth/user-info

    Extract user info from token.
    """

    async def test_get_user_info_from_token(self, auth_api, api_assert):
        """RED: Should return user info from valid token"""
        from tests.fixtures.auth_fixtures import make_dev_token_request

        # Generate a token
        token_request = make_dev_token_request()
        token_response = await auth_api.post("/dev-token", json=token_request)
        token = token_response.json().get("token")

        # Get user info
        response = await auth_api.get("/user-info", params={"token": token})

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, ["user_id", "email"])
        assert data["user_id"] == token_request["user_id"]

    async def test_user_info_invalid_token_returns_401(self, auth_api, api_assert):
        """RED: Invalid token should return 401"""
        response = await auth_api.get("/user-info", params={"token": "invalid"})

        api_assert.assert_unauthorized(response)


# =============================================================================
# API Key Endpoints Tests
# =============================================================================

class TestAuthApiKeyEndpoints:
    """
    POST /api/v1/auth/api-keys
    POST /api/v1/auth/verify-api-key
    GET /api/v1/auth/api-keys/{organization_id}
    DELETE /api/v1/auth/api-keys/{key_id}

    API key management.
    """

    async def test_create_api_key(self, auth_api, api_assert):
        """RED: API key creation should return key details"""
        from tests.fixtures.auth_fixtures import make_api_key_create_request

        request = make_api_key_create_request()

        response = await auth_api.post("/api-keys", json=request)

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "success", "api_key", "key_id", "name"
        ])
        assert data["success"] is True

    async def test_verify_api_key(self, auth_api, api_assert):
        """RED: Valid API key should verify successfully"""
        from tests.fixtures.auth_fixtures import make_api_key_create_request

        # Create API key
        create_request = make_api_key_create_request()
        create_response = await auth_api.post("/api-keys", json=create_request)
        api_key = create_response.json().get("api_key")

        # Verify API key
        response = await auth_api.post("/verify-api-key", json={
            "api_key": api_key
        })

        api_assert.assert_success(response)
        data = response.json()

        assert data["valid"] is True

    async def test_list_api_keys(self, auth_api, api_assert):
        """RED: List API keys for organization"""
        from tests.fixtures.auth_fixtures import make_api_key_create_request, make_org_id

        org_id = make_org_id()

        # Create API key
        create_request = make_api_key_create_request(organization_id=org_id)
        await auth_api.post("/api-keys", json=create_request)

        # List keys
        response = await auth_api.get(f"/api-keys/{org_id}")

        api_assert.assert_success(response)


# =============================================================================
# Device Authentication Endpoints Tests
# =============================================================================

class TestAuthDeviceEndpoints:
    """
    POST /api/v1/auth/device/register
    POST /api/v1/auth/device/authenticate
    POST /api/v1/auth/device/verify-token

    Device authentication management.
    """

    async def test_register_device(self, auth_api, api_assert):
        """RED: Device registration should return credentials"""
        from tests.fixtures.auth_fixtures import make_device_registration_request

        request = make_device_registration_request()

        response = await auth_api.post("/device/register", json=request)

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "success", "device_id", "device_secret"
        ])
        assert data["success"] is True

    async def test_authenticate_device(self, auth_api, api_assert):
        """RED: Device authentication should return token"""
        from tests.fixtures.auth_fixtures import make_device_registration_request

        # Register device first
        reg_request = make_device_registration_request()
        reg_response = await auth_api.post("/device/register", json=reg_request)
        reg_data = reg_response.json()

        # Authenticate
        auth_request = {
            "device_id": reg_data["device_id"],
            "device_secret": reg_data["device_secret"]
        }
        response = await auth_api.post("/device/authenticate", json=auth_request)

        api_assert.assert_success(response)
        data = response.json()

        assert data["authenticated"] is True
        assert "access_token" in data

    async def test_authenticate_invalid_device_returns_401(self, auth_api, api_assert):
        """RED: Invalid device credentials should return 401"""
        response = await auth_api.post("/device/authenticate", json={
            "device_id": "invalid_device",
            "device_secret": "invalid_secret"
        })

        api_assert.assert_unauthorized(response)

    async def test_list_devices(self, auth_api, api_assert):
        """RED: List devices for organization"""
        from tests.fixtures.auth_fixtures import make_device_registration_request, make_org_id

        org_id = make_org_id()

        # Register device
        reg_request = make_device_registration_request(organization_id=org_id)
        await auth_api.post("/device/register", json=reg_request)

        # List devices
        response = await auth_api.get("/device/list", params={"organization_id": org_id})

        api_assert.assert_success(response)
        data = response.json()

        assert data["success"] is True
        assert "devices" in data


# =============================================================================
# Registration Endpoints Tests
# =============================================================================

class TestAuthRegistrationEndpoints:
    """
    POST /api/v1/auth/register
    POST /api/v1/auth/verify

    User registration flow.
    """

    async def test_start_registration(self, auth_api, api_assert):
        """RED: Registration should return pending ID"""
        from tests.fixtures.auth_fixtures import make_registration_request

        request = make_registration_request()

        response = await auth_api.post("/register", json=request)

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "pending_registration_id", "verification_required", "expires_at"
        ])
        assert data["verification_required"] is True

    async def test_registration_validates_email(self, auth_api, api_assert):
        """RED: Invalid email should return 422"""
        response = await auth_api.post("/register", json={
            "email": "invalid-email",
            "password": "StrongP@ss123",
            "name": "Test"
        })
        api_assert.assert_validation_error(response)


# =============================================================================
# Health and Info Endpoints Tests
# =============================================================================

class TestAuthHealthEndpoints:
    """
    GET /health
    GET /api/v1/auth/info

    Service health and info.
    """

    async def test_health_check(self, http_client, api_assert):
        """RED: Health check should return service status"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("auth")
        response = await http_client.get(f"{base_url}/health")

        api_assert.assert_success(response)
        data = response.json()

        assert data["status"] == "healthy"
        assert "capabilities" in data

    async def test_service_info(self, auth_api, api_assert):
        """RED: Service info should return capabilities"""
        response = await auth_api.get("/info")

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "service", "version", "capabilities", "endpoints"
        ])

    async def test_service_stats(self, auth_api, api_assert):
        """RED: Stats should return service statistics"""
        response = await auth_api.get("/stats")

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "service", "status", "capabilities"
        ])
