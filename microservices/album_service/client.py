"""
Album Service Client

Client library for other microservices to interact with album service via HTTP
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class AlbumServiceClient:
    """Album Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Album Service client

        Args:
            base_url: Album service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("album_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8219"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Album Management
    # =============================================================================

    async def create_album(
        self,
        name: str,
        user_id: str,
        description: Optional[str] = None,
        organization_id: Optional[str] = None,
        auto_sync: bool = False,
        sync_frames: Optional[List[str]] = None,
        is_family_shared: bool = False,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new album

        Args:
            name: Album name
            user_id: User ID
            description: Album description
            organization_id: Organization ID for shared albums
            auto_sync: Enable automatic sync to frames
            sync_frames: List of frame IDs to sync with
            is_family_shared: Whether album is shared with family
            tags: Album tags

        Returns:
            Created album details

        Example:
            >>> async with AlbumServiceClient() as client:
            ...     album = await client.create_album(
            ...         name="Summer Vacation 2025",
            ...         user_id="user123",
            ...         description="Photos from our trip",
            ...         auto_sync=True,
            ...         sync_frames=["frame1", "frame2"]
            ...     )
        """
        try:
            payload = {
                "name": name,
                "auto_sync": auto_sync,
                "is_family_shared": is_family_shared
            }

            if description:
                payload["description"] = description
            if organization_id:
                payload["organization_id"] = organization_id
            if sync_frames:
                payload["sync_frames"] = sync_frames
            if tags:
                payload["tags"] = tags

            response = await self.client.post(
                f"{self.base_url}/api/v1/albums",
                json=payload,
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create album: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating album: {e}")
            return None

    async def get_album(
        self,
        album_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get album by ID

        Args:
            album_id: Album ID
            user_id: User ID

        Returns:
            Album details

        Example:
            >>> album = await client.get_album("alb_abc123", "user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/albums/{album_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get album: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting album: {e}")
            return None

    async def list_user_albums(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        organization_id: Optional[str] = None,
        is_family_shared: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        List albums for a user

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page
            organization_id: Filter by organization
            is_family_shared: Filter by family sharing status

        Returns:
            Paginated album list

        Example:
            >>> albums = await client.list_user_albums("user123", page=1, page_size=20)
            >>> for album in albums['albums']:
            ...     print(album['name'])
        """
        try:
            params = {
                "user_id": user_id,
                "page": page,
                "page_size": page_size
            }

            if organization_id:
                params["organization_id"] = organization_id
            if is_family_shared is not None:
                params["is_family_shared"] = is_family_shared

            response = await self.client.get(
                f"{self.base_url}/api/v1/albums",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list albums: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error listing albums: {e}")
            return None

    async def update_album(
        self,
        album_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        cover_photo_id: Optional[str] = None,
        auto_sync: Optional[bool] = None,
        sync_frames: Optional[List[str]] = None,
        is_family_shared: Optional[bool] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update album

        Args:
            album_id: Album ID
            user_id: User ID
            name: New album name
            description: New description
            cover_photo_id: New cover photo ID
            auto_sync: Update auto-sync setting
            sync_frames: Update sync frames list
            is_family_shared: Update family sharing status
            tags: Update tags

        Returns:
            Updated album details

        Example:
            >>> album = await client.update_album(
            ...     album_id="alb_abc123",
            ...     user_id="user123",
            ...     name="Updated Album Name",
            ...     auto_sync=True
            ... )
        """
        try:
            payload = {}

            if name is not None:
                payload["name"] = name
            if description is not None:
                payload["description"] = description
            if cover_photo_id is not None:
                payload["cover_photo_id"] = cover_photo_id
            if auto_sync is not None:
                payload["auto_sync"] = auto_sync
            if sync_frames is not None:
                payload["sync_frames"] = sync_frames
            if is_family_shared is not None:
                payload["is_family_shared"] = is_family_shared
            if tags is not None:
                payload["tags"] = tags

            response = await self.client.put(
                f"{self.base_url}/api/v1/albums/{album_id}",
                json=payload,
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update album: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error updating album: {e}")
            return None

    async def delete_album(
        self,
        album_id: str,
        user_id: str
    ) -> bool:
        """
        Delete album

        Args:
            album_id: Album ID
            user_id: User ID

        Returns:
            True if deleted successfully

        Example:
            >>> success = await client.delete_album("alb_abc123", "user123")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/albums/{album_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("success", False)

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete album: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting album: {e}")
            return False

    # =============================================================================
    # Album Photo Management
    # =============================================================================

    async def add_photos_to_album(
        self,
        album_id: str,
        photo_ids: List[str],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Add photos to album

        Args:
            album_id: Album ID
            photo_ids: List of photo/file IDs to add
            user_id: User ID

        Returns:
            Operation result with counts

        Example:
            >>> result = await client.add_photos_to_album(
            ...     album_id="alb_abc123",
            ...     photo_ids=["file1", "file2", "file3"],
            ...     user_id="user123"
            ... )
            >>> print(f"Added {result['added_count']} photos")
        """
        try:
            payload = {"photo_ids": photo_ids}

            response = await self.client.post(
                f"{self.base_url}/api/v1/albums/{album_id}/photos",
                json=payload,
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add photos: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error adding photos: {e}")
            return None

    async def remove_photos_from_album(
        self,
        album_id: str,
        photo_ids: List[str],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Remove photos from album

        Args:
            album_id: Album ID
            photo_ids: List of photo/file IDs to remove
            user_id: User ID

        Returns:
            Operation result with counts

        Example:
            >>> result = await client.remove_photos_from_album(
            ...     album_id="alb_abc123",
            ...     photo_ids=["file1", "file2"],
            ...     user_id="user123"
            ... )
        """
        try:
            payload = {"photo_ids": photo_ids}

            response = await self.client.request(
                "DELETE",
                f"{self.base_url}/api/v1/albums/{album_id}/photos",
                json=payload,
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to remove photos: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error removing photos: {e}")
            return None

    async def get_album_photos(
        self,
        album_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get photos in album

        Args:
            album_id: Album ID
            user_id: User ID
            limit: Maximum number of photos to return
            offset: Pagination offset

        Returns:
            List of album photos

        Example:
            >>> photos = await client.get_album_photos("alb_abc123", "user123", limit=20)
            >>> for photo in photos:
            ...     print(f"{photo['photo_id']} added at {photo['added_at']}")
        """
        try:
            params = {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/albums/{album_id}/photos",
                params=params
            )
            response.raise_for_status()
            result = response.json()
            return result.get("photos", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get album photos: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting album photos: {e}")
            return None

    # =============================================================================
    # Sync Operations
    # =============================================================================

    async def sync_album_to_frame(
        self,
        album_id: str,
        frame_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Sync album to smart frame

        Args:
            album_id: Album ID
            frame_id: Smart frame device ID
            user_id: User ID

        Returns:
            Sync status

        Example:
            >>> status = await client.sync_album_to_frame(
            ...     album_id="alb_abc123",
            ...     frame_id="frame_xyz789",
            ...     user_id="user123"
            ... )
            >>> print(f"Sync status: {status['sync_status']}")
        """
        try:
            payload = {"frame_id": frame_id}

            response = await self.client.post(
                f"{self.base_url}/api/v1/albums/{album_id}/sync",
                json=payload,
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to sync album: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error syncing album: {e}")
            return None

    async def get_album_sync_status(
        self,
        album_id: str,
        frame_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get album sync status for a frame

        Args:
            album_id: Album ID
            frame_id: Smart frame device ID
            user_id: User ID

        Returns:
            Sync status details

        Example:
            >>> status = await client.get_album_sync_status(
            ...     album_id="alb_abc123",
            ...     frame_id="frame_xyz789",
            ...     user_id="user123"
            ... )
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/albums/{album_id}/sync/{frame_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get sync status: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting sync status: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> Optional[Dict[str, Any]]:
        """
        Check service health

        Returns:
            Health status

        Example:
            >>> health = await client.health_check()
            >>> if health['status'] == 'healthy':
            ...     print("Service is healthy")
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            return None


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_album_client(base_url: Optional[str] = None) -> AlbumServiceClient:
    """
    Create an album service client

    Args:
        base_url: Album service base URL (defaults to service discovery)

    Returns:
        AlbumServiceClient

    Example:
        >>> client = await create_album_client()
        >>> album = await client.create_album(name="My Album", user_id="user123")
        >>> await client.close()
    """
    return AlbumServiceClient(base_url=base_url)
