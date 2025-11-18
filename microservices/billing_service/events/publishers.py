"""
Billing Event Publishers

发布 billing_service 产生的事件
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    BillingCalculatedEventData,
    BillingErrorEventData,
    UnitType,
    create_billing_calculated_event_data,
)

logger = logging.getLogger(__name__)


async def publish_billing_calculated(
    event_bus,
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
):
    """
    发布计费计算完成事件

    Args:
        event_bus: 事件总线实例
        user_id: 用户ID
        billing_record_id: 计费记录ID
        product_id: 产品ID
        actual_usage: 实际使用量
        unit_type: 单位类型
        token_equivalent: Token 等价值
        cost_usd: USD 成本
        unit_price: 单价
        token_conversion_rate: Token 转换率
        is_free_tier: 是否使用免费额度
        is_included_in_subscription: 是否包含在订阅中
        usage_event_id: 原始使用事件ID

    Returns:
        bool: 发布是否成功
    """
    try:
        # 构造事件数据
        event_data = create_billing_calculated_event_data(
            user_id=user_id,
            billing_record_id=billing_record_id,
            product_id=product_id,
            actual_usage=actual_usage,
            unit_type=unit_type,
            token_equivalent=token_equivalent,
            cost_usd=cost_usd,
            unit_price=unit_price,
            token_conversion_rate=token_conversion_rate,
            is_free_tier=is_free_tier,
            is_included_in_subscription=is_included_in_subscription,
            usage_event_id=usage_event_id,
        )

        # 创建事件对象
        event = Event(
            event_type=EventType.BILLING_CALCULATED,
            source=ServiceSource.BILLING_SERVICE,
            data=event_data.model_dump(),
        )

        # 发布事件
        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f"✅ Published billing.calculated event for billing_record {billing_record_id}, "
                f"user {user_id}, tokens {token_equivalent}"
            )
        else:
            logger.error(
                f"❌ Failed to publish billing.calculated event for {billing_record_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing billing_calculated event: {e}", exc_info=True)
        return False


async def publish_billing_error(
    event_bus,
    user_id: str,
    product_id: str,
    error_code: str,
    error_message: str,
    usage_event_id: Optional[str] = None,
    retry_count: int = 0,
):
    """
    发布计费错误事件

    Args:
        event_bus: 事件总线实例
        user_id: 用户ID
        product_id: 产品ID
        error_code: 错误码
        error_message: 错误消息
        usage_event_id: 原始使用事件ID
        retry_count: 重试次数

    Returns:
        bool: 发布是否成功
    """
    try:
        # 构造错误事件数据
        error_data = BillingErrorEventData(
            user_id=user_id,
            usage_event_id=usage_event_id,
            product_id=product_id,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count,
            timestamp=datetime.utcnow(),
        )

        # 创建事件对象
        event = Event(
            event_type=EventType.BILLING_RECORD_CREATED,  # 临时使用现有类型
            source=ServiceSource.BILLING_SERVICE,
            data=error_data.model_dump(),
        )

        # 修改为自定义类型
        event.type = "billing.error"

        # 发布事件
        result = await event_bus.publish_event(event)

        if result:
            logger.warning(
                f"⚠️  Published billing.error event for user {user_id}, "
                f"error_code {error_code}: {error_message}"
            )
        else:
            logger.error(f"❌ Failed to publish billing.error event for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"Error publishing billing_error event: {e}", exc_info=True)
        return False


async def publish_usage_recorded(
    event_bus,
    user_id: str,
    product_id: str,
    usage_amount: Decimal,
    unit_type: str,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    usage_details: Optional[dict] = None,
):
    """
    发布使用记录事件（用于通知其他服务）

    Args:
        event_bus: 事件总线实例
        user_id: 用户ID
        product_id: 产品ID
        usage_amount: 使用量
        unit_type: 单位类型
        session_id: 会话ID
        request_id: 请求ID
        usage_details: 使用详情

    Returns:
        bool: 发布是否成功
    """
    try:
        event_data = {
            "user_id": user_id,
            "product_id": product_id,
            "usage_amount": float(usage_amount),
            "unit_type": unit_type,
            "session_id": session_id,
            "request_id": request_id,
            "usage_details": usage_details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        event = Event(
            event_type=EventType.BILLING_RECORD_CREATED,
            source=ServiceSource.BILLING_SERVICE,
            data=event_data,
        )

        # Custom type
        event.type = "billing.usage.recorded"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f"✅ Published usage.recorded event for user {user_id}, "
                f"product {product_id}, usage {usage_amount}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing usage_recorded event: {e}", exc_info=True)
        return False
