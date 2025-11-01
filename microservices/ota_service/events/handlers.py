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


class OTAEventHandler:
    """
    Handles events subscribed by OTA Service

    Subscribes to:
    - device.deleted: Cancel all pending updates for deleted device
    """

    def __init__(self, ota_repository):
        """
        Initialize event handler

        Args:
            ota_repository: OTARepository instance for data access
        """
        self.ota_repo = ota_repository

    async def handle_device_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle device.deleted event

        When a device is deleted, cancel all pending updates for that device

        Args:
            event_data: Event data containing device_id

        Returns:
            bool: True if handled successfully
        """
        try:
            device_id = event_data.get('device_id')
            if not device_id:
                logger.warning("device.deleted event missing device_id")
                return False

            logger.info(f"Handling device.deleted event for device {device_id}")

            # Cancel all pending/in-progress updates for this device
            cancelled_count = await self.ota_repo.cancel_device_updates(device_id)

            logger.info(f"Cancelled {cancelled_count} updates for device {device_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle device.deleted event: {e}", exc_info=True)
            return False

    async def handle_event(self, event: Event) -> bool:
        """
        Route event to appropriate handler

        Args:
            event: The event to handle

        Returns:
            bool: True if handled successfully
        """
        try:
            event_type = event.type

            if event_type == "device.deleted":
                return await self.handle_device_deleted(event.data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to handle event: {e}", exc_info=True)
            return False

    def get_subscriptions(self) -> list:
        """
        Get list of event types this handler subscribes to

        Returns:
            list: List of event type values to subscribe to
        """
        return [
            "device.deleted",
        ]
