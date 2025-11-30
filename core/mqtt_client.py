"""
MQTT Client for isA Cloud Platform

Centralized MQTT event bus using AsyncMQTTClient from isa_common.
Provides async-first IoT messaging with topic patterns for device commands,
sensor readings, and system events.
"""

import json
import logging
import secrets
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from isa_common import AsyncMQTTClient

from .config_manager import ConfigManager

logger = logging.getLogger("mqtt_client")


# Topic patterns for standardized messaging
class MQTTTopics:
    """Standardized MQTT topic patterns"""

    # Device commands
    DEVICE_COMMANDS = "devices/{device_id}/commands"
    DEVICE_STATUS = "devices/{device_id}/status"
    DEVICE_TELEMETRY = "devices/{device_id}/telemetry"

    # Sensors
    SENSOR_READINGS = "sensors/{sensor_id}/readings"
    SENSOR_ALERTS = "sensors/{sensor_id}/alerts"

    # System events
    SYSTEM_EVENTS = "system/{service_name}/events"
    SYSTEM_HEALTH = "system/{service_name}/health"

    # Alerts
    ALERTS = "alerts/{alert_type}"

    # IoT commands (OTA, config, etc.)
    OTA_COMMANDS = "ota/{device_id}/commands"
    CONFIG_UPDATES = "config/{device_id}/updates"

    @classmethod
    def device_commands(cls, device_id: str) -> str:
        return cls.DEVICE_COMMANDS.format(device_id=device_id)

    @classmethod
    def device_status(cls, device_id: str) -> str:
        return cls.DEVICE_STATUS.format(device_id=device_id)

    @classmethod
    def device_telemetry(cls, device_id: str) -> str:
        return cls.DEVICE_TELEMETRY.format(device_id=device_id)

    @classmethod
    def sensor_readings(cls, sensor_id: str) -> str:
        return cls.SENSOR_READINGS.format(sensor_id=sensor_id)

    @classmethod
    def sensor_alerts(cls, sensor_id: str) -> str:
        return cls.SENSOR_ALERTS.format(sensor_id=sensor_id)

    @classmethod
    def system_events(cls, service_name: str) -> str:
        return cls.SYSTEM_EVENTS.format(service_name=service_name)

    @classmethod
    def alerts(cls, alert_type: str) -> str:
        return cls.ALERTS.format(alert_type=alert_type)


class MQTTEventBus:
    """
    Centralized MQTT event bus for IoT messaging.

    Uses AsyncMQTTClient from isa_common for true async operations.
    Follows the same pattern as NATSEventBus for consistency.
    """

    def __init__(
        self,
        service_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ):
        """
        Initialize MQTT event bus.

        Args:
            service_name: Name of the service using this bus
            host: MQTT service host (defaults to config)
            port: MQTT service port (defaults to config)
            user_id: User ID for multi-tenant operations
            organization_id: Organization ID for multi-tenant operations
        """
        self.service_name = service_name

        # Load config
        config_manager = ConfigManager(service_name)
        config = config_manager.get_service_config()

        # MQTT connection settings
        self.host = host or getattr(config, "mqtt_host", "localhost")
        self.port = port or getattr(config, "mqtt_port", 50053)
        self.user_id = user_id or service_name
        self.organization_id = organization_id or "default"

        # Async client from isa_common
        self.client = AsyncMQTTClient(
            host=self.host,
            port=self.port,
            user_id=self.user_id,
            organization_id=self.organization_id,
        )

        # Connection state
        self.session_id: Optional[str] = None
        self.connected = False

        # Message handlers
        self._handlers: Dict[str, List[Callable]] = {}

        logger.info(f"MQTTEventBus initialized for service '{service_name}'")

    async def connect(self, client_id: Optional[str] = None) -> bool:
        """
        Connect to MQTT broker.

        Args:
            client_id: Optional client ID (defaults to service_name)

        Returns:
            bool: True if connected successfully
        """
        try:
            client_id = client_id or f"{self.service_name}-{secrets.token_hex(4)}"

            async with self.client:
                result = await self.client.mqtt_connect(client_id)
                self.session_id = result.get("session_id")
                self.connected = True

            logger.info(f"MQTT connected with session: {self.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            self.connected = False
            return False

    async def disconnect(self) -> bool:
        """Disconnect from MQTT broker."""
        try:
            if self.session_id and self.connected:
                async with self.client:
                    await self.client.disconnect(self.session_id)
                self.connected = False
                self.session_id = None
                logger.info("MQTT disconnected")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting from MQTT: {e}")
            return False

    async def close(self):
        """Clean shutdown of MQTT connection."""
        await self.disconnect()

    async def publish(
        self,
        topic: str,
        payload: bytes,
        qos: int = 1,
        retained: bool = False,
    ) -> bool:
        """
        Publish binary message to topic.

        Args:
            topic: MQTT topic
            payload: Binary payload
            qos: QoS level (0, 1, or 2)
            retained: Whether to retain message

        Returns:
            bool: True if published successfully
        """
        try:
            if not self.connected or not self.session_id:
                logger.warning("MQTT not connected, attempting to connect...")
                if not await self.connect():
                    return False

            async with self.client:
                result = await self.client.publish(
                    self.session_id, topic, payload, qos=qos, retained=retained
                )

            success = result.get("success", False)
            if success:
                logger.debug(f"Published to '{topic}' (QoS {qos})")
            else:
                logger.error(f"Failed to publish to '{topic}'")
            return success

        except Exception as e:
            logger.error(f"Error publishing to '{topic}': {e}")
            return False

    async def publish_json(
        self,
        topic: str,
        data: Dict[str, Any],
        qos: int = 1,
        retained: bool = False,
    ) -> bool:
        """
        Publish JSON message to topic.

        Args:
            topic: MQTT topic
            data: Data dictionary to serialize as JSON
            qos: QoS level (0, 1, or 2)
            retained: Whether to retain message

        Returns:
            bool: True if published successfully
        """
        try:
            if not self.connected or not self.session_id:
                if not await self.connect():
                    return False

            async with self.client:
                result = await self.client.publish_json(
                    self.session_id, topic, data, qos=qos, retained=retained
                )

            return result.get("success", False)

        except Exception as e:
            logger.error(f"Error publishing JSON to '{topic}': {e}")
            return False

    async def publish_batch(
        self,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        Publish multiple messages efficiently.

        Args:
            messages: List of message dicts with 'topic', 'payload', 'qos', 'retained'

        Returns:
            Dict with 'published_count' and 'failed_count'
        """
        try:
            if not self.connected or not self.session_id:
                if not await self.connect():
                    return {"published_count": 0, "failed_count": len(messages)}

            async with self.client:
                result = await self.client.publish_batch(self.session_id, messages)

            return {
                "published_count": result.get("published_count", 0),
                "failed_count": result.get("failed_count", 0),
            }

        except Exception as e:
            logger.error(f"Error in batch publish: {e}")
            return {"published_count": 0, "failed_count": len(messages)}

    # Device command convenience methods

    async def send_device_command(
        self,
        device_id: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        priority: int = 1,
        require_ack: bool = True,
    ) -> Optional[str]:
        """
        Send command to device.

        Args:
            device_id: Target device ID
            command: Command name
            parameters: Command parameters
            timeout: Command timeout in seconds
            priority: Priority level (1-10)
            require_ack: Whether acknowledgment is required

        Returns:
            str: Command ID if sent, None on failure
        """
        command_id = secrets.token_hex(16)

        command_data = {
            "device_id": device_id,
            "command": command,
            "parameters": parameters or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "command_id": command_id,
            "timeout": timeout,
            "priority": priority,
            "require_ack": require_ack,
        }

        topic = MQTTTopics.device_commands(device_id)

        if await self.publish_json(topic, command_data, qos=2):
            logger.info(f"Device command sent: {command} -> {device_id} (ID: {command_id})")
            return command_id
        else:
            logger.error(f"Failed to send device command: {command} -> {device_id}")
            return None

    async def send_ota_command(
        self,
        device_id: str,
        firmware_url: str,
        version: str,
        checksum: str,
        force: bool = False,
    ) -> Optional[str]:
        """
        Send OTA update command to device.

        Args:
            device_id: Target device ID
            firmware_url: URL to download firmware
            version: Firmware version
            checksum: Firmware checksum
            force: Force update even if same version

        Returns:
            str: Command ID if sent, None on failure
        """
        parameters = {
            "firmware_url": firmware_url,
            "version": version,
            "checksum": checksum,
            "force": force,
        }

        return await self.send_device_command(
            device_id=device_id,
            command="ota_update",
            parameters=parameters,
            timeout=300,  # OTA updates need longer timeout
            priority=5,   # High priority
        )

    async def publish_device_status(
        self,
        device_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish device status update (retained message).

        Args:
            device_id: Device ID
            status: Status string (e.g., 'online', 'offline', 'error')
            metadata: Additional metadata

        Returns:
            bool: True if published successfully
        """
        status_data = {
            "device_id": device_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **(metadata or {}),
        }

        topic = MQTTTopics.device_status(device_id)
        return await self.publish_json(topic, status_data, qos=1, retained=True)

    async def publish_sensor_reading(
        self,
        sensor_id: str,
        reading: Dict[str, Any],
        qos: int = 0,
    ) -> bool:
        """
        Publish sensor reading.

        Args:
            sensor_id: Sensor ID
            reading: Reading data dict
            qos: QoS level (default 0 for high-frequency data)

        Returns:
            bool: True if published successfully
        """
        reading_data = {
            "sensor_id": sensor_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **reading,
        }

        topic = MQTTTopics.sensor_readings(sensor_id)
        return await self.publish_json(topic, reading_data, qos=qos)

    async def publish_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "WARNING",
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish alert message (retained, QoS 2).

        Args:
            alert_type: Type of alert (e.g., 'temperature', 'security')
            message: Alert message
            severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
            source: Source of alert (device_id, sensor_id, etc.)
            metadata: Additional metadata

        Returns:
            bool: True if published successfully
        """
        alert_data = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "source": source or self.service_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **(metadata or {}),
        }

        topic = MQTTTopics.alerts(alert_type)
        return await self.publish_json(topic, alert_data, qos=2, retained=True)

    # Device management

    async def register_device(
        self,
        device_id: str,
        device_name: str,
        device_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Register device with MQTT service.

        Args:
            device_id: Unique device ID
            device_name: Human-readable device name
            device_type: Device type (sensor, actuator, gateway, etc.)
            metadata: Additional device metadata

        Returns:
            bool: True if registered successfully
        """
        try:
            async with self.client:
                result = await self.client.register_device(
                    device_id, device_name, device_type, metadata or {}
                )
            return result.get("success", False)

        except Exception as e:
            logger.error(f"Error registering device {device_id}: {e}")
            return False

    async def update_device_status_registry(
        self,
        device_id: str,
        status: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update device status in MQTT service registry.

        Args:
            device_id: Device ID
            status: Status code (0=UNKNOWN, 1=ONLINE, 2=OFFLINE, 3=ERROR)
            metadata: Additional metadata

        Returns:
            bool: True if updated successfully
        """
        try:
            async with self.client:
                result = await self.client.update_device_status(
                    device_id, status, metadata or {}
                )
            return result.get("success", False)

        except Exception as e:
            logger.error(f"Error updating device status {device_id}: {e}")
            return False

    async def get_statistics(self) -> Dict[str, Any]:
        """Get MQTT service statistics."""
        try:
            async with self.client:
                return await self.client.get_statistics()
        except Exception as e:
            logger.error(f"Error getting MQTT statistics: {e}")
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """Check MQTT service health."""
        try:
            async with self.client:
                return await self.client.health_check()
        except Exception as e:
            logger.error(f"MQTT health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


# Global instance and factory function (similar to nats_client.py)
_mqtt_bus_instance: Optional[MQTTEventBus] = None


async def get_mqtt_bus(service_name: str) -> MQTTEventBus:
    """
    Get or create global MQTTEventBus instance.

    Args:
        service_name: Name of the calling service

    Returns:
        MQTTEventBus: Initialized and connected event bus
    """
    global _mqtt_bus_instance

    if _mqtt_bus_instance is None:
        _mqtt_bus_instance = MQTTEventBus(service_name)
        await _mqtt_bus_instance.connect()
        logger.info(f"Created global MQTTEventBus for '{service_name}'")

    return _mqtt_bus_instance


# Backward compatibility: DeviceCommandClient as async wrapper
class DeviceCommandClient:
    """
    Async device command client.

    Wrapper around MQTTEventBus for device command operations.
    Maintained for backward compatibility.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 50053,
        user_id: str = "device_command_client",
    ):
        self.mqtt_bus = MQTTEventBus(
            service_name="device_command_client",
            host=host,
            port=port,
            user_id=user_id,
        )

    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        return await self.mqtt_bus.connect()

    async def disconnect(self):
        """Disconnect from MQTT broker."""
        await self.mqtt_bus.disconnect()

    async def send_device_command(
        self,
        device_id: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        priority: int = 1,
        require_ack: bool = True,
    ) -> Optional[str]:
        """Send command to device."""
        return await self.mqtt_bus.send_device_command(
            device_id, command, parameters, timeout, priority, require_ack
        )

    async def send_ota_command(
        self,
        device_id: str,
        firmware_url: str,
        version: str,
        checksum: str,
        force: bool = False,
    ) -> Optional[str]:
        """Send OTA update command."""
        return await self.mqtt_bus.send_ota_command(
            device_id, firmware_url, version, checksum, force
        )

    def is_connected(self) -> bool:
        """Check connection status."""
        return self.mqtt_bus.connected


# Factory functions (backward compatibility)

async def create_command_client(
    host: str = "localhost",
    port: int = 50053,
    user_id: str = "device_command_client",
) -> DeviceCommandClient:
    """
    Create and connect device command client.

    Args:
        host: MQTT service host
        port: MQTT service port
        user_id: User ID for operations

    Returns:
        DeviceCommandClient: Connected client instance
    """
    client = DeviceCommandClient(host=host, port=port, user_id=user_id)
    await client.connect()
    return client


async def create_mqtt_bus(
    service_name: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> MQTTEventBus:
    """
    Create and connect MQTT event bus.

    Args:
        service_name: Name of the service
        host: Optional MQTT service host
        port: Optional MQTT service port

    Returns:
        MQTTEventBus: Connected event bus instance
    """
    bus = MQTTEventBus(service_name, host=host, port=port)
    await bus.connect()
    return bus
