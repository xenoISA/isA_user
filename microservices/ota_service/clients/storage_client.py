"""
Storage Service Client for OTA Service

HTTP client for synchronous communication with storage_service
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class StorageClient:
    """Client for storage_service"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize Storage Service client

        Args:
            base_url: Storage service base URL
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("storage_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8208"

        self.client = httpx.AsyncClient(timeout=30.0)  # Longer timeout for file uploads
        logger.info(f"StorageClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def upload_firmware(
        self,
        firmware_id: str,
        file_content: bytes,
        filename: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload firmware binary to storage service (MinIO/S3)

        Args:
            firmware_id: Unique firmware ID
            file_content: Binary file content
            filename: Original filename
            user_id: User ID
            metadata: Additional metadata

        Returns:
            Upload result with download_url
        """
        try:
            # Prepare multipart form data
            files = {
                'file': (filename, file_content, 'application/octet-stream')
            }

            data = {
                'firmware_id': firmware_id,
                'user_id': user_id,
                'folder': 'firmware',
                'metadata': str(metadata or {})
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/storage/upload",
                files=files,
                data=data
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Firmware {firmware_id} uploaded successfully")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to upload firmware: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error uploading firmware: {e}")
            return None

    async def get_firmware_download_url(
        self,
        firmware_id: str,
        expiry_seconds: int = 3600
    ) -> Optional[str]:
        """
        Get presigned download URL for firmware

        Args:
            firmware_id: Firmware ID
            expiry_seconds: URL expiry time in seconds

        Returns:
            Presigned download URL
        """
        try:
            params = {
                'firmware_id': firmware_id,
                'expiry': expiry_seconds
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/storage/firmware/{firmware_id}/download-url",
                params=params
            )
            response.raise_for_status()

            result = response.json()
            return result.get('download_url')

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Firmware {firmware_id} not found in storage")
                return None
            logger.error(f"Failed to get download URL: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
            return None

    async def delete_firmware(self, firmware_id: str) -> bool:
        """
        Delete firmware from storage

        Args:
            firmware_id: Firmware ID

        Returns:
            True if successful
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/storage/firmware/{firmware_id}"
            )
            response.raise_for_status()
            logger.info(f"Firmware {firmware_id} deleted from storage")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete firmware: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting firmware: {e}")
            return False

    async def get_storage_usage(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get storage usage for user

        Args:
            user_id: User ID

        Returns:
            Storage usage data
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/storage/usage/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get storage usage: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting storage usage: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if storage service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
