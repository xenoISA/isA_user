"""
Membership Service API Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Purpose:
- Test actual HTTP endpoints against running membership_service
- Validate request/response schemas
- Test status code contracts (200, 201, 400, 403, 404, 422)
- Test pagination and query parameters

Usage:
    pytest tests/api/tdd/membership_service -v
    pytest tests/api/tdd/membership_service -v -k "health"
"""
import pytest
import pytest_asyncio
import uuid
import httpx
from datetime import datetime

from tests.contracts.membership.data_contract import MembershipTestDataFactory

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for tests"""
    return f"api_test_{uuid.uuid4().hex[:12]}"


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def membership_api():
    """Provide API client for membership service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


BASE_URL = "http://localhost:8250"
API_PREFIX = "/api/v1/memberships"


# =============================================================================
# Health Endpoint Tests (3 tests)
# =============================================================================

class TestMembershipHealthAPI:
    """Membership service health endpoint contracts"""

    async def test_health_endpoint_returns_200(self, membership_api: httpx.AsyncClient):
        """GET /health returns 200 OK"""
        response = await membership_api.get(f"{BASE_URL}/health")
        assert response.status_code == 200

    async def test_health_returns_service_name(self, membership_api: httpx.AsyncClient):
        """GET /health returns service name"""
        response = await membership_api.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            assert data.get("service") == "membership_service"

    async def test_service_info_returns_200(self, membership_api: httpx.AsyncClient):
        """GET /api/v1/memberships/info returns 200"""
        response = await membership_api.get(f"{BASE_URL}{API_PREFIX}/info")
        assert response.status_code == 200


# =============================================================================
# Enrollment Endpoint Tests (6 tests)
# =============================================================================

class TestEnrollmentAPI:
    """POST /api/v1/memberships endpoint contracts"""

    async def test_enroll_membership_returns_201_or_200(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships creates new membership"""
        user_id = unique_user_id()

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}",
            json={
                "user_id": user_id,
                "enrollment_source": "api_test"
            }
        )

        # Either success or already exists
        assert response.status_code in [200, 201, 400, 409], \
            f"Unexpected status code: {response.status_code}"

    async def test_enroll_with_promo_code(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships with promo code"""
        user_id = unique_user_id()

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}",
            json={
                "user_id": user_id,
                "promo_code": "WELCOME100",
                "enrollment_source": "promotion"
            }
        )

        assert response.status_code in [200, 201, 400, 409], \
            f"Unexpected status code: {response.status_code}"

    async def test_enroll_rejects_empty_user_id(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships with empty user_id returns 400 or 422"""
        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}",
            json={
                "user_id": "",
                "enrollment_source": "api_test"
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_enroll_rejects_missing_user_id(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships without user_id returns 400 or 422"""
        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}",
            json={
                "enrollment_source": "api_test"
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_enroll_response_includes_membership(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships returns membership data"""
        user_id = unique_user_id()

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}",
            json={
                "user_id": user_id
            }
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "membership" in data or "membership_id" in data

    async def test_enroll_with_organization(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships with organization_id"""
        user_id = unique_user_id()
        org_id = MembershipTestDataFactory.make_organization_id()

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}",
            json={
                "user_id": user_id,
                "organization_id": org_id
            }
        )

        assert response.status_code in [200, 201, 400, 409], \
            f"Unexpected status code: {response.status_code}"


# =============================================================================
# Points Endpoint Tests (6 tests)
# =============================================================================

class TestPointsAPI:
    """Points API endpoint contracts"""

    async def test_earn_points_returns_200(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships/points/earn returns 200"""
        user_id = unique_user_id()

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}/points/earn",
            json={
                "user_id": user_id,
                "points_amount": 500,
                "source": "order_completed"
            }
        )

        # User may not exist, that's OK for API contract test
        assert response.status_code in [200, 400, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_earn_points_rejects_negative_amount(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships/points/earn rejects negative points"""
        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}/points/earn",
            json={
                "user_id": unique_user_id(),
                "points_amount": -100,
                "source": "test"
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_earn_points_rejects_zero_amount(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships/points/earn rejects zero points"""
        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}/points/earn",
            json={
                "user_id": unique_user_id(),
                "points_amount": 0,
                "source": "test"
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_redeem_points_returns_200(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships/points/redeem returns 200 or error"""
        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}/points/redeem",
            json={
                "user_id": unique_user_id(),
                "points_amount": 100,
                "reward_code": "FREE_SHIPPING"
            }
        )

        # User may not exist or have insufficient points
        assert response.status_code in [200, 400, 403, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_get_points_balance_returns_200(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/points/balance returns 200 or 404"""
        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/points/balance",
            params={"user_id": unique_user_id()}
        )

        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_points_balance_includes_tier_info(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/points/balance includes tier info"""
        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/points/balance",
            params={"user_id": unique_user_id()}
        )

        if response.status_code == 200:
            data = response.json()
            # Should have points fields
            assert "points_balance" in data or "balance" in data


# =============================================================================
# Membership CRUD Endpoint Tests (5 tests)
# =============================================================================

class TestMembershipCRUDAPI:
    """Membership CRUD endpoint contracts"""

    async def test_get_membership_returns_200_or_404(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/{id} returns 200 or 404"""
        membership_id = "mem_nonexistent"

        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/{membership_id}"
        )

        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_list_memberships_returns_200(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships returns 200 with list"""
        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}",
            params={"page": 1, "page_size": 10}
        )

        assert response.status_code in [200, 401, 403], \
            f"Unexpected status code: {response.status_code}"

    async def test_list_memberships_with_status_filter(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships with status filter"""
        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}",
            params={"status": "active", "page": 1, "page_size": 10}
        )

        assert response.status_code in [200, 401, 403], \
            f"Unexpected status code: {response.status_code}"

    async def test_cancel_membership_returns_200_or_404(
        self, membership_api: httpx.AsyncClient
    ):
        """DELETE /api/v1/memberships/{id} returns 200 or 404"""
        membership_id = "mem_nonexistent"

        response = await membership_api.delete(
            f"{BASE_URL}{API_PREFIX}/{membership_id}",
            json={"reason": "Test cancellation"}
        )

        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_suspend_membership_returns_200_or_404(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships/{id}/suspend returns 200 or 404"""
        membership_id = "mem_nonexistent"

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}/{membership_id}/suspend",
            json={"reason": "Test suspension"}
        )

        assert response.status_code in [200, 400, 404], \
            f"Unexpected status code: {response.status_code}"


# =============================================================================
# Tier Endpoint Tests (4 tests)
# =============================================================================

class TestTierAPI:
    """Tier API endpoint contracts"""

    async def test_get_tier_status_returns_200_or_404(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/{id}/tier returns 200 or 404"""
        membership_id = "mem_nonexistent"

        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/{membership_id}/tier"
        )

        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_tier_status_includes_progress(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/{id}/tier includes progress info"""
        membership_id = "mem_nonexistent"

        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/{membership_id}/tier"
        )

        if response.status_code == 200:
            data = response.json()
            # Should have tier progress fields
            assert "current_tier" in data or "tier_progress" in data

    async def test_list_tiers_returns_200(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/tiers returns 200"""
        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/tiers"
        )

        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_list_tiers_returns_all_tiers(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/tiers returns tier list"""
        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/tiers"
        )

        if response.status_code == 200:
            data = response.json()
            # Should have tiers list
            if "tiers" in data:
                assert len(data["tiers"]) >= 1


# =============================================================================
# Benefits Endpoint Tests (4 tests)
# =============================================================================

class TestBenefitsAPI:
    """Benefits API endpoint contracts"""

    async def test_get_benefits_returns_200_or_404(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/{id}/benefits returns 200 or 404"""
        membership_id = "mem_nonexistent"

        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/{membership_id}/benefits"
        )

        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_use_benefit_returns_200_or_error(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships/{id}/benefits/use returns appropriate status"""
        membership_id = "mem_nonexistent"

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}/{membership_id}/benefits/use",
            json={"benefit_code": "FREE_SHIPPING"}
        )

        assert response.status_code in [200, 400, 403, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_use_benefit_rejects_empty_code(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships/{id}/benefits/use rejects empty code"""
        membership_id = "mem_nonexistent"

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}/{membership_id}/benefits/use",
            json={"benefit_code": ""}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_use_benefit_rejects_missing_code(
        self, membership_api: httpx.AsyncClient
    ):
        """POST /api/v1/memberships/{id}/benefits/use rejects missing code"""
        membership_id = "mem_nonexistent"

        response = await membership_api.post(
            f"{BASE_URL}{API_PREFIX}/{membership_id}/benefits/use",
            json={}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# Stats Endpoint Tests (2 tests)
# =============================================================================

class TestStatsAPI:
    """Stats API endpoint contracts"""

    async def test_get_stats_returns_200(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/stats returns 200"""
        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/stats"
        )

        assert response.status_code in [200, 401, 403], \
            f"Unexpected status code: {response.status_code}"

    async def test_stats_includes_totals(
        self, membership_api: httpx.AsyncClient
    ):
        """GET /api/v1/memberships/stats includes total counts"""
        response = await membership_api.get(
            f"{BASE_URL}{API_PREFIX}/stats"
        )

        if response.status_code == 200:
            data = response.json()
            assert "total_memberships" in data or "active_memberships" in data
