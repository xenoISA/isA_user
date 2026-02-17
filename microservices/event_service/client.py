"""
Event Service Client

Client library for other microservices to interact with event service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class EventServiceClient:
    """Event Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Event Service client

        Args:
            base_url: Event service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("event_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                # Use environment variable or default to localhost:8230
                import os
                self.base_url = os.getenv("EVENT_SERVICE_URL", "http://localhost:8230")

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Event Publishing
    # =============================================================================

    async def create_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create and publish an event

        Args:
            event_type: Type of event (user.created, file.uploaded, etc.)
            entity_type: Type of entity (user, file, album, etc.)
            entity_id: Entity identifier
            user_id: User ID who triggered event (optional)
            organization_id: Organization ID (optional)
            data: Event payload data (optional)
            metadata: Additional metadata (optional)
            correlation_id: Correlation ID for tracing (optional)

        Returns:
            Created event data

        Example:
            >>> client = EventServiceClient()
            >>> event = await client.create_event(
            ...     event_type="file.uploaded",
            ...     entity_type="file",
            ...     entity_id="file123",
            ...     user_id="user456",
            ...     data={"filename": "photo.jpg", "size": 1024000}
            ... )
        """
        try:
            payload = {
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id
            }

            if user_id:
                payload["user_id"] = user_id
            if organization_id:
                payload["organization_id"] = organization_id
            if data:
                payload["data"] = data
            if metadata:
                payload["metadata"] = metadata
            if correlation_id:
                payload["correlation_id"] = correlation_id

            response = await self.client.post(
                f"{self.base_url}/api/events/create",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create event: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None

    async def create_batch_events(
        self,
        events: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Create multiple events in batch

        Args:
            events: List of event dictionaries

        Returns:
            List of created events

        Example:
            >>> events = [
            ...     {
            ...         "event_type": "file.uploaded",
            ...         "entity_type": "file",
            ...         "entity_id": "file1",
            ...         "user_id": "user123"
            ...     },
            ...     {
            ...         "event_type": "file.uploaded",
            ...         "entity_type": "file",
            ...         "entity_id": "file2",
            ...         "user_id": "user123"
            ...     }
            ... ]
            >>> result = await client.create_batch_events(events)
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/events/batch",
                json={"events": events}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create batch events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating batch events: {e}")
            return None

    # =============================================================================
    # Event Querying
    # =============================================================================

    async def get_event(
        self,
        event_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific event by ID

        Args:
            event_id: Event ID

        Returns:
            Event data

        Example:
            >>> event = await client.get_event("evt_123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/events/{event_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get event: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return None

    async def query_events(
        self,
        event_types: Optional[List[str]] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Query events with filters

        Args:
            event_types: Filter by event types
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            user_id: Filter by user ID
            organization_id: Filter by organization ID
            start_time: Filter events after this time (ISO format)
            end_time: Filter events before this time (ISO format)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Query results with events and pagination

        Example:
            >>> result = await client.query_events(
            ...     event_types=["file.uploaded", "file.deleted"],
            ...     user_id="user123",
            ...     limit=50
            ... )
            >>> for event in result['events']:
            ...     print(f"{event['event_type']}: {event['entity_id']}")
        """
        try:
            payload = {
                "limit": limit,
                "offset": offset
            }

            if event_types:
                payload["event_types"] = event_types
            if entity_type:
                payload["entity_type"] = entity_type
            if entity_id:
                payload["entity_id"] = entity_id
            if user_id:
                payload["user_id"] = user_id
            if organization_id:
                payload["organization_id"] = organization_id
            if start_time:
                payload["start_time"] = start_time
            if end_time:
                payload["end_time"] = end_time

            response = await self.client.post(
                f"{self.base_url}/api/events/query",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to query events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error querying events: {e}")
            return None

    async def get_entity_projection(
        self,
        entity_type: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get entity state projection from events

        Args:
            entity_type: Entity type
            entity_id: Entity ID

        Returns:
            Current entity state built from events

        Example:
            >>> projection = await client.get_entity_projection("album", "album123")
            >>> print(f"Album state: {projection}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/events/projections/{entity_type}/{entity_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get entity projection: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting entity projection: {e}")
            return None

    # =============================================================================
    # Event Subscriptions
    # =============================================================================

    async def create_subscription(
        self,
        event_types: List[str],
        endpoint_url: str,
        subscriber_id: str,
        active: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create event subscription

        Args:
            event_types: List of event types to subscribe to
            endpoint_url: Webhook URL to receive events
            subscriber_id: Subscriber identifier
            active: Whether subscription is active
            filters: Additional filters (optional)

        Returns:
            Created subscription

        Example:
            >>> sub = await client.create_subscription(
            ...     event_types=["file.uploaded", "file.deleted"],
            ...     endpoint_url="https://myapp.com/webhooks/events",
            ...     subscriber_id="myapp"
            ... )
        """
        try:
            payload = {
                "event_types": event_types,
                "endpoint_url": endpoint_url,
                "subscriber_id": subscriber_id,
                "active": active
            }

            if filters:
                payload["filters"] = filters

            response = await self.client.post(
                f"{self.base_url}/api/events/subscriptions",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None

    async def list_subscriptions(self) -> Optional[List[Dict[str, Any]]]:
        """
        List all event subscriptions

        Returns:
            List of subscriptions

        Example:
            >>> subs = await client.list_subscriptions()
            >>> for sub in subs:
            ...     print(f"{sub['subscriber_id']}: {sub['event_types']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/events/subscriptions"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list subscriptions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing subscriptions: {e}")
            return None

    async def delete_subscription(
        self,
        subscription_id: str
    ) -> bool:
        """
        Delete event subscription

        Args:
            subscription_id: Subscription ID

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_subscription("sub_123")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/events/subscriptions/{subscription_id}"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete subscription: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting subscription: {e}")
            return False

    # =============================================================================
    # Event Replay
    # =============================================================================

    async def replay_events(
        self,
        start_time: str,
        end_time: str,
        event_types: Optional[List[str]] = None,
        target_endpoint: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Replay historical events

        Args:
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            event_types: Filter by event types (optional)
            target_endpoint: Target endpoint for replay (optional)

        Returns:
            Replay job information

        Example:
            >>> job = await client.replay_events(
            ...     start_time="2024-01-01T00:00:00Z",
            ...     end_time="2024-01-02T00:00:00Z",
            ...     event_types=["file.uploaded"]
            ... )
        """
        try:
            payload = {
                "start_time": start_time,
                "end_time": end_time
            }

            if event_types:
                payload["event_types"] = event_types
            if target_endpoint:
                payload["target_endpoint"] = target_endpoint

            response = await self.client.post(
                f"{self.base_url}/api/events/replay",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to replay events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error replaying events: {e}")
            return None

    # =============================================================================
    # Event Processors
    # =============================================================================

    async def create_processor(
        self,
        processor_id: str,
        event_types: List[str],
        handler_function: str,
        active: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create event processor

        Args:
            processor_id: Processor identifier
            event_types: Event types to process
            handler_function: Handler function name
            active: Whether processor is active

        Returns:
            Created processor

        Example:
            >>> processor = await client.create_processor(
            ...     processor_id="file_processor",
            ...     event_types=["file.uploaded"],
            ...     handler_function="process_file_upload"
            ... )
        """
        try:
            payload = {
                "processor_id": processor_id,
                "event_types": event_types,
                "handler_function": handler_function,
                "active": active
            }

            response = await self.client.post(
                f"{self.base_url}/api/events/processors",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create processor: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating processor: {e}")
            return None

    async def list_processors(self) -> Optional[List[Dict[str, Any]]]:
        """
        List all event processors

        Returns:
            List of processors

        Example:
            >>> processors = await client.list_processors()
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/events/processors"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list processors: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing processors: {e}")
            return None

    async def toggle_processor(
        self,
        processor_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Toggle processor active status

        Args:
            processor_id: Processor ID

        Returns:
            Updated processor

        Example:
            >>> result = await client.toggle_processor("file_processor")
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/events/processors/{processor_id}/toggle"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to toggle processor: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error toggling processor: {e}")
            return None

    # =============================================================================
    # Statistics
    # =============================================================================

    async def get_event_statistics(self) -> Optional[Dict[str, Any]]:
        """
        Get event statistics

        Returns:
            Event statistics

        Example:
            >>> stats = await client.get_event_statistics()
            >>> print(f"Total events: {stats['total_events']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/events/statistics"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get statistics: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["EventServiceClient"]
