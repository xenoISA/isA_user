"""
Unit Golden Tests: Payment Service Models

Tests model validation and serialization without external dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import ValidationError

from microservices.payment_service.models import (
    # Enums
    PaymentStatus,
    PaymentMethod,
    SubscriptionStatus,
    SubscriptionTier,
    BillingCycle,
    InvoiceStatus,
    RefundStatus,
    Currency,
    # Core Models
    SubscriptionPlan,
    Subscription,
    Payment,
    Invoice,
    Refund,
    PaymentMethodInfo,
    # Request Models
    CreatePaymentIntentRequest,
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    CancelSubscriptionRequest,
    CreateRefundRequest,
    # Response Models
    PaymentIntentResponse,
    SubscriptionResponse,
    PaymentHistoryResponse,
    InvoiceResponse,
)


# ====================
# Enum Tests
# ====================

class TestPaymentStatus:
    """Test PaymentStatus enum"""

    def test_payment_status_values(self):
        """Test all payment status values are defined"""
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.PROCESSING.value == "processing"
        assert PaymentStatus.SUCCEEDED.value == "succeeded"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.CANCELED.value == "canceled"
        assert PaymentStatus.REFUNDED.value == "refunded"
        assert PaymentStatus.PARTIAL_REFUND.value == "partial_refund"

    def test_payment_status_comparison(self):
        """Test payment status comparison"""
        assert PaymentStatus.PENDING != PaymentStatus.SUCCEEDED
        assert PaymentStatus.PENDING.value == "pending"


class TestPaymentMethod:
    """Test PaymentMethod enum"""

    def test_payment_method_values(self):
        """Test all payment method values"""
        assert PaymentMethod.CREDIT_CARD.value == "credit_card"
        assert PaymentMethod.DEBIT_CARD.value == "debit_card"
        assert PaymentMethod.ALIPAY.value == "alipay"
        assert PaymentMethod.WECHAT_PAY.value == "wechat_pay"
        assert PaymentMethod.BANK_TRANSFER.value == "bank_transfer"
        assert PaymentMethod.STRIPE.value == "stripe"
        assert PaymentMethod.PAYPAL.value == "paypal"


class TestSubscriptionStatus:
    """Test SubscriptionStatus enum"""

    def test_subscription_status_values(self):
        """Test all subscription status values"""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.PAST_DUE.value == "past_due"
        assert SubscriptionStatus.CANCELED.value == "canceled"
        assert SubscriptionStatus.INCOMPLETE.value == "incomplete"
        assert SubscriptionStatus.INCOMPLETE_EXPIRED.value == "incomplete_expired"
        assert SubscriptionStatus.TRIALING.value == "trialing"
        assert SubscriptionStatus.UNPAID.value == "unpaid"
        assert SubscriptionStatus.PAUSED.value == "paused"


class TestSubscriptionTier:
    """Test SubscriptionTier enum"""

    def test_subscription_tier_values(self):
        """Test all subscription tier values"""
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.BASIC.value == "basic"
        assert SubscriptionTier.PRO.value == "pro"
        assert SubscriptionTier.ENTERPRISE.value == "enterprise"
        assert SubscriptionTier.CUSTOM.value == "custom"


class TestBillingCycle:
    """Test BillingCycle enum"""

    def test_billing_cycle_values(self):
        """Test all billing cycle values"""
        assert BillingCycle.MONTHLY.value == "monthly"
        assert BillingCycle.QUARTERLY.value == "quarterly"
        assert BillingCycle.YEARLY.value == "yearly"
        assert BillingCycle.ONE_TIME.value == "one_time"


class TestInvoiceStatus:
    """Test InvoiceStatus enum"""

    def test_invoice_status_values(self):
        """Test all invoice status values"""
        assert InvoiceStatus.DRAFT.value == "draft"
        assert InvoiceStatus.OPEN.value == "open"
        assert InvoiceStatus.PAID.value == "paid"
        assert InvoiceStatus.VOID.value == "void"
        assert InvoiceStatus.UNCOLLECTIBLE.value == "uncollectible"


class TestRefundStatus:
    """Test RefundStatus enum"""

    def test_refund_status_values(self):
        """Test all refund status values"""
        assert RefundStatus.PENDING.value == "pending"
        assert RefundStatus.PROCESSING.value == "processing"
        assert RefundStatus.SUCCEEDED.value == "succeeded"
        assert RefundStatus.FAILED.value == "failed"
        assert RefundStatus.CANCELED.value == "canceled"


class TestCurrency:
    """Test Currency enum"""

    def test_currency_values(self):
        """Test all currency values"""
        assert Currency.USD.value == "USD"
        assert Currency.EUR.value == "EUR"
        assert Currency.GBP.value == "GBP"
        assert Currency.CNY.value == "CNY"
        assert Currency.JPY.value == "JPY"


# ====================
# Core Model Tests
# ====================

class TestSubscriptionPlan:
    """Test SubscriptionPlan model"""

    def test_subscription_plan_creation_with_all_fields(self):
        """Test creating subscription plan with all fields"""
        now = datetime.now(timezone.utc)

        plan = SubscriptionPlan(
            id="plan_db_123",
            plan_id="plan_pro_monthly",
            name="Pro Monthly",
            description="Professional plan billed monthly",
            tier=SubscriptionTier.PRO,
            price=Decimal("29.99"),
            currency=Currency.USD,
            billing_cycle=BillingCycle.MONTHLY,
            features={"storage_gb": 100, "users": 5, "api_calls": 10000},
            credits_included=1000,
            max_users=5,
            max_storage_gb=100,
            trial_days=14,
            stripe_price_id="price_stripe_123",
            stripe_product_id="prod_stripe_456",
            is_active=True,
            is_public=True,
            created_at=now,
            updated_at=now,
        )

        assert plan.plan_id == "plan_pro_monthly"
        assert plan.name == "Pro Monthly"
        assert plan.tier == SubscriptionTier.PRO
        assert plan.price == Decimal("29.99")
        assert plan.currency == Currency.USD
        assert plan.billing_cycle == BillingCycle.MONTHLY
        assert plan.credits_included == 1000
        assert plan.trial_days == 14
        assert plan.is_active is True

    def test_subscription_plan_with_minimal_fields(self):
        """Test creating subscription plan with only required fields"""
        plan = SubscriptionPlan(
            plan_id="plan_basic",
            name="Basic Plan",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
        )

        assert plan.plan_id == "plan_basic"
        assert plan.tier == SubscriptionTier.BASIC
        assert plan.price == Decimal("9.99")
        assert plan.currency == Currency.USD
        assert plan.credits_included == 0
        assert plan.trial_days == 0
        assert plan.is_active is True
        assert plan.is_public is True

    def test_subscription_plan_free_tier(self):
        """Test free tier subscription plan"""
        plan = SubscriptionPlan(
            plan_id="plan_free",
            name="Free Plan",
            tier=SubscriptionTier.FREE,
            price=Decimal("0.00"),
            billing_cycle=BillingCycle.MONTHLY,
            features={"storage_gb": 1, "users": 1},
        )

        assert plan.tier == SubscriptionTier.FREE
        assert plan.price == Decimal("0.00")

    def test_subscription_plan_negative_price_validation(self):
        """Test that negative prices are rejected"""
        with pytest.raises(ValidationError):
            SubscriptionPlan(
                plan_id="plan_invalid",
                name="Invalid Plan",
                tier=SubscriptionTier.BASIC,
                price=Decimal("-10.00"),
                billing_cycle=BillingCycle.MONTHLY,
            )

    def test_subscription_plan_enterprise_tier(self):
        """Test enterprise tier with custom features"""
        plan = SubscriptionPlan(
            plan_id="plan_enterprise",
            name="Enterprise Plan",
            tier=SubscriptionTier.ENTERPRISE,
            price=Decimal("299.99"),
            currency=Currency.EUR,
            billing_cycle=BillingCycle.YEARLY,
            features={
                "storage_gb": 1000,
                "users": 50,
                "api_calls": 1000000,
                "sla": "99.9%",
                "support": "24/7",
            },
            credits_included=100000,
        )

        assert plan.tier == SubscriptionTier.ENTERPRISE
        assert plan.currency == Currency.EUR
        assert plan.billing_cycle == BillingCycle.YEARLY
        assert plan.features["support"] == "24/7"


class TestSubscription:
    """Test Subscription model"""

    def test_subscription_creation_with_all_fields(self):
        """Test creating subscription with all fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        subscription = Subscription(
            id="sub_db_123",
            subscription_id="sub_user_pro_123",
            user_id="user_456",
            organization_id="org_789",
            plan_id="plan_pro_monthly",
            status=SubscriptionStatus.ACTIVE,
            tier=SubscriptionTier.PRO,
            current_period_start=now,
            current_period_end=future,
            billing_cycle=BillingCycle.MONTHLY,
            trial_start=now,
            trial_end=now + timedelta(days=14),
            cancel_at_period_end=False,
            canceled_at=None,
            cancellation_reason=None,
            payment_method_id="pm_123",
            last_payment_date=now,
            next_payment_date=future,
            stripe_subscription_id="sub_stripe_xyz",
            stripe_customer_id="cus_stripe_abc",
            metadata={"source": "website"},
            created_at=now,
            updated_at=now,
        )

        assert subscription.subscription_id == "sub_user_pro_123"
        assert subscription.user_id == "user_456"
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.tier == SubscriptionTier.PRO
        assert subscription.billing_cycle == BillingCycle.MONTHLY
        assert subscription.cancel_at_period_end is False

    def test_subscription_with_minimal_fields(self):
        """Test creating subscription with only required fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        subscription = Subscription(
            subscription_id="sub_minimal",
            user_id="user_123",
            plan_id="plan_basic",
            status=SubscriptionStatus.ACTIVE,
            tier=SubscriptionTier.BASIC,
            current_period_start=now,
            current_period_end=future,
            billing_cycle=BillingCycle.MONTHLY,
        )

        assert subscription.subscription_id == "sub_minimal"
        assert subscription.cancel_at_period_end is False
        assert subscription.canceled_at is None

    def test_subscription_trialing_status(self):
        """Test subscription in trial period"""
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=14)
        period_end = now + timedelta(days=44)

        subscription = Subscription(
            subscription_id="sub_trial",
            user_id="user_123",
            plan_id="plan_pro",
            status=SubscriptionStatus.TRIALING,
            tier=SubscriptionTier.PRO,
            current_period_start=now,
            current_period_end=period_end,
            billing_cycle=BillingCycle.MONTHLY,
            trial_start=now,
            trial_end=trial_end,
        )

        assert subscription.status == SubscriptionStatus.TRIALING
        assert subscription.trial_start is not None
        assert subscription.trial_end is not None

    def test_subscription_canceled(self):
        """Test canceled subscription"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        subscription = Subscription(
            subscription_id="sub_canceled",
            user_id="user_123",
            plan_id="plan_basic",
            status=SubscriptionStatus.CANCELED,
            tier=SubscriptionTier.BASIC,
            current_period_start=now - timedelta(days=30),
            current_period_end=now,
            billing_cycle=BillingCycle.MONTHLY,
            cancel_at_period_end=True,
            canceled_at=now,
            cancellation_reason="Too expensive",
        )

        assert subscription.status == SubscriptionStatus.CANCELED
        assert subscription.cancel_at_period_end is True
        assert subscription.canceled_at is not None
        assert subscription.cancellation_reason == "Too expensive"


class TestPayment:
    """Test Payment model"""

    def test_payment_creation_with_all_fields(self):
        """Test creating payment with all fields"""
        now = datetime.now(timezone.utc)

        payment = Payment(
            id="pay_db_123",
            payment_id="pay_user_456_001",
            user_id="user_456",
            organization_id="org_789",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            description="Pro Plan - Monthly subscription",
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.CREDIT_CARD,
            subscription_id="sub_123",
            invoice_id="inv_123",
            processor="stripe",
            processor_payment_id="pi_stripe_xyz",
            processor_response={"status": "succeeded", "receipt_url": "https://..."},
            failure_reason=None,
            failure_code=None,
            created_at=now,
            paid_at=now,
            failed_at=None,
        )

        assert payment.payment_id == "pay_user_456_001"
        assert payment.amount == Decimal("29.99")
        assert payment.currency == Currency.USD
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.payment_method == PaymentMethod.CREDIT_CARD
        assert payment.processor == "stripe"

    def test_payment_with_minimal_fields(self):
        """Test creating payment with only required fields"""
        payment = Payment(
            payment_id="pay_minimal",
            user_id="user_123",
            amount=Decimal("9.99"),
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
        )

        assert payment.payment_id == "pay_minimal"
        assert payment.amount == Decimal("9.99")
        assert payment.currency == Currency.USD
        assert payment.processor == "stripe"

    def test_payment_failed(self):
        """Test failed payment"""
        now = datetime.now(timezone.utc)

        payment = Payment(
            payment_id="pay_failed",
            user_id="user_123",
            amount=Decimal("19.99"),
            status=PaymentStatus.FAILED,
            payment_method=PaymentMethod.CREDIT_CARD,
            failure_reason="Insufficient funds",
            failure_code="card_declined",
            created_at=now,
            failed_at=now,
        )

        assert payment.status == PaymentStatus.FAILED
        assert payment.failure_reason == "Insufficient funds"
        assert payment.failure_code == "card_declined"

    def test_payment_negative_amount_validation(self):
        """Test that negative amounts are rejected"""
        with pytest.raises(ValidationError):
            Payment(
                payment_id="pay_invalid",
                user_id="user_123",
                amount=Decimal("-10.00"),
                status=PaymentStatus.PENDING,
                payment_method=PaymentMethod.STRIPE,
            )

    def test_payment_different_currencies(self):
        """Test payment with different currencies"""
        payment_eur = Payment(
            payment_id="pay_eur",
            user_id="user_123",
            amount=Decimal("25.00"),
            currency=Currency.EUR,
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.STRIPE,
        )

        payment_cny = Payment(
            payment_id="pay_cny",
            user_id="user_456",
            amount=Decimal("199.00"),
            currency=Currency.CNY,
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.ALIPAY,
        )

        assert payment_eur.currency == Currency.EUR
        assert payment_cny.currency == Currency.CNY
        assert payment_cny.payment_method == PaymentMethod.ALIPAY


class TestInvoice:
    """Test Invoice model"""

    def test_invoice_creation_with_all_fields(self):
        """Test creating invoice with all fields"""
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=30)
        period_end = now

        invoice = Invoice(
            id="inv_db_123",
            invoice_id="inv_user_456_001",
            invoice_number="INV-2023-001",
            user_id="user_456",
            organization_id="org_789",
            subscription_id="sub_123",
            status=InvoiceStatus.PAID,
            amount_total=Decimal("29.99"),
            amount_paid=Decimal("29.99"),
            amount_due=Decimal("0.00"),
            currency=Currency.USD,
            billing_period_start=period_start,
            billing_period_end=period_end,
            payment_method_id="pm_123",
            payment_intent_id="pi_123",
            line_items=[
                {"description": "Pro Plan", "amount": Decimal("29.99")},
            ],
            stripe_invoice_id="in_stripe_xyz",
            due_date=now + timedelta(days=7),
            paid_at=now,
            created_at=now - timedelta(days=1),
            updated_at=now,
        )

        assert invoice.invoice_id == "inv_user_456_001"
        assert invoice.invoice_number == "INV-2023-001"
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.amount_total == Decimal("29.99")
        assert invoice.amount_paid == Decimal("29.99")
        assert invoice.amount_due == Decimal("0.00")

    def test_invoice_with_minimal_fields(self):
        """Test creating invoice with only required fields"""
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=30)

        invoice = Invoice(
            invoice_id="inv_minimal",
            invoice_number="INV-MIN-001",
            user_id="user_123",
            status=InvoiceStatus.OPEN,
            amount_total=Decimal("9.99"),
            amount_due=Decimal("9.99"),
            billing_period_start=period_start,
            billing_period_end=now,
        )

        assert invoice.invoice_id == "inv_minimal"
        assert invoice.status == InvoiceStatus.OPEN
        assert invoice.amount_paid == Decimal("0")
        assert invoice.currency == Currency.USD

    def test_invoice_open_status(self):
        """Test invoice with open status"""
        now = datetime.now(timezone.utc)

        invoice = Invoice(
            invoice_id="inv_open",
            invoice_number="INV-OPEN-001",
            user_id="user_123",
            status=InvoiceStatus.OPEN,
            amount_total=Decimal("49.99"),
            amount_due=Decimal("49.99"),
            billing_period_start=now - timedelta(days=30),
            billing_period_end=now,
            due_date=now + timedelta(days=14),
        )

        assert invoice.status == InvoiceStatus.OPEN
        assert invoice.amount_due == Decimal("49.99")
        assert invoice.paid_at is None

    def test_invoice_with_line_items(self):
        """Test invoice with multiple line items"""
        now = datetime.now(timezone.utc)

        line_items = [
            {
                "description": "Pro Plan Subscription",
                "amount": Decimal("29.99"),
                "quantity": 1,
            },
            {
                "description": "Additional Storage",
                "amount": Decimal("10.00"),
                "quantity": 2,
            },
        ]

        invoice = Invoice(
            invoice_id="inv_items",
            invoice_number="INV-ITEMS-001",
            user_id="user_123",
            status=InvoiceStatus.OPEN,
            amount_total=Decimal("49.99"),
            amount_due=Decimal("49.99"),
            billing_period_start=now - timedelta(days=30),
            billing_period_end=now,
            line_items=line_items,
        )

        assert len(invoice.line_items) == 2
        assert invoice.line_items[0]["description"] == "Pro Plan Subscription"
        assert invoice.line_items[1]["amount"] == Decimal("10.00")


class TestRefund:
    """Test Refund model"""

    def test_refund_creation_with_all_fields(self):
        """Test creating refund with all fields"""
        now = datetime.now(timezone.utc)

        refund = Refund(
            id="ref_db_123",
            refund_id="ref_pay_456_001",
            payment_id="pay_456",
            user_id="user_123",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            reason="Customer requested cancellation",
            status=RefundStatus.SUCCEEDED,
            processor="stripe",
            processor_refund_id="re_stripe_xyz",
            processor_response={"status": "succeeded"},
            requested_by="user_123",
            approved_by="admin_789",
            requested_at=now - timedelta(hours=2),
            processed_at=now - timedelta(hours=1),
            completed_at=now,
        )

        assert refund.refund_id == "ref_pay_456_001"
        assert refund.payment_id == "pay_456"
        assert refund.amount == Decimal("29.99")
        assert refund.status == RefundStatus.SUCCEEDED
        assert refund.reason == "Customer requested cancellation"

    def test_refund_with_minimal_fields(self):
        """Test creating refund with only required fields"""
        refund = Refund(
            refund_id="ref_minimal",
            payment_id="pay_123",
            user_id="user_123",
            amount=Decimal("9.99"),
            status=RefundStatus.PENDING,
        )

        assert refund.refund_id == "ref_minimal"
        assert refund.amount == Decimal("9.99")
        assert refund.currency == Currency.USD
        assert refund.processor == "stripe"

    def test_refund_pending_status(self):
        """Test refund with pending status"""
        now = datetime.now(timezone.utc)

        refund = Refund(
            refund_id="ref_pending",
            payment_id="pay_123",
            user_id="user_123",
            amount=Decimal("19.99"),
            reason="Duplicate charge",
            status=RefundStatus.PENDING,
            requested_by="user_123",
            requested_at=now,
        )

        assert refund.status == RefundStatus.PENDING
        assert refund.processed_at is None
        assert refund.completed_at is None

    def test_refund_negative_amount_validation(self):
        """Test that negative refund amounts are rejected"""
        with pytest.raises(ValidationError):
            Refund(
                refund_id="ref_invalid",
                payment_id="pay_123",
                user_id="user_123",
                amount=Decimal("-10.00"),
                status=RefundStatus.PENDING,
            )

    def test_refund_failed_status(self):
        """Test refund with failed status"""
        now = datetime.now(timezone.utc)

        refund = Refund(
            refund_id="ref_failed",
            payment_id="pay_123",
            user_id="user_123",
            amount=Decimal("29.99"),
            reason="Customer dispute",
            status=RefundStatus.FAILED,
            processor_response={"error": "insufficient_funds"},
            requested_at=now - timedelta(hours=1),
            processed_at=now,
        )

        assert refund.status == RefundStatus.FAILED
        assert refund.completed_at is None


class TestPaymentMethodInfo:
    """Test PaymentMethodInfo model"""

    def test_payment_method_credit_card(self):
        """Test payment method with credit card info"""
        now = datetime.now(timezone.utc)

        payment_method = PaymentMethodInfo(
            id="pm_db_123",
            user_id="user_456",
            method_type=PaymentMethod.CREDIT_CARD,
            card_brand="Visa",
            card_last4="4242",
            card_exp_month=12,
            card_exp_year=2025,
            stripe_payment_method_id="pm_stripe_xyz",
            is_default=True,
            is_verified=True,
            created_at=now,
        )

        assert payment_method.user_id == "user_456"
        assert payment_method.method_type == PaymentMethod.CREDIT_CARD
        assert payment_method.card_brand == "Visa"
        assert payment_method.card_last4 == "4242"
        assert payment_method.is_default is True

    def test_payment_method_bank_transfer(self):
        """Test payment method with bank transfer info"""
        payment_method = PaymentMethodInfo(
            user_id="user_123",
            method_type=PaymentMethod.BANK_TRANSFER,
            bank_name="Chase Bank",
            bank_account_last4="5678",
            is_verified=True,
        )

        assert payment_method.method_type == PaymentMethod.BANK_TRANSFER
        assert payment_method.bank_name == "Chase Bank"
        assert payment_method.bank_account_last4 == "5678"

    def test_payment_method_alipay(self):
        """Test payment method with Alipay"""
        payment_method = PaymentMethodInfo(
            user_id="user_123",
            method_type=PaymentMethod.ALIPAY,
            external_account_id="alipay_user_abc",
            is_verified=True,
        )

        assert payment_method.method_type == PaymentMethod.ALIPAY
        assert payment_method.external_account_id == "alipay_user_abc"

    def test_payment_method_defaults(self):
        """Test payment method default values"""
        payment_method = PaymentMethodInfo(
            user_id="user_123",
            method_type=PaymentMethod.STRIPE,
        )

        assert payment_method.is_default is False
        assert payment_method.is_verified is False


# ====================
# Request Model Tests
# ====================

class TestCreatePaymentIntentRequest:
    """Test CreatePaymentIntentRequest model"""

    def test_create_payment_intent_request_with_all_fields(self):
        """Test creating payment intent request with all fields"""
        request = CreatePaymentIntentRequest(
            amount=Decimal("29.99"),
            currency=Currency.USD,
            description="Pro Plan subscription",
            user_id="user_456",
            payment_method_id="pm_123",
            metadata={"subscription_id": "sub_123"},
        )

        assert request.amount == Decimal("29.99")
        assert request.currency == Currency.USD
        assert request.description == "Pro Plan subscription"
        assert request.user_id == "user_456"
        assert request.payment_method_id == "pm_123"

    def test_create_payment_intent_request_minimal(self):
        """Test creating payment intent request with minimal fields"""
        request = CreatePaymentIntentRequest(
            amount=Decimal("9.99"),
            user_id="user_123",
        )

        assert request.amount == Decimal("9.99")
        assert request.currency == Currency.USD
        assert request.description is None

    def test_create_payment_intent_negative_amount_validation(self):
        """Test that negative amounts are rejected"""
        with pytest.raises(ValidationError):
            CreatePaymentIntentRequest(
                amount=Decimal("-10.00"),
                user_id="user_123",
            )


class TestCreateSubscriptionRequest:
    """Test CreateSubscriptionRequest model"""

    def test_create_subscription_request_with_all_fields(self):
        """Test creating subscription request with all fields"""
        request = CreateSubscriptionRequest(
            user_id="user_456",
            plan_id="plan_pro_monthly",
            payment_method_id="pm_123",
            trial_days=14,
            metadata={"source": "website"},
        )

        assert request.user_id == "user_456"
        assert request.plan_id == "plan_pro_monthly"
        assert request.payment_method_id == "pm_123"
        assert request.trial_days == 14

    def test_create_subscription_request_minimal(self):
        """Test creating subscription request with minimal fields"""
        request = CreateSubscriptionRequest(
            user_id="user_123",
            plan_id="plan_basic",
        )

        assert request.user_id == "user_123"
        assert request.plan_id == "plan_basic"
        assert request.payment_method_id is None
        assert request.trial_days is None


class TestUpdateSubscriptionRequest:
    """Test UpdateSubscriptionRequest model"""

    def test_update_subscription_request_plan_change(self):
        """Test updating subscription to different plan"""
        request = UpdateSubscriptionRequest(
            plan_id="plan_pro_yearly",
        )

        assert request.plan_id == "plan_pro_yearly"
        assert request.payment_method_id is None
        assert request.cancel_at_period_end is None

    def test_update_subscription_request_payment_method(self):
        """Test updating subscription payment method"""
        request = UpdateSubscriptionRequest(
            payment_method_id="pm_new_456",
        )

        assert request.payment_method_id == "pm_new_456"

    def test_update_subscription_request_cancel_at_period_end(self):
        """Test setting subscription to cancel at period end"""
        request = UpdateSubscriptionRequest(
            cancel_at_period_end=True,
        )

        assert request.cancel_at_period_end is True

    def test_update_subscription_request_all_fields(self):
        """Test updating subscription with all fields"""
        request = UpdateSubscriptionRequest(
            plan_id="plan_enterprise",
            payment_method_id="pm_789",
            cancel_at_period_end=False,
            metadata={"updated_by": "admin"},
        )

        assert request.plan_id == "plan_enterprise"
        assert request.payment_method_id == "pm_789"
        assert request.cancel_at_period_end is False


class TestCancelSubscriptionRequest:
    """Test CancelSubscriptionRequest model"""

    def test_cancel_subscription_request_immediate(self):
        """Test immediate subscription cancellation"""
        request = CancelSubscriptionRequest(
            immediate=True,
            reason="No longer needed",
            feedback="Service was great but we're downsizing",
        )

        assert request.immediate is True
        assert request.reason == "No longer needed"
        assert request.feedback == "Service was great but we're downsizing"

    def test_cancel_subscription_request_at_period_end(self):
        """Test cancellation at period end"""
        request = CancelSubscriptionRequest(
            immediate=False,
            reason="Switching to competitor",
        )

        assert request.immediate is False
        assert request.reason == "Switching to competitor"

    def test_cancel_subscription_request_defaults(self):
        """Test cancel subscription request defaults"""
        request = CancelSubscriptionRequest()

        assert request.immediate is False
        assert request.reason is None
        assert request.feedback is None


class TestCreateRefundRequest:
    """Test CreateRefundRequest model"""

    def test_create_refund_request_full_refund(self):
        """Test creating full refund request"""
        request = CreateRefundRequest(
            payment_id="pay_123",
            reason="Customer requested refund",
            requested_by="user_123",
        )

        assert request.payment_id == "pay_123"
        assert request.amount is None
        assert request.reason == "Customer requested refund"
        assert request.requested_by == "user_123"

    def test_create_refund_request_partial_refund(self):
        """Test creating partial refund request"""
        request = CreateRefundRequest(
            payment_id="pay_456",
            amount=Decimal("10.00"),
            reason="Partial service delivery",
            requested_by="admin_789",
        )

        assert request.payment_id == "pay_456"
        assert request.amount == Decimal("10.00")
        assert request.reason == "Partial service delivery"


# ====================
# Response Model Tests
# ====================

class TestPaymentIntentResponse:
    """Test PaymentIntentResponse model"""

    def test_payment_intent_response_with_all_fields(self):
        """Test creating payment intent response with all fields"""
        response = PaymentIntentResponse(
            payment_intent_id="pi_123",
            client_secret="pi_123_secret_xyz",
            amount=Decimal("29.99"),
            currency=Currency.USD,
            status=PaymentStatus.SUCCEEDED,
            metadata={"subscription_id": "sub_123"},
        )

        assert response.payment_intent_id == "pi_123"
        assert response.client_secret == "pi_123_secret_xyz"
        assert response.amount == Decimal("29.99")
        assert response.currency == Currency.USD
        assert response.status == PaymentStatus.SUCCEEDED

    def test_payment_intent_response_without_client_secret(self):
        """Test payment intent response without Stripe client secret"""
        response = PaymentIntentResponse(
            payment_intent_id="pi_local_123",
            amount=Decimal("9.99"),
            currency=Currency.EUR,
            status=PaymentStatus.PENDING,
        )

        assert response.payment_intent_id == "pi_local_123"
        assert response.client_secret is None
        assert response.currency == Currency.EUR


class TestSubscriptionResponse:
    """Test SubscriptionResponse model"""

    def test_subscription_response_complete(self):
        """Test complete subscription response with all nested objects"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        plan = SubscriptionPlan(
            plan_id="plan_pro",
            name="Pro Plan",
            tier=SubscriptionTier.PRO,
            price=Decimal("29.99"),
            billing_cycle=BillingCycle.MONTHLY,
        )

        subscription = Subscription(
            subscription_id="sub_123",
            user_id="user_456",
            plan_id="plan_pro",
            status=SubscriptionStatus.ACTIVE,
            tier=SubscriptionTier.PRO,
            current_period_start=now,
            current_period_end=future,
            billing_cycle=BillingCycle.MONTHLY,
        )

        invoice = Invoice(
            invoice_id="inv_next",
            invoice_number="INV-NEXT-001",
            user_id="user_456",
            status=InvoiceStatus.DRAFT,
            amount_total=Decimal("29.99"),
            amount_due=Decimal("29.99"),
            billing_period_start=future,
            billing_period_end=future + timedelta(days=30),
        )

        payment_method = PaymentMethodInfo(
            user_id="user_456",
            method_type=PaymentMethod.CREDIT_CARD,
            card_brand="Visa",
            card_last4="4242",
        )

        response = SubscriptionResponse(
            subscription=subscription,
            plan=plan,
            next_invoice=invoice,
            payment_method=payment_method,
        )

        assert response.subscription.subscription_id == "sub_123"
        assert response.plan.plan_id == "plan_pro"
        assert response.next_invoice is not None
        assert response.next_invoice.invoice_id == "inv_next"
        assert response.payment_method is not None
        assert response.payment_method.card_last4 == "4242"

    def test_subscription_response_minimal(self):
        """Test subscription response with minimal fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        plan = SubscriptionPlan(
            plan_id="plan_basic",
            name="Basic Plan",
            tier=SubscriptionTier.BASIC,
            price=Decimal("9.99"),
            billing_cycle=BillingCycle.MONTHLY,
        )

        subscription = Subscription(
            subscription_id="sub_minimal",
            user_id="user_123",
            plan_id="plan_basic",
            status=SubscriptionStatus.ACTIVE,
            tier=SubscriptionTier.BASIC,
            current_period_start=now,
            current_period_end=future,
            billing_cycle=BillingCycle.MONTHLY,
        )

        response = SubscriptionResponse(
            subscription=subscription,
            plan=plan,
        )

        assert response.subscription.subscription_id == "sub_minimal"
        assert response.plan.name == "Basic Plan"
        assert response.next_invoice is None
        assert response.payment_method is None


class TestPaymentHistoryResponse:
    """Test PaymentHistoryResponse model"""

    def test_payment_history_response_with_payments(self):
        """Test payment history response with multiple payments"""
        payments = [
            Payment(
                payment_id=f"pay_{i}",
                user_id="user_123",
                amount=Decimal("29.99"),
                status=PaymentStatus.SUCCEEDED,
                payment_method=PaymentMethod.CREDIT_CARD,
            )
            for i in range(3)
        ]

        response = PaymentHistoryResponse(
            payments=payments,
            total_count=3,
            total_amount=Decimal("89.97"),
            filters_applied={"status": "succeeded", "user_id": "user_123"},
        )

        assert len(response.payments) == 3
        assert response.total_count == 3
        assert response.total_amount == Decimal("89.97")
        assert response.filters_applied["status"] == "succeeded"

    def test_payment_history_response_empty(self):
        """Test payment history response with no payments"""
        response = PaymentHistoryResponse(
            payments=[],
            total_count=0,
            total_amount=Decimal("0.00"),
            filters_applied={},
        )

        assert len(response.payments) == 0
        assert response.total_count == 0
        assert response.total_amount == Decimal("0.00")


class TestInvoiceResponse:
    """Test InvoiceResponse model"""

    def test_invoice_response_with_payment(self):
        """Test invoice response with payment details"""
        now = datetime.now(timezone.utc)

        invoice = Invoice(
            invoice_id="inv_123",
            invoice_number="INV-2023-001",
            user_id="user_456",
            status=InvoiceStatus.PAID,
            amount_total=Decimal("29.99"),
            amount_paid=Decimal("29.99"),
            amount_due=Decimal("0.00"),
            billing_period_start=now - timedelta(days=30),
            billing_period_end=now,
        )

        payment = Payment(
            payment_id="pay_123",
            user_id="user_456",
            amount=Decimal("29.99"),
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethod.CREDIT_CARD,
            invoice_id="inv_123",
        )

        response = InvoiceResponse(
            invoice=invoice,
            payment=payment,
            download_url="https://example.com/invoices/inv_123.pdf",
        )

        assert response.invoice.invoice_id == "inv_123"
        assert response.invoice.status == InvoiceStatus.PAID
        assert response.payment is not None
        assert response.payment.payment_id == "pay_123"
        assert response.download_url is not None

    def test_invoice_response_unpaid(self):
        """Test invoice response for unpaid invoice"""
        now = datetime.now(timezone.utc)

        invoice = Invoice(
            invoice_id="inv_unpaid",
            invoice_number="INV-2023-002",
            user_id="user_123",
            status=InvoiceStatus.OPEN,
            amount_total=Decimal("9.99"),
            amount_due=Decimal("9.99"),
            billing_period_start=now - timedelta(days=30),
            billing_period_end=now,
        )

        response = InvoiceResponse(
            invoice=invoice,
        )

        assert response.invoice.status == InvoiceStatus.OPEN
        assert response.payment is None
        assert response.download_url is None


if __name__ == "__main__":
    pytest.main([__file__])
