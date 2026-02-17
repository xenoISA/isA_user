"""
Storage Service Data Contract

Defines canonical data structures for storage service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for storage service test data.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Import from production models for type consistency
from microservices.storage_service.models import (
    FileStatus,
    FileAccessLevel,
    StorageProvider,
)


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class FileUploadRequestContract(BaseModel):
    """
    Contract: File upload request schema

    Used for creating file upload requests in tests.
    Maps to FastAPI multipart/form-data parameters.
    """
    user_id: str = Field(..., min_length=1, description="User ID who owns the file")
    organization_id: Optional[str] = Field(None, description="Organization ID (optional)")
    access_level: FileAccessLevel = Field(FileAccessLevel.PRIVATE, description="File access level")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")
    tags: Optional[List[str]] = Field(default_factory=list, description="File tags")
    auto_delete_after_days: Optional[int] = Field(None, ge=1, le=365, description="Auto-delete after N days")
    enable_indexing: bool = Field(True, description="Enable auto-indexing for RAG")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "organization_id": "org_456",
                "access_level": "private",
                "metadata": {"source": "mobile_app"},
                "tags": ["photo", "vacation"],
                "auto_delete_after_days": 30,
                "enable_indexing": True,
            }
        }


class FileShareRequestContract(BaseModel):
    """
    Contract: File share request schema

    Used for creating file share requests in tests.
    """
    file_id: str = Field(..., description="File ID to share")
    shared_by: str = Field(..., description="User ID who shares the file")
    shared_with: Optional[str] = Field(None, description="User ID to share with")
    shared_with_email: Optional[str] = Field(None, description="Email to share with")
    permissions: Dict[str, bool] = Field(
        default_factory=lambda: {"view": True, "download": False, "delete": False},
        description="Permission settings"
    )
    password: Optional[str] = Field(None, min_length=4, description="Access password")
    expires_hours: int = Field(24, ge=1, le=720, description="Expiration in hours (max 30 days)")
    max_downloads: Optional[int] = Field(None, ge=1, description="Maximum download count")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_abc123",
                "shared_by": "user_123",
                "shared_with_email": "friend@example.com",
                "permissions": {"view": True, "download": True, "delete": False},
                "password": "secret",
                "expires_hours": 48,
                "max_downloads": 5,
            }
        }


class FileListRequestContract(BaseModel):
    """
    Contract: File list request schema

    Used for listing files in tests.
    """
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID filter")
    prefix: Optional[str] = Field(None, description="File path prefix filter")
    status: Optional[FileStatus] = Field(None, description="File status filter")
    limit: int = Field(100, ge=1, le=1000, description="Result limit")
    offset: int = Field(0, ge=0, description="Result offset")


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class FileUploadResponseContract(BaseModel):
    """
    Contract: File upload response schema

    Validates API response structure for file uploads.
    """
    file_id: str = Field(..., pattern=r"^file_[0-9a-f]{32}$", description="Generated file ID")
    file_path: str = Field(..., description="Storage path")
    download_url: str = Field(..., description="Presigned download URL")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    content_type: str = Field(..., description="MIME type")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    message: str = Field(default="File uploaded successfully", description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_abc123def456",
                "file_path": "users/user_123/2025/12/10/20251210_120000_abc123.jpg",
                "download_url": "https://minio.example.com/presigned-url",
                "file_size": 1048576,
                "content_type": "image/jpeg",
                "uploaded_at": "2025-12-10T12:00:00Z",
                "message": "File uploaded successfully",
            }
        }


class FileInfoResponseContract(BaseModel):
    """
    Contract: File info response schema

    Validates API response structure for file details.
    """
    file_id: str = Field(..., description="File ID")
    user_id: Optional[str] = Field(None, description="Owner user ID")  # GOLDEN: API doesn't always return this
    file_name: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Storage path")
    file_size: int = Field(..., ge=0, description="File size")
    content_type: str = Field(..., description="MIME type")
    status: FileStatus = Field(..., description="File status")
    access_level: FileAccessLevel = Field(..., description="Access level")
    download_url: Optional[str] = Field(None, description="Download URL")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags")
    uploaded_at: datetime = Field(..., description="Upload time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class FileShareResponseContract(BaseModel):
    """
    Contract: File share response schema

    Validates API response structure for file shares.
    """
    share_id: str = Field(..., pattern=r"^share_[0-9a-f]{12}$", description="Share ID")
    file_id: Optional[str] = Field(None, description="File ID that was shared")  # GOLDEN: API doesn't return this
    shared_by: Optional[str] = Field(None, description="User who shared the file")  # GOLDEN: API doesn't return this
    share_url: str = Field(..., description="Share URL")
    access_token: Optional[str] = Field(None, description="Access token (if no password)")
    expires_at: datetime = Field(..., description="Expiration time")
    permissions: Dict[str, bool] = Field(..., description="Permission settings")
    message: str = Field(default="File shared successfully", description="Success message")


class StorageStatsResponseContract(BaseModel):
    """
    Contract: Storage stats response schema

    Validates API response structure for storage statistics.
    """
    user_id: Optional[str] = Field(None, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    total_quota_bytes: int = Field(..., ge=0, description="Total quota")
    used_bytes: int = Field(..., ge=0, description="Used storage")
    available_bytes: int = Field(..., ge=0, description="Available storage")
    usage_percentage: float = Field(..., ge=0, le=100, description="Usage percentage")
    file_count: int = Field(..., ge=0, description="Number of files")
    by_type: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Stats by file type")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Stats by status")


# ============================================================================
# Test Data Factory
# ============================================================================

class StorageTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    @staticmethod
    def make_user_id() -> str:
        """Generate unique test user ID"""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_file_id() -> str:
        """Generate valid file ID"""
        return f"file_{uuid.uuid4().hex[:32]}"

    @staticmethod
    def make_share_id() -> str:
        """Generate valid share ID"""
        return f"share_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_upload_request(**overrides) -> FileUploadRequestContract:
        """
        Create valid file upload request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            FileUploadRequestContract with valid data

        Example:
            request = StorageTestDataFactory.make_upload_request(
                user_id="user_123",
                access_level=FileAccessLevel.PUBLIC,
            )
        """
        defaults = {
            "user_id": StorageTestDataFactory.make_user_id(),
            "organization_id": None,
            "access_level": FileAccessLevel.PRIVATE,
            "metadata": {"test": True, "source": "pytest"},
            "tags": ["test", "automated"],
            "auto_delete_after_days": None,
            "enable_indexing": True,
        }
        defaults.update(overrides)
        return FileUploadRequestContract(**defaults)

    @staticmethod
    def make_share_request(**overrides) -> FileShareRequestContract:
        """
        Create valid file share request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            FileShareRequestContract with valid data
        """
        defaults = {
            "file_id": StorageTestDataFactory.make_file_id(),
            "shared_by": StorageTestDataFactory.make_user_id(),
            "shared_with": None,
            "shared_with_email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "permissions": {"view": True, "download": True, "delete": False},
            "password": None,
            "expires_hours": 24,
            "max_downloads": None,
        }
        defaults.update(overrides)
        return FileShareRequestContract(**defaults)

    @staticmethod
    def make_list_request(**overrides) -> FileListRequestContract:
        """Create valid file list request"""
        defaults = {
            "user_id": StorageTestDataFactory.make_user_id(),
            "organization_id": None,
            "prefix": None,
            "status": None,
            "limit": 100,
            "offset": 0,
        }
        defaults.update(overrides)
        return FileListRequestContract(**defaults)

    @staticmethod
    def make_upload_response(**overrides) -> FileUploadResponseContract:
        """
        Create expected file upload response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "file_id": StorageTestDataFactory.make_file_id(),
            "file_path": f"users/{StorageTestDataFactory.make_user_id()}/2025/12/10/test.jpg",
            "download_url": "https://minio.example.com/presigned-url",
            "file_size": 1024 * 1024,  # 1MB
            "content_type": "image/jpeg",
            "uploaded_at": datetime.now(timezone.utc),
            "message": "File uploaded successfully",
        }
        defaults.update(overrides)
        return FileUploadResponseContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_upload_request_missing_user_id() -> dict:
        """Generate upload request missing required user_id"""
        return {
            "access_level": "private",
            "metadata": {},
            "tags": [],
        }

    @staticmethod
    def make_invalid_upload_request_invalid_access_level() -> dict:
        """Generate upload request with invalid access_level"""
        return {
            "user_id": "user_123",
            "access_level": "invalid_level",  # Invalid enum value
        }

    @staticmethod
    def make_invalid_share_request_missing_file_id() -> dict:
        """Generate share request missing required file_id"""
        return {
            "shared_by": "user_123",
            "expires_hours": 24,
        }


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class FileUploadRequestBuilder:
    """
    Builder pattern for creating complex file upload requests.

    Useful for tests that need to gradually construct requests.

    Example:
        request = (
            FileUploadRequestBuilder()
            .with_user("user_123")
            .with_public_access()
            .with_tags(["photo", "vacation"])
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "user_id": StorageTestDataFactory.make_user_id(),
            "access_level": FileAccessLevel.PRIVATE,
            "metadata": {},
            "tags": [],
            "enable_indexing": True,
        }

    def with_user(self, user_id: str) -> "FileUploadRequestBuilder":
        """Set user ID"""
        self._data["user_id"] = user_id
        return self

    def with_organization(self, org_id: str) -> "FileUploadRequestBuilder":
        """Set organization ID"""
        self._data["organization_id"] = org_id
        return self

    def with_public_access(self) -> "FileUploadRequestBuilder":
        """Set access level to public"""
        self._data["access_level"] = FileAccessLevel.PUBLIC
        return self

    def with_private_access(self) -> "FileUploadRequestBuilder":
        """Set access level to private"""
        self._data["access_level"] = FileAccessLevel.PRIVATE
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "FileUploadRequestBuilder":
        """Add metadata"""
        self._data["metadata"] = metadata
        return self

    def with_tags(self, tags: List[str]) -> "FileUploadRequestBuilder":
        """Add tags"""
        self._data["tags"] = tags
        return self

    def with_auto_delete(self, days: int) -> "FileUploadRequestBuilder":
        """Set auto-delete after N days"""
        self._data["auto_delete_after_days"] = days
        return self

    def without_indexing(self) -> "FileUploadRequestBuilder":
        """Disable indexing"""
        self._data["enable_indexing"] = False
        return self

    def build(self) -> FileUploadRequestContract:
        """Build the final request"""
        return FileUploadRequestContract(**self._data)


class FileShareRequestBuilder:
    """
    Builder pattern for creating complex file share requests.

    Example:
        request = (
            FileShareRequestBuilder()
            .for_file("file_123")
            .shared_by("user_456")
            .with_email("friend@example.com")
            .with_password("secret")
            .with_download_permission()
            .expires_in_hours(48)
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "file_id": StorageTestDataFactory.make_file_id(),
            "shared_by": StorageTestDataFactory.make_user_id(),
            "permissions": {"view": True, "download": False, "delete": False},
            "expires_hours": 24,
        }

    def for_file(self, file_id: str) -> "FileShareRequestBuilder":
        """Set file ID"""
        self._data["file_id"] = file_id
        return self

    def shared_by(self, user_id: str) -> "FileShareRequestBuilder":
        """Set sharing user"""
        self._data["shared_by"] = user_id
        return self

    def with_user(self, user_id: str) -> "FileShareRequestBuilder":
        """Share with specific user"""
        self._data["shared_with"] = user_id
        return self

    def with_email(self, email: str) -> "FileShareRequestBuilder":
        """Share with email"""
        self._data["shared_with_email"] = email
        return self

    def with_password(self, password: str) -> "FileShareRequestBuilder":
        """Require password"""
        self._data["password"] = password
        return self

    def with_download_permission(self) -> "FileShareRequestBuilder":
        """Allow download"""
        self._data["permissions"]["download"] = True
        return self

    def with_delete_permission(self) -> "FileShareRequestBuilder":
        """Allow delete (dangerous!)"""
        self._data["permissions"]["delete"] = True
        return self

    def expires_in_hours(self, hours: int) -> "FileShareRequestBuilder":
        """Set expiration"""
        self._data["expires_hours"] = hours
        return self

    def with_max_downloads(self, count: int) -> "FileShareRequestBuilder":
        """Limit downloads"""
        self._data["max_downloads"] = count
        return self

    def build(self) -> FileShareRequestContract:
        """Build the final request"""
        return FileShareRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Request Contracts
    "FileUploadRequestContract",
    "FileShareRequestContract",
    "FileListRequestContract",

    # Response Contracts
    "FileUploadResponseContract",
    "FileInfoResponseContract",
    "FileShareResponseContract",
    "StorageStatsResponseContract",

    # Factory
    "StorageTestDataFactory",

    # Builders
    "FileUploadRequestBuilder",
    "FileShareRequestBuilder",
]
