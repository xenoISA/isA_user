"""
Billing Event Data Models

billing_service 专属的事件数据结构定义
这些模型用于解析和构造事件数据

Event Architecture:
- BillingEventType: Events published by billing_service
- BillingSubscribedEventType: Events billing_service subscribes to
- Stream: billing-stream (subjects: billing.>)
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..models import BillingAccountType


# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class BillingEventType(str, Enum):
    """
    Events published by billing_service.

    These are the authoritative event types for this service.
    Other services should reference these when subscribing.
    """
    # Billing calculation events
    USAGE_RECORDED = "billing.usage.recorded"
    CALCULATED = "billing.calculated"
    PROCESSED = "billing.processed"

    # Invoice events
    INVOICE_CREATED = "billing.invoice.created"

    # Quota events
    QUOTA_EXCEEDED = "billing.quota.exceeded"

    # Error events
    ERROR = "billing.error"

    # Record events
    RECORD_CREATED = "billing.record.created"


class BillingSubscribedEventType(str, Enum):
    """
    Events that billing_service subscribes to from other services.
    """
    # Session events (from session_service)
    SESSION_TOKENS_USED = "session.tokens_used"
    SESSION_ENDED = "session.ended"

    # Order events (from order_service)
    ORDER_COMPLETED = "order.completed"

    # User lifecycle events (from account_service)
    USER_DELETED = "user.deleted"


class BillingStreamConfig:
    """Stream configuration for billing_service"""
    STREAM_NAME = "billing-stream"
    SUBJECTS = ["billing.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "billing"


class UnitType(str, Enum):
    """使用量单位类型"""

    TOKEN = "token"  # LLM tokens (GPT-4, embeddings)
    IMAGE = "image"  # Image generation
    MINUTE = "minute"  # Audio processing
    HOUR = "hour"
    CHARACTER = "character"  # TTS character count
    REQUEST = "request"  # API calls, tool executions
    URL = "url"
    BYTE = "byte"  # Storage (Minio, Qdrant)
    GB = "gb"
    GB_MONTH = "gb_month"
    EXECUTION = "execution"
    OPERATION = "operation"
    UNIT = "unit"
    SECOND = "second"  # Video processing


class BillingSurface(str, Enum):
    """Customer-facing abstraction for a billing event."""
    ABSTRACT_SERVICE = "abstract_service"
    ADD_ON = "add_on"


class CostComponentType(str, Enum):
    """Underlying component classes bundled into an abstract service."""
    RUNTIME = "runtime"
    TOKEN_COMPUTE = "token_compute"
    STORAGE = "storage"
    NETWORK = "network"
    EXTERNAL_API = "external_api"


class CostComponent(BaseModel):
    """Underlying resource or external API component for a usage event."""
    component_id: str = Field(..., description="Stable component identifier")
    component_type: CostComponentType = Field(
        ..., description="Underlying resource or API class"
    )
    bundled: bool = Field(
        default=True,
        description="Whether the component is bundled into the abstract service price",
    )
    customer_visible: bool = Field(
        default=False,
        description="Whether the component is intentionally exposed to customers",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Provider or implementation behind the component",
    )
    meter_type: Optional[str] = Field(
        default=None,
        description="Internal meter for the component when known",
    )
    unit_type: Optional[UnitType] = Field(
        default=None,
        description="Native unit used by the component when known",
    )
    usage_amount: Optional[Decimal] = Field(
        default=None,
        description="Underlying usage amount when the producer provides it",
    )
    notes: Optional[str] = None


class UsageEventData(BaseModel):
    """
    使用记录事件数据结构

    由以下服务发布：isA_Model, isA_MCP, storage_service 等
    billing_service 监听并处理此事件

    Canonical NATS subject family: billing.usage.recorded.>
    """

    # 用户上下文
    user_id: str = Field(..., description="触发使用的用户ID")
    actor_user_id: Optional[str] = Field(None, description="Human actor ID")
    billing_account_type: Optional[BillingAccountType] = Field(
        None, description="Canonical payer type"
    )
    billing_account_id: Optional[str] = Field(
        None, description="Canonical payer identifier"
    )
    organization_id: Optional[str] = Field(
        None, description="组织ID（如果在组织上下文中）"
    )
    agent_id: Optional[str] = Field(None, description="Agent identifier")
    subscription_id: Optional[str] = Field(None, description="活跃订阅ID")

    # 使用详情
    product_id: str = Field(
        ..., description="产品ID (gpt-4, dall-e-3, mcp-tool-web-search 等)"
    )
    service_type: Optional[str] = Field(
        None, description="Canonical service type"
    )
    operation_type: Optional[str] = Field(
        None, description="Canonical operation type"
    )
    source_service: Optional[str] = Field(
        None, description="Originating service name"
    )
    resource_name: Optional[str] = Field(
        None, description="Resource identifier within the service"
    )
    usage_amount: Decimal = Field(..., description="使用量（原生单位）")
    unit_type: UnitType = Field(..., description="单位类型")

    # 会话追踪
    session_id: Optional[str] = Field(None, description="会话ID")
    request_id: Optional[str] = Field(None, description="请求追踪ID")

    # 元数据
    usage_details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional usage details"
    )
    billing_surface: BillingSurface = Field(
        default=BillingSurface.ABSTRACT_SERVICE,
        description="Customer-facing abstraction for the invoiceable event",
    )
    cost_components: List[CostComponent] = Field(
        default_factory=list,
        description="Bundled underlying resource or external API components",
    )
    schema_version: Optional[str] = Field(
        None, description="Event schema version when provided by the publisher"
    )
    meter_type: Optional[str] = Field(
        None, description="Billing meter type when provided by the publisher"
    )
    credits_used: Optional[int] = Field(
        None, ge=0, description="Credits already calculated by the publisher"
    )
    cost_usd: Optional[Decimal] = Field(
        None, ge=0, description="USD cost already calculated by the publisher"
    )
    credit_consumption_handled: bool = Field(
        False, description="Whether credit deduction was already handled upstream"
    )
    idempotency_key: Optional[str] = Field(
        None, description="Idempotency key provided by the publisher"
    )
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {Decimal: lambda v: float(v), datetime: lambda v: v.isoformat()}


class BillingCalculatedEventData(BaseModel):
    """
    计费计算完成事件数据结构

    由 billing_service 发布
    wallet_service 监听并处理此事件（执行扣费）

    NATS Subject: billing.calculated
    """

    # 关联信息
    user_id: str = Field(..., description="用户ID")
    billing_record_id: str = Field(..., description="计费记录ID")
    usage_event_id: Optional[str] = Field(None, description="原始使用事件ID")

    # 产品信息
    product_id: str = Field(..., description="产品ID")
    actual_usage: Decimal = Field(..., description="原始使用量")
    unit_type: UnitType = Field(..., description="单位类型")

    # 成本计算
    token_equivalent: Decimal = Field(..., description="Token 等价值")
    cost_usd: Decimal = Field(..., description="实际 USD 成本")
    unit_price: Decimal = Field(..., description="单价 (USD)")

    # Token 转换率
    token_conversion_rate: Decimal = Field(
        ..., description="Token 转换率 (例如: 1 image = 1333 tokens)"
    )

    # 计费分类
    is_free_tier: bool = Field(False, description="是否使用免费额度")
    is_included_in_subscription: bool = Field(False, description="是否包含在订阅中")

    # 时间戳
    timestamp: Optional[datetime] = Field(None, description="计算时间")

    class Config:
        json_encoders = {Decimal: lambda v: float(v), datetime: lambda v: v.isoformat()}


class BillingErrorEventData(BaseModel):
    """
    计费错误事件数据结构

    当计费处理失败时发布
    notification_service 监听并通知用户

    NATS Subject: billing.error
    """

    user_id: str = Field(..., description="用户ID")
    usage_event_id: Optional[str] = Field(None, description="使用事件ID")
    product_id: str = Field(..., description="产品ID")

    # 错误信息
    error_code: str = Field(
        ..., description="错误码 (PRICING_NOT_FOUND, CALCULATION_FAILED 等)"
    )
    error_message: str = Field(..., description="错误消息")
    retry_count: int = Field(0, description="重试次数")

    # 时间戳
    timestamp: Optional[datetime] = Field(None, description="错误发生时间")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Helper functions for backward compatibility with isa_common
def parse_usage_event(event_data: dict) -> UsageEventData:
    """
    解析使用事件数据

    用于从 NATS 消息中解析事件数据
    """
    return UsageEventData(**event_data)


def create_billing_calculated_event_data(
    user_id: str,
    billing_record_id: str,
    product_id: str,
    actual_usage: Decimal,
    unit_type: UnitType,
    token_equivalent: Decimal,
    cost_usd: Decimal,
    unit_price: Decimal,
    token_conversion_rate: Decimal,
    is_free_tier: bool = False,
    is_included_in_subscription: bool = False,
    usage_event_id: Optional[str] = None,
) -> BillingCalculatedEventData:
    """
    创建计费计算完成事件数据

    便捷函数用于构造事件数据
    """
    return BillingCalculatedEventData(
        user_id=user_id,
        billing_record_id=billing_record_id,
        usage_event_id=usage_event_id,
        product_id=product_id,
        actual_usage=actual_usage,
        unit_type=unit_type,
        token_equivalent=token_equivalent,
        cost_usd=cost_usd,
        unit_price=unit_price,
        token_conversion_rate=token_conversion_rate,
        is_free_tier=is_free_tier,
        is_included_in_subscription=is_included_in_subscription,
        timestamp=datetime.utcnow(),
    )
