"""
Subscription Service — Component Tests for Admin Endpoints (#195)

Tests for:
- GET /api/v1/subscriptions/admin/all — list all subscriptions (admin)
- PUT /api/v1/subscriptions/admin/{subscription_id}/tier — force tier change
- POST /api/v1/subscriptions/admin/{subscription_id}/credits — credit adjustment

All tests use mocked dependencies via dependency injection overrides.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

pytestmark = [pytest.mark.component, pytest.mark.asyncio]

# Lazy imports to avoid import-time side effects
ADMIN_HEADERS = {"X-Admin-Role": "true", "X-Admin-User-Id": "admin_test_001"}
NON_ADMIN_HEADERS = {}


def _make_mock_subscription(
    subscription_id="sub_001",
    user_id="user_001",
    tier_code="pro",
    status="active",
    credits_remaining=5000,
    credits_allocated=10000,
):
    """Create a mock subscription object."""
    from microservices.subscription_service.models import (
        UserSubscription,
        SubscriptionStatus,
        BillingCycle,
    )

    now = datetime.now(timezone.utc)
    return UserSubscription(
        subscription_id=subscription_id,
        user_id=user_id,
        tier_id=tier_code,
        tier_code=tier_code,
        status=SubscriptionStatus(status),
        billing_cycle=BillingCycle.MONTHLY,
        credits_allocated=credits_allocated,
        credits_used=credits_allocated - credits_remaining,
        credits_remaining=credits_remaining,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )


@pytest.fixture
def mock_subscription_service():
    """Create a mock subscription service with mocked repository."""
    service = MagicMock()
    service.repository = MagicMock()
    service._get_tier_info = MagicMock()
    service.event_bus = None
    return service


@pytest.fixture
async def client(mock_subscription_service):
    """Create an async test client with dependency overrides."""
    from microservices.subscription_service.main import app, get_subscription_service

    app.dependency_overrides[get_subscription_service] = lambda: mock_subscription_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestAdminListAllSubscriptions:
    """Tests for GET /api/v1/subscriptions/admin/all"""

    async def test_returns_403_without_admin_header(self, client):
        """Non-admin requests are rejected with 403"""
        response = await client.get(
            "/api/v1/subscriptions/admin/all",
            headers=NON_ADMIN_HEADERS,
        )
        assert response.status_code == 403

    async def test_returns_subscriptions_with_admin_header(
        self, client, mock_subscription_service
    ):
        """Admin can list all subscriptions"""
        sub = _make_mock_subscription()
        mock_subscription_service.repository.get_subscriptions = AsyncMock(
            return_value=[sub]
        )

        response = await client.get(
            "/api/v1/subscriptions/admin/all",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["subscriptions"]) == 1

    async def test_filters_by_tier_code(self, client, mock_subscription_service):
        """Admin can filter subscriptions by tier"""
        mock_subscription_service.repository.get_subscriptions = AsyncMock(
            return_value=[]
        )

        response = await client.get(
            "/api/v1/subscriptions/admin/all?tier_code=pro",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        mock_subscription_service.repository.get_subscriptions.assert_called_once()
        call_kwargs = mock_subscription_service.repository.get_subscriptions.call_args
        assert call_kwargs.kwargs.get("tier_code") == "pro" or call_kwargs[1].get("tier_code") == "pro"

    async def test_filters_by_status(self, client, mock_subscription_service):
        """Admin can filter subscriptions by status"""
        mock_subscription_service.repository.get_subscriptions = AsyncMock(
            return_value=[]
        )

        response = await client.get(
            "/api/v1/subscriptions/admin/all?status=active",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200


class TestAdminForceTierChange:
    """Tests for PUT /api/v1/subscriptions/admin/{subscription_id}/tier"""

    async def test_returns_403_without_admin_header(self, client):
        """Non-admin requests are rejected with 403"""
        response = await client.put(
            "/api/v1/subscriptions/admin/sub_001/tier?new_tier_code=max",
            headers=NON_ADMIN_HEADERS,
        )
        assert response.status_code == 403

    async def test_changes_tier_successfully(self, client, mock_subscription_service):
        """Admin can force-change subscription tier"""
        sub = _make_mock_subscription(tier_code="pro")
        mock_subscription_service.repository.get_subscription = AsyncMock(
            return_value=sub
        )
        mock_subscription_service._get_tier_info.return_value = {
            "tier_id": "max",
            "tier_code": "max",
            "credits_monthly": 50000,
        }
        mock_subscription_service.repository.update_subscription = AsyncMock(
            return_value=sub
        )
        mock_subscription_service.repository.add_history = AsyncMock()

        response = await client.put(
            "/api/v1/subscriptions/admin/sub_001/tier?new_tier_code=max",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["previous_tier"] == "pro"
        assert data["new_tier"] == "max"

    async def test_returns_404_for_missing_subscription(
        self, client, mock_subscription_service
    ):
        """Returns 404 when subscription not found"""
        mock_subscription_service.repository.get_subscription = AsyncMock(
            return_value=None
        )

        response = await client.put(
            "/api/v1/subscriptions/admin/sub_nonexistent/tier?new_tier_code=max",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 404

    async def test_returns_400_for_invalid_tier(
        self, client, mock_subscription_service
    ):
        """Returns 400 when target tier does not exist"""
        from microservices.subscription_service.protocols import TierNotFoundError

        sub = _make_mock_subscription()
        mock_subscription_service.repository.get_subscription = AsyncMock(
            return_value=sub
        )
        mock_subscription_service._get_tier_info.side_effect = TierNotFoundError(
            "Tier 'invalid' not found"
        )

        response = await client.put(
            "/api/v1/subscriptions/admin/sub_001/tier?new_tier_code=invalid",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 400


class TestAdminCreditAdjustment:
    """Tests for POST /api/v1/subscriptions/admin/{subscription_id}/credits"""

    async def test_returns_403_without_admin_header(self, client):
        """Non-admin requests are rejected with 403"""
        response = await client.post(
            "/api/v1/subscriptions/admin/sub_001/credits?credits=100&reason=test",
            headers=NON_ADMIN_HEADERS,
        )
        assert response.status_code == 403

    async def test_adds_credits_successfully(self, client, mock_subscription_service):
        """Admin can add credits to a subscription"""
        sub = _make_mock_subscription(credits_remaining=5000, credits_allocated=10000)
        mock_subscription_service.repository.get_subscription = AsyncMock(
            return_value=sub
        )
        mock_subscription_service.repository.update_subscription = AsyncMock()
        mock_subscription_service.repository.add_history = AsyncMock()

        response = await client.post(
            "/api/v1/subscriptions/admin/sub_001/credits?credits=1000&reason=promotional+bonus",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_credits"] == 6000
        assert data["adjustment"] == 1000

    async def test_subtracts_credits_successfully(
        self, client, mock_subscription_service
    ):
        """Admin can subtract credits from a subscription"""
        sub = _make_mock_subscription(credits_remaining=5000)
        mock_subscription_service.repository.get_subscription = AsyncMock(
            return_value=sub
        )
        mock_subscription_service.repository.update_subscription = AsyncMock()
        mock_subscription_service.repository.add_history = AsyncMock()

        response = await client.post(
            "/api/v1/subscriptions/admin/sub_001/credits?credits=-2000&reason=abuse+correction",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_credits"] == 3000

    async def test_credits_cannot_go_below_zero(
        self, client, mock_subscription_service
    ):
        """Credit subtraction floors at zero"""
        sub = _make_mock_subscription(credits_remaining=100)
        mock_subscription_service.repository.get_subscription = AsyncMock(
            return_value=sub
        )
        mock_subscription_service.repository.update_subscription = AsyncMock()
        mock_subscription_service.repository.add_history = AsyncMock()

        response = await client.post(
            "/api/v1/subscriptions/admin/sub_001/credits?credits=-500&reason=correction",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_credits"] == 0

    async def test_returns_404_for_missing_subscription(
        self, client, mock_subscription_service
    ):
        """Returns 404 when subscription not found"""
        mock_subscription_service.repository.get_subscription = AsyncMock(
            return_value=None
        )

        response = await client.post(
            "/api/v1/subscriptions/admin/sub_nonexistent/credits?credits=100&reason=test",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 404
