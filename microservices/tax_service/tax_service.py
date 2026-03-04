"""
Tax Service Business Logic

Encapsulates tax calculation, persistence, and retrieval.
Extracted from main.py endpoints for testability and separation of concerns.
"""

import logging
from typing import Any, Dict, List, Optional

from .protocols import TaxRepositoryProtocol, EventBusProtocol
from .events.models import TaxLineItem
from .events.publishers import publish_tax_calculated

logger = logging.getLogger(__name__)


class TaxService:
    """Tax service core business logic"""

    def __init__(
        self,
        repository: TaxRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        provider=None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.provider = provider
        logger.info("TaxService initialized with dependency injection")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def calculate_tax(
        self,
        items: List[Dict[str, Any]],
        address: Dict[str, Any],
        currency: str = "USD",
        order_id: Optional[str] = None,
        user_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Calculate tax for items and a shipping address.

        If order_id is provided, the calculation is persisted and an event published.
        Otherwise it's a preview (not stored).

        Returns the provider result dict, augmented with calculation_id and
        order_id when persisted.
        Raises ValueError for invalid input.
        """
        if not items or not address:
            raise ValueError("items and address are required")

        result = await self.provider.calculate(
            items=items, address=address, currency=currency
        )

        if order_id and self.repository:
            subtotal = self._compute_subtotal(items)

            calculation = await self.repository.create_calculation(
                order_id=order_id,
                user_id=user_id,
                subtotal=subtotal,
                total_tax=result.get("total_tax", 0),
                currency=currency,
                tax_lines=result.get("lines", []),
                shipping_address=address,
            )

            calculation_id = calculation["calculation_id"]

            # Publish event (best-effort)
            tax_lines = self._build_tax_lines(result.get("lines", []))
            await publish_tax_calculated(
                event_bus=self.event_bus,
                order_id=order_id,
                calculation_id=calculation_id,
                user_id=user_id,
                subtotal=subtotal,
                total_tax=result.get("total_tax", 0),
                currency=currency,
                tax_lines=tax_lines,
                shipping_address=address,
            )

            result["calculation_id"] = calculation_id
            result["order_id"] = order_id

        return result

    async def get_calculation(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get tax calculation for an order. Returns None if not found."""
        return await self.repository.get_calculation_by_order(order_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_subtotal(items: List[Dict[str, Any]]) -> float:
        """Compute pre-tax subtotal from items."""
        return sum(
            item.get("amount", 0)
            or (item.get("unit_price", 0) * item.get("quantity", 1))
            for item in items
        )

    @staticmethod
    def _build_tax_lines(lines: List[Dict[str, Any]]) -> List[TaxLineItem]:
        """Convert raw provider lines to TaxLineItem models."""
        return [
            TaxLineItem(
                line_item_id=line.get("line_item_id", f"line_{i}"),
                sku_id=line.get("sku_id"),
                tax_amount=float(line.get("tax_amount", 0)),
                tax_rate=float(line.get("rate", 0)),
                jurisdiction=line.get("jurisdiction"),
                tax_type=line.get("tax_type"),
            )
            for i, line in enumerate(lines)
        ]
