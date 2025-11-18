"""
Storage Service Client for Order Service

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

        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"StorageClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_storage_usage(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's storage usage

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
                logger.warning(f"Storage usage for user {user_id} not found")
                return None
            logger.error(f"Failed to get storage usage: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting storage usage: {e}")
            return None

    async def validate_quota(
        self,
        user_id: str,
        additional_size: int
    ) -> bool:
        """
        Validate if user has enough quota for additional storage

        Args:
            user_id: User ID
            additional_size: Additional size in bytes

        Returns:
            True if user has enough quota
        """
        try:
            usage = await self.get_storage_usage(user_id)
            if not usage:
                return False

            used = usage.get('used_bytes', 0)
            quota = usage.get('quota_bytes', 0)

            return (used + additional_size) <= quota

        except Exception as e:
            logger.error(f"Error validating quota: {e}")
            return False

    async def get_storage_quota(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's storage quota

        Args:
            user_id: User ID

        Returns:
            Storage quota information
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/storage/quota/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get storage quota: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting storage quota: {e}")
            return None

    async def update_quota(
        self,
        user_id: str,
        new_quota_bytes: int
    ) -> bool:
        """
        Update user's storage quota

        Args:
            user_id: User ID
            new_quota_bytes: New quota in bytes

        Returns:
            True if successful
        """
        try:
            payload = {
                "user_id": user_id,
                "quota_bytes": new_quota_bytes
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/storage/quota/update",
                json=payload
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update quota: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error updating quota: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if storage service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
