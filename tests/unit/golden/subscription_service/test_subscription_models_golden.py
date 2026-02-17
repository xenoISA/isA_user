"""
Unit Golden Tests: Subscription Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import ValidationError

from microservices.subscription_service.models import (
    # Enums
    SubscriptionStatus,
    BillingCycle,
    SubscriptionAction,
    InitiatedBy,
    # Core Models
    UserSubscription,
    SubscriptionHistory,
    # Request Models
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    CancelSubscriptionRequest,
    ConsumeCreditsRequest,
    # Response Models
    CreateSubscriptionResponse,
    CancelSubscriptionResponse,
    ConsumeCreditsResponse,
    CreditBalanceResponse,
    SubscriptionResponse,
    SubscriptionListResponse,
    SubscriptionHistoryResponse,
    SubscriptionStatsResponse,
    # Service Models
    HealthResponse,
    SubscriptionServiceInfo,
    ErrorResponse,
)


# ====================
# Enum Tests
# ====================

class TestSubscriptionStatus:
    """Test SubscriptionStatus enum"""

    def test_subscription_status_values(self):
        """Test all subscription status values are defined"""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.TRIALING.value == "trialing"
        assert SubscriptionStatus.PAST_DUE.value == "past_due"
        assert SubscriptionStatus.CANCELED.value == "canceled"
        assert SubscriptionStatus.PAUSED.value == "paused"
        assert SubscriptionStatus.EXPIRED.value == "expired"
        assert SubscriptionStatus.INCOMPLETE.value == "incomplete"

    def test_subscription_status_comparison(self):
        """Test subscription status comparison"""
        assert SubscriptionStatus.ACTIVE != SubscriptionStatus.CANCELED
        assert SubscriptionStatus.ACTIVE.value == "active"


class TestBillingCycle:
    """Test BillingCycle enum"""

    def test_billing_cycle_values(self):
        """Test all billing cycle values"""
        assert BillingCycle.MONTHLY.value == "monthly"
        assert BillingCycle.YEARLY.value == "yearly"
        assert BillingCycle.QUARTERLY.value == "quarterly"

    def test_billing_cycle_comparison(self):
        """Test billing cycle comparison"""
        assert BillingCycle.MONTHLY != BillingCycle.YEARLY
        assert BillingCycle.YEARLY.value == "yearly"


class TestSubscriptionAction:
    """Test SubscriptionAction enum"""

    def test_subscription_action_values(self):
        """Test all subscription action values"""
        assert SubscriptionAction.CREATED.value == "created"
        assert SubscriptionAction.UPGRADED.value == "upgraded"
        assert SubscriptionAction.DOWNGRADED.value == "downgraded"
        assert SubscriptionAction.RENEWED.value == "renewed"
        assert SubscriptionAction.CANCELED.value == "canceled"
        assert SubscriptionAction.PAUSED.value == "paused"
        assert SubscriptionAction.RESUMED.value == "resumed"
        assert SubscriptionAction.EXPIRED.value == "expired"
        assert SubscriptionAction.CREDITS_ALLOCATED.value == "credits_allocated"
        assert SubscriptionAction.CREDITS_CONSUMED.value == "credits_consumed"
        assert SubscriptionAction.CREDITS_REFUNDED.value == "credits_refunded"
        assert SubscriptionAction.CREDITS_ROLLED_OVER.value == "credits_rolled_over"
        assert SubscriptionAction.TRIAL_STARTED.value == "trial_started"
        assert SubscriptionAction.TRIAL_ENDED.value == "trial_ended"
        assert SubscriptionAction.PAYMENT_FAILED.value == "payment_failed"
        assert SubscriptionAction.PAYMENT_SUCCEEDED.value == "payment_succeeded"

    def test_subscription_action_comparison(self):
        """Test subscription action comparison"""
        assert SubscriptionAction.CREATED != SubscriptionAction.CANCELED
        assert SubscriptionAction.UPGRADED.value == "upgraded"


class TestInitiatedBy:
    """Test InitiatedBy enum"""

    def test_initiated_by_values(self):
        """Test all initiated by values"""
        assert InitiatedBy.USER.value == "user"
        assert InitiatedBy.SYSTEM.value == "system"
        assert InitiatedBy.ADMIN.value == "admin"
        assert InitiatedBy.PAYMENT_PROVIDER.value == "payment_provider"

    def test_initiated_by_comparison(self):
        """Test initiated by comparison"""
        assert InitiatedBy.USER != InitiatedBy.SYSTEM
        assert InitiatedBy.ADMIN.value == "admin"


# ====================
# Core Model Tests
# ====================

class TestUserSubscription:
    """Test UserSubscription model validation"""

    def test_user_subscription_creation_with_all_fields(self):
        """Test creating user subscription with all fields"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        trial_end = now + timedelta(days=14)
        next_billing = now + timedelta(days=30)

        subscription = UserSubscription(
            id=1,
            subscription_id="sub_123456",
            user_id="user_789",
            organization_id="org_001",
            tier_id="tier_pro_001",
            tier_code="pro",
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            price_paid=Decimal("9.99"),
            currency="USD",
            credits_allocated=100000,
            credits_used=25000,
            credits_remaining=75000,
            credits_rolled_over=5000,
            current_period_start=now,
            current_period_end=period_end,
            trial_start=now,
            trial_end=trial_end,
            is_trial=True,
            seats_purchased=5,
            seats_used=3,
            cancel_at_period_end=False,
            canceled_at=None,
            cancellation_reason=None,
            payment_method_id="pm_card_123",
            external_subscription_id="stripe_sub_xyz",
            auto_renew=True,
            next_billing_date=next_billing,
            last_billing_date=now,
            metadata={"source": "web", "campaign": "summer2024"},
            created_at=now,
            updated_at=now,
        )

        assert subscription.subscription_id == "sub_123456"
        assert subscription.user_id == "user_789"
        assert subscription.organization_id == "org_001"
        assert subscription.tier_code == "pro"
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.billing_cycle == BillingCycle.MONTHLY
        assert subscription.price_paid == Decimal("9.99")
        assert subscription.currency == "USD"
        assert subscription.credits_allocated == 100000
        assert subscription.credits_used == 25000
        assert subscription.credits_remaining == 75000
        assert subscription.is_trial is True
        assert subscription.seats_purchased == 5
        assert subscription.auto_renew is True

    def test_user_subscription_with_minimal_fields(self):
        """Test creating user subscription with only required fields"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        subscription = UserSubscription(
            subscription_id="sub_minimal",
            user_id="user_123",
            tier_id="tier_free_001",
            tier_code="free",
            current_period_start=now,
            current_period_end=period_end,
        )

        assert subscription.subscription_id == "sub_minimal"
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.billing_cycle == BillingCycle.MONTHLY
        assert subscription.price_paid == Decimal("0")
        assert subscription.currency == "USD"
        assert subscription.credits_allocated == 0
        assert subscription.credits_used == 0
        assert subscription.credits_remaining == 0
        assert subscription.is_trial is False
        assert subscription.seats_purchased == 1
        assert subscription.seats_used == 1
        assert subscription.cancel_at_period_end is False
        assert subscription.auto_renew is True

    def test_user_subscription_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            UserSubscription(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "subscription_id" in missing_fields
        assert "tier_id" in missing_fields
        assert "tier_code" in missing_fields
        assert "current_period_start" in missing_fields
        assert "current_period_end" in missing_fields

    def test_user_subscription_credits_validation(self):
        """Test credits must be non-negative"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        # Valid: non-negative credits
        subscription = UserSubscription(
            subscription_id="sub_credits",
            user_id="user_123",
            tier_id="tier_pro_001",
            tier_code="pro",
            current_period_start=now,
            current_period_end=period_end,
            credits_allocated=0,
            credits_used=0,
            credits_remaining=0,
        )
        assert subscription.credits_allocated == 0

        # Invalid: negative credits
        with pytest.raises(ValidationError):
            UserSubscription(
                subscription_id="sub_invalid",
                user_id="user_123",
                tier_id="tier_pro_001",
                tier_code="pro",
                current_period_start=now,
                current_period_end=period_end,
                credits_allocated=-100,
            )

    def test_user_subscription_seats_validation(self):
        """Test seats must be at least 1"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        # Valid: 1 or more seats
        subscription = UserSubscription(
            subscription_id="sub_seats",
            user_id="user_123",
            tier_id="tier_team_001",
            tier_code="team",
            current_period_start=now,
            current_period_end=period_end,
            seats_purchased=10,
        )
        assert subscription.seats_purchased == 10

        # Invalid: 0 seats
        with pytest.raises(ValidationError):
            UserSubscription(
                subscription_id="sub_invalid",
                user_id="user_123",
                tier_id="tier_team_001",
                tier_code="team",
                current_period_start=now,
                current_period_end=period_end,
                seats_purchased=0,
            )

    def test_user_subscription_with_trial(self):
        """Test subscription with trial period"""
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=14)
        period_end = now + timedelta(days=30)

        subscription = UserSubscription(
            subscription_id="sub_trial",
            user_id="user_123",
            tier_id="tier_pro_001",
            tier_code="pro",
            status=SubscriptionStatus.TRIALING,
            current_period_start=now,
            current_period_end=period_end,
            trial_start=now,
            trial_end=trial_end,
            is_trial=True,
        )

        assert subscription.status == SubscriptionStatus.TRIALING
        assert subscription.is_trial is True
        assert subscription.trial_start == now
        assert subscription.trial_end == trial_end

    def test_user_subscription_with_cancellation(self):
        """Test subscription with cancellation"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        canceled_at = now

        subscription = UserSubscription(
            subscription_id="sub_canceled",
            user_id="user_123",
            tier_id="tier_pro_001",
            tier_code="pro",
            status=SubscriptionStatus.CANCELED,
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=True,
            canceled_at=canceled_at,
            cancellation_reason="Too expensive",
        )

        assert subscription.status == SubscriptionStatus.CANCELED
        assert subscription.cancel_at_period_end is True
        assert subscription.canceled_at == canceled_at
        assert subscription.cancellation_reason == "Too expensive"


class TestSubscriptionHistory:
    """Test SubscriptionHistory model validation"""

    def test_subscription_history_creation_with_all_fields(self):
        """Test creating subscription history with all fields"""
        now = datetime.now(timezone.utc)
        period_start = now
        period_end = now + timedelta(days=30)

        history = SubscriptionHistory(
            id=1,
            history_id="hist_123456",
            subscription_id="sub_789",
            user_id="user_001",
            organization_id="org_001",
            action=SubscriptionAction.UPGRADED,
            previous_tier_code="free",
            new_tier_code="pro",
            previous_status="active",
            new_status="active",
            credits_change=100000,
            credits_balance_after=100000,
            price_change=Decimal("9.99"),
            period_start=period_start,
            period_end=period_end,
            reason="User upgraded to Pro plan",
            initiated_by=InitiatedBy.USER,
            metadata={"source": "mobile_app", "version": "1.5.0"},
            created_at=now,
        )

        assert history.history_id == "hist_123456"
        assert history.subscription_id == "sub_789"
        assert history.user_id == "user_001"
        assert history.action == SubscriptionAction.UPGRADED
        assert history.previous_tier_code == "free"
        assert history.new_tier_code == "pro"
        assert history.credits_change == 100000
        assert history.credits_balance_after == 100000
        assert history.price_change == Decimal("9.99")
        assert history.initiated_by == InitiatedBy.USER

    def test_subscription_history_with_minimal_fields(self):
        """Test creating subscription history with only required fields"""
        history = SubscriptionHistory(
            history_id="hist_minimal",
            subscription_id="sub_123",
            user_id="user_456",
            action=SubscriptionAction.CREATED,
        )

        assert history.history_id == "hist_minimal"
        assert history.subscription_id == "sub_123"
        assert history.user_id == "user_456"
        assert history.action == SubscriptionAction.CREATED
        assert history.credits_change == 0
        assert history.price_change == Decimal("0")
        assert history.initiated_by == InitiatedBy.SYSTEM

    def test_subscription_history_credits_consumed(self):
        """Test subscription history for credits consumption"""
        history = SubscriptionHistory(
            history_id="hist_credits_consumed",
            subscription_id="sub_123",
            user_id="user_456",
            action=SubscriptionAction.CREDITS_CONSUMED,
            credits_change=-5000,
            credits_balance_after=95000,
            reason="AI model inference usage",
            metadata={"service": "model_inference", "tokens": 10000},
        )

        assert history.action == SubscriptionAction.CREDITS_CONSUMED
        assert history.credits_change == -5000
        assert history.credits_balance_after == 95000
        assert "model_inference" in history.metadata.get("service", "")

    def test_subscription_history_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            SubscriptionHistory(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "history_id" in missing_fields
        assert "subscription_id" in missing_fields
        assert "action" in missing_fields


# ====================
# Request Model Tests
# ====================

class TestCreateSubscriptionRequest:
    """Test CreateSubscriptionRequest model validation"""

    def test_create_subscription_request_valid(self):
        """Test valid subscription creation request"""
        request = CreateSubscriptionRequest(
            user_id="user_123",
            tier_code="pro",
            billing_cycle=BillingCycle.MONTHLY,
            seats=1,
        )

        assert request.user_id == "user_123"
        assert request.tier_code == "pro"
        assert request.billing_cycle == BillingCycle.MONTHLY
        assert request.seats == 1
        assert request.use_trial is False

    def test_create_subscription_request_with_trial(self):
        """Test subscription creation request with trial"""
        request = CreateSubscriptionRequest(
            user_id="user_123",
            organization_id="org_001",
            tier_code="max",
            billing_cycle=BillingCycle.YEARLY,
            payment_method_id="pm_card_123",
            seats=1,
            use_trial=True,
            promo_code="SUMMER2024",
            metadata={"source": "landing_page"},
        )

        assert request.user_id == "user_123"
        assert request.organization_id == "org_001"
        assert request.tier_code == "max"
        assert request.billing_cycle == BillingCycle.YEARLY
        assert request.use_trial is True
        assert request.promo_code == "SUMMER2024"
        assert request.metadata == {"source": "landing_page"}

    def test_create_subscription_request_team_seats(self):
        """Test team subscription with multiple seats"""
        request = CreateSubscriptionRequest(
            user_id="user_123",
            organization_id="org_team",
            tier_code="team",
            billing_cycle=BillingCycle.MONTHLY,
            seats=10,
        )

        assert request.tier_code == "team"
        assert request.seats == 10

    def test_create_subscription_request_defaults(self):
        """Test default values for optional fields"""
        request = CreateSubscriptionRequest(
            user_id="user_123",
            tier_code="free",
        )

        assert request.billing_cycle == BillingCycle.MONTHLY
        assert request.seats == 1
        assert request.use_trial is False
        assert request.promo_code is None
        assert request.metadata is None

    def test_create_subscription_request_invalid_seats(self):
        """Test that invalid seats raise ValidationError"""
        with pytest.raises(ValidationError):
            CreateSubscriptionRequest(
                user_id="user_123",
                tier_code="team",
                seats=0,
            )


class TestUpdateSubscriptionRequest:
    """Test UpdateSubscriptionRequest model validation"""

    def test_update_subscription_request_partial(self):
        """Test partial update request"""
        request = UpdateSubscriptionRequest(
            tier_code="max",
            auto_renew=False,
        )

        assert request.tier_code == "max"
        assert request.auto_renew is False
        assert request.billing_cycle is None
        assert request.seats is None

    def test_update_subscription_request_all_fields(self):
        """Test update request with all fields"""
        request = UpdateSubscriptionRequest(
            tier_code="enterprise",
            billing_cycle=BillingCycle.YEARLY,
            seats=50,
            auto_renew=True,
            payment_method_id="pm_new_card_456",
            metadata={"updated_by": "admin"},
        )

        assert request.tier_code == "enterprise"
        assert request.billing_cycle == BillingCycle.YEARLY
        assert request.seats == 50
        assert request.auto_renew is True
        assert request.payment_method_id == "pm_new_card_456"

    def test_update_subscription_request_change_billing_cycle(self):
        """Test changing billing cycle"""
        request = UpdateSubscriptionRequest(
            billing_cycle=BillingCycle.YEARLY,
        )

        assert request.billing_cycle == BillingCycle.YEARLY
        assert request.tier_code is None

    def test_update_subscription_request_invalid_seats(self):
        """Test that invalid seats raise ValidationError"""
        with pytest.raises(ValidationError):
            UpdateSubscriptionRequest(seats=0)


class TestCancelSubscriptionRequest:
    """Test CancelSubscriptionRequest model validation"""

    def test_cancel_subscription_request_immediate(self):
        """Test immediate cancellation request"""
        request = CancelSubscriptionRequest(
            immediate=True,
            reason="No longer needed",
            feedback="Found alternative solution",
        )

        assert request.immediate is True
        assert request.reason == "No longer needed"
        assert request.feedback == "Found alternative solution"

    def test_cancel_subscription_request_at_period_end(self):
        """Test cancellation at period end"""
        request = CancelSubscriptionRequest(
            immediate=False,
            reason="Too expensive",
        )

        assert request.immediate is False
        assert request.reason == "Too expensive"
        assert request.feedback is None

    def test_cancel_subscription_request_defaults(self):
        """Test default values"""
        request = CancelSubscriptionRequest()

        assert request.immediate is False
        assert request.reason is None
        assert request.feedback is None


class TestConsumeCreditsRequest:
    """Test ConsumeCreditsRequest model validation"""

    def test_consume_credits_request_valid(self):
        """Test valid credits consumption request"""
        request = ConsumeCreditsRequest(
            user_id="user_123",
            credits_to_consume=5000,
            service_type="model_inference",
            description="GPT-4 API call",
        )

        assert request.user_id == "user_123"
        assert request.credits_to_consume == 5000
        assert request.service_type == "model_inference"
        assert request.description == "GPT-4 API call"

    def test_consume_credits_request_with_organization(self):
        """Test credits consumption for organization"""
        request = ConsumeCreditsRequest(
            user_id="user_123",
            organization_id="org_001",
            credits_to_consume=10000,
            service_type="storage_minio",
            usage_record_id="usage_rec_456",
            metadata={"bucket": "photos", "size_mb": 1024},
        )

        assert request.user_id == "user_123"
        assert request.organization_id == "org_001"
        assert request.credits_to_consume == 10000
        assert request.service_type == "storage_minio"
        assert request.usage_record_id == "usage_rec_456"

    def test_consume_credits_request_invalid_amount(self):
        """Test that zero or negative credits raise ValidationError"""
        # Zero credits
        with pytest.raises(ValidationError):
            ConsumeCreditsRequest(
                user_id="user_123",
                credits_to_consume=0,
                service_type="model_inference",
            )

        # Negative credits
        with pytest.raises(ValidationError):
            ConsumeCreditsRequest(
                user_id="user_123",
                credits_to_consume=-100,
                service_type="model_inference",
            )

    def test_consume_credits_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ConsumeCreditsRequest(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "credits_to_consume" in missing_fields
        assert "service_type" in missing_fields


# ====================
# Response Model Tests
# ====================

class TestCreateSubscriptionResponse:
    """Test CreateSubscriptionResponse model"""

    def test_create_subscription_response_success(self):
        """Test successful subscription creation response"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        subscription = UserSubscription(
            subscription_id="sub_new_123",
            user_id="user_456",
            tier_id="tier_pro_001",
            tier_code="pro",
            current_period_start=now,
            current_period_end=period_end,
            credits_allocated=100000,
        )

        response = CreateSubscriptionResponse(
            success=True,
            message="Subscription created successfully",
            subscription=subscription,
            credits_allocated=100000,
            next_billing_date=period_end,
        )

        assert response.success is True
        assert response.message == "Subscription created successfully"
        assert response.subscription is not None
        assert response.subscription.subscription_id == "sub_new_123"
        assert response.credits_allocated == 100000

    def test_create_subscription_response_failure(self):
        """Test failed subscription creation response"""
        response = CreateSubscriptionResponse(
            success=False,
            message="Payment method invalid",
            subscription=None,
        )

        assert response.success is False
        assert "invalid" in response.message.lower()
        assert response.subscription is None
        assert response.credits_allocated is None


class TestCancelSubscriptionResponse:
    """Test CancelSubscriptionResponse model"""

    def test_cancel_subscription_response_immediate(self):
        """Test immediate cancellation response"""
        now = datetime.now(timezone.utc)

        response = CancelSubscriptionResponse(
            success=True,
            message="Subscription canceled immediately",
            canceled_at=now,
            effective_date=now,
            credits_remaining=50000,
        )

        assert response.success is True
        assert response.canceled_at == now
        assert response.effective_date == now
        assert response.credits_remaining == 50000

    def test_cancel_subscription_response_at_period_end(self):
        """Test cancellation at period end response"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=15)

        response = CancelSubscriptionResponse(
            success=True,
            message="Subscription will be canceled at period end",
            canceled_at=now,
            effective_date=period_end,
            credits_remaining=75000,
        )

        assert response.success is True
        assert response.canceled_at == now
        assert response.effective_date == period_end
        assert response.effective_date > response.canceled_at

    def test_cancel_subscription_response_failure(self):
        """Test failed cancellation response"""
        response = CancelSubscriptionResponse(
            success=False,
            message="Subscription not found",
        )

        assert response.success is False
        assert response.canceled_at is None
        assert response.effective_date is None


class TestConsumeCreditsResponse:
    """Test ConsumeCreditsResponse model"""

    def test_consume_credits_response_success(self):
        """Test successful credits consumption response"""
        response = ConsumeCreditsResponse(
            success=True,
            message="Credits consumed successfully",
            credits_consumed=5000,
            credits_remaining=95000,
            subscription_id="sub_123",
            consumed_from="subscription",
        )

        assert response.success is True
        assert response.credits_consumed == 5000
        assert response.credits_remaining == 95000
        assert response.subscription_id == "sub_123"
        assert response.consumed_from == "subscription"

    def test_consume_credits_response_insufficient_credits(self):
        """Test insufficient credits response"""
        response = ConsumeCreditsResponse(
            success=False,
            message="Insufficient credits",
            credits_consumed=0,
            credits_remaining=1000,
        )

        assert response.success is False
        assert response.credits_consumed == 0
        assert response.credits_remaining == 1000

    def test_consume_credits_response_defaults(self):
        """Test default values"""
        response = ConsumeCreditsResponse(
            success=True,
            message="Credits consumed",
        )

        assert response.credits_consumed == 0
        assert response.credits_remaining == 0
        assert response.subscription_id is None


class TestCreditBalanceResponse:
    """Test CreditBalanceResponse model"""

    def test_credit_balance_response_with_subscription(self):
        """Test credit balance response with active subscription"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=15)

        response = CreditBalanceResponse(
            success=True,
            message="Credit balance retrieved",
            user_id="user_123",
            organization_id="org_001",
            subscription_credits_remaining=75000,
            subscription_credits_total=100000,
            subscription_period_end=period_end,
            total_credits_available=75000,
            subscription_id="sub_123",
            tier_code="pro",
            tier_name="Pro Plan",
        )

        assert response.success is True
        assert response.user_id == "user_123"
        assert response.subscription_credits_remaining == 75000
        assert response.subscription_credits_total == 100000
        assert response.total_credits_available == 75000
        assert response.tier_code == "pro"

    def test_credit_balance_response_no_subscription(self):
        """Test credit balance response with no subscription"""
        response = CreditBalanceResponse(
            success=True,
            message="No active subscription",
            user_id="user_123",
            subscription_credits_remaining=0,
            subscription_credits_total=0,
            total_credits_available=0,
        )

        assert response.success is True
        assert response.subscription_credits_remaining == 0
        assert response.total_credits_available == 0
        assert response.subscription_id is None

    def test_credit_balance_response_defaults(self):
        """Test default values"""
        response = CreditBalanceResponse(
            success=True,
            message="Balance check",
            user_id="user_456",
        )

        assert response.subscription_credits_remaining == 0
        assert response.subscription_credits_total == 0
        assert response.total_credits_available == 0


class TestSubscriptionResponse:
    """Test SubscriptionResponse model"""

    def test_subscription_response_success(self):
        """Test successful subscription response"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        subscription = UserSubscription(
            subscription_id="sub_123",
            user_id="user_456",
            tier_id="tier_pro_001",
            tier_code="pro",
            current_period_start=now,
            current_period_end=period_end,
        )

        response = SubscriptionResponse(
            success=True,
            message="Subscription retrieved",
            subscription=subscription,
        )

        assert response.success is True
        assert response.subscription is not None
        assert response.subscription.subscription_id == "sub_123"

    def test_subscription_response_not_found(self):
        """Test subscription not found response"""
        response = SubscriptionResponse(
            success=False,
            message="Subscription not found",
            subscription=None,
        )

        assert response.success is False
        assert response.subscription is None


class TestSubscriptionListResponse:
    """Test SubscriptionListResponse model"""

    def test_subscription_list_response_with_data(self):
        """Test subscription list response with data"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        subscriptions = [
            UserSubscription(
                subscription_id=f"sub_{i}",
                user_id=f"user_{i}",
                tier_id=f"tier_pro_{i}",
                tier_code="pro",
                current_period_start=now,
                current_period_end=period_end,
            )
            for i in range(3)
        ]

        response = SubscriptionListResponse(
            success=True,
            message="Subscriptions retrieved",
            subscriptions=subscriptions,
            total=3,
            page=1,
            page_size=50,
        )

        assert response.success is True
        assert len(response.subscriptions) == 3
        assert response.total == 3
        assert response.page == 1
        assert response.page_size == 50

    def test_subscription_list_response_empty(self):
        """Test empty subscription list response"""
        response = SubscriptionListResponse(
            success=True,
            message="No subscriptions found",
            subscriptions=[],
            total=0,
        )

        assert response.success is True
        assert len(response.subscriptions) == 0
        assert response.total == 0

    def test_subscription_list_response_defaults(self):
        """Test default values"""
        response = SubscriptionListResponse(
            success=True,
            message="Subscriptions list",
        )

        assert response.subscriptions == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 50


class TestSubscriptionHistoryResponse:
    """Test SubscriptionHistoryResponse model"""

    def test_subscription_history_response_with_data(self):
        """Test history response with data"""
        history_entries = [
            SubscriptionHistory(
                history_id=f"hist_{i}",
                subscription_id="sub_123",
                user_id="user_456",
                action=SubscriptionAction.CREDITS_CONSUMED,
            )
            for i in range(5)
        ]

        response = SubscriptionHistoryResponse(
            success=True,
            message="History retrieved",
            history=history_entries,
            total=5,
        )

        assert response.success is True
        assert len(response.history) == 5
        assert response.total == 5

    def test_subscription_history_response_empty(self):
        """Test empty history response"""
        response = SubscriptionHistoryResponse(
            success=True,
            message="No history found",
            history=[],
            total=0,
        )

        assert response.success is True
        assert len(response.history) == 0
        assert response.total == 0

    def test_subscription_history_response_defaults(self):
        """Test default values"""
        response = SubscriptionHistoryResponse(
            success=True,
            message="History",
        )

        assert response.history == []
        assert response.total == 0


class TestSubscriptionStatsResponse:
    """Test SubscriptionStatsResponse model"""

    def test_subscription_stats_response_complete(self):
        """Test complete subscription statistics"""
        stats = SubscriptionStatsResponse(
            total_subscriptions=1000,
            active_subscriptions=750,
            trialing_subscriptions=50,
            canceled_subscriptions=200,
            subscriptions_by_tier={
                "free": 500,
                "pro": 350,
                "max": 100,
                "team": 40,
                "enterprise": 10,
            },
            monthly_recurring_revenue=Decimal("45000.00"),
            annual_recurring_revenue=Decimal("540000.00"),
            total_credits_allocated=500000000,
            total_credits_consumed=350000000,
            average_credit_usage_percentage=70.0,
        )

        assert stats.total_subscriptions == 1000
        assert stats.active_subscriptions == 750
        assert stats.trialing_subscriptions == 50
        assert stats.canceled_subscriptions == 200
        assert stats.subscriptions_by_tier["free"] == 500
        assert stats.subscriptions_by_tier["enterprise"] == 10
        assert stats.monthly_recurring_revenue == Decimal("45000.00")
        assert stats.annual_recurring_revenue == Decimal("540000.00")
        assert stats.total_credits_allocated == 500000000
        assert stats.total_credits_consumed == 350000000
        assert stats.average_credit_usage_percentage == 70.0

    def test_subscription_stats_response_minimal(self):
        """Test minimal subscription statistics"""
        stats = SubscriptionStatsResponse(
            total_subscriptions=0,
            active_subscriptions=0,
            trialing_subscriptions=0,
            canceled_subscriptions=0,
            subscriptions_by_tier={},
            monthly_recurring_revenue=Decimal("0.00"),
            annual_recurring_revenue=Decimal("0.00"),
            total_credits_allocated=0,
            total_credits_consumed=0,
            average_credit_usage_percentage=0.0,
        )

        assert stats.total_subscriptions == 0
        assert stats.active_subscriptions == 0
        assert stats.subscriptions_by_tier == {}
        assert stats.monthly_recurring_revenue == Decimal("0.00")


# ====================
# Service Model Tests
# ====================

class TestHealthResponse:
    """Test HealthResponse model"""

    def test_health_response_healthy(self):
        """Test healthy service response"""
        response = HealthResponse(
            status="healthy",
            service="subscription_service",
            port=8080,
            version="1.0.0",
            timestamp="2024-12-15T10:00:00Z",
            database_connected=True,
        )

        assert response.status == "healthy"
        assert response.service == "subscription_service"
        assert response.port == 8080
        assert response.version == "1.0.0"
        assert response.database_connected is True

    def test_health_response_unhealthy(self):
        """Test unhealthy service response"""
        response = HealthResponse(
            status="unhealthy",
            service="subscription_service",
            port=8080,
            version="1.0.0",
            timestamp="2024-12-15T10:00:00Z",
            database_connected=False,
        )

        assert response.status == "unhealthy"
        assert response.database_connected is False

    def test_health_response_defaults(self):
        """Test default values"""
        response = HealthResponse(
            status="healthy",
            service="subscription_service",
            port=8080,
            version="1.0.0",
            timestamp="2024-12-15T10:00:00Z",
        )

        assert response.database_connected is False


class TestSubscriptionServiceInfo:
    """Test SubscriptionServiceInfo model"""

    def test_service_info_complete(self):
        """Test complete service information"""
        info = SubscriptionServiceInfo(
            service="subscription_service",
            version="1.0.0",
            description="Subscription and credit management service",
            capabilities=[
                "subscription_management",
                "credit_allocation",
                "credit_consumption",
                "billing_cycle_management",
                "trial_management",
            ],
            supported_tiers=["free", "pro", "max", "team", "enterprise"],
            supported_billing_cycles=["monthly", "quarterly", "yearly"],
        )

        assert info.service == "subscription_service"
        assert info.version == "1.0.0"
        assert len(info.capabilities) == 5
        assert "subscription_management" in info.capabilities
        assert len(info.supported_tiers) == 5
        assert "enterprise" in info.supported_tiers
        assert len(info.supported_billing_cycles) == 3
        assert "yearly" in info.supported_billing_cycles

    def test_service_info_minimal(self):
        """Test minimal service information"""
        info = SubscriptionServiceInfo(
            service="subscription_service",
            version="0.1.0",
            description="Beta version",
            capabilities=[],
            supported_tiers=[],
            supported_billing_cycles=[],
        )

        assert info.service == "subscription_service"
        assert info.capabilities == []
        assert info.supported_tiers == []


class TestErrorResponse:
    """Test ErrorResponse model"""

    def test_error_response_with_code(self):
        """Test error response with error code"""
        response = ErrorResponse(
            error="Subscription not found",
            error_code="SUBSCRIPTION_NOT_FOUND",
            details={"subscription_id": "sub_123"},
        )

        assert response.success is False
        assert response.error == "Subscription not found"
        assert response.error_code == "SUBSCRIPTION_NOT_FOUND"
        assert response.details == {"subscription_id": "sub_123"}

    def test_error_response_simple(self):
        """Test simple error response"""
        response = ErrorResponse(
            error="Invalid request",
        )

        assert response.success is False
        assert response.error == "Invalid request"
        assert response.error_code is None
        assert response.details is None

    def test_error_response_with_validation_details(self):
        """Test error response with validation details"""
        response = ErrorResponse(
            error="Validation failed",
            error_code="VALIDATION_ERROR",
            details={
                "field": "credits_to_consume",
                "message": "Must be greater than 0",
            },
        )

        assert response.success is False
        assert response.error == "Validation failed"
        assert response.error_code == "VALIDATION_ERROR"
        assert "field" in response.details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
