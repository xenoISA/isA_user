"""
Media Service - Component Golden Tests

GOLDEN: These tests document the CURRENT behavior of MediaService.
DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions in business logic
- Document what the service currently does
- All tests should PASS (they describe existing behavior)

Related Documents:
- Data Contract: tests/contracts/media/data_contract.py
- Logic Contract: tests/contracts/media/logic_contract.md
- Design: docs/design/media_service.md

Usage:
    pytest tests/component/golden/media_service -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from tests.component.golden.media_service.mocks import (
    MockMediaRepository,
    MockEventBus,
    MockStorageClient,
    MockDeviceClient,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio, pytest.mark.golden]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo():
    """Create a fresh MockMediaRepository"""
    return MockMediaRepository()


@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


@pytest.fixture
def mock_storage_client():
    """Create MockStorageClient"""
    client = MockStorageClient()
    client.seed_file("file_test_123", status="active", size=1024)
    return client


@pytest.fixture
def mock_device_client():
    """Create MockDeviceClient"""
    client = MockDeviceClient()
    client.seed_device("dev_test_123", status="active", type="smart_frame")
    return client


# =============================================================================
# Photo Version Operations - Current Behavior
# =============================================================================

class TestMediaServicePhotoVersionCreateGolden:
    """Characterization: PhotoVersion creation current behavior"""

    async def test_create_photo_version_returns_response(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: create_photo_version returns PhotoVersionResponse"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import (
            PhotoVersionCreateRequest,
            PhotoVersionType,
            PhotoVersionResponse,
        )

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        request = PhotoVersionCreateRequest(
            photo_id="photo_test_123",
            version_name="AI Enhanced",
            version_type=PhotoVersionType.AI_ENHANCED,
            file_id="file_test_123",
            processing_params={"enhance_level": "high"},
        )

        result = await service.create_photo_version(
            request=request,
            user_id="usr_test_123",
            organization_id=None,
        )

        assert isinstance(result, PhotoVersionResponse)
        assert result.version_id is not None
        assert result.version_id.startswith("ver_")
        assert result.photo_id == "photo_test_123"
        assert result.version_name == "AI Enhanced"

    async def test_create_photo_version_calls_repository(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: create_photo_version calls repository.create_photo_version"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import (
            PhotoVersionCreateRequest,
            PhotoVersionType,
        )

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        request = PhotoVersionCreateRequest(
            photo_id="photo_test_123",
            version_name="Test Version",
            version_type=PhotoVersionType.ORIGINAL,
            file_id="file_test_123",
        )

        await service.create_photo_version(
            request=request,
            user_id="usr_test_123",
        )

        # Repository should be called
        mock_repo.create_photo_version.assert_called_once()


class TestMediaServicePhotoVersionGetGolden:
    """Characterization: PhotoVersion retrieval current behavior"""

    async def test_get_existing_version_returns_response(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: get_photo_version returns PhotoVersionResponse for existing version"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import PhotoVersion, PhotoVersionType

        # Setup mock to return a version
        mock_version = PhotoVersion(
            version_id="ver_test_123",
            photo_id="photo_test_123",
            user_id="usr_test_123",
            version_name="Original",
            version_type=PhotoVersionType.ORIGINAL,
            file_id="file_test_123",
            is_current=True,
            version_number=1,
        )
        mock_repo.get_photo_version.return_value = mock_version

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.get_photo_version(
            version_id="ver_test_123",
            user_id="usr_test_123",
        )

        assert result is not None
        assert result.version_id == "ver_test_123"

    async def test_get_nonexistent_version_raises_error(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: get_photo_version raises MediaNotFoundError for non-existent version"""
        from microservices.media_service.media_service import MediaService, MediaNotFoundError

        mock_repo.get_photo_version.return_value = None

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        with pytest.raises(MediaNotFoundError):
            await service.get_photo_version(
                version_id="ver_nonexistent",
                user_id="usr_test_123",
            )


# =============================================================================
# Playlist Operations - Current Behavior
# =============================================================================

class TestMediaServicePlaylistCreateGolden:
    """Characterization: Playlist creation current behavior"""

    async def test_create_playlist_returns_response(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: create_playlist returns PlaylistResponse"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import (
            PlaylistCreateRequest,
            PlaylistType,
            PlaylistResponse,
        )

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        request = PlaylistCreateRequest(
            name="Beach Vacation 2024",
            description="Our trip to the beach",
            playlist_type=PlaylistType.MANUAL,
            photo_ids=["photo_1", "photo_2", "photo_3"],
            shuffle=False,
            loop=True,
            transition_duration=10,
        )

        result = await service.create_playlist(
            request=request,
            user_id="usr_test_123",
            organization_id=None,
        )

        assert isinstance(result, PlaylistResponse)
        assert result.playlist_id is not None
        assert result.playlist_id.startswith("pl_")
        assert result.name == "Beach Vacation 2024"


class TestMediaServicePlaylistGetGolden:
    """Characterization: Playlist retrieval current behavior"""

    async def test_get_existing_playlist_returns_response(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: get_playlist returns PlaylistResponse for existing playlist"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import Playlist, PlaylistType

        mock_playlist = Playlist(
            playlist_id="pl_test_123",
            user_id="usr_test_123",
            name="Test Playlist",
            playlist_type=PlaylistType.MANUAL,
            photo_ids=["photo_1"],
            shuffle=False,
            loop=True,
            transition_duration=5,
        )
        mock_repo.get_playlist.return_value = mock_playlist

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.get_playlist(
            playlist_id="pl_test_123",
            user_id="usr_test_123",
        )

        assert result is not None
        assert result.playlist_id == "pl_test_123"

    async def test_get_nonexistent_playlist_raises_error(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: get_playlist raises MediaNotFoundError for non-existent playlist"""
        from microservices.media_service.media_service import MediaService, MediaNotFoundError

        mock_repo.get_playlist.return_value = None

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        with pytest.raises(MediaNotFoundError):
            await service.get_playlist(
                playlist_id="pl_nonexistent",
                user_id="usr_test_123",
            )


class TestMediaServicePlaylistUpdateGolden:
    """Characterization: Playlist update current behavior"""

    async def test_update_playlist_returns_updated_response(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: update_playlist returns updated PlaylistResponse"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import (
            Playlist,
            PlaylistType,
            PlaylistUpdateRequest,
        )

        # Setup existing playlist
        mock_playlist = Playlist(
            playlist_id="pl_test_123",
            user_id="usr_test_123",
            name="Original Name",
            playlist_type=PlaylistType.MANUAL,
            photo_ids=["photo_1"],
            shuffle=False,
            loop=True,
            transition_duration=5,
        )
        mock_repo.get_playlist.return_value = mock_playlist
        mock_repo.update_playlist.return_value = mock_playlist

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        request = PlaylistUpdateRequest(
            name="Updated Name",
            shuffle=True,
        )

        result = await service.update_playlist(
            playlist_id="pl_test_123",
            request=request,
            user_id="usr_test_123",
        )

        assert result is not None
        mock_repo.update_playlist.assert_called_once()


class TestMediaServicePlaylistDeleteGolden:
    """Characterization: Playlist delete current behavior"""

    async def test_delete_existing_playlist_returns_true(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: delete_playlist returns True for existing playlist"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import Playlist, PlaylistType

        mock_playlist = Playlist(
            playlist_id="pl_test_123",
            user_id="usr_test_123",
            name="Test Playlist",
            playlist_type=PlaylistType.MANUAL,
            photo_ids=[],
            shuffle=False,
            loop=True,
            transition_duration=5,
        )
        mock_repo.get_playlist.return_value = mock_playlist
        mock_repo.delete_playlist.return_value = True

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.delete_playlist(
            playlist_id="pl_test_123",
            user_id="usr_test_123",
        )

        assert result is True


# =============================================================================
# Rotation Schedule Operations - Current Behavior
# =============================================================================

class TestMediaServiceRotationScheduleCreateGolden:
    """Characterization: RotationSchedule creation current behavior"""

    async def test_create_rotation_schedule_returns_response(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: create_rotation_schedule returns RotationScheduleResponse"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import (
            RotationScheduleCreateRequest,
            ScheduleType,
            RotationScheduleResponse,
        )

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        request = RotationScheduleCreateRequest(
            frame_id="dev_frame_123",
            playlist_id="pl_test_123",
            schedule_type=ScheduleType.TIME_BASED,
            start_time="08:00",
            end_time="22:00",
        )

        result = await service.create_rotation_schedule(
            request=request,
            user_id="usr_test_123",
        )

        assert isinstance(result, RotationScheduleResponse)
        assert result.schedule_id is not None
        assert result.schedule_id.startswith("sch_")  # Actual prefix is sch_
        assert result.frame_id == "dev_frame_123"


# =============================================================================
# Photo Metadata Operations - Current Behavior
# =============================================================================

class TestMediaServicePhotoMetadataGolden:
    """Characterization: PhotoMetadata operations current behavior"""

    async def test_update_photo_metadata_returns_response(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: update_photo_metadata returns PhotoMetadataResponse"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import (
            PhotoMetadataUpdateRequest,
            PhotoMetadataResponse,
        )

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        request = PhotoMetadataUpdateRequest(
            ai_labels=["beach", "sunset", "vacation"],
            ai_scenes=["beach", "sunset"],
            quality_score=0.95,
        )

        result = await service.update_photo_metadata(
            file_id="file_test_123",
            user_id="usr_test_123",
            request=request,
        )

        assert isinstance(result, PhotoMetadataResponse)
        assert result.file_id == "file_test_123"

    async def test_get_photo_metadata_returns_response(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: get_photo_metadata returns PhotoMetadataResponse for existing metadata"""
        from microservices.media_service.media_service import MediaService
        from microservices.media_service.models import PhotoMetadata, PhotoMetadataResponse

        mock_metadata = PhotoMetadata(
            file_id="file_test_123",
            user_id="usr_test_123",
            ai_labels=["test"],
        )
        mock_repo.get_photo_metadata.return_value = mock_metadata

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.get_photo_metadata(
            file_id="file_test_123",
            user_id="usr_test_123",
        )

        assert isinstance(result, PhotoMetadataResponse)
        assert result.file_id == "file_test_123"

    async def test_get_nonexistent_metadata_returns_none(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: get_photo_metadata returns None for non-existent metadata"""
        from microservices.media_service.media_service import MediaService

        mock_repo.get_photo_metadata.return_value = None

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.get_photo_metadata(
            file_id="file_nonexistent",
            user_id="usr_test_123",
        )

        # Current behavior: returns None instead of raising error
        assert result is None


# =============================================================================
# Health Check - Current Behavior
# =============================================================================

class TestMediaServiceHealthGolden:
    """Characterization: Health check current behavior"""

    async def test_check_health_returns_dict(
        self, mock_repo, mock_event_bus
    ):
        """GOLDEN: check_health returns health status dict"""
        from microservices.media_service.media_service import MediaService

        mock_repo.check_connection = AsyncMock(return_value=True)

        service = MediaService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.check_health()

        assert isinstance(result, dict)
        assert "status" in result or "service" in result
