"""
Media Service Client for Album Service

HTTP client for synchronous communication with media_service
Provides methods to interact with photo versions and caching
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class MediaServiceClient:
    """Client for media_service HTTP API"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize media service client

        Args:
            config_manager: ConfigManager instance for service discovery
        """
        self.config_manager = config_manager or ConfigManager("album_service")

        # Get media_service endpoint from Consul or use fallback
        self.base_url = self._get_service_url("media_service", "http://localhost:8222")

        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "X-Service-Name": "album_service"  # Internal service identifier
            }
        )

        logger.info(f"MediaServiceClient initialized with base_url: {self.base_url}")

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

    async def get_photo_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get photo metadata including versions

        Args:
            file_id: File ID

        Returns:
            Photo metadata dict or None if not found
        """
        try:
            response = await self.client.get(f"/api/v1/photos/{file_id}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Photo not found: {file_id}")
                return None
            else:
                logger.error(f"Failed to get photo metadata {file_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching photo metadata {file_id}: {e}")
            return None

    async def trigger_photo_cache(self, file_id: str, frame_id: str) -> bool:
        """
        Trigger photo caching for a specific frame

        Args:
            file_id: File ID
            frame_id: Frame/device ID

        Returns:
            True if cache triggered successfully
        """
        try:
            response = await self.client.post(
                f"/api/v1/photos/{file_id}/cache",
                json={"frame_id": frame_id}
            )

            if response.status_code in [200, 201, 202]:
                logger.info(f"Triggered cache for photo {file_id} on frame {frame_id}")
                return True
            else:
                logger.error(f"Failed to trigger cache: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error triggering photo cache: {e}")
            return False

    async def get_photo_versions(self, file_id: str) -> List[Dict[str, Any]]:
        """
        Get available versions of a photo (thumbnail, hd, original)

        Args:
            file_id: File ID

        Returns:
            List of version dicts
        """
        try:
            metadata = await self.get_photo_metadata(file_id)

            if metadata and "versions" in metadata:
                return metadata["versions"]

            return []

        except Exception as e:
            logger.error(f"Error fetching photo versions {file_id}: {e}")
            return []

    async def get_cached_photos_for_frame(self, frame_id: str) -> List[str]:
        """
        Get list of cached photo IDs for a specific frame

        Args:
            frame_id: Frame/device ID

        Returns:
            List of file IDs
        """
        try:
            response = await self.client.get(f"/api/v1/cache/frame/{frame_id}")

            if response.status_code == 200:
                data = response.json()
                return data.get("cached_photos", [])
            else:
                logger.error(f"Failed to get cached photos for frame {frame_id}: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching cached photos: {e}")
            return []

    async def create_photo_playlist(
        self,
        name: str,
        photo_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a photo playlist in media service

        Args:
            name: Playlist name
            photo_ids: List of file IDs
            metadata: Optional metadata

        Returns:
            Playlist ID or None if failed
        """
        try:
            response = await self.client.post(
                "/api/v1/playlists",
                json={
                    "name": name,
                    "photo_ids": photo_ids,
                    "metadata": metadata or {}
                }
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return data.get("playlist_id")
            else:
                logger.error(f"Failed to create playlist: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None

    async def sync_album_to_playlist(
        self,
        album_id: str,
        photo_ids: List[str]
    ) -> Optional[str]:
        """
        Sync album photos to media service playlist

        Args:
            album_id: Album ID
            photo_ids: List of file IDs in album

        Returns:
            Playlist ID or None if failed
        """
        try:
            return await self.create_photo_playlist(
                name=f"album_{album_id}",
                photo_ids=photo_ids,
                metadata={"album_id": album_id, "source": "album_service"}
            )

        except Exception as e:
            logger.error(f"Error syncing album to playlist: {e}")
            return None

    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
        logger.info("MediaServiceClient closed")
