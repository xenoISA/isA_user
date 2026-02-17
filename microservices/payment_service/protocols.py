"""
Payment Service Protocols

Defines interfaces for dependency injection and testing.
Following the protocol-based architecture pattern.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from .models import (
    BillingCycle,
    Currency,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentMethodInfo,
    PaymentStatus,
    Refund,
    RefundStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
)


# ====================
# Repository Protocol
# ====================


class PaymentRepositoryProtocol(Protocol):
    """Protocol for payment data repository"""

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...

    # Subscription Plans
    async def create_subscription_plan(
        self, plan: SubscriptionPlan
    ) -> Optional[SubscriptionPlan]:
        """Create a subscription plan"""
        ...

    async def get_subscription_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """Get subscription plan by ID"""
        ...

    async def list_subscription_plans(
        self,
        tier: Optional[SubscriptionTier] = None,
        is_public: bool = True,
    ) -> List[SubscriptionPlan]:
        """List subscription plans"""
        ...

    # Subscriptions
    async def create_subscription(
        self, subscription: Subscription
    ) -> Optional[Subscription]:
        """Create a subscription"""
        ...

    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID"""
        ...

    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's current subscription"""
        ...

    async def get_user_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription"""
        ...

    async def update_subscription(
        self,
        subscription_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Subscription]:
        """Update subscription"""
        ...

    async def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False,
        reason: Optional[str] = None,
    ) -> Optional[Subscription]:
        """Cancel subscription"""
        ...

    # Payments
    async def create_payment(self, payment: Payment) -> Optional[Payment]:
        """Create a payment record"""
        ...

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        ...

    async def update_payment_status(
        self,
        payment_id: str,
        status: PaymentStatus,
        processor_response: Optional[Dict[str, Any]] = None,
    ) -> Optional[Payment]:
        """Update payment status"""
        ...

    async def get_user_payments(
        self,
        user_id: str,
        limit: int = 10,
        status: Optional[PaymentStatus] = None,
    ) -> List[Payment]:
        """Get user's payment history"""
        ...

    # Payment Methods
    async def save_payment_method(
        self, method: PaymentMethodInfo
    ) -> Optional[PaymentMethodInfo]:
        """Save payment method"""
        ...

    async def get_user_payment_methods(self, user_id: str) -> List[PaymentMethodInfo]:
        """Get user's payment methods"""
        ...

    async def get_user_default_payment_method(
        self, user_id: str
    ) -> Optional[PaymentMethodInfo]:
        """Get user's default payment method"""
        ...

    # Invoices
    async def create_invoice(self, invoice: Invoice) -> Optional[Invoice]:
        """Create an invoice"""
        ...

    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID"""
        ...

    async def mark_invoice_paid(
        self,
        invoice_id: str,
        payment_intent_id: str,
    ) -> Optional[Invoice]:
        """Mark invoice as paid"""
        ...

    # Refunds
    async def create_refund(self, refund: Refund) -> Optional[Refund]:
        """Create a refund"""
        ...

    async def update_refund_status(
        self, refund_id: str, status: RefundStatus
    ) -> bool:
        """Update refund status"""
        ...

    async def process_refund(
        self,
        refund_id: str,
        approved_by: Optional[str] = None,
    ) -> Optional[Refund]:
        """Process refund"""
        ...

    # Statistics
    async def get_revenue_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get revenue statistics"""
        ...

    async def get_subscription_statistics(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        ...


# ====================
# Event Bus Protocol
# ====================


class EventBusProtocol(Protocol):
    """Protocol for event bus operations"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event to the event bus"""
        ...

    async def subscribe_to_events(
        self, pattern: str, handler: Any, durable: str
    ) -> None:
        """Subscribe to events matching a pattern"""
        ...

    async def close(self) -> None:
        """Close event bus connection"""
        ...


# ====================
# Service Client Protocols
# ====================


class AccountClientProtocol(Protocol):
    """Protocol for account service client"""

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user account profile"""
        ...

    async def validate_user(self, user_id: str) -> bool:
        """Validate user exists"""
        ...


class WalletClientProtocol(Protocol):
    """Protocol for wallet service client"""

    async def get_balance(
        self,
        user_id: str,
        wallet_type: str = "main",
    ) -> Optional[Dict[str, Any]]:
        """Get wallet balance"""
        ...

    async def add_funds(
        self,
        user_id: str,
        wallet_type: str,
        amount: float,
        description: str,
        reference_id: str,
    ) -> Dict[str, Any]:
        """Add funds to wallet"""
        ...

    async def consume(
        self,
        user_id: str,
        wallet_type: str,
        amount: float,
        description: str,
        reference_id: str,
    ) -> Dict[str, Any]:
        """Consume from wallet"""
        ...


class BillingClientProtocol(Protocol):
    """Protocol for billing service client"""

    async def record_usage(
        self,
        user_id: str,
        product_id: str,
        service_type: str,
        usage_amount: int,
    ) -> Dict[str, Any]:
        """Record usage for billing"""
        ...

    async def get_billing_records(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get billing records"""
        ...


class ProductClientProtocol(Protocol):
    """Protocol for product service client"""

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details"""
        ...

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: str,
        subscription_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get product pricing information"""
        ...


# ====================
# Custom Exceptions (no I/O operations)
# ====================


class PaymentServiceError(Exception):
    """Base exception for payment service errors"""

    pass


class PaymentNotFoundError(PaymentServiceError):
    """Raised when payment is not found"""

    pass


class PaymentFailedError(PaymentServiceError):
    """Raised when payment processing fails"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        payment_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.payment_id = payment_id


class SubscriptionNotFoundError(PaymentServiceError):
    """Raised when subscription is not found"""

    pass


class SubscriptionPlanNotFoundError(PaymentServiceError):
    """Raised when subscription plan is not found"""

    pass


class InvoiceNotFoundError(PaymentServiceError):
    """Raised when invoice is not found"""

    pass


class InvoiceNotOpenError(PaymentServiceError):
    """Raised when invoice is not open for payment"""

    def __init__(self, message: str, current_status: Optional[str] = None):
        super().__init__(message)
        self.current_status = current_status


class RefundNotFoundError(PaymentServiceError):
    """Raised when refund is not found"""

    pass


class RefundNotEligibleError(PaymentServiceError):
    """Raised when payment is not eligible for refund"""

    def __init__(
        self,
        message: str,
        payment_status: Optional[str] = None,
        payment_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.payment_status = payment_status
        self.payment_id = payment_id


class RefundAmountExceededError(PaymentServiceError):
    """Raised when refund amount exceeds payment amount"""

    def __init__(
        self,
        message: str,
        payment_amount: Optional[Decimal] = None,
        requested_amount: Optional[Decimal] = None,
    ):
        super().__init__(message)
        self.payment_amount = payment_amount
        self.requested_amount = requested_amount


class UserValidationError(PaymentServiceError):
    """Raised when user validation fails"""

    pass


class StripeIntegrationError(PaymentServiceError):
    """Raised when Stripe integration fails"""

    def __init__(
        self,
        message: str,
        stripe_error_code: Optional[str] = None,
        stripe_error_type: Optional[str] = None,
    ):
        super().__init__(message)
        self.stripe_error_code = stripe_error_code
        self.stripe_error_type = stripe_error_type


class WebhookVerificationError(PaymentServiceError):
    """Raised when webhook signature verification fails"""

    pass


__all__ = [
    # Protocols
    "PaymentRepositoryProtocol",
    "EventBusProtocol",
    "AccountClientProtocol",
    "WalletClientProtocol",
    "BillingClientProtocol",
    "ProductClientProtocol",
    # Exceptions
    "PaymentServiceError",
    "PaymentNotFoundError",
    "PaymentFailedError",
    "SubscriptionNotFoundError",
    "SubscriptionPlanNotFoundError",
    "InvoiceNotFoundError",
    "InvoiceNotOpenError",
    "RefundNotFoundError",
    "RefundNotEligibleError",
    "RefundAmountExceededError",
    "UserValidationError",
    "StripeIntegrationError",
    "WebhookVerificationError",
]
