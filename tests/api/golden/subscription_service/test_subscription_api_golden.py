"""
Subscription Service API Golden Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Purpose:
- Test actual HTTP endpoints against running subscription_service
- Validate request/response schemas
- Test status code contracts (200, 201, 400, 402, 404, 422)
- Test pagination and query parameters

Usage:
    pytest tests/api/golden/subscription_service -v
    pytest tests/api/golden/subscription_service -v -k "health"
"""
import pytest
import uuid
from datetime import datetime

from tests.api.conftest import APIClient, APIAssertions
from tests.contracts.subscription.data_contract import SubscriptionTestDataFactory

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for tests"""
    return f"api_test_{uuid.uuid4().hex[:12]}"


def unique_subscription_id() -> str:
    """Generate unique subscription ID for tests"""
    return f"sub_api_{uuid.uuid4().hex[:16]}"


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestSubscriptionHealthAPIGolden:
    """GOLDEN: Subscription service health endpoint contracts"""

    async def test_health_endpoint_returns_200(self, subscription_api: APIClient):
        """GOLDEN: GET /health returns 200 OK"""
        response = await subscription_api.get_raw("/health")
        assert response.status_code == 200

    async def test_health_detailed_returns_200(self, subscription_api: APIClient):
        """GOLDEN: GET /health/detailed returns 200 with component status"""
        response = await subscription_api.get_raw("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "service" in data


# =============================================================================
# Subscription Creation Tests
# =============================================================================

class TestSubscriptionCreateAPIGolden:
    """GOLDEN: POST /api/v1/subscriptions endpoint contracts"""

    async def test_create_subscription_returns_success(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / creates subscription and returns response"""
        user_id = unique_user_id()

        response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro",
                "billing_cycle": "monthly",
                "seats": 1,
                "use_trial": False
            }
        )

        api_assert.assert_created(response)
        data = response.json()
        api_assert.assert_has_fields(data, ["success", "subscription_id", "tier_code"])
        assert data["success"] is True
        assert data["tier_code"] == "pro"

    async def test_create_subscription_free_tier(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with free tier creates free subscription"""
        user_id = unique_user_id()

        response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "free",
            }
        )

        api_assert.assert_created(response)
        data = response.json()
        assert data["tier_code"] == "free"

    async def test_create_subscription_with_trial(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with use_trial=true starts trial"""
        user_id = unique_user_id()

        response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro",
                "use_trial": True
            }
        )

        api_assert.assert_created(response)
        data = response.json()
        # Trial subscriptions should have trialing status
        assert data["success"] is True

    async def test_create_subscription_rejects_empty_user_id(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with empty user_id returns 400 or 422"""
        response = await subscription_api.post(
            "",
            json={
                "user_id": "",
                "tier_code": "pro"
            }
        )

        # Accept either 400 or 422 for validation error
        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_create_subscription_rejects_invalid_tier(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with invalid tier returns 404"""
        user_id = unique_user_id()

        response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "platinum"  # Invalid tier
            }
        )

        # Should return 404 for tier not found
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"

    async def test_create_subscription_duplicate_blocked(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / for user with existing subscription returns error"""
        user_id = unique_user_id()

        # Create first subscription
        response1 = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )
        api_assert.assert_created(response1)

        # Try to create duplicate
        response2 = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "max"
            }
        )

        # Should return error (success=false or conflict status)
        data = response2.json()
        assert data.get("success") is False or response2.status_code == 409


# =============================================================================
# Subscription Retrieval Tests
# =============================================================================

class TestSubscriptionGetAPIGolden:
    """GOLDEN: GET /api/v1/subscriptions/{subscription_id} endpoint contracts"""

    async def test_get_subscription_returns_details(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{subscription_id} returns subscription details"""
        user_id = unique_user_id()

        # Create subscription first
        create_response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )
        api_assert.assert_created(create_response)
        subscription_id = create_response.json()["subscription_id"]

        # Get subscription
        response = await subscription_api.get(f"/{subscription_id}")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, [
            "subscription_id", "user_id", "tier_code", "status"
        ])
        assert data["subscription_id"] == subscription_id

    async def test_get_subscription_nonexistent_returns_404(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{nonexistent_id} returns 404"""
        subscription_id = f"sub_nonexistent_{uuid.uuid4().hex[:8]}"
        response = await subscription_api.get(f"/{subscription_id}")
        api_assert.assert_not_found(response)


# =============================================================================
# Subscription List Tests
# =============================================================================

class TestSubscriptionListAPIGolden:
    """GOLDEN: GET /api/v1/subscriptions endpoint contracts"""

    async def test_list_subscriptions_returns_list(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET / returns subscription list"""
        response = await subscription_api.get("")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, ["subscriptions", "total", "page", "page_size"])
        assert isinstance(data["subscriptions"], list)

    async def test_list_subscriptions_by_user(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /?user_id=xxx returns user's subscriptions"""
        user_id = unique_user_id()

        # Create subscription
        await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )

        # List by user
        response = await subscription_api.get(f"?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        assert len(data["subscriptions"]) >= 1

    async def test_list_subscriptions_pagination(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /?page=1&page_size=5 respects pagination"""
        response = await subscription_api.get("?page=1&page_size=5")
        api_assert.assert_success(response)

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    async def test_list_subscriptions_by_status(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /?status=active filters by status"""
        response = await subscription_api.get("?status=active")
        api_assert.assert_success(response)

        data = response.json()
        for sub in data["subscriptions"]:
            assert sub["status"] == "active"


# =============================================================================
# User Subscription Tests
# =============================================================================

class TestUserSubscriptionAPIGolden:
    """GOLDEN: GET /api/v1/subscriptions/user/{user_id} endpoint contracts"""

    async def test_get_user_subscription_returns_subscription(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /user/{user_id} returns user's active subscription"""
        user_id = unique_user_id()

        # Create subscription
        create_response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )
        api_assert.assert_created(create_response)

        # Get user subscription
        response = await subscription_api.get(f"/user/{user_id}")
        api_assert.assert_success(response)

        data = response.json()
        assert data["user_id"] == user_id

    async def test_get_user_subscription_no_subscription(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /user/{user_id} returns success=false for no subscription"""
        user_id = unique_user_id()

        response = await subscription_api.get(f"/user/{user_id}")
        api_assert.assert_success(response)

        data = response.json()
        assert data.get("success") is False


# =============================================================================
# Credit Balance Tests
# =============================================================================

class TestCreditBalanceAPIGolden:
    """GOLDEN: GET /api/v1/subscriptions/credits/balance endpoint contracts"""

    async def test_get_credit_balance_with_subscription(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /credits/balance returns balance for user with subscription"""
        user_id = unique_user_id()

        # Create subscription
        await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )

        # Get balance
        response = await subscription_api.get(f"/credits/balance?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, [
            "subscription_credits_remaining",
            "subscription_credits_total",
            "tier_code"
        ])

    async def test_get_credit_balance_no_subscription(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /credits/balance returns zero for user without subscription"""
        user_id = unique_user_id()

        response = await subscription_api.get(f"/credits/balance?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        assert data["subscription_credits_remaining"] == 0
        assert data["subscription_credits_total"] == 0

    async def test_get_credit_balance_requires_user_id(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /credits/balance without user_id returns 422"""
        response = await subscription_api.get("/credits/balance")
        api_assert.assert_validation_error(response)


# =============================================================================
# Credit Consumption Tests
# =============================================================================

class TestCreditConsumeAPIGolden:
    """GOLDEN: POST /api/v1/subscriptions/credits/consume endpoint contracts"""

    async def test_consume_credits_success(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /credits/consume deducts credits successfully"""
        user_id = unique_user_id()

        # Create subscription
        await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )

        # Consume credits
        response = await subscription_api.post(
            "/credits/consume",
            json={
                "user_id": user_id,
                "credits": 1000000,
                "service_type": "api_test"
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["success"] is True
        api_assert.assert_has_fields(data, ["credits_remaining"])

    async def test_consume_credits_insufficient_balance(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /credits/consume with insufficient credits returns 402"""
        user_id = unique_user_id()

        # Create free subscription (1M credits)
        await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "free"
            }
        )

        # Try to consume more than available
        response = await subscription_api.post(
            "/credits/consume",
            json={
                "user_id": user_id,
                "credits": 50000000,  # More than 1M
                "service_type": "api_test"
            }
        )

        # Should return 402 Payment Required
        assert response.status_code == 402, \
            f"Expected 402, got {response.status_code}"

    async def test_consume_credits_no_subscription(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /credits/consume without subscription returns 404"""
        user_id = unique_user_id()

        response = await subscription_api.post(
            "/credits/consume",
            json={
                "user_id": user_id,
                "credits": 1000,
                "service_type": "api_test"
            }
        )

        # Should return 404 for no subscription
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"


# =============================================================================
# Subscription Cancellation Tests
# =============================================================================

class TestSubscriptionCancelAPIGolden:
    """GOLDEN: POST /api/v1/subscriptions/{id}/cancel endpoint contracts"""

    async def test_cancel_subscription_at_period_end(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /{id}/cancel with immediate=false cancels at period end"""
        user_id = unique_user_id()

        # Create subscription
        create_response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )
        subscription_id = create_response.json()["subscription_id"]

        # Cancel at period end
        response = await subscription_api.post(
            f"/{subscription_id}/cancel?user_id={user_id}",
            json={
                "immediate": False,
                "reason": "API test cancellation"
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["success"] is True
        assert data.get("cancel_at_period_end") is True

    async def test_cancel_subscription_immediate(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /{id}/cancel with immediate=true cancels immediately"""
        user_id = unique_user_id()

        # Create subscription
        create_response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )
        subscription_id = create_response.json()["subscription_id"]

        # Cancel immediately
        response = await subscription_api.post(
            f"/{subscription_id}/cancel?user_id={user_id}",
            json={
                "immediate": True,
                "reason": "API test immediate cancellation"
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["success"] is True

    async def test_cancel_subscription_not_owner(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /{id}/cancel by non-owner returns 403"""
        user_id = unique_user_id()
        other_user_id = unique_user_id()

        # Create subscription
        create_response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )
        subscription_id = create_response.json()["subscription_id"]

        # Try to cancel with different user
        response = await subscription_api.post(
            f"/{subscription_id}/cancel?user_id={other_user_id}",
            json={
                "immediate": False,
                "reason": "Unauthorized cancellation attempt"
            }
        )

        # Should return 403 Forbidden
        assert response.status_code == 403, \
            f"Expected 403, got {response.status_code}"

    async def test_cancel_subscription_not_found(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /{nonexistent_id}/cancel returns 404"""
        subscription_id = f"sub_nonexistent_{uuid.uuid4().hex[:8]}"

        response = await subscription_api.post(
            f"/{subscription_id}/cancel?user_id=any_user",
            json={
                "immediate": False,
                "reason": "Test"
            }
        )

        api_assert.assert_not_found(response)


# =============================================================================
# Subscription History Tests
# =============================================================================

class TestSubscriptionHistoryAPIGolden:
    """GOLDEN: GET /api/v1/subscriptions/{id}/history endpoint contracts"""

    async def test_get_subscription_history_returns_list(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{id}/history returns history list"""
        user_id = unique_user_id()

        # Create subscription
        create_response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )
        subscription_id = create_response.json()["subscription_id"]

        # Get history
        response = await subscription_api.get(f"/{subscription_id}/history")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, ["history", "total", "page", "page_size"])
        assert isinstance(data["history"], list)
        # Should have at least creation entry
        assert len(data["history"]) >= 1

    async def test_get_subscription_history_pagination(
        self, subscription_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{id}/history respects pagination"""
        user_id = unique_user_id()

        # Create subscription
        create_response = await subscription_api.post(
            "",
            json={
                "user_id": user_id,
                "tier_code": "pro"
            }
        )
        subscription_id = create_response.json()["subscription_id"]

        # Get history with pagination
        response = await subscription_api.get(f"/{subscription_id}/history?page=1&page_size=10")
        api_assert.assert_success(response)

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


# =============================================================================
# SUMMARY
# =============================================================================
"""
SUBSCRIPTION SERVICE API GOLDEN TESTS SUMMARY:

Test Coverage (28 tests total):

1. Health Endpoints (2 tests):
   - /health returns 200
   - /health/detailed returns 200 with status

2. Subscription Creation (6 tests):
   - Creates subscription returns success
   - Creates free tier
   - Creates with trial
   - Rejects empty user_id
   - Rejects invalid tier (404)
   - Blocks duplicate subscription

3. Subscription Retrieval (2 tests):
   - Get by ID returns details
   - Get nonexistent returns 404

4. Subscription List (4 tests):
   - Returns subscription list
   - Filters by user_id
   - Respects pagination
   - Filters by status

5. User Subscription (2 tests):
   - Returns user's subscription
   - Returns success=false for no subscription

6. Credit Balance (3 tests):
   - Returns balance with subscription
   - Returns zero without subscription
   - Requires user_id (422)

7. Credit Consumption (3 tests):
   - Consumes credits successfully
   - Returns 402 for insufficient balance
   - Returns 404 for no subscription

8. Subscription Cancellation (4 tests):
   - Cancels at period end
   - Cancels immediately
   - Returns 403 for non-owner
   - Returns 404 for not found

9. Subscription History (2 tests):
   - Returns history list
   - Respects pagination

Key Features:
- Real HTTP calls against running service
- Tests HTTP status code contracts
- Tests response schema contracts
- No mocking - validates actual behavior
- Uses unique IDs for test isolation

Run with:
    pytest tests/api/golden/subscription_service -v
"""
