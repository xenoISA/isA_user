"""
Organization Service API Golden Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Usage:
    pytest tests/api/golden/organization_service -v
    pytest tests/api/golden/organization_service -v -k "health"
"""
import pytest
import uuid
from datetime import datetime

from tests.api.conftest import APIClient, APIAssertions

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_org_name() -> str:
    """Generate unique organization name for tests"""
    return f"API Test Org {uuid.uuid4().hex[:8]}"


def unique_email() -> str:
    """Generate unique email for tests"""
    return f"api_test_{uuid.uuid4().hex[:8]}@example.com"


def unique_user_id() -> str:
    """Generate unique user ID for tests"""
    return f"api_test_usr_{uuid.uuid4().hex[:12]}"


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestOrganizationHealthAPIGolden:
    """GOLDEN: Organization service health endpoint contracts"""

    async def test_health_endpoint_returns_200(self, organization_api: APIClient):
        """GOLDEN: GET /health returns 200 OK"""
        response = await organization_api.get_raw("/health")
        assert response.status_code == 200

    async def test_health_response_contains_status(self, organization_api: APIClient):
        """GOLDEN: GET /health returns status field"""
        response = await organization_api.get_raw("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


# =============================================================================
# Organization CRUD Tests
# =============================================================================

class TestOrganizationCreateAPIGolden:
    """GOLDEN: POST /api/v1/organizations endpoint contracts"""

    async def test_create_organization_success(
        self, organization_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / creates organization and returns response"""
        owner_user_id = unique_user_id()

        response = await organization_api.post(
            "",
            json={
                "name": unique_org_name(),
                "billing_email": unique_email(),
            },
            headers={"X-User-ID": owner_user_id}
        )

        api_assert.assert_created(response)
        data = response.json()
        api_assert.assert_has_fields(data, ["organization_id", "name", "billing_email", "status"])
        assert data["status"] == "active"

    async def test_create_organization_validates_empty_name(
        self, organization_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with empty name returns 422"""
        response = await organization_api.post(
            "",
            json={
                "name": "",
                "billing_email": unique_email(),
            },
            headers={"X-User-ID": unique_user_id()}
        )

        api_assert.assert_validation_error(response)

    async def test_create_organization_validates_email_format(
        self, organization_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with invalid email returns 422"""
        response = await organization_api.post(
            "",
            json={
                "name": unique_org_name(),
                "billing_email": "not-an-email",
            },
            headers={"X-User-ID": unique_user_id()}
        )

        api_assert.assert_validation_error(response)


class TestOrganizationGetAPIGolden:
    """GOLDEN: GET /api/v1/organizations/{id} endpoint contracts"""

    async def test_get_organization_not_found(
        self, organization_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{id} with non-existent ID returns 404 or 403"""
        response = await organization_api.get(
            f"/{uuid.uuid4()}",
            headers={"X-User-ID": unique_user_id()}
        )

        # Either 404 (not found) or 403 (access denied) is acceptable
        assert response.status_code in [403, 404], \
            f"Expected 403/404, got {response.status_code}"


class TestOrganizationMembersAPIGolden:
    """GOLDEN: Organization members endpoint contracts"""

    async def test_get_members_requires_access(
        self, organization_api: APIClient
    ):
        """GOLDEN: GET /{id}/members requires user to be a member"""
        response = await organization_api.get(
            f"/{uuid.uuid4()}/members",
            headers={"X-User-ID": unique_user_id()}
        )

        # User is not a member, so should get 403
        assert response.status_code in [403, 404], \
            f"Expected 403/404, got {response.status_code}"


class TestOrganizationContextAPIGolden:
    """GOLDEN: Context switching endpoint contracts"""

    async def test_switch_to_personal_context(
        self, organization_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /context with null org_id returns personal context"""
        user_id = unique_user_id()

        response = await organization_api.post(
            "/context",
            json={"organization_id": None},
            headers={"X-User-ID": user_id}
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["context_type"] == "individual"
        assert data["organization_id"] is None


# =============================================================================
# User Organizations Endpoint Tests
# =============================================================================

class TestUserOrganizationsAPIGolden:
    """GOLDEN: User organizations endpoint contracts"""

    async def test_get_user_organizations_empty(
        self, organization_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /users/{user_id}/organizations returns empty list for new user"""
        user_id = unique_user_id()

        response = await organization_api.get(
            f"/users/{user_id}",
            headers={"X-User-ID": user_id}
        )

        api_assert.assert_success(response)
        data = response.json()
        api_assert.assert_has_fields(data, ["organizations", "total"])
        assert data["total"] == 0
        assert len(data["organizations"]) == 0


# =============================================================================
# Service Info Endpoint Tests
# =============================================================================

class TestOrganizationServiceInfoAPIGolden:
    """GOLDEN: Service info endpoint contracts"""

    async def test_service_info_returns_200(self, organization_api: APIClient):
        """GOLDEN: GET / returns service info"""
        response = await organization_api.get_raw("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "organization_service"
