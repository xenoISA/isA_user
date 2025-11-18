"""
Device Service Event Publishers

Publish events for device lifecycle and status changes.
Following wallet_service pattern.
"""

import logging
from typing import Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    create_device_registered_event_data,
    create_device_status_changed_event_data,
    create_device_paired_event_data,
    create_device_firmware_updated_event_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Device Event Publishers
# ============================================================================

async def publish_device_registered(
    event_bus,
    device_id: str,
    device_name: str,
    device_type: str,
    owner_id: Optional[str] = None,
    event_id: Optional[str] = None
):
    """
    Publish device.registered event
    
    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        device_name: Device name
        device_type: Device type
        owner_id: Optional owner user ID
        event_id: Optional event ID for idempotency
    """
    try:
        event_data = create_device_registered_event_data(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            owner_id=owner_id
        )
        
        event = Event(
            event_id=event_id,
            event_type=EventType.DEVICE_REGISTERED,
            source=ServiceSource.DEVICE_SERVICE,
            data=event_data.model_dump()
        )
        
        await event_bus.publish(event)
        logger.info(f"Published device.registered for device {device_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish device.registered: {e}")
        raise


async def publish_device_status_changed(
    event_bus,
    device_id: str,
    old_status: str,
    new_status: str,
    reason: Optional[str] = None,
    event_id: Optional[str] = None
):
    """
    Publish device.status.changed event
    
    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        old_status: Previous status
        new_status: New status
        reason: Optional reason for status change
        event_id: Optional event ID for idempotency
    """
    try:
        event_data = create_device_status_changed_event_data(
            device_id=device_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason
        )
        
        event = Event(
            event_id=event_id,
            event_type=EventType.DEVICE_STATUS_CHANGED,
            source=ServiceSource.DEVICE_SERVICE,
            data=event_data.model_dump()
        )
        
        await event_bus.publish(event)
        logger.info(f"Published device.status.changed for device {device_id}: {old_status} -> {new_status}")
        
    except Exception as e:
        logger.error(f"Failed to publish device.status.changed: {e}")
        raise


async def publish_device_paired(
    event_bus,
    device_id: str,
    user_id: str,
    device_name: Optional[str] = None,
    device_type: Optional[str] = None,
    event_id: Optional[str] = None
):
    """
    Publish device.paired event
    
    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        user_id: User ID
        device_name: Optional device name
        device_type: Optional device type
        event_id: Optional event ID for idempotency
    """
    try:
        event_data = create_device_paired_event_data(
            device_id=device_id,
            user_id=user_id,
            device_name=device_name,
            device_type=device_type
        )
        
        event = Event(
            event_id=event_id,
            event_type=EventType.DEVICE_PAIRED,
            source=ServiceSource.DEVICE_SERVICE,
            data=event_data.model_dump()
        )
        
        await event_bus.publish(event)
        logger.info(f"Published device.paired for device {device_id}, user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish device.paired: {e}")
        raise


async def publish_device_firmware_updated(
    event_bus,
    device_id: str,
    old_version: str,
    new_version: str,
    update_id: Optional[str] = None,
    event_id: Optional[str] = None
):
    """
    Publish device.firmware.updated event
    
    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        old_version: Previous firmware version
        new_version: New firmware version
        update_id: Optional OTA update ID
        event_id: Optional event ID for idempotency
    """
    try:
        event_data = create_device_firmware_updated_event_data(
            device_id=device_id,
            old_version=old_version,
            new_version=new_version,
            update_id=update_id
        )
        
        event = Event(
            event_id=event_id,
            event_type=EventType.DEVICE_FIRMWARE_UPDATED,
            source=ServiceSource.DEVICE_SERVICE,
            data=event_data.model_dump()
        )
        
        await event_bus.publish(event)
        logger.info(f"Published device.firmware.updated for device {device_id}: {old_version} -> {new_version}")
        
    except Exception as e:
        logger.error(f"Failed to publish device.firmware.updated: {e}")
        raise
