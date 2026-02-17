"""
Order Service Data Contract

Defines canonical data structures for order service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for order service test data.
Zero hardcoded data - all test data generated through factory methods.
"""

import uuid
import secrets
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# Enums (Mirror production models)
# ============================================================================

class OrderStatusContract(str, Enum):
    """Order status enumeration for contracts"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderTypeContract(str, Enum):
    """Order type enumeration for contracts"""
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"
    CREDIT_PURCHASE = "credit_purchase"
    PREMIUM_UPGRADE = "premium_upgrade"


class PaymentStatusContract(str, Enum):
    """Payment status enumeration for contracts"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================================================
# Request Contracts (12 schemas)
# ============================================================================

class OrderCreateRequestContract(BaseModel):
    """
    Contract: Order creation request schema

    Used for creating orders in tests.
    Maps to order service create endpoint.
    """
    user_id: str = Field(..., min_length=1, description="User ID placing the order")
    order_type: OrderTypeContract = Field(..., description="Type of order")
    total_amount: Decimal = Field(..., gt=0, description="Total order amount")
    currency: str = Field(default="USD", max_length=3, description="Order currency")
    payment_intent_id: Optional[str] = Field(None, description="Associated payment intent")
    subscription_id: Optional[str] = Field(None, description="Associated subscription")
    wallet_id: Optional[str] = Field(None, description="Target wallet for credits")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Order items")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    expires_in_minutes: Optional[int] = Field(default=30, ge=1, le=1440, description="Expiration time")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty or whitespace")
        return v.strip()

    @field_validator('total_amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CNY', 'CAD', 'AUD']
        if v.upper() not in valid_currencies:
            raise ValueError(f"Invalid currency: {v}")
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123def456",
                "order_type": "purchase",
                "total_amount": 99.99,
                "currency": "USD",
                "items": [{"product_id": "prod_001", "quantity": 1}]
            }
        }


class OrderUpdateRequestContract(BaseModel):
    """
    Contract: Order update request schema

    Used for updating order details in tests.
    """
    status: Optional[OrderStatusContract] = Field(None, description="New order status")
    payment_status: Optional[PaymentStatusContract] = Field(None, description="New payment status")
    payment_intent_id: Optional[str] = Field(None, description="Payment intent ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "processing",
                "payment_status": "processing",
                "payment_intent_id": "pi_xxx123"
            }
        }


class OrderCancelRequestContract(BaseModel):
    """
    Contract: Order cancellation request schema

    Used for cancelling orders in tests.
    """
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")
    refund_amount: Optional[Decimal] = Field(None, ge=0, description="Refund amount if applicable")

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Customer requested cancellation",
                "refund_amount": 99.99
            }
        }


class OrderCompleteRequestContract(BaseModel):
    """
    Contract: Order completion request schema

    Used for completing orders after payment in tests.
    """
    payment_confirmed: bool = Field(..., description="Payment confirmation status")
    transaction_id: Optional[str] = Field(None, description="Transaction reference")
    credits_added: Optional[Decimal] = Field(None, ge=0, description="Credits added to wallet")

    class Config:
        json_schema_extra = {
            "example": {
                "payment_confirmed": True,
                "transaction_id": "txn_abc123",
                "credits_added": 100.00
            }
        }


class OrderListParamsContract(BaseModel):
    """
    Contract: Order list query parameters schema

    Used for listing orders with pagination in tests.
    """
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    order_type: Optional[OrderTypeContract] = Field(None, description="Filter by order type")
    status: Optional[OrderStatusContract] = Field(None, description="Filter by status")
    payment_status: Optional[PaymentStatusContract] = Field(None, description="Filter by payment status")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 50,
                "status": "completed"
            }
        }


class OrderSearchParamsContract(BaseModel):
    """
    Contract: Order search query parameters schema

    Used for searching orders in tests.
    """
    query: str = Field(..., min_length=1, max_length=100, description="Search query")
    user_id: Optional[str] = Field(None, description="Filter by user")
    limit: int = Field(default=50, ge=1, le=100, description="Max results")
    include_cancelled: bool = Field(default=False, description="Include cancelled orders")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "query": "order_abc",
                "limit": 50
            }
        }


class OrderFilterContract(BaseModel):
    """
    Contract: Order filtering parameters schema

    Internal filter model for repository operations.
    """
    user_id: Optional[str] = None
    order_type: Optional[OrderTypeContract] = None
    status: Optional[OrderStatusContract] = None
    payment_status: Optional[PaymentStatusContract] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class OrderItemContract(BaseModel):
    """
    Contract: Order item schema

    Used for order line items in tests.
    """
    product_id: str = Field(..., description="Product ID")
    name: Optional[str] = Field(None, description="Product name")
    quantity: int = Field(default=1, ge=1, description="Quantity")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")
    total_price: Optional[Decimal] = Field(None, description="Line total")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Item metadata")


class PaymentServiceRequestContract(BaseModel):
    """
    Contract: Payment service request schema

    Used for payment service integration tests.
    """
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USD", description="Currency")
    description: str = Field(..., description="Payment description")
    user_id: str = Field(..., description="User ID")
    order_id: str = Field(..., description="Order ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Payment metadata")


class WalletServiceRequestContract(BaseModel):
    """
    Contract: Wallet service request schema

    Used for wallet service integration tests.
    """
    user_id: str = Field(..., description="User ID")
    amount: Decimal = Field(..., description="Amount")
    order_id: str = Field(..., description="Order ID")
    description: str = Field(..., description="Transaction description")
    transaction_type: str = Field(default="deposit", description="Transaction type")


# ============================================================================
# Response Contracts (10 schemas)
# ============================================================================

class OrderContract(BaseModel):
    """
    Contract: Core order model

    Represents an order entity in responses.
    """
    order_id: str
    user_id: str
    order_type: OrderTypeContract
    status: OrderStatusContract
    total_amount: Decimal
    currency: str = "USD"
    payment_status: PaymentStatusContract
    payment_intent_id: Optional[str] = None
    subscription_id: Optional[str] = None
    wallet_id: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class OrderResponseContract(BaseModel):
    """
    Contract: Order response schema

    Standard response for order operations.
    """
    success: bool
    order: Optional[OrderContract] = None
    message: str
    error_code: Optional[str] = None


class OrderListResponseContract(BaseModel):
    """
    Contract: Order list response schema

    Paginated list of orders.
    """
    orders: List[OrderContract]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class OrderSummaryContract(BaseModel):
    """
    Contract: Order summary schema

    Abbreviated order information.
    """
    order_id: str
    user_id: str
    order_type: OrderTypeContract
    status: OrderStatusContract
    total_amount: Decimal
    currency: str
    created_at: datetime


class OrderSummaryResponseContract(BaseModel):
    """
    Contract: Order summary list response

    List of order summaries.
    """
    orders: List[OrderSummaryContract]
    count: int


class OrderStatisticsResponseContract(BaseModel):
    """
    Contract: Order statistics response schema

    Analytics and metrics for orders.
    """
    total_orders: int
    orders_by_status: Dict[str, int]
    orders_by_type: Dict[str, int]
    total_revenue: Decimal
    revenue_by_currency: Dict[str, Decimal]
    avg_order_value: Decimal
    recent_orders_24h: int
    recent_orders_7d: int
    recent_orders_30d: int


class OrderSearchResponseContract(BaseModel):
    """
    Contract: Order search response schema

    Search results for orders.
    """
    orders: List[OrderContract]
    count: int
    query: str


class HealthResponseContract(BaseModel):
    """
    Contract: Health check response

    Service health status.
    """
    status: str
    service: str = "order_service"
    port: int = 8210
    version: str = "1.0.0"
    timestamp: datetime


class DetailedHealthResponseContract(BaseModel):
    """
    Contract: Detailed health response

    Service health with database status.
    """
    service: str = "order_service"
    status: str = "operational"
    port: int = 8210
    version: str = "1.0.0"
    database_connected: bool
    timestamp: Optional[datetime] = None


# ============================================================================
# OrderTestDataFactory - 40+ methods (25 valid + 15 invalid)
# ============================================================================

class OrderTestDataFactory:
    """
    Test data factory for order_service - zero hardcoded data.

    All factory methods generate unique, random data suitable for testing.
    """

    # === ID Generators (5 methods) ===

    @staticmethod
    def make_order_id() -> str:
        """Generate valid order ID"""
        return f"order_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_payment_intent_id() -> str:
        """Generate valid payment intent ID"""
        return f"pi_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_subscription_id() -> str:
        """Generate valid subscription ID"""
        return f"sub_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_wallet_id() -> str:
        """Generate valid wallet ID"""
        return f"wallet_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_transaction_id() -> str:
        """Generate valid transaction ID"""
        return f"txn_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_product_id() -> str:
        """Generate valid product ID"""
        return f"prod_{uuid.uuid4().hex[:8]}"

    # === Amount Generators (5 methods) ===

    @staticmethod
    def make_amount() -> Decimal:
        """Generate valid positive amount"""
        return Decimal(str(round(random.uniform(9.99, 999.99), 2)))

    @staticmethod
    def make_small_amount() -> Decimal:
        """Generate small valid amount"""
        return Decimal(str(round(random.uniform(0.99, 9.99), 2)))

    @staticmethod
    def make_large_amount() -> Decimal:
        """Generate large valid amount"""
        return Decimal(str(round(random.uniform(1000.00, 9999.99), 2)))

    @staticmethod
    def make_credit_amount() -> Decimal:
        """Generate credit amount (integer-like)"""
        return Decimal(str(random.randint(10, 1000)))

    @staticmethod
    def make_refund_amount(original: Decimal) -> Decimal:
        """Generate valid refund amount (partial or full)"""
        percentage = random.uniform(0.5, 1.0)
        return Decimal(str(round(float(original) * percentage, 2)))

    # === Currency ===

    @staticmethod
    def make_currency() -> str:
        """Generate valid currency code"""
        currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]
        return random.choice(currencies)

    # === Timestamp Generators (4 methods) ===

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days: int = 7) -> datetime:
        """Generate past timestamp"""
        return datetime.now(timezone.utc) - timedelta(days=random.randint(1, days))

    @staticmethod
    def make_future_timestamp(minutes: int = 30) -> datetime:
        """Generate future timestamp (for expiration)"""
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)

    @staticmethod
    def make_expiration_minutes() -> int:
        """Generate valid expiration minutes"""
        return random.randint(15, 60)

    # === Order Type Generators (4 methods) ===

    @staticmethod
    def make_order_type() -> OrderTypeContract:
        """Generate random order type"""
        return random.choice(list(OrderTypeContract))

    @staticmethod
    def make_purchase_type() -> OrderTypeContract:
        """Generate purchase order type"""
        return OrderTypeContract.PURCHASE

    @staticmethod
    def make_subscription_type() -> OrderTypeContract:
        """Generate subscription order type"""
        return OrderTypeContract.SUBSCRIPTION

    @staticmethod
    def make_credit_purchase_type() -> OrderTypeContract:
        """Generate credit purchase order type"""
        return OrderTypeContract.CREDIT_PURCHASE

    # === Status Generators (3 methods) ===

    @staticmethod
    def make_order_status() -> OrderStatusContract:
        """Generate random order status"""
        return random.choice(list(OrderStatusContract))

    @staticmethod
    def make_pending_status() -> OrderStatusContract:
        """Generate pending status"""
        return OrderStatusContract.PENDING

    @staticmethod
    def make_payment_status() -> PaymentStatusContract:
        """Generate random payment status"""
        return random.choice(list(PaymentStatusContract))

    # === Complex Object Generators (10 methods) ===

    @staticmethod
    def make_order_item(**overrides) -> Dict[str, Any]:
        """Generate valid order item"""
        item = {
            "product_id": OrderTestDataFactory.make_product_id(),
            "name": f"Product {secrets.token_hex(4)}",
            "quantity": random.randint(1, 5),
            "unit_price": float(OrderTestDataFactory.make_small_amount()),
        }
        item["total_price"] = item["unit_price"] * item["quantity"]
        item.update(overrides)
        return item

    @staticmethod
    def make_order_items(count: int = 2) -> List[Dict[str, Any]]:
        """Generate list of order items"""
        return [OrderTestDataFactory.make_order_item() for _ in range(count)]

    @staticmethod
    def make_metadata(**overrides) -> Dict[str, Any]:
        """Generate valid metadata"""
        metadata = {
            "source": random.choice(["web", "mobile", "api"]),
            "session_id": secrets.token_hex(8),
        }
        metadata.update(overrides)
        return metadata

    @staticmethod
    def make_create_request(**overrides) -> OrderCreateRequestContract:
        """Generate valid order creation request"""
        order_type = overrides.pop('order_type', OrderTestDataFactory.make_purchase_type())

        defaults = {
            "user_id": OrderTestDataFactory.make_user_id(),
            "order_type": order_type,
            "total_amount": OrderTestDataFactory.make_amount(),
            "currency": "USD",
            "items": OrderTestDataFactory.make_order_items(),
            "expires_in_minutes": 30,
        }

        # Add required fields based on order type
        if order_type == OrderTypeContract.CREDIT_PURCHASE:
            defaults["wallet_id"] = OrderTestDataFactory.make_wallet_id()
        elif order_type == OrderTypeContract.SUBSCRIPTION:
            defaults["subscription_id"] = OrderTestDataFactory.make_subscription_id()

        defaults.update(overrides)
        return OrderCreateRequestContract(**defaults)

    @staticmethod
    def make_credit_purchase_request(**overrides) -> OrderCreateRequestContract:
        """Generate valid credit purchase request"""
        return OrderTestDataFactory.make_create_request(
            order_type=OrderTypeContract.CREDIT_PURCHASE,
            wallet_id=OrderTestDataFactory.make_wallet_id(),
            **overrides
        )

    @staticmethod
    def make_subscription_request(**overrides) -> OrderCreateRequestContract:
        """Generate valid subscription request"""
        return OrderTestDataFactory.make_create_request(
            order_type=OrderTypeContract.SUBSCRIPTION,
            subscription_id=OrderTestDataFactory.make_subscription_id(),
            **overrides
        )

    @staticmethod
    def make_update_request(**overrides) -> OrderUpdateRequestContract:
        """Generate valid update request"""
        defaults = {
            "status": OrderStatusContract.PROCESSING,
            "payment_status": PaymentStatusContract.PROCESSING,
        }
        defaults.update(overrides)
        return OrderUpdateRequestContract(**defaults)

    @staticmethod
    def make_cancel_request(**overrides) -> OrderCancelRequestContract:
        """Generate valid cancel request"""
        defaults = {
            "reason": f"Test cancellation {secrets.token_hex(4)}",
        }
        defaults.update(overrides)
        return OrderCancelRequestContract(**defaults)

    @staticmethod
    def make_complete_request(**overrides) -> OrderCompleteRequestContract:
        """Generate valid complete request"""
        defaults = {
            "payment_confirmed": True,
            "transaction_id": OrderTestDataFactory.make_transaction_id(),
        }
        defaults.update(overrides)
        return OrderCompleteRequestContract(**defaults)

    @staticmethod
    def make_search_params(**overrides) -> OrderSearchParamsContract:
        """Generate valid search params"""
        defaults = {
            "query": f"order_{secrets.token_hex(4)}",
            "limit": 50,
        }
        defaults.update(overrides)
        return OrderSearchParamsContract(**defaults)

    @staticmethod
    def make_list_params(**overrides) -> OrderListParamsContract:
        """Generate valid list params"""
        defaults = {
            "page": 1,
            "page_size": 50,
        }
        defaults.update(overrides)
        return OrderListParamsContract(**defaults)

    # === Response Generators (5 methods) ===

    @staticmethod
    def make_order(**overrides) -> OrderContract:
        """Generate valid order object"""
        now = OrderTestDataFactory.make_timestamp()
        defaults = {
            "order_id": OrderTestDataFactory.make_order_id(),
            "user_id": OrderTestDataFactory.make_user_id(),
            "order_type": OrderTypeContract.PURCHASE,
            "status": OrderStatusContract.PENDING,
            "total_amount": OrderTestDataFactory.make_amount(),
            "currency": "USD",
            "payment_status": PaymentStatusContract.PENDING,
            "items": OrderTestDataFactory.make_order_items(),
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return OrderContract(**defaults)

    @staticmethod
    def make_completed_order(**overrides) -> OrderContract:
        """Generate completed order"""
        now = OrderTestDataFactory.make_timestamp()
        return OrderTestDataFactory.make_order(
            status=OrderStatusContract.COMPLETED,
            payment_status=PaymentStatusContract.COMPLETED,
            payment_intent_id=OrderTestDataFactory.make_payment_intent_id(),
            completed_at=now,
            **overrides
        )

    @staticmethod
    def make_order_response(success: bool = True, **overrides) -> OrderResponseContract:
        """Generate order response"""
        defaults = {
            "success": success,
            "order": OrderTestDataFactory.make_order() if success else None,
            "message": "Operation successful" if success else "Operation failed",
            "error_code": None if success else "ERROR",
        }
        defaults.update(overrides)
        return OrderResponseContract(**defaults)

    @staticmethod
    def make_statistics() -> OrderStatisticsResponseContract:
        """Generate order statistics"""
        total = random.randint(100, 1000)
        return OrderStatisticsResponseContract(
            total_orders=total,
            orders_by_status={
                "pending": random.randint(10, 50),
                "processing": random.randint(5, 20),
                "completed": random.randint(50, total - 100),
                "failed": random.randint(1, 10),
                "cancelled": random.randint(1, 10),
                "refunded": random.randint(1, 5),
            },
            orders_by_type={
                "purchase": random.randint(40, 60),
                "subscription": random.randint(20, 40),
                "credit_purchase": random.randint(10, 20),
                "premium_upgrade": random.randint(5, 10),
            },
            total_revenue=Decimal(str(random.uniform(10000, 100000))),
            revenue_by_currency={"USD": Decimal(str(random.uniform(10000, 100000)))},
            avg_order_value=Decimal(str(random.uniform(50, 200))),
            recent_orders_24h=random.randint(10, 50),
            recent_orders_7d=random.randint(50, 200),
            recent_orders_30d=random.randint(200, 500),
        )

    @staticmethod
    def make_health_response() -> HealthResponseContract:
        """Generate health response"""
        return HealthResponseContract(
            status="healthy",
            timestamp=OrderTestDataFactory.make_timestamp()
        )

    # === Invalid Data Generators (15 methods) ===

    @staticmethod
    def make_invalid_order_id() -> str:
        """Generate invalid order ID (wrong format)"""
        return "invalid_order"

    @staticmethod
    def make_invalid_user_id() -> str:
        """Generate invalid user ID (empty)"""
        return ""

    @staticmethod
    def make_empty_user_id() -> str:
        """Generate whitespace-only user ID"""
        return "   "

    @staticmethod
    def make_invalid_amount() -> Decimal:
        """Generate invalid amount (zero)"""
        return Decimal("0")

    @staticmethod
    def make_negative_amount() -> Decimal:
        """Generate invalid negative amount"""
        return Decimal("-99.99")

    @staticmethod
    def make_invalid_currency() -> str:
        """Generate invalid currency code"""
        return "INVALID"

    @staticmethod
    def make_invalid_order_type() -> str:
        """Generate invalid order type"""
        return "invalid_type"

    @staticmethod
    def make_invalid_status() -> str:
        """Generate invalid order status"""
        return "invalid_status"

    @staticmethod
    def make_invalid_create_request_missing_user() -> Dict[str, Any]:
        """Generate create request missing user_id"""
        return {
            "order_type": "purchase",
            "total_amount": 99.99,
            "currency": "USD"
        }

    @staticmethod
    def make_invalid_create_request_zero_amount() -> Dict[str, Any]:
        """Generate create request with zero amount"""
        return {
            "user_id": OrderTestDataFactory.make_user_id(),
            "order_type": "purchase",
            "total_amount": 0,
            "currency": "USD"
        }

    @staticmethod
    def make_invalid_credit_request_no_wallet() -> Dict[str, Any]:
        """Generate credit purchase without wallet_id"""
        return {
            "user_id": OrderTestDataFactory.make_user_id(),
            "order_type": "credit_purchase",
            "total_amount": 50.00,
            "currency": "USD"
            # Missing wallet_id
        }

    @staticmethod
    def make_invalid_subscription_request_no_sub_id() -> Dict[str, Any]:
        """Generate subscription order without subscription_id"""
        return {
            "user_id": OrderTestDataFactory.make_user_id(),
            "order_type": "subscription",
            "total_amount": 9.99,
            "currency": "USD"
            # Missing subscription_id
        }

    @staticmethod
    def make_invalid_complete_request() -> Dict[str, Any]:
        """Generate complete request with payment_confirmed=false"""
        return {
            "payment_confirmed": False,
            "transaction_id": OrderTestDataFactory.make_transaction_id()
        }

    @staticmethod
    def make_invalid_refund_amount(original: Decimal) -> Decimal:
        """Generate refund amount exceeding original"""
        return original + Decimal("100.00")

    @staticmethod
    def make_invalid_search_query() -> str:
        """Generate empty search query"""
        return ""


# ============================================================================
# Request Builders (4 builders)
# ============================================================================

class OrderCreateRequestBuilder:
    """Builder for order creation requests"""

    def __init__(self):
        self._user_id = OrderTestDataFactory.make_user_id()
        self._order_type = OrderTypeContract.PURCHASE
        self._total_amount = OrderTestDataFactory.make_amount()
        self._currency = "USD"
        self._payment_intent_id = None
        self._subscription_id = None
        self._wallet_id = None
        self._items = []
        self._metadata = None
        self._expires_in_minutes = 30

    def with_user_id(self, value: str) -> 'OrderCreateRequestBuilder':
        self._user_id = value
        return self

    def with_order_type(self, value: OrderTypeContract) -> 'OrderCreateRequestBuilder':
        self._order_type = value
        return self

    def with_total_amount(self, value: Decimal) -> 'OrderCreateRequestBuilder':
        self._total_amount = value
        return self

    def with_currency(self, value: str) -> 'OrderCreateRequestBuilder':
        self._currency = value
        return self

    def with_payment_intent_id(self, value: str) -> 'OrderCreateRequestBuilder':
        self._payment_intent_id = value
        return self

    def with_subscription_id(self, value: str) -> 'OrderCreateRequestBuilder':
        self._subscription_id = value
        return self

    def with_wallet_id(self, value: str) -> 'OrderCreateRequestBuilder':
        self._wallet_id = value
        return self

    def with_items(self, value: List[Dict[str, Any]]) -> 'OrderCreateRequestBuilder':
        self._items = value
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'OrderCreateRequestBuilder':
        self._metadata = value
        return self

    def with_expires_in_minutes(self, value: int) -> 'OrderCreateRequestBuilder':
        self._expires_in_minutes = value
        return self

    def as_credit_purchase(self) -> 'OrderCreateRequestBuilder':
        self._order_type = OrderTypeContract.CREDIT_PURCHASE
        self._wallet_id = OrderTestDataFactory.make_wallet_id()
        return self

    def as_subscription(self) -> 'OrderCreateRequestBuilder':
        self._order_type = OrderTypeContract.SUBSCRIPTION
        self._subscription_id = OrderTestDataFactory.make_subscription_id()
        return self

    def build(self) -> OrderCreateRequestContract:
        return OrderCreateRequestContract(
            user_id=self._user_id,
            order_type=self._order_type,
            total_amount=self._total_amount,
            currency=self._currency,
            payment_intent_id=self._payment_intent_id,
            subscription_id=self._subscription_id,
            wallet_id=self._wallet_id,
            items=self._items,
            metadata=self._metadata,
            expires_in_minutes=self._expires_in_minutes
        )


class OrderUpdateRequestBuilder:
    """Builder for order update requests"""

    def __init__(self):
        self._status = None
        self._payment_status = None
        self._payment_intent_id = None
        self._metadata = None

    def with_status(self, value: OrderStatusContract) -> 'OrderUpdateRequestBuilder':
        self._status = value
        return self

    def with_payment_status(self, value: PaymentStatusContract) -> 'OrderUpdateRequestBuilder':
        self._payment_status = value
        return self

    def with_payment_intent_id(self, value: str) -> 'OrderUpdateRequestBuilder':
        self._payment_intent_id = value
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'OrderUpdateRequestBuilder':
        self._metadata = value
        return self

    def as_processing(self) -> 'OrderUpdateRequestBuilder':
        self._status = OrderStatusContract.PROCESSING
        self._payment_status = PaymentStatusContract.PROCESSING
        return self

    def as_completed(self) -> 'OrderUpdateRequestBuilder':
        self._status = OrderStatusContract.COMPLETED
        self._payment_status = PaymentStatusContract.COMPLETED
        return self

    def build(self) -> OrderUpdateRequestContract:
        return OrderUpdateRequestContract(
            status=self._status,
            payment_status=self._payment_status,
            payment_intent_id=self._payment_intent_id,
            metadata=self._metadata
        )


class OrderCancelRequestBuilder:
    """Builder for order cancel requests"""

    def __init__(self):
        self._reason = None
        self._refund_amount = None

    def with_reason(self, value: str) -> 'OrderCancelRequestBuilder':
        self._reason = value
        return self

    def with_refund_amount(self, value: Decimal) -> 'OrderCancelRequestBuilder':
        self._refund_amount = value
        return self

    def with_full_refund(self, original_amount: Decimal) -> 'OrderCancelRequestBuilder':
        self._refund_amount = original_amount
        return self

    def with_partial_refund(self, original_amount: Decimal, percentage: float = 0.5) -> 'OrderCancelRequestBuilder':
        self._refund_amount = Decimal(str(round(float(original_amount) * percentage, 2)))
        return self

    def build(self) -> OrderCancelRequestContract:
        return OrderCancelRequestContract(
            reason=self._reason,
            refund_amount=self._refund_amount
        )


class OrderCompleteRequestBuilder:
    """Builder for order complete requests"""

    def __init__(self):
        self._payment_confirmed = True
        self._transaction_id = None
        self._credits_added = None

    def with_payment_confirmed(self, value: bool) -> 'OrderCompleteRequestBuilder':
        self._payment_confirmed = value
        return self

    def with_transaction_id(self, value: str) -> 'OrderCompleteRequestBuilder':
        self._transaction_id = value
        return self

    def with_credits_added(self, value: Decimal) -> 'OrderCompleteRequestBuilder':
        self._credits_added = value
        return self

    def with_payment_details(self) -> 'OrderCompleteRequestBuilder':
        self._transaction_id = OrderTestDataFactory.make_transaction_id()
        return self

    def for_credit_purchase(self, amount: Decimal) -> 'OrderCompleteRequestBuilder':
        self._credits_added = amount
        self._transaction_id = OrderTestDataFactory.make_transaction_id()
        return self

    def build(self) -> OrderCompleteRequestContract:
        return OrderCompleteRequestContract(
            payment_confirmed=self._payment_confirmed,
            transaction_id=self._transaction_id,
            credits_added=self._credits_added
        )
