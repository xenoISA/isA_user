"""
NATS JetStream Client for Python Microservices
Provides event-driven communication with isA_Cloud
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

import nats
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig
from nats.errors import TimeoutError

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
    FILE_UPLOADED_WITH_AI = "file.uploaded.with_ai"  # 🆕 新增：带 AI 元数据的文件上传事件
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
    GATEWAY = "api_gateway"


class Event:
    """Event model"""
    def __init__(self, 
                 event_type: EventType,
                 source: ServiceSource,
                 data: Dict[str, Any],
                 subject: Optional[str] = None,
                 metadata: Optional[Dict[str, str]] = None):
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
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
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
    """NATS JetStream event bus client"""
    
    def __init__(self,
                 service_name: str,
                 nats_url: str = None,
                 username: str = None,
                 password: str = None):
        self.service_name = service_name
        self.nats_url = nats_url or os.getenv("NATS_URL", "nats://localhost:4222")
        self.username = username or os.getenv("NATS_USERNAME", None)
        self.password = password or os.getenv("NATS_PASSWORD", None)
        
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[JetStreamContext] = None
        self._subscriptions = []
        self._is_connected = False
        
    async def connect(self):
        """Connect to NATS server"""
        try:
            # Prepare connection options
            connect_opts = {
                "servers": [self.nats_url],
                "name": self.service_name,
                "reconnect_time_wait": 2,
                "max_reconnect_attempts": 10,
                "error_cb": self._error_callback,
                "disconnected_cb": self._disconnected_callback,
                "reconnected_cb": self._reconnected_callback
            }

            # Only add auth if credentials provided
            if self.username and self.password:
                connect_opts["user"] = self.username
                connect_opts["password"] = self.password

            self.nc = await nats.connect(**connect_opts)
            
            # Create JetStream context
            self.js = self.nc.jetstream()
            
            # Initialize streams (will be created by Go service if not exists)
            await self._ensure_streams()
            
            self._is_connected = True
            logger.info(f"Connected to NATS at {self.nats_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise
    
    async def _ensure_streams(self):
        """Ensure required streams exist"""
        try:
            # Try to get stream info
            await self.js.stream_info("EVENTS")
            logger.info("Connected to existing EVENTS stream")
        except Exception as e:
            # Stream doesn't exist, create it
            logger.info(f"EVENTS stream not found, creating it: {e}")
            try:
                from nats.js.api import StreamConfig

                stream_config = StreamConfig(
                    name="EVENTS",
                    subjects=["events.>"],  # All events subjects
                    description="Event-driven architecture event stream",
                    max_age=604800,  # 7 days retention in seconds
                    storage="file",  # File-based storage for durability
                    max_bytes=100 * 1024 * 1024,  # 100MB max storage (reasonable for development)
                    max_msgs=-1,  # No message limit
                    retention="limits",  # Delete old messages when limits reached
                    discard="old",  # Discard old messages first
                    duplicate_window=120,  # 2 min duplicate detection in seconds
                )

                await self.js.add_stream(stream_config)
                logger.info("✅ Created EVENTS stream successfully")
            except Exception as create_error:
                logger.error(f"Failed to create EVENTS stream: {create_error}")
                # Don't raise - allow service to continue without event publishing
    
    async def publish_event(self, event: Event) -> bool:
        """Publish an event to JetStream"""
        if not self._is_connected:
            logger.error("Not connected to NATS")
            return False
        
        try:
            # Construct subject
            subject = f"events.{event.source}.{event.type}"
            
            # Publish to JetStream
            ack = await self.js.publish(
                subject,
                json.dumps(event.to_dict()).encode()
            )
            
            logger.info(f"Published event {event.type} [{event.id}] to {subject}")
            return True
            
        except TimeoutError:
            logger.error(f"Timeout publishing event {event.id}")
            return False
        except Exception as e:
            logger.error(f"Error publishing event {event.id}: {e}")
            return False
    
    async def subscribe_to_events(self,
                                  pattern: str,
                                  handler: Callable,
                                  durable: Optional[str] = None) -> str:
        """Subscribe to events with a pattern"""
        if not self._is_connected:
            logger.error("Not connected to NATS")
            return None

        try:
            from nats.js.api import DeliverPolicy

            # Create subject filter
            subject = f"events.{pattern}"

            # Create ephemeral consumer that only receives NEW messages
            # This prevents replaying old messages from JetStream
            sub = await self.js.subscribe(
                subject,
                manual_ack=False,  # Automatic ack for simplicity
                config=ConsumerConfig(
                    deliver_policy=DeliverPolicy.NEW,  # Only new messages
                )
            )

            # Start message handler
            asyncio.create_task(self._handle_messages(sub, handler))

            self._subscriptions.append(sub)
            logger.info(f"Subscribed to {subject} (deliver_policy=NEW)")

            return durable

        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return None
    
    async def _handle_messages(self, subscription, handler: Callable):
        """Handle incoming messages"""
        try:
            async for msg in subscription.messages:
                try:
                    # Parse event
                    data = json.loads(msg.data.decode())
                    event = Event.from_dict(data)
                    
                    # Call handler
                    await handler(event)
                    
                    # Message auto-acknowledged (no manual ack needed)
                    
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    # Auto-ack mode - no manual error handling needed
                    
        except Exception as e:
            logger.error(f"Subscription error: {e}")
    
    async def close(self):
        """Close NATS connection"""
        if self.nc:
            await self.nc.close()
            self._is_connected = False
            logger.info("Disconnected from NATS")
    
    async def _error_callback(self, e):
        logger.error(f"NATS error: {e}")
    
    async def _disconnected_callback(self):
        self._is_connected = False
        logger.warning("Disconnected from NATS")
    
    async def _reconnected_callback(self):
        self._is_connected = True
        logger.info("Reconnected to NATS")


# Singleton instance
_event_bus: Optional[NATSEventBus] = None


async def get_event_bus(service_name: str) -> NATSEventBus:
    """Get or create event bus instance"""
    global _event_bus
    
    if _event_bus is None:
        _event_bus = NATSEventBus(service_name)
        await _event_bus.connect()
    
    return _event_bus


async def publish_payment_event(payment_id: str, 
                               amount: float, 
                               status: str,
                               user_id: str,
                               metadata: Optional[Dict] = None):
    """Helper function to publish payment events"""
    event_bus = await get_event_bus("payment_service")
    
    # Determine event type based on status
    event_type_map = {
        "initiated": EventType.PAYMENT_INITIATED,
        "completed": EventType.PAYMENT_COMPLETED,
        "failed": EventType.PAYMENT_FAILED,
        "refunded": EventType.PAYMENT_REFUNDED
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
            "timestamp": datetime.utcnow().isoformat()
        },
        metadata=metadata
    )
    
    return await event_bus.publish_event(event)