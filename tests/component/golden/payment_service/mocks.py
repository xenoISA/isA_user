"""
Payment Service Mocks

Mock implementations for payment_service component testing.
Implements all protocol interfaces defined in protocols.py.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../microservices/payment_service"))

from microservices.payment_service.models import (
    BillingCycle,
    Currency,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentMethodInfo,
    PaymentMethod,
    PaymentStatus,
    Refund,
    RefundStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
)


class MockPaymentRepository:
    """Mock implementation of PaymentRepositoryProtocol"""

    def __init__(self):
        self.plans: Dict[str, SubscriptionPlan] = {}
        self.subscriptions: Dict[str, Subscription] = {}
        self.payments: Dict[str, Payment] = {}
        self.invoices: Dict[str, Invoice] = {}
        self.refunds: Dict[str, Refund] = {}
        self.payment_methods: Dict[str, List[PaymentMethodInfo]] = {}
        self._connected = True
        
        # Call tracking for verification
        self.calls: List[Dict[str, Any]] = []

    def _record_call(self, method: str, **kwargs):
        """Record method call for test verification"""
        self.calls.append({"method": method, "kwargs": kwargs})

    async def check_connection(self) -> bool:
        """Check database connection"""
        self._record_call("check_connection")
        return self._connected

    # ==================== Subscription Plans ====================

    async def create_subscription_plan(
        self, plan: SubscriptionPlan
    ) -> Optional[SubscriptionPlan]:
        """Create a subscription plan"""
        self._record_call("create_subscription_plan", plan=plan)
        plan.created_at = datetime.utcnow()
        plan.updated_at = datetime.utcnow()
        self.plans[plan.plan_id] = plan
        return plan

    async def get_subscription_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """Get subscription plan by ID"""
        self._record_call("get_subscription_plan", plan_id=plan_id)
        return self.plans.get(plan_id)

    async def list_subscription_plans(
        self,
        tier: Optional[SubscriptionTier] = None,
        is_public: bool = True,
    ) -> List[SubscriptionPlan]:
        """List subscription plans"""
        self._record_call("list_subscription_plans", tier=tier, is_public=is_public)
        plans = list(self.plans.values())
        if tier:
            plans = [p for p in plans if p.tier == tier]
        if is_public:
            plans = [p for p in plans if p.is_public]
        return plans

    # ==================== Subscriptions ====================

    async def create_subscription(
        self, subscription: Subscription
    ) -> Optional[Subscription]:
        """Create a subscription"""
        self._record_call("create_subscription", subscription=subscription)
        subscription.created_at = datetime.utcnow()
        subscription.updated_at = datetime.utcnow()
        self.subscriptions[subscription.subscription_id] = subscription
        return subscription

    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID"""
        self._record_call("get_subscription", subscription_id=subscription_id)
        return self.subscriptions.get(subscription_id)

    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's current subscription"""
        self._record_call("get_user_subscription", user_id=user_id)
        for sub in self.subscriptions.values():
            if sub.user_id == user_id:
                return sub
        return None

    async def get_user_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription"""
        self._record_call("get_user_active_subscription", user_id=user_id)
        for sub in self.subscriptions.values():
            if sub.user_id == user_id and sub.status in [
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
            ]:
                return sub
        return None

    async def update_subscription(
        self,
        subscription_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Subscription]:
        """Update subscription"""
        self._record_call(
            "update_subscription", subscription_id=subscription_id, updates=updates
        )
        if subscription_id not in self.subscriptions:
            return None
        sub = self.subscriptions[subscription_id]
        for key, value in updates.items():
            if hasattr(sub, key):
                setattr(sub, key, value)
        sub.updated_at = datetime.utcnow()
        return sub

    async def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False,
        reason: Optional[str] = None,
    ) -> Optional[Subscription]:
        """Cancel subscription"""
        self._record_call(
            "cancel_subscription",
            subscription_id=subscription_id,
            immediate=immediate,
            reason=reason,
        )
        if subscription_id not in self.subscriptions:
            return None
        sub = self.subscriptions[subscription_id]
        sub.canceled_at = datetime.utcnow()
        sub.cancellation_reason = reason
        if immediate:
            sub.status = SubscriptionStatus.CANCELED
        else:
            sub.cancel_at_period_end = True
        sub.updated_at = datetime.utcnow()
        return sub

    # ==================== Payments ====================

    async def create_payment(self, payment: Payment) -> Optional[Payment]:
        """Create a payment record"""
        self._record_call("create_payment", payment=payment)
        payment.created_at = datetime.utcnow()
        self.payments[payment.payment_id] = payment
        return payment

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        self._record_call("get_payment", payment_id=payment_id)
        return self.payments.get(payment_id)

    async def update_payment_status(
        self,
        payment_id: str,
        status: PaymentStatus,
        processor_response: Optional[Dict[str, Any]] = None,
    ) -> Optional[Payment]:
        """Update payment status"""
        self._record_call(
            "update_payment_status",
            payment_id=payment_id,
            status=status,
            processor_response=processor_response,
        )
        if payment_id not in self.payments:
            return None
        payment = self.payments[payment_id]
        payment.status = status
        if processor_response:
            payment.processor_response = processor_response
        if status == PaymentStatus.SUCCEEDED:
            payment.paid_at = datetime.utcnow()
        elif status == PaymentStatus.FAILED:
            payment.failed_at = datetime.utcnow()
        return payment

    async def get_user_payments(
        self,
        user_id: str,
        limit: int = 10,
        status: Optional[PaymentStatus] = None,
    ) -> List[Payment]:
        """Get user's payment history"""
        self._record_call(
            "get_user_payments", user_id=user_id, limit=limit, status=status
        )
        payments = [p for p in self.payments.values() if p.user_id == user_id]
        if status:
            payments = [p for p in payments if p.status == status]
        return payments[:limit]

    # ==================== Payment Methods ====================

    async def save_payment_method(
        self, method: PaymentMethodInfo
    ) -> Optional[PaymentMethodInfo]:
        """Save payment method"""
        self._record_call("save_payment_method", method=method)
        method.created_at = datetime.utcnow()
        if method.user_id not in self.payment_methods:
            self.payment_methods[method.user_id] = []
        self.payment_methods[method.user_id].append(method)
        return method

    async def get_user_payment_methods(self, user_id: str) -> List[PaymentMethodInfo]:
        """Get user's payment methods"""
        self._record_call("get_user_payment_methods", user_id=user_id)
        return self.payment_methods.get(user_id, [])

    async def get_user_default_payment_method(
        self, user_id: str
    ) -> Optional[PaymentMethodInfo]:
        """Get user's default payment method"""
        self._record_call("get_user_default_payment_method", user_id=user_id)
        methods = self.payment_methods.get(user_id, [])
        for method in methods:
            if method.is_default:
                return method
        return methods[0] if methods else None

    # ==================== Invoices ====================

    async def create_invoice(self, invoice: Invoice) -> Optional[Invoice]:
        """Create an invoice"""
        self._record_call("create_invoice", invoice=invoice)
        invoice.created_at = datetime.utcnow()
        invoice.updated_at = datetime.utcnow()
        self.invoices[invoice.invoice_id] = invoice
        return invoice

    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID"""
        self._record_call("get_invoice", invoice_id=invoice_id)
        return self.invoices.get(invoice_id)

    async def mark_invoice_paid(
        self,
        invoice_id: str,
        payment_intent_id: str,
    ) -> Optional[Invoice]:
        """Mark invoice as paid"""
        self._record_call(
            "mark_invoice_paid",
            invoice_id=invoice_id,
            payment_intent_id=payment_intent_id,
        )
        if invoice_id not in self.invoices:
            return None
        invoice = self.invoices[invoice_id]
        invoice.status = InvoiceStatus.PAID
        invoice.payment_intent_id = payment_intent_id
        invoice.paid_at = datetime.utcnow()
        invoice.amount_paid = invoice.amount_total
        invoice.amount_due = Decimal("0")
        invoice.updated_at = datetime.utcnow()
        return invoice

    # ==================== Refunds ====================

    async def create_refund(self, refund: Refund) -> Optional[Refund]:
        """Create a refund"""
        self._record_call("create_refund", refund=refund)
        self.refunds[refund.refund_id] = refund
        return refund

    async def update_refund_status(
        self, refund_id: str, status: RefundStatus
    ) -> bool:
        """Update refund status"""
        self._record_call(
            "update_refund_status", refund_id=refund_id, status=status
        )
        if refund_id not in self.refunds:
            return False
        self.refunds[refund_id].status = status
        return True

    async def process_refund(
        self,
        refund_id: str,
        approved_by: Optional[str] = None,
    ) -> Optional[Refund]:
        """Process refund"""
        self._record_call(
            "process_refund", refund_id=refund_id, approved_by=approved_by
        )
        if refund_id not in self.refunds:
            return None
        refund = self.refunds[refund_id]
        refund.status = RefundStatus.SUCCEEDED
        refund.approved_by = approved_by
        refund.processed_at = datetime.utcnow()
        refund.completed_at = datetime.utcnow()
        return refund

    # ==================== Statistics ====================

    async def get_revenue_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get revenue statistics"""
        self._record_call("get_revenue_statistics", days=days)
        succeeded_payments = [
            p for p in self.payments.values()
            if p.status == PaymentStatus.SUCCEEDED
        ]
        total_revenue = sum(p.amount for p in succeeded_payments)
        return {
            "total_revenue": float(total_revenue),
            "payment_count": len(succeeded_payments),
            "average_payment": float(total_revenue / len(succeeded_payments)) if succeeded_payments else 0,
            "period_days": days,
            "daily_revenue": {},
        }

    async def get_subscription_statistics(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        self._record_call("get_subscription_statistics")
        active_subs = [
            s for s in self.subscriptions.values()
            if s.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
        ]
        tier_distribution = {}
        for sub in active_subs:
            tier = sub.tier.value
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
        return {
            "active_subscriptions": len(active_subs),
            "tier_distribution": tier_distribution,
            "churn_rate": 0.0,
            "canceled_last_30_days": 0,
        }


class MockEventBus:
    """Mock implementation of EventBusProtocol"""

    def __init__(self):
        self.published_events: List[Any] = []
        self.subscriptions: Dict[str, Any] = {}
        self._closed = False

    async def publish_event(self, event: Any) -> None:
        """Publish an event to the event bus"""
        self.published_events.append(event)

    async def subscribe_to_events(
        self, pattern: str, handler: Any, durable: str
    ) -> None:
        """Subscribe to events matching a pattern"""
        self.subscriptions[pattern] = {"handler": handler, "durable": durable}

    async def close(self) -> None:
        """Close event bus connection"""
        self._closed = True

    def get_published_events_by_type(self, event_type: str) -> List[Any]:
        """Get all published events of a specific type"""
        return [
            e for e in self.published_events
            if hasattr(e, "event_type") and e.event_type == event_type
        ]

    def clear_events(self):
        """Clear all published events"""
        self.published_events = []


class MockAccountClient:
    """Mock implementation of AccountClientProtocol"""

    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self._default_account = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "name": "Test User",
            "status": "active",
        }

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user account profile"""
        if user_id in self.accounts:
            return self.accounts[user_id]
        # Return default account for any user_id starting with "test_" or "user_"
        if user_id.startswith("test_") or user_id.startswith("user_"):
            return {**self._default_account, "user_id": user_id}
        return None

    async def validate_user(self, user_id: str) -> bool:
        """Validate user exists"""
        return await self.get_account_profile(user_id) is not None

    def add_account(self, user_id: str, profile: Dict[str, Any]):
        """Add a test account"""
        self.accounts[user_id] = profile


class MockWalletClient:
    """Mock implementation of WalletClientProtocol"""

    def __init__(self):
        self.wallets: Dict[str, Dict[str, Decimal]] = {}
        self.transactions: List[Dict[str, Any]] = []

    async def get_balance(
        self,
        user_id: str,
        wallet_type: str = "main",
    ) -> Optional[Dict[str, Any]]:
        """Get wallet balance"""
        key = f"{user_id}:{wallet_type}"
        balance = self.wallets.get(key, Decimal("0"))
        return {
            "user_id": user_id,
            "wallet_type": wallet_type,
            "balance": float(balance),
            "currency": "USD",
        }

    async def add_funds(
        self,
        user_id: str,
        wallet_type: str,
        amount: float,
        description: str,
        reference_id: str,
    ) -> Dict[str, Any]:
        """Add funds to wallet"""
        key = f"{user_id}:{wallet_type}"
        current = self.wallets.get(key, Decimal("0"))
        self.wallets[key] = current + Decimal(str(amount))
        transaction = {
            "type": "credit",
            "user_id": user_id,
            "wallet_type": wallet_type,
            "amount": amount,
            "description": description,
            "reference_id": reference_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.transactions.append(transaction)
        return {"success": True, "transaction": transaction}

    async def consume(
        self,
        user_id: str,
        wallet_type: str,
        amount: float,
        description: str,
        reference_id: str,
    ) -> Dict[str, Any]:
        """Consume from wallet"""
        key = f"{user_id}:{wallet_type}"
        current = self.wallets.get(key, Decimal("0"))
        if current < Decimal(str(amount)):
            return {"success": False, "error": "Insufficient funds"}
        self.wallets[key] = current - Decimal(str(amount))
        transaction = {
            "type": "debit",
            "user_id": user_id,
            "wallet_type": wallet_type,
            "amount": amount,
            "description": description,
            "reference_id": reference_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.transactions.append(transaction)
        return {"success": True, "transaction": transaction}


class MockBillingClient:
    """Mock implementation of BillingClientProtocol"""

    def __init__(self):
        self.usage_records: List[Dict[str, Any]] = []
        self.billing_records: Dict[str, List[Dict[str, Any]]] = {}

    async def record_usage(
        self,
        user_id: str,
        product_id: str,
        service_type: str,
        usage_amount: int,
    ) -> Dict[str, Any]:
        """Record usage for billing"""
        record = {
            "user_id": user_id,
            "product_id": product_id,
            "service_type": service_type,
            "usage_amount": usage_amount,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.usage_records.append(record)
        if user_id not in self.billing_records:
            self.billing_records[user_id] = []
        self.billing_records[user_id].append(record)
        return {"success": True, "record": record}

    async def get_billing_records(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get billing records"""
        records = self.billing_records.get(user_id, [])
        return records[:limit]


class MockProductClient:
    """Mock implementation of ProductClientProtocol"""

    def __init__(self):
        self.products: Dict[str, Dict[str, Any]] = {}
        self._default_product = {
            "product_id": "default_product",
            "name": "Default Product",
            "price": 29.99,
            "currency": "USD",
        }

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details"""
        if product_id in self.products:
            return self.products[product_id]
        return {**self._default_product, "product_id": product_id}

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: str,
        subscription_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get product pricing information"""
        product = await self.get_product(product_id)
        if not product:
            return None
        discount = 0.0
        if subscription_id:
            discount = 0.10  # 10% discount for subscribers
        return {
            "product_id": product_id,
            "user_id": user_id,
            "base_price": product["price"],
            "discount": discount,
            "final_price": product["price"] * (1 - discount),
            "currency": product["currency"],
        }

    def add_product(self, product_id: str, product: Dict[str, Any]):
        """Add a test product"""
        self.products[product_id] = product
