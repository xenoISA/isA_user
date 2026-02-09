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
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


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
    CHARACTER = "character"  # TTS character count
    REQUEST = "request"  # API calls, tool executions
    BYTE = "byte"  # Storage (Minio, Qdrant)
    SECOND = "second"  # Video processing


class UsageEventData(BaseModel):
    """
    使用记录事件数据结构

    由以下服务发布：isA_Model, isA_MCP, storage_service 等
    billing_service 监听并处理此事件

    NATS Subject: billing.usage.recorded.{product_id}
    """

    # 用户上下文
    user_id: str = Field(..., description="触发使用的用户ID")
    organization_id: Optional[str] = Field(
        None, description="组织ID（如果在组织上下文中）"
    )
    subscription_id: Optional[str] = Field(None, description="活跃订阅ID")

    # 使用详情
    product_id: str = Field(
        ..., description="产品ID (gpt-4, dall-e-3, mcp-tool-web-search 等)"
    )
    usage_amount: Decimal = Field(..., description="使用量（原生单位）")
    unit_type: UnitType = Field(..., description="单位类型")

    # 会话追踪
    session_id: Optional[str] = Field(None, description="会话ID")
    request_id: Optional[str] = Field(None, description="请求追踪ID")

    # 元数据
    usage_details: Dict[str, Any] = Field(
        default_factory=dict, description="额外的使用详情"
    )
    timestamp: Optional[datetime] = Field(None, description="事件时间戳")

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
