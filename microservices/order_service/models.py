"""
Order Service Data Models

Pydantic models for order management, transactions, and order processing.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderType(str, Enum):
    """Order type enumeration"""
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"
    CREDIT_PURCHASE = "credit_purchase"
    PREMIUM_UPGRADE = "premium_upgrade"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# Core Order Models

class Order(BaseModel):
    """Core order model"""
    order_id: str
    user_id: str
    order_type: OrderType
    status: OrderStatus
    total_amount: Decimal
    currency: str = "USD"
    payment_status: PaymentStatus
    payment_intent_id: Optional[str] = None
    subscription_id: Optional[str] = None
    wallet_id: Optional[str] = None
    items: List[Dict[str, Any]] = []
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


# Request Models

class OrderCreateRequest(BaseModel):
    """Create order request"""
    user_id: str = Field(..., description="User ID placing the order")
    order_type: OrderType = Field(..., description="Type of order")
    total_amount: Decimal = Field(..., gt=0, description="Total order amount")
    currency: str = Field(default="USD", description="Order currency")
    payment_intent_id: Optional[str] = Field(None, description="Associated payment intent")
    subscription_id: Optional[str] = Field(None, description="Associated subscription")
    wallet_id: Optional[str] = Field(None, description="Target wallet for credits")
    items: List[Dict[str, Any]] = Field(default=[], description="Order items")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    expires_in_minutes: Optional[int] = Field(default=30, description="Order expiration time")

    @validator('total_amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v


class OrderUpdateRequest(BaseModel):
    """Update order request"""
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    payment_intent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OrderCancelRequest(BaseModel):
    """Cancel order request"""
    reason: Optional[str] = Field(None, description="Cancellation reason")
    refund_amount: Optional[Decimal] = Field(None, description="Refund amount if applicable")


class OrderCompleteRequest(BaseModel):
    """Complete order request"""
    payment_confirmed: bool = Field(..., description="Payment confirmation status")
    transaction_id: Optional[str] = Field(None, description="Transaction reference")
    credits_added: Optional[Decimal] = Field(None, description="Credits added to wallet")
    

# Response Models

class OrderResponse(BaseModel):
    """Order response model"""
    success: bool
    order: Optional[Order] = None
    message: str
    error_code: Optional[str] = None


class OrderListResponse(BaseModel):
    """Order list response"""
    orders: List[Order]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class OrderSummary(BaseModel):
    """Order summary model"""
    order_id: str
    user_id: str
    order_type: OrderType
    status: OrderStatus
    total_amount: Decimal
    currency: str
    created_at: datetime
    

class OrderSummaryResponse(BaseModel):
    """Order summary response"""
    orders: List[OrderSummary]
    count: int


# Filter and Query Models

class OrderFilter(BaseModel):
    """Order filtering parameters"""
    user_id: Optional[str] = None
    order_type: Optional[OrderType] = None
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class OrderSearchParams(BaseModel):
    """Order search parameters"""
    query: str = Field(..., description="Search query")
    user_id: Optional[str] = None
    limit: int = Field(default=50, le=100)
    include_cancelled: bool = Field(default=False)


# Order Statistics Models

class OrderStatistics(BaseModel):
    """Order statistics model"""
    total_orders: int
    orders_by_status: Dict[str, int]
    orders_by_type: Dict[str, int]
    total_revenue: Decimal
    revenue_by_currency: Dict[str, Decimal]
    avg_order_value: Decimal
    recent_orders_24h: int
    recent_orders_7d: int
    recent_orders_30d: int


# Service Integration Models

class PaymentServiceRequest(BaseModel):
    """Request to payment service"""
    amount: Decimal
    currency: str
    description: str
    user_id: str
    order_id: str
    metadata: Optional[Dict[str, Any]] = None


class WalletServiceRequest(BaseModel):
    """Request to wallet service"""
    user_id: str
    amount: Decimal
    order_id: str
    description: str
    transaction_type: str = "deposit"


class OrderServiceStatus(BaseModel):
    """Order service status response"""
    service: str = "order_service"
    status: str = "operational"
    port: int = 8210
    version: str = "1.0.0"
    database_connected: bool
    timestamp: Optional[datetime] = None
    stats: Optional[OrderStatistics] = None


# Webhook and Event Models

class OrderEvent(BaseModel):
    """Order event model"""
    event_type: str
    order_id: str
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]


class WebhookPayload(BaseModel):
    """Webhook payload model"""
    event: OrderEvent
    signature: Optional[str] = None
    webhook_id: str