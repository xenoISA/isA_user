"""
Unit Golden Tests: Storage Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.storage_service.models import (
    FileStatus,
    StorageProvider,
    FileAccessLevel,
    StoredFile,
    FileShare,
    StorageQuota,
    FileUploadRequest,
    FileUploadResponse,
    FileListRequest,
    FileInfoResponse,
    FileShareRequest,
    FileShareResponse,
    StorageStatsResponse,
)


class TestFileStatus:
    """Test FileStatus enum"""

    def test_file_status_values(self):
        """Test all file status values are defined"""
        assert FileStatus.UPLOADING.value == "uploading"
        assert FileStatus.AVAILABLE.value == "available"
        assert FileStatus.DELETED.value == "deleted"
        assert FileStatus.FAILED.value == "failed"
        assert FileStatus.ARCHIVED.value == "archived"

    def test_file_status_comparison(self):
        """Test file status comparison"""
        assert FileStatus.UPLOADING.value == "uploading"
        assert FileStatus.AVAILABLE != FileStatus.DELETED
        assert FileStatus.AVAILABLE.value == "available"


class TestStorageProvider:
    """Test StorageProvider enum"""

    def test_storage_provider_values(self):
        """Test all storage provider values"""
        assert StorageProvider.MINIO.value == "minio"
        assert StorageProvider.S3.value == "s3"
        assert StorageProvider.AZURE.value == "azure"
        assert StorageProvider.GCS.value == "gcs"
        assert StorageProvider.LOCAL.value == "local"

    def test_storage_provider_comparison(self):
        """Test storage provider comparison"""
        assert StorageProvider.MINIO != StorageProvider.S3
        assert StorageProvider.S3.value == "s3"


class TestFileAccessLevel:
    """Test FileAccessLevel enum"""

    def test_file_access_level_values(self):
        """Test all file access level values"""
        assert FileAccessLevel.PUBLIC.value == "public"
        assert FileAccessLevel.PRIVATE.value == "private"
        assert FileAccessLevel.RESTRICTED.value == "restricted"
        assert FileAccessLevel.SHARED.value == "shared"

    def test_file_access_level_comparison(self):
        """Test file access level comparison"""
        assert FileAccessLevel.PUBLIC != FileAccessLevel.PRIVATE
        assert FileAccessLevel.PRIVATE.value == "private"


class TestStoredFile:
    """Test StoredFile model validation"""

    def test_stored_file_creation_with_all_fields(self):
        """Test creating stored file with all fields"""
        now = datetime.now(timezone.utc)

        file = StoredFile(
            id=1,
            file_id="file_123",
            user_id="user_456",
            organization_id="org_789",
            file_name="test_document.pdf",
            file_path="/uploads/2024/12/test_document.pdf",
            file_size=1024000,
            content_type="application/pdf",
            file_extension="pdf",
            storage_provider=StorageProvider.MINIO,
            bucket_name="user-files",
            object_name="user_456/test_document.pdf",
            status=FileStatus.AVAILABLE,
            access_level=FileAccessLevel.PRIVATE,
            checksum="abc123def456",
            etag="etag_xyz",
            version_id="v1",
            metadata={"category": "documents", "year": "2024"},
            tags=["important", "work"],
            download_url="https://storage.example.com/download/file_123",
            download_url_expires_at=now + timedelta(hours=1),
            uploaded_at=now,
            updated_at=now,
            deleted_at=None,
        )

        assert file.file_id == "file_123"
        assert file.user_id == "user_456"
        assert file.organization_id == "org_789"
        assert file.file_name == "test_document.pdf"
        assert file.file_size == 1024000
        assert file.content_type == "application/pdf"
        assert file.storage_provider == StorageProvider.MINIO
        assert file.status == FileStatus.AVAILABLE
        assert file.access_level == FileAccessLevel.PRIVATE
        assert file.checksum == "abc123def456"
        assert len(file.metadata) == 2
        assert len(file.tags) == 2

    def test_stored_file_with_minimal_fields(self):
        """Test creating stored file with only required fields"""
        file = StoredFile(
            file_id="file_minimal",
            user_id="user_123",
            file_name="simple.txt",
            file_path="/uploads/simple.txt",
            file_size=256,
            content_type="text/plain",
            bucket_name="default-bucket",
            object_name="simple.txt",
        )

        assert file.file_id == "file_minimal"
        assert file.user_id == "user_123"
        assert file.file_name == "simple.txt"
        assert file.file_size == 256
        assert file.storage_provider == StorageProvider.MINIO
        assert file.status == FileStatus.AVAILABLE
        assert file.access_level == FileAccessLevel.PRIVATE
        assert file.organization_id is None
        assert file.metadata == {}
        assert file.tags == []

    def test_stored_file_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            StoredFile(user_id="user_123", file_name="test.txt")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "file_id" in missing_fields
        assert "file_path" in missing_fields
        assert "file_size" in missing_fields
        assert "content_type" in missing_fields
        assert "bucket_name" in missing_fields
        assert "object_name" in missing_fields

    def test_stored_file_with_metadata_and_tags(self):
        """Test stored file with metadata and tags"""
        file = StoredFile(
            file_id="file_meta",
            user_id="user_123",
            file_name="photo.jpg",
            file_path="/photos/photo.jpg",
            file_size=512000,
            content_type="image/jpeg",
            bucket_name="photos",
            object_name="photo.jpg",
            metadata={
                "camera": "Canon EOS",
                "location": "New York",
                "date_taken": "2024-12-15",
            },
            tags=["vacation", "family", "2024"],
        )

        assert len(file.metadata) == 3
        assert file.metadata["camera"] == "Canon EOS"
        assert len(file.tags) == 3
        assert "vacation" in file.tags

    def test_stored_file_with_different_providers(self):
        """Test stored file with different storage providers"""
        # Test S3
        s3_file = StoredFile(
            file_id="s3_file",
            user_id="user_123",
            file_name="s3_doc.pdf",
            file_path="/s3/doc.pdf",
            file_size=1024,
            content_type="application/pdf",
            storage_provider=StorageProvider.S3,
            bucket_name="aws-bucket",
            object_name="doc.pdf",
        )
        assert s3_file.storage_provider == StorageProvider.S3

        # Test Azure
        azure_file = StoredFile(
            file_id="azure_file",
            user_id="user_123",
            file_name="azure_doc.pdf",
            file_path="/azure/doc.pdf",
            file_size=1024,
            content_type="application/pdf",
            storage_provider=StorageProvider.AZURE,
            bucket_name="azure-container",
            object_name="doc.pdf",
        )
        assert azure_file.storage_provider == StorageProvider.AZURE

    def test_stored_file_with_different_statuses(self):
        """Test stored file with different status values"""
        for status in [
            FileStatus.UPLOADING,
            FileStatus.AVAILABLE,
            FileStatus.DELETED,
            FileStatus.FAILED,
            FileStatus.ARCHIVED,
        ]:
            file = StoredFile(
                file_id=f"file_{status.value}",
                user_id="user_123",
                file_name="test.txt",
                file_path="/test.txt",
                file_size=100,
                content_type="text/plain",
                bucket_name="bucket",
                object_name="test.txt",
                status=status,
            )
            assert file.status == status


class TestFileShare:
    """Test FileShare model validation"""

    def test_file_share_creation_with_all_fields(self):
        """Test creating file share with all fields"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)

        share = FileShare(
            id=1,
            share_id="share_123",
            file_id="file_456",
            shared_by="user_789",
            shared_with="user_101",
            shared_with_email="user@example.com",
            access_token="token_abc123",
            password="secret123",
            permissions={"view": True, "download": True, "delete": False},
            max_downloads=10,
            download_count=3,
            expires_at=expires,
            is_active=True,
            created_at=now,
            accessed_at=now,
        )

        assert share.share_id == "share_123"
        assert share.file_id == "file_456"
        assert share.shared_by == "user_789"
        assert share.shared_with == "user_101"
        assert share.shared_with_email == "user@example.com"
        assert share.access_token == "token_abc123"
        assert share.permissions["view"] is True
        assert share.permissions["download"] is True
        assert share.max_downloads == 10
        assert share.download_count == 3
        assert share.is_active is True

    def test_file_share_with_minimal_fields(self):
        """Test creating file share with only required fields"""
        share = FileShare(
            share_id="share_minimal",
            file_id="file_123",
            shared_by="user_456",
        )

        assert share.share_id == "share_minimal"
        assert share.file_id == "file_123"
        assert share.shared_by == "user_456"
        assert share.shared_with is None
        assert share.shared_with_email is None
        assert share.permissions == {"view": True, "download": False, "delete": False}
        assert share.download_count == 0
        assert share.is_active is True
        assert share.max_downloads is None

    def test_file_share_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            FileShare(shared_by="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "share_id" in missing_fields
        assert "file_id" in missing_fields

    def test_file_share_with_custom_permissions(self):
        """Test file share with custom permission configurations"""
        # View only
        share_view = FileShare(
            share_id="share_view",
            file_id="file_123",
            shared_by="user_456",
            permissions={"view": True, "download": False, "delete": False},
        )
        assert share_view.permissions["view"] is True
        assert share_view.permissions["download"] is False

        # View and download
        share_download = FileShare(
            share_id="share_download",
            file_id="file_123",
            shared_by="user_456",
            permissions={"view": True, "download": True, "delete": False},
        )
        assert share_download.permissions["download"] is True

    def test_file_share_with_expiration(self):
        """Test file share with expiration date"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)

        share = FileShare(
            share_id="share_expires",
            file_id="file_123",
            shared_by="user_456",
            expires_at=expires,
        )

        assert share.expires_at == expires
        assert share.expires_at > now

    def test_file_share_with_download_limit(self):
        """Test file share with download limits"""
        share = FileShare(
            share_id="share_limited",
            file_id="file_123",
            shared_by="user_456",
            max_downloads=5,
            download_count=0,
        )

        assert share.max_downloads == 5
        assert share.download_count == 0

        # Simulate downloads
        share.download_count = 3
        assert share.download_count == 3
        assert share.download_count < share.max_downloads


class TestStorageQuota:
    """Test StorageQuota model validation"""

    def test_storage_quota_creation_with_all_fields(self):
        """Test creating storage quota with all fields"""
        now = datetime.now(timezone.utc)

        quota = StorageQuota(
            id=1,
            user_id="user_123",
            organization_id="org_456",
            total_quota_bytes=10737418240,  # 10 GB
            used_bytes=2147483648,  # 2 GB
            file_count=150,
            max_file_size=104857600,  # 100 MB
            max_file_count=1000,
            allowed_extensions=["jpg", "png", "pdf", "doc", "txt"],
            blocked_extensions=["exe", "bat", "sh"],
            is_active=True,
            updated_at=now,
        )

        assert quota.user_id == "user_123"
        assert quota.organization_id == "org_456"
        assert quota.total_quota_bytes == 10737418240
        assert quota.used_bytes == 2147483648
        assert quota.file_count == 150
        assert quota.max_file_size == 104857600
        assert quota.max_file_count == 1000
        assert len(quota.allowed_extensions) == 5
        assert len(quota.blocked_extensions) == 3
        assert quota.is_active is True

    def test_storage_quota_with_minimal_fields(self):
        """Test creating storage quota with only required fields"""
        quota = StorageQuota(
            total_quota_bytes=5368709120,  # 5 GB
        )

        assert quota.total_quota_bytes == 5368709120
        assert quota.used_bytes == 0
        assert quota.file_count == 0
        assert quota.user_id is None
        assert quota.organization_id is None
        assert quota.max_file_size is None
        assert quota.allowed_extensions is None
        assert quota.is_active is True

    def test_storage_quota_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            StorageQuota(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "total_quota_bytes" in missing_fields

    def test_storage_quota_for_user(self):
        """Test storage quota for individual user"""
        quota = StorageQuota(
            user_id="user_123",
            total_quota_bytes=5368709120,  # 5 GB
            used_bytes=1073741824,  # 1 GB
            file_count=50,
        )

        assert quota.user_id == "user_123"
        assert quota.organization_id is None
        remaining = quota.total_quota_bytes - quota.used_bytes
        assert remaining == 4294967296  # 4 GB remaining

    def test_storage_quota_for_organization(self):
        """Test storage quota for organization"""
        quota = StorageQuota(
            organization_id="org_456",
            total_quota_bytes=53687091200,  # 50 GB
            used_bytes=10737418240,  # 10 GB
            file_count=500,
        )

        assert quota.organization_id == "org_456"
        assert quota.user_id is None
        remaining = quota.total_quota_bytes - quota.used_bytes
        assert remaining == 42949672960  # 40 GB remaining

    def test_storage_quota_with_file_restrictions(self):
        """Test storage quota with file type and size restrictions"""
        quota = StorageQuota(
            user_id="user_123",
            total_quota_bytes=5368709120,
            max_file_size=52428800,  # 50 MB max
            max_file_count=500,
            allowed_extensions=["jpg", "png", "gif", "pdf"],
            blocked_extensions=["exe", "bat", "cmd"],
        )

        assert quota.max_file_size == 52428800
        assert quota.max_file_count == 500
        assert "jpg" in quota.allowed_extensions
        assert "exe" in quota.blocked_extensions


class TestFileUploadRequest:
    """Test FileUploadRequest model validation"""

    def test_file_upload_request_minimal(self):
        """Test minimal file upload request"""
        request = FileUploadRequest(user_id="user_123")

        assert request.user_id == "user_123"
        assert request.organization_id is None
        assert request.access_level == FileAccessLevel.PRIVATE
        assert request.metadata is None
        assert request.tags is None
        assert request.auto_delete_after_days is None
        assert request.enable_indexing is True

    def test_file_upload_request_with_all_fields(self):
        """Test file upload request with all fields"""
        request = FileUploadRequest(
            user_id="user_123",
            organization_id="org_456",
            access_level=FileAccessLevel.SHARED,
            metadata={"category": "documents", "project": "Q4"},
            tags=["important", "confidential"],
            auto_delete_after_days=30,
            enable_indexing=True,
        )

        assert request.user_id == "user_123"
        assert request.organization_id == "org_456"
        assert request.access_level == FileAccessLevel.SHARED
        assert request.metadata["category"] == "documents"
        assert len(request.tags) == 2
        assert request.auto_delete_after_days == 30
        assert request.enable_indexing is True

    def test_file_upload_request_with_public_access(self):
        """Test file upload request with public access level"""
        request = FileUploadRequest(
            user_id="user_123", access_level=FileAccessLevel.PUBLIC
        )

        assert request.access_level == FileAccessLevel.PUBLIC

    def test_file_upload_request_with_indexing_disabled(self):
        """Test file upload request with indexing disabled"""
        request = FileUploadRequest(user_id="user_123", enable_indexing=False)

        assert request.enable_indexing is False

    def test_file_upload_request_missing_user_id(self):
        """Test that missing user_id raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            FileUploadRequest()

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "user_id" in missing_fields


class TestFileUploadResponse:
    """Test FileUploadResponse model"""

    def test_file_upload_response_creation(self):
        """Test creating file upload response"""
        now = datetime.now(timezone.utc)

        response = FileUploadResponse(
            file_id="file_123",
            file_path="/uploads/2024/12/document.pdf",
            download_url="https://storage.example.com/download/file_123",
            file_size=1024000,
            content_type="application/pdf",
            uploaded_at=now,
            message="File uploaded successfully",
        )

        assert response.file_id == "file_123"
        assert response.file_path == "/uploads/2024/12/document.pdf"
        assert response.download_url == "https://storage.example.com/download/file_123"
        assert response.file_size == 1024000
        assert response.content_type == "application/pdf"
        assert response.uploaded_at == now
        assert response.message == "File uploaded successfully"

    def test_file_upload_response_default_message(self):
        """Test file upload response with default message"""
        now = datetime.now(timezone.utc)

        response = FileUploadResponse(
            file_id="file_456",
            file_path="/uploads/photo.jpg",
            download_url="https://storage.example.com/download/file_456",
            file_size=512000,
            content_type="image/jpeg",
            uploaded_at=now,
        )

        assert response.message == "File uploaded successfully"


class TestFileListRequest:
    """Test FileListRequest model validation"""

    def test_file_list_request_defaults(self):
        """Test default file list request parameters"""
        request = FileListRequest(user_id="user_123")

        assert request.user_id == "user_123"
        assert request.organization_id is None
        assert request.prefix is None
        assert request.status is None
        assert request.limit == 100
        assert request.offset == 0

    def test_file_list_request_with_filters(self):
        """Test file list request with filters"""
        request = FileListRequest(
            user_id="user_123",
            organization_id="org_456",
            prefix="/documents",
            status=FileStatus.AVAILABLE,
            limit=50,
            offset=10,
        )

        assert request.user_id == "user_123"
        assert request.organization_id == "org_456"
        assert request.prefix == "/documents"
        assert request.status == FileStatus.AVAILABLE
        assert request.limit == 50
        assert request.offset == 10

    def test_file_list_request_limit_validation(self):
        """Test limit validation (min/max constraints)"""
        # Test minimum limit
        with pytest.raises(ValidationError):
            FileListRequest(user_id="user_123", limit=0)

        # Test maximum limit
        with pytest.raises(ValidationError):
            FileListRequest(user_id="user_123", limit=1001)

        # Test valid limits
        request_min = FileListRequest(user_id="user_123", limit=1)
        assert request_min.limit == 1

        request_max = FileListRequest(user_id="user_123", limit=1000)
        assert request_max.limit == 1000

    def test_file_list_request_offset_validation(self):
        """Test offset validation (non-negative)"""
        with pytest.raises(ValidationError):
            FileListRequest(user_id="user_123", offset=-1)

        # Test valid offset
        request = FileListRequest(user_id="user_123", offset=0)
        assert request.offset == 0


class TestFileInfoResponse:
    """Test FileInfoResponse model"""

    def test_file_info_response_creation(self):
        """Test creating file info response"""
        now = datetime.now(timezone.utc)

        response = FileInfoResponse(
            file_id="file_123",
            file_name="document.pdf",
            file_path="/uploads/2024/12/document.pdf",
            file_size=1024000,
            content_type="application/pdf",
            status=FileStatus.AVAILABLE,
            access_level=FileAccessLevel.PRIVATE,
            download_url="https://storage.example.com/download/file_123",
            metadata={"category": "documents"},
            tags=["important", "work"],
            uploaded_at=now,
            updated_at=now,
        )

        assert response.file_id == "file_123"
        assert response.file_name == "document.pdf"
        assert response.file_size == 1024000
        assert response.content_type == "application/pdf"
        assert response.status == FileStatus.AVAILABLE
        assert response.access_level == FileAccessLevel.PRIVATE
        assert response.download_url is not None
        assert len(response.metadata) == 1
        assert len(response.tags) == 2

    def test_file_info_response_without_optional_fields(self):
        """Test file info response without optional fields"""
        now = datetime.now(timezone.utc)

        response = FileInfoResponse(
            file_id="file_456",
            file_name="simple.txt",
            file_path="/uploads/simple.txt",
            file_size=256,
            content_type="text/plain",
            status=FileStatus.AVAILABLE,
            access_level=FileAccessLevel.PRIVATE,
            uploaded_at=now,
        )

        assert response.file_id == "file_456"
        assert response.download_url is None
        assert response.metadata is None
        assert response.tags is None
        assert response.updated_at is None


class TestFileShareRequest:
    """Test FileShareRequest model validation"""

    def test_file_share_request_minimal(self):
        """Test minimal file share request"""
        request = FileShareRequest(file_id="file_123", shared_by="user_456")

        assert request.file_id == "file_123"
        assert request.shared_by == "user_456"
        assert request.shared_with is None
        assert request.shared_with_email is None
        assert request.permissions == {"view": True, "download": False, "delete": False}
        assert request.password is None
        assert request.expires_hours == 24
        assert request.max_downloads is None

    def test_file_share_request_with_all_fields(self):
        """Test file share request with all fields"""
        request = FileShareRequest(
            file_id="file_123",
            shared_by="user_456",
            shared_with="user_789",
            shared_with_email="recipient@example.com",
            permissions={"view": True, "download": True, "delete": False},
            password="secret123",
            expires_hours=72,
            max_downloads=10,
        )

        assert request.file_id == "file_123"
        assert request.shared_by == "user_456"
        assert request.shared_with == "user_789"
        assert request.shared_with_email == "recipient@example.com"
        assert request.permissions["download"] is True
        assert request.password == "secret123"
        assert request.expires_hours == 72
        assert request.max_downloads == 10

    def test_file_share_request_expires_hours_validation(self):
        """Test expires_hours validation (min/max constraints)"""
        # Test minimum (1 hour)
        with pytest.raises(ValidationError):
            FileShareRequest(
                file_id="file_123", shared_by="user_456", expires_hours=0
            )

        # Test maximum (720 hours = 30 days)
        with pytest.raises(ValidationError):
            FileShareRequest(
                file_id="file_123", shared_by="user_456", expires_hours=721
            )

        # Test valid values
        request_min = FileShareRequest(
            file_id="file_123", shared_by="user_456", expires_hours=1
        )
        assert request_min.expires_hours == 1

        request_max = FileShareRequest(
            file_id="file_123", shared_by="user_456", expires_hours=720
        )
        assert request_max.expires_hours == 720

    def test_file_share_request_with_custom_permissions(self):
        """Test file share request with custom permissions"""
        # View and download
        request_download = FileShareRequest(
            file_id="file_123",
            shared_by="user_456",
            permissions={"view": True, "download": True, "delete": False},
        )
        assert request_download.permissions["download"] is True

        # All permissions
        request_all = FileShareRequest(
            file_id="file_123",
            shared_by="user_456",
            permissions={"view": True, "download": True, "delete": True},
        )
        assert request_all.permissions["delete"] is True


class TestFileShareResponse:
    """Test FileShareResponse model"""

    def test_file_share_response_creation(self):
        """Test creating file share response"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)

        response = FileShareResponse(
            share_id="share_123",
            share_url="https://storage.example.com/share/share_123",
            access_token="token_abc123",
            expires_at=expires,
            permissions={"view": True, "download": True, "delete": False},
            message="File shared successfully",
        )

        assert response.share_id == "share_123"
        assert response.share_url == "https://storage.example.com/share/share_123"
        assert response.access_token == "token_abc123"
        assert response.expires_at == expires
        assert response.permissions["view"] is True
        assert response.message == "File shared successfully"

    def test_file_share_response_default_message(self):
        """Test file share response with default message"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)

        response = FileShareResponse(
            share_id="share_456",
            share_url="https://storage.example.com/share/share_456",
            expires_at=expires,
            permissions={"view": True, "download": False, "delete": False},
        )

        assert response.message == "File shared successfully"
        assert response.access_token is None


class TestStorageStatsResponse:
    """Test StorageStatsResponse model"""

    def test_storage_stats_response_for_user(self):
        """Test storage stats response for user"""
        response = StorageStatsResponse(
            user_id="user_123",
            total_quota_bytes=10737418240,  # 10 GB
            used_bytes=2147483648,  # 2 GB
            available_bytes=8589934592,  # 8 GB
            usage_percentage=20.0,
            file_count=150,
            by_type={
                "image/jpeg": {"count": 50, "size": 1073741824},
                "application/pdf": {"count": 30, "size": 536870912},
                "video/mp4": {"count": 10, "size": 537395200},
            },
            by_status={
                "available": 140,
                "uploading": 5,
                "archived": 5,
            },
        )

        assert response.user_id == "user_123"
        assert response.organization_id is None
        assert response.total_quota_bytes == 10737418240
        assert response.used_bytes == 2147483648
        assert response.available_bytes == 8589934592
        assert response.usage_percentage == 20.0
        assert response.file_count == 150
        assert len(response.by_type) == 3
        assert response.by_type["image/jpeg"]["count"] == 50
        assert len(response.by_status) == 3

    def test_storage_stats_response_for_organization(self):
        """Test storage stats response for organization"""
        response = StorageStatsResponse(
            organization_id="org_456",
            total_quota_bytes=53687091200,  # 50 GB
            used_bytes=21474836480,  # 20 GB
            available_bytes=32212254720,  # 30 GB
            usage_percentage=40.0,
            file_count=1000,
            by_type={
                "application/pdf": {"count": 500, "size": 10737418240},
                "image/png": {"count": 300, "size": 6442450944},
                "text/plain": {"count": 200, "size": 4294967296},
            },
            by_status={
                "available": 950,
                "uploading": 30,
                "archived": 20,
            },
        )

        assert response.organization_id == "org_456"
        assert response.user_id is None
        assert response.usage_percentage == 40.0
        assert response.file_count == 1000

    def test_storage_stats_response_zero_usage(self):
        """Test storage stats response with zero usage"""
        response = StorageStatsResponse(
            user_id="user_new",
            total_quota_bytes=5368709120,  # 5 GB
            used_bytes=0,
            available_bytes=5368709120,
            usage_percentage=0.0,
            file_count=0,
            by_type={},
            by_status={},
        )

        assert response.used_bytes == 0
        assert response.available_bytes == response.total_quota_bytes
        assert response.usage_percentage == 0.0
        assert response.file_count == 0
        assert len(response.by_type) == 0

    def test_storage_stats_response_full_quota(self):
        """Test storage stats response with full quota"""
        response = StorageStatsResponse(
            user_id="user_full",
            total_quota_bytes=5368709120,  # 5 GB
            used_bytes=5368709120,  # 5 GB
            available_bytes=0,
            usage_percentage=100.0,
            file_count=500,
            by_type={
                "video/mp4": {"count": 500, "size": 5368709120},
            },
            by_status={
                "available": 500,
            },
        )

        assert response.used_bytes == response.total_quota_bytes
        assert response.available_bytes == 0
        assert response.usage_percentage == 100.0


if __name__ == "__main__":
    pytest.main([__file__])
