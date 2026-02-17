"""
Unit Golden Tests: Media Service Models

Tests model validation and serialization without external dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.media_service.models import (
    # Enums
    PhotoVersionType,
    PlaylistType,
    CacheStatus,
    ScheduleType,
    # Core Models
    PhotoVersion,
    PhotoMetadata,
    Playlist,
    RotationSchedule,
    PhotoCache,
    # Request Models
    PhotoVersionCreateRequest,
    PlaylistCreateRequest,
    PlaylistUpdateRequest,
    RotationScheduleCreateRequest,
    PhotoMetadataUpdateRequest,
    # Response Models
    PhotoVersionResponse,
    PhotoMetadataResponse,
    PlaylistResponse,
    RotationScheduleResponse,
    PhotoCacheResponse,
)


# ==================== Enum Tests ====================

class TestPhotoVersionType:
    """Test PhotoVersionType enum"""

    def test_photo_version_type_values(self):
        """Test all photo version type values are defined"""
        assert PhotoVersionType.ORIGINAL.value == "original"
        assert PhotoVersionType.AI_ENHANCED.value == "ai_enhanced"
        assert PhotoVersionType.AI_STYLED.value == "ai_styled"
        assert PhotoVersionType.AI_BACKGROUND_REMOVED.value == "ai_background_removed"
        assert PhotoVersionType.USER_EDITED.value == "user_edited"

    def test_photo_version_type_comparison(self):
        """Test photo version type comparison"""
        assert PhotoVersionType.ORIGINAL.value == "original"
        assert PhotoVersionType.ORIGINAL != PhotoVersionType.AI_ENHANCED
        assert PhotoVersionType.AI_STYLED == PhotoVersionType.AI_STYLED


class TestPlaylistType:
    """Test PlaylistType enum"""

    def test_playlist_type_values(self):
        """Test all playlist type values are defined"""
        assert PlaylistType.MANUAL.value == "manual"
        assert PlaylistType.SMART.value == "smart"
        assert PlaylistType.AI_CURATED.value == "ai_curated"

    def test_playlist_type_comparison(self):
        """Test playlist type comparison"""
        assert PlaylistType.MANUAL.value == "manual"
        assert PlaylistType.MANUAL != PlaylistType.SMART
        assert PlaylistType.AI_CURATED == PlaylistType.AI_CURATED


class TestCacheStatus:
    """Test CacheStatus enum"""

    def test_cache_status_values(self):
        """Test all cache status values are defined"""
        assert CacheStatus.PENDING.value == "pending"
        assert CacheStatus.DOWNLOADING.value == "downloading"
        assert CacheStatus.CACHED.value == "cached"
        assert CacheStatus.FAILED.value == "failed"
        assert CacheStatus.EXPIRED.value == "expired"

    def test_cache_status_comparison(self):
        """Test cache status comparison"""
        assert CacheStatus.PENDING.value == "pending"
        assert CacheStatus.CACHED != CacheStatus.FAILED
        assert CacheStatus.EXPIRED == CacheStatus.EXPIRED


class TestScheduleType:
    """Test ScheduleType enum"""

    def test_schedule_type_values(self):
        """Test all schedule type values are defined"""
        assert ScheduleType.CONTINUOUS.value == "continuous"
        assert ScheduleType.TIME_BASED.value == "time_based"
        assert ScheduleType.EVENT_BASED.value == "event_based"

    def test_schedule_type_comparison(self):
        """Test schedule type comparison"""
        assert ScheduleType.CONTINUOUS.value == "continuous"
        assert ScheduleType.TIME_BASED != ScheduleType.EVENT_BASED
        assert ScheduleType.CONTINUOUS == ScheduleType.CONTINUOUS


# ==================== Core Model Tests ====================

class TestPhotoVersion:
    """Test PhotoVersion model"""

    def test_photo_version_creation_minimal(self):
        """Test creating photo version with minimal required fields"""
        version = PhotoVersion(
            version_id="ver_123",
            photo_id="photo_456",
            user_id="user_789",
            version_name="Enhanced Version",
            version_type=PhotoVersionType.AI_ENHANCED,
            file_id="file_001"
        )

        assert version.version_id == "ver_123"
        assert version.photo_id == "photo_456"
        assert version.user_id == "user_789"
        assert version.version_name == "Enhanced Version"
        assert version.version_type == PhotoVersionType.AI_ENHANCED
        assert version.file_id == "file_001"
        assert version.is_current is False
        assert version.version_number == 1
        assert version.processing_params == {}
        assert version.metadata == {}

    def test_photo_version_creation_with_all_fields(self):
        """Test creating photo version with all fields"""
        now = datetime.now(timezone.utc)
        processing_params = {"brightness": 1.2, "contrast": 1.1}
        metadata = {"source": "ai_processor", "model": "v2"}

        version = PhotoVersion(
            version_id="ver_456",
            photo_id="photo_789",
            user_id="user_123",
            organization_id="org_456",
            version_name="Styled Version",
            version_type=PhotoVersionType.AI_STYLED,
            processing_mode="auto_enhance",
            file_id="file_002",
            cloud_url="https://cdn.example.com/photo.jpg",
            local_path="/storage/photo.jpg",
            file_size=2048000,
            processing_params=processing_params,
            metadata=metadata,
            is_current=True,
            version_number=3,
            created_at=now,
            updated_at=now
        )

        assert version.version_id == "ver_456"
        assert version.organization_id == "org_456"
        assert version.processing_mode == "auto_enhance"
        assert version.cloud_url == "https://cdn.example.com/photo.jpg"
        assert version.local_path == "/storage/photo.jpg"
        assert version.file_size == 2048000
        assert version.processing_params == processing_params
        assert version.metadata == metadata
        assert version.is_current is True
        assert version.version_number == 3
        assert version.created_at == now

    def test_photo_version_json_parsing(self):
        """Test photo version with JSON string parsing"""
        version = PhotoVersion(
            version_id="ver_789",
            photo_id="photo_001",
            user_id="user_001",
            version_name="Test",
            version_type=PhotoVersionType.ORIGINAL,
            file_id="file_003",
            processing_params='{"filter": "sepia"}',
            metadata='{"tag": "test"}'
        )

        assert version.processing_params == {"filter": "sepia"}
        assert version.metadata == {"tag": "test"}

    def test_photo_version_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            PhotoVersion(
                version_id="ver_123",
                user_id="user_123"
            )

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "photo_id" in missing_fields
        assert "version_name" in missing_fields
        assert "version_type" in missing_fields
        assert "file_id" in missing_fields


class TestPhotoMetadata:
    """Test PhotoMetadata model"""

    def test_photo_metadata_creation_minimal(self):
        """Test creating photo metadata with minimal fields"""
        metadata = PhotoMetadata(
            file_id="file_123",
            user_id="user_456"
        )

        assert metadata.file_id == "file_123"
        assert metadata.user_id == "user_456"
        assert metadata.ai_labels == []
        assert metadata.ai_objects == []
        assert metadata.ai_scenes == []
        assert metadata.ai_colors == []
        assert metadata.full_metadata == {}

    def test_photo_metadata_with_exif_data(self):
        """Test photo metadata with EXIF data"""
        metadata = PhotoMetadata(
            file_id="file_456",
            user_id="user_789",
            camera_make="Canon",
            camera_model="EOS R5",
            lens_model="RF 24-70mm f/2.8",
            focal_length="50mm",
            aperture="f/2.8",
            shutter_speed="1/200",
            iso=400,
            flash_used=False
        )

        assert metadata.camera_make == "Canon"
        assert metadata.camera_model == "EOS R5"
        assert metadata.lens_model == "RF 24-70mm f/2.8"
        assert metadata.focal_length == "50mm"
        assert metadata.aperture == "f/2.8"
        assert metadata.shutter_speed == "1/200"
        assert metadata.iso == 400
        assert metadata.flash_used is False

    def test_photo_metadata_with_location(self):
        """Test photo metadata with location data"""
        photo_time = datetime.now(timezone.utc)

        metadata = PhotoMetadata(
            file_id="file_789",
            user_id="user_001",
            latitude=37.7749,
            longitude=-122.4194,
            location_name="San Francisco, CA",
            photo_taken_at=photo_time
        )

        assert metadata.latitude == 37.7749
        assert metadata.longitude == -122.4194
        assert metadata.location_name == "San Francisco, CA"
        assert metadata.photo_taken_at == photo_time

    def test_photo_metadata_with_ai_analysis(self):
        """Test photo metadata with AI analysis data"""
        face_data = {"faces": [{"x": 100, "y": 200, "confidence": 0.95}]}
        text_data = {"text": ["Sign", "Street"], "language": "en"}

        metadata = PhotoMetadata(
            file_id="file_001",
            user_id="user_002",
            ai_labels=["outdoor", "nature", "landscape"],
            ai_objects=["tree", "mountain", "sky"],
            ai_scenes=["mountain_view", "sunset"],
            ai_colors=["blue", "orange", "green"],
            face_detection=face_data,
            text_detection=text_data,
            quality_score=8.5,
            blur_score=0.1,
            brightness=0.7,
            contrast=0.8
        )

        assert metadata.ai_labels == ["outdoor", "nature", "landscape"]
        assert metadata.ai_objects == ["tree", "mountain", "sky"]
        assert metadata.ai_scenes == ["mountain_view", "sunset"]
        assert metadata.ai_colors == ["blue", "orange", "green"]
        assert metadata.face_detection == face_data
        assert metadata.text_detection == text_data
        assert metadata.quality_score == 8.5
        assert metadata.blur_score == 0.1
        assert metadata.brightness == 0.7
        assert metadata.contrast == 0.8

    def test_photo_metadata_json_parsing(self):
        """Test photo metadata with JSON string parsing"""
        metadata = PhotoMetadata(
            file_id="file_002",
            user_id="user_003",
            ai_labels='["person", "indoor"]',
            ai_objects='["chair", "table"]',
            face_detection='{"count": 2}',
            full_metadata='{"raw": "data"}'
        )

        assert metadata.ai_labels == ["person", "indoor"]
        assert metadata.ai_objects == ["chair", "table"]
        assert metadata.face_detection == {"count": 2}
        assert metadata.full_metadata == {"raw": "data"}


class TestPlaylist:
    """Test Playlist model"""

    def test_playlist_creation_minimal(self):
        """Test creating playlist with minimal fields"""
        playlist = Playlist(
            playlist_id="pls_123",
            name="My Vacation Photos",
            user_id="user_456"
        )

        assert playlist.playlist_id == "pls_123"
        assert playlist.name == "My Vacation Photos"
        assert playlist.user_id == "user_456"
        assert playlist.playlist_type == PlaylistType.MANUAL
        assert playlist.photo_ids == []
        assert playlist.shuffle is False
        assert playlist.loop is True
        assert playlist.transition_duration == 5

    def test_playlist_creation_with_all_fields(self):
        """Test creating playlist with all fields"""
        now = datetime.now(timezone.utc)
        photo_ids = ["photo_1", "photo_2", "photo_3"]
        smart_criteria = {"tag": "vacation", "year": 2024}

        playlist = Playlist(
            playlist_id="pls_456",
            name="Smart Vacation Mix",
            description="AI-curated vacation memories",
            user_id="user_789",
            organization_id="org_123",
            playlist_type=PlaylistType.AI_CURATED,
            smart_criteria=smart_criteria,
            photo_ids=photo_ids,
            shuffle=True,
            loop=False,
            transition_duration=10,
            created_at=now,
            updated_at=now
        )

        assert playlist.playlist_id == "pls_456"
        assert playlist.name == "Smart Vacation Mix"
        assert playlist.description == "AI-curated vacation memories"
        assert playlist.organization_id == "org_123"
        assert playlist.playlist_type == PlaylistType.AI_CURATED
        assert playlist.smart_criteria == smart_criteria
        assert playlist.photo_ids == photo_ids
        assert playlist.shuffle is True
        assert playlist.loop is False
        assert playlist.transition_duration == 10

    def test_playlist_manual_type(self):
        """Test manual playlist"""
        playlist = Playlist(
            playlist_id="pls_manual",
            name="Favorite Photos",
            user_id="user_001",
            playlist_type=PlaylistType.MANUAL,
            photo_ids=["photo_a", "photo_b", "photo_c"]
        )

        assert playlist.playlist_type == PlaylistType.MANUAL
        assert len(playlist.photo_ids) == 3

    def test_playlist_smart_type(self):
        """Test smart playlist with criteria"""
        criteria = {
            "location": "San Francisco",
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"}
        }

        playlist = Playlist(
            playlist_id="pls_smart",
            name="SF 2024",
            user_id="user_002",
            playlist_type=PlaylistType.SMART,
            smart_criteria=criteria
        )

        assert playlist.playlist_type == PlaylistType.SMART
        assert playlist.smart_criteria == criteria

    def test_playlist_json_parsing(self):
        """Test playlist with JSON string parsing"""
        playlist = Playlist(
            playlist_id="pls_json",
            name="Test Playlist",
            user_id="user_003",
            photo_ids='["p1", "p2"]',
            smart_criteria='{"tag": "family"}'
        )

        assert playlist.photo_ids == ["p1", "p2"]
        assert playlist.smart_criteria == {"tag": "family"}

    def test_playlist_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Playlist(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "playlist_id" in missing_fields
        assert "name" in missing_fields


class TestRotationSchedule:
    """Test RotationSchedule model"""

    def test_rotation_schedule_creation_minimal(self):
        """Test creating rotation schedule with minimal fields"""
        schedule = RotationSchedule(
            schedule_id="sched_123",
            user_id="user_456",
            frame_id="frame_789"
        )

        assert schedule.schedule_id == "sched_123"
        assert schedule.user_id == "user_456"
        assert schedule.frame_id == "frame_789"
        assert schedule.schedule_type == ScheduleType.CONTINUOUS
        assert schedule.rotation_interval == 10
        assert schedule.shuffle is False
        assert schedule.is_active is True
        assert schedule.days_of_week == []

    def test_rotation_schedule_continuous(self):
        """Test continuous rotation schedule"""
        schedule = RotationSchedule(
            schedule_id="sched_cont",
            user_id="user_001",
            frame_id="frame_001",
            playlist_id="pls_001",
            schedule_type=ScheduleType.CONTINUOUS,
            rotation_interval=15,
            shuffle=True
        )

        assert schedule.schedule_type == ScheduleType.CONTINUOUS
        assert schedule.rotation_interval == 15
        assert schedule.shuffle is True

    def test_rotation_schedule_time_based(self):
        """Test time-based rotation schedule"""
        schedule = RotationSchedule(
            schedule_id="sched_time",
            user_id="user_002",
            frame_id="frame_002",
            playlist_id="pls_002",
            schedule_type=ScheduleType.TIME_BASED,
            start_time="09:00",
            end_time="17:00",
            days_of_week=[1, 2, 3, 4, 5],  # Weekdays
            rotation_interval=30
        )

        assert schedule.schedule_type == ScheduleType.TIME_BASED
        assert schedule.start_time == "09:00"
        assert schedule.end_time == "17:00"
        assert schedule.days_of_week == [1, 2, 3, 4, 5]
        assert schedule.rotation_interval == 30

    def test_rotation_schedule_event_based(self):
        """Test event-based rotation schedule"""
        schedule = RotationSchedule(
            schedule_id="sched_event",
            user_id="user_003",
            frame_id="frame_003",
            schedule_type=ScheduleType.EVENT_BASED,
            is_active=True
        )

        assert schedule.schedule_type == ScheduleType.EVENT_BASED
        assert schedule.is_active is True

    def test_rotation_schedule_json_parsing(self):
        """Test rotation schedule with JSON string parsing"""
        schedule = RotationSchedule(
            schedule_id="sched_json",
            user_id="user_004",
            frame_id="frame_004",
            days_of_week='[0, 6]'  # Weekend
        )

        assert schedule.days_of_week == [0, 6]

    def test_rotation_schedule_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            RotationSchedule(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "schedule_id" in missing_fields
        assert "frame_id" in missing_fields


class TestPhotoCache:
    """Test PhotoCache model"""

    def test_photo_cache_creation_minimal(self):
        """Test creating photo cache with minimal fields"""
        cache = PhotoCache(
            cache_id="cache_123",
            user_id="user_456",
            frame_id="frame_789",
            photo_id="photo_001"
        )

        assert cache.cache_id == "cache_123"
        assert cache.user_id == "user_456"
        assert cache.frame_id == "frame_789"
        assert cache.photo_id == "photo_001"
        assert cache.cache_status == CacheStatus.PENDING
        assert cache.hit_count == 0
        assert cache.retry_count == 0

    def test_photo_cache_creation_with_all_fields(self):
        """Test creating photo cache with all fields"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)

        cache = PhotoCache(
            cache_id="cache_456",
            user_id="user_789",
            frame_id="frame_001",
            photo_id="photo_002",
            version_id="ver_001",
            cache_status=CacheStatus.CACHED,
            cached_url="https://cache.example.com/photo.jpg",
            local_path="/cache/photo.jpg",
            cache_size=1024000,
            cache_format="jpeg",
            cache_quality="high",
            hit_count=42,
            last_accessed_at=now,
            retry_count=0,
            created_at=now,
            updated_at=now,
            expires_at=expires
        )

        assert cache.cache_id == "cache_456"
        assert cache.version_id == "ver_001"
        assert cache.cache_status == CacheStatus.CACHED
        assert cache.cached_url == "https://cache.example.com/photo.jpg"
        assert cache.local_path == "/cache/photo.jpg"
        assert cache.cache_size == 1024000
        assert cache.cache_format == "jpeg"
        assert cache.cache_quality == "high"
        assert cache.hit_count == 42
        assert cache.last_accessed_at == now
        assert cache.expires_at == expires

    def test_photo_cache_pending_status(self):
        """Test photo cache with pending status"""
        cache = PhotoCache(
            cache_id="cache_pending",
            user_id="user_001",
            frame_id="frame_001",
            photo_id="photo_001",
            cache_status=CacheStatus.PENDING
        )

        assert cache.cache_status == CacheStatus.PENDING

    def test_photo_cache_downloading_status(self):
        """Test photo cache with downloading status"""
        cache = PhotoCache(
            cache_id="cache_download",
            user_id="user_002",
            frame_id="frame_002",
            photo_id="photo_002",
            cache_status=CacheStatus.DOWNLOADING
        )

        assert cache.cache_status == CacheStatus.DOWNLOADING

    def test_photo_cache_failed_status(self):
        """Test photo cache with failed status"""
        cache = PhotoCache(
            cache_id="cache_failed",
            user_id="user_003",
            frame_id="frame_003",
            photo_id="photo_003",
            cache_status=CacheStatus.FAILED,
            error_message="Network timeout",
            retry_count=3
        )

        assert cache.cache_status == CacheStatus.FAILED
        assert cache.error_message == "Network timeout"
        assert cache.retry_count == 3

    def test_photo_cache_expired_status(self):
        """Test photo cache with expired status"""
        past = datetime.now(timezone.utc) - timedelta(days=1)

        cache = PhotoCache(
            cache_id="cache_expired",
            user_id="user_004",
            frame_id="frame_004",
            photo_id="photo_004",
            cache_status=CacheStatus.EXPIRED,
            expires_at=past
        )

        assert cache.cache_status == CacheStatus.EXPIRED
        assert cache.expires_at < datetime.now(timezone.utc)

    def test_photo_cache_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            PhotoCache(cache_id="cache_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "user_id" in missing_fields
        assert "frame_id" in missing_fields
        assert "photo_id" in missing_fields


# ==================== Request Model Tests ====================

class TestPhotoVersionCreateRequest:
    """Test PhotoVersionCreateRequest model"""

    def test_photo_version_create_request_minimal(self):
        """Test minimal photo version creation request"""
        request = PhotoVersionCreateRequest(
            photo_id="photo_123",
            version_name="Enhanced",
            version_type=PhotoVersionType.AI_ENHANCED,
            file_id="file_456"
        )

        assert request.photo_id == "photo_123"
        assert request.version_name == "Enhanced"
        assert request.version_type == PhotoVersionType.AI_ENHANCED
        assert request.file_id == "file_456"
        assert request.processing_mode is None
        assert request.processing_params is None

    def test_photo_version_create_request_with_all_fields(self):
        """Test photo version creation request with all fields"""
        params = {"brightness": 1.3, "saturation": 1.2}

        request = PhotoVersionCreateRequest(
            photo_id="photo_456",
            version_name="Styled Portrait",
            version_type=PhotoVersionType.AI_STYLED,
            processing_mode="portrait_enhance",
            file_id="file_789",
            processing_params=params
        )

        assert request.photo_id == "photo_456"
        assert request.version_name == "Styled Portrait"
        assert request.version_type == PhotoVersionType.AI_STYLED
        assert request.processing_mode == "portrait_enhance"
        assert request.file_id == "file_789"
        assert request.processing_params == params

    def test_photo_version_create_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            PhotoVersionCreateRequest(photo_id="photo_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "version_name" in missing_fields
        assert "version_type" in missing_fields
        assert "file_id" in missing_fields


class TestPlaylistCreateRequest:
    """Test PlaylistCreateRequest model"""

    def test_playlist_create_request_minimal(self):
        """Test minimal playlist creation request"""
        request = PlaylistCreateRequest(
            name="My Playlist"
        )

        assert request.name == "My Playlist"
        assert request.description is None
        assert request.playlist_type == PlaylistType.MANUAL
        assert request.photo_ids == []
        assert request.smart_criteria is None
        assert request.shuffle is False
        assert request.loop is True
        assert request.transition_duration == 5

    def test_playlist_create_request_manual_with_photos(self):
        """Test manual playlist creation request with photos"""
        photo_ids = ["photo_1", "photo_2", "photo_3", "photo_4"]

        request = PlaylistCreateRequest(
            name="Summer Vacation",
            description="Best moments from summer 2024",
            playlist_type=PlaylistType.MANUAL,
            photo_ids=photo_ids,
            shuffle=True,
            loop=True,
            transition_duration=8
        )

        assert request.name == "Summer Vacation"
        assert request.description == "Best moments from summer 2024"
        assert request.playlist_type == PlaylistType.MANUAL
        assert request.photo_ids == photo_ids
        assert request.shuffle is True
        assert request.loop is True
        assert request.transition_duration == 8

    def test_playlist_create_request_smart(self):
        """Test smart playlist creation request"""
        criteria = {
            "tags": ["family", "vacation"],
            "location": "Hawaii",
            "date_range": {"start": "2024-06-01", "end": "2024-08-31"}
        }

        request = PlaylistCreateRequest(
            name="Smart Summer Mix",
            playlist_type=PlaylistType.SMART,
            smart_criteria=criteria,
            transition_duration=10
        )

        assert request.name == "Smart Summer Mix"
        assert request.playlist_type == PlaylistType.SMART
        assert request.smart_criteria == criteria
        assert request.transition_duration == 10

    def test_playlist_create_request_ai_curated(self):
        """Test AI-curated playlist creation request"""
        request = PlaylistCreateRequest(
            name="AI Best Moments",
            description="AI-selected best photos",
            playlist_type=PlaylistType.AI_CURATED,
            shuffle=False,
            transition_duration=7
        )

        assert request.name == "AI Best Moments"
        assert request.playlist_type == PlaylistType.AI_CURATED

    def test_playlist_create_request_transition_duration_validation(self):
        """Test transition duration validation (1-60 seconds)"""
        # Valid durations
        request1 = PlaylistCreateRequest(name="Test1", transition_duration=1)
        request2 = PlaylistCreateRequest(name="Test2", transition_duration=60)
        assert request1.transition_duration == 1
        assert request2.transition_duration == 60

        # Invalid durations
        with pytest.raises(ValidationError):
            PlaylistCreateRequest(name="Test3", transition_duration=0)

        with pytest.raises(ValidationError):
            PlaylistCreateRequest(name="Test4", transition_duration=61)

    def test_playlist_create_request_name_validation(self):
        """Test name validation (min_length=1)"""
        with pytest.raises(ValidationError):
            PlaylistCreateRequest(name="")


class TestPlaylistUpdateRequest:
    """Test PlaylistUpdateRequest model"""

    def test_playlist_update_request_partial(self):
        """Test partial playlist update request"""
        request = PlaylistUpdateRequest(
            name="Updated Name",
            description="Updated description"
        )

        assert request.name == "Updated Name"
        assert request.description == "Updated description"
        assert request.photo_ids is None
        assert request.smart_criteria is None
        assert request.shuffle is None
        assert request.loop is None
        assert request.transition_duration is None

    def test_playlist_update_request_all_fields(self):
        """Test playlist update request with all fields"""
        photo_ids = ["new_1", "new_2"]
        criteria = {"tag": "new_tag"}

        request = PlaylistUpdateRequest(
            name="New Name",
            description="New description",
            photo_ids=photo_ids,
            smart_criteria=criteria,
            shuffle=True,
            loop=False,
            transition_duration=12
        )

        assert request.name == "New Name"
        assert request.description == "New description"
        assert request.photo_ids == photo_ids
        assert request.smart_criteria == criteria
        assert request.shuffle is True
        assert request.loop is False
        assert request.transition_duration == 12

    def test_playlist_update_request_only_photos(self):
        """Test updating only photo list"""
        request = PlaylistUpdateRequest(
            photo_ids=["p1", "p2", "p3"]
        )

        assert request.photo_ids == ["p1", "p2", "p3"]
        assert request.name is None

    def test_playlist_update_request_only_settings(self):
        """Test updating only playback settings"""
        request = PlaylistUpdateRequest(
            shuffle=True,
            loop=False,
            transition_duration=15
        )

        assert request.shuffle is True
        assert request.loop is False
        assert request.transition_duration == 15

    def test_playlist_update_request_transition_duration_validation(self):
        """Test transition duration validation in update"""
        # Valid
        request = PlaylistUpdateRequest(transition_duration=30)
        assert request.transition_duration == 30

        # Invalid
        with pytest.raises(ValidationError):
            PlaylistUpdateRequest(transition_duration=0)

        with pytest.raises(ValidationError):
            PlaylistUpdateRequest(transition_duration=100)


class TestRotationScheduleCreateRequest:
    """Test RotationScheduleCreateRequest model"""

    def test_rotation_schedule_create_request_minimal(self):
        """Test minimal rotation schedule creation request"""
        request = RotationScheduleCreateRequest(
            frame_id="frame_123",
            playlist_id="pls_456"
        )

        assert request.frame_id == "frame_123"
        assert request.playlist_id == "pls_456"
        assert request.schedule_type == ScheduleType.CONTINUOUS
        assert request.start_time is None
        assert request.end_time is None
        assert request.days_of_week == []
        assert request.rotation_interval == 10
        assert request.shuffle is False

    def test_rotation_schedule_create_request_continuous(self):
        """Test continuous rotation schedule creation"""
        request = RotationScheduleCreateRequest(
            frame_id="frame_001",
            playlist_id="pls_001",
            schedule_type=ScheduleType.CONTINUOUS,
            rotation_interval=20,
            shuffle=True
        )

        assert request.schedule_type == ScheduleType.CONTINUOUS
        assert request.rotation_interval == 20
        assert request.shuffle is True

    def test_rotation_schedule_create_request_time_based(self):
        """Test time-based rotation schedule creation"""
        request = RotationScheduleCreateRequest(
            frame_id="frame_002",
            playlist_id="pls_002",
            schedule_type=ScheduleType.TIME_BASED,
            start_time="08:00",
            end_time="18:00",
            days_of_week=[1, 2, 3, 4, 5],
            rotation_interval=30
        )

        assert request.schedule_type == ScheduleType.TIME_BASED
        assert request.start_time == "08:00"
        assert request.end_time == "18:00"
        assert request.days_of_week == [1, 2, 3, 4, 5]
        assert request.rotation_interval == 30

    def test_rotation_schedule_create_request_event_based(self):
        """Test event-based rotation schedule creation"""
        request = RotationScheduleCreateRequest(
            frame_id="frame_003",
            playlist_id="pls_003",
            schedule_type=ScheduleType.EVENT_BASED,
            rotation_interval=5
        )

        assert request.schedule_type == ScheduleType.EVENT_BASED
        assert request.rotation_interval == 5

    def test_rotation_schedule_create_request_interval_validation(self):
        """Test rotation interval validation (ge=1)"""
        # Valid
        request = RotationScheduleCreateRequest(
            frame_id="frame_004",
            playlist_id="pls_004",
            rotation_interval=1
        )
        assert request.rotation_interval == 1

        # Invalid
        with pytest.raises(ValidationError):
            RotationScheduleCreateRequest(
                frame_id="frame_005",
                playlist_id="pls_005",
                rotation_interval=0
            )

    def test_rotation_schedule_create_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            RotationScheduleCreateRequest(frame_id="frame_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "playlist_id" in missing_fields


class TestPhotoMetadataUpdateRequest:
    """Test PhotoMetadataUpdateRequest model"""

    def test_photo_metadata_update_request_partial(self):
        """Test partial metadata update request"""
        request = PhotoMetadataUpdateRequest(
            ai_labels=["outdoor", "nature"]
        )

        assert request.ai_labels == ["outdoor", "nature"]
        assert request.ai_objects is None
        assert request.quality_score is None

    def test_photo_metadata_update_request_all_fields(self):
        """Test metadata update request with all fields"""
        face_data = {"count": 3}

        request = PhotoMetadataUpdateRequest(
            ai_labels=["person", "indoor"],
            ai_objects=["chair", "table", "laptop"],
            ai_scenes=["office", "workspace"],
            ai_colors=["white", "gray", "black"],
            face_detection=face_data,
            quality_score=9.2
        )

        assert request.ai_labels == ["person", "indoor"]
        assert request.ai_objects == ["chair", "table", "laptop"]
        assert request.ai_scenes == ["office", "workspace"]
        assert request.ai_colors == ["white", "gray", "black"]
        assert request.face_detection == face_data
        assert request.quality_score == 9.2

    def test_photo_metadata_update_request_only_quality(self):
        """Test updating only quality score"""
        request = PhotoMetadataUpdateRequest(
            quality_score=7.5
        )

        assert request.quality_score == 7.5


# ==================== Response Model Tests ====================

class TestPhotoVersionResponse:
    """Test PhotoVersionResponse model"""

    def test_photo_version_response_creation(self):
        """Test creating photo version response"""
        now = datetime.now(timezone.utc)

        response = PhotoVersionResponse(
            version_id="ver_123",
            photo_id="photo_456",
            user_id="user_789",
            version_name="Enhanced Version",
            version_type=PhotoVersionType.AI_ENHANCED,
            file_id="file_001",
            cloud_url="https://cdn.example.com/photo.jpg",
            file_size=2048000,
            is_current=True,
            version_number=2,
            created_at=now
        )

        assert response.version_id == "ver_123"
        assert response.photo_id == "photo_456"
        assert response.user_id == "user_789"
        assert response.version_name == "Enhanced Version"
        assert response.version_type == PhotoVersionType.AI_ENHANCED
        assert response.file_id == "file_001"
        assert response.cloud_url == "https://cdn.example.com/photo.jpg"
        assert response.file_size == 2048000
        assert response.is_current is True
        assert response.version_number == 2
        assert response.created_at == now

    def test_photo_version_response_minimal(self):
        """Test photo version response with minimal fields"""
        response = PhotoVersionResponse(
            version_id="ver_min",
            photo_id="photo_min",
            user_id="user_min",
            version_name="Original",
            version_type=PhotoVersionType.ORIGINAL,
            file_id="file_min",
            cloud_url=None,
            file_size=None,
            is_current=False,
            version_number=1,
            created_at=None
        )

        assert response.version_id == "ver_min"
        assert response.cloud_url is None
        assert response.file_size is None


class TestPhotoMetadataResponse:
    """Test PhotoMetadataResponse model"""

    def test_photo_metadata_response_creation(self):
        """Test creating photo metadata response"""
        now = datetime.now(timezone.utc)

        response = PhotoMetadataResponse(
            file_id="file_123",
            camera_model="Canon EOS R5",
            location_name="Yosemite National Park",
            photo_taken_at=now,
            ai_labels=["outdoor", "nature", "mountain"],
            ai_objects=["tree", "rock", "sky"],
            ai_scenes=["mountain_landscape"],
            quality_score=9.1,
            full_metadata={"exif": "data"}
        )

        assert response.file_id == "file_123"
        assert response.camera_model == "Canon EOS R5"
        assert response.location_name == "Yosemite National Park"
        assert response.photo_taken_at == now
        assert response.ai_labels == ["outdoor", "nature", "mountain"]
        assert response.ai_objects == ["tree", "rock", "sky"]
        assert response.ai_scenes == ["mountain_landscape"]
        assert response.quality_score == 9.1
        assert response.full_metadata == {"exif": "data"}

    def test_photo_metadata_response_minimal(self):
        """Test photo metadata response with minimal fields"""
        response = PhotoMetadataResponse(
            file_id="file_min",
            camera_model=None,
            location_name=None,
            photo_taken_at=None,
            ai_labels=[],
            ai_objects=[],
            ai_scenes=[],
            quality_score=None
        )

        assert response.file_id == "file_min"
        assert response.ai_labels == []
        assert response.full_metadata == {}


class TestPlaylistResponse:
    """Test PlaylistResponse model"""

    def test_playlist_response_creation(self):
        """Test creating playlist response"""
        now = datetime.now(timezone.utc)
        photo_ids = ["photo_1", "photo_2", "photo_3"]

        response = PlaylistResponse(
            playlist_id="pls_123",
            name="Vacation Photos",
            description="Summer 2024 highlights",
            user_id="user_456",
            playlist_type=PlaylistType.MANUAL,
            photo_ids=photo_ids,
            shuffle=True,
            loop=True,
            transition_duration=8,
            created_at=now,
            updated_at=now
        )

        assert response.playlist_id == "pls_123"
        assert response.name == "Vacation Photos"
        assert response.description == "Summer 2024 highlights"
        assert response.user_id == "user_456"
        assert response.playlist_type == PlaylistType.MANUAL
        assert response.photo_ids == photo_ids
        assert response.shuffle is True
        assert response.loop is True
        assert response.transition_duration == 8
        assert response.created_at == now

    def test_playlist_response_smart_type(self):
        """Test smart playlist response"""
        response = PlaylistResponse(
            playlist_id="pls_smart",
            name="Smart Mix",
            description=None,
            user_id="user_789",
            playlist_type=PlaylistType.SMART,
            photo_ids=[],
            shuffle=False,
            loop=True,
            transition_duration=5,
            created_at=None,
            updated_at=None
        )

        assert response.playlist_type == PlaylistType.SMART
        assert response.photo_ids == []


class TestRotationScheduleResponse:
    """Test RotationScheduleResponse model"""

    def test_rotation_schedule_response_creation(self):
        """Test creating rotation schedule response"""
        now = datetime.now(timezone.utc)

        response = RotationScheduleResponse(
            schedule_id="sched_123",
            frame_id="frame_456",
            playlist_id="pls_789",
            schedule_type=ScheduleType.TIME_BASED,
            rotation_interval=30,
            is_active=True,
            created_at=now
        )

        assert response.schedule_id == "sched_123"
        assert response.frame_id == "frame_456"
        assert response.playlist_id == "pls_789"
        assert response.schedule_type == ScheduleType.TIME_BASED
        assert response.rotation_interval == 30
        assert response.is_active is True
        assert response.created_at == now

    def test_rotation_schedule_response_continuous(self):
        """Test continuous rotation schedule response"""
        response = RotationScheduleResponse(
            schedule_id="sched_cont",
            frame_id="frame_001",
            playlist_id="pls_001",
            schedule_type=ScheduleType.CONTINUOUS,
            rotation_interval=10,
            is_active=True,
            created_at=None
        )

        assert response.schedule_type == ScheduleType.CONTINUOUS

    def test_rotation_schedule_response_inactive(self):
        """Test inactive rotation schedule response"""
        response = RotationScheduleResponse(
            schedule_id="sched_inactive",
            frame_id="frame_002",
            playlist_id=None,
            schedule_type=ScheduleType.CONTINUOUS,
            rotation_interval=10,
            is_active=False,
            created_at=None
        )

        assert response.is_active is False
        assert response.playlist_id is None


class TestPhotoCacheResponse:
    """Test PhotoCacheResponse model"""

    def test_photo_cache_response_creation(self):
        """Test creating photo cache response"""
        now = datetime.now(timezone.utc)

        response = PhotoCacheResponse(
            cache_id="cache_123",
            frame_id="frame_456",
            photo_id="photo_789",
            cache_status=CacheStatus.CACHED,
            hit_count=15,
            last_accessed_at=now
        )

        assert response.cache_id == "cache_123"
        assert response.frame_id == "frame_456"
        assert response.photo_id == "photo_789"
        assert response.cache_status == CacheStatus.CACHED
        assert response.hit_count == 15
        assert response.last_accessed_at == now

    def test_photo_cache_response_pending(self):
        """Test pending cache response"""
        response = PhotoCacheResponse(
            cache_id="cache_pending",
            frame_id="frame_001",
            photo_id="photo_001",
            cache_status=CacheStatus.PENDING,
            hit_count=0,
            last_accessed_at=None
        )

        assert response.cache_status == CacheStatus.PENDING
        assert response.hit_count == 0

    def test_photo_cache_response_failed(self):
        """Test failed cache response"""
        response = PhotoCacheResponse(
            cache_id="cache_failed",
            frame_id="frame_002",
            photo_id="photo_002",
            cache_status=CacheStatus.FAILED,
            hit_count=0,
            last_accessed_at=None
        )

        assert response.cache_status == CacheStatus.FAILED


if __name__ == "__main__":
    pytest.main([__file__])
