"""
Inventory Service Event Handlers

Handlers for events from other services - Uses PostgreSQL repository
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

from .publishers import (
    publish_stock_reserved,
    publish_stock_committed,
    publish_stock_released,
    publish_stock_failed
)
from .models import ReservedItem

logger = logging.getLogger(__name__)


async def handle_order_created(
    event_data: Dict[str, Any],
    repository,
    event_bus
) -> None:
    """
    Handle order.created event

    Reserve inventory for the order items
    """
    try:
        order_id = event_data.get("order_id")
        user_id = event_data.get("user_id")
        items = event_data.get("items") or []

        if not order_id or not items:
            logger.warning("order.created event missing required fields (order_id or items)")
            return

        logger.info(f"Processing order.created event for order {order_id}")

        # Build reserved items list
        reserved_items = []
        items_for_db = []
        for item in items:
            sku_id = item.get("sku_id") or item.get("product_id") or item.get("id")
            quantity = item.get("quantity", 1)
            unit_price = item.get("unit_price") or item.get("price")

            if sku_id:
                reserved_items.append(ReservedItem(
                    sku_id=sku_id,
                    quantity=quantity,
                    unit_price=unit_price
                ))
                items_for_db.append({
                    "sku_id": sku_id,
                    "quantity": quantity,
                    "unit_price": unit_price
                })

        if not reserved_items:
            logger.warning(f"No valid items to reserve for order {order_id}")
            await publish_stock_failed(
                event_bus=event_bus,
                order_id=order_id,
                user_id=user_id,
                items=items,
                error_message="No valid items to reserve",
                error_code="NO_VALID_ITEMS"
            )
            return

        # Create reservation in database
        reservation = await repository.create_reservation(
            order_id=order_id,
            user_id=user_id,
            items=items_for_db,
            expires_in_minutes=30
        )

        reservation_id = reservation["reservation_id"]
        expires_at = reservation["expires_at"]

        # Publish stock reserved event
        await publish_stock_reserved(
            event_bus=event_bus,
            order_id=order_id,
            reservation_id=reservation_id,
            user_id=user_id,
            items=reserved_items,
            expires_at=expires_at,
            metadata={"source_event": "order.created"}
        )

        logger.info(f"Reserved inventory for order {order_id}, reservation {reservation_id}")

    except Exception as e:
        logger.error(f"Error handling order.created event: {e}")
        # Try to publish failure event
        try:
            await publish_stock_failed(
                event_bus=event_bus,
                order_id=event_data.get("order_id", "unknown"),
                user_id=event_data.get("user_id", "unknown"),
                items=event_data.get("items", []),
                error_message=str(e),
                error_code="RESERVATION_ERROR"
            )
        except Exception as pub_error:
            logger.error(f"Failed to publish stock.failed event: {pub_error}")


async def handle_payment_completed(
    event_data: Dict[str, Any],
    repository,
    event_bus
) -> None:
    """
    Handle payment.completed event

    Commit the inventory reservation
    """
    try:
        # Extract order_id from payment event metadata or directly
        order_id = event_data.get("order_id")
        if not order_id:
            # Try to find in metadata
            metadata = event_data.get("metadata", {})
            order_id = metadata.get("order_id")

        user_id = event_data.get("user_id")

        if not order_id:
            logger.warning("payment.completed event missing order_id")
            return

        logger.info(f"Processing payment.completed event for order {order_id}")

        # Find active reservation for this order
        reservation = await repository.get_active_reservation_for_order(order_id)

        if not reservation:
            logger.warning(f"No active reservation found for order {order_id}")
            return

        reservation_id = reservation["reservation_id"]

        # Commit reservation in database
        await repository.commit_reservation(reservation_id)

        # Build reserved items
        items = reservation.get("items", [])
        reserved_items = [ReservedItem(**item) for item in items]

        # Publish stock committed event
        await publish_stock_committed(
            event_bus=event_bus,
            order_id=order_id,
            reservation_id=reservation_id,
            user_id=user_id or reservation.get("user_id"),
            items=reserved_items,
            metadata={"source_event": "payment.completed"}
        )

        logger.info(f"Committed inventory for order {order_id}, reservation {reservation_id}")

    except Exception as e:
        logger.error(f"Error handling payment.completed event: {e}")


async def handle_order_canceled(
    event_data: Dict[str, Any],
    repository,
    event_bus
) -> None:
    """
    Handle order.canceled event

    Release the inventory reservation
    """
    try:
        order_id = event_data.get("order_id")
        user_id = event_data.get("user_id")
        cancellation_reason = event_data.get("cancellation_reason")

        if not order_id:
            logger.warning("order.canceled event missing order_id")
            return

        logger.info(f"Processing order.canceled event for order {order_id}")

        # Find active reservation for this order
        reservation = await repository.get_active_reservation_for_order(order_id)

        if not reservation:
            logger.info(f"No active reservation found for order {order_id} (may already be released)")
            return

        reservation_id = reservation["reservation_id"]

        # Release reservation in database
        await repository.release_reservation(reservation_id)

        # Build reserved items
        items = reservation.get("items", [])
        reserved_items = [ReservedItem(**item) for item in items]

        # Publish stock released event
        await publish_stock_released(
            event_bus=event_bus,
            order_id=order_id,
            reservation_id=reservation_id,
            user_id=user_id or reservation.get("user_id"),
            items=reserved_items,
            reason=cancellation_reason or "order_canceled",
            metadata={"source_event": "order.canceled"}
        )

        logger.info(f"Released inventory for order {order_id}, reservation {reservation_id}")

    except Exception as e:
        logger.error(f"Error handling order.canceled event: {e}")


def get_event_handlers(
    repository,
    event_bus
) -> Dict[str, callable]:
    """
    Return a mapping of event patterns to handler functions

    Event patterns include the service prefix for proper event routing.
    This will be used in main.py to register event subscriptions.

    Args:
        repository: InventoryRepository instance for database operations
        event_bus: Event bus instance for publishing events

    Returns:
        Dict mapping event patterns to handler functions
    """
    return {
        "order_service.order.created": lambda event: handle_order_created(
            event.data, repository, event_bus
        ),
        "payment_service.payment.completed": lambda event: handle_payment_completed(
            event.data, repository, event_bus
        ),
        "order_service.order.canceled": lambda event: handle_order_canceled(
            event.data, repository, event_bus
        ),
    }
