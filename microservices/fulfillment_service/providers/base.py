"""Fulfillment provider interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class FulfillmentProvider(ABC):
    """Abstract fulfillment provider."""

    @abstractmethod
    async def create_shipment(self, order_id: str, items: List[Dict[str, Any]], address: Dict[str, Any]) -> Dict[str, Any]:
        """Create a shipment."""
        raise NotImplementedError
