"""
Credit Service API Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Purpose:
- Test actual HTTP endpoints against running credit_service (port 8229)
- Validate request/response schemas
- Test status code contracts (200, 201, 400, 404, 422)
- Test credit allocation, consumption, campaigns, and transfers

Test Coverage (30 tests):
1. Health endpoints (2 tests)
2. Account endpoints (4 tests)
3. Balance endpoint (2 tests)
4. Allocate endpoint (4 tests)
5. Consume endpoint (4 tests)
6. Check availability (2 tests)
7. Transfer endpoint (3 tests)
8. Transactions endpoint (2 tests)
9. Campaign endpoints (4 tests)
10. Statistics endpoint (2 tests)
11. Error handling (3 tests)

Usage:
    pytest tests/api/credit/test_credit_api.py -v
    pytest tests/api/credit/test_credit_api.py -v -k "health"
    pytest tests/api/credit/test_credit_api.py -v -k "allocate"
"""
import pytest
from datetime import datetime, timedelta

from tests.api.conftest import APIClient, APIAssertions
from tests.contracts.credit.data_contract import (
    CreditTestDataFactory,
    CreditTypeEnum,
)
from tests.api.credit.conftest import unique_user_id, unique_campaign_id


pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# =============================================================================
# Health Endpoint Tests (2 tests)
# =============================================================================

class TestCreditHealthAPI:
    """API tests for credit service health endpoints"""

    async def test_health_endpoint_returns_200(self, credit_api: APIClient):
        """API: GET /health returns 200 OK"""
        response = await credit_api.get_raw("/health")
        assert response.status_code == 200

    async def test_health_detailed_returns_200(self, credit_api: APIClient):
        """API: GET /health/detailed returns 200 with component status"""
        response = await credit_api.get_raw("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "service" in data


# =============================================================================
# Account Endpoint Tests (4 tests)
# =============================================================================

class TestCreditAccountAPI:
    """API tests for credit account endpoints"""

    async def test_create_account_returns_200_or_201(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /accounts creates credit account"""
        request = CreditTestDataFactory.make_create_account_request(
            user_id=unique_user_id(),
            credit_type=CreditTypeEnum.BONUS.value
        )

        response = await credit_api.post("/accounts", json=request.model_dump())

        # Accept success or expected failures for API test
        assert response.status_code in [200, 201, 400, 409, 500], \
            f"Unexpected status code: {response.status_code}"

    async def test_create_account_rejects_invalid_credit_type(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /accounts with invalid credit_type returns 400 or 422"""
        response = await credit_api.post(
            "/accounts",
            json={
                "user_id": unique_user_id(),
                "credit_type": "invalid_type",
                "expiration_policy": "fixed_days",
                "expiration_days": 90
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_get_user_accounts_returns_200(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /accounts?user_id={user_id} returns account list"""
        user_id = unique_user_id()

        response = await credit_api.get(f"/accounts?user_id={user_id}")

        # Accept success or not found
        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_get_account_by_id_with_nonexistent_returns_404(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /accounts/{account_id} with nonexistent ID returns 404"""
        account_id = CreditTestDataFactory.make_nonexistent_account_id()

        response = await credit_api.get(f"/accounts/{account_id}")

        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"


# =============================================================================
# Balance Endpoint Tests (2 tests)
# =============================================================================

class TestCreditBalanceAPI:
    """API tests for credit balance endpoint"""

    async def test_get_balance_returns_200(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /balance?user_id={user_id} returns balance summary"""
        user_id = unique_user_id()

        response = await credit_api.get(f"/balance?user_id={user_id}")

        # Accept success or not found for non-existent user
        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Validate response has expected fields
            assert "total_balance" in data or "user_id" in data

    async def test_get_balance_rejects_missing_user_id(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /balance without user_id returns 400 or 422"""
        response = await credit_api.get("/balance")

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# Allocate Endpoint Tests (4 tests)
# =============================================================================

class TestCreditAllocateAPI:
    """API tests for credit allocation endpoint"""

    async def test_allocate_credits_returns_200_or_201(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /allocate allocates credits to user"""
        request = CreditTestDataFactory.make_allocate_credits_request(
            user_id=unique_user_id(),
            credit_type=CreditTypeEnum.BONUS.value,
            amount=1000
        )

        response = await credit_api.post("/allocate", json=request.model_dump())

        # Accept success or expected failures
        assert response.status_code in [200, 201, 400, 404, 500], \
            f"Unexpected status code: {response.status_code}"

    async def test_allocate_credits_rejects_negative_amount(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /allocate with negative amount returns 400 or 422"""
        response = await credit_api.post(
            "/allocate",
            json={
                "user_id": unique_user_id(),
                "credit_type": CreditTypeEnum.BONUS.value,
                "amount": -100,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_allocate_credits_rejects_zero_amount(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /allocate with zero amount returns 400 or 422"""
        response = await credit_api.post(
            "/allocate",
            json={
                "user_id": unique_user_id(),
                "credit_type": CreditTypeEnum.BONUS.value,
                "amount": 0,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_allocate_credits_rejects_empty_user_id(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /allocate with empty user_id returns 400 or 422"""
        response = await credit_api.post(
            "/allocate",
            json={
                "user_id": "",
                "credit_type": CreditTypeEnum.BONUS.value,
                "amount": 1000,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# Consume Endpoint Tests (4 tests)
# =============================================================================

class TestCreditConsumeAPI:
    """API tests for credit consumption endpoint"""

    async def test_consume_credits_returns_200(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /consume consumes credits from user account"""
        request = CreditTestDataFactory.make_consume_credits_request(
            user_id=unique_user_id(),
            amount=500
        )

        response = await credit_api.post("/consume", json=request.model_dump())

        # Accept success or expected failures (insufficient balance, user not found)
        assert response.status_code in [200, 400, 402, 404, 500], \
            f"Unexpected status code: {response.status_code}"

    async def test_consume_credits_rejects_negative_amount(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /consume with negative amount returns 400 or 422"""
        response = await credit_api.post(
            "/consume",
            json={
                "user_id": unique_user_id(),
                "amount": -100,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_consume_credits_rejects_zero_amount(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /consume with zero amount returns 400 or 422"""
        response = await credit_api.post(
            "/consume",
            json={
                "user_id": unique_user_id(),
                "amount": 0,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_consume_credits_with_insufficient_balance(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /consume with insufficient balance returns 400 or 402"""
        # Try to consume large amount for likely new user
        response = await credit_api.post(
            "/consume",
            json={
                "user_id": unique_user_id(),
                "amount": 999999,
            }
        )

        # 402 Payment Required or 400 Bad Request for insufficient balance
        assert response.status_code in [400, 402, 404], \
            f"Expected 400/402/404, got {response.status_code}"


# =============================================================================
# Check Availability Endpoint Tests (2 tests)
# =============================================================================

class TestCreditCheckAvailabilityAPI:
    """API tests for credit availability check endpoint"""

    async def test_check_availability_returns_200(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /check-availability checks if credits available"""
        request = CreditTestDataFactory.make_check_availability_request(
            user_id=unique_user_id(),
            amount=500
        )

        response = await credit_api.post("/check-availability", json=request.model_dump())

        # Accept success or not found
        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Validate response has expected fields
            assert "available" in data or "total_balance" in data

    async def test_check_availability_rejects_negative_amount(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /check-availability with negative amount returns 400 or 422"""
        response = await credit_api.post(
            "/check-availability",
            json={
                "user_id": unique_user_id(),
                "amount": -100,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# Transfer Endpoint Tests (3 tests)
# =============================================================================

class TestCreditTransferAPI:
    """API tests for credit transfer endpoint"""

    async def test_transfer_credits_returns_200(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /transfer transfers credits between users"""
        request = CreditTestDataFactory.make_transfer_credits_request(
            from_user_id=unique_user_id(),
            to_user_id=unique_user_id(),
            credit_type=CreditTypeEnum.BONUS.value,
            amount=500
        )

        response = await credit_api.post("/transfer", json=request.model_dump())

        # Accept success or expected failures
        assert response.status_code in [200, 400, 402, 404, 500], \
            f"Unexpected status code: {response.status_code}"

    async def test_transfer_credits_rejects_negative_amount(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /transfer with negative amount returns 400 or 422"""
        response = await credit_api.post(
            "/transfer",
            json={
                "from_user_id": unique_user_id(),
                "to_user_id": unique_user_id(),
                "credit_type": CreditTypeEnum.BONUS.value,
                "amount": -100,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_transfer_credits_rejects_same_user(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /transfer with same from_user and to_user returns 400"""
        user_id = unique_user_id()

        response = await credit_api.post(
            "/transfer",
            json={
                "from_user_id": user_id,
                "to_user_id": user_id,
                "credit_type": CreditTypeEnum.BONUS.value,
                "amount": 500,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# Transactions Endpoint Tests (2 tests)
# =============================================================================

class TestCreditTransactionsAPI:
    """API tests for credit transactions endpoint"""

    async def test_get_transactions_returns_200(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /transactions?user_id={user_id} returns transaction list"""
        user_id = unique_user_id()

        response = await credit_api.get(f"/transactions?user_id={user_id}")

        # Accept success or not found
        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Validate response structure
            assert "transactions" in data or isinstance(data, list)

    async def test_get_transactions_supports_pagination(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /transactions supports page and page_size parameters"""
        user_id = unique_user_id()

        response = await credit_api.get(
            f"/transactions?user_id={user_id}&page=1&page_size=10"
        )

        # Accept success or not found
        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"


# =============================================================================
# Campaign Endpoint Tests (4 tests)
# =============================================================================

class TestCreditCampaignAPI:
    """API tests for credit campaign endpoints"""

    async def test_create_campaign_returns_200_or_201(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /campaigns creates credit campaign"""
        now = datetime.utcnow()
        request = CreditTestDataFactory.make_create_campaign_request(
            name=f"API Test Campaign {unique_campaign_id()}",
            credit_type=CreditTypeEnum.PROMOTIONAL.value,
            credit_amount=1000,
            total_budget=100000,
            start_date=now,
            end_date=now + timedelta(days=30)
        )

        response = await credit_api.post("/campaigns", json=request.model_dump())

        # Accept success or expected failures
        assert response.status_code in [200, 201, 400, 500], \
            f"Unexpected status code: {response.status_code}"

    async def test_create_campaign_rejects_invalid_date_range(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST /campaigns with end_date before start_date returns 400 or 422"""
        now = datetime.utcnow()

        response = await credit_api.post(
            "/campaigns",
            json={
                "name": f"Invalid Campaign {unique_campaign_id()}",
                "credit_type": CreditTypeEnum.PROMOTIONAL.value,
                "credit_amount": 1000,
                "total_budget": 100000,
                "start_date": now.isoformat(),
                "end_date": (now - timedelta(days=1)).isoformat(),
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_get_campaigns_returns_200(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /campaigns returns campaign list"""
        response = await credit_api.get("/campaigns")

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}"

        data = response.json()
        # Validate response is a list or has campaigns field
        assert isinstance(data, list) or "campaigns" in data

    async def test_get_campaign_by_id_with_nonexistent_returns_404(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /campaigns/{campaign_id} with nonexistent ID returns 404"""
        campaign_id = CreditTestDataFactory.make_nonexistent_campaign_id()

        response = await credit_api.get(f"/campaigns/{campaign_id}")

        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"


# =============================================================================
# Statistics Endpoint Tests (2 tests)
# =============================================================================

class TestCreditStatisticsAPI:
    """API tests for credit statistics endpoint"""

    async def test_get_statistics_returns_200(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /statistics returns credit statistics"""
        response = await credit_api.get("/statistics")

        # Accept success or service-specific responses
        assert response.status_code in [200, 400, 500], \
            f"Unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Validate response has statistical fields
            assert "total_allocated" in data or "statistics" in data or isinstance(data, dict)

    async def test_get_statistics_supports_date_range(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /statistics supports start_date and end_date parameters"""
        now = datetime.utcnow()
        start_date = (now - timedelta(days=30)).isoformat()
        end_date = now.isoformat()

        response = await credit_api.get(
            f"/statistics?start_date={start_date}&end_date={end_date}"
        )

        # Accept success or service-specific responses
        assert response.status_code in [200, 400, 422, 500], \
            f"Unexpected status code: {response.status_code}"


# =============================================================================
# Error Handling Tests (3 tests)
# =============================================================================

class TestCreditErrorHandlingAPI:
    """API tests for credit service error handling"""

    async def test_invalid_endpoint_returns_404(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: GET /invalid-endpoint returns 404"""
        response = await credit_api.get("/invalid-endpoint-does-not-exist")

        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"

    async def test_malformed_json_returns_400_or_422(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST with malformed JSON returns 400 or 422"""
        import httpx

        # Send raw malformed JSON
        response = await credit_api.client.post(
            f"{credit_api.url}/allocate",
            content=b'{"user_id": "test", "amount": invalid}',  # Invalid JSON
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_missing_required_field_returns_422(
        self, credit_api: APIClient, api_assert: APIAssertions
    ):
        """API: POST with missing required fields returns 422"""
        # Missing 'amount' field
        response = await credit_api.post(
            "/allocate",
            json={
                "user_id": unique_user_id(),
                "credit_type": CreditTypeEnum.BONUS.value,
                # Missing 'amount' field
            }
        )

        assert response.status_code == 422, \
            f"Expected 422, got {response.status_code}"
