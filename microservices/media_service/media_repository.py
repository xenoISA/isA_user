"""
Media Repository - Data access layer for media service
Handles database operations for photo versions, metadata, playlists, schedules, and cache

Uses PostgresClient with gRPC for PostgreSQL access
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from core.config_manager import ConfigManager
from .models import (
    PhotoVersion, PhotoMetadata, Playlist, RotationSchedule, PhotoCache,
    PhotoVersionType, PlaylistType, CacheStatus, ScheduleType
)

logger = logging.getLogger(__name__)


class MediaRepository:
    """Media repository - data access layer for media operations"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize media repository with PostgresClient"""
        # 使用 config_manager 进行服务发现
        if config is None:
            config = ConfigManager("media_service")

        # 发现 PostgreSQL 服务
        # 优先级：环境变量 → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_GRPC_HOST',
            env_port_key='POSTGRES_GRPC_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(host=host, port=port, user_id='media_service')

        # Table names (media schema)
        self.schema = "media"
        self.versions_table = "photo_versions"
        self.metadata_table = "photo_metadata"
        self.playlists_table = "playlists"
        self.schedules_table = "rotation_schedules"
        self.cache_table = "photo_cache"

    # ==================== Photo Versions Operations ====================

    async def create_photo_version(self, version_data: PhotoVersion) -> Optional[PhotoVersion]:
        """Create a new photo version"""
        try:
            data = {
                "version_id": version_data.version_id,
                "photo_id": version_data.photo_id,
                "user_id": version_data.user_id,
                "organization_id": version_data.organization_id,
                "version_name": version_data.version_name,
                "version_type": version_data.version_type.value if hasattr(version_data.version_type, 'value') else str(version_data.version_type),
                "processing_mode": version_data.processing_mode or "",
                "file_id": version_data.file_id,
                "cloud_url": version_data.cloud_url or "",
                "local_path": version_data.local_path or "",
                "file_size": version_data.file_size or 0,
                "processing_params": version_data.processing_params or {},
                "metadata": version_data.metadata or {},
                "is_current": version_data.is_current or False,
                "version_number": version_data.version_number or 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            with self.db:
                count = self.db.insert_into(self.versions_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_photo_version(version_data.version_id)
            # If count is None or 0, still try to return the version (might have been inserted)
            return await self.get_photo_version(version_data.version_id)

        except Exception as e:
            logger.error(f"Error creating photo version: {e}")
            raise

    async def get_photo_version(self, version_id: str) -> Optional[PhotoVersion]:
        """Get photo version by ID"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.versions_table}
                WHERE version_id = $1
            """
            params = [version_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return PhotoVersion.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting photo version: {e}")
            return None

    async def list_photo_versions(
        self,
        photo_id: str,
        user_id: str
    ) -> List[PhotoVersion]:
        """List all versions of a photo"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.versions_table}
                WHERE photo_id = $1 AND user_id = $2
                ORDER BY version_number DESC
            """
            params = [photo_id, user_id]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [PhotoVersion.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing photo versions: {e}")
            return []

    async def delete_photo_version(
        self,
        version_id: str,
        user_id: str
    ) -> bool:
        """Delete a photo version"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.versions_table}
                WHERE version_id = $1 AND user_id = $2
            """
            params = [version_id, user_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting photo version: {e}")
            raise

    # ==================== Photo Metadata Operations ====================

    async def create_or_update_metadata(
        self,
        metadata_data: PhotoMetadata
    ) -> Optional[PhotoMetadata]:
        """Create or update photo metadata"""
        try:
            # Check if exists
            existing = await self.get_photo_metadata(metadata_data.file_id)

            if existing:
                # Update
                return await self._update_metadata(metadata_data)
            else:
                # Create
                return await self._create_metadata(metadata_data)

        except Exception as e:
            logger.error(f"Error creating/updating metadata: {e}")
            raise

    async def _create_metadata(self, metadata_data: PhotoMetadata) -> Optional[PhotoMetadata]:
        """Create new metadata"""
        data = {
            "file_id": metadata_data.file_id,
            "user_id": metadata_data.user_id,
            "organization_id": metadata_data.organization_id,
            "camera_make": metadata_data.camera_make,
            "camera_model": metadata_data.camera_model,
            "lens_model": metadata_data.lens_model,
            "focal_length": metadata_data.focal_length,
            "aperture": metadata_data.aperture,
            "shutter_speed": metadata_data.shutter_speed,
            "iso": metadata_data.iso,
            "flash_used": metadata_data.flash_used,
            "latitude": metadata_data.latitude,
            "longitude": metadata_data.longitude,
            "location_name": metadata_data.location_name,
            "photo_taken_at": metadata_data.photo_taken_at,
            "ai_labels": metadata_data.ai_labels or [],
            "ai_objects": metadata_data.ai_objects or [],
            "ai_scenes": metadata_data.ai_scenes or [],
            "ai_colors": metadata_data.ai_colors or [],
            "face_detection": metadata_data.face_detection or {},
            "text_detection": metadata_data.text_detection or {},
            "quality_score": metadata_data.quality_score,
            "blur_score": metadata_data.blur_score,
            "brightness": metadata_data.brightness,
            "contrast": metadata_data.contrast,
            "full_metadata": metadata_data.full_metadata or {},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        with self.db:
            count = self.db.insert_into(self.metadata_table, [data], schema=self.schema)

        if count is not None and count > 0:
            return await self.get_photo_metadata(metadata_data.file_id)
        elif count is None:
            logger.error(f"PostgreSQL insert returned None for file_id={metadata_data.file_id}")
            logger.error(f"Data causing error: {data}")
            raise Exception("Database insert failed - check PostgreSQL logs for type mismatch")
        return None

    async def _update_metadata(self, metadata_data: PhotoMetadata) -> Optional[PhotoMetadata]:
        """Update existing metadata"""
        # Build update dynamically based on non-None fields
        update_fields = {}
        if metadata_data.ai_labels is not None:
            update_fields["ai_labels"] = metadata_data.ai_labels
        if metadata_data.ai_objects is not None:
            update_fields["ai_objects"] = metadata_data.ai_objects
        if metadata_data.quality_score is not None:
            update_fields["quality_score"] = metadata_data.quality_score

        if not update_fields:
            return await self.get_photo_metadata(metadata_data.file_id)

        # Build SET clause
        set_clauses = []
        params = []
        param_count = 0

        for key, value in update_fields.items():
            param_count += 1
            set_clauses.append(f"{key} = ${param_count}")
            params.append(value)

        param_count += 1
        set_clauses.append(f"updated_at = ${param_count}")
        params.append(datetime.now(timezone.utc))

        param_count += 1
        params.append(metadata_data.file_id)

        set_clause = ", ".join(set_clauses)
        query = f"""
            UPDATE {self.schema}.{self.metadata_table}
            SET {set_clause}
            WHERE file_id = ${param_count}
        """

        with self.db:
            self.db.execute(query, params, schema=self.schema)

        return await self.get_photo_metadata(metadata_data.file_id)

    async def get_photo_metadata(self, file_id: str) -> Optional[PhotoMetadata]:
        """Get photo metadata by file_id"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.metadata_table}
                WHERE file_id = $1
            """
            params = [file_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return PhotoMetadata.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting photo metadata: {e}")
            return None

    # ==================== Playlist Operations ====================

    async def create_playlist(self, playlist_data: Playlist) -> Optional[Playlist]:
        """Create a new playlist"""
        try:
            data = {
                "playlist_id": playlist_data.playlist_id,
                "name": playlist_data.name,
                "description": playlist_data.description or "",
                "user_id": playlist_data.user_id,
                "organization_id": playlist_data.organization_id,
                "playlist_type": playlist_data.playlist_type.value if hasattr(playlist_data.playlist_type, 'value') else str(playlist_data.playlist_type),
                "smart_criteria": playlist_data.smart_criteria or {},
                "photo_ids": playlist_data.photo_ids or [],
                "shuffle": playlist_data.shuffle or False,
                "loop": playlist_data.loop or True,
                "transition_duration": playlist_data.transition_duration or 5,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            with self.db:
                count = self.db.insert_into(self.playlists_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_playlist(playlist_data.playlist_id)
            # Even if count is None, try to get the playlist (might have been inserted)
            return await self.get_playlist(playlist_data.playlist_id)

        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            raise

    async def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """Get playlist by ID"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.playlists_table}
                WHERE playlist_id = $1
            """
            params = [playlist_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return Playlist.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting playlist: {e}")
            return None

    async def list_user_playlists(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Playlist]:
        """List playlists for a user"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.playlists_table}
                WHERE user_id = $1
                ORDER BY updated_at DESC
                LIMIT {limit} OFFSET {offset}
            """
            params = [user_id]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [Playlist.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing playlists: {e}")
            return []

    async def delete_playlist(self, playlist_id: str, user_id: str) -> bool:
        """Delete a playlist"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.playlists_table}
                WHERE playlist_id = $1 AND user_id = $2
            """
            params = [playlist_id, user_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error deleting playlist: {e}")
            raise

    # ==================== Rotation Schedule Operations ====================

    async def create_rotation_schedule(
        self,
        schedule_data: RotationSchedule
    ) -> Optional[RotationSchedule]:
        """Create a new rotation schedule"""
        try:
            data = {
                "schedule_id": schedule_data.schedule_id,
                "user_id": schedule_data.user_id,
                "frame_id": schedule_data.frame_id,
                "playlist_id": schedule_data.playlist_id,
                "schedule_type": schedule_data.schedule_type.value if hasattr(schedule_data.schedule_type, 'value') else str(schedule_data.schedule_type),
                "start_time": schedule_data.start_time,
                "end_time": schedule_data.end_time,
                "days_of_week": schedule_data.days_of_week or [],
                "rotation_interval": schedule_data.rotation_interval or 10,
                "shuffle": schedule_data.shuffle or False,
                "is_active": schedule_data.is_active or True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            with self.db:
                count = self.db.insert_into(self.schedules_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_rotation_schedule(schedule_data.schedule_id)
            # Even if count is None, try to get the schedule (might have been inserted)
            return await self.get_rotation_schedule(schedule_data.schedule_id)

        except Exception as e:
            logger.error(f"Error creating rotation schedule: {e}")
            raise

    async def get_rotation_schedule(self, schedule_id: str) -> Optional[RotationSchedule]:
        """Get rotation schedule by ID"""
        try:
            query = f"""
                SELECT
                    schedule_id, user_id, frame_id, playlist_id, schedule_type,
                    start_time::text as start_time,
                    end_time::text as end_time,
                    days_of_week, rotation_interval, shuffle, is_active,
                    created_at, updated_at
                FROM {self.schema}.{self.schedules_table}
                WHERE schedule_id = $1
            """
            params = [schedule_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return RotationSchedule.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting rotation schedule: {e}")
            return None

    async def list_frame_schedules(
        self,
        frame_id: str,
        user_id: str
    ) -> List[RotationSchedule]:
        """List all schedules for a frame"""
        try:
            query = f"""
                SELECT
                    schedule_id, user_id, frame_id, playlist_id, schedule_type,
                    start_time::text as start_time,
                    end_time::text as end_time,
                    days_of_week, rotation_interval, shuffle, is_active,
                    created_at, updated_at
                FROM {self.schema}.{self.schedules_table}
                WHERE frame_id = $1 AND user_id = $2
                ORDER BY created_at DESC
            """
            params = [frame_id, user_id]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [RotationSchedule.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing frame schedules: {e}")
            return []

    async def update_schedule_status(
        self,
        schedule_id: str,
        user_id: str,
        is_active: bool
    ) -> Optional[RotationSchedule]:
        """Update schedule active status"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.schedules_table}
                SET is_active = $1, updated_at = $2
                WHERE schedule_id = $3 AND user_id = $4
            """
            params = [is_active, datetime.now(timezone.utc), schedule_id, user_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            if count > 0:
                return await self.get_rotation_schedule(schedule_id)
            return None

        except Exception as e:
            logger.error(f"Error updating schedule status: {e}")
            raise

    async def delete_rotation_schedule(
        self,
        schedule_id: str,
        user_id: str
    ) -> bool:
        """Delete a rotation schedule"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.schedules_table}
                WHERE schedule_id = $1 AND user_id = $2
            """
            params = [schedule_id, user_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error deleting rotation schedule: {e}")
            raise

    # ==================== Photo Cache Operations ====================

    async def create_photo_cache(
        self,
        cache_data: PhotoCache
    ) -> Optional[PhotoCache]:
        """Create a new photo cache entry"""
        try:
            data = {
                "cache_id": cache_data.cache_id,
                "user_id": cache_data.user_id,
                "frame_id": cache_data.frame_id,
                "photo_id": cache_data.photo_id,
                "version_id": cache_data.version_id,
                "cache_status": cache_data.cache_status.value if hasattr(cache_data.cache_status, 'value') else cache_data.cache_status,
                "cached_url": cache_data.cached_url,
                "local_path": cache_data.local_path,
                "cache_size": cache_data.cache_size,
                "cache_format": cache_data.cache_format,
                "cache_quality": cache_data.cache_quality,
                "hit_count": cache_data.hit_count,
                "last_accessed_at": cache_data.last_accessed_at,
                "error_message": cache_data.error_message,
                "retry_count": cache_data.retry_count,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "expires_at": cache_data.expires_at
            }

            with self.db:
                count = self.db.insert_into(self.cache_table, [data], schema=self.schema)

            if count > 0:
                return await self.get_photo_cache(cache_data.cache_id)
            return None

        except Exception as e:
            logger.error(f"Error creating photo cache: {e}")
            raise

    async def get_photo_cache(self, cache_id: str) -> Optional[PhotoCache]:
        """Get photo cache by ID"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.cache_table}
                WHERE cache_id = $1
            """
            params = [cache_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return PhotoCache.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting photo cache: {e}")
            return None

    async def get_frame_cache(
        self,
        frame_id: str,
        photo_id: str,
        user_id: str
    ) -> Optional[PhotoCache]:
        """Get cached photo for a frame"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.cache_table}
                WHERE frame_id = $1 AND photo_id = $2 AND user_id = $3
                ORDER BY created_at DESC
                LIMIT 1
            """
            params = [frame_id, photo_id, user_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return PhotoCache.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting frame cache: {e}")
            return None

    async def list_frame_cache(
        self,
        frame_id: str,
        user_id: str,
        status: Optional[CacheStatus] = None
    ) -> List[PhotoCache]:
        """List all cache entries for a frame"""
        try:
            if status:
                query = f"""
                    SELECT * FROM {self.schema}.{self.cache_table}
                    WHERE frame_id = $1 AND user_id = $2 AND cache_status = $3
                    ORDER BY last_accessed_at DESC
                """
                params = [frame_id, user_id, status.value if hasattr(status, 'value') else status]
            else:
                query = f"""
                    SELECT * FROM {self.schema}.{self.cache_table}
                    WHERE frame_id = $1 AND user_id = $2
                    ORDER BY last_accessed_at DESC
                """
                params = [frame_id, user_id]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [PhotoCache.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing frame cache: {e}")
            return []

    async def update_cache_status(
        self,
        cache_id: str,
        status: CacheStatus,
        error_message: Optional[str] = None
    ) -> Optional[PhotoCache]:
        """Update cache status"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.cache_table}
                SET cache_status = $1,
                    error_message = $2,
                    updated_at = $3
                WHERE cache_id = $4
            """
            params = [
                status.value if hasattr(status, 'value') else status,
                error_message,
                datetime.now(timezone.utc),
                cache_id
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            if count > 0:
                return await self.get_photo_cache(cache_id)
            return None

        except Exception as e:
            logger.error(f"Error updating cache status: {e}")
            raise

    async def increment_cache_hit(self, cache_id: str) -> bool:
        """Increment cache hit count"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.cache_table}
                SET hit_count = hit_count + 1,
                    last_accessed_at = $1,
                    updated_at = $1
                WHERE cache_id = $2
            """
            params = [datetime.now(timezone.utc), cache_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error incrementing cache hit: {e}")
            return False

    async def delete_photo_cache(self, cache_id: str) -> bool:
        """Delete a photo cache entry"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.cache_table}
                WHERE cache_id = $1
            """
            params = [cache_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error deleting photo cache: {e}")
            raise

    async def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.cache_table}
                WHERE expires_at IS NOT NULL AND expires_at < $1
            """
            params = [datetime.now(timezone.utc)]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            return 0

    # ==================== Playlist Update Operations ====================

    async def update_playlist(
        self,
        playlist_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Playlist]:
        """Update playlist fields"""
        try:
            if not update_data:
                return await self.get_playlist(playlist_id)

            # Build SET clause dynamically
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            param_count += 1
            params.append(playlist_id)
            param_count += 1
            params.append(user_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.playlists_table}
                SET {set_clause}
                WHERE playlist_id = ${param_count - 1} AND user_id = ${param_count}
            """

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            if count > 0:
                return await self.get_playlist(playlist_id)
            return None

        except Exception as e:
            logger.error(f"Error updating playlist: {e}")
            raise

    # ==================== Utility Methods ====================

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            with self.db:
                result = self.db.query_row("SELECT 1 as connected", [])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
