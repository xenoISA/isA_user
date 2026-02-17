"""
Fulfillment Service Event Publishers

Functions to publish events from fulfillment service
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.nats_client import Event
from .models import (
    ShipmentPreparedEvent,
    LabelCreatedEvent,
    ShipmentCanceledEvent,
    ShipmentFailedEvent,
    ShipmentItem
)

logger = logging.getLogger(__name__)


async def publish_shipment_prepared(
    event_bus,
    order_id: str,
    shipment_id: str,
    user_id: str,
    items: List[ShipmentItem],
    shipping_address: Dict[str, Any],
    estimated_weight_grams: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish fulfillment.shipment.prepared event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping fulfillment.shipment.prepared event")
        return False

    try:
        event_data = ShipmentPreparedEvent(
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id,
            items=items,
            shipping_address=shipping_address,
            estimated_weight_grams=estimated_weight_grams,
            metadata=metadata or {}
        )

        event = Event(
            event_type="fulfillment.shipment.prepared",
            source="fulfillment_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published fulfillment.shipment.prepared event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish fulfillment.shipment.prepared event: {e}")
        return False


async def publish_label_created(
    event_bus,
    order_id: str,
    shipment_id: str,
    user_id: str,
    carrier: str,
    tracking_number: str,
    label_url: Optional[str] = None,
    estimated_delivery: Optional[datetime] = None,
    shipping_cost: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish fulfillment.label.created event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping fulfillment.label.created event")
        return False

    try:
        event_data = LabelCreatedEvent(
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id,
            carrier=carrier,
            tracking_number=tracking_number,
            label_url=label_url,
            estimated_delivery=estimated_delivery,
            shipping_cost=shipping_cost,
            metadata=metadata or {}
        )

        event = Event(
            event_type="fulfillment.label.created",
            source="fulfillment_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published fulfillment.label.created event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish fulfillment.label.created event: {e}")
        return False


async def publish_shipment_canceled(
    event_bus,
    order_id: str,
    shipment_id: str,
    user_id: str,
    reason: Optional[str] = None,
    refund_shipping: bool = False,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish fulfillment.shipment.canceled event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping fulfillment.shipment.canceled event")
        return False

    try:
        event_data = ShipmentCanceledEvent(
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id,
            reason=reason,
            refund_shipping=refund_shipping,
            metadata=metadata or {}
        )

        event = Event(
            event_type="fulfillment.shipment.canceled",
            source="fulfillment_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published fulfillment.shipment.canceled event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish fulfillment.shipment.canceled event: {e}")
        return False


async def publish_shipment_failed(
    event_bus,
    order_id: str,
    user_id: str,
    error_message: str,
    error_code: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish fulfillment.shipment.failed event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping fulfillment.shipment.failed event")
        return False

    try:
        event_data = ShipmentFailedEvent(
            order_id=order_id,
            user_id=user_id,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {}
        )

        event = Event(
            event_type="fulfillment.shipment.failed",
            source="fulfillment_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published fulfillment.shipment.failed event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish fulfillment.shipment.failed event: {e}")
        return False
