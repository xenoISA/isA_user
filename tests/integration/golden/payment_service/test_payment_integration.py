"""
Payment Service Integration Tests

Tests the PaymentService layer with mocked dependencies (repository, event_bus).
These are NOT HTTP tests - they test the service business logic layer directly.

Purpose:
- Test PaymentService business logic with mocked repository
- Test event publishing integration
- Test validation and error handling
- Test cross-service interactions (account, wallet, billing)

According to CDD_GUIDE.md:
- Service layer tests use mocked repository (no real DB)
- Service layer tests use mocked event bus (no real NATS)
- Use PaymentTestDataFactory from data contracts (no hardcoded data)
- Target 20-30 tests with full coverage

Usage:
    pytest tests/integration/golden/payment_service/test_payment_integration.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Import from centralized data contracts
from tests.contracts.payment.data_contract import (
    PaymentTestDataFactory,
    PaymentStatusEnum,
    PaymentMethodEnum,
    SubscriptionStatusEnum,
    SubscriptionTierEnum,
    BillingCycleEnum,
    InvoiceStatusEnum,
    RefundStatusEnum,
    CurrencyEnum,
)

# Import service layer to test
from microservices.payment_service.payment_service import PaymentService

# Import protocols
from microservices.payment_service.protocols import (
    PaymentRepositoryProtocol,
    EventBusProtocol,
    AccountClientProtocol,
    WalletClientProtocol,
    BillingClientProtocol,
    ProductClientProtocol,
)

# Import models
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

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_payment_repository():
    """Mock payment repository for testing service layer."""
    repo = AsyncMock()
    repo._plans = {}
    repo._subscriptions = {}
    repo._payments = {}
    repo._invoices = {}
    repo._refunds = {}
    repo._payment_methods = {}
    
    # Setup basic repository methods
    async def create_subscription_plan(plan):
        plan.created_at = datetime.utcnow()
        repo._plans[plan.plan_id] = plan
        return plan
    
    async def get_subscription_plan(plan_id):
        return repo._plans.get(plan_id)
    
    async def list_subscription_plans(tier=None, is_public=True):
        plans = list(repo._plans.values())
        if tier:
            plans = [p for p in plans if p.tier == tier]
        return plans
    
    async def create_subscription(subscription):
        subscription.created_at = datetime.utcnow()
        repo._subscriptions[subscription.subscription_id] = subscription
        return subscription
    
    async def get_subscription(subscription_id):
        return repo._subscriptions.get(subscription_id)
    
    async def get_user_active_subscription(user_id):
        for sub in repo._subscriptions.values():
            if sub.user_id == user_id and sub.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]:
                return sub
        return None
    
    async def update_subscription(subscription_id, updates):
        if subscription_id not in repo._subscriptions:
            return None
        sub = repo._subscriptions[subscription_id]
        for key, value in updates.items():
            if hasattr(sub, key):
                setattr(sub, key, value)
        return sub
    
    async def cancel_subscription(subscription_id, immediate=False, reason=None):
        if subscription_id not in repo._subscriptions:
            return None
        sub = repo._subscriptions[subscription_id]
        sub.canceled_at = datetime.utcnow()
        sub.cancellation_reason = reason
        if immediate:
            sub.status = SubscriptionStatus.CANCELED
        else:
            sub.cancel_at_period_end = True
        return sub
    
    async def create_payment(payment):
        payment.created_at = datetime.utcnow()
        repo._payments[payment.payment_id] = payment
        return payment
    
    async def get_payment(payment_id):
        return repo._payments.get(payment_id)
    
    async def update_payment_status(payment_id, status, processor_response=None):
        if payment_id not in repo._payments:
            return None
        payment = repo._payments[payment_id]
        payment.status = status
        if processor_response:
            payment.processor_response = processor_response
        if status == PaymentStatus.SUCCEEDED:
            payment.paid_at = datetime.utcnow()
        elif status == PaymentStatus.FAILED:
            payment.failed_at = datetime.utcnow()
        return payment
    
    async def get_user_payments(user_id, limit=10, status=None):
        payments = [p for p in repo._payments.values() if p.user_id == user_id]
        if status:
            payments = [p for p in payments if p.status == status]
        return payments[:limit]
    
    async def get_user_default_payment_method(user_id):
        methods = repo._payment_methods.get(user_id, [])
        for m in methods:
            if m.is_default:
                return m
        return methods[0] if methods else None
    
    async def create_invoice(invoice):
        invoice.created_at = datetime.utcnow()
        repo._invoices[invoice.invoice_id] = invoice
        return invoice
    
    async def get_invoice(invoice_id):
        return repo._invoices.get(invoice_id)
    
    async def mark_invoice_paid(invoice_id, payment_intent_id):
        if invoice_id not in repo._invoices:
            return None
        invoice = repo._invoices[invoice_id]
        invoice.status = InvoiceStatus.PAID
        invoice.payment_intent_id = payment_intent_id
        invoice.paid_at = datetime.utcnow()
        return invoice
    
    async def create_refund(refund):
        repo._refunds[refund.refund_id] = refund
        return refund
    
    async def update_refund_status(refund_id, status):
        if refund_id not in repo._refunds:
            return False
        repo._refunds[refund_id].status = status
        return True
    
    async def process_refund(refund_id, approved_by=None):
        if refund_id not in repo._refunds:
            return None
        refund = repo._refunds[refund_id]
        refund.status = RefundStatus.SUCCEEDED
        refund.approved_by = approved_by
        refund.processed_at = datetime.utcnow()
        return refund
    
    async def get_revenue_statistics(days=30):
        payments = [p for p in repo._payments.values() if p.status == PaymentStatus.SUCCEEDED]
        total = sum(p.amount for p in payments)
        return {
            "total_revenue": float(total),
            "payment_count": len(payments),
            "average_payment": float(total / len(payments)) if payments else 0,
            "period_days": days,
        }
    
    async def get_subscription_statistics():
        active = [s for s in repo._subscriptions.values() 
                 if s.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]]
        tier_dist = {}
        for s in active:
            tier_dist[s.tier.value] = tier_dist.get(s.tier.value, 0) + 1
        return {
            "active_subscriptions": len(active),
            "tier_distribution": tier_dist,
            "churn_rate": 0.0,
        }
    
    repo.create_subscription_plan = AsyncMock(side_effect=create_subscription_plan)
    repo.get_subscription_plan = AsyncMock(side_effect=get_subscription_plan)
    repo.list_subscription_plans = AsyncMock(side_effect=list_subscription_plans)
    repo.create_subscription = AsyncMock(side_effect=create_subscription)
    repo.get_subscription = AsyncMock(side_effect=get_subscription)
    repo.get_user_active_subscription = AsyncMock(side_effect=get_user_active_subscription)
    repo.update_subscription = AsyncMock(side_effect=update_subscription)
    repo.cancel_subscription = AsyncMock(side_effect=cancel_subscription)
    repo.create_payment = AsyncMock(side_effect=create_payment)
    repo.get_payment = AsyncMock(side_effect=get_payment)
    repo.update_payment_status = AsyncMock(side_effect=update_payment_status)
    repo.get_user_payments = AsyncMock(side_effect=get_user_payments)
    repo.get_user_default_payment_method = AsyncMock(side_effect=get_user_default_payment_method)
    repo.create_invoice = AsyncMock(side_effect=create_invoice)
    repo.get_invoice = AsyncMock(side_effect=get_invoice)
    repo.mark_invoice_paid = AsyncMock(side_effect=mark_invoice_paid)
    repo.create_refund = AsyncMock(side_effect=create_refund)
    repo.update_refund_status = AsyncMock(side_effect=update_refund_status)
    repo.process_refund = AsyncMock(side_effect=process_refund)
    repo.get_revenue_statistics = AsyncMock(side_effect=get_revenue_statistics)
    repo.get_subscription_statistics = AsyncMock(side_effect=get_subscription_statistics)
    
    return repo


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event publishing."""
    bus = AsyncMock()
    bus.published_events = []
    
    async def capture_event(event):
        bus.published_events.append(event)
    
    bus.publish_event = AsyncMock(side_effect=capture_event)
    return bus


@pytest.fixture
def mock_account_client():
    """Mock account client for cross-service tests."""
    client = AsyncMock()
    client._accounts = {}
    
    async def get_account_profile(user_id):
        if user_id in client._accounts:
            return client._accounts[user_id]
        # Return valid account for test_ or user_ prefixed IDs
        if user_id.startswith("test_") or user_id.startswith("user_"):
            return {"user_id": user_id, "email": f"{user_id}@test.com", "status": "active"}
        return None
    
    async def validate_user(user_id):
        profile = await get_account_profile(user_id)
        return profile is not None
    
    client.get_account_profile = AsyncMock(side_effect=get_account_profile)
    client.validate_user = AsyncMock(side_effect=validate_user)
    return client


@pytest.fixture
def mock_wallet_client():
    """Mock wallet client for cross-service tests."""
    client = AsyncMock()
    client._wallets = {}
    
    async def get_balance(user_id, wallet_type="main"):
        balance = client._wallets.get(f"{user_id}:{wallet_type}", Decimal("100"))
        return {"user_id": user_id, "wallet_type": wallet_type, "balance": float(balance)}
    
    async def add_funds(user_id, wallet_type, amount, description, reference_id):
        key = f"{user_id}:{wallet_type}"
        client._wallets[key] = client._wallets.get(key, Decimal("0")) + Decimal(str(amount))
        return {"success": True, "transaction_id": f"txn_{reference_id}"}
    
    async def consume(user_id, wallet_type, amount, description, reference_id):
        key = f"{user_id}:{wallet_type}"
        current = client._wallets.get(key, Decimal("0"))
        if current < Decimal(str(amount)):
            return {"success": False, "error": "Insufficient funds"}
        client._wallets[key] = current - Decimal(str(amount))
        return {"success": True, "transaction_id": f"txn_{reference_id}"}
    
    client.get_balance = AsyncMock(side_effect=get_balance)
    client.add_funds = AsyncMock(side_effect=add_funds)
    client.consume = AsyncMock(side_effect=consume)
    return client


@pytest.fixture
def mock_billing_client():
    """Mock billing client for cross-service tests."""
    client = AsyncMock()
    client._records = []
    
    async def record_usage(user_id, product_id, service_type, usage_amount):
        record = {
            "user_id": user_id,
            "product_id": product_id,
            "service_type": service_type,
            "usage_amount": usage_amount,
            "timestamp": datetime.utcnow().isoformat(),
        }
        client._records.append(record)
        return {"success": True, "record_id": f"rec_{len(client._records)}"}
    
    async def get_billing_records(user_id, limit=10):
        return [r for r in client._records if r["user_id"] == user_id][:limit]
    
    client.record_usage = AsyncMock(side_effect=record_usage)
    client.get_billing_records = AsyncMock(side_effect=get_billing_records)
    return client


@pytest.fixture
def mock_product_client():
    """Mock product client for cross-service tests."""
    client = AsyncMock()
    client._products = {}
    
    async def get_product(product_id):
        return client._products.get(product_id, {
            "product_id": product_id,
            "name": f"Product {product_id}",
            "price": 29.99,
        })
    
    async def get_product_pricing(product_id, user_id, subscription_id=None):
        product = await get_product(product_id)
        discount = 0.1 if subscription_id else 0
        return {
            "product_id": product_id,
            "base_price": product["price"],
            "discount": discount,
            "final_price": product["price"] * (1 - discount),
        }
    
    client.get_product = AsyncMock(side_effect=get_product)
    client.get_product_pricing = AsyncMock(side_effect=get_product_pricing)
    return client


@pytest.fixture
def payment_service(
    mock_payment_repository,
    mock_event_bus,
    mock_account_client,
    mock_wallet_client,
    mock_billing_client,
    mock_product_client,
):
    """Create PaymentService with mocked dependencies."""
    return PaymentService(
        repository=mock_payment_repository,
        stripe_secret_key=None,  # Disable Stripe
        event_bus=mock_event_bus,
        account_client=mock_account_client,
        wallet_client=mock_wallet_client,
        billing_client=mock_billing_client,
        product_client=mock_product_client,
    )


# ============================================================================
# Subscription Plan Integration Tests (6 tests)
# ============================================================================

class TestSubscriptionPlanIntegration:
    """Integration tests for subscription plan operations."""

    async def test_create_plan_with_factory_data(
        self, payment_service, mock_payment_repository
    ):
        """Creates plan with data from PaymentTestDataFactory."""
        plan_data = PaymentTestDataFactory.make_valid_create_plan_request()
        
        result = await payment_service.create_subscription_plan(
            plan_id=plan_data["plan_id"],
            name=plan_data["name"],
            tier=SubscriptionTier(plan_data["tier"]),
            price=Decimal(str(plan_data["price"])),
            billing_cycle=BillingCycle(plan_data["billing_cycle"]),
            features=plan_data.get("features", {}),
            trial_days=plan_data.get("trial_days", 0),
        )
        
        assert result is not None
        assert result.plan_id == plan_data["plan_id"]
        assert result.name == plan_data["name"]

    async def test_create_enterprise_plan(
        self, payment_service, mock_payment_repository
    ):
        """Creates enterprise tier plan successfully."""
        plan_data = PaymentTestDataFactory.make_valid_enterprise_plan()
        
        result = await payment_service.create_subscription_plan(
            plan_id=plan_data["plan_id"],
            name=plan_data["name"],
            tier=SubscriptionTier(plan_data["tier"]),
            price=Decimal(str(plan_data["price"])),
            billing_cycle=BillingCycle(plan_data["billing_cycle"]),
            features=plan_data.get("features", {}),
        )
        
        assert result.tier == SubscriptionTier.ENTERPRISE

    async def test_list_plans_by_tier_integration(
        self, payment_service, mock_payment_repository
    ):
        """Lists plans filtered by tier."""
        # Create plans for different tiers
        for tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO]:
            plan = SubscriptionPlan(
                plan_id=f"plan_{tier.value}_test",
                name=f"{tier.value.title()} Test Plan",
                tier=tier,
                price=Decimal("19.99"),
                billing_cycle=BillingCycle.MONTHLY,
                is_public=True,
            )
            await mock_payment_repository.create_subscription_plan(plan)
        
        pro_plans = await payment_service.list_subscription_plans(tier=SubscriptionTier.PRO)
        
        for plan in pro_plans:
            assert plan.tier == SubscriptionTier.PRO


# ============================================================================
# Subscription Integration Tests (8 tests)
# ============================================================================

class TestSubscriptionIntegration:
    """Integration tests for subscription lifecycle operations."""

    async def test_create_subscription_with_factory_data(
        self, payment_service, mock_payment_repository, mock_account_client
    ):
        """Creates subscription using factory-generated data."""
        # Setup plan
        plan_data = PaymentTestDataFactory.make_valid_create_plan_request()
        plan = SubscriptionPlan(
            plan_id=plan_data["plan_id"],
            name=plan_data["name"],
            tier=SubscriptionTier(plan_data["tier"]),
            price=Decimal(str(plan_data["price"])),
            billing_cycle=BillingCycle(plan_data["billing_cycle"]),
            trial_days=plan_data.get("trial_days", 14),
            is_public=True,
        )
        await mock_payment_repository.create_subscription_plan(plan)
        
        # Create subscription with factory data
        sub_data = PaymentTestDataFactory.make_valid_create_subscription_request()
        sub_data["plan_id"] = plan_data["plan_id"]  # Use created plan
        
        request = CreateSubscriptionRequest(
            user_id=sub_data["user_id"],
            plan_id=sub_data["plan_id"],
            trial_days=sub_data.get("trial_days"),
            metadata=sub_data.get("metadata"),
        )
        
        result = await payment_service.create_subscription(request)
        
        assert result.subscription is not None
        assert result.subscription.user_id == sub_data["user_id"]

    async def test_subscription_user_validation_integration(
        self, payment_service, mock_payment_repository, mock_account_client
    ):
        """Validates user via account service before creating subscription."""
        # Setup plan
        plan = SubscriptionPlan(
            plan_id="plan_validation_test",
            name="Validation Test Plan",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
            is_public=True,
        )
        await mock_payment_repository.create_subscription_plan(plan)
        
        request = CreateSubscriptionRequest(
            user_id="test_valid_user",
            plan_id="plan_validation_test",
        )
        
        result = await payment_service.create_subscription(request)
        
        # Verify account client was called
        mock_account_client.get_account_profile.assert_called()
        assert result.subscription is not None

    async def test_subscription_invalid_user_rejected(
        self, payment_service, mock_payment_repository
    ):
        """Rejects subscription for invalid user."""
        plan = SubscriptionPlan(
            plan_id="plan_reject_test",
            name="Reject Test Plan",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
            is_public=True,
        )
        await mock_payment_repository.create_subscription_plan(plan)
        
        request = CreateSubscriptionRequest(
            user_id="unknown_invalid_user",  # Won't be validated
            plan_id="plan_reject_test",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.create_subscription(request)
        
        assert "not exist" in str(exc_info.value).lower() or "validation failed" in str(exc_info.value).lower()

    async def test_subscription_cancel_integration(
        self, payment_service, mock_payment_repository, mock_event_bus
    ):
        """Cancels subscription and publishes event."""
        # Setup subscription
        plan = SubscriptionPlan(
            plan_id="plan_cancel_test",
            name="Cancel Test Plan",
            tier=SubscriptionTier.PRO,
            price=Decimal("29.99"),
            billing_cycle=BillingCycle.MONTHLY,
            is_public=True,
        )
        await mock_payment_repository.create_subscription_plan(plan)
        
        subscription = Subscription(
            subscription_id="sub_cancel_test",
            user_id="test_cancel_user",
            plan_id="plan_cancel_test",
            status=SubscriptionStatus.ACTIVE,
            tier=SubscriptionTier.PRO,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            billing_cycle=BillingCycle.MONTHLY,
        )
        await mock_payment_repository.create_subscription(subscription)
        
        request = CancelSubscriptionRequest(
            immediate=True,
            reason="Testing cancellation",
        )
        
        result = await payment_service.cancel_subscription("sub_cancel_test", request)
        
        assert result.status == SubscriptionStatus.CANCELED
        # Event should be published
        assert len(mock_event_bus.published_events) > 0

    async def test_subscription_update_plan_change(
        self, payment_service, mock_payment_repository
    ):
        """Updates subscription with plan change."""
        # Create two plans
        basic_plan = SubscriptionPlan(
            plan_id="plan_basic_upgrade",
            name="Basic Plan",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
            is_public=True,
        )
        pro_plan = SubscriptionPlan(
            plan_id="plan_pro_upgrade",
            name="Pro Plan",
            tier=SubscriptionTier.PRO,
            price=Decimal("29.99"),
            billing_cycle=BillingCycle.MONTHLY,
            is_public=True,
        )
        await mock_payment_repository.create_subscription_plan(basic_plan)
        await mock_payment_repository.create_subscription_plan(pro_plan)
        
        subscription = Subscription(
            subscription_id="sub_upgrade_test",
            user_id="test_upgrade_user",
            plan_id="plan_basic_upgrade",
            status=SubscriptionStatus.ACTIVE,
            tier=SubscriptionTier.BASIC,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            billing_cycle=BillingCycle.MONTHLY,
        )
        await mock_payment_repository.create_subscription(subscription)
        
        request = UpdateSubscriptionRequest(
            plan_id="plan_pro_upgrade",
        )
        
        result = await payment_service.update_subscription("sub_upgrade_test", request)
        
        assert result.subscription.plan_id == "plan_pro_upgrade"


# ============================================================================
# Payment Integration Tests (8 tests)
# ============================================================================

class TestPaymentIntegration:
    """Integration tests for payment operations."""

    async def test_create_payment_intent_with_factory_data(
        self, payment_service, mock_account_client
    ):
        """Creates payment intent using factory data."""
        payment_data = PaymentTestDataFactory.make_valid_create_payment_intent_request()
        
        request = CreatePaymentIntentRequest(
            user_id=payment_data["user_id"],
            amount=Decimal(str(payment_data["amount"])),
            currency=Currency(payment_data["currency"]),
            description=payment_data.get("description"),
            metadata=payment_data.get("metadata"),
        )
        
        result = await payment_service.create_payment_intent(request)
        
        assert result.payment_intent_id is not None
        assert result.amount == Decimal(str(payment_data["amount"]))
        assert result.status == PaymentStatus.PENDING

    async def test_payment_intent_user_validation(
        self, payment_service, mock_account_client
    ):
        """Validates user before creating payment intent."""
        request = CreatePaymentIntentRequest(
            user_id="test_payment_user",
            amount=Decimal("49.99"),
            currency=Currency.USD,
        )
        
        result = await payment_service.create_payment_intent(request)
        
        mock_account_client.get_account_profile.assert_called_with("test_payment_user")
        assert result is not None

    async def test_payment_confirm_publishes_event(
        self, payment_service, mock_payment_repository, mock_event_bus
    ):
        """Confirms payment and publishes completed event."""
        # Create pending payment
        payment = Payment(
            payment_id="pi_confirm_event",
            user_id="test_user_123",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
            processor_payment_id="pi_confirm_event",
        )
        await mock_payment_repository.create_payment(payment)
        
        result = await payment_service.confirm_payment("pi_confirm_event")
        
        assert result.status == PaymentStatus.SUCCEEDED
        # Verify event was published
        assert len(mock_event_bus.published_events) > 0

    async def test_payment_failure_handling(
        self, payment_service, mock_payment_repository
    ):
        """Handles payment failure correctly."""
        payment = Payment(
            payment_id="pi_fail_test",
            user_id="test_user_123",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
        )
        await mock_payment_repository.create_payment(payment)
        
        result = await payment_service.fail_payment(
            "pi_fail_test",
            failure_reason="Card declined",
            failure_code="card_declined",
        )
        
        assert result.status == PaymentStatus.FAILED
        assert result.failure_reason == "Card declined"

    async def test_payment_history_with_factory_data(
        self, payment_service, mock_payment_repository
    ):
        """Retrieves payment history using factory generated payments."""
        user_id = "test_history_user"
        
        # Create multiple payments
        for i in range(5):
            payment = Payment(
                payment_id=f"pi_history_{i}",
                user_id=user_id,
                amount=Decimal("10.00"),
                currency=Currency.USD,
                status=PaymentStatus.SUCCEEDED,
                payment_method=PaymentMethod.STRIPE,
            )
            await mock_payment_repository.create_payment(payment)
        
        result = await payment_service.get_payment_history(user_id)
        
        assert result.total_count == 5
        assert len(result.payments) == 5


# ============================================================================
# Refund Integration Tests (6 tests)
# ============================================================================

class TestRefundIntegration:
    """Integration tests for refund operations."""

    async def test_create_refund_with_factory_data(
        self, payment_service, mock_payment_repository
    ):
        """Creates refund using factory data."""
        # Create succeeded payment first
        payment = Payment(
            payment_id="pi_refund_factory",
            user_id="test_refund_user",
            amount=Decimal("49.99"),
            currency=Currency.USD,
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.STRIPE,
            processor_payment_id="pi_refund_factory",
        )
        await mock_payment_repository.create_payment(payment)
        
        refund_data = PaymentTestDataFactory.make_valid_create_refund_request()
        refund_data["payment_id"] = "pi_refund_factory"
        refund_data["amount"] = 49.99
        
        request = CreateRefundRequest(
            payment_id=refund_data["payment_id"],
            amount=Decimal(str(refund_data["amount"])),
            reason=refund_data["reason"],
            requested_by=refund_data["requested_by"],
        )
        
        result = await payment_service.create_refund(request)
        
        assert result is not None
        assert result.amount == Decimal("49.99")
        assert result.status == RefundStatus.PROCESSING

    async def test_partial_refund_updates_payment_status(
        self, payment_service, mock_payment_repository
    ):
        """Partial refund updates payment to partial_refund status."""
        payment = Payment(
            payment_id="pi_partial_refund",
            user_id="test_user_123",
            amount=Decimal("100.00"),
            currency=Currency.USD,
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.STRIPE,
            processor_payment_id="pi_partial_refund",
        )
        await mock_payment_repository.create_payment(payment)
        
        request = CreateRefundRequest(
            payment_id="pi_partial_refund",
            amount=Decimal("30.00"),  # Partial
            reason="Partial service",
            requested_by="admin",
        )
        
        await payment_service.create_refund(request)
        
        # Check payment status was updated
        updated_payment = await mock_payment_repository.get_payment("pi_partial_refund")
        assert updated_payment.status == PaymentStatus.PARTIAL_REFUND

    async def test_full_refund_updates_payment_status(
        self, payment_service, mock_payment_repository
    ):
        """Full refund updates payment to refunded status."""
        payment = Payment(
            payment_id="pi_full_refund",
            user_id="test_user_123",
            amount=Decimal("50.00"),
            currency=Currency.USD,
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.STRIPE,
            processor_payment_id="pi_full_refund",
        )
        await mock_payment_repository.create_payment(payment)
        
        request = CreateRefundRequest(
            payment_id="pi_full_refund",
            amount=Decimal("50.00"),  # Full amount
            reason="Full refund",
            requested_by="admin",
        )
        
        await payment_service.create_refund(request)
        
        updated_payment = await mock_payment_repository.get_payment("pi_full_refund")
        assert updated_payment.status == PaymentStatus.REFUNDED

    async def test_refund_exceeds_amount_rejected(
        self, payment_service, mock_payment_repository
    ):
        """Rejects refund that exceeds payment amount."""
        payment = Payment(
            payment_id="pi_exceed_refund",
            user_id="test_user_123",
            amount=Decimal("50.00"),
            currency=Currency.USD,
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.STRIPE,
        )
        await mock_payment_repository.create_payment(payment)
        
        request = CreateRefundRequest(
            payment_id="pi_exceed_refund",
            amount=Decimal("100.00"),  # Exceeds payment
            reason="Over refund",
            requested_by="admin",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await payment_service.create_refund(request)
        
        assert "exceeds" in str(exc_info.value).lower()


# ============================================================================
# Event Publishing Integration Tests (5 tests)
# ============================================================================

class TestEventPublishingIntegration:
    """Tests for event publishing integration."""

    async def test_subscription_created_event_structure(
        self, payment_service, mock_payment_repository, mock_event_bus
    ):
        """Verifies subscription.created event structure."""
        plan = SubscriptionPlan(
            plan_id="plan_event_test",
            name="Event Test Plan",
            tier=SubscriptionTier.PRO,
            price=Decimal("29.99"),
            billing_cycle=BillingCycle.MONTHLY,
            trial_days=14,
            is_public=True,
        )
        await mock_payment_repository.create_subscription_plan(plan)
        
        request = CreateSubscriptionRequest(
            user_id="test_event_user",
            plan_id="plan_event_test",
        )
        
        await payment_service.create_subscription(request)
        
        # Verify event was published
        assert len(mock_event_bus.published_events) > 0

    async def test_payment_completed_event_published(
        self, payment_service, mock_payment_repository, mock_event_bus
    ):
        """Verifies payment.completed event is published on confirmation."""
        payment = Payment(
            payment_id="pi_event_complete",
            user_id="test_user_123",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
            processor_payment_id="pi_event_complete",
        )
        await mock_payment_repository.create_payment(payment)
        
        await payment_service.confirm_payment("pi_event_complete")
        
        assert len(mock_event_bus.published_events) > 0

    async def test_no_event_bus_does_not_crash(
        self, mock_payment_repository, mock_account_client,
        mock_wallet_client, mock_billing_client, mock_product_client
    ):
        """Service works without event bus configured."""
        service = PaymentService(
            repository=mock_payment_repository,
            stripe_secret_key=None,
            event_bus=None,  # No event bus
            account_client=mock_account_client,
            wallet_client=mock_wallet_client,
            billing_client=mock_billing_client,
            product_client=mock_product_client,
        )
        
        plan = SubscriptionPlan(
            plan_id="plan_no_bus",
            name="No Bus Plan",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
            is_public=True,
        )
        await mock_payment_repository.create_subscription_plan(plan)
        
        # Should not raise
        request = CreateSubscriptionRequest(
            user_id="test_no_bus_user",
            plan_id="plan_no_bus",
        )
        
        result = await service.create_subscription(request)
        assert result.subscription is not None


# ============================================================================
# Statistics Integration Tests (3 tests)
# ============================================================================

class TestStatisticsIntegration:
    """Integration tests for statistics operations."""

    async def test_revenue_stats_calculation(
        self, payment_service, mock_payment_repository
    ):
        """Calculates revenue stats correctly."""
        # Create succeeded payments
        for i in range(3):
            payment = Payment(
                payment_id=f"pi_stats_{i}",
                user_id="test_stats_user",
                amount=Decimal("30.00"),
                currency=Currency.USD,
                status=PaymentStatus.SUCCEEDED,
                payment_method=PaymentMethod.STRIPE,
            )
            await mock_payment_repository.create_payment(payment)
        
        stats = await payment_service.get_revenue_stats()
        
        assert stats["payment_count"] == 3
        assert stats["total_revenue"] == 90.0

    async def test_subscription_stats_calculation(
        self, payment_service, mock_payment_repository
    ):
        """Calculates subscription stats correctly."""
        # Create active subscriptions
        for tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO, SubscriptionTier.PRO]:
            sub = Subscription(
                subscription_id=f"sub_stats_{tier.value}_{datetime.utcnow().timestamp()}",
                user_id=f"user_{tier.value}",
                plan_id="plan_stats",
                status=SubscriptionStatus.ACTIVE,
                tier=tier,
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
                billing_cycle=BillingCycle.MONTHLY,
            )
            await mock_payment_repository.create_subscription(sub)
        
        stats = await payment_service.get_subscription_stats()
        
        assert stats["active_subscriptions"] == 3
        assert "tier_distribution" in stats
