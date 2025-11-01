"""
Album Service Event Subscription Tests

Tests that Album Service correctly handles events from other services
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.album_service.events import AlbumEventHandler
from microservices.album_service.models import Album, AlbumPhoto


class MockAlbumRepository:
    """Mock Album Repository for testing"""

    def __init__(self):
        self.albums = {}
        self.photos = {}
        self.sync_statuses = {}
        self.removed_photos = []
        self.deleted_sync_frames = []

    async def remove_photo_from_all_albums(self, photo_id: str) -> int:
        """Mock remove photo from all albums"""
        count = 0
        for album_id, photos in self.photos.items():
            if photo_id in photos:
                photos.remove(photo_id)
                count += 1
        self.removed_photos.append(photo_id)
        return count

    async def delete_sync_status_by_frame(self, frame_id: str) -> int:
        """Mock delete sync status by frame"""
        count = 0
        to_delete = []
        for key, status in self.sync_statuses.items():
            if status.get('frame_id') == frame_id:
                to_delete.append(key)
                count += 1

        for key in to_delete:
            del self.sync_statuses[key]

        self.deleted_sync_frames.append(frame_id)
        return count


async def test_file_deleted_event():
    """Test that file.deleted event removes photo from all albums"""
    print("\n" + "="*80)
    print("TEST: Handle file.deleted Event")
    print("="*80)

    # Setup
    mock_repo = MockAlbumRepository()
    event_handler = AlbumEventHandler(mock_repo)

    # Prepare test data - photo exists in 3 albums
    mock_repo.photos = {
        "album_1": ["photo_123", "photo_456"],
        "album_2": ["photo_123", "photo_789"],
        "album_3": ["photo_123", "photo_101"]
    }

    # Create file.deleted event
    event_data = {
        "file_id": "photo_123",
        "user_id": "user_456",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    success = await event_handler.handle_file_deleted(event_data)

    # Verify
    assert success is True, "Event handling should succeed"
    assert "photo_123" in mock_repo.removed_photos, "Photo should be marked as removed"

    # Verify photo was removed from all albums
    for album_id, photos in mock_repo.photos.items():
        assert "photo_123" not in photos, f"Photo should be removed from {album_id}"

    print("✅ TEST PASSED: file.deleted event handled correctly")
    print(f"   Photo removed from {len(mock_repo.photos)} albums")
    return True


async def test_device_deleted_event():
    """Test that device.deleted event cleans up sync status"""
    print("\n" + "="*80)
    print("TEST: Handle device.deleted Event")
    print("="*80)

    # Setup
    mock_repo = MockAlbumRepository()
    event_handler = AlbumEventHandler(mock_repo)

    # Prepare test data - device has sync status for 3 albums
    mock_repo.sync_statuses = {
        "album_1_frame_123": {"album_id": "album_1", "frame_id": "frame_123"},
        "album_2_frame_123": {"album_id": "album_2", "frame_id": "frame_123"},
        "album_3_frame_123": {"album_id": "album_3", "frame_id": "frame_123"},
        "album_4_frame_456": {"album_id": "album_4", "frame_id": "frame_456"}
    }

    # Create device.deleted event
    event_data = {
        "device_id": "frame_123",
        "user_id": "user_456",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    success = await event_handler.handle_device_deleted(event_data)

    # Verify
    assert success is True, "Event handling should succeed"
    assert "frame_123" in mock_repo.deleted_sync_frames, "Frame should be marked as deleted"

    # Verify sync status was cleaned up
    remaining_frames = [s.get('frame_id') for s in mock_repo.sync_statuses.values()]
    assert "frame_123" not in remaining_frames, "All sync status for frame_123 should be deleted"
    assert "frame_456" in remaining_frames, "Other frames should not be affected"

    print("✅ TEST PASSED: device.deleted event handled correctly")
    print(f"   Sync status cleaned up for device")
    return True


async def test_missing_file_id():
    """Test handling of file.deleted event with missing file_id"""
    print("\n" + "="*80)
    print("TEST: Handle file.deleted Event with Missing file_id")
    print("="*80)

    # Setup
    mock_repo = MockAlbumRepository()
    event_handler = AlbumEventHandler(mock_repo)

    # Create event with missing file_id
    event_data = {
        "user_id": "user_456",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    success = await event_handler.handle_file_deleted(event_data)

    # Verify - should return False for invalid event
    assert success is False, "Should return False for missing file_id"
    assert len(mock_repo.removed_photos) == 0, "No photos should be removed"

    print("✅ TEST PASSED: Invalid event handled gracefully")
    return True


async def test_missing_device_id():
    """Test handling of device.deleted event with missing device_id"""
    print("\n" + "="*80)
    print("TEST: Handle device.deleted Event with Missing device_id")
    print("="*80)

    # Setup
    mock_repo = MockAlbumRepository()
    event_handler = AlbumEventHandler(mock_repo)

    # Create event with missing device_id
    event_data = {
        "user_id": "user_456",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    success = await event_handler.handle_device_deleted(event_data)

    # Verify - should return False for invalid event
    assert success is False, "Should return False for missing device_id"
    assert len(mock_repo.deleted_sync_frames) == 0, "No sync statuses should be deleted"

    print("✅ TEST PASSED: Invalid event handled gracefully")
    return True


async def test_event_routing():
    """Test that events are routed to correct handlers"""
    print("\n" + "="*80)
    print("TEST: Event Routing")
    print("="*80)

    # Setup
    mock_repo = MockAlbumRepository()
    event_handler = AlbumEventHandler(mock_repo)

    # Prepare test data
    mock_repo.photos = {
        "album_1": ["photo_123"]
    }

    # Create file.deleted event using Event class
    event = Event(
        event_type=EventType.FILE_DELETED,
        source=ServiceSource.STORAGE_SERVICE,
        data={
            "file_id": "photo_123",
            "user_id": "user_456"
        }
    )

    # Route event
    success = await event_handler.handle_event(event)

    # Verify
    assert success is True, "Event should be routed and handled"
    assert "photo_123" in mock_repo.removed_photos, "Photo should be removed"

    print("✅ TEST PASSED: Event routing works correctly")
    return True


async def test_get_subscriptions():
    """Test that handler returns correct subscriptions"""
    print("\n" + "="*80)
    print("TEST: Get Subscriptions")
    print("="*80)

    # Setup
    mock_repo = MockAlbumRepository()
    event_handler = AlbumEventHandler(mock_repo)

    # Get subscriptions
    subscriptions = event_handler.get_subscriptions()

    # Verify
    assert isinstance(subscriptions, list), "Should return a list"
    assert len(subscriptions) > 0, "Should have at least one subscription"
    assert EventType.FILE_DELETED.value in subscriptions, "Should subscribe to file.deleted"

    print("✅ TEST PASSED: Subscriptions configured correctly")
    print(f"   Subscriptions: {subscriptions}")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("ALBUM SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)

    tests = [
        ("File Deleted Event", test_file_deleted_event),
        ("Device Deleted Event", test_device_deleted_event),
        ("Missing File ID", test_missing_file_id),
        ("Missing Device ID", test_missing_device_id),
        ("Event Routing", test_event_routing),
        ("Get Subscriptions", test_get_subscriptions),
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
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
