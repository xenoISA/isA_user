"""
Order Service - Mock Dependencies

Mock implementations for component testing.
Returns Order model objects as expected by the service.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid

# Import the actual models used by the service
from microservices.order_service.models import (
    Order, OrderStatus, OrderType, PaymentStatus
)


class MockOrderRepository:
    """Mock order repository for component testing

    Implements OrderRepositoryProtocol interface.
    Returns Order model objects, not dicts.
    """

    def __init__(self):
        self._data: Dict[str, Order] = {}
        self._user_index: Dict[str, List[str]] = {}  # user_id -> [order_ids]
        self._payment_intent_index: Dict[str, str] = {}  # payment_intent_id -> order_id
        self._subscription_index: Dict[str, List[str]] = {}  # subscription_id -> [order_ids]
        self._stats: Dict[str, Any] = {}
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    def set_order(
        self,
        order_id: str,
        user_id: str,
        order_type: OrderType,
        status: OrderStatus = OrderStatus.PENDING,
        total_amount: Decimal = Decimal("10.00"),
        currency: str = "USD",
        payment_status: PaymentStatus = PaymentStatus.PENDING,
        payment_intent_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ):
        """Add an order to the mock repository"""
        now = datetime.now(timezone.utc)
        order = Order(
            order_id=order_id,
            user_id=user_id,
            order_type=order_type,
            status=status,
            total_amount=total_amount,
            currency=currency,
            payment_status=payment_status,
            payment_intent_id=payment_intent_id,
            subscription_id=subscription_id,
            wallet_id=wallet_id,
            items=items or [],
            metadata=metadata,
            created_at=created_at or now,
            updated_at=updated_at or now,
            completed_at=completed_at,
            expires_at=expires_at
        )
        self._data[order_id] = order

        # Update indexes
        if user_id not in self._user_index:
            self._user_index[user_id] = []
        if order_id not in self._user_index[user_id]:
            self._user_index[user_id].append(order_id)

        if payment_intent_id:
            self._payment_intent_index[payment_intent_id] = order_id

        if subscription_id:
            if subscription_id not in self._subscription_index:
                self._subscription_index[subscription_id] = []
            if order_id not in self._subscription_index[subscription_id]:
                self._subscription_index[subscription_id].append(order_id)

    def set_stats(
        self,
        total_orders: int = 0,
        orders_by_status: Optional[Dict[str, int]] = None,
        orders_by_type: Optional[Dict[str, int]] = None,
        total_revenue: Decimal = Decimal("0"),
        revenue_by_currency: Optional[Dict[str, Decimal]] = None,
        avg_order_value: Decimal = Decimal("0"),
        recent_orders_24h: int = 0,
        recent_orders_7d: int = 0,
        recent_orders_30d: int = 0
    ):
        """Set service statistics"""
        self._stats = {
            "total_orders": total_orders,
            "orders_by_status": orders_by_status or {},
            "orders_by_type": orders_by_type or {},
            "total_revenue": total_revenue,
            "revenue_by_currency": revenue_by_currency or {"USD": Decimal("0")},
            "avg_order_value": avg_order_value,
            "recent_orders_24h": recent_orders_24h,
            "recent_orders_7d": recent_orders_7d,
            "recent_orders_30d": recent_orders_30d
        }

    def set_error(self, error: Exception):
        """Set an error to be raised on operations"""
        self._error = error

    def _log_call(self, method: str, **kwargs):
        """Log method calls for assertions"""
        self._call_log.append({"method": method, "kwargs": kwargs})

    def assert_called(self, method: str):
        """Assert that a method was called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method in called_methods, f"Expected {method} to be called, but got {called_methods}"

    def assert_called_with(self, method: str, **kwargs):
        """Assert that a method was called with specific kwargs"""
        for call in self._call_log:
            if call["method"] == method:
                for key, value in kwargs.items():
                    assert key in call["kwargs"], f"Expected kwarg {key} not found"
                    assert call["kwargs"][key] == value, f"Expected {key}={value}, got {call['kwargs'][key]}"
                return
        raise AssertionError(f"Expected {method} to be called with {kwargs}")

    def get_call_count(self, method: str) -> int:
        """Get number of times a method was called"""
        return sum(1 for c in self._call_log if c["method"] == method)

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
        self._log_call(
            "create_order",
            user_id=user_id,
            order_type=order_type,
            total_amount=total_amount,
            currency=currency,
            payment_intent_id=payment_intent_id,
            subscription_id=subscription_id,
            wallet_id=wallet_id,
            items=items,
            metadata=metadata,
            expires_at=expires_at
        )

        if self._error:
            raise self._error

        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        order = Order(
            order_id=order_id,
            user_id=user_id,
            order_type=order_type,
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            currency=currency,
            payment_status=PaymentStatus.PENDING,
            payment_intent_id=payment_intent_id,
            subscription_id=subscription_id,
            wallet_id=wallet_id,
            items=items or [],
            metadata=metadata,
            created_at=now,
            updated_at=now,
            completed_at=None,
            expires_at=expires_at
        )

        self._data[order_id] = order

        # Update indexes
        if user_id not in self._user_index:
            self._user_index[user_id] = []
        self._user_index[user_id].append(order_id)

        if payment_intent_id:
            self._payment_intent_index[payment_intent_id] = order_id

        if subscription_id:
            if subscription_id not in self._subscription_index:
                self._subscription_index[subscription_id] = []
            self._subscription_index[subscription_id].append(order_id)

        return order

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        self._log_call("get_order", order_id=order_id)
        if self._error:
            raise self._error
        return self._data.get(order_id)

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
        self._log_call(
            "update_order",
            order_id=order_id,
            status=status,
            payment_status=payment_status,
            payment_intent_id=payment_intent_id,
            metadata=metadata,
            completed_at=completed_at
        )

        if self._error:
            raise self._error

        if order_id not in self._data:
            return None

        order = self._data[order_id]
        updated_order = Order(
            order_id=order.order_id,
            user_id=order.user_id,
            order_type=order.order_type,
            status=status or order.status,
            total_amount=order.total_amount,
            currency=order.currency,
            payment_status=payment_status or order.payment_status,
            payment_intent_id=payment_intent_id or order.payment_intent_id,
            subscription_id=order.subscription_id,
            wallet_id=order.wallet_id,
            items=order.items,
            metadata=metadata if metadata is not None else order.metadata,
            created_at=order.created_at,
            updated_at=datetime.now(timezone.utc),
            completed_at=completed_at or order.completed_at,
            expires_at=order.expires_at
        )

        self._data[order_id] = updated_order
        return updated_order

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
        self._log_call(
            "list_orders",
            limit=limit,
            offset=offset,
            user_id=user_id,
            order_type=order_type,
            status=status,
            payment_status=payment_status
        )

        if self._error:
            raise self._error

        results = []
        for order in self._data.values():
            if user_id and order.user_id != user_id:
                continue
            if order_type and order.order_type != order_type:
                continue
            if status and order.status != status:
                continue
            if payment_status and order.payment_status != payment_status:
                continue
            results.append(order)

        # Sort by created_at descending
        results.sort(key=lambda o: o.created_at, reverse=True)

        return results[offset:offset + limit]

    async def get_user_orders(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """Get orders for a specific user"""
        self._log_call("get_user_orders", user_id=user_id, limit=limit, offset=offset)

        if self._error:
            raise self._error

        order_ids = self._user_index.get(user_id, [])
        orders = [self._data[oid] for oid in order_ids if oid in self._data]
        orders.sort(key=lambda o: o.created_at, reverse=True)

        return orders[offset:offset + limit]

    async def search_orders(
        self,
        query: str,
        limit: int = 50,
        user_id: Optional[str] = None
    ) -> List[Order]:
        """Search orders"""
        self._log_call("search_orders", query=query, limit=limit, user_id=user_id)

        if self._error:
            raise self._error

        results = []
        query_lower = query.lower()

        for order in self._data.values():
            if user_id and order.user_id != user_id:
                continue

            # Search in order_id, user_id, and metadata
            searchable = f"{order.order_id} {order.user_id} {order.order_type.value}"
            if order.metadata:
                searchable += f" {str(order.metadata)}"

            if query_lower in searchable.lower():
                results.append(order)
                if len(results) >= limit:
                    break

        return results

    async def get_orders_by_payment_intent(
        self,
        payment_intent_id: str
    ) -> List[Order]:
        """Get orders by payment intent ID"""
        self._log_call("get_orders_by_payment_intent", payment_intent_id=payment_intent_id)

        if self._error:
            raise self._error

        order_id = self._payment_intent_index.get(payment_intent_id)
        if order_id and order_id in self._data:
            return [self._data[order_id]]
        return []

    async def get_order_by_payment_intent(
        self,
        payment_intent_id: str
    ) -> Optional[Order]:
        """Get single order by payment intent ID"""
        self._log_call("get_order_by_payment_intent", payment_intent_id=payment_intent_id)

        if self._error:
            raise self._error

        order_id = self._payment_intent_index.get(payment_intent_id)
        if order_id:
            return self._data.get(order_id)
        return None

    async def get_orders_by_subscription(
        self,
        subscription_id: str
    ) -> List[Order]:
        """Get orders by subscription ID"""
        self._log_call("get_orders_by_subscription", subscription_id=subscription_id)

        if self._error:
            raise self._error

        order_ids = self._subscription_index.get(subscription_id, [])
        return [self._data[oid] for oid in order_ids if oid in self._data]

    async def cancel_order(
        self,
        order_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Cancel an order"""
        self._log_call("cancel_order", order_id=order_id, reason=reason)

        if self._error:
            raise self._error

        if order_id not in self._data:
            return False

        order = self._data[order_id]
        updated_order = Order(
            order_id=order.order_id,
            user_id=order.user_id,
            order_type=order.order_type,
            status=OrderStatus.CANCELLED,
            total_amount=order.total_amount,
            currency=order.currency,
            payment_status=order.payment_status,
            payment_intent_id=order.payment_intent_id,
            subscription_id=order.subscription_id,
            wallet_id=order.wallet_id,
            items=order.items,
            metadata={**(order.metadata or {}), "cancel_reason": reason} if reason else order.metadata,
            created_at=order.created_at,
            updated_at=datetime.now(timezone.utc),
            completed_at=order.completed_at,
            expires_at=order.expires_at
        )

        self._data[order_id] = updated_order
        return True

    async def complete_order(
        self,
        order_id: str,
        payment_intent_id: Optional[str] = None
    ) -> bool:
        """Complete an order"""
        self._log_call("complete_order", order_id=order_id, payment_intent_id=payment_intent_id)

        if self._error:
            raise self._error

        if order_id not in self._data:
            return False

        order = self._data[order_id]
        now = datetime.now(timezone.utc)

        updated_order = Order(
            order_id=order.order_id,
            user_id=order.user_id,
            order_type=order.order_type,
            status=OrderStatus.COMPLETED,
            total_amount=order.total_amount,
            currency=order.currency,
            payment_status=PaymentStatus.COMPLETED,
            payment_intent_id=payment_intent_id or order.payment_intent_id,
            subscription_id=order.subscription_id,
            wallet_id=order.wallet_id,
            items=order.items,
            metadata=order.metadata,
            created_at=order.created_at,
            updated_at=now,
            completed_at=now,
            expires_at=order.expires_at
        )

        self._data[order_id] = updated_order

        if payment_intent_id:
            self._payment_intent_index[payment_intent_id] = order_id

        return True

    async def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        self._log_call("get_order_statistics")

        if self._error:
            raise self._error

        if self._stats:
            return self._stats

        # Calculate from data
        total = len(self._data)
        orders_by_status = {}
        orders_by_type = {}
        total_revenue = Decimal("0")
        revenue_by_currency: Dict[str, Decimal] = {}

        for order in self._data.values():
            # Count by status
            status_key = order.status.value
            orders_by_status[status_key] = orders_by_status.get(status_key, 0) + 1

            # Count by type
            type_key = order.order_type.value
            orders_by_type[type_key] = orders_by_type.get(type_key, 0) + 1

            # Sum revenue (only completed orders)
            if order.status == OrderStatus.COMPLETED:
                total_revenue += order.total_amount
                if order.currency not in revenue_by_currency:
                    revenue_by_currency[order.currency] = Decimal("0")
                revenue_by_currency[order.currency] += order.total_amount

        avg_value = total_revenue / total if total > 0 else Decimal("0")

        return {
            "total_orders": total,
            "orders_by_status": orders_by_status,
            "orders_by_type": orders_by_type,
            "total_revenue": total_revenue,
            "revenue_by_currency": revenue_by_currency or {"USD": Decimal("0")},
            "avg_order_value": avg_value,
            "recent_orders_24h": 0,
            "recent_orders_7d": 0,
            "recent_orders_30d": 0
        }


class MockEventBus:
    """Mock NATS event bus"""

    def __init__(self):
        self.published_events: List[Any] = []
        self._call_log: List[Dict] = []

    async def publish(self, event: Any):
        """Publish event"""
        self._call_log.append({"method": "publish", "event": event})
        self.published_events.append(event)

    async def publish_event(self, event: Any):
        """Publish event (alias)"""
        await self.publish(event)

    def assert_published(self, event_type: str = None):
        """Assert that an event was published"""
        assert len(self.published_events) > 0, "No events were published"
        if event_type:
            event_types = [getattr(e, "event_type", str(e)) for e in self.published_events]
            assert event_type in str(event_types), f"Expected {event_type} event, got {event_types}"

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def clear(self):
        """Clear all published events"""
        self.published_events.clear()
        self._call_log.clear()


class MockAccountClient:
    """Mock Account Service client"""

    def __init__(self):
        self._users: Dict[str, Dict[str, Any]] = {}
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    def set_user(self, user_id: str, name: str = "Test User", email: str = "test@example.com"):
        """Add a user to the mock"""
        self._users[user_id] = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "is_active": True
        }

    def set_error(self, error: Exception):
        """Set an error to be raised"""
        self._error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user account profile"""
        self._call_log.append({"method": "get_account_profile", "user_id": user_id})
        if self._error:
            raise self._error
        return self._users.get(user_id)

    async def validate_user(self, user_id: str) -> bool:
        """Validate user exists"""
        self._call_log.append({"method": "validate_user", "user_id": user_id})
        if self._error:
            raise self._error
        return user_id in self._users


class MockWalletClient:
    """Mock Wallet Service client"""

    def __init__(self):
        self._wallets: Dict[str, Decimal] = {}
        self._transactions: List[Dict[str, Any]] = []
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    def set_wallet(self, wallet_id: str, balance: Decimal = Decimal("0")):
        """Add a wallet to the mock"""
        self._wallets[wallet_id] = balance

    def set_error(self, error: Exception):
        """Set an error to be raised"""
        self._error = error

    async def add_credits(
        self,
        wallet_id: str,
        user_id: str,
        amount: Decimal,
        order_id: str,
        description: str
    ) -> Optional[Dict[str, Any]]:
        """Add credits to wallet"""
        self._call_log.append({
            "method": "add_credits",
            "wallet_id": wallet_id,
            "user_id": user_id,
            "amount": amount,
            "order_id": order_id,
            "description": description
        })

        if self._error:
            raise self._error

        if wallet_id not in self._wallets:
            return None

        self._wallets[wallet_id] += amount
        self._transactions.append({
            "wallet_id": wallet_id,
            "user_id": user_id,
            "amount": amount,
            "order_id": order_id,
            "type": "credit"
        })

        return {"success": True, "new_balance": self._wallets[wallet_id]}

    async def process_refund(
        self,
        wallet_id: str,
        user_id: str,
        amount: Decimal,
        order_id: str,
        description: str
    ) -> Optional[Dict[str, Any]]:
        """Process refund to wallet"""
        self._call_log.append({
            "method": "process_refund",
            "wallet_id": wallet_id,
            "user_id": user_id,
            "amount": amount,
            "order_id": order_id,
            "description": description
        })

        if self._error:
            raise self._error

        if wallet_id not in self._wallets:
            return None

        self._wallets[wallet_id] += amount
        self._transactions.append({
            "wallet_id": wallet_id,
            "user_id": user_id,
            "amount": amount,
            "order_id": order_id,
            "type": "refund"
        })

        return {"success": True, "new_balance": self._wallets[wallet_id]}

    def get_balance(self, wallet_id: str) -> Optional[Decimal]:
        """Get wallet balance"""
        return self._wallets.get(wallet_id)


class MockPaymentClient:
    """Mock Payment Service client"""

    def __init__(self):
        self._intents: Dict[str, Dict[str, Any]] = {}
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    def set_payment_intent(
        self,
        intent_id: str,
        status: str = "succeeded",
        amount: Decimal = Decimal("10.00")
    ):
        """Add a payment intent to the mock"""
        self._intents[intent_id] = {
            "payment_intent_id": intent_id,
            "status": status,
            "amount": amount
        }

    def set_error(self, error: Exception):
        """Set an error to be raised"""
        self._error = error

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        order_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create payment intent"""
        self._call_log.append({
            "method": "create_payment_intent",
            "amount": amount,
            "currency": currency,
            "user_id": user_id,
            "order_id": order_id,
            "metadata": metadata
        })

        if self._error:
            raise self._error

        intent_id = f"pi_{uuid.uuid4().hex[:12]}"
        self._intents[intent_id] = {
            "payment_intent_id": intent_id,
            "status": "requires_payment_method",
            "amount": amount,
            "currency": currency,
            "order_id": order_id
        }

        return self._intents[intent_id]

    async def get_payment_status(
        self,
        payment_intent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get payment status"""
        self._call_log.append({
            "method": "get_payment_status",
            "payment_intent_id": payment_intent_id
        })

        if self._error:
            raise self._error

        return self._intents.get(payment_intent_id)
