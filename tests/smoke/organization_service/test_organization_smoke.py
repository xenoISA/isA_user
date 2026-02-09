"""
Organization Service Smoke Tests

Quick sanity checks to verify organization_service is deployed and functioning correctly.
These tests are designed to:
1. Run quickly (< 30 seconds total)
2. Validate critical paths only
3. Catch obvious deployment failures

Purpose:
- Verify service is up and responding
- Test basic CRUD operations work
- Test critical user flows (create org, add member, switch context)
- Validate data contracts are honored

Usage:
    pytest tests/smoke/organization_service -v
    pytest tests/smoke/organization_service -v -k "health"

Environment Variables:
    ORGANIZATION_BASE_URL: Base URL for organization service (default: http://localhost:8203)
"""

import os
import pytest
import uuid
import httpx
from datetime import datetime

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

# Configuration
BASE_URL = os.getenv("ORGANIZATION_BASE_URL", "http://localhost:8203")
API_V1 = f"{BASE_URL}/api/v1/organizations"
TIMEOUT = 10.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for smoke tests"""
    return f"smoke_test_usr_{uuid.uuid4().hex[:8]}"


def unique_org_name() -> str:
    """Generate unique organization name for smoke tests"""
    return f"Smoke Test Org {uuid.uuid4().hex[:6]}"


def unique_email() -> str:
    """Generate unique email for smoke tests"""
    return f"smoke_test_{uuid.uuid4().hex[:8]}@example.com"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Async HTTP client for smoke tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
async def test_organization(http_client):
    """
    Create a test organization for smoke tests.

    This fixture creates an organization, yields it for testing,
    and cleans it up afterward.
    """
    owner_user_id = unique_user_id()

    # Create organization
    response = await http_client.post(
        API_V1,
        json={
            "name": unique_org_name(),
            "billing_email": unique_email(),
        },
        headers={"X-User-ID": owner_user_id}
    )

    if response.status_code in [200, 201]:
        org_data = response.json()
        org_data["_owner_user_id"] = owner_user_id
        yield org_data

        # Cleanup - try to delete the organization
        try:
            org_id = org_data["organization_id"]
            await http_client.delete(
                f"{API_V1}/{org_id}",
                headers={"X-User-ID": owner_user_id}
            )
        except Exception:
            pass  # Ignore cleanup errors
    else:
        pytest.skip(f"Could not create test organization: {response.status_code} - {response.text}")


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

    async def test_health_contains_status(self, http_client):
        """SMOKE: GET /health returns status field"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data, "Response missing status field"
        assert data["status"] == "healthy"


# =============================================================================
# SMOKE TEST 2: Organization CRUD
# =============================================================================

class TestOrganizationCRUDSmoke:
    """Smoke: Organization CRUD operation sanity checks"""

    async def test_create_organization_works(self, http_client):
        """SMOKE: POST /organizations creates an organization"""
        owner_user_id = unique_user_id()

        response = await http_client.post(
            API_V1,
            json={
                "name": unique_org_name(),
                "billing_email": unique_email(),
            },
            headers={"X-User-ID": owner_user_id}
        )

        assert response.status_code in [200, 201], \
            f"Create organization failed: {response.status_code} - {response.text}"

        data = response.json()
        assert "organization_id" in data, "Response missing organization_id"
        assert data["status"] == "active", "Organization should be active"

        # Cleanup
        try:
            await http_client.delete(
                f"{API_V1}/{data['organization_id']}",
                headers={"X-User-ID": owner_user_id}
            )
        except Exception:
            pass

    async def test_get_organization_works(self, http_client, test_organization):
        """SMOKE: GET /organizations/{id} retrieves organization"""
        org_id = test_organization["organization_id"]
        user_id = test_organization["_owner_user_id"]

        response = await http_client.get(
            f"{API_V1}/{org_id}",
            headers={"X-User-ID": user_id}
        )

        assert response.status_code == 200, \
            f"Get organization failed: {response.status_code}"

        data = response.json()
        assert data["organization_id"] == org_id

    async def test_update_organization_works(self, http_client, test_organization):
        """SMOKE: PUT /organizations/{id} updates organization"""
        org_id = test_organization["organization_id"]
        user_id = test_organization["_owner_user_id"]
        new_name = f"Updated {unique_org_name()}"

        response = await http_client.put(
            f"{API_V1}/{org_id}",
            json={"name": new_name},
            headers={"X-User-ID": user_id}
        )

        assert response.status_code == 200, \
            f"Update organization failed: {response.status_code}"

        data = response.json()
        assert data["name"] == new_name


# =============================================================================
# SMOKE TEST 3: Member Operations
# =============================================================================

class TestMemberSmoke:
    """Smoke: Member operation sanity checks"""

    async def test_get_members_works(self, http_client, test_organization):
        """SMOKE: GET /organizations/{id}/members retrieves members"""
        org_id = test_organization["organization_id"]
        user_id = test_organization["_owner_user_id"]

        response = await http_client.get(
            f"{API_V1}/{org_id}/members",
            headers={"X-User-ID": user_id}
        )

        assert response.status_code == 200, \
            f"Get members failed: {response.status_code}"

        data = response.json()
        assert "members" in data, "Response missing members field"
        assert len(data["members"]) >= 1, "Should have at least owner member"

    async def test_add_member_works(self, http_client, test_organization):
        """SMOKE: POST /organizations/{id}/members adds member"""
        org_id = test_organization["organization_id"]
        owner_id = test_organization["_owner_user_id"]
        new_member_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}/{org_id}/members",
            json={"user_id": new_member_id, "role": "member"},
            headers={"X-User-ID": owner_id}
        )

        assert response.status_code in [200, 201], \
            f"Add member failed: {response.status_code} - {response.text}"

        data = response.json()
        assert data["user_id"] == new_member_id


# =============================================================================
# SMOKE TEST 4: Context Switching
# =============================================================================

class TestContextSmoke:
    """Smoke: Context switching sanity checks"""

    async def test_switch_to_personal_context_works(self, http_client):
        """SMOKE: POST /organizations/context with null org_id works"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}/context",
            json={"organization_id": None},
            headers={"X-User-ID": user_id}
        )

        assert response.status_code == 200, \
            f"Switch context failed: {response.status_code}"

        data = response.json()
        assert data["context_type"] == "individual"

    async def test_switch_to_organization_context_works(self, http_client, test_organization):
        """SMOKE: POST /organizations/context with org_id works"""
        org_id = test_organization["organization_id"]
        user_id = test_organization["_owner_user_id"]

        response = await http_client.post(
            f"{API_V1}/context",
            json={"organization_id": org_id},
            headers={"X-User-ID": user_id}
        )

        assert response.status_code == 200, \
            f"Switch context failed: {response.status_code}"

        data = response.json()
        assert data["context_type"] == "organization"
        assert data["organization_id"] == org_id


# =============================================================================
# SMOKE TEST 5: User Organizations
# =============================================================================

class TestUserOrganizationsSmoke:
    """Smoke: User organizations sanity checks"""

    async def test_get_user_organizations_works(self, http_client, test_organization):
        """SMOKE: GET /organizations/users/{user_id} retrieves user's organizations"""
        user_id = test_organization["_owner_user_id"]

        response = await http_client.get(
            f"{API_V1}/users/{user_id}",
            headers={"X-User-ID": user_id}
        )

        assert response.status_code == 200, \
            f"Get user organizations failed: {response.status_code}"

        data = response.json()
        assert "organizations" in data, "Response missing organizations field"
        assert len(data["organizations"]) >= 1, "Should have at least 1 organization"


# =============================================================================
# SMOKE TEST 6: Statistics
# =============================================================================

class TestStatsSmoke:
    """Smoke: Organization statistics sanity checks"""

    async def test_get_org_stats_works(self, http_client, test_organization):
        """SMOKE: GET /organizations/{id}/stats retrieves statistics"""
        org_id = test_organization["organization_id"]
        user_id = test_organization["_owner_user_id"]

        response = await http_client.get(
            f"{API_V1}/{org_id}/stats",
            headers={"X-User-ID": user_id}
        )

        assert response.status_code == 200, \
            f"Get stats failed: {response.status_code}"

        data = response.json()
        assert "organization_id" in data
        assert "member_count" in data


# =============================================================================
# SMOKE TEST 7: Critical User Flow
# =============================================================================

class TestCriticalFlowSmoke:
    """Smoke: Critical user flow end-to-end"""

    async def test_complete_organization_lifecycle(self, http_client):
        """
        SMOKE: Complete organization lifecycle works end-to-end

        Tests: Create Org -> Add Member -> Switch Context -> Delete Org
        """
        owner_id = unique_user_id()
        member_id = unique_user_id()
        org_id = None

        try:
            # Step 1: Create organization
            create_response = await http_client.post(
                API_V1,
                json={
                    "name": unique_org_name(),
                    "billing_email": unique_email(),
                },
                headers={"X-User-ID": owner_id}
            )
            assert create_response.status_code in [200, 201], "Failed to create org"
            org_id = create_response.json()["organization_id"]

            # Step 2: Add member
            add_member_response = await http_client.post(
                f"{API_V1}/{org_id}/members",
                json={"user_id": member_id, "role": "member"},
                headers={"X-User-ID": owner_id}
            )
            assert add_member_response.status_code in [200, 201], "Failed to add member"

            # Step 3: Switch context for member
            context_response = await http_client.post(
                f"{API_V1}/context",
                json={"organization_id": org_id},
                headers={"X-User-ID": member_id}
            )
            assert context_response.status_code == 200, "Failed to switch context"
            assert context_response.json()["context_type"] == "organization"

            # Step 4: Verify member list
            members_response = await http_client.get(
                f"{API_V1}/{org_id}/members",
                headers={"X-User-ID": owner_id}
            )
            assert members_response.status_code == 200, "Failed to get members"
            assert len(members_response.json()["members"]) >= 2, "Should have 2 members"

            # Step 5: Delete organization
            delete_response = await http_client.delete(
                f"{API_V1}/{org_id}",
                headers={"X-User-ID": owner_id}
            )
            assert delete_response.status_code == 200, "Failed to delete org"

        finally:
            # Cleanup if needed
            if org_id:
                try:
                    await http_client.delete(
                        f"{API_V1}/{org_id}",
                        headers={"X-User-ID": owner_id}
                    )
                except Exception:
                    pass


# =============================================================================
# SMOKE TEST 8: Error Handling
# =============================================================================

class TestErrorHandlingSmoke:
    """Smoke: Error handling sanity checks"""

    async def test_not_found_returns_403_or_404(self, http_client):
        """SMOKE: Non-existent organization returns 403 or 404"""
        fake_org_id = f"org_nonexistent_{uuid.uuid4().hex[:8]}"
        user_id = unique_user_id()

        response = await http_client.get(
            f"{API_V1}/{fake_org_id}",
            headers={"X-User-ID": user_id}
        )

        # Either 404 (not found) or 403 (access denied) is acceptable
        assert response.status_code in [403, 404], \
            f"Expected 403/404, got {response.status_code}"

    async def test_invalid_request_returns_error(self, http_client):
        """SMOKE: Invalid request returns 400 or 422"""
        response = await http_client.post(
            API_V1,
            json={"name": ""},  # Empty name
            headers={"X-User-ID": unique_user_id()}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# SUMMARY
# =============================================================================
"""
ORGANIZATION SERVICE SMOKE TESTS SUMMARY:

Test Coverage (15 tests total):

1. Health (2 tests):
   - /health responds with 200
   - /health contains status field

2. Organization CRUD (3 tests):
   - Create organization works
   - Get organization works
   - Update organization works

3. Members (2 tests):
   - Get members works
   - Add member works

4. Context Switching (2 tests):
   - Switch to personal context works
   - Switch to organization context works

5. User Organizations (1 test):
   - Get user organizations works

6. Statistics (1 test):
   - Get org stats works

7. Critical Flow (1 test):
   - Complete lifecycle: Create -> Add Member -> Switch Context -> Delete

8. Error Handling (2 tests):
   - Not found returns 403/404
   - Invalid request returns error

Characteristics:
- Fast execution (< 30 seconds)
- No external dependencies (other than running organization_service)
- Tests critical paths only
- Validates deployment health

Run with:
    pytest tests/smoke/organization_service -v
    pytest tests/smoke/organization_service -v --timeout=60
"""
