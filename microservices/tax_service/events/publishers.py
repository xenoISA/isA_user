"""
Tax Service Event Publishers

Functions to publish events from tax service
"""

import logging
from typing import Optional, Dict, Any, List

from core.nats_client import Event
from .models import (
    TaxCalculatedEvent,
    TaxFailedEvent,
    TaxLineItem
)

logger = logging.getLogger(__name__)


async def publish_tax_calculated(
    event_bus,
    order_id: str,
    calculation_id: str,
    user_id: str,
    subtotal: float,
    total_tax: float,
    currency: str = "USD",
    tax_lines: Optional[List[TaxLineItem]] = None,
    shipping_address: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish tax.calculated event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping tax.calculated event")
        return False

    try:
        event_data = TaxCalculatedEvent(
            order_id=order_id,
            calculation_id=calculation_id,
            user_id=user_id,
            subtotal=subtotal,
            total_tax=total_tax,
            currency=currency,
            tax_lines=tax_lines or [],
            shipping_address=shipping_address,
            metadata=metadata or {}
        )

        event = Event(
            event_type="tax.calculated",
            source="tax_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published tax.calculated event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish tax.calculated event: {e}")
        return False


async def publish_tax_failed(
    event_bus,
    order_id: str,
    user_id: str,
    error_message: str,
    error_code: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish tax.failed event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping tax.failed event")
        return False

    try:
        event_data = TaxFailedEvent(
            order_id=order_id,
            user_id=user_id,
            error_code=error_code,
            error_message=error_message,
            items=items,
            metadata=metadata or {}
        )

        event = Event(
            event_type="tax.failed",
            source="tax_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published tax.failed event for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish tax.failed event: {e}")
        return False
