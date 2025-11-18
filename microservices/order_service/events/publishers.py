"""
Order Service Event Publishers

Functions to publish events from order service
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.nats_client import Event, EventType, ServiceSource
from .models import (
    OrderCreatedEvent,
    OrderUpdatedEvent,
    OrderCanceledEvent,
    OrderCompletedEvent,
    OrderExpiredEvent
)

logger = logging.getLogger(__name__)


async def publish_order_created(
    event_bus,
    order_id: str,
    user_id: str,
    order_type: str,
    total_amount: float,
    currency: str = "USD",
    payment_intent_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    wallet_id: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish order.created event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping order.created event")
        return False

    try:
        event_data = OrderCreatedEvent(
            order_id=order_id,
            user_id=user_id,
            order_type=order_type,
            total_amount=total_amount,
            currency=currency,
            payment_intent_id=payment_intent_id,
            subscription_id=subscription_id,
            wallet_id=wallet_id,
            items=items,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.ORDER_CREATED,
            source=ServiceSource.ORDER_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published order.created event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish order.created event: {e}")
        return False


async def publish_order_updated(
    event_bus,
    order_id: str,
    user_id: str,
    updated_fields: Dict[str, Any],
    old_status: Optional[str] = None,
    new_status: Optional[str] = None
) -> bool:
    """Publish order.updated event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping order.updated event")
        return False

    try:
        event_data = OrderUpdatedEvent(
            order_id=order_id,
            user_id=user_id,
            updated_fields=updated_fields,
            old_status=old_status,
            new_status=new_status
        )

        event = Event(
            event_type=EventType.ORDER_UPDATED,
            source=ServiceSource.ORDER_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published order.updated event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish order.updated event: {e}")
        return False


async def publish_order_canceled(
    event_bus,
    order_id: str,
    user_id: str,
    order_type: str,
    total_amount: float,
    currency: str = "USD",
    cancellation_reason: Optional[str] = None,
    refund_amount: Optional[float] = None
) -> bool:
    """Publish order.canceled event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping order.canceled event")
        return False

    try:
        event_data = OrderCanceledEvent(
            order_id=order_id,
            user_id=user_id,
            order_type=order_type,
            total_amount=total_amount,
            currency=currency,
            cancellation_reason=cancellation_reason,
            refund_amount=refund_amount
        )

        event = Event(
            event_type=EventType.ORDER_CANCELED,
            source=ServiceSource.ORDER_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published order.canceled event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish order.canceled event: {e}")
        return False


async def publish_order_completed(
    event_bus,
    order_id: str,
    user_id: str,
    order_type: str,
    total_amount: float,
    currency: str = "USD",
    payment_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    credits_added: Optional[float] = None
) -> bool:
    """Publish order.completed event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping order.completed event")
        return False

    try:
        event_data = OrderCompletedEvent(
            order_id=order_id,
            user_id=user_id,
            order_type=order_type,
            total_amount=total_amount,
            currency=currency,
            payment_id=payment_id,
            transaction_id=transaction_id,
            credits_added=credits_added
        )

        event = Event(
            event_type=EventType.ORDER_COMPLETED,
            source=ServiceSource.ORDER_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published order.completed event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish order.completed event: {e}")
        return False


async def publish_order_expired(
    event_bus,
    order_id: str,
    user_id: str,
    order_type: str,
    total_amount: float,
    expired_at: datetime,
    payment_intent_id: Optional[str] = None
) -> bool:
    """Publish order.expired event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping order.expired event")
        return False

    try:
        event_data = OrderExpiredEvent(
            order_id=order_id,
            user_id=user_id,
            order_type=order_type,
            total_amount=total_amount,
            expired_at=expired_at,
            payment_intent_id=payment_intent_id
        )

        event = Event(
            event_type=EventType.ORDER_EXPIRED,
            source=ServiceSource.ORDER_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published order.expired event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish order.expired event: {e}")
        return False
