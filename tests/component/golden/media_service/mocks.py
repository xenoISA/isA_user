"""
Media Service - Mock Dependencies (Golden)

Mock implementations for component golden testing.
These mocks simulate external dependencies (repository, event bus, service clients)
without requiring real infrastructure.

Usage:
    from tests.component.golden.media_service.mocks import (
        MockMediaRepository,
        MockEventBus,
        MockStorageClient,
        MockDeviceClient,
    )
"""

from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid


class MockMediaRepository:
    """
    Mock media repository for golden component testing.

    Simple mock that allows tests to override return_value for each method.
    Create methods return the input data by default (side_effect=lambda x: x).
    """

    def __init__(self):
        # Photo Version methods - create returns input
        self.create_photo_version = AsyncMock(side_effect=lambda x: x)
        self.get_photo_version = AsyncMock(return_value=None)
        self.list_photo_versions = AsyncMock(return_value=[])
        self.delete_photo_version = AsyncMock(return_value=True)

        # Photo Metadata methods - create returns input
        self.create_or_update_metadata = AsyncMock(side_effect=lambda x: x)
        self.get_photo_metadata = AsyncMock(return_value=None)

        # Playlist methods - create returns input
        self.create_playlist = AsyncMock(side_effect=lambda x: x)
        self.get_playlist = AsyncMock(return_value=None)
        self.list_user_playlists = AsyncMock(return_value=[])
        self.update_playlist = AsyncMock()  # Set return_value in test
        self.delete_playlist = AsyncMock(return_value=True)

        # Rotation Schedule methods - create returns input
        self.create_rotation_schedule = AsyncMock(side_effect=lambda x: x)
        self.get_rotation_schedule = AsyncMock(return_value=None)
        self.list_frame_schedules = AsyncMock(return_value=[])
        self.update_schedule_status = AsyncMock()
        self.delete_rotation_schedule = AsyncMock(return_value=True)

        # Photo Cache methods - create returns input
        self.create_photo_cache = AsyncMock(side_effect=lambda x: x)
        self.get_photo_cache = AsyncMock(return_value=None)
        self.get_frame_cache = AsyncMock(return_value=None)
        self.list_frame_cache = AsyncMock(return_value=[])
        self.update_cache_status = AsyncMock()

        # Health check
        self.check_connection = AsyncMock(return_value=True)


class MockEventBus:
    """Mock NATS event bus for golden component testing."""

    def __init__(self):
        self.published_events: List[Any] = []
        self.publish = AsyncMock(side_effect=self._publish)
        self.publish_event = AsyncMock(side_effect=self._publish)

    async def _publish(self, event: Any) -> None:
        """Track published event"""
        self.published_events.append(event)

    def get_published_events(self, event_type: Optional[str] = None) -> List[Any]:
        """Get published events, optionally filtered by type"""
        if event_type is None:
            return self.published_events
        return [
            e for e in self.published_events
            if hasattr(e, 'type') and e.type == event_type
            or isinstance(e, dict) and e.get('type') == event_type
        ]

    def assert_event_published(self, event_type: str) -> None:
        """Assert that an event of given type was published"""
        events = self.get_published_events(event_type)
        assert len(events) > 0, f"Expected event '{event_type}' to be published"

    def clear(self):
        """Clear all published events"""
        self.published_events.clear()


class MockStorageClient:
    """Mock Storage Service client for testing"""

    def __init__(self):
        self._files: Dict[str, Dict] = {}
        self.get_file = AsyncMock(side_effect=self._get_file)
        self.file_exists = AsyncMock(side_effect=self._file_exists)

    async def _get_file(self, file_id: str) -> Optional[Dict]:
        return self._files.get(file_id)

    async def _file_exists(self, file_id: str) -> bool:
        return file_id in self._files

    def seed_file(self, file_id: str, **kwargs) -> Dict:
        """Seed a file for testing"""
        record = {"file_id": file_id, **kwargs}
        self._files[file_id] = record
        return record


class MockDeviceClient:
    """Mock Device Service client for testing"""

    def __init__(self):
        self._devices: Dict[str, Dict] = {}
        self.get_device = AsyncMock(side_effect=self._get_device)
        self.device_exists = AsyncMock(side_effect=self._device_exists)

    async def _get_device(self, device_id: str) -> Optional[Dict]:
        return self._devices.get(device_id)

    async def _device_exists(self, device_id: str) -> bool:
        return device_id in self._devices

    def seed_device(self, device_id: str, **kwargs) -> Dict:
        """Seed a device for testing"""
        record = {"device_id": device_id, **kwargs}
        self._devices[device_id] = record
        return record
