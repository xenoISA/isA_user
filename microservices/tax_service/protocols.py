"""
Tax Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class TaxServiceError(Exception):
    """Base exception for tax service errors"""
    pass


class TaxCalculationNotFoundError(Exception):
    """Tax calculation not found"""
    pass


@runtime_checkable
class TaxRepositoryProtocol(Protocol):
    """Interface for Tax Repository"""

    async def create_calculation(
        self, order_id: str, user_id: str, subtotal: float, total_tax: float,
        currency: str = "USD", tax_lines: Optional[List[Dict[str, Any]]] = None,
        shipping_address: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...

    async def get_calculation(self, calculation_id: str) -> Optional[Dict[str, Any]]: ...

    async def get_calculation_by_order(self, order_id: str) -> Optional[Dict[str, Any]]: ...

    async def list_calculations(
        self, limit: int = 50, offset: int = 0,
        order_id: Optional[str] = None, user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...


@runtime_checkable
class TaxProviderProtocol(Protocol):
    """Interface for Tax Provider"""

    async def calculate(
        self, items: List[Dict[str, Any]], address: Dict[str, Any],
        currency: str = "USD",
    ) -> Dict[str, Any]: ...


@runtime_checkable
class TaxServiceProtocol(Protocol):
    """Interface for Tax Service business logic"""

    async def calculate_tax(
        self, items: List[Dict[str, Any]], address: Dict[str, Any],
        currency: str = "USD", order_id: Optional[str] = None,
        user_id: str = "unknown",
    ) -> Dict[str, Any]: ...

    async def get_calculation(self, order_id: str) -> Optional[Dict[str, Any]]: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
