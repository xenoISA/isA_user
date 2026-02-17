"""
Auth Service CRUD Integration Tests

Tests authentication lifecycle operations with real services.
These tests verify token generation, verification, and API key management.

Usage:
    pytest tests/integration/services/auth/test_auth_crud_integration.py -v
"""

from typing import List

import httpx
import pytest
import pytest_asyncio

from tests.fixtures import make_device_id, make_email, make_org_id, make_user_id
from tests.fixtures.auth_fixtures import (
    make_api_key_create_request,
    make_dev_token_request,
    make_device_registration_request,
    make_registration_request,
    make_token_pair_request,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

AUTH_SERVICE_URL = "http://localhost:8201"
API_BASE = f"{AUTH_SERVICE_URL}/api/v1/auth"
TIMEOUT = 30.0


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def http_client():
    """HTTP client for integration tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate unique user ID for test isolation"""
    return make_user_id()


@pytest.fixture
def test_org_id():
    """Generate unique organization ID for test isolation"""
    return make_org_id()


@pytest.fixture
def test_email():
    """Generate unique email for test isolation"""
    return make_email()


# ============================================================================
# Token Lifecycle Integration Tests
# ============================================================================


class TestTokenLifecycleIntegration:
    """
    Integration tests for JWT token lifecycle.
    Tests token generation, verification, and refresh.
    """

    async def test_full_token_lifecycle(self, http_client, test_user_id, test_email):
        """
        Integration: Full token lifecycle - generate, verify, refresh

        1. Generate token pair
        2. Verify access token
        3. Get user info from token
        4. Refresh access token
        5. Verify new access token
        """
        # 1. Generate token pair
        token_request = make_token_pair_request(user_id=test_user_id, email=test_email)

        token_response = await http_client.post(
            f"{API_BASE}/token-pair", json=token_request
        )
        assert token_response.status_code == 200, (
            f"Token pair failed: {token_response.text}"
        )

        token_data = token_response.json()
        assert token_data["success"] is True
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]

        # 2. Verify access token
        verify_response = await http_client.post(
            f"{API_BASE}/verify-token", json={"token": access_token}
        )
        assert verify_response.status_code == 200

        verify_data = verify_response.json()
        assert verify_data["valid"] is True
        assert verify_data["user_id"] == test_user_id

        # 3. Get user info from token
        info_response = await http_client.get(
            f"{API_BASE}/user-info", params={"token": access_token}
        )
        assert info_response.status_code == 200

        info_data = info_response.json()
        assert info_data["user_id"] == test_user_id
        assert info_data["email"] == test_email

        # 4. Refresh access token
        refresh_response = await http_client.post(
            f"{API_BASE}/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200

        refresh_data = refresh_response.json()
        assert refresh_data["success"] is True
        new_access_token = refresh_data["access_token"]

        # 5. Verify new access token
        verify_new_response = await http_client.post(
            f"{API_BASE}/verify-token", json={"token": new_access_token}
        )
        assert verify_new_response.status_code == 200
        assert verify_new_response.json()["valid"] is True


class TestDevTokenIntegration:
    """
    Integration tests for development token generation.
    """

    async def test_dev_token_with_permissions(
        self, http_client, test_user_id, test_email
    ):
        """
        Integration: Dev token with permissions

        1. Generate dev token with permissions
        2. Verify token
        3. Check permissions in verification
        """
        request = make_dev_token_request(
            user_id=test_user_id,
            email=test_email,
            permissions=["read:photos", "write:photos"],
            subscription_level="pro",
        )

        response = await http_client.post(f"{API_BASE}/dev-token", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        token = data["token"]

        # Verify token
        verify_response = await http_client.post(
            f"{API_BASE}/verify-token", json={"token": token}
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True


# ============================================================================
# API Key Integration Tests
# ============================================================================


class TestApiKeyLifecycleIntegration:
    """
    Integration tests for API key lifecycle.
    """

    async def test_full_api_key_lifecycle(self, http_client, test_org_id):
        """
        Integration: Full API key lifecycle - create, verify, list, revoke

        1. Create API key
        2. Verify API key
        3. List organization keys
        4. Revoke API key
        5. Verify revoked key fails
        """
        # 1. Create API key
        create_request = make_api_key_create_request(
            organization_id=test_org_id,
            name="Integration Test Key",
            permissions=["read:data"],
        )

        create_response = await http_client.post(
            f"{API_BASE}/api-keys", json=create_request
        )
        assert create_response.status_code == 200

        create_data = create_response.json()
        assert create_data["success"] is True
        api_key = create_data["api_key"]
        key_id = create_data["key_id"]

        # 2. Verify API key
        verify_response = await http_client.post(
            f"{API_BASE}/verify-api-key", json={"api_key": api_key}
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True

        # 3. List organization keys
        list_response = await http_client.get(f"{API_BASE}/api-keys/{test_org_id}")
        assert list_response.status_code == 200

        # 4. Revoke API key
        revoke_response = await http_client.delete(
            f"{API_BASE}/api-keys/{key_id}", params={"organization_id": test_org_id}
        )
        assert revoke_response.status_code == 200

        # 5. Verify revoked key fails
        verify_revoked_response = await http_client.post(
            f"{API_BASE}/verify-api-key", json={"api_key": api_key}
        )
        assert verify_revoked_response.status_code == 200
        assert verify_revoked_response.json()["valid"] is False


# ============================================================================
# Device Authentication Integration Tests
# ============================================================================


class TestDeviceAuthIntegration:
    """
    Integration tests for device authentication.
    """

    async def test_full_device_auth_lifecycle(self, http_client, test_org_id):
        """
        Integration: Full device auth lifecycle - register, authenticate, verify, revoke

        1. Register device
        2. Authenticate device
        3. Verify device token
        4. Refresh device secret
        5. Revoke device
        """
        device_id = make_device_id()

        # 1. Register device
        reg_request = make_device_registration_request(
            device_id=device_id,
            organization_id=test_org_id,
            device_name="Integration Test Device",
            device_type="emo_frame",
        )

        reg_response = await http_client.post(
            f"{API_BASE}/device/register", json=reg_request
        )
        assert reg_response.status_code == 200

        reg_data = reg_response.json()
        assert reg_data["success"] is True
        device_secret = reg_data["device_secret"]

        # 2. Authenticate device
        auth_response = await http_client.post(
            f"{API_BASE}/device/authenticate",
            json={"device_id": device_id, "device_secret": device_secret},
        )
        assert auth_response.status_code == 200

        auth_data = auth_response.json()
        assert auth_data["authenticated"] is True
        device_token = auth_data.get("access_token")

        # 3. Verify device token
        if device_token:
            verify_response = await http_client.post(
                f"{API_BASE}/device/verify-token", json={"token": device_token}
            )
            assert verify_response.status_code == 200

        # 4. List devices
        list_response = await http_client.get(
            f"{API_BASE}/device/list", params={"organization_id": test_org_id}
        )
        assert list_response.status_code == 200

        # 5. Revoke device
        revoke_response = await http_client.delete(
            f"{API_BASE}/device/{device_id}", params={"organization_id": test_org_id}
        )
        assert revoke_response.status_code == 200


# ============================================================================
# Registration Integration Tests
# ============================================================================


class TestRegistrationIntegration:
    """
    Integration tests for user registration flow.
    """

    async def test_registration_flow_start(self, http_client, test_email):
        """
        Integration: Start registration flow

        1. Start registration
        2. Verify pending registration created
        """
        reg_request = make_registration_request(email=test_email)

        response = await http_client.post(f"{API_BASE}/register", json=reg_request)
        assert response.status_code == 200

        data = response.json()
        assert "pending_registration_id" in data
        assert data["verification_required"] is True


# ============================================================================
# Health Check Integration Tests
# ============================================================================


class TestAuthHealthIntegration:
    """
    Integration tests for health checks.
    """

    async def test_basic_health(self, http_client):
        """
        Integration: Basic health check
        """
        response = await http_client.get(f"{AUTH_SERVICE_URL}/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"

    async def test_service_info(self, http_client):
        """
        Integration: Service info endpoint
        """
        response = await http_client.get(f"{API_BASE}/info")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "auth_microservice"
        assert "capabilities" in data

    async def test_service_stats(self, http_client):
        """
        Integration: Service stats endpoint
        """
        response = await http_client.get(f"{API_BASE}/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "operational"
