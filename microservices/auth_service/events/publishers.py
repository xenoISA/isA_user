"""
Auth Service Event Publishers

Publish events for authentication and device pairing.
Following wallet_service pattern.
"""

import logging
from datetime import datetime
from typing import Optional

from core.nats_client import Event

from .models import (
    create_pairing_token_generated_event_data,
    create_pairing_token_verified_event_data,
    create_pairing_completed_event_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Device Pairing Event Publishers
# ============================================================================

async def publish_device_pairing_token_generated(
    event_bus,
    device_id: str,
    pairing_token: str,
    expires_at: datetime,
    event_id: Optional[str] = None
):
    """
    Publish device.pairing_token.generated event
    
    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        pairing_token: Generated pairing token
        expires_at: Token expiration time
        event_id: Optional event ID for idempotency
    """
    try:
        event_data = create_pairing_token_generated_event_data(
            device_id=device_id,
            pairing_token=pairing_token,
            expires_at=expires_at
        )
        
        event = Event(
            event_id=event_id,
            event_type="device.pairing_token.generated",
            source="auth_service",
            data=event_data.model_dump()
        )
        
        await event_bus.publish(event)
        logger.info(f"Published device.pairing_token.generated for device {device_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish device.pairing_token.generated: {e}")
        raise


async def publish_device_pairing_token_verified(
    event_bus,
    device_id: str,
    user_id: str,
    pairing_token: str,
    event_id: Optional[str] = None
):
    """
    Publish device.pairing_token.verified event
    
    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        user_id: User ID who verified the token
        pairing_token: Verified pairing token
        event_id: Optional event ID for idempotency
    """
    try:
        event_data = create_pairing_token_verified_event_data(
            device_id=device_id,
            user_id=user_id,
            pairing_token=pairing_token
        )
        
        event = Event(
            event_id=event_id,
            event_type="device.pairing_token.verified",
            source="auth_service",
            data=event_data.model_dump()
        )
        
        await event_bus.publish(event)
        logger.info(f"Published device.pairing_token.verified for device {device_id}, user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish device.pairing_token.verified: {e}")
        raise


async def publish_device_pairing_completed(
    event_bus,
    device_id: str,
    user_id: str,
    device_name: Optional[str] = None,
    device_type: Optional[str] = None,
    event_id: Optional[str] = None
):
    """
    Publish device.pairing.completed event
    
    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        user_id: User ID who paired the device
        device_name: Optional device name
        device_type: Optional device type
        event_id: Optional event ID for idempotency
    """
    try:
        event_data = create_pairing_completed_event_data(
            device_id=device_id,
            user_id=user_id,
            device_name=device_name,
            device_type=device_type
        )
        
        event = Event(
            event_id=event_id,
            event_type="device.pairing.completed",
            source="auth_service",
            data=event_data.model_dump()
        )
        
        await event_bus.publish(event)
        logger.info(f"Published device.pairing.completed for device {device_id}, user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish device.pairing.completed: {e}")
        raise
