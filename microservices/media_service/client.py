"""
Media Service Client

HTTP client library for other microservices to interact with media service.
Handles photo versions, metadata, playlists, rotation schedules, and photo caching.
"""

import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class MediaServiceClient:
    """Media Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Media Service client

        Args:
            base_url: Media service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("media_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8222"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Photo Versions
    # =============================================================================

    async def create_photo_version(
        self,
        photo_id: str,
        version_name: str,
        version_type: str,
        file_id: str,
        user_id: str,
        processing_mode: Optional[str] = None,
        processing_params: Optional[Dict[str, Any]] = None,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new photo version

        Args:
            photo_id: Original photo ID
            version_name: Version name
            version_type: Version type (original, ai_enhanced, ai_styled, etc.)
            file_id: File ID for this version
            user_id: User ID
            processing_mode: Optional processing mode
            processing_params: Optional processing parameters
            organization_id: Optional organization ID

        Returns:
            Created photo version
        """
        try:
            payload = {
                "photo_id": photo_id,
                "version_name": version_name,
                "version_type": version_type,
                "file_id": file_id
            }

            if processing_mode:
                payload["processing_mode"] = processing_mode
            if processing_params:
                payload["processing_params"] = processing_params

            params = {"user_id": user_id}
            if organization_id:
                params["organization_id"] = organization_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/versions",
                json=payload,
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create photo version: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating photo version: {e}")
            return None

    async def get_photo_version(
        self,
        version_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get photo version by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/versions/{version_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get photo version: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting photo version: {e}")
            return None

    async def list_photo_versions(
        self,
        photo_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """List all versions of a photo"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/photos/{photo_id}/versions",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list photo versions: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error listing photo versions: {e}")
            return []

    # =============================================================================
    # Photo Metadata
    # =============================================================================

    async def update_photo_metadata(
        self,
        file_id: str,
        user_id: str,
        ai_labels: Optional[List[str]] = None,
        ai_objects: Optional[List[str]] = None,
        ai_scenes: Optional[List[str]] = None,
        ai_colors: Optional[List[str]] = None,
        face_detection: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update or create photo metadata"""
        try:
            payload = {}
            if ai_labels is not None:
                payload["ai_labels"] = ai_labels
            if ai_objects is not None:
                payload["ai_objects"] = ai_objects
            if ai_scenes is not None:
                payload["ai_scenes"] = ai_scenes
            if ai_colors is not None:
                payload["ai_colors"] = ai_colors
            if face_detection is not None:
                payload["face_detection"] = face_detection
            if quality_score is not None:
                payload["quality_score"] = quality_score

            params = {"user_id": user_id}
            if organization_id:
                params["organization_id"] = organization_id

            response = await self.client.put(
                f"{self.base_url}/api/v1/metadata/{file_id}",
                json=payload,
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update photo metadata: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating photo metadata: {e}")
            return None

    async def get_photo_metadata(
        self,
        file_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get photo metadata by file ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/metadata/{file_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get photo metadata: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting photo metadata: {e}")
            return None

    # =============================================================================
    # Playlists
    # =============================================================================

    async def create_playlist(
        self,
        name: str,
        user_id: str,
        playlist_type: str = "manual",
        description: Optional[str] = None,
        photo_ids: Optional[List[str]] = None,
        smart_criteria: Optional[Dict[str, Any]] = None,
        shuffle: bool = False,
        loop: bool = True,
        transition_duration: int = 5,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new playlist"""
        try:
            payload = {
                "name": name,
                "playlist_type": playlist_type,
                "shuffle": shuffle,
                "loop": loop,
                "transition_duration": transition_duration
            }

            if description:
                payload["description"] = description
            if photo_ids:
                payload["photo_ids"] = photo_ids
            if smart_criteria:
                payload["smart_criteria"] = smart_criteria

            params = {"user_id": user_id}
            if organization_id:
                params["organization_id"] = organization_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/playlists",
                json=payload,
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create playlist: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None

    async def get_playlist(
        self,
        playlist_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get playlist by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/playlists/{playlist_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get playlist: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting playlist: {e}")
            return None

    async def list_user_playlists(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List user's playlists"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/playlists",
                params={"user_id": user_id, "limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list playlists: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error listing playlists: {e}")
            return []

    async def update_playlist(
        self,
        playlist_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        photo_ids: Optional[List[str]] = None,
        smart_criteria: Optional[Dict[str, Any]] = None,
        shuffle: Optional[bool] = None,
        loop: Optional[bool] = None,
        transition_duration: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update playlist"""
        try:
            payload = {}
            if name is not None:
                payload["name"] = name
            if description is not None:
                payload["description"] = description
            if photo_ids is not None:
                payload["photo_ids"] = photo_ids
            if smart_criteria is not None:
                payload["smart_criteria"] = smart_criteria
            if shuffle is not None:
                payload["shuffle"] = shuffle
            if loop is not None:
                payload["loop"] = loop
            if transition_duration is not None:
                payload["transition_duration"] = transition_duration

            response = await self.client.put(
                f"{self.base_url}/api/v1/playlists/{playlist_id}",
                json=payload,
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update playlist: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating playlist: {e}")
            return None

    async def delete_playlist(
        self,
        playlist_id: str,
        user_id: str
    ) -> bool:
        """Delete playlist"""
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/playlists/{playlist_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete playlist: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting playlist: {e}")
            return False

    # =============================================================================
    # Rotation Schedules
    # =============================================================================

    async def create_rotation_schedule(
        self,
        frame_id: str,
        playlist_id: str,
        user_id: str,
        schedule_type: str = "continuous",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        days_of_week: Optional[List[int]] = None,
        rotation_interval: int = 10,
        shuffle: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Create a new rotation schedule for a smart frame"""
        try:
            payload = {
                "frame_id": frame_id,
                "playlist_id": playlist_id,
                "schedule_type": schedule_type,
                "rotation_interval": rotation_interval,
                "shuffle": shuffle
            }

            if start_time:
                payload["start_time"] = start_time
            if end_time:
                payload["end_time"] = end_time
            if days_of_week:
                payload["days_of_week"] = days_of_week

            response = await self.client.post(
                f"{self.base_url}/api/v1/schedules",
                json=payload,
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create rotation schedule: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating rotation schedule: {e}")
            return None

    async def get_rotation_schedule(
        self,
        schedule_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get rotation schedule by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/schedules/{schedule_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get rotation schedule: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting rotation schedule: {e}")
            return None

    async def list_frame_schedules(
        self,
        frame_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """List all schedules for a smart frame"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/frames/{frame_id}/schedules",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list frame schedules: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error listing frame schedules: {e}")
            return []

    async def update_schedule_status(
        self,
        schedule_id: str,
        is_active: bool,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Update schedule active status"""
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/v1/schedules/{schedule_id}/status",
                params={"is_active": is_active, "user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update schedule status: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating schedule status: {e}")
            return None

    async def delete_rotation_schedule(
        self,
        schedule_id: str,
        user_id: str
    ) -> bool:
        """Delete rotation schedule"""
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/schedules/{schedule_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete rotation schedule: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting rotation schedule: {e}")
            return False

    # =============================================================================
    # Photo Cache
    # =============================================================================

    async def cache_photo_for_frame(
        self,
        frame_id: str,
        photo_id: str,
        user_id: str,
        version_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create cache entry for a photo on a smart frame"""
        try:
            params = {
                "frame_id": frame_id,
                "photo_id": photo_id,
                "user_id": user_id
            }
            if version_id:
                params["version_id"] = version_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/cache",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cache photo: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error caching photo: {e}")
            return None

    async def list_frame_cache(
        self,
        frame_id: str,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List cache entries for a smart frame"""
        try:
            params = {"user_id": user_id}
            if status:
                params["status"] = status

            response = await self.client.get(
                f"{self.base_url}/api/v1/frames/{frame_id}/cache",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list frame cache: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error listing frame cache: {e}")
            return []

    async def update_cache_status(
        self,
        cache_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update photo cache status"""
        try:
            params = {"status": status}
            if error_message:
                params["error_message"] = error_message

            response = await self.client.patch(
                f"{self.base_url}/api/v1/cache/{cache_id}/status",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update cache status: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating cache status: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
