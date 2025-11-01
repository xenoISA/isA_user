"""
Product Service Data Models

Defines all products, services, pricing models, and plans available on the platform
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field


# ====================
# 枚举类型定义
# ====================

class ProductType(str, Enum):
    """产品类型"""
    MODEL = "model"                      # AI模型
    STORAGE = "storage"                  # 存储服务
    AGENT = "agent"                      # AI代理
    MCP_TOOL = "mcp_tool"               # MCP工具
    API_SERVICE = "api_service"          # API服务
    NOTIFICATION = "notification"        # 通知服务
    COMPUTATION = "computation"          # 计算服务
    DATA_PROCESSING = "data_processing"  # 数据处理
    INTEGRATION = "integration"          # 集成服务
    OTHER = "other"                      # 其他


class PricingType(str, Enum):
    """定价类型"""
    USAGE_BASED = "usage_based"          # 按用量计费
    SUBSCRIPTION = "subscription"        # 订阅制
    ONE_TIME = "one_time"               # 一次性付费
    FREEMIUM = "freemium"               # 免费增值
    HYBRID = "hybrid"                    # 混合模式


class UnitType(str, Enum):
    """计费单位类型"""
    TOKEN = "token"                      # Token
    REQUEST = "request"                  # 请求次数
    MINUTE = "minute"                    # 分钟
    HOUR = "hour"                        # 小时
    DAY = "day"                          # 天
    MB = "mb"                            # 兆字节
    GB = "gb"                            # 千兆字节
    USER = "user"                        # 用户数
    NOTIFICATION = "notification"        # 通知数量
    EMAIL = "email"                      # 邮件数量
    ITEM = "item"                        # 项目数量


class PlanTier(str, Enum):
    """计划层级"""
    FREE = "free"                        # 免费版
    BASIC = "basic"                      # 基础版
    PRO = "pro"                          # 专业版
    ENTERPRISE = "enterprise"            # 企业版
    CUSTOM = "custom"                    # 定制版


class TargetAudience(str, Enum):
    """目标用户"""
    INDIVIDUAL = "individual"            # 个人用户
    TEAM = "team"                        # 团队
    ENTERPRISE = "enterprise"            # 企业


class DependencyType(str, Enum):
    """依赖类型"""
    REQUIRED = "required"                # 必需的
    OPTIONAL = "optional"                # 可选的
    ALTERNATIVE = "alternative"          # 替代的


class Currency(str, Enum):
    """货币类型"""
    USD = "USD"
    EUR = "EUR"
    CNY = "CNY"
    CREDIT = "CREDIT"                    # 平台积分


# ====================
# 核心数据模型
# ====================

class ProductCategory(BaseModel):
    """产品分类模型"""
    id: Optional[int] = None
    category_id: str = Field(..., description="分类ID")
    name: str = Field(..., description="分类名称")
    description: Optional[str] = None
    parent_category_id: Optional[str] = None
    display_order: int = Field(default=0, description="显示顺序")
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Product(BaseModel):
    """产品模型"""
    id: Optional[int] = None
    product_id: str = Field(..., description="产品ID")
    category_id: str = Field(..., description="分类ID")
    
    # 产品详情
    name: str = Field(..., description="产品名称")
    description: Optional[str] = None
    short_description: Optional[str] = None
    
    # 产品分类
    product_type: ProductType
    provider: Optional[str] = None  # openai, anthropic, minio, internal等
    
    # 产品规格
    specifications: Dict[str, Any] = Field(default_factory=dict)
    capabilities: List[str] = Field(default_factory=list)
    limitations: Dict[str, Any] = Field(default_factory=dict)
    
    # 可用性
    is_active: bool = True
    is_public: bool = True
    requires_approval: bool = False
    
    # 版本信息
    version: str = Field(default="1.0")
    release_date: Optional[date] = None
    deprecation_date: Optional[date] = None
    
    # 集成信息
    service_endpoint: Optional[str] = None
    service_type: Optional[str] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PricingModel(BaseModel):
    """定价模型"""
    id: Optional[int] = None
    pricing_model_id: str = Field(..., description="定价模型ID")
    product_id: str = Field(..., description="产品ID")
    
    # 定价模型详情
    name: str = Field(..., description="定价模型名称")
    pricing_type: PricingType
    
    # 按用量定价
    unit_type: Optional[UnitType] = None
    base_unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    
    # 输入/输出定价（适用于模型）
    input_unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    output_unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    
    # 固定费用
    setup_cost: Decimal = Field(default=Decimal("0"), ge=0)
    base_cost_per_request: Decimal = Field(default=Decimal("0"), ge=0)
    
    # 订阅定价
    monthly_price: Decimal = Field(default=Decimal("0"), ge=0)
    yearly_price: Decimal = Field(default=Decimal("0"), ge=0)
    
    # 免费层
    free_tier_limit: Decimal = Field(default=Decimal("0"), ge=0)
    free_tier_period: str = Field(default="monthly")
    
    # 计费配置
    minimum_charge: Decimal = Field(default=Decimal("0"), ge=0)
    currency: Currency = Currency.CREDIT
    billing_unit_size: int = Field(default=1, ge=1)
    
    # 阶梯定价
    tier_pricing: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 状态和时间
    is_active: bool = True
    effective_from: datetime = Field(default_factory=datetime.utcnow)
    effective_until: Optional[datetime] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ServicePlan(BaseModel):
    """服务计划模型"""
    id: Optional[int] = None
    plan_id: str = Field(..., description="计划ID")
    
    # 计划详情
    name: str = Field(..., description="计划名称")
    description: Optional[str] = None
    plan_tier: PlanTier
    
    # 计划定价
    monthly_price: Decimal = Field(default=Decimal("0"), ge=0)
    yearly_price: Decimal = Field(default=Decimal("0"), ge=0)
    setup_fee: Decimal = Field(default=Decimal("0"), ge=0)
    currency: Currency = Currency.CREDIT
    
    # 计划特性和限制
    included_credits: Decimal = Field(default=Decimal("0"), ge=0)
    credit_rollover: bool = False
    
    # 服务包含项
    included_products: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 使用限制
    usage_limits: Dict[str, Any] = Field(default_factory=dict)
    
    # 计划功能
    features: List[str] = Field(default_factory=list)
    
    # 超出部分定价
    overage_pricing: Dict[str, Any] = Field(default_factory=dict)
    
    # 计划可用性
    is_active: bool = True
    is_public: bool = True
    requires_approval: bool = False
    max_users: Optional[int] = None
    
    # 目标用户
    target_audience: Optional[TargetAudience] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProductDependency(BaseModel):
    """产品依赖模型"""
    id: Optional[int] = None
    product_id: str = Field(..., description="产品ID")
    depends_on_product_id: str = Field(..., description="依赖的产品ID")
    dependency_type: DependencyType
    created_at: Optional[datetime] = None


# ====================
# 请求/响应模型
# ====================

class ProductSearchRequest(BaseModel):
    """产品搜索请求"""
    category_id: Optional[str] = None
    product_type: Optional[ProductType] = None
    provider: Optional[str] = None
    is_active: bool = True
    is_public: bool = True
    search_term: Optional[str] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class PricingCalculationRequest(BaseModel):
    """定价计算请求"""
    product_id: str
    usage_amount: Decimal = Field(..., ge=0)
    unit_type: Optional[UnitType] = None
    user_plan_id: Optional[str] = None  # 用户当前计划
    calculation_date: Optional[datetime] = None


class PricingCalculationResponse(BaseModel):
    """定价计算响应"""
    product_id: str
    pricing_model_id: str
    usage_amount: Decimal
    unit_type: UnitType
    unit_price: Decimal
    total_cost: Decimal
    currency: Currency
    
    # 免费层应用
    free_tier_applied: bool = False
    free_tier_used: Decimal = Field(default=Decimal("0"))
    free_tier_remaining: Decimal = Field(default=Decimal("0"))
    
    # 阶梯定价详情
    tier_breakdown: Optional[List[Dict[str, Any]]] = None
    
    # 计划折扣
    plan_discount_applied: bool = False
    plan_discount_amount: Decimal = Field(default=Decimal("0"))
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProductCatalogResponse(BaseModel):
    """产品目录响应"""
    categories: List[ProductCategory]
    products: List[Product]
    pricing_models: List[PricingModel]
    service_plans: List[ServicePlan]
    total_products: int
    filters_applied: Dict[str, Any]


class PlanComparisonResponse(BaseModel):
    """计划比较响应"""
    plans: List[ServicePlan]
    comparison_matrix: Dict[str, Dict[str, Any]]  # 计划功能对比矩阵
    recommended_plan: Optional[str] = None


# ====================
# 系统模型
# ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    port: int
    version: str
    database_status: str


class ServiceInfo(BaseModel):
    """服务信息"""
    service: str
    version: str
    description: str
    capabilities: List[str]
    supported_product_types: List[ProductType]
    supported_pricing_types: List[PricingType]


class SubscriptionStatus(str, Enum):
    """订阅状态"""
    ACTIVE = "active"                    # 活跃
    TRIALING = "trialing"               # 试用中
    PAST_DUE = "past_due"               # 逾期
    CANCELED = "canceled"               # 已取消
    INCOMPLETE = "incomplete"           # 不完整
    INCOMPLETE_EXPIRED = "incomplete_expired"  # 不完整已过期
    UNPAID = "unpaid"                   # 未付款
    PAUSED = "paused"                   # 暂停


class BillingCycle(str, Enum):
    """计费周期"""
    MONTHLY = "monthly"                  # 月付
    QUARTERLY = "quarterly"              # 季付
    YEARLY = "yearly"                    # 年付
    ONE_TIME = "one_time"               # 一次性


# ====================
# 订阅管理模型
# ====================

class UserSubscription(BaseModel):
    """用户订阅模型"""
    id: Optional[int] = None
    subscription_id: str = Field(..., description="订阅ID")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = None
    
    # 订阅计划
    plan_id: str = Field(..., description="计划ID")
    plan_tier: PlanTier
    
    # 订阅状态
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    
    # 计费周期
    current_period_start: datetime
    current_period_end: datetime
    
    # 试用期
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    
    # 取消设置
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    # 下次续费
    next_billing_date: Optional[datetime] = None
    
    # 支付集成（如果需要实际支付）
    payment_method_id: Optional[str] = None
    external_subscription_id: Optional[str] = None  # Stripe等外部订阅ID
    
    # 使用量和限制
    usage_this_period: Dict[str, Any] = Field(default_factory=dict)
    quota_limits: Dict[str, Any] = Field(default_factory=dict)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubscriptionUsage(BaseModel):
    """订阅使用量模型"""
    id: Optional[int] = None
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None
    
    # 使用周期
    period_start: datetime
    period_end: datetime
    
    # 产品使用量
    product_usage: Dict[str, Any] = Field(
        default_factory=dict,
        description="产品使用量详情: {product_id: {usage_amount: 100, cost: 10.50}}"
    )
    
    # 总计
    total_usage_cost: Decimal = Field(default=Decimal("0"), ge=0)
    credits_consumed: Decimal = Field(default=Decimal("0"), ge=0)
    
    # 计费状态
    is_billed: bool = False
    billed_at: Optional[datetime] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ====================
# 订阅请求/响应模型
# ====================

class CreateSubscriptionRequest(BaseModel):
    """创建订阅请求"""
    user_id: str
    organization_id: Optional[str] = None
    plan_id: str
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_method_id: Optional[str] = None
    trial_days: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateSubscriptionRequest(BaseModel):
    """更新订阅请求"""
    plan_id: Optional[str] = None
    billing_cycle: Optional[BillingCycle] = None
    cancel_at_period_end: Optional[bool] = None
    payment_method_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CancelSubscriptionRequest(BaseModel):
    """取消订阅请求"""
    immediate: bool = False
    reason: Optional[str] = None
    feedback: Optional[str] = None


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    subscription: UserSubscription
    plan: ServicePlan
    current_usage: Optional[SubscriptionUsage] = None
    next_billing_amount: Optional[Decimal] = None
    days_until_renewal: Optional[int] = None


class SubscriptionStatsResponse(BaseModel):
    """订阅统计响应"""
    total_subscriptions: int
    active_subscriptions: int
    trialing_subscriptions: int
    canceled_subscriptions: int
    subscriptions_by_tier: Dict[PlanTier, int]
    monthly_recurring_revenue: Decimal
    annual_recurring_revenue: Decimal
    churn_rate: Optional[float] = None


# ====================
# 产品使用量跟踪
# ====================

class ProductUsageRecord(BaseModel):
    """产品使用量记录"""
    id: Optional[int] = None
    usage_id: str = Field(..., description="使用记录ID")
    
    # 用户信息
    user_id: str
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    
    # 产品信息
    product_id: str
    pricing_model_id: str
    
    # 使用量详情
    usage_amount: Decimal = Field(..., ge=0)
    unit_type: UnitType
    unit_price: Decimal = Field(..., ge=0)
    total_cost: Decimal = Field(..., ge=0)
    currency: Currency = Currency.CREDIT
    
    # 时间信息
    usage_timestamp: datetime = Field(default_factory=datetime.utcnow)
    usage_period_start: Optional[datetime] = None
    usage_period_end: Optional[datetime] = None
    
    # 详细信息
    usage_details: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # 计费状态
    is_free_tier: bool = False
    is_included_in_plan: bool = False
    billing_status: str = Field(default="pending")
    
    created_at: Optional[datetime] = None


class ProductStats(BaseModel):
    """产品统计"""
    total_products: int
    active_products: int
    products_by_type: Dict[ProductType, int]
    products_by_provider: Dict[str, int]
    total_pricing_models: int
    active_pricing_models: int
    total_service_plans: int
    active_service_plans: int
    total_subscriptions: int
    active_subscriptions: int