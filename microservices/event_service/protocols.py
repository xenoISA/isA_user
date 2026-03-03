"""
Event Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
from datetime import datetime

from .models import (
    Event, EventSource, EventCategory, EventStatus, EventStatistics,
    EventProcessingResult, EventProjection, EventProcessor, EventSubscription,
)


class EventServiceError(Exception):
    """Base exception for event service errors"""
    pass


class EventNotFoundError(Exception):
    """Event not found"""
    pass


@runtime_checkable
class EventRepositoryProtocol(Protocol):
    """Interface for Event Repository"""

    async def initialize(self) -> None: ...

    async def close(self) -> None: ...

    async def save_event(self, event: Event) -> Event: ...

    async def get_event(self, event_id: str) -> Optional[Event]: ...

    async def query_events(
        self, user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        event_source: Optional[EventSource] = None,
        event_category: Optional[EventCategory] = None,
        status: Optional[EventStatus] = None,
        correlation_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100, offset: int = 0,
    ) -> Tuple[List[Event], int]: ...

    async def update_event_status(
        self, event_id: str, status: EventStatus,
        error_message: Optional[str] = None,
        processed_at: Optional[datetime] = None,
    ) -> bool: ...

    async def update_event(self, event: Event) -> bool: ...

    async def get_unprocessed_events(self, limit: int = 100) -> List[Event]: ...

    async def get_statistics(self, user_id: Optional[str] = None) -> EventStatistics: ...

    async def save_processing_result(self, result: EventProcessingResult) -> None: ...

    async def save_projection(self, projection: EventProjection) -> None: ...

    async def get_projection(
        self, entity_type: str, entity_id: str, projection_name: str = "default",
    ) -> Optional[EventProjection]: ...

    async def save_processor(self, processor: EventProcessor) -> None: ...

    async def get_processors(self) -> List[EventProcessor]: ...

    async def save_subscription(self, subscription: EventSubscription) -> None: ...

    async def get_subscriptions(self) -> List[EventSubscription]: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
