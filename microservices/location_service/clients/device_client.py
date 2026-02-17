"""
Device Service Client

Client for location_service to interact with device_service.
Used for verifying device ownership and retrieving device information.
"""

import os
import sys
from typing import Any, Dict, List, Optional

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.device_service.client import DeviceServiceClient


class DeviceClient:
    """
    Wrapper client for Device Service calls from Location Service.

    This wrapper provides location-specific convenience methods
    while delegating to the actual DeviceServiceClient.
    """

    def __init__(self, base_url: str = None, consul_registry=None):
        """
        Initialize Device Service client

        Args:
            base_url: Device service base URL (optional, uses service discovery)
            consul_registry: ConsulRegistry instance for service discovery
        """
        self._client = DeviceServiceClient(
            base_url=base_url, consul_registry=consul_registry
        )

    async def close(self):
        """Close HTTP client"""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Location-Specific Device Methods
    # =============================================================================

    async def verify_device_ownership(
        self, device_id: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Verify that a device belongs to a user

        Args:
            device_id: Device ID
            user_id: User ID

        Returns:
            Dict with verification result
        """
        try:
            device = await self._client.get_device(device_id)
            if device and device.get("user_id") == user_id:
                return {"verified": True, "device": device}
            return {"verified": False, "reason": "Device not owned by user"}
        except Exception as e:
            return {"verified": False, "reason": str(e)}

    async def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all devices for a user

        Args:
            user_id: User ID

        Returns:
            List of devices
        """
        try:
            result = await self._client.list_devices(user_id=user_id)
            return result.get("devices", [])
        except Exception:
            return []

    async def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device information

        Args:
            device_id: Device ID

        Returns:
            Device information or None
        """
        try:
            return await self._client.get_device(device_id)
        except Exception:
            return None


__all__ = ["DeviceClient"]
