"""
Inventory Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class InventoryServiceError(Exception):
    """Base exception for inventory service errors"""
    pass


class ReservationNotFoundError(Exception):
    """Reservation not found"""
    pass


@runtime_checkable
class InventoryRepositoryProtocol(Protocol):
    """Interface for Inventory Repository"""

    async def create_reservation(
        self, order_id: str, user_id: str, items: List[Dict[str, Any]],
        expires_in_minutes: int = 30, metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...

    async def get_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]: ...

    async def get_reservation_by_order(
        self, order_id: str, status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def get_active_reservation_for_order(self, order_id: str) -> Optional[Dict[str, Any]]: ...

    async def commit_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]: ...

    async def release_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]: ...

    async def list_reservations(
        self, limit: int = 50, offset: int = 0,
        order_id: Optional[str] = None, user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...


@runtime_checkable
class InventoryServiceProtocol(Protocol):
    """Interface for Inventory Service business logic"""

    async def reserve_inventory(
        self, order_id: str, items: List[Dict[str, Any]], user_id: str = "unknown",
    ) -> Dict[str, Any]: ...

    async def commit_reservation(
        self, order_id: str, reservation_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def release_reservation(
        self, order_id: str, reservation_id: Optional[str] = None,
        reason: str = "manual_release",
    ) -> Dict[str, Any]: ...

    async def get_reservation(self, order_id: str) -> Optional[Dict[str, Any]]: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
