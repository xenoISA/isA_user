"""
Album Service Event Publishing Tests

Tests that Album Service correctly publishes events for all album operations
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.album_service.album_service import AlbumService
from microservices.album_service.models import (
    AlbumCreateRequest, AlbumUpdateRequest, AlbumAddPhotosRequest,
    AlbumRemovePhotosRequest, AlbumSyncRequest, Album, AlbumPhoto,
    AlbumSyncStatus, SyncStatus
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)
        print(f"✅ Event captured: {event.type}")
        print(f"   Data: {event.data}")


class MockAlbumRepository:
    """Mock Album Repository for testing"""

    def __init__(self):
        self.albums = {}
        self.photos = {}

    async def create_album(self, album):
        """Mock create album"""
        self.albums[album.album_id] = album
        return album

    async def get_album_by_id(self, album_id, user_id):
        """Mock get album by id"""
        return self.albums.get(album_id)

    async def update_album(self, album_id, user_id, update_data):
        """Mock update album"""
        return True

    async def delete_album(self, album_id, user_id):
        """Mock delete album"""
        if album_id in self.albums:
            del self.albums[album_id]
            return True
        return False

    async def add_photos_to_album(self, album_id, photo_ids, added_by):
        """Mock add photos to album"""
        return len(photo_ids)

    async def remove_photos_from_album(self, album_id, photo_ids):
        """Mock remove photos from album"""
        return len(photo_ids)

    async def update_album_sync_status(self, album_id, frame_id, user_id, status_data):
        """Mock update sync status"""
        return True

    async def get_album_sync_status(self, album_id, frame_id):
        """Mock get sync status"""
        return AlbumSyncStatus(
            album_id=album_id,
            user_id="user_123",
            frame_id=frame_id,
            last_sync_timestamp=datetime.now(timezone.utc),
            sync_version=1,
            total_photos=10,
            synced_photos=0,
            pending_photos=10,
            failed_photos=0,
            sync_status=SyncStatus.IN_PROGRESS,
            error_message=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    async def check_connection(self):
        """Mock check connection"""
        return True


async def test_album_created_event():
    """Test that album.created event is published when creating an album"""
    print("\n" + "="*80)
    print("TEST: Album Created Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    album_service = AlbumService(event_bus=mock_event_bus)
    album_service.album_repo = MockAlbumRepository()

    # Create album
    request = AlbumCreateRequest(
        name="Vacation Photos",
        description="Summer 2025 trip",
        auto_sync=True,
        sync_frames=["frame_123"],
        is_family_shared=True,
        tags=["vacation", "summer"]
    )

    album = await album_service.create_album(request, user_id="user_123")

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.ALBUM_CREATED.value, f"Expected {EventType.ALBUM_CREATED.value}"
    assert event.source == ServiceSource.ALBUM_SERVICE.value
    assert event.data["user_id"] == "user_123"
    assert event.data["name"] == "Vacation Photos"
    assert event.data["is_family_shared"] is True

    print("✅ TEST PASSED: album.created event published correctly")
    return True


async def test_album_updated_event():
    """Test that album.updated event is published when updating an album"""
    print("\n" + "="*80)
    print("TEST: Album Updated Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    album_service = AlbumService(event_bus=mock_event_bus)
    mock_repo = MockAlbumRepository()
    album_service.album_repo = mock_repo

    # Create initial album
    album = Album(
        album_id="album_123",
        name="Original Name",
        user_id="user_123",
        photo_count=0,
        auto_sync=True,
        sync_frames=[],
        is_family_shared=False,
        tags=[],
        metadata={}
    )
    mock_repo.albums["album_123"] = album

    # Update album
    update_request = AlbumUpdateRequest(
        name="Updated Name",
        description="New description",
        tags=["updated"]
    )

    updated_album = await album_service.update_album("album_123", "user_123", update_request)

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.ALBUM_UPDATED.value
    assert event.source == ServiceSource.ALBUM_SERVICE.value
    assert event.data["album_id"] == "album_123"
    assert event.data["user_id"] == "user_123"
    assert "updates" in event.data

    print("✅ TEST PASSED: album.updated event published correctly")
    return True


async def test_album_deleted_event():
    """Test that album.deleted event is published when deleting an album"""
    print("\n" + "="*80)
    print("TEST: Album Deleted Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    album_service = AlbumService(event_bus=mock_event_bus)
    mock_repo = MockAlbumRepository()
    album_service.album_repo = mock_repo

    # Create album to delete
    album = Album(
        album_id="album_123",
        name="To Delete",
        user_id="user_123",
        photo_count=0,
        auto_sync=True,
        sync_frames=[],
        is_family_shared=False,
        tags=[],
        metadata={}
    )
    mock_repo.albums["album_123"] = album

    # Delete album
    success = await album_service.delete_album("album_123", "user_123")

    # Verify event was published
    assert success is True
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.ALBUM_DELETED.value
    assert event.source == ServiceSource.ALBUM_SERVICE.value
    assert event.data["album_id"] == "album_123"
    assert event.data["user_id"] == "user_123"

    print("✅ TEST PASSED: album.deleted event published correctly")
    return True


async def test_album_photo_added_event():
    """Test that album.photo.added event is published when adding photos"""
    print("\n" + "="*80)
    print("TEST: Album Photo Added Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    album_service = AlbumService(event_bus=mock_event_bus)
    mock_repo = MockAlbumRepository()
    album_service.album_repo = mock_repo

    # Create album
    album = Album(
        album_id="album_123",
        name="Photos",
        user_id="user_123",
        photo_count=0,
        auto_sync=True,
        sync_frames=[],
        is_family_shared=False,
        tags=[],
        metadata={}
    )
    mock_repo.albums["album_123"] = album

    # Add photos
    request = AlbumAddPhotosRequest(
        photo_ids=["photo_1", "photo_2", "photo_3"]
    )

    result = await album_service.add_photos_to_album("album_123", "user_123", request)

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.ALBUM_PHOTO_ADDED.value
    assert event.source == ServiceSource.ALBUM_SERVICE.value
    assert event.data["album_id"] == "album_123"
    assert event.data["added_count"] == 3
    assert len(event.data["photo_ids"]) == 3

    print("✅ TEST PASSED: album.photo.added event published correctly")
    return True


async def test_album_photo_removed_event():
    """Test that album.photo.removed event is published when removing photos"""
    print("\n" + "="*80)
    print("TEST: Album Photo Removed Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    album_service = AlbumService(event_bus=mock_event_bus)
    mock_repo = MockAlbumRepository()
    album_service.album_repo = mock_repo

    # Create album with photos
    album = Album(
        album_id="album_123",
        name="Photos",
        user_id="user_123",
        photo_count=5,
        auto_sync=True,
        sync_frames=[],
        is_family_shared=False,
        tags=[],
        metadata={}
    )
    mock_repo.albums["album_123"] = album

    # Remove photos
    request = AlbumRemovePhotosRequest(
        photo_ids=["photo_1", "photo_2"]
    )

    result = await album_service.remove_photos_from_album("album_123", "user_123", request)

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.ALBUM_PHOTO_REMOVED.value
    assert event.source == ServiceSource.ALBUM_SERVICE.value
    assert event.data["album_id"] == "album_123"
    assert event.data["removed_count"] == 2

    print("✅ TEST PASSED: album.photo.removed event published correctly")
    return True


async def test_album_synced_event():
    """Test that album.synced event is published when syncing to frame"""
    print("\n" + "="*80)
    print("TEST: Album Synced Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    album_service = AlbumService(event_bus=mock_event_bus)
    mock_repo = MockAlbumRepository()
    album_service.album_repo = mock_repo

    # Create album
    album = Album(
        album_id="album_123",
        name="Photos",
        user_id="user_123",
        photo_count=10,
        auto_sync=True,
        sync_frames=["frame_123"],
        is_family_shared=False,
        tags=[],
        metadata={}
    )
    mock_repo.albums["album_123"] = album

    # Sync album to frame
    request = AlbumSyncRequest(frame_id="frame_123")

    sync_status = await album_service.sync_album_to_frame("album_123", "user_123", request)

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.ALBUM_SYNCED.value
    assert event.source == ServiceSource.ALBUM_SERVICE.value
    assert event.data["album_id"] == "album_123"
    assert event.data["frame_id"] == "frame_123"
    assert event.data["total_photos"] == 10

    print("✅ TEST PASSED: album.synced event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("ALBUM SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Album Created Event", test_album_created_event),
        ("Album Updated Event", test_album_updated_event),
        ("Album Deleted Event", test_album_deleted_event),
        ("Album Photo Added Event", test_album_photo_added_event),
        ("Album Photo Removed Event", test_album_photo_removed_event),
        ("Album Synced Event", test_album_synced_event),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
