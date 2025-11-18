"""
Event Service - Event Publishers

Functions to publish events from the event service.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .models import (
    EventCreatedEvent,
    EventProcessedEvent,
    EventFailedEvent,
    EventReplayStartedEvent,
    EventReplayCompletedEvent,
)

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publisher for event service events"""

    def __init__(self, event_bus):
        """
        Initialize event publisher

        Args:
            event_bus: NATS event bus instance
        """
        self.event_bus = event_bus

    async def publish_event_created(
        self,
        event_id: str,
        event_type: str,
        event_source: str,
        event_category: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish event created event

        Args:
            event_id: Event ID
            event_type: Type of event
            event_source: Source of event
            event_category: Category of event
            user_id: User ID (optional)
            organization_id: Organization ID (optional)
            data: Event data (optional)

        Returns:
            True if published successfully
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping event.created publication")
            return False

        try:
            event = EventCreatedEvent(
                event_id=event_id,
                event_type=event_type,
                event_source=event_source,
                event_category=event_category,
                user_id=user_id,
                organization_id=organization_id,
                data=data or {},
            )

            await self.event_bus.publish(
                subject=f"events.service.event.created",
                data=event.model_dump(),
                headers={
                    "event_id": event_id,
                    "event_type": event_type,
                    "source": "event_service",
                },
            )

            logger.debug(f"Published event.created for event_id={event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event.created: {e}")
            return False

    async def publish_event_processed(
        self,
        event_id: str,
        processor_name: str,
        status: str,
        duration_ms: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish event processed event

        Args:
            event_id: Event ID
            processor_name: Name of processor
            status: Processing status
            duration_ms: Processing duration in milliseconds (optional)
            result: Processing result data (optional)

        Returns:
            True if published successfully
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping event.processed publication")
            return False

        try:
            event = EventProcessedEvent(
                event_id=event_id,
                processor_name=processor_name,
                status=status,
                duration_ms=duration_ms,
                result=result,
            )

            await self.event_bus.publish(
                subject=f"events.service.event.processed",
                data=event.model_dump(),
                headers={
                    "event_id": event_id,
                    "processor": processor_name,
                    "source": "event_service",
                },
            )

            logger.debug(f"Published event.processed for event_id={event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event.processed: {e}")
            return False

    async def publish_event_failed(
        self,
        event_id: str,
        processor_name: str,
        error_message: str,
        error_type: str,
        retry_count: int = 0,
        will_retry: bool = False,
    ) -> bool:
        """
        Publish event failed event

        Args:
            event_id: Event ID
            processor_name: Name of processor
            error_message: Error message
            error_type: Type of error
            retry_count: Number of retries
            will_retry: Whether will retry

        Returns:
            True if published successfully
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping event.failed publication")
            return False

        try:
            event = EventFailedEvent(
                event_id=event_id,
                processor_name=processor_name,
                error_message=error_message,
                error_type=error_type,
                retry_count=retry_count,
                will_retry=will_retry,
            )

            await self.event_bus.publish(
                subject=f"events.service.event.failed",
                data=event.model_dump(),
                headers={
                    "event_id": event_id,
                    "processor": processor_name,
                    "source": "event_service",
                },
            )

            logger.debug(f"Published event.failed for event_id={event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event.failed: {e}")
            return False

    async def publish_replay_started(
        self,
        replay_id: str,
        start_time: datetime,
        end_time: datetime,
        event_types: Optional[list] = None,
        target_service: Optional[str] = None,
    ) -> bool:
        """
        Publish event replay started event

        Args:
            replay_id: Replay job ID
            start_time: Start time
            end_time: End time
            event_types: Event types to replay (optional)
            target_service: Target service (optional)

        Returns:
            True if published successfully
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping replay.started publication")
            return False

        try:
            event = EventReplayStartedEvent(
                replay_id=replay_id,
                start_time=start_time,
                end_time=end_time,
                event_types=event_types,
                target_service=target_service,
            )

            await self.event_bus.publish(
                subject=f"events.service.replay.started",
                data=event.model_dump(),
                headers={
                    "replay_id": replay_id,
                    "source": "event_service",
                },
            )

            logger.info(f"Published replay.started for replay_id={replay_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish replay.started: {e}")
            return False

    async def publish_replay_completed(
        self,
        replay_id: str,
        events_replayed: int,
        duration_ms: int,
        success: bool = True,
    ) -> bool:
        """
        Publish event replay completed event

        Args:
            replay_id: Replay job ID
            events_replayed: Number of events replayed
            duration_ms: Total duration in milliseconds
            success: Whether replay was successful

        Returns:
            True if published successfully
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping replay.completed publication")
            return False

        try:
            event = EventReplayCompletedEvent(
                replay_id=replay_id,
                events_replayed=events_replayed,
                duration_ms=duration_ms,
                success=success,
            )

            await self.event_bus.publish(
                subject=f"events.service.replay.completed",
                data=event.model_dump(),
                headers={
                    "replay_id": replay_id,
                    "source": "event_service",
                },
            )

            logger.info(f"Published replay.completed for replay_id={replay_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish replay.completed: {e}")
            return False


# Convenience functions for standalone usage
async def publish_event_created(
    event_bus,
    event_id: str,
    event_type: str,
    event_source: str,
    event_category: str,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Publish event created event (convenience function)"""
    publisher = EventPublisher(event_bus)
    return await publisher.publish_event_created(
        event_id=event_id,
        event_type=event_type,
        event_source=event_source,
        event_category=event_category,
        user_id=user_id,
        organization_id=organization_id,
        data=data,
    )


async def publish_event_processed(
    event_bus,
    event_id: str,
    processor_name: str,
    status: str,
    duration_ms: Optional[int] = None,
    result: Optional[Dict[str, Any]] = None,
) -> bool:
    """Publish event processed event (convenience function)"""
    publisher = EventPublisher(event_bus)
    return await publisher.publish_event_processed(
        event_id=event_id,
        processor_name=processor_name,
        status=status,
        duration_ms=duration_ms,
        result=result,
    )


async def publish_event_failed(
    event_bus,
    event_id: str,
    processor_name: str,
    error_message: str,
    error_type: str,
    retry_count: int = 0,
    will_retry: bool = False,
) -> bool:
    """Publish event failed event (convenience function)"""
    publisher = EventPublisher(event_bus)
    return await publisher.publish_event_failed(
        event_id=event_id,
        processor_name=processor_name,
        error_message=error_message,
        error_type=error_type,
        retry_count=retry_count,
        will_retry=will_retry,
    )


__all__ = [
    "EventPublisher",
    "publish_event_created",
    "publish_event_processed",
    "publish_event_failed",
]
