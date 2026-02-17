"""
Mock Storage Repository for Component Testing

Implements storage repository interface for testing StorageService without database.
Follows the established mock pattern from tests/component/mocks/.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import uuid

from microservices.storage_service.models import (
    StoredFile,
    FileShare,
    StorageQuota,
    FileStatus,
    FileAccessLevel,
    StorageProvider,
)


class MockStorageRepository:
    """
    Mock implementation of StorageRepository for testing.

    Provides in-memory storage and configurable behavior for testing
    StorageService without a real database or MinIO.

    Pattern: Follows tests/component/mocks/account_repository_mock.py
    """

    def __init__(self):
        # In-memory storage
        self._files: Dict[str, StoredFile] = {}
        self._shares: Dict[str, FileShare] = {}
        self._quotas: Dict[tuple, StorageQuota] = {}  # (quota_type, entity_id) -> quota

        # Call history tracking
        self._call_history: List[Dict[str, Any]] = []

        # Error simulation
        self._should_raise: Optional[Exception] = None

    # ========================================================================
    # Test Helper Methods
    # ========================================================================

    def _record_call(self, method: str, **kwargs):
        """Record method call for verification"""
        self._call_history.append({
            "method": method,
            "timestamp": datetime.now(timezone.utc),
            **kwargs
        })

    def _check_error(self):
        """Check if should raise configured error"""
        if self._should_raise:
            error = self._should_raise
            self._should_raise = None  # Reset after raising
            raise error

    def add_file(self, file: StoredFile):
        """Add a file to mock storage"""
        self._files[file.file_id] = file

    def add_share(self, share: FileShare):
        """Add a share to mock storage"""
        self._shares[share.share_id] = share

    def add_quota(self, quota: StorageQuota):
        """Add a quota to mock storage"""
        key = (quota.quota_type, quota.entity_id)
        self._quotas[key] = quota

    def set_error(self, error: Exception):
        """Configure an error to be raised on next call"""
        self._should_raise = error

    def get_calls(self, method: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded calls, optionally filtered by method"""
        if method:
            return [c for c in self._call_history if c["method"] == method]
        return self._call_history

    def get_last_call(self, method: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the last recorded call"""
        calls = self.get_calls(method)
        return calls[-1] if calls else None

    def assert_called(self, method: str):
        """Assert that a method was called"""
        calls = self.get_calls(method)
        assert len(calls) > 0, f"Expected {method} to be called, but it wasn't"

    def assert_called_with(self, method: str, **expected_kwargs):
        """Assert that a method was called with specific arguments"""
        calls = self.get_calls(method)
        assert len(calls) > 0, f"Expected {method} to be called, but it wasn't"

        last_call = calls[-1]
        for key, value in expected_kwargs.items():
            assert key in last_call, f"Expected {key} in call args"
            assert last_call[key] == value, f"Expected {key}={value}, got {last_call[key]}"

    def clear(self):
        """Clear all stored data and call history"""
        self._files.clear()
        self._shares.clear()
        self._quotas.clear()
        self._call_history.clear()
        self._should_raise = None

    # ========================================================================
    # File Operations
    # ========================================================================

    async def create_file_record(self, file_data: StoredFile) -> Optional[StoredFile]:
        """Create a new file record"""
        self._record_call("create_file_record", file_data=file_data)
        self._check_error()

        # Store file
        self._files[file_data.file_id] = file_data

        # Update quota
        quota_key = ("user", file_data.user_id)
        if quota_key in self._quotas:
            quota = self._quotas[quota_key]
            quota.used_bytes = (quota.used_bytes or 0) + file_data.file_size
            quota.file_count = (quota.file_count or 0) + 1

        return file_data

    async def get_file_by_id(
        self, file_id: str, user_id: Optional[str] = None
    ) -> Optional[StoredFile]:
        """Get file record by file_id"""
        self._record_call("get_file_by_id", file_id=file_id, user_id=user_id)
        self._check_error()

        file = self._files.get(file_id)
        if file and file.status != FileStatus.DELETED:
            if user_id is None or file.user_id == user_id:
                return file
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
        self._record_call(
            "list_user_files",
            user_id=user_id,
            organization_id=organization_id,
            status=status,
            content_type=content_type,
            prefix=prefix,
            limit=limit,
            offset=offset
        )
        self._check_error()

        # Filter files
        files = [
            f for f in self._files.values()
            if f.user_id == user_id and f.status != FileStatus.DELETED
        ]

        # Apply filters
        if organization_id:
            files = [f for f in files if f.organization_id == organization_id]

        if status:
            files = [f for f in files if f.status == status]

        if content_type:
            files = [f for f in files if f.content_type.startswith(content_type)]

        if prefix:
            files = [f for f in files if f.file_path.startswith(prefix)]

        # Sort by uploaded_at descending
        files.sort(key=lambda f: f.uploaded_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        # Apply pagination
        return files[offset:offset + limit]

    async def update_file_status(
        self,
        file_id: str,
        user_id: str,
        status: FileStatus,
        download_url: Optional[str] = None,
        download_url_expires_at: Optional[datetime] = None
    ) -> bool:
        """Update file status and optionally download URL"""
        self._record_call(
            "update_file_status",
            file_id=file_id,
            user_id=user_id,
            status=status,
            download_url=download_url
        )
        self._check_error()

        file = self._files.get(file_id)
        if file and file.user_id == user_id:
            file.status = status
            file.updated_at = datetime.now(timezone.utc)
            if download_url:
                file.download_url = download_url
                file.download_url_expires_at = download_url_expires_at
            return True
        return False

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Soft delete a file (set status to deleted)"""
        self._record_call("delete_file", file_id=file_id, user_id=user_id)
        self._check_error()

        file = self._files.get(file_id)
        if file and file.user_id == user_id:
            file.status = FileStatus.DELETED
            file.updated_at = datetime.now(timezone.utc)

            # Update quota
            quota_key = ("user", user_id)
            if quota_key in self._quotas:
                quota = self._quotas[quota_key]
                quota.used_bytes = max(0, (quota.used_bytes or 0) - file.file_size)
                quota.file_count = max(0, (quota.file_count or 0) - 1)

            return True
        return False

    # ========================================================================
    # File Share Operations
    # ========================================================================

    async def create_file_share(self, share_data: FileShare) -> Optional[FileShare]:
        """Create a new file share record"""
        self._record_call("create_file_share", share_data=share_data)
        self._check_error()

        self._shares[share_data.share_id] = share_data
        return share_data

    async def get_file_share(
        self,
        share_id: Optional[str] = None,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[FileShare]:
        """Get file share by share_id or file_id + user_id"""
        self._record_call(
            "get_file_share",
            share_id=share_id,
            file_id=file_id,
            user_id=user_id
        )
        self._check_error()

        if share_id:
            share = self._shares.get(share_id)
            if share and share.is_active:
                return share
        elif file_id and user_id:
            for share in self._shares.values():
                if share.file_id == file_id and share.shared_with == user_id and share.is_active:
                    return share
        return None

    async def list_file_shares(
        self,
        file_id: Optional[str] = None,
        shared_by: Optional[str] = None,
        shared_with: Optional[str] = None
    ) -> List[FileShare]:
        """List file shares with optional filters"""
        self._record_call(
            "list_file_shares",
            file_id=file_id,
            shared_by=shared_by,
            shared_with=shared_with
        )
        self._check_error()

        shares = [s for s in self._shares.values() if s.is_active]

        if file_id:
            shares = [s for s in shares if s.file_id == file_id]

        if shared_by:
            shares = [s for s in shares if s.shared_by == shared_by]

        if shared_with:
            shares = [s for s in shares if s.shared_with == shared_with]

        # Sort by created_at descending
        shares.sort(key=lambda s: s.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        return shares

    async def increment_share_download(self, share_id: str) -> bool:
        """Increment download count and update accessed_at for a share"""
        self._record_call("increment_share_download", share_id=share_id)
        self._check_error()

        share = self._shares.get(share_id)
        if share:
            share.download_count = (share.download_count or 0) + 1
            share.accessed_at = datetime.now(timezone.utc)
            return True
        return False

    # ========================================================================
    # Storage Quota Operations
    # ========================================================================

    async def get_storage_quota(
        self,
        quota_type: str,
        entity_id: str
    ) -> Optional[StorageQuota]:
        """Get storage quota for user or organization"""
        self._record_call(
            "get_storage_quota",
            quota_type=quota_type,
            entity_id=entity_id
        )
        self._check_error()

        key = (quota_type, entity_id)
        return self._quotas.get(key)

    async def create_storage_quota(
        self,
        quota_type: str,
        entity_id: str,
        total_quota_bytes: int = 10737418240,  # 10GB default
        max_file_size: int = 104857600,  # 100MB default
        max_file_count: int = 10000
    ) -> Optional[StorageQuota]:
        """Create a new storage quota record"""
        self._record_call(
            "create_storage_quota",
            quota_type=quota_type,
            entity_id=entity_id,
            total_quota_bytes=total_quota_bytes
        )
        self._check_error()

        quota = StorageQuota(
            quota_type=quota_type,
            entity_id=entity_id,
            total_quota_bytes=total_quota_bytes,
            used_bytes=0,
            file_count=0,
            max_file_size=max_file_size,
            max_file_count=max_file_count,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        key = (quota_type, entity_id)
        self._quotas[key] = quota
        return quota

    async def update_storage_usage(
        self,
        quota_type: str,
        entity_id: str,
        bytes_delta: int,
        file_count_delta: int = 0
    ) -> bool:
        """Update storage usage (add or subtract bytes and file count)"""
        self._record_call(
            "update_storage_usage",
            quota_type=quota_type,
            entity_id=entity_id,
            bytes_delta=bytes_delta,
            file_count_delta=file_count_delta
        )
        self._check_error()

        key = (quota_type, entity_id)

        # Create quota if not exists
        if key not in self._quotas:
            await self.create_storage_quota(quota_type, entity_id)

        quota = self._quotas.get(key)
        if quota:
            quota.used_bytes = (quota.used_bytes or 0) + bytes_delta
            quota.file_count = (quota.file_count or 0) + file_count_delta
            quota.updated_at = datetime.now(timezone.utc)
            return True
        return False

    async def get_storage_stats(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get storage statistics for user and optionally organization"""
        self._record_call(
            "get_storage_stats",
            user_id=user_id,
            organization_id=organization_id
        )
        self._check_error()

        stats = {
            "user_quota": None,
            "org_quota": None,
            "total_files": 0,
            "total_size": 0
        }

        # Get user quota
        user_quota = await self.get_storage_quota("user", user_id)
        if user_quota:
            used_bytes = user_quota.used_bytes or 0
            total_quota_bytes = user_quota.total_quota_bytes or 0
            stats["user_quota"] = {
                "used_bytes": used_bytes,
                "total_quota_bytes": total_quota_bytes,
                "file_count": user_quota.file_count or 0,
                "max_file_count": user_quota.max_file_count,
                "usage_percent": (used_bytes / total_quota_bytes * 100) if total_quota_bytes > 0 else 0
            }

        # Get org quota if organization_id provided
        if organization_id:
            org_quota = await self.get_storage_quota("organization", organization_id)
            if org_quota:
                used_bytes = org_quota.used_bytes or 0
                total_quota_bytes = org_quota.total_quota_bytes or 0
                stats["org_quota"] = {
                    "used_bytes": used_bytes,
                    "total_quota_bytes": total_quota_bytes,
                    "file_count": org_quota.file_count or 0,
                    "max_file_count": org_quota.max_file_count,
                    "usage_percent": (used_bytes / total_quota_bytes * 100) if total_quota_bytes > 0 else 0
                }

        # Count actual files
        active_files = [
            f for f in self._files.values()
            if f.user_id == user_id and f.status == FileStatus.AVAILABLE
        ]
        stats["total_files"] = len(active_files)
        stats["total_size"] = sum(f.file_size for f in active_files)

        return stats

    # ========================================================================
    # Utility Methods
    # ========================================================================

    async def check_connection(self) -> bool:
        """Check database connection"""
        self._record_call("check_connection")
        self._check_error()
        return True
