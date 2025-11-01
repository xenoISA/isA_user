"""
Device Service Client

Client library for other microservices to interact with device service
"""

import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class DeviceServiceClient:
    """Device Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Device Service client

        Args:
            base_url: Device service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("device_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8220"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Device Registration & Management
    # =============================================================================

    async def register_device(
        self,
        device_name: str,
        device_type: str,
        user_id: str,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        serial_number: Optional[str] = None,
        firmware_version: Optional[str] = None,
        hardware_version: Optional[str] = None,
        mac_address: Optional[str] = None,
        connectivity_type: Optional[str] = None,
        security_level: str = "standard",
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Register new device

        Args:
            device_name: Device name
            device_type: Device type (sensor, actuator, gateway, smart_frame, etc.)
            user_id: Owner user ID
            manufacturer: Device manufacturer (optional)
            model: Device model (optional)
            serial_number: Device serial number (optional)
            firmware_version: Firmware version (optional)
            hardware_version: Hardware version (optional)
            mac_address: MAC address (optional)
            connectivity_type: Connectivity type (wifi, cellular, lora, ethernet, etc.)
            security_level: Security level (standard, high, critical)
            organization_id: Organization ID (optional)
            metadata: Additional metadata (optional)
            tags: Device tags (optional)

        Returns:
            Registered device

        Example:
            >>> client = DeviceServiceClient()
            >>> device = await client.register_device(
            ...     device_name="Smart Frame 001",
            ...     device_type="smart_frame",
            ...     user_id="user123",
            ...     manufacturer="isA Corp",
            ...     model="SF-2024"
            ... )
        """
        try:
            payload = {
                "device_name": device_name,
                "device_type": device_type,
                "security_level": security_level
            }

            if manufacturer:
                payload["manufacturer"] = manufacturer
            if model:
                payload["model"] = model
            if serial_number:
                payload["serial_number"] = serial_number
            if firmware_version:
                payload["firmware_version"] = firmware_version
            if hardware_version:
                payload["hardware_version"] = hardware_version
            if mac_address:
                payload["mac_address"] = mac_address
            if connectivity_type:
                payload["connectivity_type"] = connectivity_type
            if organization_id:
                payload["organization_id"] = organization_id
            if metadata:
                payload["metadata"] = metadata
            if tags:
                payload["tags"] = tags

            response = await self.client.post(
                f"{self.base_url}/api/v1/devices",
                json=payload,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to register device: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return None

    async def get_device(
        self,
        device_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get device details

        Args:
            device_id: Device ID
            user_id: User ID

        Returns:
            Device details

        Example:
            >>> device = await client.get_device("device123", "user456")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/{device_id}",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get device: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting device: {e}")
            return None

    async def update_device(
        self,
        device_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update device information

        Args:
            device_id: Device ID
            user_id: User ID
            updates: Update data

        Returns:
            Updated device

        Example:
            >>> updated = await client.update_device(
            ...     device_id="device123",
            ...     user_id="user456",
            ...     updates={"status": "active", "firmware_version": "2.0.0"}
            ... )
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/devices/{device_id}",
                json=updates,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update device: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating device: {e}")
            return None

    async def decommission_device(
        self,
        device_id: str,
        user_id: str
    ) -> bool:
        """
        Decommission device

        Args:
            device_id: Device ID
            user_id: User ID

        Returns:
            True if successful

        Example:
            >>> success = await client.decommission_device("device123", "user456")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/devices/{device_id}",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to decommission device: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error decommissioning device: {e}")
            return False

    async def list_devices(
        self,
        user_id: str,
        status: Optional[str] = None,
        device_type: Optional[str] = None,
        connectivity: Optional[str] = None,
        group_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        List user devices

        Args:
            user_id: User ID
            status: Filter by status (optional)
            device_type: Filter by device type (optional)
            connectivity: Filter by connectivity type (optional)
            group_id: Filter by group ID (optional)
            limit: Result limit (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            Device list response

        Example:
            >>> devices = await client.list_devices("user123", device_type="smart_frame")
        """
        try:
            params = {"limit": limit, "offset": offset}
            if status:
                params["status"] = status
            if device_type:
                params["device_type"] = device_type
            if connectivity:
                params["connectivity"] = connectivity
            if group_id:
                params["group_id"] = group_id

            response = await self.client.get(
                f"{self.base_url}/api/v1/devices",
                params=params,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list devices: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return None

    # =============================================================================
    # Device Authentication
    # =============================================================================

    async def authenticate_device(
        self,
        device_id: str,
        device_secret: str
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate device and get access token

        Args:
            device_id: Device ID
            device_secret: Device secret/credential

        Returns:
            Authentication response with access token

        Example:
            >>> auth = await client.authenticate_device("device123", "secret_key")
            >>> access_token = auth["access_token"]
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/auth",
                json={
                    "device_id": device_id,
                    "device_secret": device_secret
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to authenticate device: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error authenticating device: {e}")
            return None

    # =============================================================================
    # Device Commands
    # =============================================================================

    async def send_command(
        self,
        device_id: str,
        user_id: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        priority: int = 5,
        require_ack: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Send command to device

        Args:
            device_id: Device ID
            user_id: User ID sending command
            command: Command name
            parameters: Command parameters (optional)
            timeout: Command timeout in seconds (default: 30)
            priority: Command priority 1-10 (default: 5)
            require_ack: Require acknowledgment (default: False)

        Returns:
            Command result

        Example:
            >>> result = await client.send_command(
            ...     device_id="device123",
            ...     user_id="user456",
            ...     command="display_control",
            ...     parameters={"action": "next_photo"}
            ... )
        """
        try:
            payload = {
                "command": command,
                "parameters": parameters or {},
                "timeout": timeout,
                "priority": priority,
                "require_ack": require_ack
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/commands",
                json=payload,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send command: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None

    async def bulk_send_commands(
        self,
        device_ids: List[str],
        user_id: str,
        command_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        priority: int = 5,
        require_ack: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Send command to multiple devices

        Args:
            device_ids: List of device IDs
            user_id: User ID sending commands
            command_name: Command name
            parameters: Command parameters (optional)
            timeout: Command timeout in seconds (default: 30)
            priority: Command priority 1-10 (default: 5)
            require_ack: Require acknowledgment (default: False)

        Returns:
            Bulk command results

        Example:
            >>> results = await client.bulk_send_commands(
            ...     device_ids=["device1", "device2"],
            ...     user_id="user123",
            ...     command_name="sync_content"
            ... )
        """
        try:
            payload = {
                "device_ids": device_ids,
                "command_name": command_name,
                "parameters": parameters or {},
                "timeout": timeout,
                "priority": priority,
                "require_ack": require_ack
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/bulk/commands",
                json=payload,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send bulk commands: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sending bulk commands: {e}")
            return None

    # =============================================================================
    # Device Health & Stats
    # =============================================================================

    async def get_device_health(
        self,
        device_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get device health status

        Args:
            device_id: Device ID
            user_id: User ID

        Returns:
            Device health status

        Example:
            >>> health = await client.get_device_health("device123", "user456")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/{device_id}/health",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get device health: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting device health: {e}")
            return None

    async def get_device_stats(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user device statistics

        Args:
            user_id: User ID

        Returns:
            Device statistics

        Example:
            >>> stats = await client.get_device_stats("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/stats",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get device stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting device stats: {e}")
            return None

    # =============================================================================
    # Device Groups
    # =============================================================================

    async def create_device_group(
        self,
        group_name: str,
        user_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create device group

        Args:
            group_name: Group name
            user_id: Owner user ID
            description: Group description (optional)
            tags: Group tags (optional)

        Returns:
            Created device group

        Example:
            >>> group = await client.create_device_group(
            ...     group_name="Living Room Devices",
            ...     user_id="user123"
            ... )
        """
        try:
            payload = {
                "group_name": group_name
            }

            if description:
                payload["description"] = description
            if tags:
                payload["tags"] = tags

            response = await self.client.post(
                f"{self.base_url}/api/v1/groups",
                json=payload,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create device group: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating device group: {e}")
            return None

    async def add_device_to_group(
        self,
        group_id: str,
        device_id: str,
        user_id: str
    ) -> bool:
        """
        Add device to group

        Args:
            group_id: Group ID
            device_id: Device ID
            user_id: User ID

        Returns:
            True if successful

        Example:
            >>> success = await client.add_device_to_group("group123", "device456", "user789")
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/groups/{group_id}/devices/{device_id}",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add device to group: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error adding device to group: {e}")
            return False

    # =============================================================================
    # Smart Frame Specific Operations
    # =============================================================================

    async def list_smart_frames(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        List smart frames with family sharing permissions

        Args:
            user_id: User ID

        Returns:
            Smart frame list

        Example:
            >>> frames = await client.list_smart_frames("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/frames",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list smart frames: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing smart frames: {e}")
            return None

    async def control_frame_display(
        self,
        frame_id: str,
        user_id: str,
        command_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Control smart frame display

        Args:
            frame_id: Frame device ID
            user_id: User ID
            command_data: Display control data

        Returns:
            Command result

        Example:
            >>> result = await client.control_frame_display(
            ...     frame_id="frame123",
            ...     user_id="user456",
            ...     command_data={"action": "next_photo"}
            ... )
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/frames/{frame_id}/display",
                json=command_data,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to control frame display: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error controlling frame display: {e}")
            return None

    async def sync_frame_content(
        self,
        frame_id: str,
        user_id: str,
        album_ids: List[str],
        sync_type: str = "incremental",
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Sync content to smart frame

        Args:
            frame_id: Frame device ID
            user_id: User ID
            album_ids: List of album IDs to sync
            sync_type: Sync type (incremental/full)
            force: Force full sync

        Returns:
            Sync result

        Example:
            >>> result = await client.sync_frame_content(
            ...     frame_id="frame123",
            ...     user_id="user456",
            ...     album_ids=["album1", "album2"]
            ... )
        """
        try:
            payload = {
                "album_ids": album_ids,
                "sync_type": sync_type,
                "force": force
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/frames/{frame_id}/sync",
                json=payload,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to sync frame content: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error syncing frame content: {e}")
            return None

    async def update_frame_config(
        self,
        frame_id: str,
        user_id: str,
        config_updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update smart frame configuration

        Args:
            frame_id: Frame device ID
            user_id: User ID
            config_updates: Configuration updates

        Returns:
            Update result

        Example:
            >>> result = await client.update_frame_config(
            ...     frame_id="frame123",
            ...     user_id="user456",
            ...     config_updates={"brightness": 80, "rotation_interval": 10}
            ... )
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/devices/frames/{frame_id}/config",
                json=config_updates,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update frame config: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating frame config: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["DeviceServiceClient"]
