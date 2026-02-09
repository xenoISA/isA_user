"""
Billing Service Protocols

Defines interfaces for dependency injection and testing.
Following the protocol-based architecture pattern.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol, Tuple

from .models import (
    BillingEvent,
    BillingQuota,
    BillingRecord,
    BillingStatus, 
    ServiceType,
)


# ====================
# Repository Protocol
# ====================


class BillingRepositoryProtocol(Protocol):
    """Protocol for billing data repository"""

    async def initialize(self) -> None:
        """Initialize repository connection"""
        ...

    async def close(self) -> None:
        """Close repository connection"""
        ...

    # Billing Records
    async def create_billing_record(
        self, billing_record: BillingRecord
    ) -> BillingRecord:
        """Create a new billing record"""
        ...

    async def get_billing_record(self, billing_id: str) -> Optional[BillingRecord]:
        """Get billing record by ID"""
        ...

    async def update_billing_record_status(
        self,
        billing_id: str,
        status: BillingStatus,
        failure_reason: Optional[str] = None,
        wallet_transaction_id: Optional[str] = None,
        payment_transaction_id: Optional[str] = None,
    ) -> Optional[BillingRecord]:
        """Update billing record status"""
        ...

    async def get_user_billing_records(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[BillingStatus] = None,
        service_type: Optional[ServiceType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BillingRecord]:
        """Get user's billing records"""
        ...

    # Billing Events
    async def create_billing_event(self, billing_event: BillingEvent) -> BillingEvent:
        """Create a billing event"""
        ...

    # Usage Aggregations
    async def get_usage_aggregations(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        period_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Any]:
        """Get usage aggregations"""
        ...

    # Quotas
    async def get_billing_quota(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        product_id: Optional[str] = None,
    ) -> Optional[BillingQuota]:
        """Get billing quota"""
        ...

    # Statistics
    async def get_billing_stats(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get billing statistics"""
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


class ProductClientProtocol(Protocol):
    """Protocol for product service client"""

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: str,
        subscription_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get product pricing information"""
        ...


class WalletClientProtocol(Protocol):
    """Protocol for wallet service client"""

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


class SubscriptionClientProtocol(Protocol):
    """Protocol for subscription service client"""

    async def get_credit_balance(
        self, user_id: str, organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get user's subscription credit balance"""
        ...

    async def consume_credits(
        self,
        user_id: str,
        credits_amount: int,
        service_type: str,
        description: str,
        usage_record_id: str,
        organization_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Consume subscription credits"""
        ...


# ====================
# Custom Exceptions (no I/O operations)
# ====================


class BillingServiceError(Exception):
    """Base exception for billing service errors"""

    pass


class ProductPricingNotFoundError(BillingServiceError):
    """Raised when product pricing information is not found"""

    pass


class QuotaExceededError(BillingServiceError):
    """Raised when usage quota is exceeded"""

    def __init__(
        self,
        message: str,
        quota_limit: Optional[Decimal] = None,
        quota_used: Optional[Decimal] = None,
    ):
        super().__init__(message)
        self.quota_limit = quota_limit
        self.quota_used = quota_used


class BillingRecordNotFoundError(BillingServiceError):
    """Raised when billing record is not found"""

    pass


class WalletDeductionFailedError(BillingServiceError):
    """Raised when wallet deduction fails"""

    def __init__(self, message: str, transaction_id: Optional[str] = None):
        super().__init__(message)
        self.transaction_id = transaction_id


class CreditConsumptionFailedError(BillingServiceError):
    """Raised when credit consumption fails"""

    def __init__(self, message: str, transaction_id: Optional[str] = None):
        super().__init__(message)
        self.transaction_id = transaction_id


class InvalidBillingMethodError(BillingServiceError):
    """Raised when billing method is invalid or unsupported"""

    pass


__all__ = [
    "BillingRepositoryProtocol",
    "EventBusProtocol",
    "ProductClientProtocol",
    "WalletClientProtocol",
    "SubscriptionClientProtocol",
    "BillingServiceError",
    "ProductPricingNotFoundError",
    "QuotaExceededError",
    "BillingRecordNotFoundError",
    "WalletDeductionFailedError",
    "CreditConsumptionFailedError",
    "InvalidBillingMethodError",
]
