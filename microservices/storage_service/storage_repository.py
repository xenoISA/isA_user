"""
Storage Repository - Data access layer for storage service
Handles database operations for file storage, sharing, and quotas

Uses AsyncPostgresClient with gRPC for true non-blocking PostgreSQL access
Migrated to AsyncPostgresClient - 2025-11-30
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    StoredFile, FileShare, StorageQuota,
    FileStatus, StorageProvider, FileAccessLevel
)

logger = logging.getLogger(__name__)


class StorageRepository:
    """Storage repository - data access layer for file storage operations using async PostgreSQL"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize storage repository with AsyncPostgresClient"""
        # 使用 config_manager 进行服务发现
        if config is None:
            config = ConfigManager("storage_service")

        # 发现 PostgreSQL 服务
        # 优先级：环境变量 → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(host=host, port=port, user_id='storage_service')
        # Table names (storage schema)
        self.schema = "storage"
        self.files_table = "storage_files"
        self.shares_table = "file_shares"
        self.quotas_table = "storage_quotas"
        self.intelligence_table = "storage_intelligence_index"

    # ==================== Storage Files Operations ====================

    async def create_file_record(self, file_data: StoredFile) -> Optional[StoredFile]:
        """Create a new file record in storage_files table"""
        try:
            data = {
                "file_id": file_data.file_id,
                "user_id": file_data.user_id,
                "organization_id": file_data.organization_id,
                "file_name": file_data.file_name,
                "file_path": file_data.file_path,
                "file_size": file_data.file_size,
                "content_type": file_data.content_type,
                "file_extension": file_data.file_extension,
                "storage_provider": file_data.storage_provider.value if hasattr(file_data.storage_provider, 'value') else file_data.storage_provider,
                "bucket_name": file_data.bucket_name,
                "object_name": file_data.object_name,
                "status": file_data.status.value if hasattr(file_data.status, 'value') else file_data.status,
                "access_level": file_data.access_level.value if hasattr(file_data.access_level, 'value') else file_data.access_level,
                "checksum": file_data.checksum,
                "etag": file_data.etag,
                "version_id": file_data.version_id,
                "metadata": file_data.metadata or {},
                "tags": file_data.tags or [],
                "download_url": file_data.download_url,
                "download_url_expires_at": file_data.download_url_expires_at.isoformat() if file_data.download_url_expires_at else None,
                "uploaded_at": (file_data.uploaded_at or datetime.now(timezone.utc)).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            async with self.db:
                count = await self.db.insert_into(self.files_table, [data], schema=self.schema)

            if count and count > 0:
                # Fetch the created file
                return await self.get_file_by_id(file_data.file_id, file_data.user_id)
            return None

        except Exception as e:
            logger.error(f"Error creating file record: {e}")
            raise

    async def get_file_by_id(self, file_id: str, user_id: Optional[str] = None) -> Optional[StoredFile]:
        """Get file record by file_id"""
        try:
            if user_id:
                query = f"""
                    SELECT * FROM {self.schema}.{self.files_table}
                    WHERE file_id = $1 AND user_id = $2 AND status != 'deleted'
                """
                params = [file_id, user_id]
            else:
                query = f"""
                    SELECT * FROM {self.schema}.{self.files_table}
                    WHERE file_id = $1 AND status != 'deleted'
                """
                params = [file_id]

            async with self.db:
                result = await self.db.query_row(query, params=params)

            if result:
                return StoredFile.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting file by ID {file_id}: {e}")
            return None

    async def list_user_files(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        status: Optional[FileStatus] = None,
        content_type: Optional[str] = None,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StoredFile]:
        """List files for a user with optional filters"""
        try:
            conditions = ["user_id = $1", "status != 'deleted'"]
            params = [user_id]
            param_count = 1

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if status:
                param_count += 1
                status_value = status.value if hasattr(status, 'value') else status
                conditions.append(f"status = ${param_count}")
                params.append(status_value)

            if content_type:
                param_count += 1
                conditions.append(f"content_type LIKE ${param_count}")
                params.append(f"{content_type}%")

            if prefix:
                param_count += 1
                conditions.append(f"file_path LIKE ${param_count}")
                params.append(f"{prefix}%")

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.files_table}
                WHERE {where_clause}
                ORDER BY uploaded_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            async with self.db:
                results = await self.db.query(query, params=params)

            return [StoredFile.model_validate(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error listing user files: {e}")
            return []

    async def update_file_status(
        self,
        file_id: str,
        user_id: str,
        status: FileStatus,
        download_url: Optional[str] = None,
        download_url_expires_at: Optional[datetime] = None
    ) -> bool:
        """Update file status and optionally download URL"""
        try:
            status_value = status.value if hasattr(status, 'value') else status

            if download_url:
                query = f"""
                    UPDATE {self.schema}.{self.files_table}
                    SET status = $1, download_url = $2, download_url_expires_at = $3, updated_at = $4
                    WHERE file_id = $5 AND user_id = $6
                """
                params = [status_value, download_url, download_url_expires_at, datetime.now(timezone.utc), file_id, user_id]
            else:
                query = f"""
                    UPDATE {self.schema}.{self.files_table}
                    SET status = $1, updated_at = $2
                    WHERE file_id = $3 AND user_id = $4
                """
                params = [status_value, datetime.now(timezone.utc), file_id, user_id]

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count > 0 if count else False

        except Exception as e:
            logger.error(f"Error updating file status: {e}")
            raise

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Soft delete a file (set status to deleted)"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.files_table}
                SET status = 'deleted', deleted_at = $1, updated_at = $1
                WHERE file_id = $2 AND user_id = $3
            """
            params = [datetime.now(timezone.utc), file_id, user_id]

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count > 0 if count else False

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise

    # ==================== File Shares Operations ====================

    async def create_file_share(self, share_data: FileShare) -> Optional[FileShare]:
        """Create a new file share record"""
        try:
            # Convert permissions dict to array format for PostgreSQL
            permissions_array = []
            if share_data.permissions:
                if share_data.permissions.get("view", False):
                    permissions_array.append("read")
                if share_data.permissions.get("download", False):
                    permissions_array.append("download")
                if share_data.permissions.get("delete", False):
                    permissions_array.append("delete")

            data = {
                "share_id": share_data.share_id,
                "file_id": share_data.file_id,
                "shared_by": share_data.shared_by,
                "shared_with": share_data.shared_with,
                "shared_with_email": share_data.shared_with_email,
                "access_token": share_data.access_token or "",
                "password": share_data.password,
                "permissions": permissions_array or ["read"],
                "max_downloads": share_data.max_downloads,
                "download_count": share_data.download_count or 0,
                "expires_at": share_data.expires_at.isoformat() if share_data.expires_at else None,
                "is_active": share_data.is_active if hasattr(share_data, 'is_active') else True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "accessed_at": None
            }

            async with self.db:
                count = await self.db.insert_into(self.shares_table, [data], schema=self.schema)

            logger.info(f"Insert file share result: count={count}, share_id={share_data.share_id}")

            if count and count > 0:
                return await self.get_file_share(share_data.share_id)

            logger.warning(f"Failed to create file share, count={count}")
            return None

        except Exception as e:
            logger.error(f"Error creating file share: {e}")
            raise

    async def get_file_share(
        self,
        share_id: Optional[str] = None,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[FileShare]:
        """Get file share by share_id or file_id + user_id"""
        try:
            logger.info(f"Getting file share: share_id={share_id}, file_id={file_id}, user_id={user_id}")

            if share_id:
                query = f"""
                    SELECT * FROM {self.schema}.{self.shares_table}
                    WHERE share_id = $1 AND is_active = TRUE
                """
                params = [share_id]
            elif file_id and user_id:
                query = f"""
                    SELECT * FROM {self.schema}.{self.shares_table}
                    WHERE file_id = $1 AND shared_with = $2 AND is_active = TRUE
                """
                params = [file_id, user_id]
            else:
                logger.error("Either share_id or (file_id + user_id) must be provided")
                return None

            async with self.db:
                result = await self.db.query_row(query, params=params)

            logger.info(f"Query result for share_id={share_id}: {result}")

            if result:
                # Convert permissions array to dict format
                if 'permissions' in result:
                    permissions_value = result['permissions']
                    # Handle both list and protobuf ListValue
                    if isinstance(permissions_value, list):
                        permissions_array = permissions_value
                    else:
                        # Convert protobuf ListValue to list
                        permissions_array = []
                        try:
                            for item in permissions_value:
                                if hasattr(item, 'string_value'):
                                    permissions_array.append(item.string_value)
                                else:
                                    permissions_array.append(str(item))
                        except:
                            permissions_array = []

                    result['permissions'] = {
                        "view": "read" in permissions_array or "view" in permissions_array,
                        "download": "download" in permissions_array,
                        "delete": "delete" in permissions_array
                    }

                share = FileShare.model_validate(result)
                logger.info(f"Validated FileShare: {share}")
                return share

            logger.warning(f"No share found for share_id={share_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting file share (share_id={share_id}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def list_file_shares(
        self,
        file_id: Optional[str] = None,
        shared_by: Optional[str] = None,
        shared_with: Optional[str] = None
    ) -> List[FileShare]:
        """List file shares with optional filters"""
        try:
            conditions = ["is_active = TRUE"]
            params = []
            param_count = 0

            if file_id:
                param_count += 1
                conditions.append(f"file_id = ${param_count}")
                params.append(file_id)

            if shared_by:
                param_count += 1
                conditions.append(f"shared_by = ${param_count}")
                params.append(shared_by)

            if shared_with:
                param_count += 1
                conditions.append(f"shared_with = ${param_count}")
                params.append(shared_with)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.shares_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
            """

            async with self.db:
                results = await self.db.query(query, params=params)

            if not results:
                return []

            # Convert permissions array to dict format for each result
            shares = []
            for row in results:
                if 'permissions' in row:
                    permissions_value = row['permissions']
                    # Handle both list and protobuf ListValue
                    if isinstance(permissions_value, list):
                        permissions_array = permissions_value
                    else:
                        # Convert protobuf ListValue to list
                        permissions_array = []
                        try:
                            for item in permissions_value:
                                if hasattr(item, 'string_value'):
                                    permissions_array.append(item.string_value)
                                else:
                                    permissions_array.append(str(item))
                        except:
                            permissions_array = []

                    row['permissions'] = {
                        "view": "read" in permissions_array or "view" in permissions_array,
                        "download": "download" in permissions_array,
                        "delete": "delete" in permissions_array
                    }
                shares.append(FileShare.model_validate(row))

            return shares

        except Exception as e:
            logger.error(f"Error listing file shares: {e}")
            return []

    async def increment_share_download(self, share_id: str) -> bool:
        """Increment download count and update accessed_at for a share"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.shares_table}
                SET download_count = download_count + 1, accessed_at = $1
                WHERE share_id = $2
            """
            params = [datetime.now(timezone.utc), share_id]

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count > 0 if count else False

        except Exception as e:
            logger.error(f"Error incrementing share download: {e}")
            return False

    # ==================== Storage Quotas Operations ====================

    async def get_storage_quota(
        self,
        quota_type: str,
        entity_id: str
    ) -> Optional[StorageQuota]:
        """Get storage quota for user or organization"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.quotas_table}
                WHERE quota_type = $1 AND entity_id = $2 AND is_active = TRUE
            """
            params = [quota_type, entity_id]

            async with self.db:
                result = await self.db.query_row(query, params=params)

            if result:
                return StorageQuota.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting storage quota: {e}")
            return None

    async def create_storage_quota(
        self,
        quota_type: str,
        entity_id: str,
        total_quota_bytes: int = 10737418240,  # 10GB default
        max_file_size: int = 104857600,  # 100MB default
        max_file_count: int = 10000
    ) -> Optional[StorageQuota]:
        """Create a new storage quota record"""
        try:
            data = {
                "quota_type": quota_type,
                "entity_id": entity_id,
                "total_quota_bytes": total_quota_bytes,
                "used_bytes": 0,
                "file_count": 0,
                "max_file_size": max_file_size,
                "max_file_count": max_file_count,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            async with self.db:
                count = await self.db.insert_into(self.quotas_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_storage_quota(quota_type, entity_id)
            return None

        except Exception as e:
            logger.error(f"Error creating storage quota: {e}")
            raise

    async def update_storage_usage(
        self,
        quota_type: str,
        entity_id: str,
        bytes_delta: int,
        file_count_delta: int = 0
    ) -> bool:
        """Update storage usage (add or subtract bytes and file count)"""
        try:
            # First, check if quota record exists
            existing_quota = await self.get_storage_quota(quota_type, entity_id)

            # If no quota exists, create one with default values
            if not existing_quota:
                logger.info(f"Creating default quota for {quota_type}:{entity_id}")
                await self.create_storage_quota(
                    quota_type=quota_type,
                    entity_id=entity_id,
                    total_quota_bytes=10737418240,  # 10GB default
                    max_file_size=524288000,  # 500MB default
                    max_file_count=10000
                )

            # Now update the usage (use COALESCE to handle NULL values)
            query = f"""
                UPDATE {self.schema}.{self.quotas_table}
                SET
                    used_bytes = COALESCE(used_bytes, 0) + $1,
                    file_count = COALESCE(file_count, 0) + $2,
                    updated_at = $3
                WHERE quota_type = $4 AND entity_id = $5
            """
            params = [bytes_delta, file_count_delta, datetime.now(timezone.utc), quota_type, entity_id]

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating storage usage: {e}")
            raise

    async def get_storage_stats(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get storage statistics for user and optionally organization"""
        try:
            stats = {
                "user_quota": None,
                "org_quota": None,
                "total_files": 0,
                "total_size": 0
            }

            # Get user quota
            user_quota = await self.get_storage_quota("user", user_id)
            if user_quota:
                used_bytes = user_quota.used_bytes if user_quota.used_bytes is not None else 0
                total_quota_bytes = user_quota.total_quota_bytes if user_quota.total_quota_bytes is not None else 0
                stats["user_quota"] = {
                    "used_bytes": used_bytes,
                    "total_quota_bytes": total_quota_bytes,
                    "file_count": user_quota.file_count if user_quota.file_count is not None else 0,
                    "max_file_count": user_quota.max_file_count,
                    "usage_percent": (used_bytes / total_quota_bytes * 100) if total_quota_bytes > 0 else 0
                }

            # Get org quota if organization_id provided
            if organization_id:
                org_quota = await self.get_storage_quota("organization", organization_id)
                if org_quota:
                    used_bytes = org_quota.used_bytes if org_quota.used_bytes is not None else 0
                    total_quota_bytes = org_quota.total_quota_bytes if org_quota.total_quota_bytes is not None else 0
                    stats["org_quota"] = {
                        "used_bytes": used_bytes,
                        "total_quota_bytes": total_quota_bytes,
                        "file_count": org_quota.file_count if org_quota.file_count is not None else 0,
                        "max_file_count": org_quota.max_file_count,
                        "usage_percent": (used_bytes / total_quota_bytes * 100) if total_quota_bytes > 0 else 0
                    }

            # Get actual file stats from storage_files
            query = f"""
                SELECT COUNT(*) as file_count, COALESCE(SUM(file_size), 0) as total_size
                FROM {self.schema}.{self.files_table}
                WHERE user_id = $1 AND status = 'active'
            """
            params = [user_id]

            async with self.db:
                result = await self.db.query_row(query, params=params)

            if result:
                stats["total_files"] = result.get("file_count", 0)
                stats["total_size"] = result.get("total_size", 0)

            return stats

        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return stats

    # ==================== Utility Methods ====================

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            async with self.db:
                result = await self.db.query_row("SELECT 1 as connected", params=[])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
