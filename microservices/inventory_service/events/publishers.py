"""
Inventory Service Event Publishers

Functions to publish events from inventory service
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.nats_client import Event
from .models import (
    StockReservedEvent,
    StockCommittedEvent,
    StockReleasedEvent,
    StockFailedEvent,
    ReservedItem
)

logger = logging.getLogger(__name__)


async def publish_stock_reserved(
    event_bus,
    order_id: str,
    reservation_id: str,
    user_id: str,
    items: List[ReservedItem],
    expires_at: datetime,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish inventory.reserved event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping inventory.reserved event")
        return False

    try:
        event_data = StockReservedEvent(
            order_id=order_id,
            reservation_id=reservation_id,
            user_id=user_id,
            items=items,
            expires_at=expires_at,
            metadata=metadata or {}
        )

        event = Event(
            event_type="inventory.reserved",
            source="inventory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published inventory.reserved event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish inventory.reserved event: {e}")
        return False


async def publish_stock_committed(
    event_bus,
    order_id: str,
    reservation_id: str,
    user_id: str,
    items: List[ReservedItem],
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish inventory.committed event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping inventory.committed event")
        return False

    try:
        event_data = StockCommittedEvent(
            order_id=order_id,
            reservation_id=reservation_id,
            user_id=user_id,
            items=items,
            metadata=metadata or {}
        )

        event = Event(
            event_type="inventory.committed",
            source="inventory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published inventory.committed event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish inventory.committed event: {e}")
        return False


async def publish_stock_released(
    event_bus,
    order_id: str,
    user_id: str,
    items: List[ReservedItem],
    reservation_id: Optional[str] = None,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish inventory.released event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping inventory.released event")
        return False

    try:
        event_data = StockReleasedEvent(
            order_id=order_id,
            reservation_id=reservation_id,
            user_id=user_id,
            items=items,
            reason=reason,
            metadata=metadata or {}
        )

        event = Event(
            event_type="inventory.released",
            source="inventory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published inventory.released event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish inventory.released event: {e}")
        return False


async def publish_stock_failed(
    event_bus,
    order_id: str,
    user_id: str,
    items: List[Dict[str, Any]],
    error_message: str,
    error_code: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish inventory.failed event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping inventory.failed event")
        return False

    try:
        event_data = StockFailedEvent(
            order_id=order_id,
            user_id=user_id,
            items=items,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {}
        )

        event = Event(
            event_type="inventory.failed",
            source="inventory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published inventory.failed event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish inventory.failed event: {e}")
        return False
