"""
Album Repository - Data access layer for album service
Handles database operations for albums, album photos, and sync status

Uses PostgresClient with gRPC for PostgreSQL access
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from .models import Album, AlbumPhoto, AlbumSyncStatus, SyncStatus

logger = logging.getLogger(__name__)


class AlbumRepository:
    """Album repository - data access layer for album operations"""

    def __init__(self):
        """Initialize album repository with PostgresClient"""
        # TODO: Use Consul service discovery instead of hardcoded host/port
        self.db = PostgresClient(
            host='isa-postgres-grpc',
            port=50061,
            user_id='album_service'
        )
        # Table names (album schema)
        self.schema = "album"
        self.albums_table = "albums"
        self.album_photos_table = "album_photos"
        self.sync_status_table = "album_sync_status"

    # ==================== Album Operations ====================

    async def create_album(self, album_data: Album) -> Optional[Album]:
        """Create a new album"""
        try:
            data = {
                "album_id": album_data.album_id,
                "name": album_data.name,
                "description": album_data.description,
                "user_id": album_data.user_id,
                "organization_id": album_data.organization_id,
                "cover_photo_id": album_data.cover_photo_id,
                "photo_count": 0,
                "auto_sync": album_data.auto_sync,
                "sync_frames": album_data.sync_frames or [],
                "is_family_shared": album_data.is_family_shared,
                "sharing_resource_id": album_data.sharing_resource_id,
                "tags": album_data.tags or [],
                "metadata": album_data.metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_synced_at": None
            }

            with self.db:
                count = self.db.insert_into(self.albums_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_album_by_id(album_data.album_id, album_data.user_id)
            # Even if count is None, try to get the album (might have been inserted)
            return await self.get_album_by_id(album_data.album_id, album_data.user_id)

        except Exception as e:
            logger.error(f"Error creating album: {e}")
            raise

    async def get_album_by_id(self, album_id: str, user_id: Optional[str] = None) -> Optional[Album]:
        """Get album by album_id"""
        try:
            if user_id:
                query = f"""
                    SELECT * FROM {self.schema}.{self.albums_table}
                    WHERE album_id = $1 AND user_id = $2
                """
                params = [album_id, user_id]
            else:
                query = f"""
                    SELECT * FROM {self.schema}.{self.albums_table}
                    WHERE album_id = $1
                """
                params = [album_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return Album.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting album by ID {album_id}: {e}")
            return None

    async def list_user_albums(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        is_family_shared: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Album]:
        """List albums for a user with optional filters"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if is_family_shared is not None:
                param_count += 1
                conditions.append(f"is_family_shared = ${param_count}")
                params.append(is_family_shared)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.albums_table}
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [Album.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing user albums: {e}")
            return []

    async def update_album(
        self,
        album_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update album"""
        try:
            # Build SET clause dynamically
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            # Add WHERE conditions
            param_count += 1
            params.append(album_id)
            album_id_param = param_count

            param_count += 1
            params.append(user_id)
            user_id_param = param_count

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.albums_table}
                SET {set_clause}
                WHERE album_id = ${album_id_param} AND user_id = ${user_id_param}
            """

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating album: {e}")
            raise

    async def delete_album(self, album_id: str, user_id: str) -> bool:
        """Delete an album (hard delete for now)"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.albums_table}
                WHERE album_id = $1 AND user_id = $2
            """
            params = [album_id, user_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting album: {e}")
            raise

    async def update_album_photo_count(self, album_id: str) -> bool:
        """Update photo count for an album"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.albums_table}
                SET
                    photo_count = (
                        SELECT COUNT(*) FROM {self.schema}.{self.album_photos_table}
                        WHERE album_id = $1
                    ),
                    updated_at = $2
                WHERE album_id = $1
            """
            params = [album_id, datetime.now(timezone.utc)]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating album photo count: {e}")
            return False

    # ==================== Album Photos Operations ====================

    async def add_photos_to_album(
        self,
        album_id: str,
        photo_ids: List[str],
        added_by: str
    ) -> int:
        """Add photos to album (returns number of photos added)"""
        try:
            # Prepare data for bulk insert
            data_list = []
            for idx, photo_id in enumerate(photo_ids):
                data_list.append({
                    "album_id": album_id,
                    "photo_id": photo_id,
                    "added_by": added_by,
                    "added_at": datetime.now(timezone.utc),
                    "is_featured": False,
                    "display_order": idx,
                    "ai_tags": [],
                    "ai_objects": [],
                    "ai_scenes": [],
                    "face_detection_results": None
                })

            with self.db:
                count = self.db.insert_into(
                    self.album_photos_table,
                    data_list,
                    schema=self.schema,
                    on_conflict="DO NOTHING"  # Ignore duplicates
                )

            # Update album photo count
            if count is not None and count > 0:
                await self.update_album_photo_count(album_id)

            return count if count is not None else 0

        except Exception as e:
            logger.error(f"Error adding photos to album: {e}")
            raise

    async def remove_photos_from_album(
        self,
        album_id: str,
        photo_ids: List[str]
    ) -> int:
        """Remove photos from album (returns number of photos removed)"""
        try:
            # Build IN clause
            placeholders = ",".join([f"${i+2}" for i in range(len(photo_ids))])
            query = f"""
                DELETE FROM {self.schema}.{self.album_photos_table}
                WHERE album_id = $1 AND photo_id IN ({placeholders})
            """
            params = [album_id] + photo_ids

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            # Update album photo count
            if count is not None and count > 0:
                await self.update_album_photo_count(album_id)

            return count if count is not None else 0

        except Exception as e:
            logger.error(f"Error removing photos from album: {e}")
            raise

    async def get_album_photos(
        self,
        album_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[AlbumPhoto]:
        """Get photos in an album"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.album_photos_table}
                WHERE album_id = $1
                ORDER BY display_order ASC, added_at DESC
                LIMIT {limit} OFFSET {offset}
            """
            params = [album_id]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [AlbumPhoto.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting album photos: {e}")
            return []

    async def remove_all_photos_from_album(self, album_id: str) -> bool:
        """Remove all photos from an album"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.album_photos_table}
                WHERE album_id = $1
            """
            params = [album_id]

            with self.db:
                self.db.execute(query, params, schema=self.schema)

            # Update album photo count to 0
            await self.update_album_photo_count(album_id)
            return True

        except Exception as e:
            logger.error(f"Error removing all photos from album: {e}")
            return False

    # ==================== Album Sync Status Operations ====================

    async def get_album_sync_status(
        self,
        album_id: str,
        frame_id: str
    ) -> Optional[AlbumSyncStatus]:
        """Get sync status for album and frame"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.sync_status_table}
                WHERE album_id = $1 AND frame_id = $2
            """
            params = [album_id, frame_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return AlbumSyncStatus.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting album sync status: {e}")
            return None

    async def update_album_sync_status(
        self,
        album_id: str,
        frame_id: str,
        user_id: str,
        status_data: Dict[str, Any]
    ) -> bool:
        """Update or create album sync status"""
        try:
            # First, try to get existing record
            existing = await self.get_album_sync_status(album_id, frame_id)

            if existing:
                # Update existing record
                set_clauses = []
                params = []
                param_count = 0

                for key, value in status_data.items():
                    param_count += 1
                    set_clauses.append(f"{key} = ${param_count}")
                    params.append(value)

                param_count += 1
                set_clauses.append(f"updated_at = ${param_count}")
                params.append(datetime.now(timezone.utc))

                param_count += 1
                params.append(album_id)
                album_id_param = param_count

                param_count += 1
                params.append(frame_id)
                frame_id_param = param_count

                set_clause = ", ".join(set_clauses)
                query = f"""
                    UPDATE {self.schema}.{self.sync_status_table}
                    SET {set_clause}
                    WHERE album_id = ${album_id_param} AND frame_id = ${frame_id_param}
                """

                with self.db:
                    count = self.db.execute(query, params, schema=self.schema)

                return count is not None and count > 0
            else:
                # Create new record
                data = {
                    "album_id": album_id,
                    "user_id": user_id,
                    "frame_id": frame_id,
                    "last_sync_timestamp": status_data.get("last_sync_timestamp"),
                    "sync_version": status_data.get("sync_version", 0),
                    "total_photos": status_data.get("total_photos", 0),
                    "synced_photos": status_data.get("synced_photos", 0),
                    "pending_photos": status_data.get("pending_photos", 0),
                    "failed_photos": status_data.get("failed_photos", 0),
                    "sync_status": status_data.get("sync_status", "pending"),
                    "error_message": status_data.get("error_message"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

                with self.db:
                    count = self.db.insert_into(self.sync_status_table, [data], schema=self.schema)

                return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating album sync status: {e}")
            raise

    async def list_album_sync_statuses(
        self,
        album_id: Optional[str] = None,
        frame_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[AlbumSyncStatus]:
        """List album sync statuses with optional filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if album_id:
                param_count += 1
                conditions.append(f"album_id = ${param_count}")
                params.append(album_id)

            if frame_id:
                param_count += 1
                conditions.append(f"frame_id = ${param_count}")
                params.append(frame_id)

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"""
                SELECT * FROM {self.schema}.{self.sync_status_table}
                WHERE {where_clause}
                ORDER BY updated_at DESC
            """

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [AlbumSyncStatus.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing album sync statuses: {e}")
            return []

    # ==================== Event Handler Methods ====================

    async def remove_photo_from_all_albums(self, photo_id: str) -> int:
        """
        Remove a photo from all albums (for file.deleted event handling)

        Args:
            photo_id: Photo file ID to remove

        Returns:
            int: Number of albums the photo was removed from
        """
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.photo_table}
                WHERE photo_id = $1
            """

            with self.db:
                count = self.db.execute(query, [photo_id], schema=self.schema)

            logger.info(f"Removed photo {photo_id} from {count} albums")
            return count if count else 0

        except Exception as e:
            logger.error(f"Error removing photo from all albums: {e}")
            return 0

    async def delete_sync_status_by_frame(self, frame_id: str) -> int:
        """
        Delete all sync status records for a frame (for device.deleted event handling)

        Args:
            frame_id: Frame device ID

        Returns:
            int: Number of sync status records deleted
        """
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.sync_status_table}
                WHERE frame_id = $1
            """

            with self.db:
                count = self.db.execute(query, [frame_id], schema=self.schema)

            logger.info(f"Deleted {count} sync status records for frame {frame_id}")
            return count if count else 0

        except Exception as e:
            logger.error(f"Error deleting sync status by frame: {e}")
            return 0

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
