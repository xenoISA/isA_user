"""
Calendar Service - Business Logic

日历事件管理业务逻辑层

Uses dependency injection for testability.
- Repository is injected, not created at import time
- Event publishers are lazily loaded
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Import protocols (no I/O dependencies) - NOT the concrete repository!
from .protocols import (
    CalendarEventRepositoryProtocol,
    CalendarEventNotFoundError,
    DuplicateEventError,
    InvalidDateRangeError,
)
from .models import (
    EventCreateRequest,
    EventListResponse,
    EventQueryRequest,
    EventResponse,
    EventUpdateRequest,
    RecurrenceType,
    SyncProvider,
    SyncStatusResponse,
)

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class CalendarServiceError(Exception):
    """Base exception for service errors"""
    pass


class CalendarServiceValidationError(CalendarServiceError):
    """Validation error"""
    pass


class CalendarService:
    """
    Calendar service business logic

    Handles all business operations while delegating
    data access to the repository layer.
    """

    def __init__(
        self,
        repository: Optional[CalendarEventRepositoryProtocol] = None,
        event_bus=None,
    ):
        """
        Initialize service with injected dependencies.

        Args:
            repository: Repository (inject mock for testing)
            event_bus: Event bus for publishing events
        """
        self.repo = repository  # Will be set by factory if None
        self.event_bus = event_bus
        self._event_publishers_loaded = False
        self._event_publisher = None

    def _lazy_load_event_publishers(self):
        """Lazy load event publishers to avoid import-time I/O"""
        if not self._event_publishers_loaded:
            try:
                # Import Event and EventType only when needed
                from core.nats_client import Event
                # Store them for later use
                self.Event = Event
                self.EventType = EventType
                self.ServiceSource = ServiceSource
            except ImportError:
                self.Event = None
                self.EventType = None
                self.ServiceSource = None
            self._event_publishers_loaded = True

    async def create_event(
        self, request: EventCreateRequest
    ) -> Optional[EventResponse]:
        """创建日历事件"""
        try:
            # Validate dates
            if request.end_time <= request.start_time:
                raise CalendarServiceValidationError("End time must be after start time")

            # Prepare event data
            event_data = request.dict()

            # Create event
            event = await self.repo.create_event(event_data)

            if event:
                logger.info(
                    f"Created event {event.event_id} for user {request.user_id}"
                )

                # Publish event.created event
                if self.event_bus:
                    try:
                        self._lazy_load_event_publishers()
                        if self.Event:
                            nats_event = self.Event(
                                event_type="calendar.event.created",
                                source="calendar_service",
                                data={
                                    "event_id": event.event_id,
                                    "user_id": request.user_id,
                                    "title": request.title,
                                    "start_time": request.start_time.isoformat(),
                                    "end_time": request.end_time.isoformat(),
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                            await self.event_bus.publish_event(nats_event)
                    except Exception as e:
                        logger.error(f"Failed to publish calendar.event.created event: {e}")

            return event

        except CalendarServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            raise

    async def get_event(
        self, event_id: str, user_id: str = None
    ) -> Optional[EventResponse]:
        """获取事件详情"""
        return await self.repo.get_event_by_id(event_id, user_id)

    async def query_events(self, request: EventQueryRequest) -> EventListResponse:
        """查询事件列表"""
        try:
            events = await self.repo.get_events_by_user(
                user_id=request.user_id,
                start_date=request.start_date,
                end_date=request.end_date,
                category=request.category.value if request.category else None,
                limit=request.limit,
                offset=request.offset,
            )

            # Get total count (simplified - in production use a separate count query)
            total = len(events)
            page = request.offset // request.limit + 1

            return EventListResponse(
                events=events, total=total, page=page, page_size=request.limit
            )

        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            raise

    async def get_upcoming_events(
        self, user_id: str, days: int = 7
    ) -> List[EventResponse]:
        """获取即将到来的事件"""
        return await self.repo.get_upcoming_events(user_id, days)

    async def get_today_events(self, user_id: str) -> List[EventResponse]:
        """获取今天的事件"""
        return await self.repo.get_today_events(user_id)

    async def update_event(
        self, event_id: str, request: EventUpdateRequest, user_id: str = None
    ) -> Optional[EventResponse]:
        """更新事件"""
        try:
            # Get existing event
            existing = await self.repo.get_event_by_id(event_id, user_id)
            if not existing:
                return None

            # Prepare updates
            updates = request.dict(exclude_unset=True)

            # Validate dates if both provided
            if "start_time" in updates and "end_time" in updates:
                if updates["end_time"] <= updates["start_time"]:
                    raise CalendarServiceValidationError("End time must be after start time")

            # Update event
            updated = await self.repo.update_event(event_id, updates)

            if updated:
                logger.info(f"Updated event {event_id}")

                # Publish event.updated event
                if self.event_bus:
                    try:
                        self._lazy_load_event_publishers()
                        if self.Event:
                            nats_event = self.Event(
                                event_type=".event.updated",
                                source="_service",
                                data={
                                    "event_id": event_id,
                                    "user_id": user_id,
                                    "updated_fields": list(updates.keys()),
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                            await self.event_bus.publish_event(nats_event)
                    except Exception as e:
                        logger.error(f"Failed to publish calendar.event.updated event: {e}")

            return updated

        except CalendarServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to update event {event_id}: {e}")
            raise

    async def delete_event(self, event_id: str, user_id: str = None) -> bool:
        """删除事件"""
        try:
            result = await self.repo.delete_event(event_id, user_id)

            if result and self.event_bus:
                try:
                    self._lazy_load_event_publishers()
                    if self.Event:
                        nats_event = self.Event(
                            event_type=".event.deleted",
                            source="_service",
                            data={
                                "event_id": event_id,
                                "user_id": user_id,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                        await self.event_bus.publish_event(nats_event)
                except Exception as e:
                    logger.error(f"Failed to publish calendar.event.deleted event: {e}")

            if result:
                logger.info(f"Deleted event {event_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            return False

    async def sync_with_external_calendar(
        self, user_id: str, provider: str, credentials: Dict[str, Any] = None
    ) -> SyncStatusResponse:
        """同步外部日历"""
        try:
            logger.info(f"Starting {provider} sync for user {user_id}")

            synced_count = 0

            if provider == SyncProvider.GOOGLE.value:
                synced_count = await self._sync_google_calendar(user_id, credentials)
            elif provider == SyncProvider.APPLE.value:
                synced_count = await self._sync_apple_calendar(user_id, credentials)
            elif provider == SyncProvider.OUTLOOK.value:
                synced_count = await self._sync_outlook_calendar(user_id, credentials)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            # Update sync status
            await self.repo.update_sync_status(
                user_id=user_id,
                provider=provider,
                status="active",
                synced_count=synced_count,
            )

            return SyncStatusResponse(
                provider=provider,
                last_synced=datetime.utcnow(),
                synced_events=synced_count,
                status="success",
                message=f"Successfully synced {synced_count} events"
            )

        except Exception as e:
            logger.error(f"Failed to sync {provider} calendar: {e}")

            # Update sync status with error
            await self.repo.update_sync_status(
                user_id=user_id, provider=provider, status="error", error_message=str(e)
            )

            return SyncStatusResponse(
                provider=provider,
                last_synced=datetime.utcnow(),
                synced_events=0,
                status="error",
                message=str(e),
            )

    async def get_sync_status(
        self, user_id: str, provider: str = None
    ) -> Optional[SyncStatusResponse]:
        """获取同步状态"""
        try:
            status = await self.repo.get_sync_status(user_id, provider)

            if status:
                return SyncStatusResponse(
                    provider=status.get("provider"),
                    last_synced=status.get("last_sync_time"),
                    synced_events=status.get("synced_events_count", 0),
                    status=status.get("status", "unknown"),
                    message=status.get("error_message"),
                )
            return None

        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return None

    # External calendar sync implementations

    async def _sync_google_calendar(self, user_id: str, credentials: Dict[str, Any]) -> int:
        """同步 Google Calendar"""
        # TODO: Implement Google Calendar API integration
        # Requirements:
        # 1. pip install google-auth google-auth-oauthlib google-api-python-client
        # 2. Use OAuth2 credentials
        # 3. Fetch events from primary calendar
        # 4. Insert/update events in local database

        logger.warning("Google Calendar sync not fully implemented yet")
        return 0

    async def _sync_apple_calendar(self, user_id: str, credentials: Dict[str, Any]) -> int:
        """同步 Apple iCloud Calendar"""
        # TODO: Implement Apple iCloud Calendar integration
        # Use CalDAV protocol

        logger.warning("Apple Calendar sync not fully implemented yet")
        return 0

    async def _sync_outlook_calendar(self, user_id: str, credentials: Dict[str, Any]) -> int:
        """同步 Microsoft Outlook Calendar"""
        # TODO: Implement Microsoft Graph API integration
        # Requirements:
        # 1. pip install msal requests
        # 2. Use Microsoft Graph API

        logger.warning("Outlook Calendar sync not fully implemented yet")
        return 0


__all__ = ["CalendarService"]

