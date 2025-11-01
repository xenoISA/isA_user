"""
Billing Service Data Models

专注于使用量跟踪、费用计算和计费处理
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# ====================
# 枚举类型定义
# ====================

class BillingStatus(str, Enum):
    """计费状态"""
    PENDING = "pending"                  # 待处理
    PROCESSING = "processing"            # 处理中
    COMPLETED = "completed"              # 已完成
    FAILED = "failed"                    # 失败
    REFUNDED = "refunded"                # 已退款


class BillingMethod(str, Enum):
    """计费方式"""
    WALLET_DEDUCTION = "wallet_deduction"  # 钱包扣费
    PAYMENT_CHARGE = "payment_charge"      # 支付扣费
    CREDIT_CONSUMPTION = "credit_consumption"  # 积分消费
    SUBSCRIPTION_INCLUDED = "subscription_included"  # 订阅包含


class EventType(str, Enum):
    """计费事件类型"""
    USAGE_RECORDED = "usage_recorded"      # 使用量记录
    BILLING_PROCESSED = "billing_processed"  # 计费处理
    PAYMENT_COMPLETED = "payment_completed"  # 支付完成
    REFUND_ISSUED = "refund_issued"        # 退款发放
    QUOTA_EXCEEDED = "quota_exceeded"      # 配额超出
    BILLING_FAILED = "billing_failed"     # 计费失败


class ServiceType(str, Enum):
    """服务类型"""
    MODEL_INFERENCE = "model_inference"    # 模型推理
    MCP_SERVICE = "mcp_service"           # MCP服务
    AGENT_EXECUTION = "agent_execution"    # Agent执行
    STORAGE_MINIO = "storage_minio"       # Minio存储
    API_GATEWAY = "api_gateway"           # API网关
    NOTIFICATION = "notification"          # 通知服务
    OTHER = "other"                       # 其他


class Currency(str, Enum):
    """货币类型"""
    USD = "USD"
    CNY = "CNY"
    CREDIT = "CREDIT"                     # 平台积分


# ====================
# 核心数据模型
# ====================

class BillingRecord(BaseModel):
    """计费记录模型"""
    id: Optional[int] = None
    billing_id: str = Field(..., description="计费记录ID")
    
    # 关联信息
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    usage_record_id: str = Field(..., description="使用记录ID")
    
    # 产品信息
    product_id: str = Field(..., description="产品ID")
    service_type: ServiceType
    
    # 计费详情
    usage_amount: Decimal = Field(..., ge=0, description="使用量")
    unit_price: Decimal = Field(..., ge=0, description="单价")
    total_amount: Decimal = Field(..., ge=0, description="总金额")
    currency: Currency = Currency.CREDIT
    
    # 计费方式和状态
    billing_method: BillingMethod
    billing_status: BillingStatus = BillingStatus.PENDING
    
    # 处理信息
    processed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    
    # 关联的钱包/支付记录
    wallet_transaction_id: Optional[str] = None
    payment_transaction_id: Optional[str] = None
    
    # 元数据
    billing_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BillingEvent(BaseModel):
    """计费事件模型"""
    id: Optional[int] = None
    event_id: str = Field(..., description="事件ID")
    
    # 事件详情
    event_type: EventType
    event_source: str = Field(..., description="事件源")
    
    # 关联实体
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    billing_record_id: Optional[str] = None
    
    # 事件数据
    event_data: Dict[str, Any] = Field(default_factory=dict)
    amount: Optional[Decimal] = None
    currency: Optional[Currency] = None
    
    # 处理状态
    is_processed: bool = False
    processed_at: Optional[datetime] = None
    
    created_at: Optional[datetime] = None


class UsageAggregation(BaseModel):
    """使用量聚合模型"""
    id: Optional[int] = None
    aggregation_id: str = Field(..., description="聚合ID")
    
    # 聚合维度
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    service_type: Optional[ServiceType] = None
    product_id: Optional[str] = None
    
    # 时间周期
    period_start: datetime
    period_end: datetime
    period_type: str = Field(..., description="周期类型：hourly, daily, monthly")
    
    # 聚合数据
    total_usage_count: int = Field(default=0, ge=0)
    total_usage_amount: Decimal = Field(default=Decimal("0"), ge=0)
    total_cost: Decimal = Field(default=Decimal("0"), ge=0)
    
    # 服务详细使用量
    service_breakdown: Dict[str, Any] = Field(
        default_factory=dict,
        description="服务使用量详细分解"
    )
    
    # 计费状态
    is_billed: bool = False
    billed_at: Optional[datetime] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BillingQuota(BaseModel):
    """计费配额模型"""
    id: Optional[int] = None
    quota_id: str = Field(..., description="配额ID")
    
    # 配额所有者
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    
    # 配额范围
    service_type: ServiceType
    product_id: Optional[str] = None
    
    # 配额设置
    quota_limit: Decimal = Field(..., ge=0, description="配额限制")
    quota_used: Decimal = Field(default=Decimal("0"), ge=0, description="已使用配额")
    quota_period: str = Field(default="monthly", description="配额周期")
    
    # 重置设置
    reset_date: datetime = Field(..., description="下次重置日期")
    last_reset_date: Optional[datetime] = None
    auto_reset: bool = True
    
    # 状态
    is_active: bool = True
    is_exceeded: bool = False
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ====================
# 请求/响应模型
# ====================

class RecordUsageRequest(BaseModel):
    """记录使用量请求"""
    user_id: str
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    
    # 产品使用信息
    product_id: str
    service_type: ServiceType
    usage_amount: Decimal = Field(..., ge=0)
    
    # 会话信息
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # 使用详情
    usage_details: Optional[Dict[str, Any]] = None
    usage_timestamp: Optional[datetime] = None


class BillingCalculationRequest(BaseModel):
    """计费计算请求"""
    user_id: str
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    product_id: str
    usage_amount: Decimal = Field(..., ge=0)


class BillingCalculationResponse(BaseModel):
    """计费计算响应"""
    success: bool
    message: str
    
    # 计算结果
    product_id: str
    usage_amount: Decimal
    unit_price: Decimal
    total_cost: Decimal
    currency: Currency
    
    # 免费层和订阅包含
    is_free_tier: bool = False
    is_included_in_subscription: bool = False
    free_tier_remaining: Optional[Decimal] = None
    
    # 建议的计费方式
    suggested_billing_method: BillingMethod
    available_billing_methods: List[BillingMethod]
    
    # 用户余额信息
    wallet_balance: Optional[Decimal] = None
    credit_balance: Optional[Decimal] = None


class ProcessBillingRequest(BaseModel):
    """处理计费请求"""
    usage_record_id: str
    billing_method: BillingMethod
    force_process: bool = False  # 强制处理，即使余额不足


class ProcessBillingResponse(BaseModel):
    """处理计费响应"""
    success: bool
    message: str
    billing_record_id: Optional[str] = None
    
    # 处理结果
    amount_charged: Optional[Decimal] = None
    billing_method_used: Optional[BillingMethod] = None
    
    # 余额信息
    remaining_wallet_balance: Optional[Decimal] = None
    remaining_credit_balance: Optional[Decimal] = None
    
    # 关联的交易ID
    wallet_transaction_id: Optional[str] = None
    payment_transaction_id: Optional[str] = None


class UsageStatsRequest(BaseModel):
    """使用量统计请求"""
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    service_type: Optional[ServiceType] = None
    product_id: Optional[str] = None
    
    # 时间范围
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period_type: str = Field(default="daily", description="统计周期")


class UsageStatsResponse(BaseModel):
    """使用量统计响应"""
    period_start: datetime
    period_end: datetime
    period_type: str
    
    # 总体统计
    total_usage_records: int
    total_cost: Decimal
    total_usage_amount: Decimal
    
    # 服务分解
    service_breakdown: Dict[str, Dict[str, Any]]
    
    # 时间趋势
    time_series: List[Dict[str, Any]]
    
    # 计费方式分解
    billing_method_breakdown: Dict[BillingMethod, Decimal]


class QuotaCheckRequest(BaseModel):
    """配额检查请求"""
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    service_type: ServiceType
    product_id: Optional[str] = None
    requested_amount: Decimal = Field(..., ge=0)


class QuotaCheckResponse(BaseModel):
    """配额检查响应"""
    allowed: bool
    message: str
    
    # 配额信息
    quota_limit: Optional[Decimal] = None
    quota_used: Optional[Decimal] = None
    quota_remaining: Optional[Decimal] = None
    quota_period: Optional[str] = None
    next_reset_date: Optional[datetime] = None
    
    # 如果超出配额的建议
    suggested_actions: List[str] = Field(default_factory=list)


# ====================
# 系统模型
# ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    port: int
    version: str
    dependencies: Dict[str, str]  # 依赖服务状态


class ServiceInfo(BaseModel):
    """服务信息"""
    service: str
    version: str
    description: str
    capabilities: List[str]
    supported_services: List[ServiceType]
    supported_billing_methods: List[BillingMethod]


class BillingStats(BaseModel):
    """计费统计"""
    total_billing_records: int
    pending_billing_records: int
    completed_billing_records: int
    failed_billing_records: int
    
    # 金额统计
    total_revenue: Decimal
    revenue_by_service: Dict[ServiceType, Decimal]
    revenue_by_method: Dict[BillingMethod, Decimal]
    
    # 用户统计
    active_users: int
    active_organizations: int
    
    # 时间范围
    stats_period_start: datetime
    stats_period_end: datetime