"""
Vault Service API Tests

Tests HTTP endpoints with real requests against running service.
"""
import pytest
import httpx
import uuid
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

pytestmark = [pytest.mark.api, pytest.mark.asyncio]

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = os.getenv("VAULT_BASE_URL", "http://localhost:8214")
API_V1 = f"{BASE_URL}/api/v1/vault"
TIMEOUT = 10.0


# =============================================================================
# Test Data Factory
# =============================================================================

class VaultAPITestDataFactory:
    """Factory for generating API test data"""

    @staticmethod
    def unique_id() -> str:
        return uuid.uuid4().hex[:8]

    @staticmethod
    def user_id() -> str:
        return f"api_user_{VaultAPITestDataFactory.unique_id()}"

    @staticmethod
    def secret_name() -> str:
        return f"api_secret_{VaultAPITestDataFactory.unique_id()}"

    @staticmethod
    def secret_value() -> str:
        return f"sk_test_{VaultAPITestDataFactory.unique_id()}"

    @staticmethod
    def create_request(**kwargs) -> dict:
        """Generate create secret request body"""
        return {
            "secret_type": kwargs.get("secret_type", "api_key"),
            "provider": kwargs.get("provider"),
            "name": kwargs.get("name", VaultAPITestDataFactory.secret_name()),
            "description": kwargs.get("description"),
            "secret_value": kwargs.get("secret_value", VaultAPITestDataFactory.secret_value()),
            "organization_id": kwargs.get("organization_id"),
            "metadata": kwargs.get("metadata", {}),
            "tags": kwargs.get("tags", []),
            "expires_at": kwargs.get("expires_at"),
            "rotation_enabled": kwargs.get("rotation_enabled", False),
            "rotation_days": kwargs.get("rotation_days"),
            "blockchain_verify": kwargs.get("blockchain_verify", False),
        }

    @staticmethod
    def headers(user_id: Optional[str] = None) -> dict:
        """Generate request headers"""
        return {
            "X-User-Id": user_id or VaultAPITestDataFactory.user_id(),
            "Content-Type": "application/json",
        }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def user_id():
    """Generate unique user ID for test"""
    return VaultAPITestDataFactory.user_id()


@pytest.fixture
async def created_secret(http_client, user_id):
    """Create a secret and return its data"""
    request_data = VaultAPITestDataFactory.create_request()
    headers = VaultAPITestDataFactory.headers(user_id)

    response = await http_client.post(
        f"{API_V1}/secrets",
        json=request_data,
        headers=headers,
    )

    if response.status_code == 201:
        return response.json()
    return None


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestHealthEndpoint:
    """Tests for health check endpoints"""

    async def test_health_returns_200(self, http_client):
        """GET /health should return 200"""
        response = await http_client.get(f"{BASE_URL}/health")

        assert response.status_code == 200

    async def test_health_response_schema(self, http_client):
        """Health response should match expected schema"""
        response = await http_client.get(f"{BASE_URL}/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert data.get("service") == "vault_service"
        assert data.get("port") == 8214

    async def test_health_detailed_returns_200_or_404(self, http_client):
        """GET /health/detailed should return 200 or 404"""
        response = await http_client.get(f"{BASE_URL}/health/detailed")

        assert response.status_code in [200, 404]

    async def test_info_endpoint(self, http_client):
        """GET /info should return service info"""
        response = await http_client.get(f"{BASE_URL}/info")

        assert response.status_code == 200
        data = response.json()
        assert data.get("service") == "vault_service"
        assert "capabilities" in data
        assert "endpoints" in data


# =============================================================================
# Create Secret Tests
# =============================================================================

class TestCreateSecret:
    """Tests for POST /api/v1/vault/secrets"""

    async def test_create_secret_success(self, http_client, user_id):
        """Should create secret successfully"""
        request_data = VaultAPITestDataFactory.create_request()
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.post(
            f"{API_V1}/secrets",
            json=request_data,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "vault_id" in data
        assert data["user_id"] == user_id
        assert data["name"] == request_data["name"]

    async def test_create_secret_requires_auth(self, http_client):
        """Should return 401 without X-User-Id header"""
        request_data = VaultAPITestDataFactory.create_request()

        response = await http_client.post(
            f"{API_V1}/secrets",
            json=request_data,
        )

        assert response.status_code == 401

    async def test_create_secret_validates_required_fields(self, http_client, user_id):
        """Should return 422 for missing required fields"""
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.post(
            f"{API_V1}/secrets",
            json={},
            headers=headers,
        )

        assert response.status_code == 422

    async def test_create_secret_validates_name_length(self, http_client, user_id):
        """Should reject name over 255 characters"""
        request_data = VaultAPITestDataFactory.create_request(name="a" * 256)
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.post(
            f"{API_V1}/secrets",
            json=request_data,
            headers=headers,
        )

        assert response.status_code == 422

    async def test_create_secret_validates_tags_count(self, http_client, user_id):
        """Should reject more than 10 tags"""
        request_data = VaultAPITestDataFactory.create_request(tags=[f"tag{i}" for i in range(11)])
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.post(
            f"{API_V1}/secrets",
            json=request_data,
            headers=headers,
        )

        assert response.status_code == 422

    async def test_create_secret_all_types(self, http_client, user_id):
        """Should accept all secret types"""
        secret_types = [
            "api_key", "database_credential", "ssh_key", "ssl_certificate",
            "oauth_token", "aws_credential", "blockchain_key",
            "environment_variable", "custom"
        ]
        headers = VaultAPITestDataFactory.headers(user_id)

        for secret_type in secret_types:
            request_data = VaultAPITestDataFactory.create_request(secret_type=secret_type)
            response = await http_client.post(
                f"{API_V1}/secrets",
                json=request_data,
                headers=headers,
            )
            assert response.status_code == 201, f"Failed for type: {secret_type}"

    async def test_create_secret_with_provider(self, http_client, user_id):
        """Should accept provider"""
        request_data = VaultAPITestDataFactory.create_request(provider="openai")
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.post(
            f"{API_V1}/secrets",
            json=request_data,
            headers=headers,
        )

        assert response.status_code == 201
        assert response.json().get("provider") == "openai"


# =============================================================================
# Get Secret Tests
# =============================================================================

class TestGetSecret:
    """Tests for GET /api/v1/vault/secrets/{vault_id}"""

    async def test_get_secret_success(self, http_client, user_id, created_secret):
        """Should get secret with decrypted value"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        vault_id = created_secret["vault_id"]
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/secrets/{vault_id}",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "secret_value" in data
        assert data["vault_id"] == vault_id

    async def test_get_secret_without_decrypt(self, http_client, user_id, created_secret):
        """Should get secret without decryption"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        vault_id = created_secret["vault_id"]
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/secrets/{vault_id}",
            params={"decrypt": "false"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["secret_value"] == "[ENCRYPTED]"

    async def test_get_secret_not_found(self, http_client, user_id):
        """Should return 404 for non-existent secret"""
        headers = VaultAPITestDataFactory.headers(user_id)
        fake_id = str(uuid.uuid4())

        response = await http_client.get(
            f"{API_V1}/secrets/{fake_id}",
            headers=headers,
        )

        assert response.status_code == 404

    async def test_get_secret_access_denied(self, http_client, user_id, created_secret):
        """Should return 403 for unauthorized access"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        vault_id = created_secret["vault_id"]
        other_user = VaultAPITestDataFactory.user_id()
        headers = VaultAPITestDataFactory.headers(other_user)

        response = await http_client.get(
            f"{API_V1}/secrets/{vault_id}",
            headers=headers,
        )

        assert response.status_code == 403


# =============================================================================
# List Secrets Tests
# =============================================================================

class TestListSecrets:
    """Tests for GET /api/v1/vault/secrets"""

    async def test_list_secrets_empty(self, http_client, user_id):
        """Should return empty list for new user"""
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/secrets",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    async def test_list_secrets_with_items(self, http_client, user_id, created_secret):
        """Should return list with created items"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/secrets",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

    async def test_list_secrets_with_type_filter(self, http_client, user_id):
        """Should filter by secret type"""
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/secrets",
            params={"secret_type": "api_key"},
            headers=headers,
        )

        assert response.status_code == 200

    async def test_list_secrets_pagination(self, http_client, user_id):
        """Should support pagination"""
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/secrets",
            params={"page": 1, "page_size": 10},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


# =============================================================================
# Update Secret Tests
# =============================================================================

class TestUpdateSecret:
    """Tests for PUT /api/v1/vault/secrets/{vault_id}"""

    async def test_update_secret_success(self, http_client, user_id, created_secret):
        """Should update secret successfully"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        vault_id = created_secret["vault_id"]
        headers = VaultAPITestDataFactory.headers(user_id)
        new_name = f"updated_{VaultAPITestDataFactory.unique_id()}"

        response = await http_client.put(
            f"{API_V1}/secrets/{vault_id}",
            json={"name": new_name},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name

    async def test_update_secret_not_found(self, http_client, user_id):
        """Should return 404 for non-existent secret"""
        headers = VaultAPITestDataFactory.headers(user_id)
        fake_id = str(uuid.uuid4())

        response = await http_client.put(
            f"{API_V1}/secrets/{fake_id}",
            json={"name": "new_name"},
            headers=headers,
        )

        assert response.status_code in [403, 404]


# =============================================================================
# Delete Secret Tests
# =============================================================================

class TestDeleteSecret:
    """Tests for DELETE /api/v1/vault/secrets/{vault_id}"""

    async def test_delete_secret_success(self, http_client, user_id):
        """Should delete secret successfully"""
        # Create secret first
        request_data = VaultAPITestDataFactory.create_request()
        headers = VaultAPITestDataFactory.headers(user_id)

        create_response = await http_client.post(
            f"{API_V1}/secrets",
            json=request_data,
            headers=headers,
        )

        if create_response.status_code != 201:
            pytest.skip("Could not create test secret")

        vault_id = create_response.json()["vault_id"]

        # Delete secret
        response = await http_client.delete(
            f"{API_V1}/secrets/{vault_id}",
            headers=headers,
        )

        assert response.status_code == 200

    async def test_delete_secret_not_found(self, http_client, user_id):
        """Should return 403/404 for non-existent secret"""
        headers = VaultAPITestDataFactory.headers(user_id)
        fake_id = str(uuid.uuid4())

        response = await http_client.delete(
            f"{API_V1}/secrets/{fake_id}",
            headers=headers,
        )

        assert response.status_code in [403, 404]


# =============================================================================
# Share Secret Tests
# =============================================================================

class TestShareSecret:
    """Tests for POST /api/v1/vault/secrets/{vault_id}/share"""

    async def test_share_secret_success(self, http_client, user_id, created_secret):
        """Should share secret successfully"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        vault_id = created_secret["vault_id"]
        headers = VaultAPITestDataFactory.headers(user_id)
        recipient_id = VaultAPITestDataFactory.user_id()

        response = await http_client.post(
            f"{API_V1}/secrets/{vault_id}/share",
            json={
                "shared_with_user_id": recipient_id,
                "permission_level": "read",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "share_id" in data

    async def test_share_secret_requires_target(self, http_client, user_id, created_secret):
        """Should require user or org ID"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        vault_id = created_secret["vault_id"]
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.post(
            f"{API_V1}/secrets/{vault_id}/share",
            json={"permission_level": "read"},
            headers=headers,
        )

        assert response.status_code == 422


# =============================================================================
# Shared Secrets Tests
# =============================================================================

class TestSharedSecrets:
    """Tests for GET /api/v1/vault/shared"""

    async def test_get_shared_secrets(self, http_client, user_id):
        """Should return shared secrets"""
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/shared",
            headers=headers,
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)


# =============================================================================
# Audit Logs Tests
# =============================================================================

class TestAuditLogs:
    """Tests for GET /api/v1/vault/audit-logs"""

    async def test_get_audit_logs(self, http_client, user_id):
        """Should return audit logs"""
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/audit-logs",
            headers=headers,
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Tests for GET /api/v1/vault/stats"""

    async def test_get_stats(self, http_client, user_id):
        """Should return vault statistics"""
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.get(
            f"{API_V1}/stats",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_secrets" in data
        assert "active_secrets" in data


# =============================================================================
# Rotate Secret Tests
# =============================================================================

class TestRotateSecret:
    """Tests for POST /api/v1/vault/secrets/{vault_id}/rotate"""

    async def test_rotate_secret(self, http_client, user_id, created_secret):
        """Should rotate secret successfully"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        vault_id = created_secret["vault_id"]
        headers = VaultAPITestDataFactory.headers(user_id)
        new_value = VaultAPITestDataFactory.secret_value()

        response = await http_client.post(
            f"{API_V1}/secrets/{vault_id}/rotate",
            params={"new_secret_value": new_value},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] > created_secret["version"]


# =============================================================================
# Test Credential Tests
# =============================================================================

class TestCredentialTest:
    """Tests for POST /api/v1/vault/secrets/{vault_id}/test"""

    async def test_credential(self, http_client, user_id, created_secret):
        """Should test credential"""
        if not created_secret:
            pytest.skip("Could not create test secret")

        vault_id = created_secret["vault_id"]
        headers = VaultAPITestDataFactory.headers(user_id)

        response = await http_client.post(
            f"{API_V1}/secrets/{vault_id}/test",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
