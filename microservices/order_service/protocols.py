"""
Order Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime
from decimal import Decimal

# Import only models (no I/O dependencies)
from .models import Order, OrderStatus, OrderType, PaymentStatus


# ============================================================================
# Custom Exceptions - defined here to avoid importing repository
# ============================================================================

class OrderNotFoundError(Exception):
    """Order not found error"""
    pass


class OrderValidationError(Exception):
    """Order validation error"""
    pass


class OrderServiceError(Exception):
    """Base exception for order service errors"""
    pass


class DuplicateOrderError(Exception):
    """Duplicate order error"""
    pass


class PaymentRequiredError(Exception):
    """Payment required to complete order"""
    pass


class InvalidOrderStateError(Exception):
    """Invalid order state transition"""
    pass


# ============================================================================
# Repository Protocol
# ============================================================================

@runtime_checkable
class OrderRepositoryProtocol(Protocol):
    """
    Interface for Order Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create_order(
        self,
        user_id: str,
        order_type: OrderType,
        total_amount: Decimal,
        currency: str = "USD",
        payment_intent_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Order:
        """Create a new order"""
        ...

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        ...

    async def update_order(
        self,
        order_id: str,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        payment_intent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[Order]:
        """Update order"""
        ...

    async def list_orders(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        order_type: Optional[OrderType] = None,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None
    ) -> List[Order]:
        """List orders with filtering"""
        ...

    async def get_user_orders(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """Get orders for a specific user"""
        ...

    async def search_orders(
        self,
        query: str,
        limit: int = 50,
        user_id: Optional[str] = None
    ) -> List[Order]:
        """Search orders"""
        ...

    async def get_orders_by_payment_intent(
        self,
        payment_intent_id: str
    ) -> List[Order]:
        """Get orders by payment intent ID"""
        ...

    async def get_order_by_payment_intent(
        self,
        payment_intent_id: str
    ) -> Optional[Order]:
        """Get single order by payment intent ID"""
        ...

    async def get_orders_by_subscription(
        self,
        subscription_id: str
    ) -> List[Order]:
        """Get orders by subscription ID"""
        ...

    async def cancel_order(
        self,
        order_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Cancel an order"""
        ...

    async def complete_order(
        self,
        order_id: str,
        payment_intent_id: Optional[str] = None
    ) -> bool:
        """Complete an order"""
        ...

    async def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        ...


# ============================================================================
# Event Bus Protocol
# ============================================================================

@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


# ============================================================================
# Client Protocols
# ============================================================================

@runtime_checkable
class PaymentClientProtocol(Protocol):
    """Interface for Payment Service Client"""

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        order_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create payment intent"""
        ...

    async def get_payment_status(
        self,
        payment_intent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get payment status"""
        ...


@runtime_checkable
class WalletClientProtocol(Protocol):
    """Interface for Wallet Service Client"""

    async def add_credits(
        self,
        wallet_id: str,
        user_id: str,
        amount: Decimal,
        order_id: str,
        description: str
    ) -> Optional[Dict[str, Any]]:
        """Add credits to wallet"""
        ...

    async def process_refund(
        self,
        wallet_id: str,
        user_id: str,
        amount: Decimal,
        order_id: str,
        description: str
    ) -> Optional[Dict[str, Any]]:
        """Process refund to wallet"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for Account Service Client"""

    async def get_account_profile(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user account profile"""
        ...

    async def validate_user(
        self,
        user_id: str
    ) -> bool:
        """Validate user exists"""
        ...


@runtime_checkable
class BillingClientProtocol(Protocol):
    """Interface for Billing Service Client"""

    async def create_invoice(
        self,
        user_id: str,
        order_id: str,
        amount: Decimal,
        currency: str,
        items: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Create invoice for order"""
        ...


@runtime_checkable
class StorageClientProtocol(Protocol):
    """Interface for Storage Service Client"""

    async def get_download_url(
        self,
        file_id: str,
        user_id: str
    ) -> Optional[str]:
        """Get download URL for digital goods"""
        ...
