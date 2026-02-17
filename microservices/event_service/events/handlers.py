"""
Event Service - Event Handlers

Handlers for processing events subscribed by the event service.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class EventHandlers:
    """Event handlers for the event service"""

    def __init__(self, event_service=None):
        """
        Initialize event handlers

        Args:
            event_service: Reference to the event service instance
        """
        self.event_service = event_service

    async def handle_event_created(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle event.created events from other services

        Args:
            event_data: Event data dictionary

        Returns:
            True if handled successfully
        """
        try:
            event_id = event_data.get("event_id")
            event_type = event_data.get("event_type")

            logger.info(f"Handling event.created: event_id={event_id}, type={event_type}")

            # Process the event (e.g., store in database, trigger workflows)
            if self.event_service:
                # Example: Store the event
                # await self.event_service.store_external_event(event_data)
                pass

            return True

        except Exception as e:
            logger.error(f"Error handling event.created: {e}")
            return False

    async def handle_event_processed(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle event.processed events

        Args:
            event_data: Event data dictionary

        Returns:
            True if handled successfully
        """
        try:
            event_id = event_data.get("event_id")
            processor_name = event_data.get("processor_name")
            status = event_data.get("status")

            logger.info(
                f"Handling event.processed: event_id={event_id}, "
                f"processor={processor_name}, status={status}"
            )

            # Update processing status, metrics, etc.
            if self.event_service:
                # Example: Update event processing metrics
                # await self.event_service.update_processing_metrics(event_id, status)
                pass

            return True

        except Exception as e:
            logger.error(f"Error handling event.processed: {e}")
            return False

    async def handle_event_failed(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle event.failed events

        Args:
            event_data: Event data dictionary

        Returns:
            True if handled successfully
        """
        try:
            event_id = event_data.get("event_id")
            processor_name = event_data.get("processor_name")
            error_message = event_data.get("error_message")
            will_retry = event_data.get("will_retry", False)

            logger.warning(
                f"Handling event.failed: event_id={event_id}, "
                f"processor={processor_name}, will_retry={will_retry}, "
                f"error={error_message}"
            )

            # Handle failure (e.g., alert, retry logic, dead letter queue)
            if self.event_service:
                # Example: Move to dead letter queue if not retrying
                # if not will_retry:
                #     await self.event_service.move_to_dlq(event_id)
                pass

            return True

        except Exception as e:
            logger.error(f"Error handling event.failed: {e}")
            return False

    async def handle_service_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Generic handler for service events

        Args:
            event_data: Event data dictionary

        Returns:
            True if handled successfully
        """
        try:
            event_type = event_data.get("event_type")
            source_service = event_data.get("source", "unknown")

            logger.debug(
                f"Handling service event: type={event_type}, source={source_service}"
            )

            # Route to appropriate handler based on event type
            if "created" in event_type:
                return await self.handle_event_created(event_data)
            elif "processed" in event_type:
                return await self.handle_event_processed(event_data)
            elif "failed" in event_type:
                return await self.handle_event_failed(event_data)
            else:
                logger.info(f"No specific handler for event type: {event_type}")
                return True

        except Exception as e:
            logger.error(f"Error handling service event: {e}")
            return False


# Standalone handler functions for convenience
async def handle_event_created(
    event_data: Dict[str, Any], event_service: Optional[Any] = None
) -> bool:
    """Handle event.created event (convenience function)"""
    handler = EventHandlers(event_service)
    return await handler.handle_event_created(event_data)


async def handle_event_processed(
    event_data: Dict[str, Any], event_service: Optional[Any] = None
) -> bool:
    """Handle event.processed event (convenience function)"""
    handler = EventHandlers(event_service)
    return await handler.handle_event_processed(event_data)


async def handle_event_failed(
    event_data: Dict[str, Any], event_service: Optional[Any] = None
) -> bool:
    """Handle event.failed event (convenience function)"""
    handler = EventHandlers(event_service)
    return await handler.handle_event_failed(event_data)


__all__ = [
    "EventHandlers",
    "handle_event_created",
    "handle_event_processed",
    "handle_event_failed",
]
