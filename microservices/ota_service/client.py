"""
OTA Service Client

Client library for other microservices to interact with OTA service
"""

import httpx
from core.config_manager import ConfigManager
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class OTAServiceClient:
    """OTA Service HTTP client"""

    def __init__(self, base_url: str = None, config: Optional[ConfigManager] = None):
        """
        Initialize OTA Service client

        Args:
            base_url: OTA service base URL, defaults to service discovery
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via ConfigManager
            if config is None:
                config = ConfigManager("ota_service_client")

            try:
                host, port = config.discover_service(
                    service_name='ota_service',
                    default_host='localhost',
                    default_port=8221,
                    env_host_key='OTA_SERVICE_HOST',
                    env_port_key='OTA_SERVICE_PORT'
                )
                self.base_url = f"http://{host}:{port}"
                logger.info(f"OTA service discovered at {self.base_url}")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8221"

        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Firmware Management
    # =============================================================================

    async def upload_firmware(
        self,
        firmware_file: bytes,
        filename: str,
        version: str,
        device_type: str,
        user_id: str,
        description: Optional[str] = None,
        release_notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload firmware file

        Args:
            firmware_file: Firmware binary content
            filename: Firmware filename
            version: Firmware version
            device_type: Target device type
            user_id: User ID
            description: Firmware description (optional)
            release_notes: Release notes (optional)
            metadata: Additional metadata (optional)

        Returns:
            Uploaded firmware info

        Example:
            >>> client = OTAServiceClient()
            >>> firmware = await client.upload_firmware(
            ...     firmware_file=binary_data,
            ...     filename="firmware_v1.2.3.bin",
            ...     version="1.2.3",
            ...     device_type="smart_frame",
            ...     user_id="user123"
            ... )
        """
        try:
            from io import BytesIO

            files = {"file": (filename, BytesIO(firmware_file), "application/octet-stream")}
            data = {
                "version": version,
                "device_type": device_type
            }

            if description:
                data["description"] = description
            if release_notes:
                data["release_notes"] = release_notes
            if metadata:
                import json
                data["metadata"] = json.dumps(metadata)

            response = await self.client.post(
                f"{self.base_url}/api/v1/firmware",
                files=files,
                data=data,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to upload firmware: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error uploading firmware: {e}")
            return None

    async def get_firmware(
        self,
        firmware_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get firmware details

        Args:
            firmware_id: Firmware ID
            user_id: User ID

        Returns:
            Firmware details

        Example:
            >>> firmware = await client.get_firmware("fw123", "user456")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/firmware/{firmware_id}",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get firmware: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting firmware: {e}")
            return None

    async def list_firmware(
        self,
        user_id: str,
        device_type: Optional[str] = None,
        version: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[List[Dict[str, Any]]]:
        """
        List firmware

        Args:
            user_id: User ID
            device_type: Filter by device type (optional)
            version: Filter by version (optional)
            limit: Result limit (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of firmware

        Example:
            >>> firmwares = await client.list_firmware("user123", device_type="smart_frame")
        """
        try:
            params = {"limit": limit, "offset": offset}
            if device_type:
                params["device_type"] = device_type
            if version:
                params["version"] = version

            response = await self.client.get(
                f"{self.base_url}/api/v1/firmware",
                params=params,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list firmware: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing firmware: {e}")
            return None

    async def delete_firmware(
        self,
        firmware_id: str,
        user_id: str
    ) -> bool:
        """
        Delete firmware

        Args:
            firmware_id: Firmware ID
            user_id: User ID

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_firmware("fw123", "user456")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/firmware/{firmware_id}",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete firmware: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting firmware: {e}")
            return False

    # =============================================================================
    # Update Campaigns
    # =============================================================================

    async def create_campaign(
        self,
        campaign_name: str,
        firmware_id: str,
        user_id: str,
        device_filters: Optional[Dict[str, Any]] = None,
        deployment_strategy: str = "progressive",
        schedule_time: Optional[str] = None,
        target_devices: Optional[List[str]] = None,
        auto_approve: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Create update campaign

        Args:
            campaign_name: Campaign name
            firmware_id: Target firmware ID
            user_id: User ID
            device_filters: Device filter criteria (optional)
            deployment_strategy: Deployment strategy (progressive/immediate/scheduled)
            schedule_time: Schedule time for deployment (optional)
            target_devices: Specific target device IDs (optional)
            auto_approve: Auto-approve campaign (default: False)

        Returns:
            Created campaign

        Example:
            >>> campaign = await client.create_campaign(
            ...     campaign_name="Smart Frame Update v1.2.3",
            ...     firmware_id="fw123",
            ...     user_id="user456",
            ...     deployment_strategy="progressive"
            ... )
        """
        try:
            payload = {
                "campaign_name": campaign_name,
                "firmware_id": firmware_id,
                "deployment_strategy": deployment_strategy,
                "auto_approve": auto_approve
            }

            if device_filters:
                payload["device_filters"] = device_filters
            if schedule_time:
                payload["schedule_time"] = schedule_time
            if target_devices:
                payload["target_devices"] = target_devices

            response = await self.client.post(
                f"{self.base_url}/api/v1/campaigns",
                json=payload,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create campaign: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            return None

    async def get_campaign(
        self,
        campaign_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get campaign details

        Args:
            campaign_id: Campaign ID
            user_id: User ID

        Returns:
            Campaign details

        Example:
            >>> campaign = await client.get_campaign("camp123", "user456")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/campaigns/{campaign_id}",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get campaign: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting campaign: {e}")
            return None

    async def start_campaign(
        self,
        campaign_id: str,
        user_id: str
    ) -> bool:
        """
        Start update campaign

        Args:
            campaign_id: Campaign ID
            user_id: User ID

        Returns:
            True if successful

        Example:
            >>> success = await client.start_campaign("camp123", "user456")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/campaigns/{campaign_id}/start",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to start campaign: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error starting campaign: {e}")
            return False

    async def pause_campaign(
        self,
        campaign_id: str,
        user_id: str
    ) -> bool:
        """
        Pause update campaign

        Args:
            campaign_id: Campaign ID
            user_id: User ID

        Returns:
            True if successful

        Example:
            >>> success = await client.pause_campaign("camp123", "user456")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/campaigns/{campaign_id}/pause",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to pause campaign: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error pausing campaign: {e}")
            return False

    async def cancel_campaign(
        self,
        campaign_id: str,
        user_id: str
    ) -> bool:
        """
        Cancel update campaign

        Args:
            campaign_id: Campaign ID
            user_id: User ID

        Returns:
            True if successful

        Example:
            >>> success = await client.cancel_campaign("camp123", "user456")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/campaigns/{campaign_id}/cancel",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cancel campaign: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error canceling campaign: {e}")
            return False

    # =============================================================================
    # Device Updates
    # =============================================================================

    async def update_device(
        self,
        device_id: str,
        firmware_id: str,
        user_id: str,
        force: bool = False,
        schedule_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Initiate device update

        Args:
            device_id: Device ID
            firmware_id: Target firmware ID
            user_id: User ID
            force: Force immediate update (default: False)
            schedule_time: Schedule update time (optional)

        Returns:
            Update details

        Example:
            >>> update = await client.update_device(
            ...     device_id="device123",
            ...     firmware_id="fw456",
            ...     user_id="user789"
            ... )
        """
        try:
            payload = {
                "firmware_id": firmware_id,
                "force": force
            }

            if schedule_time:
                payload["schedule_time"] = schedule_time

            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/update",
                json=payload,
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

    async def get_update_status(
        self,
        update_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get update status

        Args:
            update_id: Update ID
            user_id: User ID

        Returns:
            Update status

        Example:
            >>> status = await client.get_update_status("upd123", "user456")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/updates/{update_id}",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get update status: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting update status: {e}")
            return None

    async def get_device_update_history(
        self,
        device_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get device update history

        Args:
            device_id: Device ID
            user_id: User ID
            limit: Result limit (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
            Update history

        Example:
            >>> history = await client.get_device_update_history("device123", "user456")
        """
        try:
            params = {"limit": limit, "offset": offset}

            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/{device_id}/updates",
                params=params,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get device update history: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting device update history: {e}")
            return None

    async def rollback_device(
        self,
        device_id: str,
        user_id: str,
        target_version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Rollback device firmware

        Args:
            device_id: Device ID
            user_id: User ID
            target_version: Target version to rollback to (optional, defaults to previous)

        Returns:
            Rollback result

        Example:
            >>> result = await client.rollback_device("device123", "user456")
        """
        try:
            payload = {}
            if target_version:
                payload["target_version"] = target_version

            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/rollback",
                json=payload,
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to rollback device: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error rolling back device: {e}")
            return None

    # =============================================================================
    # Statistics
    # =============================================================================

    async def get_update_stats(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get update statistics

        Args:
            user_id: User ID

        Returns:
            Update statistics

        Example:
            >>> stats = await client.get_update_stats("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/stats",
                headers={"X-Internal-Call": "true", "X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get update stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting update stats: {e}")
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


__all__ = ["OTAServiceClient"]
