"""
Storage Service Client for Album Service

HTTP client for synchronous communication with storage_service
Provides methods to fetch file metadata for albums
"""

import httpx
import logging
from typing import Optional, Dict, Any
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class StorageServiceClient:
    """Client for storage_service HTTP API"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize storage service client

        Args:
            config_manager: ConfigManager instance for service discovery
        """
        self.config_manager = config_manager or ConfigManager("album_service")

        # Get storage_service endpoint from Consul or use fallback
        self.base_url = self._get_service_url("storage_service", "http://localhost:8220")

        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "X-Service-Name": "album_service"  # Internal service identifier
            }
        )

        logger.info(f"StorageServiceClient initialized with base_url: {self.base_url}")

    def _get_service_url(self, service_name: str, fallback_url: str) -> str:
        """Get service URL from Consul or use fallback"""
        try:
            if self.config_manager:
                url = self.config_manager.get_service_endpoint(service_name)
                if url:
                    return url
        except Exception as e:
            logger.warning(f"Failed to get {service_name} from Consul: {e}")

        logger.info(f"Using fallback URL for {service_name}: {fallback_url}")
        return fallback_url

    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata including AI labels

        Args:
            file_id: File ID

        Returns:
            File metadata dict or None if not found
        """
        try:
            response = await self.client.get(f"/api/v1/files/{file_id}/metadata")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"File not found: {file_id}")
                return None
            else:
                logger.error(f"Failed to get file metadata {file_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching file metadata {file_id}: {e}")
            return None

    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get basic file information

        Args:
            file_id: File ID

        Returns:
            File info dict or None if not found
        """
        try:
            response = await self.client.get(f"/api/v1/files/{file_id}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"File not found: {file_id}")
                return None
            else:
                logger.error(f"Failed to get file info {file_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching file info {file_id}: {e}")
            return None

    async def get_download_url(self, file_id: str, size: Optional[str] = None) -> Optional[str]:
        """
        Get download URL for a file

        Args:
            file_id: File ID
            size: Optional size variant (thumbnail, hd, original)

        Returns:
            Download URL or None if not found
        """
        try:
            params = {}
            if size:
                params["size"] = size

            # Construct download URL
            url = f"{self.base_url}/api/v1/files/download/{file_id}"
            if params:
                url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

            return url

        except Exception as e:
            logger.error(f"Error getting download URL {file_id}: {e}")
            return None

    async def check_file_exists(self, file_id: str) -> bool:
        """
        Check if file exists

        Args:
            file_id: File ID

        Returns:
            True if file exists, False otherwise
        """
        try:
            response = await self.client.head(f"/api/v1/files/{file_id}")
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error checking file existence {file_id}: {e}")
            return False

    async def get_files_batch(self, file_ids: list) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for multiple files at once

        Args:
            file_ids: List of file IDs

        Returns:
            Dict mapping file_id to metadata
        """
        try:
            response = await self.client.post(
                "/api/v1/files/batch/metadata",
                json={"file_ids": file_ids}
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get batch file metadata: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching batch file metadata: {e}")
            return {}

    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
        logger.info("StorageServiceClient closed")
