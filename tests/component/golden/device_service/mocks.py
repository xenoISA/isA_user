"""
Mock implementations for Device Service component testing

These mocks implement the protocols defined in device_service.protocols
without requiring actual I/O dependencies.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from microservices.device_service.models import (
    DeviceResponse,
    DeviceGroupResponse,
    DeviceStatus,
    DeviceType,
    ConnectivityType,
)


class MockDeviceRepository:
    """Mock implementation of DeviceRepositoryProtocol"""

    def __init__(self):
        self.devices: Dict[str, DeviceResponse] = {}
        self.device_groups: Dict[str, DeviceGroupResponse] = {}
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.call_count = {
            "create_device": 0,
            "get_device_by_id": 0,
            "list_user_devices": 0,
            "update_device": 0,
            "update_device_status": 0,
            "delete_device": 0,
            "create_device_group": 0,
            "get_device_group_by_id": 0,
            "create_device_command": 0,
            "update_command_status": 0,
            "check_connection": 0,
        }

    async def create_device(self, device_data: Dict[str, Any]) -> Optional[DeviceResponse]:
        """Create a new device"""
        self.call_count["create_device"] += 1

        device_id = device_data.get("device_id", f"dev_{len(self.devices) + 1}")
        now = datetime.now(timezone.utc)

        device = DeviceResponse(
            device_id=device_id,
            user_id=device_data["user_id"],
            organization_id=device_data.get("organization_id"),
            device_name=device_data["device_name"],
            device_type=device_data.get("device_type", DeviceType.SENSOR),
            manufacturer=device_data.get("manufacturer", "Unknown"),
            model=device_data.get("model", "Unknown"),
            serial_number=device_data.get("serial_number", ""),
            firmware_version=device_data.get("firmware_version", "1.0.0"),
            hardware_version=device_data.get("hardware_version", "1.0"),
            mac_address=device_data.get("mac_address"),
            connectivity_type=device_data.get("connectivity_type", ConnectivityType.WIFI),
            security_level=device_data.get("security_level", "standard"),
            status=DeviceStatus.PENDING,
            location=device_data.get("location", {}),
            metadata=device_data.get("metadata", {}),
            group_id=device_data.get("group_id"),
            tags=device_data.get("tags", []),
            last_seen=now,
            registered_at=now,
            updated_at=now,
        )

        self.devices[device_id] = device
        return device

    async def get_device_by_id(self, device_id: str) -> Optional[DeviceResponse]:
        """Get device by ID"""
        self.call_count["get_device_by_id"] += 1
        return self.devices.get(device_id)

    async def list_user_devices(
        self,
        user_id: str,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DeviceResponse]:
        """List devices for a user"""
        self.call_count["list_user_devices"] += 1

        devices = [d for d in self.devices.values() if d.user_id == user_id]

        if device_type:
            devices = [d for d in devices if d.device_type == device_type]

        if status:
            devices = [d for d in devices if d.status == status]

        return devices[offset:offset + limit]

    async def update_device(
        self,
        device_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update device information"""
        self.call_count["update_device"] += 1

        if device_id not in self.devices:
            return False

        device = self.devices[device_id]

        # Update fields
        for key, value in update_data.items():
            if hasattr(device, key):
                setattr(device, key, value)

        device.updated_at = datetime.now(timezone.utc)
        return True

    async def update_device_status(
        self,
        device_id: str,
        status: DeviceStatus,
        last_seen: datetime
    ) -> bool:
        """Update device status"""
        self.call_count["update_device_status"] += 1

        if device_id not in self.devices:
            return False

        device = self.devices[device_id]
        device.status = status
        device.last_seen = last_seen
        device.updated_at = datetime.now(timezone.utc)
        return True

    async def delete_device(self, device_id: str) -> bool:
        """Delete/decommission a device"""
        self.call_count["delete_device"] += 1

        if device_id in self.devices:
            del self.devices[device_id]
            return True
        return False

    async def create_device_group(self, group_data: Dict[str, Any]) -> Optional[DeviceGroupResponse]:
        """Create a device group"""
        self.call_count["create_device_group"] += 1

        group_id = group_data.get("group_id", f"grp_{len(self.device_groups) + 1}")
        now = datetime.now(timezone.utc)

        group = DeviceGroupResponse(
            group_id=group_id,
            user_id=group_data["user_id"],
            organization_id=group_data.get("organization_id"),
            group_name=group_data["group_name"],
            description=group_data.get("description"),
            device_ids=group_data.get("device_ids", []),
            parent_group_id=group_data.get("parent_group_id"),
            device_count=len(group_data.get("device_ids", [])),
            tags=group_data.get("tags", []),
            metadata=group_data.get("metadata", {}),
            created_at=now,
            updated_at=now,
        )

        self.device_groups[group_id] = group
        return group

    async def get_device_group_by_id(self, group_id: str) -> Optional[DeviceGroupResponse]:
        """Get device group by ID"""
        self.call_count["get_device_group_by_id"] += 1
        return self.device_groups.get(group_id)

    async def create_device_command(self, command_data: Dict[str, Any]) -> bool:
        """Create a device command"""
        self.call_count["create_device_command"] += 1

        command_id = command_data.get("command_id", f"cmd_{len(self.commands) + 1}")
        self.commands[command_id] = command_data
        return True

    async def update_command_status(
        self,
        command_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update command status"""
        self.call_count["update_command_status"] += 1

        if command_id not in self.commands:
            return False

        self.commands[command_id]["status"] = status
        if result:
            self.commands[command_id]["result"] = result
        if error_message:
            self.commands[command_id]["error_message"] = error_message

        return True

    async def check_connection(self) -> bool:
        """Check database connection"""
        self.call_count["check_connection"] += 1
        return True


class MockEventBus:
    """Mock implementation of EventBusProtocol"""

    def __init__(self):
        self.published_events: List[Any] = []
        self.call_count = {"publish_event": 0}

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        self.call_count["publish_event"] += 1
        self.published_events.append(event)


class MockTelemetryClient:
    """Mock implementation of TelemetryClientProtocol"""

    def __init__(self):
        self.device_stats: Dict[str, Dict[str, Any]] = {}
        self.call_count = {"get_device_stats": 0}

    async def get_device_stats(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device statistics from telemetry service"""
        self.call_count["get_device_stats"] += 1
        return self.device_stats.get(device_id, {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "temperature": 42.5,
            "uptime_seconds": 86400,
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        })

    def set_device_stats(self, device_id: str, stats: Dict[str, Any]):
        """Set mock stats for a device"""
        self.device_stats[device_id] = stats


class MockMQTTCommandClient:
    """Mock implementation of MQTTCommandClientProtocol"""

    def __init__(self):
        self.connected = False
        self.sent_commands: List[Dict[str, Any]] = []
        self.call_count = {
            "connect": 0,
            "disconnect": 0,
            "send_device_command": 0,
            "is_connected": 0,
        }

    async def connect(self) -> None:
        """Connect to MQTT broker"""
        self.call_count["connect"] += 1
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker"""
        self.call_count["disconnect"] += 1
        self.connected = False

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
        self.call_count["send_device_command"] += 1

        command_id = f"cmd_{len(self.sent_commands) + 1}"
        self.sent_commands.append({
            "command_id": command_id,
            "device_id": device_id,
            "command": command,
            "parameters": parameters,
            "timeout": timeout,
            "priority": priority,
            "require_ack": require_ack,
        })

        return command_id

    def is_connected(self) -> bool:
        """Check if MQTT client is connected"""
        self.call_count["is_connected"] += 1
        return self.connected
