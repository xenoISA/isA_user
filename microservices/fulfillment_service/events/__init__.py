"""
Fulfillment Service Events Module

Exports all event-related functionality for fulfillment service
"""

from .models import (
    FulfillmentEventType,
    FulfillmentSubscribedEventType,
    FulfillmentStreamConfig,
    ShipmentItem,
    ShipmentPreparedEvent,
    LabelCreatedEvent,
    ShipmentCanceledEvent,
    ShipmentFailedEvent
)

from .publishers import (
    publish_shipment_prepared,
    publish_label_created,
    publish_shipment_canceled,
    publish_shipment_failed
)

from .handlers import get_event_handlers

__all__ = [
    # Event Types
    "FulfillmentEventType",
    "FulfillmentSubscribedEventType",
    "FulfillmentStreamConfig",
    # Event Models
    "ShipmentItem",
    "ShipmentPreparedEvent",
    "LabelCreatedEvent",
    "ShipmentCanceledEvent",
    "ShipmentFailedEvent",
    # Publishers
    "publish_shipment_prepared",
    "publish_label_created",
    "publish_shipment_canceled",
    "publish_shipment_failed",
    # Handlers
    "get_event_handlers"
]
