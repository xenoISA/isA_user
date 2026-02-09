"""
Fulfillment Service Event Handlers

Handlers for events from other services - Uses PostgreSQL repository
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .publishers import (
    publish_shipment_prepared,
    publish_label_created,
    publish_shipment_canceled,
    publish_shipment_failed
)
from .models import ShipmentItem

logger = logging.getLogger(__name__)


async def handle_tax_calculated(
    event_data: Dict[str, Any],
    fulfillment_provider,
    repository,
    event_bus
) -> None:
    """
    Handle tax.calculated event

    Prepare shipment after tax is calculated (order is ready for fulfillment)
    """
    try:
        order_id = event_data.get("order_id")
        user_id = event_data.get("user_id")
        shipping_address = event_data.get("shipping_address") or {}
        metadata = event_data.get("metadata", {})

        if not order_id:
            logger.warning("tax.calculated event missing order_id")
            return

        logger.info(f"Processing tax.calculated event for order {order_id}")

        # Check if we already have a shipment for this order
        existing_shipment = await repository.get_shipment_by_order(order_id)

        if existing_shipment:
            logger.info(f"Shipment already exists for order {order_id}, skipping preparation")
            return

        # Get items from the original order (passed via metadata or from inventory event)
        items_data = metadata.get("items") or []

        # If no items in metadata, create placeholder
        if not items_data:
            items_data = [{"sku_id": "placeholder", "quantity": 1}]

        # Convert to ShipmentItem models
        shipment_items = []
        items_for_db = []
        total_weight = 0
        for item in items_data:
            sku_id = item.get("sku_id") or item.get("product_id") or "unknown"
            quantity = item.get("quantity", 1)
            weight = item.get("weight_grams", 500)  # Default 500g per item
            total_weight += weight * quantity

            shipment_items.append(ShipmentItem(
                sku_id=sku_id,
                quantity=quantity,
                weight_grams=weight
            ))
            items_for_db.append({
                "sku_id": sku_id,
                "quantity": quantity,
                "weight_grams": weight
            })

        # Create shipment in database
        shipment = await repository.create_shipment(
            order_id=order_id,
            user_id=user_id,
            items=items_for_db,
            shipping_address=shipping_address,
            metadata={"estimated_weight_grams": total_weight, "source_event": "tax.calculated"}
        )

        shipment_id = shipment["shipment_id"]

        # Publish shipment prepared event
        await publish_shipment_prepared(
            event_bus=event_bus,
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id,
            items=shipment_items,
            shipping_address=shipping_address,
            estimated_weight_grams=total_weight,
            metadata={"source_event": "tax.calculated"}
        )

        logger.info(f"Prepared shipment {shipment_id} for order {order_id}")

    except Exception as e:
        logger.error(f"Error handling tax.calculated event: {e}")
        try:
            await publish_shipment_failed(
                event_bus=event_bus,
                order_id=event_data.get("order_id", "unknown"),
                user_id=event_data.get("user_id", "unknown"),
                error_message=str(e),
                error_code="PREPARATION_ERROR"
            )
        except Exception as pub_error:
            logger.error(f"Failed to publish shipment.failed event: {pub_error}")


async def handle_payment_completed(
    event_data: Dict[str, Any],
    fulfillment_provider,
    repository,
    event_bus
) -> None:
    """
    Handle payment.completed event

    Create shipping label after payment is completed
    """
    try:
        # Extract order_id from payment event metadata or directly
        order_id = event_data.get("order_id")
        if not order_id:
            metadata = event_data.get("metadata", {})
            order_id = metadata.get("order_id")

        user_id = event_data.get("user_id")

        if not order_id:
            logger.warning("payment.completed event missing order_id")
            return

        logger.info(f"Processing payment.completed event for order {order_id}")

        # Find shipment for this order
        shipment = await repository.get_shipment_by_order(order_id)

        if not shipment:
            logger.warning(f"No shipment found for order {order_id}")
            return

        shipment_id = shipment["shipment_id"]

        if shipment["status"] == "label_purchased":
            logger.info(f"Label already created for shipment {shipment_id}")
            return

        # Create shipping label using provider
        try:
            items = shipment.get("items", [])
            shipping_address = shipment.get("shipping_address", {})

            label_result = await fulfillment_provider.create_shipment(
                order_id=order_id,
                items=items,
                address=shipping_address
            )

            # Get label info
            tracking_number = label_result.get("tracking_number", f"trk_{uuid4().hex[:10]}")
            carrier = label_result.get("carrier", "USPS")
            label_url = label_result.get("label_url")

            # Update shipment in database
            await repository.create_label(
                shipment_id=shipment_id,
                carrier=carrier,
                tracking_number=tracking_number,
                label_url=label_url
            )

            # Publish label created event
            await publish_label_created(
                event_bus=event_bus,
                order_id=order_id,
                shipment_id=shipment_id,
                user_id=user_id or shipment.get("user_id"),
                carrier=carrier,
                tracking_number=tracking_number,
                label_url=label_url,
                estimated_delivery=datetime.now(timezone.utc) + timedelta(days=5),
                metadata={"source_event": "payment.completed"}
            )

            logger.info(f"Created shipping label for order {order_id}, tracking: {tracking_number}")

        except Exception as label_error:
            logger.error(f"Failed to create label for order {order_id}: {label_error}")
            await publish_shipment_failed(
                event_bus=event_bus,
                order_id=order_id,
                user_id=user_id or shipment.get("user_id", "unknown"),
                error_message=str(label_error),
                error_code="LABEL_CREATION_ERROR"
            )

    except Exception as e:
        logger.error(f"Error handling payment.completed event: {e}")


async def handle_order_canceled(
    event_data: Dict[str, Any],
    fulfillment_provider,
    repository,
    event_bus
) -> None:
    """
    Handle order.canceled event

    Cancel shipment if order is canceled
    """
    try:
        order_id = event_data.get("order_id")
        user_id = event_data.get("user_id")
        cancellation_reason = event_data.get("cancellation_reason")

        if not order_id:
            logger.warning("order.canceled event missing order_id")
            return

        logger.info(f"Processing order.canceled event for order {order_id}")

        # Find shipment for this order
        shipment = await repository.get_shipment_by_order(order_id)

        if not shipment:
            logger.info(f"No shipment found for order {order_id} (may not have been prepared yet)")
            return

        shipment_id = shipment["shipment_id"]

        if shipment["status"] == "failed":
            logger.info(f"Shipment {shipment_id} already canceled")
            return

        # Determine if shipping should be refunded
        refund_shipping = shipment["status"] == "label_purchased"

        # Cancel shipment in database
        await repository.cancel_shipment(shipment_id, reason=cancellation_reason)

        # Publish shipment canceled event
        await publish_shipment_canceled(
            event_bus=event_bus,
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id or shipment.get("user_id"),
            reason=cancellation_reason or "order_canceled",
            refund_shipping=refund_shipping,
            metadata={"source_event": "order.canceled"}
        )

        logger.info(f"Canceled shipment {shipment_id} for order {order_id}")

    except Exception as e:
        logger.error(f"Error handling order.canceled event: {e}")


def get_event_handlers(
    fulfillment_provider,
    repository,
    event_bus
) -> Dict[str, callable]:
    """
    Return a mapping of event patterns to handler functions

    Event patterns include the service prefix for proper event routing.
    This will be used in main.py to register event subscriptions.

    Args:
        fulfillment_provider: Fulfillment provider instance
        repository: FulfillmentRepository instance for database operations
        event_bus: Event bus instance for publishing events

    Returns:
        Dict mapping event patterns to handler functions
    """
    return {
        "tax_service.tax.calculated": lambda event: handle_tax_calculated(
            event.data, fulfillment_provider, repository, event_bus
        ),
        "payment_service.payment.completed": lambda event: handle_payment_completed(
            event.data, fulfillment_provider, repository, event_bus
        ),
        "order_service.order.canceled": lambda event: handle_order_canceled(
            event.data, fulfillment_provider, repository, event_bus
        ),
    }
