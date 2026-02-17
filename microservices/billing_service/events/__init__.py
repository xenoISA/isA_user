"""
Billing Service Events

集中管理 billing_service 的事件模型、发布器和处理器

Event Architecture (New Pattern):
- BillingEventType: Service-specific event types (replaces core.nats_client.EventType)
- BillingEventPublisher: Publisher class using NATSTransport
- BillingStreamConfig: Stream configuration

Legacy Support:
- publish_* functions still work with NATSEventBus
- Will be deprecated once all services migrate
"""

# Handlers
from .handlers import get_event_handlers

# Models - New pattern
from .models import (
    # Event types (service-specific)
    BillingEventType,
    BillingSubscribedEventType,
    BillingStreamConfig,
    # Event data models
    BillingCalculatedEventData,
    BillingErrorEventData,
    UnitType,
    UsageEventData,
    create_billing_calculated_event_data,
    parse_usage_event,
)

# Publishers - New pattern
from .publishers import (
    BillingEventPublisher,  # New: class-based publisher
    # Legacy: standalone functions
    publish_billing_calculated,
    publish_billing_error,
    publish_usage_recorded,
)

__all__ = [
    # Event Types (New Pattern - service-specific)
    "BillingEventType",
    "BillingSubscribedEventType",
    "BillingStreamConfig",
    # Event Data Models
    "UsageEventData",
    "BillingCalculatedEventData",
    "BillingErrorEventData",
    "UnitType",
    "parse_usage_event",
    "create_billing_calculated_event_data",
    # Publishers (New Pattern)
    "BillingEventPublisher",
    # Publishers (Legacy - for backward compatibility)
    "publish_billing_calculated",
    "publish_billing_error",
    "publish_usage_recorded",
    # Handlers
    "get_event_handlers",
]
