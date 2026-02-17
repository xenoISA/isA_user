"""
Payment Service Data Models

定义支付服务的数据模型，包括支付、订阅、账单、退款等
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# ====================
# 枚举类型定义
# ====================

class PaymentStatus(str, Enum):
    """支付状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"


class PaymentMethod(str, Enum):
    """支付方式"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    BANK_TRANSFER = "bank_transfer"
    STRIPE = "stripe"
    PAYPAL = "paypal"


class SubscriptionStatus(str, Enum):
    """订阅状态"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    UNPAID = "unpaid"
    PAUSED = "paused"


class SubscriptionTier(str, Enum):
    """订阅层级"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingCycle(str, Enum):
    """计费周期"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class InvoiceStatus(str, Enum):
    """发票状态"""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class RefundStatus(str, Enum):
    """退款状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class Currency(str, Enum):
    """货币类型"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CNY = "CNY"
    JPY = "JPY"


# ====================
# 核心数据模型
# ====================

class SubscriptionPlan(BaseModel):
    """订阅计划模型"""
    id: Optional[str] = None
    plan_id: str = Field(..., description="计划ID")
    name: str = Field(..., description="计划名称")
    description: Optional[str] = None
    tier: SubscriptionTier
    price: Decimal = Field(..., ge=0, description="价格")
    currency: Currency = Currency.USD
    billing_cycle: BillingCycle
    
    # 计划特性
    features: Dict[str, Any] = Field(default_factory=dict)
    credits_included: int = Field(default=0, description="包含的积分数")
    max_users: Optional[int] = None
    max_storage_gb: Optional[int] = None
    
    # 试用期设置
    trial_days: int = Field(default=0, description="试用天数")
    
    # Stripe集成
    stripe_price_id: Optional[str] = None
    stripe_product_id: Optional[str] = None
    
    # 状态和时间戳
    is_active: bool = True
    is_public: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Subscription(BaseModel):
    """用户订阅模型"""
    id: Optional[str] = None
    subscription_id: str = Field(..., description="订阅ID")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = None
    plan_id: str = Field(..., description="计划ID")
    
    # 订阅状态
    status: SubscriptionStatus
    tier: SubscriptionTier
    
    # 计费周期
    current_period_start: datetime
    current_period_end: datetime
    billing_cycle: BillingCycle
    
    # 试用期
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    
    # 取消设置
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    # 支付信息
    payment_method_id: Optional[str] = None
    last_payment_date: Optional[datetime] = None
    next_payment_date: Optional[datetime] = None
    
    # Stripe集成
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Payment(BaseModel):
    """支付记录模型"""
    id: Optional[str] = None
    payment_id: str = Field(..., description="支付ID")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = None
    order_id: Optional[str] = None
    
    # 支付详情
    amount: Decimal = Field(..., ge=0, description="支付金额")
    currency: Currency = Currency.USD
    subtotal_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    shipping_amount: Decimal = Field(default=Decimal("0"), ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    description: Optional[str] = None
    
    # 支付状态
    status: PaymentStatus
    payment_method: PaymentMethod
    
    # 关联信息
    subscription_id: Optional[str] = None
    invoice_id: Optional[str] = None
    
    # 支付处理
    processor: str = Field(default="stripe", description="支付处理器")
    processor_payment_id: Optional[str] = None
    processor_response: Optional[Dict[str, Any]] = None
    
    # 失败信息
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None
    
    # 时间戳
    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None


class Invoice(BaseModel):
    """发票模型"""
    id: Optional[str] = None
    invoice_id: str = Field(..., description="发票ID")
    invoice_number: str = Field(..., description="发票号")
    
    # 关联信息
    user_id: str
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    
    # 发票详情
    status: InvoiceStatus
    amount_total: Decimal = Field(..., ge=0)
    amount_paid: Decimal = Field(default=Decimal("0"), ge=0)
    amount_due: Decimal = Field(..., ge=0)
    currency: Currency = Currency.USD
    
    # 计费周期
    billing_period_start: datetime
    billing_period_end: datetime
    
    # 支付信息
    payment_method_id: Optional[str] = None
    payment_intent_id: Optional[str] = None
    
    # 行项目
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Stripe集成
    stripe_invoice_id: Optional[str] = None
    
    # 时间戳
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Refund(BaseModel):
    """退款模型"""
    id: Optional[str] = None
    refund_id: str = Field(..., description="退款ID")
    payment_id: str = Field(..., description="原支付ID")
    user_id: str
    
    # 退款详情
    amount: Decimal = Field(..., ge=0, description="退款金额")
    currency: Currency = Currency.USD
    reason: Optional[str] = None
    status: RefundStatus
    
    # 处理信息
    processor: str = Field(default="stripe")
    processor_refund_id: Optional[str] = None
    processor_response: Optional[Dict[str, Any]] = None
    
    # 审批信息
    requested_by: Optional[str] = None
    approved_by: Optional[str] = None
    
    # 时间戳
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PaymentMethodInfo(BaseModel):
    """支付方式信息"""
    id: Optional[str] = None
    user_id: str
    method_type: PaymentMethod
    
    # 卡片信息（如果是卡支付）
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    
    # 银行信息（如果是银行转账）
    bank_name: Optional[str] = None
    bank_account_last4: Optional[str] = None
    
    # 第三方支付信息
    external_account_id: Optional[str] = None
    
    # Stripe信息
    stripe_payment_method_id: Optional[str] = None
    
    # 状态
    is_default: bool = False
    is_verified: bool = False
    created_at: Optional[datetime] = None


# ====================
# 请求/响应模型
# ====================

class CreatePaymentIntentRequest(BaseModel):
    """创建支付意图请求"""
    amount: Decimal = Field(..., ge=0, description="支付金额")
    currency: Currency = Currency.USD
    description: Optional[str] = None
    user_id: str
    payment_method_id: Optional[str] = None
    order_id: Optional[str] = None
    subtotal_amount: Optional[Decimal] = Field(default=None, ge=0)
    tax_amount: Optional[Decimal] = Field(default=None, ge=0)
    shipping_amount: Optional[Decimal] = Field(default=None, ge=0)
    discount_amount: Optional[Decimal] = Field(default=None, ge=0)
    metadata: Optional[Dict[str, Any]] = None


class CreateSubscriptionRequest(BaseModel):
    """创建订阅请求"""
    user_id: str
    plan_id: str
    payment_method_id: Optional[str] = None
    trial_days: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateSubscriptionRequest(BaseModel):
    """更新订阅请求"""
    plan_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class CancelSubscriptionRequest(BaseModel):
    """取消订阅请求"""
    immediate: bool = False
    reason: Optional[str] = None
    feedback: Optional[str] = None


class CreateRefundRequest(BaseModel):
    """创建退款请求"""
    payment_id: str
    amount: Optional[Decimal] = None  # None表示全额退款
    reason: str
    requested_by: str


class PaymentIntentResponse(BaseModel):
    """支付意图响应"""
    payment_intent_id: str
    client_secret: Optional[str] = None  # 可选，因为没有Stripe时为None
    amount: Decimal
    currency: Currency
    status: PaymentStatus
    metadata: Optional[Dict[str, Any]] = None


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    subscription: Subscription
    plan: SubscriptionPlan
    next_invoice: Optional[Invoice] = None
    payment_method: Optional[PaymentMethodInfo] = None


class PaymentHistoryResponse(BaseModel):
    """支付历史响应"""
    payments: List[Payment]
    total_count: int
    total_amount: Decimal
    filters_applied: Dict[str, Any]


class InvoiceResponse(BaseModel):
    """发票响应"""
    invoice: Invoice
    payment: Optional[Payment] = None
    download_url: Optional[str] = None


class UsageRecord(BaseModel):
    """使用量记录"""
    user_id: str
    subscription_id: str
    metric_name: str
    quantity: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class BillingAddress(BaseModel):
    """账单地址"""
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str


class WebhookEvent(BaseModel):
    """Webhook事件模型"""
    id: str
    type: str
    data: Dict[str, Any]
    created: datetime
    livemode: bool
    pending_webhooks: int
    request: Optional[Dict[str, Any]] = None


# ====================
# 系统和服务模型
# ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    port: int
    version: str


class ServiceInfo(BaseModel):
    """服务信息"""
    service: str
    version: str
    description: str
    capabilities: Dict[str, Any]
    endpoints: Dict[str, str]


class ServiceStats(BaseModel):
    """服务统计"""
    total_payments: int
    active_subscriptions: int
    revenue_today: Decimal
    revenue_month: Decimal
    failed_payments_today: int
    refunds_today: int
