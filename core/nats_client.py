"""
NATS JetStream Client for Python Microservices
Provides event-driven communication with isA_Cloud

This module provides a wrapper around isa_common.nats_client.NATSClient
using gRPC backend for NATS communication.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.config_manager import ConfigManager


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

from isa_common import AsyncNATSClient

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types matching Go implementation"""

    # User Events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"

    # Device Events
    DEVICE_AUTHENTICATED = "device.authenticated"
    DEVICE_REGISTERED = "device.registered"
    DEVICE_ONLINE = "device.online"
    DEVICE_OFFLINE = "device.offline"
    DEVICE_COMMAND_SENT = "device.command_sent"

    # Payment Events
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_CANCELED = "subscription.canceled"

    # Organization Events
    ORG_CREATED = "organization.created"
    ORG_UPDATED = "organization.updated"
    ORG_DELETED = "organization.deleted"
    ORG_MEMBER_ADDED = "organization.member_added"
    ORG_MEMBER_REMOVED = "organization.member_removed"

    # Family Sharing Events
    FAMILY_RESOURCE_SHARED = "family.resource_shared"

    # Notification Events
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_READ = "notification.read"

    # Storage Events
    FILE_UPLOADED = "file.uploaded"
    FILE_UPLOADED_WITH_AI = (
        "file.uploaded.with_ai"  # 🆕 新增：带 AI 元数据的文件上传事件
    )
    FILE_SHARED = "file.shared"
    FILE_DELETED = "file.deleted"
    FILE_INDEXING_REQUESTED = "file.indexing.requested"
    FILE_INDEXED = "file.indexed"
    FILE_INDEXING_FAILED = "file.indexing.failed"

    # Account Events (additional user events)
    USER_PROFILE_UPDATED = "user.profile_updated"

    # Order Events
    ORDER_CREATED = "order.created"
    ORDER_COMPLETED = "order.completed"
    ORDER_CANCELED = "order.canceled"
    ORDER_FULFILLED = "order.fulfilled"

    # Session Events
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    SESSION_MESSAGE_SENT = "session.message_sent"
    SESSION_TOKENS_USED = "session.tokens_used"

    # Wallet Events
    WALLET_CREATED = "wallet.created"
    WALLET_DEPOSITED = "wallet.deposited"
    WALLET_WITHDRAWN = "wallet.withdrawn"
    WALLET_CONSUMED = "wallet.consumed"
    WALLET_TRANSFERRED = "wallet.transferred"
    WALLET_REFUNDED = "wallet.refunded"

    # Album Events
    ALBUM_CREATED = "album.created"
    ALBUM_UPDATED = "album.updated"
    ALBUM_DELETED = "album.deleted"
    ALBUM_PHOTO_ADDED = "album.photo.added"
    ALBUM_PHOTO_REMOVED = "album.photo.removed"
    ALBUM_SYNCED = "album.synced"

    # Invitation Events
    INVITATION_SENT = "invitation.sent"
    INVITATION_ACCEPTED = "invitation.accepted"
    INVITATION_DECLINED = "invitation.declined"
    INVITATION_EXPIRED = "invitation.expired"
    INVITATION_CANCELLED = "invitation.cancelled"

    # Task Events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # OTA Events
    FIRMWARE_UPLOADED = "firmware.uploaded"
    FIRMWARE_DELETED = "firmware.deleted"
    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_STARTED = "campaign.started"
    UPDATE_STARTED = "update.started"
    UPDATE_COMPLETED = "update.completed"
    UPDATE_FAILED = "update.failed"
    UPDATE_CANCELLED = "update.cancelled"
    ROLLBACK_INITIATED = "rollback.initiated"

    # Telemetry Events
    TELEMETRY_DATA_RECEIVED = "telemetry.data.received"
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    METRIC_DEFINED = "metric.defined"
    ALERT_RULE_CREATED = "alert.rule.created"

    # Memory Events
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    FACTUAL_MEMORY_STORED = "memory.factual.stored"
    EPISODIC_MEMORY_STORED = "memory.episodic.stored"
    PROCEDURAL_MEMORY_STORED = "memory.procedural.stored"
    SEMANTIC_MEMORY_STORED = "memory.semantic.stored"
    WORKING_MEMORY_ACTIVATED = "memory.working.activated"
    SESSION_MEMORY_DEACTIVATED = "memory.session.deactivated"

    # Billing Events
    USAGE_RECORDED = "billing.usage.recorded"
    BILLING_PROCESSED = "billing.processed"
    BILLING_CALCULATED = "billing.calculated"
    INVOICE_CREATED = "billing.invoice.created"
    QUOTA_EXCEEDED = "billing.quota.exceeded"
    BILLING_RECORD_CREATED = "billing.record.created"

    # Product Events
    PRODUCT_USAGE_RECORDED = "product.usage.recorded"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_ACTIVATED = "subscription.activated"
    SUBSCRIPTION_EXPIRED = "subscription.expired"
    SUBSCRIPTION_RENEWED = "subscription.renewed"
    CREDITS_CONSUMED = "subscription.credits.consumed"
    CREDITS_ALLOCATED = "subscription.credits.allocated"
    PRODUCT_AVAILABILITY_CHANGED = "product.availability.changed"

    # Vault Events
    VAULT_SECRET_CREATED = "vault.secret.created"
    VAULT_SECRET_ACCESSED = "vault.secret.accessed"
    VAULT_SECRET_UPDATED = "vault.secret.updated"
    VAULT_SECRET_DELETED = "vault.secret.deleted"
    VAULT_SECRET_SHARED = "vault.secret.shared"
    VAULT_SECRET_ROTATED = "vault.secret.rotated"

    # Authorization Events
    PERMISSION_GRANTED = "authorization.permission.granted"
    PERMISSION_REVOKED = "authorization.permission.revoked"
    ACCESS_CHECKED = "authorization.access.checked"
    ACCESS_DENIED = "authorization.access.denied"
    BULK_PERMISSIONS_UPDATED = "authorization.bulk.updated"

    # Event Service Events (for event management operations)
    EVENT_STORED = "event.stored"
    EVENT_PROCESSED_SUCCESS = "event.processed.success"
    EVENT_PROCESSED_FAILED = "event.processed.failed"
    EVENT_SUBSCRIPTION_CREATED = "event.subscription.created"
    EVENT_REPLAY_STARTED = "event.replay.started"
    EVENT_PROJECTION_CREATED = "event.projection.created"

    # Media Service Events
    PHOTO_VERSION_CREATED = "media.photo_version.created"
    PHOTO_METADATA_UPDATED = "media.photo_metadata.updated"
    MEDIA_PLAYLIST_CREATED = "media.playlist.created"
    MEDIA_PLAYLIST_UPDATED = "media.playlist.updated"
    MEDIA_PLAYLIST_DELETED = "media.playlist.deleted"
    ROTATION_SCHEDULE_CREATED = "media.rotation_schedule.created"
    ROTATION_SCHEDULE_UPDATED = "media.rotation_schedule.updated"
    PHOTO_CACHED = "media.photo.cached"

    # Calendar Service Events
    CALENDAR_EVENT_CREATED = "calendar.event.created"
    CALENDAR_EVENT_UPDATED = "calendar.event.updated"
    CALENDAR_EVENT_DELETED = "calendar.event.deleted"

    # Compliance Service Events
    COMPLIANCE_CHECK_PERFORMED = "compliance.check.performed"
    COMPLIANCE_VIOLATION_DETECTED = "compliance.violation.detected"
    COMPLIANCE_WARNING_ISSUED = "compliance.warning.issued"

    # Weather Service Events
    WEATHER_DATA_FETCHED = "weather.data.fetched"
    WEATHER_ALERT_CREATED = "weather.alert.created"

    # Location Service Events
    LOCATION_UPDATED = "location.updated"
    LOCATION_BATCH_UPDATED = "location.batch.updated"
    GEOFENCE_CREATED = "location.geofence.created"
    GEOFENCE_UPDATED = "location.geofence.updated"
    GEOFENCE_DELETED = "location.geofence.deleted"
    GEOFENCE_ACTIVATED = "location.geofence.activated"
    GEOFENCE_DEACTIVATED = "location.geofence.deactivated"
    GEOFENCE_ENTERED = "location.geofence.entered"
    GEOFENCE_EXITED = "location.geofence.exited"
    GEOFENCE_DWELL = "location.geofence.dwell"
    DEVICE_STARTED_MOVING = "location.device.started_moving"
    DEVICE_STOPPED = "location.device.stopped"
    SIGNIFICANT_MOVEMENT = "location.significant_movement"
    LOW_BATTERY_AT_LOCATION = "location.low_battery"
    PLACE_CREATED = "location.place.created"
    PLACE_UPDATED = "location.place.updated"
    PLACE_DELETED = "location.place.deleted"
    ROUTE_STARTED = "location.route.started"
    ROUTE_ENDED = "location.route.ended"


class ServiceSource(Enum):
    """Service sources matching Go implementation"""

    AUTH_SERVICE = "auth_service"
    USER_SERVICE = "user_service"
    ACCOUNT_SERVICE = "account_service"
    ORG_SERVICE = "organization_service"
    PAYMENT_SERVICE = "payment_service"
    ORDER_SERVICE = "order_service"
    SESSION_SERVICE = "session_service"
    DEVICE_SERVICE = "device_service"
    NOTIFICATION_SERVICE = "notification_service"
    AUDIT_SERVICE = "audit_service"
    AUTHORIZATION_SERVICE = "authorization_service"
    STORAGE_SERVICE = "storage_service"
    WALLET_SERVICE = "wallet_service"
    ALBUM_SERVICE = "album_service"
    INVITATION_SERVICE = "invitation_service"
    TASK_SERVICE = "task_service"
    OTA_SERVICE = "ota_service"
    TELEMETRY_SERVICE = "telemetry_service"
    MEMORY_SERVICE = "memory_service"
    BILLING_SERVICE = "billing_service"
    PRODUCT_SERVICE = "product_service"
    VAULT_SERVICE = "vault_service"
    EVENT_SERVICE = "event_service"
    MEDIA_SERVICE = "media_service"
    CALENDAR_SERVICE = "calendar_service"
    COMPLIANCE_SERVICE = "compliance_service"
    WEATHER_SERVICE = "weather_service"
    LOCATION_SERVICE = "location_service"
    SUBSCRIPTION_SERVICE = "subscription_service"
    GATEWAY = "api_gateway"


class Event:
    """Event model"""

    def __init__(
        self,
        event_type: EventType,
        source: ServiceSource,
        data: Dict[str, Any],
        subject: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.type = event_type.value
        self.source = source.value
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


class NATSEventBus:
    """
    NATS JetStream event bus using AsyncNATSClient.

    True async I/O - no thread pool overhead.
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
            service_name: Name of the service (used as user_id for tracking)
            config: Optional ConfigManager instance for service discovery
            organization_id: Organization ID for multi-tenancy
        """
        from core.config_manager import ConfigManager

        self.service_name = service_name

        # Use ConfigManager for service discovery
        # Priority: environment variables → Consul → default fallback
        if config is None:
            config = ConfigManager(service_name)

        self.host, self.port = config.discover_service(
            service_name='nats_grpc_service',
            default_host='isa-nats-grpc',
            default_port=50056,
            env_host_key='NATS_GRPC_HOST',
            env_port_key='NATS_GRPC_PORT'
        )

        self.organization_id = organization_id or os.getenv("ORGANIZATION_ID", "default-org")

        self._client: Optional[AsyncNATSClient] = None
        self._subscriptions: Dict[str, bool] = {}  # pattern -> active
        self._subscription_tasks: List[asyncio.Task] = []
        self._is_connected = False

        logger.info(f"NATS EventBus initialized: {self.host}:{self.port}")

    async def connect(self):
        """Connect to NATS gRPC service - TRUE ASYNC"""
        try:
            # 重要：使用固定的 "billing" user_id，以便与 isA_Model 共享同一个 stream
            # NATS gRPC gateway 会按 user_id 隔离 streams，必须使用相同的 user_id
            # 实际用户ID保存在 event data 里，不受影响
            self._client = AsyncNATSClient(
                host=self.host,
                port=self.port,
                user_id="billing",  # 固定使用 "billing" 以共享 stream
                organization_id=self.organization_id,
            )

            # True async context manager - connects on entry
            await self._client.__aenter__()

            # Async health check
            health = await self._client.health_check()
            if health and health.get('healthy'):
                self._is_connected = True
                logger.info(f"Connected to NATS gRPC service as {self.service_name}")
                logger.info(f"  JetStream enabled: {health.get('jetstream_enabled')}")
            else:
                logger.warning(f"NATS service health check failed: {health}")
                self._is_connected = True  # Still try to use it

        except Exception as e:
            logger.error(f"Failed to connect to NATS gRPC service: {e}")
            raise

    async def publish_event(self, event: Event) -> bool:
        """
        Publish an event to NATS JetStream - TRUE ASYNC.

        Automatically determines the appropriate stream based on event type:
        - billing.* -> billing-stream
        - session.* -> session-stream
        - order.* -> order-stream
        - wallet.* -> wallet-stream
        - etc.

        Uses JetStream for:
        - Message persistence
        - At-least-once delivery guarantee
        - No user_id isolation issues
        """
        if not self._is_connected or not self._client:
            logger.error("Not connected to NATS")
            return False

        try:
            # Use event.type as subject (e.g., "billing.usage.recorded")
            subject = event.type
            data = json.dumps(event.to_dict(), cls=DecimalEncoder).encode()

            # Determine stream name from event type
            stream_name = self._get_stream_name_for_event(event.type)

            # Ensure stream exists (idempotent) - ASYNC
            try:
                # Get subject pattern for the stream (e.g., "billing.>" for billing events)
                subject_prefix = event.type.split('.')[0]
                await self._client.create_stream(
                    name=stream_name,
                    subjects=[f"{subject_prefix}.>"],
                    max_msgs=100000,
                )
            except Exception as e:
                logger.debug(f"Stream creation note: {e}")

            # Publish to JetStream - TRUE ASYNC
            result = await self._client.publish_to_stream(
                stream_name=stream_name,
                subject=subject,
                data=data
            )

            if result and result.get('success'):
                seq = result.get('sequence', 'N/A')
                logger.info(f"Published event {event.type} [{event.id}] to stream {stream_name}, seq={seq}")
                return True
            else:
                logger.error(f"Failed to publish event {event.id} to stream {stream_name}")
                return False

        except Exception as e:
            logger.error(f"Error publishing event {event.id}: {e}")
            return False

    def _get_stream_name_for_event(self, event_type: str) -> str:
        """
        Determine the JetStream stream name based on event type.

        Mapping:
        - billing.* -> billing-stream
        - session.* -> session-stream
        - order.* -> order-stream
        - wallet.* -> wallet-stream
        - user.* -> user-stream
        - device.* -> device-stream
        - etc.
        """
        # Extract the first part of the event type (e.g., "billing" from "billing.usage.recorded")
        prefix = event_type.split('.')[0]

        # Special mappings for certain event types
        stream_mappings = {
            "billing": "billing-stream",
            "session": "session-stream",
            "order": "order-stream",
            "wallet": "wallet-stream",
            "user": "user-stream",
            "device": "device-stream",
            "payment": "payment-stream",
            "organization": "organization-stream",
            "notification": "notification-stream",
            "file": "storage-stream",
            "album": "album-stream",
            "task": "task-stream",
            "memory": "memory-stream",
            "product": "product-stream",
            "vault": "vault-stream",
            "event": "event-stream",
            "media": "media-stream",
            "calendar": "calendar-stream",
            "location": "location-stream",
            "telemetry": "telemetry-stream",
            "weather": "weather-stream",
            "invitation": "invitation-stream",
            "authorization": "authorization-stream",
            "compliance": "compliance-stream",
            "firmware": "ota-stream",
            "campaign": "ota-stream",
            "update": "ota-stream",
            "rollback": "ota-stream",
            "alert": "telemetry-stream",
            "metric": "telemetry-stream",
        }

        return stream_mappings.get(prefix, f"{prefix}-stream")

    async def publish_to_stream(self, stream_name: str, event: Event) -> bool:
        """Publish an event to a specific JetStream stream - TRUE ASYNC"""
        if not self._is_connected or not self._client:
            logger.error("Not connected to NATS")
            return False

        try:
            subject = event.type
            data = json.dumps(event.to_dict(), cls=DecimalEncoder).encode()

            result = await self._client.publish_to_stream(
                stream_name=stream_name,
                subject=subject,
                data=data
            )

            if result and result.get('success'):
                logger.info(f"Published event {event.type} [{event.id}] to stream {stream_name}, seq={result.get('sequence')}")
                return True
            else:
                logger.error(f"Failed to publish event {event.id} to stream {stream_name}")
                return False

        except Exception as e:
            logger.error(f"Error publishing event {event.id} to stream: {e}")
            return False

    async def subscribe_to_events(
        self, pattern: str, handler: Callable, durable: Optional[str] = None
    ) -> str:
        """
        Subscribe to events with a pattern using JetStream consumer.

        Uses JetStream pull-based consumer for:
        - Message persistence (won't lose messages)
        - At-least-once delivery guarantee
        - Message replay capability
        - No user_id isolation issues

        Args:
            pattern: Subject pattern to subscribe to (e.g., "billing.usage.recorded.*")
            handler: Async callback function to handle events
            durable: Optional durable name for the consumer
        """
        if not self._is_connected or not self._client:
            logger.error("Not connected to NATS")
            return None

        try:
            # Mark subscription as active
            self._subscriptions[pattern] = True

            # Create async task to handle subscription
            task = asyncio.create_task(
                self._jetstream_consumer_loop(pattern, handler, durable)
            )
            self._subscription_tasks.append(task)

            logger.info(f"Subscribed to {pattern} (JetStream consumer)")
            return durable or pattern

        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return None

    async def _jetstream_consumer_loop(self, pattern: str, handler: Callable, durable: Optional[str]):
        """
        JetStream consumer loop - TRUE ASYNC (no run_in_executor!).

        Uses pull-based consumer pattern:
        1. Create/ensure stream exists
        2. Create/ensure consumer exists
        3. Pull messages in batches
        4. Process and acknowledge messages
        """
        # Determine stream name from pattern using the same mapping as publish_event
        # Extract prefix from pattern (e.g., "billing" from "billing.usage.recorded.*")
        prefix = pattern.split('.')[0]
        stream_name = self._get_stream_name_for_event(prefix)

        # Consumer 命名：与 stream 对应，如 billing-stream -> billing-consumer
        consumer_name = durable or f"{prefix}-consumer"

        logger.info(f"Starting JetStream consumer: stream={stream_name}, consumer={consumer_name}, pattern={pattern}")

        try:
            # Step 1: Ensure stream exists (idempotent) - ASYNC
            try:
                stream_result = await self._client.create_stream(
                    name=stream_name,
                    subjects=[pattern.replace("*", ">")],  # Convert * to > for NATS wildcard
                    max_msgs=100000,
                )
                if stream_result:
                    logger.debug(f"Stream '{stream_name}' ready")
            except Exception as e:
                logger.debug(f"Stream creation note: {e}")

            # Step 2: Create consumer (idempotent) - ASYNC
            try:
                consumer_result = await self._client.create_consumer(
                    stream_name=stream_name,
                    consumer_name=consumer_name,
                    filter_subject=pattern.replace("*", ">")
                )
                if consumer_result:
                    logger.debug(f"Consumer '{consumer_name}' ready")
            except Exception as e:
                logger.debug(f"Consumer creation note: {e}")

            # Step 3: Pull loop - TRUE ASYNC (no executor!)
            while self._subscriptions.get(pattern, False):
                try:
                    # ASYNC pull - no thread pool overhead!
                    messages = await self._client.pull_messages(
                        stream_name=stream_name,
                        consumer_name=consumer_name,
                        batch_size=10
                    )

                    if messages:
                        logger.debug(f"Pulled {len(messages)} messages from {stream_name}/{consumer_name}")
                        for msg in messages:
                            try:
                                # Parse event from message data
                                if isinstance(msg.get('data'), bytes):
                                    data = json.loads(msg['data'].decode())
                                else:
                                    data = msg.get('data', {})

                                # Handle both Event envelope format and raw event data format
                                # Event envelope has: id, type, source, data, timestamp, etc.
                                # Raw data (from isA_Model) has: user_id, product_id, usage_amount, etc.
                                if 'type' in data and 'source' in data and 'data' in data:
                                    # Full Event envelope format
                                    event = Event.from_dict(data)
                                else:
                                    # Raw event data format (from isA_Model's publish_to_stream)
                                    # Wrap it in an Event envelope
                                    event = Event.__new__(Event)
                                    event.id = str(msg.get('sequence', uuid.uuid4()))
                                    event.type = msg.get('subject', pattern)
                                    event.source = 'isA_Model'
                                    event.subject = msg.get('subject')
                                    event.timestamp = data.get('timestamp', datetime.utcnow().isoformat())
                                    event.data = data  # The actual payload
                                    event.metadata = {}
                                    event.version = '1.0.0'
                                    logger.debug(f"Wrapped raw event data in Event envelope: {event.type}")

                                # Call async handler
                                await handler(event)

                            except Exception as msg_e:
                                logger.error(f"Error processing message: {msg_e}")

                    else:
                        # No messages, wait briefly before polling again
                        await asyncio.sleep(1)

                except Exception as pull_e:
                    logger.warning(f"Pull error (will retry): {pull_e}")
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"JetStream consumer loop error for {pattern}: {e}")
        finally:
            self._subscriptions[pattern] = False
            logger.info(f"JetStream consumer stopped: {consumer_name}")

    async def unsubscribe(self, pattern: str) -> bool:
        """Unsubscribe from a pattern - TRUE ASYNC"""
        if pattern in self._subscriptions:
            self._subscriptions[pattern] = False

            if self._client:
                result = await self._client.unsubscribe(subject=pattern)
                if result and result.get('success'):
                    logger.info(f"Unsubscribed from {pattern}")
                    return True

        return False

    async def create_stream(self, name: str, subjects: List[str]) -> bool:
        """Create a JetStream stream - TRUE ASYNC"""
        if not self._is_connected or not self._client:
            return False

        result = await self._client.create_stream(name=name, subjects=subjects)
        return result is not None and result.get('success', False)

    async def close(self):
        """Close NATS connection - TRUE ASYNC"""
        # Stop all subscriptions
        for pattern in list(self._subscriptions.keys()):
            self._subscriptions[pattern] = False

        # Cancel subscription tasks
        for task in self._subscription_tasks:
            if not task.done():
                task.cancel()

        # Close client using async context manager exit
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

        self._is_connected = False
        logger.info("Disconnected from NATS")

    @property
    def is_connected(self) -> bool:
        """Check if connected to NATS"""
        return self._is_connected


# Singleton instance
_event_bus: Optional[NATSEventBus] = None


async def get_event_bus(
    service_name: str,
    config: Optional["ConfigManager"] = None,
    organization_id: str = None,
) -> NATSEventBus:
    """
    Get or create event bus instance.

    Args:
        service_name: Name of the service using the event bus
        config: Optional ConfigManager instance for service discovery
        organization_id: Optional organization ID

    Returns:
        NATSEventBus instance
    """
    global _event_bus

    if _event_bus is None:
        _event_bus = NATSEventBus(
            service_name=service_name,
            config=config,
            organization_id=organization_id,
        )
        await _event_bus.connect()

    return _event_bus


async def publish_payment_event(
    payment_id: str,
    amount: float,
    status: str,
    user_id: str,
    metadata: Optional[Dict] = None,
):
    """Helper function to publish payment events"""
    event_bus = await get_event_bus("payment_service")

    # Determine event type based on status
    event_type_map = {
        "initiated": EventType.PAYMENT_INITIATED,
        "completed": EventType.PAYMENT_COMPLETED,
        "failed": EventType.PAYMENT_FAILED,
        "refunded": EventType.PAYMENT_REFUNDED,
    }

    event_type = event_type_map.get(status, EventType.PAYMENT_INITIATED)

    event = Event(
        event_type=event_type,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_id": payment_id,
            "amount": amount,
            "status": status,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
        metadata=metadata,
    )

    return await event_bus.publish_event(event)


# Convenience function for creating events
def create_event(
    event_type: EventType,
    source: ServiceSource,
    data: Dict[str, Any],
    subject: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> Event:
    """Create an Event instance"""
    return Event(
        event_type=event_type,
        source=source,
        data=data,
        subject=subject,
        metadata=metadata,
    )
