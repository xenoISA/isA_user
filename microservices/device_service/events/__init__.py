"""
Device Service Events Module

Event-driven architecture for device lifecycle and status events.
Follows the standard wallet_service pattern.
"""

from .handlers import get_event_handlers, DeviceEventHandler
from .models import (
    DeviceRegisteredEventData,
    DeviceStatusChangedEventData,
    DevicePairedEventData,
    DeviceFirmwareUpdatedEventData,
    DeviceDeletedEventData,
    DeviceOfflineEventData,
    DeviceOnlineEventData,
    create_device_registered_event_data,
    create_device_status_changed_event_data,
    create_device_paired_event_data,
    create_device_firmware_updated_event_data,
    create_device_deleted_event_data,
    create_device_offline_event_data,
    create_device_online_event_data,
)
from .publishers import (
    publish_device_registered,
    publish_device_status_changed,
    publish_device_paired,
    publish_device_firmware_updated,
    publish_device_deleted,
    publish_device_offline,
    publish_device_online,
)

__all__ = [
    # Handlers
    'get_event_handlers',
    'DeviceEventHandler',

    # Models
    'DeviceRegisteredEventData',
    'DeviceStatusChangedEventData',
    'DevicePairedEventData',
    'DeviceFirmwareUpdatedEventData',
    'DeviceDeletedEventData',
    'DeviceOfflineEventData',
    'DeviceOnlineEventData',
    'create_device_registered_event_data',
    'create_device_status_changed_event_data',
    'create_device_paired_event_data',
    'create_device_firmware_updated_event_data',
    'create_device_deleted_event_data',
    'create_device_offline_event_data',
    'create_device_online_event_data',

    # Publishers
    'publish_device_registered',
    'publish_device_status_changed',
    'publish_device_paired',
    'publish_device_firmware_updated',
    'publish_device_deleted',
    'publish_device_offline',
    'publish_device_online',
]
