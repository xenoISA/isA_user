"""
Authorization Service API Golden Tests

GOLDEN tests capture the ACTUAL behavior of the authorization service API endpoints.
These tests use JWT authentication (real auth service) + real DB + real HTTP.

Purpose:
- Document the current API contract behavior
- Find bugs/gotchas in API layer with real authentication
- If bugs found -> Write TDD RED tests -> Fix -> GREEN

According to TDD_CONTRACT.md:
- For OLD/EXISTING services, write GOLDEN tests first at ALL layers
- API tests require JWT authentication (via auth service)
- Run golden tests to find bugs
- Write TDD tests for bugs found

Usage:
    # Start port-forwards:
    kubectl port-forward -n isa-cloud-staging svc/auth 8201:8201
    kubectl port-forward -n isa-cloud-staging svc/authorization 8203:8203

    # Run tests:
    pytest tests/api/golden/authorization_service/test_authorization_api_golden.py -v
"""

import pytest
import pytest_asyncio
import httpx
import uuid
from typing import List, Dict, Any

from tests.contracts.authorization.data_contract import (
    AuthorizationTestDataFactory,
    ResourceType,
    AccessLevel,
    PermissionSource,
)

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

AUTHORIZATION_SERVICE_URL = "http://localhost:8203"
AUTH_SERVICE_URL = "http://localhost:8201"
TIMEOUT = 30.0


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """HTTP client for API tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def auth_token(http_client):
    """
    Get JWT authentication token from auth service.
    Uses dev-token endpoint for testing.
    """
    response = await http_client.post(
        f"{AUTH_SERVICE_URL}/api/v1/auth/dev-token",
        json={
            "user_id": "api_test_user",
            "email": "apitest@example.com",
            "expires_in": 3600,
        }
    )

    if response.status_code == 200:
        token = response.json().get("token")
        return token
    else:
        pytest.skip(f"Failed to get auth token: {response.status_code}")


@pytest_asyncio.fixture
async def admin_auth_token(http_client):
    """
    Get admin JWT authentication token from auth service.
    """
    response = await http_client.post(
        f"{AUTH_SERVICE_URL}/api/v1/auth/dev-token",
        json={
            "user_id": "admin_test_user",
            "email": "admin@example.com",
            "role": "admin",
            "expires_in": 3600,
        }
    )

    if response.status_code == 200:
        token = response.json().get("token")
        return token
    else:
        pytest.skip(f"Failed to get admin auth token: {response.status_code}")


@pytest_asyncio.fixture
async def auth_headers(auth_token):
    """Authentication headers with JWT token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(admin_auth_token):
    """Admin authentication headers with JWT token"""
    return {"Authorization": f"Bearer {admin_auth_token}"}


@pytest_asyncio.fixture
async def test_user_id():
    """Test user ID for API tests"""
    return "api_test_user"


@pytest_asyncio.fixture
async def cleanup_permissions(http_client, admin_auth_headers):
    """Track and cleanup permissions created during tests"""
    created_permissions: List[Dict[str, Any]] = []

    def track(user_id: str, resource_type: str, resource_name: str):
        created_permissions.append({
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_name": resource_name,
        })

    yield track

    # Cleanup after test
    for perm in created_permissions:
        try:
            await http_client.post(
                f"{AUTHORIZATION_SERVICE_URL}/api/v1/permissions/revoke",
                json={
                    "user_id": perm["user_id"],
                    "resource_type": perm["resource_type"],
                    "resource_name": perm["resource_name"],
                    "revoked_by_user_id": "cleanup_user",
                },
                headers=admin_auth_headers,
            )
        except Exception:
            pass


# ============================================================================
# GOLDEN: Service Health
# ============================================================================

class TestAuthorizationServiceHealthGolden:
    """
    GOLDEN tests for authorization service health endpoints.
    """

    async def test_root_endpoint_golden(self, http_client):
        """
        GOLDEN: Capture actual behavior of / endpoint (no auth required)
        """
        response = await http_client.get(f"{AUTHORIZATION_SERVICE_URL}/")

        # GOLDEN: Document ACTUAL response
        assert response.status_code == 200
        data = response.json()
        assert "service" in data or "message" in data

    async def test_health_endpoint_golden(self, http_client):
        """
        GOLDEN: Capture actual behavior of /health endpoint
        """
        response = await http_client.get(f"{AUTHORIZATION_SERVICE_URL}/health")

        # GOLDEN: Document ACTUAL response
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "ok", "up"]

    async def test_detailed_health_endpoint_golden(self, http_client):
        """
        GOLDEN: Capture actual behavior of detailed health endpoint
        """
        response = await http_client.get(f"{AUTHORIZATION_SERVICE_URL}/api/v1/health")

        # GOLDEN: Document ACTUAL response
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        # May include dependencies status
        if "dependencies" in data:
            assert isinstance(data["dependencies"], (list, dict))


# ============================================================================
# GOLDEN: Access Check Endpoints
# ============================================================================

class TestAccessCheckEndpointsGolden:
    """
    GOLDEN tests for access check endpoints.
    """

    async def test_check_access_basic_golden(self, http_client, auth_headers, test_user_id):
        """
        GOLDEN: Basic access check request
        """
        request_data = {
            "user_id": test_user_id,
            "resource_type": "api_endpoint",
            "resource_name": "/api/test",
            "required_access_level": "read_only",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/access/check",
            json=request_data,
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response structure
        assert response.status_code == 200
        data = response.json()
        assert "has_access" in data
        assert isinstance(data["has_access"], bool)
        assert "permission_source" in data or "source" in data
        assert "reason" in data

    async def test_check_access_mcp_tool_golden(self, http_client, auth_headers, test_user_id):
        """
        GOLDEN: Access check for MCP tool resource type
        """
        request_data = {
            "user_id": test_user_id,
            "resource_type": "mcp_tool",
            "resource_name": AuthorizationTestDataFactory.make_mcp_tool_name(),
            "required_access_level": "read_write",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/access/check",
            json=request_data,
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        assert response.status_code == 200
        data = response.json()
        assert "has_access" in data

    async def test_check_access_ai_model_golden(self, http_client, auth_headers, test_user_id):
        """
        GOLDEN: Access check for AI model resource type
        """
        request_data = {
            "user_id": test_user_id,
            "resource_type": "ai_model",
            "resource_name": AuthorizationTestDataFactory.make_ai_model_name(),
            "required_access_level": "read_only",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/access/check",
            json=request_data,
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        assert response.status_code == 200
        data = response.json()
        assert "has_access" in data

    async def test_check_access_with_organization_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Access check with organization context
        """
        request_data = {
            "user_id": test_user_id,
            "resource_type": "api_endpoint",
            "resource_name": "/api/org/data",
            "required_access_level": "read_only",
            "organization_id": AuthorizationTestDataFactory.make_organization_id(),
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/access/check",
            json=request_data,
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        assert response.status_code == 200
        data = response.json()
        assert "has_access" in data

    async def test_check_access_invalid_resource_type_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Access check with invalid resource type
        """
        request_data = {
            "user_id": test_user_id,
            "resource_type": "invalid_type",
            "resource_name": "/api/test",
            "required_access_level": "read_only",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/access/check",
            json=request_data,
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        # Expect validation error
        assert response.status_code in [400, 422]

    async def test_check_access_missing_user_id_golden(self, http_client, auth_headers):
        """
        GOLDEN: Access check with missing user_id
        """
        request_data = {
            "resource_type": "api_endpoint",
            "resource_name": "/api/test",
            "required_access_level": "read_only",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/access/check",
            json=request_data,
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        # Expect validation error
        assert response.status_code in [400, 422]


# ============================================================================
# GOLDEN: Permission Grant Endpoints
# ============================================================================

class TestPermissionGrantEndpointsGolden:
    """
    GOLDEN tests for permission grant endpoints.
    """

    async def test_grant_permission_basic_golden(
        self, http_client, admin_auth_headers, cleanup_permissions
    ):
        """
        GOLDEN: Basic permission grant request
        """
        user_id = AuthorizationTestDataFactory.make_user_id()
        resource_name = f"/api/test/{uuid.uuid4().hex[:8]}"

        request_data = {
            "user_id": user_id,
            "resource_type": "api_endpoint",
            "resource_name": resource_name,
            "access_level": "read_write",
            "permission_source": "admin_grant",
            "granted_by_user_id": "admin_test_user",
            "reason": "API test grant",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/permissions/grant",
            json=request_data,
            headers=admin_auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "granted" in data or data is True
            cleanup_permissions(user_id, "api_endpoint", resource_name)
        else:
            # May fail due to user not existing
            assert response.status_code in [400, 404, 422]

    async def test_grant_permission_with_expiry_golden(
        self, http_client, admin_auth_headers, cleanup_permissions
    ):
        """
        GOLDEN: Permission grant with expiration date
        """
        user_id = AuthorizationTestDataFactory.make_user_id()
        resource_name = f"/api/expiring/{uuid.uuid4().hex[:8]}"
        expires_at = AuthorizationTestDataFactory.make_future_timestamp(days=30)

        request_data = {
            "user_id": user_id,
            "resource_type": "mcp_tool",
            "resource_name": resource_name,
            "access_level": "read_only",
            "permission_source": "admin_grant",
            "granted_by_user_id": "admin_test_user",
            "expires_at": expires_at.isoformat(),
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/permissions/grant",
            json=request_data,
            headers=admin_auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        if response.status_code == 200:
            cleanup_permissions(user_id, "mcp_tool", resource_name)
        # Status can vary based on user existence
        assert response.status_code in [200, 400, 404, 422]

    async def test_grant_permission_missing_fields_golden(
        self, http_client, admin_auth_headers
    ):
        """
        GOLDEN: Permission grant with missing required fields
        """
        request_data = {
            "resource_type": "api_endpoint",
            "resource_name": "/api/test",
            # Missing user_id, access_level, permission_source
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/permissions/grant",
            json=request_data,
            headers=admin_auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        assert response.status_code in [400, 422]


# ============================================================================
# GOLDEN: Permission Revoke Endpoints
# ============================================================================

class TestPermissionRevokeEndpointsGolden:
    """
    GOLDEN tests for permission revoke endpoints.
    """

    async def test_revoke_permission_basic_golden(self, http_client, admin_auth_headers):
        """
        GOLDEN: Basic permission revoke request
        """
        request_data = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type": "api_endpoint",
            "resource_name": "/api/nonexistent",
            "revoked_by_user_id": "admin_test_user",
            "reason": "API test revoke",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/permissions/revoke",
            json=request_data,
            headers=admin_auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        # May return false if permission doesn't exist (expected behavior)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (bool, dict))

    async def test_revoke_permission_missing_fields_golden(
        self, http_client, admin_auth_headers
    ):
        """
        GOLDEN: Permission revoke with missing required fields
        """
        request_data = {
            "user_id": "test_user",
            # Missing resource_type and resource_name
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/permissions/revoke",
            json=request_data,
            headers=admin_auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        assert response.status_code in [400, 422]


# ============================================================================
# GOLDEN: Permission Query Endpoints
# ============================================================================

class TestPermissionQueryEndpointsGolden:
    """
    GOLDEN tests for permission query endpoints.
    """

    async def test_list_user_permissions_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: List user permissions
        """
        response = await http_client.get(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/users/{test_user_id}/permissions",
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            if isinstance(data, dict):
                # May be wrapped in pagination
                assert "permissions" in data or "items" in data or "data" in data
        else:
            # May return 404 if user doesn't exist
            assert response.status_code in [404, 403]

    async def test_get_user_permission_summary_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Get user permission summary
        """
        response = await http_client.get(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/users/{test_user_id}/permissions/summary",
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        if response.status_code == 200:
            data = response.json()
            # Check for typical summary fields
            expected_fields = ["total_permissions", "user_id"]
            has_expected = any(f in data for f in expected_fields)
            assert has_expected or isinstance(data, dict)
        else:
            assert response.status_code in [404, 403]

    async def test_list_accessible_resources_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: List user's accessible resources
        """
        response = await http_client.get(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/users/{test_user_id}/accessible-resources",
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
        else:
            assert response.status_code in [404, 403]


# ============================================================================
# GOLDEN: Bulk Operations Endpoints
# ============================================================================

class TestBulkOperationsEndpointsGolden:
    """
    GOLDEN tests for bulk operation endpoints.
    """

    async def test_bulk_grant_golden(self, http_client, admin_auth_headers):
        """
        GOLDEN: Bulk permission grant
        """
        request_data = {
            "operations": [
                {
                    "type": "grant",
                    "user_id": AuthorizationTestDataFactory.make_user_id(),
                    "resource_type": "api_endpoint",
                    "resource_name": f"/api/bulk/{uuid.uuid4().hex[:8]}",
                    "access_level": "read_only",
                    "permission_source": "admin_grant",
                    "granted_by_user_id": "admin_test_user",
                },
                {
                    "type": "grant",
                    "user_id": AuthorizationTestDataFactory.make_user_id(),
                    "resource_type": "mcp_tool",
                    "resource_name": AuthorizationTestDataFactory.make_mcp_tool_name(),
                    "access_level": "read_write",
                    "permission_source": "admin_grant",
                    "granted_by_user_id": "admin_test_user",
                },
            ],
            "executed_by_user_id": "admin_test_user",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/permissions/bulk",
            json=request_data,
            headers=admin_auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        if response.status_code == 200:
            data = response.json()
            assert "results" in data or "total_operations" in data or isinstance(data, list)
        else:
            # Bulk endpoint might not exist or have different path
            assert response.status_code in [400, 404, 422]


# ============================================================================
# GOLDEN: Service Statistics Endpoints
# ============================================================================

class TestServiceStatisticsEndpointsGolden:
    """
    GOLDEN tests for service statistics endpoints.
    """

    async def test_get_service_stats_golden(self, http_client, admin_auth_headers):
        """
        GOLDEN: Get service statistics
        """
        response = await http_client.get(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/stats",
            headers=admin_auth_headers,
        )

        # GOLDEN: Document ACTUAL response
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            # Stats endpoint might require specific permissions
            assert response.status_code in [403, 404]


# ============================================================================
# GOLDEN: Authentication Required Tests
# ============================================================================

class TestAuthenticationRequiredGolden:
    """
    GOLDEN tests for authentication requirements.
    """

    async def test_access_check_without_auth_golden(self, http_client):
        """
        GOLDEN: Access check without authentication should fail
        """
        request_data = {
            "user_id": "test_user",
            "resource_type": "api_endpoint",
            "resource_name": "/api/test",
            "required_access_level": "read_only",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/access/check",
            json=request_data,
        )

        # GOLDEN: Document ACTUAL response
        # Should require authentication
        assert response.status_code in [401, 403]

    async def test_grant_permission_without_auth_golden(self, http_client):
        """
        GOLDEN: Permission grant without authentication should fail
        """
        request_data = {
            "user_id": "test_user",
            "resource_type": "api_endpoint",
            "resource_name": "/api/test",
            "access_level": "read_only",
            "permission_source": "admin_grant",
            "granted_by_user_id": "admin",
        }

        response = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/permissions/grant",
            json=request_data,
        )

        # GOLDEN: Document ACTUAL response
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
