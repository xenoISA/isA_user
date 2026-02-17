"""
Device Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

# Import only models (no I/O dependencies)
from .models import (
    DeviceResponse,
    DeviceGroupResponse,
    DeviceStatus,
)


# Custom exceptions - defined here to avoid importing repository
class DeviceNotFoundError(Exception):
    """Device not found"""
    pass


class DeviceAlreadyExistsError(Exception):
    """Device already exists"""
    pass


class DeviceGroupNotFoundError(Exception):
    """Device group not found"""
    pass


@runtime_checkable
class DeviceRepositoryProtocol(Protocol):
    """
    Interface for Device Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create_device(self, device_data: Dict[str, Any]) -> Optional[DeviceResponse]:
        """Create a new device"""
        ...

    async def get_device_by_id(self, device_id: str) -> Optional[DeviceResponse]:
        """Get device by ID"""
        ...

    async def list_user_devices(
        self,
        user_id: str,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DeviceResponse]:
        """List devices for a user"""
        ...

    async def update_device(
        self,
        device_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update device information"""
        ...

    async def update_device_status(
        self,
        device_id: str,
        status: DeviceStatus,
        last_seen: datetime
    ) -> bool:
        """Update device status"""
        ...

    async def delete_device(self, device_id: str) -> bool:
        """Delete/decommission a device"""
        ...

    async def create_device_group(self, group_data: Dict[str, Any]) -> Optional[DeviceGroupResponse]:
        """Create a device group"""
        ...

    async def get_device_group_by_id(self, group_id: str) -> Optional[DeviceGroupResponse]:
        """Get device group by ID"""
        ...

    async def create_device_command(self, command_data: Dict[str, Any]) -> bool:
        """Create a device command"""
        ...

    async def update_command_status(
        self,
        command_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update command status"""
        ...

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class TelemetryClientProtocol(Protocol):
    """Interface for Telemetry Service Client"""

    async def get_device_stats(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device statistics from telemetry service"""
        ...


@runtime_checkable
class MQTTCommandClientProtocol(Protocol):
    """Interface for MQTT Command Client"""

    async def connect(self) -> None:
        """Connect to MQTT broker"""
        ...

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker"""
        ...

    async def send_device_command(
        self,
        device_id: str,
        command: str,
        parameters: Dict[str, Any],
        timeout: int = 30,
        priority: int = 1,
        require_ack: bool = True
    ) -> Optional[str]:
        """Send command to device via MQTT"""
        ...

    def is_connected(self) -> bool:
        """Check if MQTT client is connected"""
        ...
