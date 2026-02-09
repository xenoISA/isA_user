"""
NATS Event Bus

NATS JetStream client for event-driven microservices.
This module provides the transport mechanism - event types are defined per-service.

Each microservice defines its own events in its events/ folder:
- events/models.py: Event types and data models (e.g., BillingEventType)
- events/handlers.py: Event subscription handlers
- events/publishers.py: Event publishing functions

Usage:
    from core.nats_client import NATSEventBus, Event, get_event_bus

    # In service main.py
    event_bus = await get_event_bus("billing_service")

    # Publish
    event = Event(event_type="billing.calculated", source="billing_service", data={...})
    await event_bus.publish_event(event)

    # Subscribe
    await event_bus.subscribe_to_events("billing.usage.recorded.*", handler)

Architecture:
- Transport: core/nats_client.py (this file)
- Service events: microservices/{service}/events/models.py
- Stream mappings: Derived from event subject prefix (billing.* -> billing-stream)
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

if TYPE_CHECKING:
    from core.config_manager import ConfigManager

from isa_common import AsyncNATSClient

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal and datetime types"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class Event:
    """
    Event wrapper for all services.

    This is the transport wrapper - the actual event data
    is defined in each service's events/models.py

    Compatible with old nats_client.Event interface.
    """

    def __init__(
        self,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        subject: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.type = event_type
        self.source = source
        self.data = data
        self.subject = subject
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata = metadata or {}
        self.version = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "subject": self.subject,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        event = cls.__new__(cls)
        event.id = data.get("id")
        event.type = data.get("type")
        event.source = data.get("source")
        event.subject = data.get("subject")
        event.timestamp = data.get("timestamp")
        event.data = data.get("data", {})
        event.metadata = data.get("metadata", {})
        event.version = data.get("version", "1.0.0")
        return event

    def __repr__(self):
        return f"Event(type={self.type}, source={self.source}, id={self.id})"


# Alias for backward compatibility
EventEnvelope = Event


class NATSEventBus:
    """
    NATS JetStream event bus.

    Provides publish/subscribe functionality without
    defining any specific event types.

    Stream names are derived from event subject prefixes:
    - billing.* -> billing-stream
    - session.* -> session-stream
    - user.* -> user-stream

    Compatible with old nats_client.NATSEventBus interface.
    """

    def __init__(
        self,
        service_name: str,
        config: Optional["ConfigManager"] = None,
        organization_id: str = None,
    ):
        """
        Initialize NATS Event Bus.

        Args:
            service_name: Name of the service using this event bus
            config: Optional ConfigManager for service discovery
            organization_id: Organization ID for multi-tenancy
        """
        from core.config_manager import ConfigManager

        self.service_name = service_name

        # Use ConfigManager for service discovery
        if config is None:
            config = ConfigManager(service_name)

        self.host, self.port = config.discover_service(
            service_name="nats_service",
            default_host="nats",
            default_port=4222,
            env_host_key="NATS_HOST",
            env_port_key="NATS_PORT",
        )

        self.organization_id = organization_id or os.getenv(
            "ORGANIZATION_ID", "default-org"
        )

        self._client: Optional[AsyncNATSClient] = None
        self._subscriptions: Dict[str, bool] = {}
        self._subscription_tasks: List[asyncio.Task] = []
        self._is_connected = False

        logger.info(f"NATS Transport initialized: {self.host}:{self.port}")

    async def connect(self):
        """Connect to NATS gRPC service"""
        try:
            # All services use unified user_id="isa_event" to share streams
            self._client = AsyncNATSClient(
                host=self.host,
                port=self.port,
                user_id="isa_event",
                organization_id=self.organization_id,
            )

            await self._client.__aenter__()

            health = await self._client.health_check()
            if health and health.get("healthy"):
                self._is_connected = True
                logger.info(f"Connected to NATS as {self.service_name}")
            else:
                logger.warning(f"NATS health check failed: {health}")
                self._is_connected = True

        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise

    def _get_stream_name(self, subject: str) -> str:
        """
        Derive stream name from subject prefix.

        Examples:
            billing.usage.recorded -> billing-stream
            session.tokens_used -> session-stream
            user.created -> user-stream
            *.file.> -> file-stream (wildcard prefix uses second part)
            *.user.> -> user-stream
        """
        parts = subject.split(".")

        # Handle wildcard prefixes (e.g., *.file.>, *.user.>)
        if parts[0] in ("*", ">"):
            # Use second part as the prefix
            prefix = parts[1] if len(parts) > 1 and parts[1] not in ("*", ">") else "events"
        else:
            prefix = parts[0]

        # Special mappings for multi-prefix streams
        special_mappings = {
            "file": "storage-stream",
            "firmware": "ota-stream",
            "campaign": "ota-stream",
            "update": "ota-stream",
            "rollback": "ota-stream",
            "alert": "telemetry-stream",
            "metric": "telemetry-stream",
        }

        return special_mappings.get(prefix, f"{prefix}-stream")

    async def publish_event(
        self,
        event: Union[Dict[str, Any], Event],
        subject: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Publish event to NATS JetStream.

        Args:
            event: Event object or data dict
            subject: Optional subject override (defaults to event.type)
            metadata: Optional metadata

        Returns:
            True if published successfully
        """
        if not self._is_connected or not self._client:
            logger.error("Not connected to NATS")
            return False

        try:
            # Handle Event object or dict
            if isinstance(event, Event):
                envelope = event
                # Use {source}.{type} pattern for subject to allow filtering by source
                # This matches the subscription patterns used by handlers
                subject = subject or f"{event.source}.{event.type}"
            elif isinstance(event, dict):
                event_type = event.get("type", "unknown")
                event_source = event.get("source", self.service_name)
                subject = subject or f"{event_source}.{event_type}"
                envelope = Event(
                    event_type=event_type,
                    source=event_source,
                    data=event,
                    metadata=metadata,
                )
            else:
                envelope = event
                event_type = getattr(event, 'type', 'unknown')
                event_source = getattr(event, 'source', self.service_name)
                subject = subject or f"{event_source}.{event_type}"

            stream_name = self._get_stream_name(subject)
            payload = json.dumps(envelope.to_dict(), cls=DecimalEncoder).encode()

            # Ensure stream exists
            try:
                prefix = subject.split(".")[0]
                await self._client.create_stream(
                    name=stream_name,
                    subjects=[f"{prefix}.>"],
                    max_msgs=100000,
                )
            except Exception as e:
                logger.debug(f"Stream creation note: {e}")

            # Publish
            result = await self._client.publish_to_stream(
                stream_name=stream_name,
                subject=subject,
                data=payload,
            )

            if result and result.get("success"):
                logger.info(f"Published {subject} [{envelope.id}] to {stream_name}")
                return True
            else:
                logger.error(f"Failed to publish {subject}")
                return False

        except Exception as e:
            logger.error(f"Error publishing {subject}: {e}")
            return False

    # Alias for compatibility
    async def publish(self, subject: str, data, metadata=None) -> bool:
        """Alias for publish_event"""
        if isinstance(data, (Event, dict)):
            return await self.publish_event(data, subject=subject, metadata=metadata)
        return await self.publish_event({"data": data}, subject=subject, metadata=metadata)

    async def subscribe_to_events(
        self,
        pattern: str,
        handler: Callable,
        durable: Optional[str] = None,
        delivery_policy: str = "all",
    ) -> Optional[str]:
        """
        Subscribe to events matching pattern.

        Args:
            pattern: Subject pattern (e.g., "billing.usage.recorded.*")
            handler: Async callback function(event: Event)
            durable: Optional durable consumer name
            delivery_policy: 'all', 'new', or 'last'

        Returns:
            Consumer name if successful
        """
        consumer_name = durable
        if not self._is_connected or not self._client:
            logger.error("Not connected to NATS")
            return None

        try:
            self._subscriptions[pattern] = True

            task = asyncio.create_task(
                self._consumer_loop(pattern, handler, consumer_name, delivery_policy)
            )
            self._subscription_tasks.append(task)

            logger.info(f"Subscribed to {pattern}")
            return consumer_name or pattern

        except Exception as e:
            logger.error(f"Error subscribing to {pattern}: {e}")
            return None

    # Alias for backward compatibility
    async def subscribe(self, pattern: str, handler: Callable, consumer_name: Optional[str] = None) -> Optional[str]:
        """Alias for subscribe_to_events"""
        return await self.subscribe_to_events(pattern, handler, durable=consumer_name)

    async def _consumer_loop(
        self,
        pattern: str,
        handler: Callable,
        consumer_name: Optional[str],
        delivery_policy: str,
    ):
        """JetStream pull consumer loop"""
        # Use full pattern to derive stream name (handles wildcards like *.file.>)
        stream_name = self._get_stream_name(pattern)

        # Get a safe prefix for consumer name
        parts = pattern.split(".")
        if parts[0] in ("*", ">"):
            prefix = parts[1] if len(parts) > 1 and parts[1] not in ("*", ">") else "events"
        else:
            prefix = parts[0]
        consumer_name = consumer_name or f"{self.service_name}-{prefix}-consumer"

        logger.info(f"Starting consumer: stream={stream_name}, consumer={consumer_name}")

        try:
            # Ensure stream exists
            # For patterns like *.file.>, we need a stream that captures these subjects
            # NATS doesn't allow stream subjects starting with *, so we use different approaches:
            if parts[0] in ("*", ">"):
                # For wildcard-prefix patterns like *.file.>, use a broad capture
                # Stream captures *.{prefix}.> patterns by using > (all subjects)
                # Then filter at consumer level
                stream_subject = ">"
                filter_subject = ">"  # Consumer will get all, handler filters by event type
            else:
                stream_subject = f"{prefix}.>"
                filter_subject = pattern

            try:
                await self._client.create_stream(
                    name=stream_name,
                    subjects=[stream_subject],
                    max_msgs=100000,
                )
            except Exception as e:
                logger.debug(f"Stream creation note: {e}")

            # Create consumer
            try:
                await self._client.create_consumer(
                    stream_name=stream_name,
                    consumer_name=consumer_name,
                    filter_subject=filter_subject,
                    delivery_policy=delivery_policy,
                )
            except Exception as e:
                logger.debug(f"Consumer creation note: {e}")

            # Pull loop
            while self._subscriptions.get(pattern, False):
                try:
                    messages = await self._client.pull_messages(
                        stream_name=stream_name,
                        consumer_name=consumer_name,
                        batch_size=10,
                    )

                    if messages:
                        for msg in messages:
                            try:
                                # Parse envelope
                                if isinstance(msg.get("data"), bytes):
                                    data = json.loads(msg["data"].decode())
                                else:
                                    data = msg.get("data", {})

                                # Create event
                                if "type" in data and "source" in data and "data" in data:
                                    event = Event.from_dict(data)
                                else:
                                    # Wrap raw data
                                    event = Event(
                                        event_type=msg.get("subject", pattern),
                                        source="unknown",
                                        data=data,
                                    )
                                    event.id = str(msg.get("sequence", uuid.uuid4()))

                                await handler(event)

                            except Exception as msg_e:
                                logger.error(f"Error processing message: {msg_e}")
                    else:
                        await asyncio.sleep(1)

                except Exception as pull_e:
                    logger.warning(f"Pull error (will retry): {pull_e}")
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Consumer loop error for {pattern}: {e}")
        finally:
            self._subscriptions[pattern] = False
            logger.info(f"Consumer stopped: {consumer_name}")

    async def unsubscribe(self, pattern: str) -> bool:
        """Unsubscribe from pattern"""
        if pattern in self._subscriptions:
            self._subscriptions[pattern] = False
            return True
        return False

    async def close(self):
        """Close NATS connection"""
        for pattern in list(self._subscriptions.keys()):
            self._subscriptions[pattern] = False

        for task in self._subscription_tasks:
            if not task.done():
                task.cancel()

        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

        self._is_connected = False
        logger.info("NATS Transport closed")

    @property
    def is_connected(self) -> bool:
        return self._is_connected


# Singleton event bus instance per service
_event_buses: Dict[str, NATSEventBus] = {}


async def get_event_bus(
    service_name: str,
    config: Optional["ConfigManager"] = None,
    organization_id: str = None,
) -> NATSEventBus:
    """
    Get or create event bus instance for a service.

    Args:
        service_name: Service name
        config: Optional ConfigManager
        organization_id: Optional org ID

    Returns:
        NATSEventBus instance
    """
    global _event_buses

    if service_name not in _event_buses:
        event_bus = NATSEventBus(
            service_name=service_name,
            config=config,
            organization_id=organization_id,
        )
        await event_bus.connect()
        _event_buses[service_name] = event_bus

    return _event_buses[service_name]


# Aliases for backward compatibility
NATSTransport = NATSEventBus
get_transport = get_event_bus
