"""
Device Service Event Handlers

Handle incoming events from other services (firmware, telemetry, auth).
Migrated from events.py and following wallet_service pattern.
"""

import logging
import json
from typing import Dict, Any, Set, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from ..device_service import DeviceService

logger = logging.getLogger(__name__)

# Track processed events to prevent duplicate processing
_processed_events: Set[str] = set()


def _is_event_processed(event_id: str) -> bool:
    """Check if event has been processed"""
    return event_id in _processed_events


def _mark_event_processed(event_id: str):
    """Mark event as processed"""
    _processed_events.add(event_id)
    # Keep only last 10000 events to prevent memory leak
    if len(_processed_events) > 10000:
        _processed_events.clear()


# ============================================================================
# Event Handler Registration
# ============================================================================

def get_event_handlers(device_service: 'DeviceService', event_bus):
    """
    Get event handlers for device service
    
    Args:
        device_service: DeviceService instance
        event_bus: Event bus instance
        
    Returns:
        Dict of event type to handler function
    """
    
    async def handle_firmware_uploaded_wrapper(event_data: Dict[str, Any]):
        await handle_firmware_uploaded(event_data, device_service, event_bus)
    
    async def handle_update_completed_wrapper(event_data: Dict[str, Any]):
        await handle_update_completed(event_data, device_service, event_bus)
    
    async def handle_telemetry_data_wrapper(event_data: Dict[str, Any]):
        await handle_telemetry_data(event_data, device_service, event_bus)
    
    async def handle_device_pairing_completed_wrapper(event_data: Dict[str, Any]):
        await handle_device_pairing_completed(event_data, device_service, event_bus)
    
    handlers = {
        "firmware.uploaded": handle_firmware_uploaded_wrapper,
        "FIRMWARE_UPLOADED": handle_firmware_uploaded_wrapper,
        "update.completed": handle_update_completed_wrapper,
        "UPDATE_COMPLETED": handle_update_completed_wrapper,
        "telemetry.data.received": handle_telemetry_data_wrapper,
        "TELEMETRY_DATA_RECEIVED": handle_telemetry_data_wrapper,
        "device.pairing.completed": handle_device_pairing_completed_wrapper,
        "DEVICE_PAIRING_COMPLETED": handle_device_pairing_completed_wrapper,
    }
    
    logger.info("Device service event handlers registered")
    return handlers


# ============================================================================
# Event Handlers
# ============================================================================

async def handle_firmware_uploaded(
    event_data: Dict[str, Any],
    device_service: 'DeviceService',
    event_bus
):
    """
    Handle firmware.uploaded event - Update device firmware info
    
    When new firmware is uploaded for a device model, update all compatible
    devices to show that a firmware update is available.
    """
    try:
        event_id = event_data.get("event_id")
        if event_id and _is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return
        
        firmware_id = event_data.get("firmware_id")
        device_model = event_data.get("device_model")
        version = event_data.get("version")
        
        if not firmware_id or not device_model or not version:
            logger.warning("firmware.uploaded event missing required fields")
            return
        
        logger.info(
            f"Handling firmware.uploaded event for model={device_model}, version={version}"
        )
        
        # TODO: Implement repository method to find devices by model
        # devices = await device_service.device_repo.find_devices_by_model(device_model)
        
        logger.info(
            f"New firmware {version} available for device model {device_model}. "
            f"Devices should be notified of available update."
        )
        
        if event_id:
            _mark_event_processed(event_id)
        
    except Exception as e:
        logger.error(f"Error handling firmware.uploaded event: {e}", exc_info=True)


async def handle_update_completed(
    event_data: Dict[str, Any],
    device_service: 'DeviceService',
    event_bus
):
    """
    Handle update.completed event - Update device firmware version
    
    When an OTA update completes successfully, update the device's
    firmware_version field to reflect the new version.
    """
    try:
        event_id = event_data.get("event_id")
        if event_id and _is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return
        
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
        device = await device_service.device_repo.get_device(device_id)
        if not device:
            logger.warning(f"Device {device_id} not found")
            return
        
        old_version = device.firmware_version
        await device_service.device_repo.update_device(
            device_id,
            {"firmware_version": firmware_version}
        )
        
        logger.info(
            f"Updated device {device_id} firmware version: {old_version} → {firmware_version}"
        )
        
        if event_id:
            _mark_event_processed(event_id)
        
    except Exception as e:
        logger.error(f"Error handling update.completed event: {e}", exc_info=True)


async def handle_telemetry_data(
    event_data: Dict[str, Any],
    device_service: 'DeviceService',
    event_bus
):
    """
    Handle telemetry.data.received event - Update device health status
    
    When telemetry data is received, optionally update device last_seen
    timestamp and health metrics.
    """
    try:
        event_id = event_data.get("event_id")
        if event_id and _is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return
        
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
        
        device = await device_service.device_repo.get_device(device_id)
        if not device:
            logger.debug(f"Device {device_id} not found (may not be registered)")
            return
        
        # Update last_seen
        await device_service.device_repo.update_device(
            device_id,
            {"last_seen": datetime.now(timezone.utc)}
        )
        
        # Update device status to ACTIVE if it was INACTIVE
        if device.status == "inactive":
            await device_service.update_device_status(device_id, "active")
            logger.info(f"Device {device_id} status changed to active based on telemetry")
        
        if event_id:
            _mark_event_processed(event_id)
        
    except Exception as e:
        logger.error(f"Error handling telemetry.data.received event: {e}", exc_info=True)


async def handle_device_pairing_completed(
    event_data: Dict[str, Any],
    device_service: 'DeviceService',
    event_bus
):
    """
    Handle device.pairing.completed event from auth_service
    
    When a device is successfully paired with a user, update device status
    and owner information.
    """
    try:
        event_id = event_data.get("event_id")
        if event_id and _is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return
        
        device_id = event_data.get("device_id")
        user_id = event_data.get("user_id")
        
        if not device_id or not user_id:
            logger.warning("device.pairing.completed event missing device_id or user_id")
            return
        
        logger.info(
            f"Handling device.pairing.completed event for device={device_id}, user={user_id}"
        )
        
        # Update device with owner and set status to active
        device = await device_service.device_repo.get_device(device_id)
        if not device:
            logger.warning(f"Device {device_id} not found")
            return
        
        old_status = device.status
        await device_service.device_repo.update_device(
            device_id,
            {
                "owner_id": user_id,
                "status": "active"
            }
        )
        
        logger.info(
            f"Device {device_id} paired with user {user_id}, status: {old_status} -> active"
        )
        
        if event_id:
            _mark_event_processed(event_id)
        
    except Exception as e:
        logger.error(f"Error handling device.pairing.completed event: {e}", exc_info=True)


# ============================================================================
# DeviceEventHandler Class (for compatibility with main.py)
# ============================================================================

class DeviceEventHandler:
    """Event handler class for device service"""

    def __init__(self, device_service: 'DeviceService'):
        self.device_service = device_service
        self._handlers = {
            "firmware.uploaded": self._handle_firmware_uploaded,
            "update.completed": self._handle_update_completed,
            "telemetry.data.received": self._handle_telemetry_data,
            "device.pairing.completed": self._handle_device_pairing_completed,
        }

    async def handle_event(self, msg):
        """Handle incoming NATS message"""
        try:
            import json
            data = json.loads(msg.data.decode()) if hasattr(msg, 'data') else msg
            event_type = data.get('type', data.get('event_type', ''))

            # Find matching handler
            for pattern, handler in self._handlers.items():
                if pattern in event_type.lower():
                    await handler(data)
                    return

            logger.debug(f"No handler for event type: {event_type}")
        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    async def _handle_firmware_uploaded(self, event_data):
        await handle_firmware_uploaded(event_data, self.device_service, None)

    async def _handle_update_completed(self, event_data):
        await handle_update_completed(event_data, self.device_service, None)

    async def _handle_telemetry_data(self, event_data):
        await handle_telemetry_data(event_data, self.device_service, None)

    async def _handle_device_pairing_completed(self, event_data):
        await handle_device_pairing_completed(event_data, self.device_service, None)
