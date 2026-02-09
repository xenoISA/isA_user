"""
Telemetry Service Event Handlers

Handles incoming events from other services via NATS
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("telemetry_service.events")


class TelemetryEventHandler:
    """Handle events for Telemetry Service"""

    def __init__(self, telemetry_repository):
        """Initialize event handler with repository"""
        self.telemetry_repo = telemetry_repository

    async def handle_device_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle device.deleted event

        When a device is deleted, we should:
        - Mark device's telemetry data for cleanup (or stop accepting new data)
        - Disable alert rules specific to that device

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

            # Disable alert rules for this device
            # We don't delete telemetry data (keep for historical analysis)
            # but we can disable alert rules that target this device
            disabled_count = await self.telemetry_repo.disable_device_alert_rules(device_id)

            logger.info(f"Disabled {disabled_count} alert rules for deleted device {device_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle device.deleted event: {e}", exc_info=True)
            return False

    async def handle_user_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle user.deleted event

        When a user is deleted, we should:
        - Delete or anonymize telemetry data for privacy compliance
        - Disable alert rules for this user

        Args:
            event_data: Event data containing user_id

        Returns:
            bool: True if handled successfully
        """
        try:
            user_id = event_data.get('user_id')
            if not user_id:
                logger.warning("user.deleted event missing user_id")
                return False

            logger.info(f"Handling user.deleted event for user {user_id}")

            # Disable all alert rules for this user
            disabled_count = await self.telemetry_repo.disable_user_alert_rules(user_id)
            logger.info(f"Disabled {disabled_count} alert rules for user {user_id}")

            # Optionally anonymize or delete user telemetry data
            # For now, we keep historical data but mark it as from deleted user
            await self.telemetry_repo.anonymize_user_telemetry(user_id)
            logger.info(f"Anonymized telemetry data for user {user_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to handle user.deleted event: {e}", exc_info=True)
            return False

    async def handle_event(self, event) -> bool:
        """
        Route events to appropriate handlers

        Args:
            event: Event object from NATS

        Returns:
            bool: True if event was handled
        """
        try:
            event_type = event.type
            event_data = event.data

            logger.debug(f"Received event: {event_type}")

            # Route to specific handler
            if event_type == "device.deleted":
                return await self.handle_device_deleted(event_data)
            elif event_type == "user.deleted":
                return await self.handle_user_deleted(event_data)
            else:
                logger.debug(f"No handler for event type: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)
            return False

    def get_subscriptions(self) -> List[str]:
        """
        Get list of event types to subscribe to

        Returns:
            List of event type patterns
        """
        return [
            "device.deleted",
            "user.deleted",
        ]
