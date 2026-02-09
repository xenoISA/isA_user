"""
Tax Service Event Handlers

Handlers for events from other services - Uses PostgreSQL repository
"""

import logging
from typing import Dict, Any

from .publishers import publish_tax_calculated, publish_tax_failed
from .models import TaxLineItem

logger = logging.getLogger(__name__)


async def handle_inventory_reserved(
    event_data: Dict[str, Any],
    tax_provider,
    repository,
    event_bus
) -> None:
    """
    Handle inventory.reserved event

    Calculate tax for the order after inventory is reserved
    """
    try:
        order_id = event_data.get("order_id")
        user_id = event_data.get("user_id")
        items = event_data.get("items") or []
        metadata = event_data.get("metadata", {})

        if not order_id or not items:
            logger.warning("inventory.reserved event missing required fields (order_id or items)")
            return

        logger.info(f"Processing inventory.reserved event for order {order_id}")

        # Extract shipping address from metadata if available
        shipping_address = metadata.get("shipping_address") or metadata.get("address")

        # If no address in metadata, use a default (tax provider should handle this)
        if not shipping_address:
            shipping_address = {
                "country": "US",
                "state": "CA",
                "city": "San Francisco",
                "postal_code": "94102"
            }

        # Convert items to tax calculation format
        tax_items = []
        subtotal = 0.0
        for item in items:
            sku_id = item.get("sku_id") or item.get("product_id")
            quantity = item.get("quantity", 1)
            unit_price = item.get("unit_price") or 0.0
            line_total = unit_price * quantity
            subtotal += line_total

            tax_items.append({
                "id": sku_id,
                "sku_id": sku_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": line_total
            })

        # Calculate tax using the provider
        try:
            tax_result = await tax_provider.calculate(
                items=tax_items,
                address=shipping_address,
                currency="USD"
            )

            total_tax = tax_result.get("total_tax", 0.0)
            tax_lines_raw = tax_result.get("lines", [])

            # Convert to TaxLineItem models
            tax_lines = []
            tax_lines_for_db = []
            for i, line in enumerate(tax_lines_raw):
                tax_lines.append(TaxLineItem(
                    line_item_id=line.get("line_item_id", f"line_{i}"),
                    sku_id=line.get("sku_id"),
                    tax_amount=float(line.get("tax_amount", 0)),
                    tax_rate=float(line.get("rate", 0)),
                    jurisdiction=line.get("jurisdiction"),
                    tax_type=line.get("tax_type")
                ))
                tax_lines_for_db.append({
                    "line_item_id": line.get("line_item_id", f"line_{i}"),
                    "sku_id": line.get("sku_id"),
                    "tax_amount": float(line.get("tax_amount", 0)),
                    "rate": float(line.get("rate", 0)),
                    "jurisdiction": line.get("jurisdiction"),
                    "tax_type": line.get("tax_type")
                })

            # If no tax lines from provider, create a summary line
            if not tax_lines and total_tax > 0:
                tax_lines.append(TaxLineItem(
                    line_item_id="total",
                    tax_amount=total_tax,
                    tax_rate=total_tax / subtotal if subtotal > 0 else 0,
                    jurisdiction=shipping_address.get("state") or shipping_address.get("country"),
                    tax_type="sales_tax"
                ))
                tax_lines_for_db.append({
                    "line_item_id": "total",
                    "tax_amount": total_tax,
                    "rate": total_tax / subtotal if subtotal > 0 else 0,
                    "jurisdiction": shipping_address.get("state") or shipping_address.get("country"),
                    "tax_type": "sales_tax"
                })

            # Store calculation in database
            calculation = await repository.create_calculation(
                order_id=order_id,
                user_id=user_id,
                subtotal=subtotal,
                total_tax=total_tax,
                currency="USD",
                tax_lines=tax_lines_for_db,
                shipping_address=shipping_address,
                metadata={"source_event": "inventory.reserved"}
            )

            calculation_id = calculation["calculation_id"]

            # Publish tax calculated event
            await publish_tax_calculated(
                event_bus=event_bus,
                order_id=order_id,
                calculation_id=calculation_id,
                user_id=user_id,
                subtotal=subtotal,
                total_tax=total_tax,
                currency="USD",
                tax_lines=tax_lines,
                shipping_address=shipping_address,
                metadata={"source_event": "inventory.reserved"}
            )

            logger.info(f"Calculated tax for order {order_id}: ${total_tax:.2f}")

        except Exception as calc_error:
            logger.error(f"Tax calculation failed for order {order_id}: {calc_error}")
            await publish_tax_failed(
                event_bus=event_bus,
                order_id=order_id,
                user_id=user_id,
                error_message=str(calc_error),
                error_code="CALCULATION_ERROR",
                items=tax_items,
                metadata={"source_event": "inventory.reserved"}
            )

    except Exception as e:
        logger.error(f"Error handling inventory.reserved event: {e}")
        try:
            await publish_tax_failed(
                event_bus=event_bus,
                order_id=event_data.get("order_id", "unknown"),
                user_id=event_data.get("user_id", "unknown"),
                error_message=str(e),
                error_code="HANDLER_ERROR"
            )
        except Exception as pub_error:
            logger.error(f"Failed to publish tax.failed event: {pub_error}")


def get_event_handlers(
    tax_provider,
    repository,
    event_bus
) -> Dict[str, callable]:
    """
    Return a mapping of event patterns to handler functions

    Event patterns include the service prefix for proper event routing.
    This will be used in main.py to register event subscriptions.

    Args:
        tax_provider: Tax provider instance for calculations
        repository: TaxRepository instance for database operations
        event_bus: Event bus instance for publishing events

    Returns:
        Dict mapping event patterns to handler functions
    """
    return {
        "inventory_service.inventory.reserved": lambda event: handle_inventory_reserved(
            event.data, tax_provider, repository, event_bus
        ),
    }
