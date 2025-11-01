"""
Device Service Event Handlers

Handles event-driven updates for device firmware and status
"""

import logging
import json
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .device_service import DeviceService

logger = logging.getLogger(__name__)


class DeviceEventHandler:
    """Event handler for Device Service"""

    def __init__(self, device_service: 'DeviceService'):
        """
        Initialize event handler

        Args:
            device_service: Device service instance
        """
        self.device_service = device_service

    async def handle_event(self, msg):
        """
        Generic event handler dispatcher

        Args:
            msg: NATS message
        """
        try:
            data = json.loads(msg.data.decode())
            event_type = data.get("event_type") or data.get("type")

            logger.info(f"Received event: {event_type}")

            if event_type == "firmware.uploaded" or event_type == "FIRMWARE_UPLOADED":
                await self.handle_firmware_uploaded(data)
            elif event_type == "update.completed" or event_type == "UPDATE_COMPLETED":
                await self.handle_update_completed(data)
            elif event_type == "telemetry.data.received" or event_type == "TELEMETRY_DATA_RECEIVED":
                await self.handle_telemetry_data(data)
            else:
                logger.warning(f"Unknown event type: {event_type}")

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    async def handle_firmware_uploaded(self, event_data: Dict[str, Any]):
        """
        Handle firmware.uploaded event - Update device firmware info

        When new firmware is uploaded for a device model, update all compatible
        devices to show that a firmware update is available.

        Args:
            event_data: Event data containing firmware_id, device_model, version, etc.
        """
        try:
            firmware_id = event_data.get("firmware_id")
            device_model = event_data.get("device_model")
            version = event_data.get("version")

            if not firmware_id or not device_model or not version:
                logger.warning("firmware.uploaded event missing required fields")
                return

            logger.info(
                f"Handling firmware.uploaded event for model={device_model}, version={version}"
            )

            # Find all devices with matching model
            # TODO: Implement repository method to find devices by model
            # devices = await self.device_service.device_repo.find_devices_by_model(device_model)

            # Update device metadata to indicate firmware update available
            # For now, log the action
            logger.info(
                f"New firmware {version} available for device model {device_model}. "
                f"Devices should be notified of available update."
            )

            # In production, you might:
            # 1. Update device metadata with available_firmware_version
            # 2. Send notification to device owners
            # 3. Create OTA update campaigns automatically

        except Exception as e:
            logger.error(f"Error handling firmware.uploaded event: {e}", exc_info=True)

    async def handle_update_completed(self, event_data: Dict[str, Any]):
        """
        Handle update.completed event - Update device firmware version

        When an OTA update completes successfully, update the device's
        firmware_version field to reflect the new version.

        Args:
            event_data: Event data containing device_id, firmware_version, etc.
        """
        try:
            device_id = event_data.get("device_id")
            firmware_version = event_data.get("firmware_version")
            update_id = event_data.get("update_id")

            if not device_id or not firmware_version:
                logger.warning("update.completed event missing device_id or firmware_version")
                return

            logger.info(
                f"Handling update.completed event for device={device_id}, "
                f"new_version={firmware_version}, update_id={update_id}"
            )

            # Update device firmware version
            device = await self.device_service.device_repo.get_device(device_id)

            if not device:
                logger.warning(f"Device {device_id} not found")
                return

            # Update firmware version
            old_version = device.firmware_version
            await self.device_service.device_repo.update_device(
                device_id,
                {"firmware_version": firmware_version}
            )

            logger.info(
                f"Updated device {device_id} firmware version: {old_version} → {firmware_version}"
            )

            # Log firmware update completion (no specific event type for device.updated)
            logger.info(
                f"Device {device_id} firmware updated: {old_version} → {firmware_version} "
                f"(update_id: {update_id})"
            )

        except Exception as e:
            logger.error(f"Error handling update.completed event: {e}", exc_info=True)

    async def handle_telemetry_data(self, event_data: Dict[str, Any]):
        """
        Handle telemetry.data.received event - Update device health status

        When telemetry data is received, optionally update device last_seen
        timestamp and health metrics.

        Args:
            event_data: Event data containing device_id, metric_name, value, etc.
        """
        try:
            device_id = event_data.get("device_id")
            metric_name = event_data.get("metric_name")
            value = event_data.get("value")

            if not device_id:
                logger.warning("telemetry.data.received event missing device_id")
                return

            logger.debug(
                f"Handling telemetry.data.received event for device={device_id}, "
                f"metric={metric_name}, value={value}"
            )

            # Update device last_seen timestamp
            from datetime import datetime, timezone

            device = await self.device_service.device_repo.get_device(device_id)

            if not device:
                # Device might not be registered yet, which is OK for telemetry
                logger.debug(f"Device {device_id} not found (may not be registered)")
                return

            # Update last_seen
            await self.device_service.device_repo.update_device(
                device_id,
                {"last_seen": datetime.now(timezone.utc)}
            )

            # Optionally update device status to ACTIVE if it was INACTIVE
            if device.status == "inactive":
                await self.device_service.update_device_status(device_id, "active")
                logger.info(f"Device {device_id} status changed to active based on telemetry")

            # TODO: Implement health score calculation based on telemetry metrics
            # if metric_name in ["cpu_usage", "memory_usage", "temperature"]:
            #     await self._update_device_health_score(device_id, metric_name, value)

        except Exception as e:
            logger.error(f"Error handling telemetry.data.received event: {e}", exc_info=True)
