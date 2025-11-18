"""
Device Service Client for OTA Service

HTTP client for synchronous communication with device_service
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DeviceClient:
    """Client for device_service"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize Device Service client

        Args:
            base_url: Device service base URL
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("device_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8202"

        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"DeviceClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device information

        Args:
            device_id: Device ID

        Returns:
            Device data if found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/{device_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Device {device_id} not found")
                return None
            logger.error(f"Failed to get device: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting device: {e}")
            return None

    async def get_device_firmware_version(self, device_id: str) -> Optional[str]:
        """
        Get device's current firmware version

        Args:
            device_id: Device ID

        Returns:
            Current firmware version string
        """
        try:
            device = await self.get_device(device_id)
            if device:
                # Assuming device has a firmware_version or current_version field
                return device.get('firmware_version') or device.get('current_version')
            return None

        except Exception as e:
            logger.error(f"Error getting device firmware version: {e}")
            return None

    async def check_firmware_compatibility(
        self,
        device_id: str,
        device_model: str,
        min_hardware_version: Optional[str] = None
    ) -> bool:
        """
        Check if firmware is compatible with device

        Args:
            device_id: Device ID
            device_model: Target device model
            min_hardware_version: Minimum hardware version required

        Returns:
            True if compatible
        """
        try:
            device = await self.get_device(device_id)
            if not device:
                logger.warning(f"Device {device_id} not found for compatibility check")
                return False

            # Check device model match
            if device.get('model') != device_model:
                logger.warning(
                    f"Device model mismatch: device has {device.get('model')}, "
                    f"firmware requires {device_model}"
                )
                return False

            # Check hardware version if specified
            if min_hardware_version:
                device_hw_version = device.get('hardware_version')
                if not device_hw_version:
                    logger.warning(f"Device {device_id} has no hardware_version")
                    return True  # Allow if hw version not specified

                # Simple string comparison (can be enhanced with semver)
                if device_hw_version < min_hardware_version:
                    logger.warning(
                        f"Hardware version too old: device has {device_hw_version}, "
                        f"requires {min_hardware_version}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking firmware compatibility: {e}")
            return False

    async def update_device_firmware_version(
        self,
        device_id: str,
        firmware_version: str
    ) -> bool:
        """
        Update device's firmware version record

        Args:
            device_id: Device ID
            firmware_version: New firmware version

        Returns:
            True if successful
        """
        try:
            payload = {
                "firmware_version": firmware_version
            }

            response = await self.client.patch(
                f"{self.base_url}/api/v1/devices/{device_id}",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Updated device {device_id} firmware version to {firmware_version}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update device firmware version: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error updating device firmware version: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if device service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
