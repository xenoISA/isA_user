"""
OTA Service Event Publishers

Centralized functions for publishing events from OTA Service
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from core.nats_client import Event, EventType, ServiceSource
from .models import (
    FirmwareUploadedEvent,
    CampaignCreatedEvent,
    CampaignStartedEvent,
    UpdateCancelledEvent,
    RollbackInitiatedEvent
)

logger = logging.getLogger(__name__)


async def publish_firmware_uploaded(
    event_bus,
    firmware_id: str,
    name: str,
    version: str,
    device_model: str,
    file_size: int,
    is_security_update: bool,
    uploaded_by: str
) -> bool:
    """
    Publish firmware.uploaded event

    Args:
        event_bus: Event bus instance
        firmware_id: Unique firmware ID
        name: Firmware name
        version: Firmware version
        device_model: Target device model
        file_size: File size in bytes
        is_security_update: Is this a security update
        uploaded_by: User ID who uploaded

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = FirmwareUploadedEvent(
            firmware_id=firmware_id,
            name=name,
            version=version,
            device_model=device_model,
            file_size=file_size,
            is_security_update=is_security_update,
            uploaded_by=uploaded_by,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.FIRMWARE_UPLOADED,
            source=ServiceSource.OTA_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published firmware.uploaded event for firmware {firmware_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish firmware.uploaded event: {e}")
        return False


async def publish_campaign_created(
    event_bus,
    campaign_id: str,
    name: str,
    firmware_id: str,
    firmware_version: str,
    target_device_count: int,
    deployment_strategy: str,
    priority: str,
    created_by: str
) -> bool:
    """
    Publish campaign.created event

    Args:
        event_bus: Event bus instance
        campaign_id: Unique campaign ID
        name: Campaign name
        firmware_id: Firmware ID to deploy
        firmware_version: Firmware version
        target_device_count: Number of target devices
        deployment_strategy: Deployment strategy
        priority: Campaign priority
        created_by: User ID who created

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = CampaignCreatedEvent(
            campaign_id=campaign_id,
            name=name,
            firmware_id=firmware_id,
            firmware_version=firmware_version,
            target_device_count=target_device_count,
            deployment_strategy=deployment_strategy,
            priority=priority,
            created_by=created_by,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.CAMPAIGN_CREATED,
            source=ServiceSource.OTA_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published campaign.created event for campaign {campaign_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish campaign.created event: {e}")
        return False


async def publish_campaign_started(
    event_bus,
    campaign_id: str,
    name: str,
    firmware_id: str,
    firmware_version: str,
    target_device_count: int
) -> bool:
    """
    Publish campaign.started event

    Args:
        event_bus: Event bus instance
        campaign_id: Unique campaign ID
        name: Campaign name
        firmware_id: Firmware ID being deployed
        firmware_version: Firmware version
        target_device_count: Number of target devices

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = CampaignStartedEvent(
            campaign_id=campaign_id,
            name=name,
            firmware_id=firmware_id,
            firmware_version=firmware_version,
            target_device_count=target_device_count,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.CAMPAIGN_STARTED,
            source=ServiceSource.OTA_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published campaign.started event for campaign {campaign_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish campaign.started event: {e}")
        return False


async def publish_update_cancelled(
    event_bus,
    update_id: str,
    device_id: str,
    firmware_id: str,
    firmware_version: str,
    campaign_id: Optional[str] = None
) -> bool:
    """
    Publish update.cancelled event

    Args:
        event_bus: Event bus instance
        update_id: Update ID
        device_id: Device ID
        firmware_id: Firmware ID
        firmware_version: Firmware version
        campaign_id: Campaign ID if part of campaign

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = UpdateCancelledEvent(
            update_id=update_id,
            device_id=device_id,
            firmware_id=firmware_id,
            firmware_version=firmware_version,
            campaign_id=campaign_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.UPDATE_CANCELLED,
            source=ServiceSource.OTA_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published update.cancelled event for update {update_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish update.cancelled event: {e}")
        return False


async def publish_rollback_initiated(
    event_bus,
    rollback_id: str,
    device_id: str,
    from_version: str,
    to_version: str,
    trigger: str
) -> bool:
    """
    Publish rollback.initiated event

    Args:
        event_bus: Event bus instance
        rollback_id: Rollback ID
        device_id: Device ID
        from_version: Current firmware version
        to_version: Target rollback version
        trigger: Rollback trigger (manual/automatic)

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = RollbackInitiatedEvent(
            rollback_id=rollback_id,
            device_id=device_id,
            from_version=from_version,
            to_version=to_version,
            trigger=trigger,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.ROLLBACK_INITIATED,
            source=ServiceSource.OTA_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published rollback.initiated event for rollback {rollback_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish rollback.initiated event: {e}")
        return False
