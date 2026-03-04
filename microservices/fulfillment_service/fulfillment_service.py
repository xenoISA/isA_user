"""
Fulfillment Service Business Logic

Encapsulates shipment lifecycle: create, label, cancel, and tracking.
Extracted from main.py endpoints for testability and separation of concerns.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .protocols import FulfillmentRepositoryProtocol, EventBusProtocol
from .events.models import ShipmentItem
from .events.publishers import (
    publish_shipment_prepared,
    publish_label_created,
    publish_shipment_canceled,
)

logger = logging.getLogger(__name__)


class FulfillmentService:
    """Fulfillment service core business logic"""

    def __init__(
        self,
        repository: FulfillmentRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        provider=None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.provider = provider
        logger.info("FulfillmentService initialized with dependency injection")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_shipment(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        address: Dict[str, Any],
        user_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Create a shipment record for an order.

        Returns dict with shipment_id, order_id, status, tracking_number.
        Raises ValueError for invalid input.
        """
        if not order_id or not items or not address:
            raise ValueError("order_id, items, and address are required")

        # Get initial tracking info from provider
        result = await self.provider.create_shipment(
            order_id=order_id, items=items, address=address
        )

        shipment = await self.repository.create_shipment(
            order_id=order_id,
            user_id=user_id,
            items=items,
            shipping_address=address,
            tracking_number=result.get("tracking_number"),
            status="created",
        )

        shipment_id = shipment["shipment_id"]

        # Publish event (best-effort)
        shipment_items = self._build_shipment_items(items)
        await publish_shipment_prepared(
            event_bus=self.event_bus,
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id,
            items=shipment_items,
            shipping_address=address,
        )

        return {
            "shipment_id": shipment_id,
            "order_id": order_id,
            "status": "created",
            "tracking_number": result.get("tracking_number"),
        }

    async def create_label(self, shipment_id: str) -> Dict[str, Any]:
        """
        Create a shipping label for a shipment.

        Idempotent: returns existing label if already created.
        Raises LookupError if shipment not found.
        """
        shipment = await self.repository.get_shipment(shipment_id)
        if not shipment:
            raise LookupError("Shipment not found")

        # Idempotent — return existing label
        if shipment["status"] == "label_purchased":
            return {
                "shipment_id": shipment_id,
                "tracking_number": shipment["tracking_number"],
                "carrier": shipment["carrier"],
                "label_url": shipment["label_url"],
                "status": "label_created",
            }

        tracking_number = f"trk_{uuid4().hex[:10]}"
        carrier = "USPS"

        await self.repository.create_label(
            shipment_id=shipment_id,
            carrier=carrier,
            tracking_number=tracking_number,
        )

        estimated_delivery = datetime.now(timezone.utc) + timedelta(days=5)

        # Publish event (best-effort)
        await publish_label_created(
            event_bus=self.event_bus,
            order_id=shipment["order_id"],
            shipment_id=shipment_id,
            user_id=shipment.get("user_id", "unknown"),
            carrier=carrier,
            tracking_number=tracking_number,
            estimated_delivery=estimated_delivery,
        )

        return {
            "shipment_id": shipment_id,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "status": "label_created",
        }

    async def cancel_shipment(
        self,
        shipment_id: str,
        reason: str = "manual_cancellation",
    ) -> Dict[str, Any]:
        """
        Cancel a shipment.

        Idempotent: already-cancelled shipments return success.
        Sets refund_shipping if label was already purchased.
        Raises LookupError if shipment not found.
        """
        shipment = await self.repository.get_shipment(shipment_id)
        if not shipment:
            raise LookupError("Shipment not found")

        if shipment["status"] == "failed":
            return {
                "shipment_id": shipment_id,
                "status": "canceled",
                "message": "Already canceled",
            }

        refund_shipping = shipment["status"] == "label_purchased"

        await self.repository.cancel_shipment(shipment_id, reason=reason)

        # Publish event (best-effort)
        await publish_shipment_canceled(
            event_bus=self.event_bus,
            order_id=shipment["order_id"],
            shipment_id=shipment_id,
            user_id=shipment.get("user_id", "unknown"),
            reason=reason,
            refund_shipping=refund_shipping,
        )

        return {
            "shipment_id": shipment_id,
            "status": "canceled",
            "refund_shipping": refund_shipping,
        }

    async def get_shipment_by_order(
        self, order_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get shipment for an order."""
        return await self.repository.get_shipment_by_order(order_id)

    async def get_shipment_by_tracking(
        self, tracking_number: str
    ) -> Optional[Dict[str, Any]]:
        """Get shipment by tracking number."""
        return await self.repository.get_shipment_by_tracking(tracking_number)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_shipment_items(items: List[Dict[str, Any]]) -> List[ShipmentItem]:
        """Convert raw item dicts to ShipmentItem models."""
        return [
            ShipmentItem(
                sku_id=item.get("sku_id") or item.get("product_id") or "unknown",
                quantity=item.get("quantity", 1),
                weight_grams=item.get("weight_grams", 500),
            )
            for item in items
        ]
