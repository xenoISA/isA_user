"""
Inventory Service Business Logic

Encapsulates reservation lifecycle: reserve, commit, release, and expiry.
Extracted from main.py endpoints for testability and separation of concerns.
"""

import logging
from typing import Any, Dict, List, Optional

from .protocols import InventoryRepositoryProtocol, EventBusProtocol
from .events.models import ReservedItem
from .events.publishers import (
    publish_stock_reserved,
    publish_stock_committed,
    publish_stock_released,
    publish_stock_failed,
)

logger = logging.getLogger(__name__)


class InventoryService:
    """Inventory service core business logic"""

    def __init__(
        self,
        repository: InventoryRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        logger.info("InventoryService initialized with dependency injection")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def reserve_inventory(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        user_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Reserve inventory for an order.

        Returns dict with reservation_id, status, and expires_at.
        Raises ValueError for invalid input.
        """
        if not order_id or not items:
            raise ValueError("order_id and items are required")

        reservation = await self.repository.create_reservation(
            order_id=order_id,
            user_id=user_id,
            items=items,
            expires_in_minutes=30,
        )

        reservation_id = reservation["reservation_id"]
        expires_at = reservation["expires_at"]

        # Publish event (best-effort)
        reserved_items = self._build_reserved_items(items)
        if reserved_items:
            await publish_stock_reserved(
                event_bus=self.event_bus,
                order_id=order_id,
                reservation_id=reservation_id,
                user_id=user_id,
                items=reserved_items,
                expires_at=expires_at,
            )

        return {
            "reservation_id": reservation_id,
            "status": "active",
            "expires_at": expires_at,
        }

    async def commit_reservation(
        self,
        order_id: str,
        reservation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Commit a reservation after successful payment.

        Returns dict with order_id, reservation_id, and status.
        Raises ValueError for missing input, LookupError if not found.
        """
        if not order_id:
            raise ValueError("order_id is required")

        reservation = await self._find_reservation(order_id, reservation_id)
        if not reservation:
            raise LookupError("No active reservation found")

        res_id = reservation["reservation_id"]
        await self.repository.commit_reservation(res_id)

        # Publish event (best-effort)
        items = reservation.get("items", [])
        reserved_items = [ReservedItem(**item) for item in items]
        await publish_stock_committed(
            event_bus=self.event_bus,
            order_id=order_id,
            reservation_id=res_id,
            user_id=reservation.get("user_id", "unknown"),
            items=reserved_items,
        )

        return {
            "order_id": order_id,
            "reservation_id": res_id,
            "status": "committed",
        }

    async def release_reservation(
        self,
        order_id: str,
        reservation_id: Optional[str] = None,
        reason: str = "manual_release",
    ) -> Dict[str, Any]:
        """
        Release a reservation (order cancelled or manual).

        Returns dict with order_id, reservation_id, and status.
        If no active reservation exists, returns success with message.
        """
        if not order_id:
            raise ValueError("order_id is required")

        reservation = await self._find_reservation(order_id, reservation_id)
        if not reservation:
            return {
                "order_id": order_id,
                "status": "released",
                "message": "No active reservation found",
            }

        res_id = reservation["reservation_id"]
        await self.repository.release_reservation(res_id)

        # Publish event (best-effort)
        items = reservation.get("items", [])
        reserved_items = [ReservedItem(**item) for item in items]
        await publish_stock_released(
            event_bus=self.event_bus,
            order_id=order_id,
            reservation_id=res_id,
            user_id=reservation.get("user_id", "unknown"),
            items=reserved_items,
            reason=reason,
        )

        return {
            "order_id": order_id,
            "reservation_id": res_id,
            "status": "released",
        }

    async def get_reservation(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get reservation status for an order."""
        return await self.repository.get_reservation_by_order(order_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _find_reservation(
        self,
        order_id: str,
        reservation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find reservation by reservation_id first, then by order_id."""
        reservation = None
        if reservation_id:
            reservation = await self.repository.get_reservation(reservation_id)
        if not reservation:
            reservation = await self.repository.get_active_reservation_for_order(
                order_id
            )
        return reservation

    @staticmethod
    def _build_reserved_items(items: List[Dict[str, Any]]) -> List[ReservedItem]:
        """Convert raw item dicts to ReservedItem models."""
        reserved = []
        for item in items:
            sku_id = (
                item.get("sku_id") or item.get("product_id") or item.get("id")
            )
            if sku_id:
                reserved.append(
                    ReservedItem(
                        sku_id=sku_id,
                        quantity=item.get("quantity", 1),
                        unit_price=item.get("unit_price") or item.get("price"),
                    )
                )
        return reserved
