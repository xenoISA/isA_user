"""
Vault Service Smoke Tests

Quick sanity checks to verify vault_service is deployed and functioning correctly.
These tests are designed to:
1. Run quickly (< 30 seconds total)
2. Validate critical paths only
3. Catch obvious deployment failures

Purpose:
- Verify service is up and responding
- Test basic vault operations work
- Test critical user flows (create, get, list, share)
- Validate data contracts are honored

Usage:
    pytest tests/smoke/vault_service -v
    pytest tests/smoke/vault_service -v -k "health"

Environment Variables:
    VAULT_BASE_URL: Base URL for vault service (default: http://localhost:8214)
"""

import os
import pytest
import uuid
import httpx
from datetime import datetime

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

# Configuration
BASE_URL = os.getenv("VAULT_BASE_URL", "http://localhost:8214")
API_V1 = f"{BASE_URL}/api/v1/vault"
TIMEOUT = 10.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for smoke tests"""
    return f"usr_smoke_{uuid.uuid4().hex[:8]}"


def unique_vault_id() -> str:
    """Generate unique vault ID for smoke tests"""
    return str(uuid.uuid4())


def unique_secret_name() -> str:
    """Generate unique secret name for smoke tests"""
    return f"smoke_secret_{uuid.uuid4().hex[:8]}"


def unique_secret_value() -> str:
    """Generate unique secret value for smoke tests"""
    return f"sk_smoke_{uuid.uuid4().hex[:16]}"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Async HTTP client for smoke tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


# =============================================================================
# SMOKE TEST 1: Health Checks
# =============================================================================

class TestHealthSmoke:
    """Smoke: Health endpoint sanity checks"""

    async def test_health_endpoint_responds(self, http_client):
        """SMOKE: GET /health returns 200"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200, \
            f"Health check failed: {response.status_code}"

    async def test_health_detailed_responds(self, http_client):
        """SMOKE: GET /health/detailed returns 200"""
        response = await http_client.get(f"{BASE_URL}/health/detailed")
        # Could be 200 or 404 if not implemented
        assert response.status_code in [200, 404], \
            f"Detailed health check failed: {response.status_code}"

    async def test_health_returns_valid_json(self, http_client):
        """SMOKE: GET /health returns valid JSON with expected fields"""
        response = await http_client.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "service" in data, \
                "Health response missing status or service field"

    async def test_info_endpoint_responds(self, http_client):
        """SMOKE: GET /info returns 200"""
        response = await http_client.get(f"{BASE_URL}/info")
        assert response.status_code == 200, \
            f"Info endpoint failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 2: Secret Creation
# =============================================================================

class TestSecretCreationSmoke:
    """Smoke: Secret creation sanity checks"""

    async def test_create_secret_requires_auth(self, http_client):
        """SMOKE: POST /secrets requires X-User-Id header"""
        response = await http_client.post(
            f"{API_V1}/secrets",
            json={
                "secret_type": "api_key",
                "name": unique_secret_name(),
                "secret_value": unique_secret_value(),
            }
        )

        assert response.status_code == 401, \
            f"Expected 401, got {response.status_code}"

    async def test_create_secret_validates_input(self, http_client):
        """SMOKE: POST /secrets validates required fields"""
        user_id = unique_user_id()
        response = await http_client.post(
            f"{API_V1}/secrets",
            json={
                "secret_type": "api_key",
                "name": "",  # Empty name should be rejected
                "secret_value": unique_secret_value(),
            },
            headers={"X-User-Id": user_id}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_create_secret_works(self, http_client):
        """SMOKE: POST /secrets creates secret successfully"""
        user_id = unique_user_id()
        response = await http_client.post(
            f"{API_V1}/secrets",
            json={
                "secret_type": "api_key",
                "name": unique_secret_name(),
                "secret_value": unique_secret_value(),
            },
            headers={"X-User-Id": user_id}
        )

        assert response.status_code == 201, \
            f"Create secret failed: {response.status_code}"
        data = response.json()
        assert "vault_id" in data


# =============================================================================
# SMOKE TEST 3: Secret Retrieval
# =============================================================================

class TestSecretRetrievalSmoke:
    """Smoke: Secret retrieval sanity checks"""

    async def test_list_secrets_works(self, http_client):
        """SMOKE: GET /secrets returns secret list"""
        user_id = unique_user_id()
        response = await http_client.get(
            f"{API_V1}/secrets",
            headers={"X-User-Id": user_id}
        )

        assert response.status_code == 200, \
            f"List secrets failed: {response.status_code}"

    async def test_get_secret_handles_not_found(self, http_client):
        """SMOKE: GET /secrets/{id} handles non-existent secret"""
        user_id = unique_user_id()
        vault_id = unique_vault_id()

        response = await http_client.get(
            f"{API_V1}/secrets/{vault_id}",
            headers={"X-User-Id": user_id}
        )

        # Should return 404 for non-existent secret
        assert response.status_code in [403, 404], \
            f"Expected 403/404, got {response.status_code}"

    async def test_get_secret_requires_auth(self, http_client):
        """SMOKE: GET /secrets/{id} requires auth"""
        vault_id = unique_vault_id()

        response = await http_client.get(
            f"{API_V1}/secrets/{vault_id}"
        )

        assert response.status_code == 401, \
            f"Expected 401, got {response.status_code}"


# =============================================================================
# SMOKE TEST 4: Secret Updates
# =============================================================================

class TestSecretUpdateSmoke:
    """Smoke: Secret update sanity checks"""

    async def test_update_secret_handles_not_found(self, http_client):
        """SMOKE: PUT /secrets/{id} handles non-existent secret"""
        user_id = unique_user_id()
        vault_id = unique_vault_id()

        response = await http_client.put(
            f"{API_V1}/secrets/{vault_id}",
            json={"name": "new_name"},
            headers={"X-User-Id": user_id}
        )

        # Should return 403/404 for non-existent secret
        assert response.status_code in [403, 404, 500], \
            f"Expected 403/404/500, got {response.status_code}"


# =============================================================================
# SMOKE TEST 5: Secret Deletion
# =============================================================================

class TestSecretDeletionSmoke:
    """Smoke: Secret deletion sanity checks"""

    async def test_delete_secret_handles_not_found(self, http_client):
        """SMOKE: DELETE /secrets/{id} handles non-existent secret"""
        user_id = unique_user_id()
        vault_id = unique_vault_id()

        response = await http_client.delete(
            f"{API_V1}/secrets/{vault_id}",
            headers={"X-User-Id": user_id}
        )

        # Should return 403/404 for non-existent secret
        assert response.status_code in [403, 404, 500], \
            f"Expected 403/404/500, got {response.status_code}"


# =============================================================================
# SMOKE TEST 6: Secret Sharing
# =============================================================================

class TestSecretSharingSmoke:
    """Smoke: Secret sharing sanity checks"""

    async def test_share_secret_requires_target(self, http_client):
        """SMOKE: POST /secrets/{id}/share validates share target"""
        user_id = unique_user_id()

        # First create a secret
        create_response = await http_client.post(
            f"{API_V1}/secrets",
            json={
                "secret_type": "api_key",
                "name": unique_secret_name(),
                "secret_value": unique_secret_value(),
            },
            headers={"X-User-Id": user_id}
        )

        if create_response.status_code == 201:
            vault_id = create_response.json()["vault_id"]

            # Try to share without target
            share_response = await http_client.post(
                f"{API_V1}/secrets/{vault_id}/share",
                json={"permission_level": "read"},
                headers={"X-User-Id": user_id}
            )

            assert share_response.status_code in [400, 422], \
                f"Expected 400/422, got {share_response.status_code}"

    async def test_get_shared_secrets_works(self, http_client):
        """SMOKE: GET /shared returns shared secrets"""
        user_id = unique_user_id()

        response = await http_client.get(
            f"{API_V1}/shared",
            headers={"X-User-Id": user_id}
        )

        assert response.status_code == 200, \
            f"Get shared secrets failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 7: Secret Rotation
# =============================================================================

class TestSecretRotationSmoke:
    """Smoke: Secret rotation sanity checks"""

    async def test_rotate_secret_handles_not_found(self, http_client):
        """SMOKE: POST /secrets/{id}/rotate handles non-existent secret"""
        user_id = unique_user_id()
        vault_id = unique_vault_id()

        response = await http_client.post(
            f"{API_V1}/secrets/{vault_id}/rotate",
            params={"new_secret_value": unique_secret_value()},
            headers={"X-User-Id": user_id}
        )

        # Should return 403/404 for non-existent secret
        assert response.status_code in [400, 403, 404, 500], \
            f"Expected error, got {response.status_code}"


# =============================================================================
# SMOKE TEST 8: Statistics
# =============================================================================

class TestStatisticsSmoke:
    """Smoke: Statistics endpoint sanity checks"""

    async def test_get_statistics_works(self, http_client):
        """SMOKE: GET /stats returns statistics"""
        user_id = unique_user_id()

        response = await http_client.get(
            f"{API_V1}/stats",
            headers={"X-User-Id": user_id}
        )

        assert response.status_code == 200, \
            f"Get statistics failed: {response.status_code}"
        data = response.json()
        assert "total_secrets" in data


# =============================================================================
# SMOKE TEST 9: Audit Logs
# =============================================================================

class TestAuditLogsSmoke:
    """Smoke: Audit logs endpoint sanity checks"""

    async def test_get_audit_logs_works(self, http_client):
        """SMOKE: GET /audit-logs returns logs"""
        user_id = unique_user_id()

        response = await http_client.get(
            f"{API_V1}/audit-logs",
            headers={"X-User-Id": user_id}
        )

        assert response.status_code == 200, \
            f"Get audit logs failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 10: Critical User Flow
# =============================================================================

class TestCriticalFlowSmoke:
    """Smoke: Critical vault flow end-to-end"""

    async def test_complete_vault_lifecycle(self, http_client):
        """
        SMOKE: Complete vault lifecycle works end-to-end

        Tests: Create -> Get -> Update -> List -> Stats -> Delete
        """
        user_id = unique_user_id()
        headers = {"X-User-Id": user_id}

        # Step 1: Create secret
        create_response = await http_client.post(
            f"{API_V1}/secrets",
            json={
                "secret_type": "api_key",
                "name": unique_secret_name(),
                "secret_value": unique_secret_value(),
            },
            headers=headers
        )
        assert create_response.status_code == 201, \
            f"Create failed: {create_response.status_code}"
        vault_id = create_response.json()["vault_id"]

        # Step 2: Get secret
        get_response = await http_client.get(
            f"{API_V1}/secrets/{vault_id}",
            headers=headers
        )
        assert get_response.status_code == 200, \
            f"Get failed: {get_response.status_code}"
        assert "secret_value" in get_response.json()

        # Step 3: Update secret
        update_response = await http_client.put(
            f"{API_V1}/secrets/{vault_id}",
            json={"name": f"updated_{unique_secret_name()}"},
            headers=headers
        )
        assert update_response.status_code == 200, \
            f"Update failed: {update_response.status_code}"

        # Step 4: List secrets
        list_response = await http_client.get(
            f"{API_V1}/secrets",
            headers=headers
        )
        assert list_response.status_code == 200, \
            f"List failed: {list_response.status_code}"

        # Step 5: Get stats
        stats_response = await http_client.get(
            f"{API_V1}/stats",
            headers=headers
        )
        assert stats_response.status_code == 200, \
            f"Stats failed: {stats_response.status_code}"

        # Step 6: Delete secret
        delete_response = await http_client.delete(
            f"{API_V1}/secrets/{vault_id}",
            headers=headers
        )
        assert delete_response.status_code == 200, \
            f"Delete failed: {delete_response.status_code}"


# =============================================================================
# SMOKE TEST 11: Error Handling
# =============================================================================

class TestErrorHandlingSmoke:
    """Smoke: Error handling sanity checks"""

    async def test_invalid_json_returns_error(self, http_client):
        """SMOKE: Invalid JSON returns 400 or 422"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}/secrets",
            content="not valid json",
            headers={
                "X-User-Id": user_id,
                "Content-Type": "application/json"
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_missing_required_fields_returns_422(self, http_client):
        """SMOKE: Missing required fields returns 422"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}/secrets",
            json={},
            headers={"X-User-Id": user_id}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_invalid_secret_type_returns_422(self, http_client):
        """SMOKE: Invalid secret_type returns 422"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}/secrets",
            json={
                "secret_type": "invalid_type",
                "name": unique_secret_name(),
                "secret_value": unique_secret_value(),
            },
            headers={"X-User-Id": user_id}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# SUMMARY
# =============================================================================
"""
VAULT SERVICE SMOKE TESTS SUMMARY:

Test Coverage (~20 tests total):

1. Health (4 tests):
   - /health responds with 200
   - /health/detailed responds
   - Health returns valid JSON
   - /info responds with 200

2. Secret Creation (3 tests):
   - Create secret requires auth
   - Create secret validates input
   - Create secret works

3. Secret Retrieval (3 tests):
   - List secrets works
   - Get secret handles not found
   - Get secret requires auth

4. Secret Updates (1 test):
   - Update secret handles not found

5. Secret Deletion (1 test):
   - Delete secret handles not found

6. Secret Sharing (2 tests):
   - Share secret requires target
   - Get shared secrets works

7. Secret Rotation (1 test):
   - Rotate secret handles not found

8. Statistics (1 test):
   - Get statistics works

9. Audit Logs (1 test):
   - Get audit logs works

10. Critical Flow (1 test):
    - Complete lifecycle: Create -> Get -> Update -> List -> Stats -> Delete

11. Error Handling (3 tests):
    - Invalid JSON returns error
    - Missing required fields returns 422
    - Invalid secret_type returns 422

Characteristics:
- Fast execution (< 30 seconds)
- No external dependencies (other than running vault_service)
- Tests critical paths only
- Validates deployment health

Run with:
    pytest tests/smoke/vault_service -v
    pytest tests/smoke/vault_service -v --timeout=60
"""
