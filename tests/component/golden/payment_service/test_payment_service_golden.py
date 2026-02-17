"""
Payment Service Golden Component Tests

Golden reference tests for payment_service business logic.
Tests the PaymentService class with mocked dependencies.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, patch

import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../microservices/payment_service"))

from microservices.payment_service.payment_service import PaymentService
from microservices.payment_service.models import (
    BillingCycle,
    Currency,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Refund,
    RefundStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    CancelSubscriptionRequest,
    CreatePaymentIntentRequest,
    CreateRefundRequest,
)

from .mocks import (
    MockPaymentRepository,
    MockEventBus,
    MockAccountClient,
    MockWalletClient,
    MockBillingClient,
    MockProductClient,
)


pytestmark = [pytest.mark.component, pytest.mark.asyncio, pytest.mark.golden]


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_repository():
    """Create a mock repository instance"""
    return MockPaymentRepository()


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus instance"""
    return MockEventBus()


@pytest.fixture
def mock_account_client():
    """Create a mock account client instance"""
    return MockAccountClient()


@pytest.fixture
def mock_wallet_client():
    """Create a mock wallet client instance"""
    return MockWalletClient()


@pytest.fixture
def mock_billing_client():
    """Create a mock billing client instance"""
    return MockBillingClient()


@pytest.fixture
def mock_product_client():
    """Create a mock product client instance"""
    return MockProductClient()


@pytest.fixture
def payment_service(
    mock_repository,
    mock_event_bus,
    mock_account_client,
    mock_wallet_client,
    mock_billing_client,
    mock_product_client,
):
    """Create a PaymentService instance with mocked dependencies"""
    # Disable Stripe by not providing API key
    service = PaymentService(
        repository=mock_repository,
        stripe_secret_key=None,
        event_bus=mock_event_bus,
        account_client=mock_account_client,
        wallet_client=mock_wallet_client,
        billing_client=mock_billing_client,
        product_client=mock_product_client,
    )
    return service


@pytest.fixture
async def sample_plan(mock_repository) -> SubscriptionPlan:
    """Create a sample subscription plan for testing"""
    plan = SubscriptionPlan(
        plan_id="plan_pro_monthly",
        name="Pro Monthly",
        tier=SubscriptionTier.PRO,
        price=Decimal("29.99"),
        currency=Currency.USD,
        billing_cycle=BillingCycle.MONTHLY,
        features={"api_calls": 10000, "storage_gb": 100},
        trial_days=14,
        is_active=True,
        is_public=True,
    )
    await mock_repository.create_subscription_plan(plan)
    return plan


@pytest.fixture
async def sample_subscription(mock_repository, sample_plan) -> Subscription:
    """Create a sample subscription for testing"""
    subscription = Subscription(
        subscription_id="sub_test_123",
        user_id="test_user_123",
        plan_id=sample_plan.plan_id,
        status=SubscriptionStatus.ACTIVE,
        tier=SubscriptionTier.PRO,
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30),
        billing_cycle=BillingCycle.MONTHLY,
    )
    await mock_repository.create_subscription(subscription)
    return subscription


@pytest.fixture
async def sample_payment(mock_repository) -> Payment:
    """Create a sample payment for testing"""
    payment = Payment(
        payment_id="pi_test_123",
        user_id="test_user_123",
        amount=Decimal("29.99"),
        currency=Currency.USD,
        description="Pro Monthly Subscription",
        status=PaymentStatus.SUCCEEDED,
        payment_method=PaymentMethod.STRIPE,
        processor_payment_id="pi_test_123",
    )
    await mock_repository.create_payment(payment)
    return payment


# ============================================================
# Subscription Plan Tests
# ============================================================


class TestSubscriptionPlanOperations:
    """Tests for subscription plan management"""

    async def test_create_subscription_plan_success(self, payment_service, mock_repository):
        """Test creating a subscription plan successfully"""
        plan = await payment_service.create_subscription_plan(
            plan_id="plan_basic_monthly",
            name="Basic Monthly",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
            features={"api_calls": 1000},
            trial_days=7,
        )
        
        assert plan is not None
        assert plan.plan_id == "plan_basic_monthly"
        assert plan.name == "Basic Monthly"
        assert plan.tier == SubscriptionTier.BASIC
        assert plan.price == Decimal("9.99")
        assert plan.billing_cycle == BillingCycle.MONTHLY
        assert plan.trial_days == 7
        
        # Verify stored in repository
        stored_plan = await mock_repository.get_subscription_plan("plan_basic_monthly")
        assert stored_plan is not None

    async def test_create_plan_with_all_tiers(self, payment_service):
        """Test creating plans for all subscription tiers"""
        tiers = [
            SubscriptionTier.FREE,
            SubscriptionTier.BASIC,
            SubscriptionTier.PRO,
            SubscriptionTier.ENTERPRISE,
        ]
        
        for tier in tiers:
            plan = await payment_service.create_subscription_plan(
                plan_id=f"plan_{tier.value}_monthly",
                name=f"{tier.value.title()} Monthly",
                tier=tier,
                price=Decimal("0") if tier == SubscriptionTier.FREE else Decimal("29.99"),
                billing_cycle=BillingCycle.MONTHLY,
            )
            assert plan.tier == tier

    async def test_get_subscription_plan(self, payment_service, sample_plan):
        """Test retrieving a subscription plan"""
        plan = await payment_service.get_subscription_plan(sample_plan.plan_id)
        
        assert plan is not None
        assert plan.plan_id == sample_plan.plan_id
        assert plan.name == sample_plan.name

    async def test_get_nonexistent_plan(self, payment_service):
        """Test retrieving a non-existent plan returns None"""
        plan = await payment_service.get_subscription_plan("nonexistent_plan")
        assert plan is None

    async def test_list_subscription_plans(self, payment_service, sample_plan):
        """Test listing subscription plans"""
        # Create additional plans
        await payment_service.create_subscription_plan(
            plan_id="plan_basic",
            name="Basic",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
        )
        
        plans = await payment_service.list_subscription_plans()
        assert len(plans) >= 2

    async def test_list_plans_by_tier(self, payment_service, mock_repository, sample_plan):
        """Test listing plans filtered by tier"""
        # Create a BASIC plan
        basic_plan = SubscriptionPlan(
            plan_id="plan_basic_filter",
            name="Basic Filter Test",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
            is_public=True,
        )
        await mock_repository.create_subscription_plan(basic_plan)
        
        pro_plans = await payment_service.list_subscription_plans(tier=SubscriptionTier.PRO)
        
        for plan in pro_plans:
            assert plan.tier == SubscriptionTier.PRO


# ============================================================
# Subscription Tests
# ============================================================


class TestSubscriptionOperations:
    """Tests for subscription lifecycle management"""

    async def test_create_subscription_success(self, payment_service, sample_plan):
        """Test creating a subscription successfully"""
        request = CreateSubscriptionRequest(
            user_id="test_user_new",
            plan_id=sample_plan.plan_id,
            trial_days=14,
            metadata={"source": "web"},
        )
        
        response = await payment_service.create_subscription(request)
        
        assert response is not None
        assert response.subscription is not None
        assert response.subscription.user_id == "test_user_new"
        assert response.subscription.plan_id == sample_plan.plan_id
        assert response.subscription.status == SubscriptionStatus.TRIALING
        assert response.plan is not None

    async def test_create_subscription_without_trial(self, payment_service, mock_repository):
        """Test creating a subscription without trial period"""
        # Create plan without trial
        plan = SubscriptionPlan(
            plan_id="plan_no_trial",
            name="No Trial Plan",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
            trial_days=0,
            is_public=True,
        )
        await mock_repository.create_subscription_plan(plan)
        
        request = CreateSubscriptionRequest(
            user_id="test_user_no_trial",
            plan_id="plan_no_trial",
        )
        
        response = await payment_service.create_subscription(request)
        
        assert response.subscription.status == SubscriptionStatus.ACTIVE
        assert response.subscription.trial_start is None
        assert response.subscription.trial_end is None

    async def test_create_subscription_invalid_user(self, payment_service, sample_plan, mock_account_client):
        """Test creating subscription for invalid user fails"""
        # Configure mock to return None for this user
        mock_account_client.accounts["invalid_user"] = None
        
        request = CreateSubscriptionRequest(
            user_id="unknown_user_xyz",
            plan_id=sample_plan.plan_id,
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.create_subscription(request)
        
        assert "does not exist" in str(exc_info.value) or "validation failed" in str(exc_info.value)

    async def test_create_subscription_invalid_plan(self, payment_service):
        """Test creating subscription with invalid plan fails"""
        request = CreateSubscriptionRequest(
            user_id="test_user_123",
            plan_id="nonexistent_plan",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.create_subscription(request)
        
        assert "not found" in str(exc_info.value).lower()

    async def test_get_user_subscription(self, payment_service, sample_subscription):
        """Test retrieving user's current subscription"""
        response = await payment_service.get_user_subscription(sample_subscription.user_id)
        
        assert response is not None
        assert response.subscription.subscription_id == sample_subscription.subscription_id
        assert response.plan is not None

    async def test_get_user_subscription_not_found(self, payment_service):
        """Test retrieving subscription for user with no subscription"""
        response = await payment_service.get_user_subscription("user_without_subscription")
        assert response is None

    async def test_update_subscription(self, payment_service, sample_subscription, mock_repository):
        """Test updating a subscription"""
        # Create a new plan to upgrade to
        enterprise_plan = SubscriptionPlan(
            plan_id="plan_enterprise",
            name="Enterprise",
            tier=SubscriptionTier.ENTERPRISE,
            price=Decimal("99.99"),
            billing_cycle=BillingCycle.MONTHLY,
            is_public=True,
        )
        await mock_repository.create_subscription_plan(enterprise_plan)
        
        request = UpdateSubscriptionRequest(
            plan_id="plan_enterprise",
            metadata={"upgrade_reason": "growth"},
        )
        
        response = await payment_service.update_subscription(
            sample_subscription.subscription_id,
            request,
        )
        
        assert response is not None
        assert response.subscription.plan_id == "plan_enterprise"

    async def test_update_nonexistent_subscription(self, payment_service):
        """Test updating non-existent subscription fails"""
        request = UpdateSubscriptionRequest(
            plan_id="some_plan",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.update_subscription("nonexistent_sub", request)
        
        assert "not found" in str(exc_info.value).lower()

    async def test_cancel_subscription_immediate(self, payment_service, sample_subscription):
        """Test immediate subscription cancellation"""
        request = CancelSubscriptionRequest(
            immediate=True,
            reason="No longer needed",
        )
        
        result = await payment_service.cancel_subscription(
            sample_subscription.subscription_id,
            request,
        )
        
        assert result is not None
        assert result.status == SubscriptionStatus.CANCELED
        assert result.canceled_at is not None
        assert result.cancellation_reason == "No longer needed"

    async def test_cancel_subscription_at_period_end(self, payment_service, sample_subscription):
        """Test subscription cancellation at period end"""
        request = CancelSubscriptionRequest(
            immediate=False,
            reason="Switching plans",
        )
        
        result = await payment_service.cancel_subscription(
            sample_subscription.subscription_id,
            request,
        )
        
        assert result is not None
        assert result.cancel_at_period_end is True
        assert result.status != SubscriptionStatus.CANCELED  # Still active until period ends

    async def test_cancel_nonexistent_subscription(self, payment_service):
        """Test canceling non-existent subscription fails"""
        request = CancelSubscriptionRequest(immediate=True)
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.cancel_subscription("nonexistent_sub", request)
        
        assert "not found" in str(exc_info.value).lower()


# ============================================================
# Payment Tests
# ============================================================


class TestPaymentOperations:
    """Tests for payment processing"""

    async def test_create_payment_intent_success(self, payment_service):
        """Test creating a payment intent successfully"""
        request = CreatePaymentIntentRequest(
            user_id="test_user_123",
            amount=Decimal("49.99"),
            currency=Currency.USD,
            description="One-time purchase",
            metadata={"order_id": "order_123"},
        )
        
        response = await payment_service.create_payment_intent(request)
        
        assert response is not None
        assert response.payment_intent_id is not None
        assert response.amount == Decimal("49.99")
        assert response.currency == Currency.USD
        assert response.status == PaymentStatus.PENDING

    async def test_create_payment_intent_invalid_user(self, payment_service):
        """Test creating payment intent for invalid user fails"""
        request = CreatePaymentIntentRequest(
            user_id="unknown_user_xyz",
            amount=Decimal("49.99"),
            currency=Currency.USD,
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.create_payment_intent(request)
        
        assert "does not exist" in str(exc_info.value) or "validation failed" in str(exc_info.value)

    async def test_confirm_payment_success(self, payment_service, mock_repository):
        """Test confirming a payment successfully"""
        # Create a pending payment
        payment = Payment(
            payment_id="pi_to_confirm",
            user_id="test_user_123",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
            processor_payment_id="pi_to_confirm",
        )
        await mock_repository.create_payment(payment)
        
        result = await payment_service.confirm_payment(
            "pi_to_confirm",
            processor_response={"captured": True},
        )
        
        assert result is not None
        assert result.status == PaymentStatus.SUCCEEDED
        assert result.paid_at is not None

    async def test_confirm_nonexistent_payment(self, payment_service):
        """Test confirming non-existent payment fails"""
        with pytest.raises(ValueError) as exc_info:
            await payment_service.confirm_payment("nonexistent_payment")
        
        assert "not found" in str(exc_info.value).lower()

    async def test_fail_payment(self, payment_service, mock_repository):
        """Test marking a payment as failed"""
        # Create a pending payment
        payment = Payment(
            payment_id="pi_to_fail",
            user_id="test_user_123",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
        )
        await mock_repository.create_payment(payment)
        
        result = await payment_service.fail_payment(
            "pi_to_fail",
            failure_reason="Card declined",
            failure_code="card_declined",
        )
        
        assert result is not None
        assert result.status == PaymentStatus.FAILED
        assert result.failure_reason == "Card declined"
        assert result.failure_code == "card_declined"

    async def test_get_payment_history(self, payment_service, sample_payment):
        """Test retrieving payment history"""
        response = await payment_service.get_payment_history(
            user_id=sample_payment.user_id,
            limit=10,
        )
        
        assert response is not None
        assert response.total_count >= 1
        assert len(response.payments) >= 1

    async def test_get_payment_history_with_filters(self, payment_service, mock_repository):
        """Test payment history with filters"""
        # Create multiple payments with different statuses
        for i in range(3):
            payment = Payment(
                payment_id=f"pi_filter_{i}",
                user_id="test_filter_user",
                amount=Decimal("10.00"),
                currency=Currency.USD,
                status=PaymentStatus.SUCCEEDED if i % 2 == 0 else PaymentStatus.FAILED,
                payment_method=PaymentMethod.STRIPE,
            )
            await mock_repository.create_payment(payment)
        
        response = await payment_service.get_payment_history(
            user_id="test_filter_user",
            status=PaymentStatus.SUCCEEDED,
        )
        
        for payment in response.payments:
            assert payment.status == PaymentStatus.SUCCEEDED

    async def test_get_payment_history_empty(self, payment_service):
        """Test payment history for user with no payments"""
        response = await payment_service.get_payment_history(
            user_id="user_with_no_payments",
        )
        
        assert response.total_count == 0
        assert len(response.payments) == 0


# ============================================================
# Invoice Tests
# ============================================================


class TestInvoiceOperations:
    """Tests for invoice management"""

    async def test_create_invoice_success(self, payment_service):
        """Test creating an invoice successfully"""
        invoice = await payment_service.create_invoice(
            user_id="test_user_123",
            subscription_id="sub_test_123",
            amount_due=Decimal("29.99"),
            due_date=datetime.utcnow() + timedelta(days=14),
            line_items=[
                {"description": "Pro Plan - Monthly", "amount": 29.99}
            ],
        )
        
        assert invoice is not None
        assert invoice.invoice_id is not None
        assert invoice.invoice_number is not None
        assert invoice.status == InvoiceStatus.OPEN
        assert invoice.amount_due == Decimal("29.99")

    async def test_get_invoice(self, payment_service, mock_repository):
        """Test retrieving an invoice"""
        # Create an invoice
        invoice = Invoice(
            invoice_id="inv_test_get",
            invoice_number="INV-2024-001",
            user_id="test_user_123",
            subscription_id="sub_test",
            status=InvoiceStatus.OPEN,
            amount_total=Decimal("29.99"),
            amount_due=Decimal("29.99"),
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30),
            line_items=[],
        )
        await mock_repository.create_invoice(invoice)
        
        response = await payment_service.get_invoice("inv_test_get")
        
        assert response is not None
        assert response.invoice.invoice_id == "inv_test_get"

    async def test_get_nonexistent_invoice(self, payment_service):
        """Test retrieving non-existent invoice returns None"""
        response = await payment_service.get_invoice("nonexistent_invoice")
        assert response is None

    async def test_pay_invoice_success(self, payment_service, mock_repository):
        """Test paying an invoice successfully"""
        # Create an open invoice
        invoice = Invoice(
            invoice_id="inv_to_pay",
            invoice_number="INV-2024-PAY",
            user_id="test_user_123",
            status=InvoiceStatus.OPEN,
            amount_total=Decimal("29.99"),
            amount_due=Decimal("29.99"),
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30),
            line_items=[],
        )
        await mock_repository.create_invoice(invoice)
        
        result = await payment_service.pay_invoice(
            invoice_id="inv_to_pay",
            payment_method_id="pm_test_card",
        )
        
        assert result is not None
        assert result.status == InvoiceStatus.PAID
        assert result.paid_at is not None

    async def test_pay_already_paid_invoice(self, payment_service, mock_repository):
        """Test paying an already paid invoice fails"""
        invoice = Invoice(
            invoice_id="inv_already_paid",
            invoice_number="INV-2024-PAID",
            user_id="test_user_123",
            status=InvoiceStatus.PAID,
            amount_total=Decimal("29.99"),
            amount_due=Decimal("0"),
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30),
            line_items=[],
        )
        await mock_repository.create_invoice(invoice)
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.pay_invoice("inv_already_paid", "pm_test")
        
        assert "not open" in str(exc_info.value).lower()


# ============================================================
# Refund Tests
# ============================================================


class TestRefundOperations:
    """Tests for refund processing"""

    async def test_create_refund_success(self, payment_service, sample_payment):
        """Test creating a refund successfully"""
        request = CreateRefundRequest(
            payment_id=sample_payment.payment_id,
            amount=Decimal("29.99"),
            reason="Customer request",
            requested_by="test_user_123",
        )
        
        refund = await payment_service.create_refund(request)
        
        assert refund is not None
        assert refund.refund_id is not None
        assert refund.payment_id == sample_payment.payment_id
        assert refund.amount == Decimal("29.99")
        assert refund.status == RefundStatus.PROCESSING

    async def test_create_partial_refund(self, payment_service, sample_payment):
        """Test creating a partial refund"""
        request = CreateRefundRequest(
            payment_id=sample_payment.payment_id,
            amount=Decimal("10.00"),  # Partial amount
            reason="Partial service",
            requested_by="test_user_123",
        )
        
        refund = await payment_service.create_refund(request)
        
        assert refund is not None
        assert refund.amount == Decimal("10.00")

    async def test_refund_exceeds_payment_amount(self, payment_service, sample_payment):
        """Test refund amount exceeding payment fails"""
        request = CreateRefundRequest(
            payment_id=sample_payment.payment_id,
            amount=Decimal("100.00"),  # More than payment amount
            reason="Over-refund",
            requested_by="test_user_123",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.create_refund(request)
        
        assert "exceeds" in str(exc_info.value).lower()

    async def test_refund_nonexistent_payment(self, payment_service):
        """Test refunding non-existent payment fails"""
        request = CreateRefundRequest(
            payment_id="nonexistent_payment",
            reason="Test",
            requested_by="test_user",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.create_refund(request)
        
        assert "not found" in str(exc_info.value).lower()

    async def test_refund_failed_payment(self, payment_service, mock_repository):
        """Test refunding a failed payment fails"""
        # Create a failed payment
        failed_payment = Payment(
            payment_id="pi_failed_payment",
            user_id="test_user_123",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            status=PaymentStatus.FAILED,
            payment_method=PaymentMethod.STRIPE,
        )
        await mock_repository.create_payment(failed_payment)
        
        request = CreateRefundRequest(
            payment_id="pi_failed_payment",
            reason="Test",
            requested_by="test_user",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.create_refund(request)
        
        assert "not eligible" in str(exc_info.value).lower()

    async def test_process_refund(self, payment_service, mock_repository, sample_payment):
        """Test processing a refund"""
        # Create a pending refund
        refund = Refund(
            refund_id="re_to_process",
            payment_id=sample_payment.payment_id,
            user_id=sample_payment.user_id,
            amount=sample_payment.amount,
            currency=sample_payment.currency,
            reason="Test refund",
            status=RefundStatus.PENDING,
            requested_by="test_user",
        )
        await mock_repository.create_refund(refund)
        
        result = await payment_service.process_refund(
            refund_id="re_to_process",
            approved_by="admin_user",
        )
        
        assert result is not None
        assert result.status == RefundStatus.SUCCEEDED
        assert result.approved_by == "admin_user"


# ============================================================
# Statistics Tests
# ============================================================


class TestStatistics:
    """Tests for revenue and subscription statistics"""

    async def test_get_revenue_stats(self, payment_service, sample_payment):
        """Test retrieving revenue statistics"""
        stats = await payment_service.get_revenue_stats()
        
        assert stats is not None
        assert "total_revenue" in stats
        assert "payment_count" in stats
        assert stats["total_revenue"] >= 0

    async def test_get_subscription_stats(self, payment_service, sample_subscription):
        """Test retrieving subscription statistics"""
        stats = await payment_service.get_subscription_stats()
        
        assert stats is not None
        assert "active_subscriptions" in stats
        assert "tier_distribution" in stats
        assert stats["active_subscriptions"] >= 0


# ============================================================
# Event Publishing Tests
# ============================================================


class TestEventPublishing:
    """Tests for event publishing behavior"""

    async def test_subscription_created_event_published(
        self, payment_service, sample_plan, mock_event_bus
    ):
        """Test that subscription.created event is published"""
        request = CreateSubscriptionRequest(
            user_id="test_event_user",
            plan_id=sample_plan.plan_id,
        )
        
        await payment_service.create_subscription(request)
        
        # Verify event was published
        assert len(mock_event_bus.published_events) >= 1

    async def test_subscription_canceled_event_published(
        self, payment_service, sample_subscription, mock_event_bus
    ):
        """Test that subscription.canceled event is published"""
        request = CancelSubscriptionRequest(
            immediate=True,
            reason="Test cancellation",
        )
        
        await payment_service.cancel_subscription(
            sample_subscription.subscription_id,
            request,
        )
        
        # Verify event was published
        assert len(mock_event_bus.published_events) >= 1

    async def test_payment_intent_created_event_published(
        self, payment_service, mock_event_bus
    ):
        """Test that payment.intent.created event is published"""
        request = CreatePaymentIntentRequest(
            user_id="test_user_123",
            amount=Decimal("49.99"),
            currency=Currency.USD,
        )
        
        await payment_service.create_payment_intent(request)
        
        # Verify event was published
        assert len(mock_event_bus.published_events) >= 1

    async def test_payment_completed_event_published(
        self, payment_service, mock_repository, mock_event_bus
    ):
        """Test that payment.completed event is published"""
        # Create a pending payment
        payment = Payment(
            payment_id="pi_event_test",
            user_id="test_user_123",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
            processor_payment_id="pi_event_test",
        )
        await mock_repository.create_payment(payment)
        
        await payment_service.confirm_payment("pi_event_test")
        
        # Verify event was published
        assert len(mock_event_bus.published_events) >= 1


# ============================================================
# Edge Cases and Error Handling
# ============================================================


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    async def test_create_subscription_with_zero_trial(self, payment_service, mock_repository):
        """Test creating subscription with explicitly zero trial days"""
        plan = SubscriptionPlan(
            plan_id="plan_zero_trial",
            name="Zero Trial Plan",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
            trial_days=0,
            is_public=True,
        )
        await mock_repository.create_subscription_plan(plan)
        
        request = CreateSubscriptionRequest(
            user_id="test_user_zero_trial",
            plan_id="plan_zero_trial",
            trial_days=0,
        )
        
        response = await payment_service.create_subscription(request)
        
        assert response.subscription.status == SubscriptionStatus.ACTIVE
        assert response.subscription.trial_end is None

    async def test_create_payment_intent_with_different_currencies(self, payment_service):
        """Test creating payment intents with different currencies"""
        currencies = [Currency.USD, Currency.EUR, Currency.GBP]
        
        for currency in currencies:
            request = CreatePaymentIntentRequest(
                user_id="test_user_123",
                amount=Decimal("29.99"),
                currency=currency,
            )
            
            response = await payment_service.create_payment_intent(request)
            
            assert response.currency == currency

    async def test_full_refund_sets_payment_refunded(self, payment_service, sample_payment, mock_repository):
        """Test full refund sets payment status to refunded"""
        request = CreateRefundRequest(
            payment_id=sample_payment.payment_id,
            amount=sample_payment.amount,  # Full amount
            reason="Full refund",
            requested_by="test_user",
        )
        
        await payment_service.create_refund(request)
        
        # Check payment status was updated
        payment = await mock_repository.get_payment(sample_payment.payment_id)
        assert payment.status == PaymentStatus.REFUNDED

    async def test_partial_refund_sets_partial_refund_status(self, payment_service, mock_repository):
        """Test partial refund sets payment status to partial_refund"""
        # Create a payment with larger amount
        payment = Payment(
            payment_id="pi_partial_test",
            user_id="test_user_123",
            amount=Decimal("100.00"),
            currency=Currency.USD,
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.STRIPE,
            processor_payment_id="pi_partial_test",
        )
        await mock_repository.create_payment(payment)
        
        request = CreateRefundRequest(
            payment_id="pi_partial_test",
            amount=Decimal("30.00"),  # Partial
            reason="Partial refund",
            requested_by="test_user",
        )
        
        await payment_service.create_refund(request)
        
        # Check payment status was updated
        updated_payment = await mock_repository.get_payment("pi_partial_test")
        assert updated_payment.status == PaymentStatus.PARTIAL_REFUND

    async def test_billing_cycle_period_calculation(self, payment_service, mock_repository):
        """Test different billing cycles calculate correct periods"""
        cycles = [
            (BillingCycle.MONTHLY, 30),
            (BillingCycle.QUARTERLY, 90),
            (BillingCycle.YEARLY, 365),
        ]
        
        for billing_cycle, expected_days in cycles:
            plan = SubscriptionPlan(
                plan_id=f"plan_{billing_cycle.value}",
                name=f"{billing_cycle.value.title()} Plan",
                tier=SubscriptionTier.PRO,
                price=Decimal("29.99"),
                billing_cycle=billing_cycle,
                trial_days=0,
                is_public=True,
            )
            await mock_repository.create_subscription_plan(plan)
            
            request = CreateSubscriptionRequest(
                user_id=f"test_user_{billing_cycle.value}",
                plan_id=f"plan_{billing_cycle.value}",
            )
            
            response = await payment_service.create_subscription(request)
            
            period_delta = (
                response.subscription.current_period_end -
                response.subscription.current_period_start
            )
            
            assert period_delta.days == expected_days


# ============================================================
# Usage Recording Tests
# ============================================================


class TestUsageRecording:
    """Tests for usage recording functionality"""

    async def test_record_usage_success(self, payment_service, sample_subscription):
        """Test recording usage successfully"""
        usage = await payment_service.record_usage(
            user_id=sample_subscription.user_id,
            subscription_id=sample_subscription.subscription_id,
            metric_name="api_calls",
            quantity=100,
            metadata={"endpoint": "/api/v1/test"},
        )
        
        assert usage is not None
        assert usage.user_id == sample_subscription.user_id
        assert usage.metric_name == "api_calls"
        assert usage.quantity == 100
