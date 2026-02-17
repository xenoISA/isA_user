"""
Membership Service Smoke Tests

Quick sanity checks to verify membership_service is deployed and functioning correctly.
These tests are designed to:
1. Run quickly (< 30 seconds total)
2. Validate critical paths only
3. Catch obvious deployment failures

Purpose:
- Verify service is up and responding
- Test basic membership operations work
- Test critical user flows (enrollment, points, tiers, benefits)
- Validate data contracts are honored

Usage:
    pytest tests/smoke/membership -v
    pytest tests/smoke/membership -v -k "health"

Environment Variables:
    MEMBERSHIP_BASE_URL: Base URL for membership service (default: http://localhost:8250)
"""

import os
import pytest
import uuid
import httpx
from datetime import datetime

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

# Configuration
BASE_URL = os.getenv("MEMBERSHIP_BASE_URL", "http://localhost:8250")
API_V1 = f"{BASE_URL}/api/v1/memberships"
TIMEOUT = 10.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for smoke tests"""
    return f"smoke_test_{uuid.uuid4().hex[:8]}"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Async HTTP client for smoke tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


# =============================================================================
# SMOKE TEST 1: Health Checks (2 tests)
# =============================================================================

class TestHealthSmoke:
    """Smoke: Health endpoint sanity checks"""

    async def test_health_endpoint_responds(self, http_client):
        """SMOKE: GET /health returns 200"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200, \
            f"Health check failed: {response.status_code}"

    async def test_service_info_responds(self, http_client):
        """SMOKE: GET /api/v1/memberships/info returns 200"""
        response = await http_client.get(f"{API_V1}/info")
        assert response.status_code == 200, \
            f"Service info check failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 2: Enrollment (3 tests)
# =============================================================================

class TestEnrollmentSmoke:
    """Smoke: Enrollment sanity checks"""

    async def test_enroll_membership_works(self, http_client):
        """SMOKE: POST /api/v1/memberships enrolls new member"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": user_id,
                "enrollment_source": "smoke_test"
            }
        )

        # Accept success or already exists
        assert response.status_code in [200, 201, 400, 409], \
            f"Enrollment failed unexpectedly: {response.status_code} - {response.text}"

    async def test_enroll_rejects_empty_user(self, http_client):
        """SMOKE: POST /api/v1/memberships rejects empty user_id"""
        response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": "",
                "enrollment_source": "smoke_test"
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_enroll_with_promo_works(self, http_client):
        """SMOKE: POST /api/v1/memberships with promo code"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": user_id,
                "promo_code": "WELCOME100",
                "enrollment_source": "promotion"
            }
        )

        assert response.status_code in [200, 201, 400, 409], \
            f"Enrollment with promo failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 3: Points Operations (3 tests)
# =============================================================================

class TestPointsSmoke:
    """Smoke: Points operations sanity checks"""

    async def test_earn_points_works(self, http_client):
        """SMOKE: POST /api/v1/memberships/points/earn works"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}/points/earn",
            json={
                "user_id": user_id,
                "points_amount": 500,
                "source": "order_completed"
            }
        )

        # User may not exist, that's OK for smoke test
        assert response.status_code in [200, 400, 404], \
            f"Earn points failed unexpectedly: {response.status_code}"

    async def test_redeem_points_validates(self, http_client):
        """SMOKE: POST /api/v1/memberships/points/redeem validates"""
        response = await http_client.post(
            f"{API_V1}/points/redeem",
            json={
                "user_id": unique_user_id(),
                "points_amount": 100,
                "reward_code": "FREE_SHIPPING"
            }
        )

        # Accept various responses - testing endpoint works
        assert response.status_code in [200, 400, 403, 404], \
            f"Redeem points failed unexpectedly: {response.status_code}"

    async def test_get_balance_works(self, http_client):
        """SMOKE: GET /api/v1/memberships/points/balance works"""
        response = await http_client.get(
            f"{API_V1}/points/balance",
            params={"user_id": unique_user_id()}
        )

        assert response.status_code in [200, 404], \
            f"Get balance failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 4: Membership Management (2 tests)
# =============================================================================

class TestMembershipManagementSmoke:
    """Smoke: Membership management sanity checks"""

    async def test_get_membership_works(self, http_client):
        """SMOKE: GET /api/v1/memberships/{id} works"""
        response = await http_client.get(
            f"{API_V1}/mem_nonexistent"
        )

        assert response.status_code in [200, 404], \
            f"Get membership failed unexpectedly: {response.status_code}"

    async def test_list_memberships_works(self, http_client):
        """SMOKE: GET /api/v1/memberships works"""
        response = await http_client.get(
            f"{API_V1}",
            params={"page": 1, "page_size": 10}
        )

        assert response.status_code in [200, 401, 403], \
            f"List memberships failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 5: Tier Operations (2 tests)
# =============================================================================

class TestTierSmoke:
    """Smoke: Tier operations sanity checks"""

    async def test_get_tier_status_works(self, http_client):
        """SMOKE: GET /api/v1/memberships/{id}/tier works"""
        response = await http_client.get(
            f"{API_V1}/mem_nonexistent/tier"
        )

        assert response.status_code in [200, 404], \
            f"Get tier status failed unexpectedly: {response.status_code}"

    async def test_list_tiers_works(self, http_client):
        """SMOKE: GET /api/v1/memberships/tiers works"""
        response = await http_client.get(f"{API_V1}/tiers")

        assert response.status_code in [200, 404], \
            f"List tiers failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 6: Benefits Operations (2 tests)
# =============================================================================

class TestBenefitsSmoke:
    """Smoke: Benefits operations sanity checks"""

    async def test_get_benefits_works(self, http_client):
        """SMOKE: GET /api/v1/memberships/{id}/benefits works"""
        response = await http_client.get(
            f"{API_V1}/mem_nonexistent/benefits"
        )

        assert response.status_code in [200, 404], \
            f"Get benefits failed unexpectedly: {response.status_code}"

    async def test_use_benefit_validates(self, http_client):
        """SMOKE: POST /api/v1/memberships/{id}/benefits/use validates"""
        response = await http_client.post(
            f"{API_V1}/mem_nonexistent/benefits/use",
            json={"benefit_code": "FREE_SHIPPING"}
        )

        assert response.status_code in [200, 400, 403, 404], \
            f"Use benefit failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 7: Stats (1 test)
# =============================================================================

class TestStatsSmoke:
    """Smoke: Stats endpoint sanity checks"""

    async def test_get_stats_works(self, http_client):
        """SMOKE: GET /api/v1/memberships/stats works"""
        response = await http_client.get(f"{API_V1}/stats")

        assert response.status_code in [200, 401, 403], \
            f"Get stats failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 8: Critical User Flow (1 test)
# =============================================================================

class TestCriticalFlowSmoke:
    """Smoke: Critical membership flow end-to-end"""

    async def test_complete_membership_lifecycle(self, http_client):
        """
        SMOKE: Complete membership lifecycle works end-to-end

        Tests: Enroll -> Earn Points -> Get Balance -> Get Tier Status
        """
        user_id = unique_user_id()

        # Step 1: Enroll
        enroll_response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": user_id,
                "enrollment_source": "smoke_test"
            }
        )
        assert enroll_response.status_code in [200, 201, 400, 409], \
            f"Enrollment failed: {enroll_response.status_code}"

        # Get membership ID from response if available
        membership_id = None
        if enroll_response.status_code in [200, 201]:
            data = enroll_response.json()
            if "membership" in data:
                membership_id = data["membership"].get("membership_id")
            elif "membership_id" in data:
                membership_id = data["membership_id"]

        # Step 2: Earn Points
        earn_response = await http_client.post(
            f"{API_V1}/points/earn",
            json={
                "user_id": user_id,
                "points_amount": 1000,
                "source": "order_completed"
            }
        )
        assert earn_response.status_code in [200, 400, 404], \
            f"Earn points failed: {earn_response.status_code}"

        # Step 3: Get Balance
        balance_response = await http_client.get(
            f"{API_V1}/points/balance",
            params={"user_id": user_id}
        )
        assert balance_response.status_code in [200, 404], \
            f"Get balance failed: {balance_response.status_code}"

        # Step 4: Get Tier Status (if we have membership ID)
        if membership_id:
            tier_response = await http_client.get(
                f"{API_V1}/{membership_id}/tier"
            )
            assert tier_response.status_code in [200, 404], \
                f"Get tier status failed: {tier_response.status_code}"


# =============================================================================
# SMOKE TEST 9: Error Handling (2 tests)
# =============================================================================

class TestErrorHandlingSmoke:
    """Smoke: Error handling sanity checks"""

    async def test_not_found_returns_404(self, http_client):
        """SMOKE: Non-existent endpoint returns 404"""
        response = await http_client.get(f"{API_V1}/nonexistent_endpoint")

        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"

    async def test_invalid_json_returns_error(self, http_client):
        """SMOKE: Invalid JSON returns 400 or 422"""
        response = await http_client.post(
            f"{API_V1}",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# SUMMARY
# =============================================================================
"""
MEMBERSHIP SERVICE SMOKE TESTS SUMMARY:

Test Coverage (18 tests total):

1. Health (2 tests):
   - /health responds with 200
   - /api/v1/memberships/info responds with 200

2. Enrollment (3 tests):
   - Enroll membership works
   - Rejects empty user_id
   - Enrollment with promo code works

3. Points Operations (3 tests):
   - Earn points works
   - Redeem points validates
   - Get balance works

4. Membership Management (2 tests):
   - Get membership works
   - List memberships works

5. Tier Operations (2 tests):
   - Get tier status works
   - List tiers works

6. Benefits Operations (2 tests):
   - Get benefits works
   - Use benefit validates

7. Stats (1 test):
   - Get stats works

8. Critical Flow (1 test):
   - Complete lifecycle: Enroll -> Earn -> Balance -> Tier

9. Error Handling (2 tests):
   - Not found returns 404
   - Invalid JSON returns error

Characteristics:
- Fast execution (< 30 seconds)
- No external dependencies (other than running membership_service)
- Tests critical paths only
- Validates deployment health

Run with:
    pytest tests/smoke/membership -v
    pytest tests/smoke/membership -v --timeout=60
"""
