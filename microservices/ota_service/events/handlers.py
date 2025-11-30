"""
OTA Service Event Handlers

Handles incoming events from other services via NATS
"""

import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType

logger = logging.getLogger(__name__)


# ============================================================================
# Event Handlers
# ============================================================================


async def handle_device_deleted(event_data: Dict[str, Any], ota_repository):
    """
    Handle device.deleted event from device_service

    When a device is deleted, cancel all pending updates for that device

    Event data:
        - device_id: Device ID
        - device_name: Device name (optional)
        - reason: Deletion reason (optional)

    Args:
        event_data: Event data containing device_id
        ota_repository: OTARepository instance for data access
    """
    try:
        device_id = event_data.get('device_id')
        if not device_id:
            logger.warning("device.deleted event missing device_id")
            return

        logger.info(f"Received device.deleted event for device {device_id}")

        # Cancel all pending/in-progress updates for this device
        cancelled_count = await ota_repository.cancel_device_updates(device_id)

        logger.info(f"Cancelled {cancelled_count} OTA updates for deleted device {device_id}")

    except Exception as e:
        logger.error(f"Error handling device.deleted event: {e}", exc_info=True)


# ============================================================================
# Event Handler Registry
# ============================================================================


def get_event_handlers(ota_repository) -> Dict[str, callable]:
    """
    Return a mapping of event patterns to handler functions

    Event patterns include the service prefix for proper event routing.
    This will be used in main.py to register event subscriptions.

    Args:
        ota_repository: OTARepository instance for data access

    Returns:
        Dict mapping event patterns to handler functions
    """
    return {
        "device_service.device.deleted": lambda event: handle_device_deleted(event.data, ota_repository),
    }
