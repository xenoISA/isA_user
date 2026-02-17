"""
Subscription Service - Component Tests (Golden)

Tests for:
- Service layer with mocked dependencies
- Subscription lifecycle operations
- Credit consumption logic
- Business rule validation
- Event publishing

All tests use SubscriptionTestDataFactory - zero hardcoded data.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

# Import mocks
from .mocks import MockSubscriptionRepository, MockEventBus, SubscriptionTestDataFactory

# Import service and models
from microservices.subscription_service.subscription_service import SubscriptionService
from microservices.subscription_service.models import (
    CreateSubscriptionRequest,
    CancelSubscriptionRequest,
    ConsumeCreditsRequest,
    SubscriptionStatus,
    BillingCycle,
)
from microservices.subscription_service.protocols import (
    TierNotFoundError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_repository():
    """Create mock repository"""
    return MockSubscriptionRepository()


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    return MockEventBus()


@pytest.fixture
async def subscription_service(mock_repository, mock_event_bus):
    """Create subscription service with mocked dependencies"""
    service = SubscriptionService(
        repository=mock_repository,
        event_bus=mock_event_bus,
    )
    await service.initialize()
    return service


# ============================================================================
# Test: Subscription Creation
# ============================================================================

class TestSubscriptionCreation:
    """Test subscription creation business logic"""

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, subscription_service, mock_event_bus):
        """Successful subscription creation returns subscription with credits"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="pro",
            billing_cycle=BillingCycle.MONTHLY
        )

        # Act
        result = await subscription_service.create_subscription(request)

        # Assert
        assert result.success is True
        assert result.subscription is not None
        assert result.subscription.user_id == user_id
        assert result.subscription.tier_code == "pro"
        assert result.credits_allocated == 30000000  # Pro tier monthly

    @pytest.mark.asyncio
    async def test_create_subscription_with_trial(self, subscription_service):
        """Subscription with trial sets correct status and dates"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="pro",
            billing_cycle=BillingCycle.MONTHLY,
            use_trial=True
        )

        # Act
        result = await subscription_service.create_subscription(request)

        # Assert
        assert result.success is True
        assert result.subscription.status == SubscriptionStatus.TRIALING
        assert result.subscription.is_trial is True
        assert result.subscription.trial_end is not None

    @pytest.mark.asyncio
    async def test_create_subscription_yearly_discount(self, subscription_service):
        """Yearly billing gets 20% discount"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="pro",
            billing_cycle=BillingCycle.YEARLY
        )

        # Act
        result = await subscription_service.create_subscription(request)

        # Assert
        assert result.success is True
        # Pro: $20 * 12 * 0.8 = $192
        expected_price = Decimal("20") * 12 * Decimal("0.8")
        assert result.subscription.price_paid == expected_price
        # Credits: 30M * 12
        assert result.credits_allocated == 30000000 * 12

    @pytest.mark.asyncio
    async def test_create_subscription_quarterly_discount(self, subscription_service):
        """Quarterly billing gets 10% discount"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="pro",
            billing_cycle=BillingCycle.QUARTERLY
        )

        # Act
        result = await subscription_service.create_subscription(request)

        # Assert
        assert result.success is True
        # Pro: $20 * 3 * 0.9 = $54
        expected_price = Decimal("20") * 3 * Decimal("0.9")
        assert result.subscription.price_paid == expected_price

    @pytest.mark.asyncio
    async def test_create_subscription_team_tier_seats(self, subscription_service):
        """Team tier multiplies credits by seats"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        org_id = SubscriptionTestDataFactory.make_organization_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            organization_id=org_id,
            tier_code="team",
            billing_cycle=BillingCycle.MONTHLY,
            seats=5
        )

        # Act
        result = await subscription_service.create_subscription(request)

        # Assert
        assert result.success is True
        # Team: 50M credits per seat * 5 seats = 250M
        assert result.credits_allocated == 50000000 * 5

    @pytest.mark.asyncio
    async def test_create_subscription_free_tier(self, subscription_service):
        """Free tier gives 1M credits with no charge"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="free",
            billing_cycle=BillingCycle.MONTHLY
        )

        # Act
        result = await subscription_service.create_subscription(request)

        # Assert
        assert result.success is True
        assert result.subscription.price_paid == Decimal("0")
        assert result.credits_allocated == 1000000

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_tier(self, subscription_service):
        """Invalid tier code returns error"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="invalid_tier",
            billing_cycle=BillingCycle.MONTHLY
        )

        # Act
        result = await subscription_service.create_subscription(request)

        # Assert
        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_create_subscription_duplicate_blocked(self, subscription_service, mock_repository):
        """Cannot create duplicate active subscription for same user"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        existing_sub = SubscriptionTestDataFactory.make_active_subscription_data(user_id=user_id)
        mock_repository.add_subscription(existing_sub)

        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="pro",
            billing_cycle=BillingCycle.MONTHLY
        )

        # Act
        result = await subscription_service.create_subscription(request)

        # Assert
        assert result.success is False
        assert "already has an active subscription" in result.message

    @pytest.mark.asyncio
    async def test_create_subscription_publishes_event(self, subscription_service, mock_event_bus):
        """Subscription creation publishes subscription.created event"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="pro",
            billing_cycle=BillingCycle.MONTHLY
        )

        # Act
        await subscription_service.create_subscription(request)

        # Assert
        assert len(mock_event_bus.published_events) > 0


# ============================================================================
# Test: Credit Consumption
# ============================================================================

class TestCreditConsumption:
    """Test credit consumption business logic"""

    @pytest.mark.asyncio
    async def test_consume_credits_success(self, subscription_service, mock_repository):
        """Successful credit consumption deducts from balance"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(
            user_id=user_id,
            credits=30000000
        )
        mock_repository.add_subscription(sub_data)

        request = ConsumeCreditsRequest(
            user_id=user_id,
            credits_to_consume=5000,
            service_type="model_inference"
        )

        # Act
        result = await subscription_service.consume_credits(request)

        # Assert
        assert result.success is True
        assert result.credits_consumed == 5000
        assert result.credits_remaining == 30000000 - 5000

    @pytest.mark.asyncio
    async def test_consume_credits_insufficient(self, subscription_service, mock_repository):
        """Insufficient credits returns error"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(
            user_id=user_id,
            credits=1000
        )
        mock_repository.add_subscription(sub_data)

        request = ConsumeCreditsRequest(
            user_id=user_id,
            credits_to_consume=5000,
            service_type="model_inference"
        )

        # Act
        result = await subscription_service.consume_credits(request)

        # Assert
        assert result.success is False
        assert "Insufficient credits" in result.message

    @pytest.mark.asyncio
    async def test_consume_credits_no_subscription(self, subscription_service):
        """No active subscription returns error"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = ConsumeCreditsRequest(
            user_id=user_id,
            credits_to_consume=5000,
            service_type="model_inference"
        )

        # Act
        result = await subscription_service.consume_credits(request)

        # Assert
        assert result.success is False
        assert "No active subscription" in result.message

    @pytest.mark.asyncio
    async def test_consume_credits_publishes_event(self, subscription_service, mock_repository, mock_event_bus):
        """Credit consumption publishes event"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(
            user_id=user_id,
            credits=30000000
        )
        mock_repository.add_subscription(sub_data)

        request = ConsumeCreditsRequest(
            user_id=user_id,
            credits_to_consume=5000,
            service_type="model_inference"
        )

        # Act
        await subscription_service.consume_credits(request)

        # Assert
        assert len(mock_event_bus.published_events) > 0

    @pytest.mark.asyncio
    async def test_consume_credits_updates_balance(self, subscription_service, mock_repository):
        """Credit consumption updates remaining balance correctly"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        initial_credits = 30000000
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(
            user_id=user_id,
            credits=initial_credits
        )
        mock_repository.add_subscription(sub_data)

        # Act - consume multiple times
        for _ in range(3):
            request = ConsumeCreditsRequest(
                user_id=user_id,
                credits_to_consume=1000,
                service_type="model_inference"
            )
            result = await subscription_service.consume_credits(request)

        # Assert
        assert result.credits_remaining == initial_credits - 3000


# ============================================================================
# Test: Subscription Cancellation
# ============================================================================

class TestSubscriptionCancellation:
    """Test subscription cancellation business logic"""

    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(self, subscription_service, mock_repository):
        """Cancel at period end sets flag and effective date"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(user_id=user_id)
        sub_id = sub_data["subscription_id"]
        mock_repository.add_subscription(sub_data)

        request = CancelSubscriptionRequest(
            immediate=False,
            reason="Too expensive"
        )

        # Act
        result = await subscription_service.cancel_subscription(sub_id, request, user_id)

        # Assert
        assert result.success is True
        assert "period end" in result.message.lower()
        assert result.effective_date is not None
        assert result.canceled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediate(self, subscription_service, mock_repository):
        """Immediate cancellation sets status to canceled"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(user_id=user_id)
        sub_id = sub_data["subscription_id"]
        mock_repository.add_subscription(sub_data)

        request = CancelSubscriptionRequest(
            immediate=True,
            reason="No longer needed"
        )

        # Act
        result = await subscription_service.cancel_subscription(sub_id, request, user_id)

        # Assert
        assert result.success is True
        assert result.canceled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_subscription_not_owner(self, subscription_service, mock_repository):
        """Cannot cancel subscription owned by another user"""
        # Arrange
        owner_id = SubscriptionTestDataFactory.make_user_id()
        other_user = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(user_id=owner_id)
        sub_id = sub_data["subscription_id"]
        mock_repository.add_subscription(sub_data)

        request = CancelSubscriptionRequest(immediate=False)

        # Act
        result = await subscription_service.cancel_subscription(sub_id, request, other_user)

        # Assert
        assert result.success is False
        assert "Not authorized" in result.message

    @pytest.mark.asyncio
    async def test_cancel_subscription_not_found(self, subscription_service):
        """Cancel non-existent subscription returns error"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CancelSubscriptionRequest(immediate=False)

        # Act
        result = await subscription_service.cancel_subscription(
            "sub_nonexistent",
            request,
            user_id
        )

        # Assert
        assert result.success is False


# ============================================================================
# Test: Credit Balance
# ============================================================================

class TestCreditBalance:
    """Test credit balance retrieval"""

    @pytest.mark.asyncio
    async def test_get_credit_balance_with_subscription(self, subscription_service, mock_repository):
        """Get balance returns subscription credit info"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(
            user_id=user_id,
            credits=30000000
        )
        mock_repository.add_subscription(sub_data)

        # Act
        result = await subscription_service.get_credit_balance(user_id)

        # Assert
        assert result.success is True
        assert result.subscription_credits_remaining == 30000000
        assert result.tier_code == "pro"

    @pytest.mark.asyncio
    async def test_get_credit_balance_no_subscription(self, subscription_service):
        """Get balance without subscription returns zero"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()

        # Act
        result = await subscription_service.get_credit_balance(user_id)

        # Assert
        assert result.success is True
        assert result.subscription_credits_remaining == 0
        assert result.total_credits_available == 0

    @pytest.mark.asyncio
    async def test_get_credit_balance_with_org(self, subscription_service, mock_repository):
        """Get balance respects organization context"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        org_id = SubscriptionTestDataFactory.make_organization_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(user_id=user_id)
        sub_data["organization_id"] = org_id
        mock_repository.add_subscription(sub_data)

        # Act - query without org_id should not find it
        result = await subscription_service.get_credit_balance(user_id)

        # Assert
        assert result.subscription_credits_remaining == 0


# ============================================================================
# Test: Subscription Retrieval
# ============================================================================

class TestSubscriptionRetrieval:
    """Test subscription retrieval operations"""

    @pytest.mark.asyncio
    async def test_get_subscription_by_id(self, subscription_service, mock_repository):
        """Get subscription by ID returns correct data"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(user_id=user_id)
        sub_id = sub_data["subscription_id"]
        mock_repository.add_subscription(sub_data)

        # Act
        result = await subscription_service.get_subscription(sub_id)

        # Assert
        assert result.success is True
        assert result.subscription.subscription_id == sub_id

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(self, subscription_service):
        """Get non-existent subscription returns not found"""
        # Arrange
        sub_id = SubscriptionTestDataFactory.make_subscription_id()

        # Act
        result = await subscription_service.get_subscription(sub_id)

        # Assert
        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_get_user_subscription(self, subscription_service, mock_repository):
        """Get user subscription returns active subscription"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(user_id=user_id)
        mock_repository.add_subscription(sub_data)

        # Act
        result = await subscription_service.get_user_subscription(user_id)

        # Assert
        assert result.success is True
        assert result.subscription.user_id == user_id

    @pytest.mark.asyncio
    async def test_get_subscriptions_filtered(self, subscription_service, mock_repository):
        """Get subscriptions with filters returns matching results"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        for _ in range(3):
            sub_data = SubscriptionTestDataFactory.make_active_subscription_data()
            mock_repository.add_subscription(sub_data)

        target_sub = SubscriptionTestDataFactory.make_active_subscription_data(user_id=user_id)
        mock_repository.add_subscription(target_sub)

        # Act
        result = await subscription_service.get_subscriptions(user_id=user_id)

        # Assert
        assert result.success is True
        assert len(result.subscriptions) == 1
        assert result.subscriptions[0].user_id == user_id


# ============================================================================
# Test: Subscription History
# ============================================================================

class TestSubscriptionHistory:
    """Test subscription history retrieval"""

    @pytest.mark.asyncio
    async def test_get_subscription_history(self, subscription_service, mock_repository):
        """Get history returns recorded entries"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="pro",
            billing_cycle=BillingCycle.MONTHLY
        )
        create_result = await subscription_service.create_subscription(request)
        sub_id = create_result.subscription.subscription_id

        # Act
        result = await subscription_service.get_subscription_history(sub_id)

        # Assert
        assert result.success is True
        assert len(result.history) >= 1

    @pytest.mark.asyncio
    async def test_get_history_pagination(self, subscription_service, mock_repository):
        """Get history supports pagination"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        request = CreateSubscriptionRequest(
            user_id=user_id,
            tier_code="pro",
            billing_cycle=BillingCycle.MONTHLY
        )
        create_result = await subscription_service.create_subscription(request)
        sub_id = create_result.subscription.subscription_id

        # Act
        result = await subscription_service.get_subscription_history(
            sub_id,
            page=1,
            page_size=10
        )

        # Assert
        assert result.success is True


# ============================================================================
# Test: Tier Validation
# ============================================================================

class TestTierValidation:
    """Test tier validation logic"""

    @pytest.mark.asyncio
    async def test_valid_free_tier(self, subscription_service):
        """Free tier is valid"""
        tier = subscription_service._get_tier_info("free")
        assert tier["tier_code"] == "free"
        assert tier["monthly_credits"] == 1000000

    @pytest.mark.asyncio
    async def test_valid_pro_tier(self, subscription_service):
        """Pro tier is valid"""
        tier = subscription_service._get_tier_info("pro")
        assert tier["tier_code"] == "pro"
        assert tier["monthly_credits"] == 30000000

    @pytest.mark.asyncio
    async def test_valid_max_tier(self, subscription_service):
        """Max tier is valid"""
        tier = subscription_service._get_tier_info("max")
        assert tier["tier_code"] == "max"
        assert tier["monthly_credits"] == 100000000

    @pytest.mark.asyncio
    async def test_invalid_tier_raises_error(self, subscription_service):
        """Invalid tier raises TierNotFoundError"""
        with pytest.raises(TierNotFoundError):
            subscription_service._get_tier_info("invalid_tier")

    @pytest.mark.asyncio
    async def test_tier_case_insensitive(self, subscription_service):
        """Tier lookup is case insensitive"""
        tier = subscription_service._get_tier_info("PRO")
        assert tier["tier_code"] == "pro"


# ============================================================================
# Test: Health Check
# ============================================================================

class TestHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check(self, subscription_service):
        """Health check returns healthy status"""
        result = await subscription_service.health_check()

        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "tiers_loaded" in result


# ============================================================================
# Test: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_consume_exact_remaining_credits(self, subscription_service, mock_repository):
        """Consuming exactly remaining credits succeeds"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(
            user_id=user_id,
            credits=5000
        )
        mock_repository.add_subscription(sub_data)

        request = ConsumeCreditsRequest(
            user_id=user_id,
            credits_to_consume=5000,
            service_type="model_inference"
        )

        # Act
        result = await subscription_service.consume_credits(request)

        # Assert
        assert result.success is True
        assert result.credits_remaining == 0

    @pytest.mark.asyncio
    async def test_consume_one_credit_over_balance(self, subscription_service, mock_repository):
        """Consuming one credit over balance fails"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(
            user_id=user_id,
            credits=5000
        )
        mock_repository.add_subscription(sub_data)

        request = ConsumeCreditsRequest(
            user_id=user_id,
            credits_to_consume=5001,
            service_type="model_inference"
        )

        # Act
        result = await subscription_service.consume_credits(request)

        # Assert
        assert result.success is False

    @pytest.mark.asyncio
    async def test_minimum_credit_consumption(self, subscription_service, mock_repository):
        """Minimum consumption of 1 credit works"""
        # Arrange
        user_id = SubscriptionTestDataFactory.make_user_id()
        sub_data = SubscriptionTestDataFactory.make_active_subscription_data(
            user_id=user_id,
            credits=30000000
        )
        mock_repository.add_subscription(sub_data)

        request = ConsumeCreditsRequest(
            user_id=user_id,
            credits_to_consume=1,
            service_type="model_inference"
        )

        # Act
        result = await subscription_service.consume_credits(request)

        # Assert
        assert result.success is True
        assert result.credits_consumed == 1
