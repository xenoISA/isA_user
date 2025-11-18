#!/usr/bin/env python3
"""
Test Media Service Event Publishing

Tests that media service publishes events correctly to NATS
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.media_service.media_service import MediaService
from microservices.media_service.models import (
    PhotoVersionCreateRequest, PhotoVersionType,
    PlaylistCreateRequest, PlaylistType,
    RotationScheduleCreateRequest, ScheduleType,
    PhotoMetadataUpdateRequest
)
from core.nats_client import Event


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


class MockMediaRepository:
    """Mock repository for testing"""

    def __init__(self):
        self.photo_versions = {}
        self.playlists = {}
        self.schedules = {}
        self.metadata = {}
        self.cache = {}

    async def create_photo_version(self, version):
        """Mock create photo version"""
        self.photo_versions[version.version_id] = version
        return version

    async def list_photo_versions(self, photo_id, user_id):
        """Mock list photo versions"""
        return []

    async def create_playlist(self, playlist):
        """Mock create playlist"""
        self.playlists[playlist.playlist_id] = playlist
        return playlist

    async def get_playlist(self, playlist_id):
        """Mock get playlist"""
        return self.playlists.get(playlist_id)

    async def update_playlist(self, playlist_id, user_id, update_data):
        """Mock update playlist"""
        playlist = self.playlists.get(playlist_id)
        if playlist:
            for key, value in update_data.items():
                setattr(playlist, key, value)
        return playlist

    async def delete_playlist(self, playlist_id, user_id):
        """Mock delete playlist"""
        if playlist_id in self.playlists:
            del self.playlists[playlist_id]
            return True
        return False

    async def create_rotation_schedule(self, schedule):
        """Mock create rotation schedule"""
        self.schedules[schedule.schedule_id] = schedule
        return schedule

    async def get_photo_metadata(self, file_id):
        """Mock get photo metadata"""
        return self.metadata.get(file_id)

    async def create_or_update_metadata(self, metadata):
        """Mock create or update metadata"""
        self.metadata[metadata.file_id] = metadata
        return metadata

    async def create_photo_cache(self, cache_entry):
        """Mock create photo cache"""
        self.cache[cache_entry.cache_id] = cache_entry
        return cache_entry

    async def get_frame_cache(self, frame_id, photo_id, user_id):
        """Mock get frame cache"""
        return None

    async def check_connection(self):
        """Mock check connection"""
        return True


async def test_photo_version_created_event():
    """Test that PHOTO_VERSION_CREATED event is published"""
    print("\n" + "="*80)
    print("TEST: PHOTO_VERSION_CREATED Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    media_service = MediaService(event_bus=mock_event_bus)
    media_service.repository = MockMediaRepository()

    # Create photo version request
    request = PhotoVersionCreateRequest(
        photo_id="photo_123",
        version_name="AI Enhanced",
        version_type=PhotoVersionType.AI_ENHANCED,
        processing_mode="ai_enhanced",
        file_id="file_456"
    )

    # Create photo version
    result = await media_service.create_photo_version(request, "user_123")

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "One event should be published"

    event = mock_event_bus.published_events[0]
    # Event type uses dots: media.photo_version.created
    assert event["type"] == "media.photo_version.created", f"Event type should be media.photo_version.created, got: {event['type']}"
    assert event["source"] == "media_service", "Event source should be media_service"
    assert event["data"]["photo_id"] == "photo_123", "Event should contain photo_id"
    assert event["data"]["user_id"] == "user_123", "Event should contain user_id"
    assert event["data"]["version_type"] == "ai_enhanced", "Event should contain version_type"

    print("✅ TEST PASSED: PHOTO_VERSION_CREATED event published correctly")
    print(f"   Version ID: {result.version_id}")
    print(f"   Photo ID: {result.photo_id}")
    return True


async def test_playlist_created_event():
    """Test that MEDIA_PLAYLIST_CREATED event is published"""
    print("\n" + "="*80)
    print("TEST: MEDIA_PLAYLIST_CREATED Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    media_service = MediaService(event_bus=mock_event_bus)
    media_service.repository = MockMediaRepository()

    # Create playlist request
    request = PlaylistCreateRequest(
        name="Summer Vacation",
        description="Photos from summer vacation",
        user_id="user_123",
        playlist_type=PlaylistType.MANUAL,
        photo_ids=["photo_1", "photo_2", "photo_3"],
        shuffle=False,
        loop=True,
        transition_duration=5
    )

    # Create playlist
    result = await media_service.create_playlist(request, "user_123")

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "One event should be published"

    event = mock_event_bus.published_events[0]
    # Event type uses dots: media.playlist.created
    assert event["type"] == "media.playlist.created", f"Event type should be media.playlist.created, got: {event['type']}"
    assert event["source"] == "media_service", "Event source should be media_service"
    assert event["data"]["playlist_id"] == result.playlist_id, "Event should contain playlist_id"
    assert event["data"]["name"] == "Summer Vacation", "Event should contain name"
    assert event["data"]["photo_count"] == 3, "Event should contain photo_count"

    print("✅ TEST PASSED: MEDIA_PLAYLIST_CREATED event published correctly")
    print(f"   Playlist ID: {result.playlist_id}")
    print(f"   Name: {result.name}")
    return True


async def run_all_tests():
    """Run all event publishing tests"""
    print("\n" + "="*80)
    print("MEDIA SERVICE EVENT PUBLISHING TESTS")
    print("="*80)

    tests = [
        ("PHOTO_VERSION_CREATED", test_photo_version_created_event),
        ("MEDIA_PLAYLIST_CREATED", test_playlist_created_event)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASSED", None))
        except Exception as e:
            results.append((test_name, "FAILED", str(e)))
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, status, _ in results if status == "PASSED")
    failed = sum(1 for _, status, _ in results if status == "FAILED")

    for test_name, status, error in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {test_name}: {status}")
        if error:
            print(f"   Error: {error}")

    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
