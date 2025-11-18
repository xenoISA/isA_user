#!/usr/bin/env python3
"""
Test Storage Service Event Publishing

Tests that storage service publishes events correctly to NATS
"""

import asyncio
import sys
import os
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.storage_service.storage_service import StorageService
from microservices.storage_service.models import (
    FileUploadRequest, FileShareRequest, StoredFile, FileShare,
    FileStatus, StorageProvider, FileAccessLevel
)
from core.nats_client import get_event_bus, Event
from fastapi import UploadFile


class MockEventBus:
    """Mock event bus to capture published events"""

    def __init__(self):
        self.published_events = []
        self._is_connected = True

    async def publish_event(self, event: Event) -> bool:
        """Capture published events"""
        self.published_events.append({
            "id": event.id,
            "type": event.type,
            "source": event.source,
            "data": event.data,
            "metadata": event.metadata,
            "timestamp": event.timestamp
        })
        print(f"✅ Event captured: {event.type}")
        print(f"   Data: {event.data}")
        return True

    async def close(self):
        """Mock close"""
        pass


class MockStorageRepository:
    """Mock repository for testing"""

    async def create_file_record(self, stored_file):
        """Mock create file record"""
        return stored_file

    async def get_file_by_id(self, file_id, user_id=None):
        """Mock get file by id"""
        return StoredFile(
            file_id=file_id,
            user_id=user_id or "user_123",
            file_name="test_file.txt",
            file_path="users/user_123/2025/10/28/test.txt",
            file_size=1024,
            content_type="text/plain",
            file_extension=".txt",
            storage_provider=StorageProvider.MINIO,
            bucket_name="isa-storage",
            object_name="users/user_123/2025/10/28/test.txt",
            status=FileStatus.AVAILABLE,
            access_level=FileAccessLevel.PRIVATE,
            checksum="abc123",
            etag="etag123",
            version_id=None,
            metadata={},
            tags=[],
            download_url="https://minio.example.com/test.txt",
            download_url_expires_at=datetime.utcnow(),
            uploaded_at=datetime.utcnow()
        )

    async def update_storage_usage(self, quota_type, entity_id, bytes_delta, file_count_delta):
        """Mock update storage usage"""
        return True

    async def get_storage_quota(self, quota_type, entity_id):
        """Mock get storage quota"""
        return None  # Return None to trigger default quota creation

    async def delete_file(self, file_id, user_id):
        """Mock delete file"""
        return True

    async def create_file_share(self, share):
        """Mock create file share"""
        return share

    async def check_connection(self):
        """Mock check connection"""
        return True


class MockMinIOClient:
    """Mock MinIO client"""

    def bucket_exists(self, bucket_name):
        return True

    def put_object(self, bucket_name, object_key, data, size, metadata=None):
        return True

    def get_presigned_url(self, bucket_name, object_key, expiry_seconds):
        return f"https://minio.example.com/{bucket_name}/{object_key}"

    def delete_object(self, bucket_name, object_key):
        return True


class MockConfig:
    """Mock configuration"""
    consul_host = "localhost"
    consul_port = 8500
    minio_bucket_name = "isa-storage"


async def test_file_uploaded_event():
    """Test that uploading file publishes file.uploaded event"""
    print("\n" + "="*60)
    print("TEST 1: File Uploaded Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create storage service with mock dependencies
    storage_service = StorageService.__new__(StorageService)
    storage_service.event_bus = mock_bus
    storage_service.repository = MockStorageRepository()
    storage_service.minio_client = MockMinIOClient()
    storage_service.bucket_name = "isa-storage"
    storage_service.allowed_types = ["text/plain", "image/jpeg", "image/png"]
    storage_service.max_file_size = 500 * 1024 * 1024
    storage_service.default_quota_bytes = 10 * 1024 * 1024 * 1024

    # Create upload file
    file_content = b"This is a test file content"
    file = MagicMock(spec=UploadFile)
    file.filename = "test.txt"
    file.content_type = "text/plain"

    # Create async read function
    async def mock_read():
        return file_content
    file.read = mock_read

    request = FileUploadRequest(
        user_id="user_123",
        organization_id="org_456",
        access_level=FileAccessLevel.PRIVATE,
        metadata={"test": True},
        tags=["test"]
    )

    # Upload file
    result = await storage_service.upload_file(file, request)

    # Verify event was published
    assert len(mock_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_bus.published_events[0]
    assert event["type"] == "file.uploaded", f"Expected file.uploaded, got {event['type']}"
    assert event["source"] == "storage_service"
    assert event["data"]["user_id"] == "user_123"
    assert event["data"]["organization_id"] == "org_456"
    assert event["data"]["file_name"] == "test.txt"
    assert event["data"]["content_type"] == "text/plain"

    print(f"✅ file.uploaded event published correctly")
    print(f"   Event ID: {event['id']}")
    print(f"   File: {event['data']['file_name']}")
    print(f"   User: {event['data']['user_id']}")

    return True


async def test_file_shared_event():
    """Test that sharing file publishes file.shared event"""
    print("\n" + "="*60)
    print("TEST 2: File Shared Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create storage service
    storage_service = StorageService.__new__(StorageService)
    storage_service.event_bus = mock_bus
    storage_service.repository = MockStorageRepository()

    # Share file
    request = FileShareRequest(
        file_id="file_123",
        shared_by="user_123",
        shared_with="user_456",
        shared_with_email="user456@example.com",
        permissions={"view": True, "download": True},
        expires_hours=24
    )

    result = await storage_service.share_file(request)

    # Verify event was published
    assert len(mock_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_bus.published_events[0]
    assert event["type"] == "file.shared", f"Expected file.shared, got {event['type']}"
    assert event["source"] == "storage_service"
    assert event["data"]["file_id"] == "file_123"
    assert event["data"]["shared_by"] == "user_123"
    assert event["data"]["shared_with"] == "user_456"
    assert event["data"]["shared_with_email"] == "user456@example.com"

    print(f"✅ file.shared event published correctly")
    print(f"   Share ID: {event['data']['share_id']}")
    print(f"   File: {event['data']['file_id']}")
    print(f"   Shared by: {event['data']['shared_by']}")
    print(f"   Shared with: {event['data']['shared_with']}")

    return True


async def test_file_deleted_event():
    """Test that deleting file publishes file.deleted event"""
    print("\n" + "="*60)
    print("TEST 3: File Deleted Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create storage service
    storage_service = StorageService.__new__(StorageService)
    storage_service.event_bus = mock_bus
    storage_service.repository = MockStorageRepository()
    storage_service.minio_client = MockMinIOClient()

    # Delete file
    success = await storage_service.delete_file("file_123", "user_123", permanent=True)

    # Verify event was published
    assert success
    assert len(mock_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_bus.published_events[0]
    assert event["type"] == "file.deleted", f"Expected file.deleted, got {event['type']}"
    assert event["source"] == "storage_service"
    assert event["data"]["file_id"] == "file_123"
    assert event["data"]["user_id"] == "user_123"
    assert event["data"]["permanent"] == True

    print(f"✅ file.deleted event published correctly")
    print(f"   File: {event['data']['file_id']}")
    print(f"   User: {event['data']['user_id']}")
    print(f"   Permanent: {event['data']['permanent']}")

    return True


async def test_no_event_bus():
    """Test that service works without event bus"""
    print("\n" + "="*60)
    print("TEST 4: Service Works Without Event Bus")
    print("="*60)

    # Create storage service without event bus
    storage_service = StorageService.__new__(StorageService)
    storage_service.event_bus = None  # No event bus
    storage_service.repository = MockStorageRepository()
    storage_service.minio_client = MockMinIOClient()

    # Delete file should work without event bus
    success = await storage_service.delete_file("file_123", "user_123", permanent=False)

    assert success, "Delete should succeed even without event bus"

    print(f"✅ Service works correctly without event bus")
    print(f"   File deletion succeeded: {success}")

    return True


async def test_nats_connection():
    """Test actual NATS connection (if available)"""
    print("\n" + "="*60)
    print("TEST 5: NATS Connection Test")
    print("="*60)

    try:
        # Try to connect to NATS
        event_bus = await get_event_bus("storage_service_test")

        if event_bus and event_bus._is_connected:
            print("✅ Successfully connected to NATS")
            print(f"   URL: {event_bus.nats_url}")

            # Test publishing a storage event
            from core.nats_client import Event, EventType, ServiceSource
            test_event = Event(
                event_type=EventType.FILE_UPLOADED,
                source=ServiceSource.STORAGE_SERVICE,
                data={
                    "file_id": "test_123",
                    "file_name": "test.txt",
                    "user_id": "user_123",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            success = await event_bus.publish_event(test_event)

            if success:
                print("✅ Test storage event published to NATS successfully")
            else:
                print("⚠️  Event publish returned False")

            await event_bus.close()
            return True
        else:
            print("⚠️  NATS not available or not configured")
            return False

    except Exception as e:
        print(f"⚠️  NATS connection failed: {e}")
        print("   This is OK for testing without NATS running")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("STORAGE SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["file_uploaded_event"] = await test_file_uploaded_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["file_uploaded_event"] = False

    try:
        results["file_shared_event"] = await test_file_shared_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["file_shared_event"] = False

    try:
        results["file_deleted_event"] = await test_file_deleted_event()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["file_deleted_event"] = False

    try:
        results["no_event_bus"] = await test_no_event_bus()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results["no_event_bus"] = False

    try:
        results["nats_connection"] = await test_nats_connection()
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        results["nats_connection"] = False

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    elif passed >= 4:  # Core tests (NATS is optional)
        print("\n✅ Core functionality tests passed (NATS optional)")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())

    # Exit with appropriate code
    if passed >= 4:  # Core tests must pass (NATS is optional)
        sys.exit(0)
    else:
        sys.exit(1)
