"""
Fulfillment Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime


class FulfillmentServiceError(Exception):
    """Base exception for fulfillment service errors"""
    pass


class ShipmentNotFoundError(Exception):
    """Shipment not found"""
    pass


@runtime_checkable
class FulfillmentRepositoryProtocol(Protocol):
    """Interface for Fulfillment Repository"""

    async def create_shipment(
        self, order_id: str, user_id: str, items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any], carrier: Optional[str] = None,
        tracking_number: Optional[str] = None, status: str = "created",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...

    async def get_shipment(self, shipment_id: str) -> Optional[Dict[str, Any]]: ...

    async def get_shipment_by_order(self, order_id: str) -> Optional[Dict[str, Any]]: ...

    async def get_shipment_by_tracking(self, tracking_number: str) -> Optional[Dict[str, Any]]: ...

    async def update_shipment(
        self, shipment_id: str, status: Optional[str] = None,
        carrier: Optional[str] = None, tracking_number: Optional[str] = None,
        label_url: Optional[str] = None, estimated_delivery: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def create_label(
        self, shipment_id: str, carrier: str, tracking_number: str,
        label_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def cancel_shipment(
        self, shipment_id: str, reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def list_shipments(
        self, limit: int = 50, offset: int = 0,
        order_id: Optional[str] = None, user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
