"""Mock fulfillment provider."""

from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List

from .base import FulfillmentProvider


class MockFulfillmentProvider(FulfillmentProvider):
    async def create_shipment(self, order_id: str, items: List[Dict[str, Any]], address: Dict[str, Any]) -> Dict[str, Any]:
        shipment_id = f"shp_{uuid4().hex[:12]}"
        tracking_number = f"trk_{uuid4().hex[:10]}"
        return {
            "shipment_id": shipment_id,
            "order_id": order_id,
            "tracking_number": tracking_number,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
        }
