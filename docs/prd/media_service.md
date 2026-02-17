# Media Service - Product Requirements Document (PRD)

**Layer 2: Requirements & User Stories**

## Product Overview

The Media Service transforms raw photos into an organized, enriched, and display-optimized photo collection for smart digital frames. It provides AI-powered photo enhancement, smart curation, and efficient delivery.

---

## Epic 1: Photo Version Management

### E1-US1: Create Photo Version

**As a** User
**I want** to create AI-enhanced versions of my photos
**So that** my photos look professional on my digital frame

**Priority**: P0 (Must Have)
**Story Points**: 5

#### Acceptance Criteria

**AC1**: Create original version entry
- ✅ Given a file uploaded to storage
- ✅ When file.uploaded event received
- ✅ Then create PhotoMetadata record with file_id
- ✅ And set version_type=ORIGINAL

**AC2**: Create AI-enhanced version
- ✅ Given an original photo exists
- ✅ When user requests AI enhancement
- ✅ Then create PhotoVersion with type=AI_ENHANCED
- ✅ And send original to AI enhancement service
- ✅ And store enhanced result with new file_id
- ✅ And publish media.version.created event

**AC3**: Validation
- ✅ Version name required (1-255 chars)
- ✅ Version type must be valid enum value
- ✅ file_id must exist in storage service
- ✅ Returns 400 for invalid requests

#### Test Scenarios

```python
# Component Test
def test_create_photo_version_with_valid_data():
    request = make_version_create_request(
        photo_id="photo_123",
        version_type=PhotoVersionType.AI_ENHANCED,
        file_id="file_abc"
    )
    version = service.create_version(user_id, request)
    assert version.version_id.startswith("ver_")
    assert version.version_type == PhotoVersionType.AI_ENHANCED
```

---

### E1-US2: List Photo Versions

**As a** User
**I want** to see all versions of a photo
**So that** I can choose which version to display

**Priority**: P0
**Story Points**: 2

#### Acceptance Criteria

**AC1**: List versions for photo
- ✅ Given multiple versions exist for photo_id
- ✅ When GET /api/v1/media/photos/{photo_id}/versions
- ✅ Then return array of all versions
- ✅ And ordered by version_number DESC (newest first)

**AC2**: Include version metadata
- ✅ Each version includes: version_id, version_type, file_id, cloud_url
- ✅ Each version includes: is_current, version_number, created_at
- ✅ Current version marked with is_current=true

**AC3**: Empty state
- ✅ Given photo has no versions
- ✅ When list versions
- ✅ Then return empty array []

---

## Epic 2: Photo Metadata Management

### E2-US1: AI Photo Analysis

**As a** System
**I want** to automatically analyze uploaded photos
**So that** photos are searchable and organizable

**Priority**: P0
**Story Points**: 8

#### Acceptance Criteria

**AC1**: Trigger AI analysis on upload
- ✅ Given file.uploaded event received
- ✅ When photo file_id created
- ✅ Then send photo to AI service for analysis
- ✅ And wait for AI response (async)

**AC2**: Store AI analysis results
- ✅ AI service returns: labels, objects, scenes, colors, faces
- ✅ Store in PhotoMetadata.ai_labels, ai_objects, ai_scenes, ai_colors
- ✅ Store face detection results in face_detection JSON
- ✅ Publish media.metadata.updated event

**AC3**: Calculate quality score
- ✅ AI service returns: blur_score, brightness, contrast
- ✅ Calculate overall quality_score (0.0-1.0)
- ✅ quality_score = weighted_avg(sharpness, exposure, composition)
- ✅ Photos with score < 0.5 marked as "enhancement candidates"

**AC4**: EXIF extraction
- ✅ Extract camera_make, camera_model, lens_model from EXIF
- ✅ Extract focal_length, aperture, shutter_speed, iso
- ✅ Extract latitude, longitude from GPS data
- ✅ Geocode coordinates to location_name (if available)

#### Test Scenarios

```python
# Integration Test
@pytest.mark.integration
async def test_ai_analysis_on_upload():
    # Trigger upload event
    event = {"file_id": "file_123", "user_id": "user_001"}
    await event_handler.handle_file_uploaded(event)

    # Wait for AI processing
    await asyncio.sleep(2)

    # Verify metadata created
    metadata = await service.get_metadata("file_123", "user_001")
    assert len(metadata.ai_labels) > 0
    assert metadata.quality_score is not None
    assert 0.0 <= metadata.quality_score <= 1.0
```

---

### E2-US2: Get Photo Metadata

**As a** User
**I want** to view photo metadata and AI analysis
**So that** I understand what's in my photos

**Priority**: P1
**Story Points**: 2

#### Acceptance Criteria

**AC1**: Get metadata by file_id
- ✅ Given metadata exists for file_id
- ✅ When GET /api/v1/media/metadata/{file_id}
- ✅ Then return PhotoMetadataResponse
- ✅ And include EXIF, AI labels, quality score

**AC2**: Metadata not found
- ✅ Given file_id has no metadata
- ✅ When GET metadata
- ✅ Then return 404 Not Found

---

## Epic 3: Playlist Management

### E3-US1: Create Manual Playlist

**As a** User
**I want** to create custom playlists
**So that** I can organize photos for different occasions

**Priority**: P0
**Story Points**: 3

#### Acceptance Criteria

**AC1**: Create manual playlist
- ✅ Given valid PlaylistCreateRequest
- ✅ When POST /api/v1/media/playlists
- ✅ Then create Playlist with type=MANUAL
- ✅ And generate playlist_id
- ✅ And store photo_ids array
- ✅ And return PlaylistResponse

**AC2**: Validation
- ✅ name required (1-255 chars)
- ✅ playlist_type defaults to MANUAL
- ✅ photo_ids can be empty (populated later)
- ✅ transition_duration: 1-60 seconds
- ✅ Max 1000 photo_ids for manual playlists

**AC3**: Duplicate prevention
- ✅ Same photo_id can appear multiple times (for extended display)

#### Test Scenarios

```python
# Component Test
def test_create_manual_playlist():
    request = PlaylistCreateRequest(
        name="Family Vacation 2024",
        playlist_type=PlaylistType.MANUAL,
        photo_ids=["photo_1", "photo_2", "photo_3"],
        transition_duration=10
    )
    playlist = service.create_playlist(user_id, request)
    assert playlist.playlist_id.startswith("pl_")
    assert playlist.playlist_type == PlaylistType.MANUAL
    assert len(playlist.photo_ids) == 3
```

---

### E3-US2: Create Smart Playlist

**As a** User
**I want** to create auto-populating playlists based on criteria
**So that** new matching photos appear automatically

**Priority**: P1
**Story Points**: 8

#### Acceptance Criteria

**AC1**: Define smart criteria
- ✅ Given PlaylistCreateRequest with playlist_type=SMART
- ✅ When creating playlist
- ✅ Then store smart_criteria JSON
- ✅ And validate criteria structure

**AC2**: Supported criteria
- ✅ `ai_labels_contains`: Array of required labels
- ✅ `quality_score_min`: Minimum quality (0.0-1.0)
- ✅ `location_contains`: Location name substring
- ✅ `date_range`: {start_date, end_date}
- ✅ Criteria combined with AND logic

**AC3**: Auto-populate playlist
- ✅ When smart playlist created
- ✅ Then execute metadata query with criteria
- ✅ And populate photo_ids with matching photos
- ✅ And set photo_ids as read-only

**AC4**: Auto-update on new photos
- ✅ When new photo metadata created
- ✅ Then check if matches any smart playlist criteria
- ✅ And add photo_id to matching playlists
- ✅ And publish media.playlist.updated event

#### Test Scenarios

```python
# Logic Contract Test (BR-M007)
def test_smart_playlist_auto_population():
    # Create smart playlist for beach photos
    request = PlaylistCreateRequest(
        name="Beach Memories",
        playlist_type=PlaylistType.SMART,
        smart_criteria={
            "ai_scenes_contains": ["beach", "ocean"],
            "quality_score_min": 0.7
        }
    )
    playlist = service.create_playlist(user_id, request)

    # Verify initial population
    assert len(playlist.photo_ids) == 5  # Existing beach photos

    # Upload new beach photo
    new_photo = create_photo_with_metadata(
        ai_scenes=["beach", "sunset"],
        quality_score=0.85
    )

    # Verify auto-added to playlist
    updated_playlist = service.get_playlist(playlist.playlist_id, user_id)
    assert new_photo.photo_id in updated_playlist.photo_ids
```

---

### E3-US3: Update Playlist

**As a** User
**I want** to modify playlist settings and photos
**So that** I can refine my playlists over time

**Priority**: P1
**Story Points**: 3

#### Acceptance Criteria

**AC1**: Update manual playlist
- ✅ Given playlist_type=MANUAL
- ✅ When PUT /api/v1/media/playlists/{playlist_id}
- ✅ Then allow updating: name, description, photo_ids, settings

**AC2**: Update smart playlist (limited)
- ✅ Given playlist_type=SMART
- ✅ When updating playlist
- ✅ Then allow updating: name, description, smart_criteria
- ✅ But photo_ids is read-only (managed by criteria)

**AC3**: Re-populate on criteria change
- ✅ Given smart_criteria modified
- ✅ When playlist updated
- ✅ Then re-execute metadata query
- ✅ And replace photo_ids with new results

---

## Epic 4: Rotation Schedule Management

### E4-US1: Create Rotation Schedule

**As a** User
**I want** to schedule when playlists display on my frame
**So that** different photos show at different times

**Priority**: P0
**Story Points**: 5

#### Acceptance Criteria

**AC1**: Create continuous schedule
- ✅ Given ScheduleType.CONTINUOUS
- ✅ When creating schedule
- ✅ Then photos rotate 24/7
- ✅ And rotation_interval in seconds (default 10)

**AC2**: Create time-based schedule
- ✅ Given ScheduleType.TIME_BASED
- ✅ When creating schedule
- ✅ Then require start_time and end_time (HH:MM format)
- ✅ And require days_of_week array (0=Mon, 6=Sun)
- ✅ And only rotate during specified windows

**AC3**: Link to playlist
- ✅ Schedule must reference valid playlist_id
- ✅ Schedule must reference valid frame_id (device)
- ✅ One schedule per frame (latest wins)

#### Test Scenarios

```python
# Component Test
def test_create_time_based_schedule():
    request = RotationScheduleCreateRequest(
        frame_id="frame_001",
        playlist_id="pl_abc123",
        schedule_type=ScheduleType.TIME_BASED,
        start_time="08:00",
        end_time="22:00",
        days_of_week=[1, 2, 3, 4, 5],  # Weekdays only
        rotation_interval=15
    )
    schedule = service.create_schedule(user_id, request)
    assert schedule.schedule_type == ScheduleType.TIME_BASED
    assert schedule.rotation_interval == 15
```

---

### E4-US2: Get Active Schedule for Frame

**As a** Smart Frame Device
**I want** to get my rotation schedule
**So that** I know which photos to display

**Priority**: P0
**Story Points**: 2

#### Acceptance Criteria

**AC1**: Get schedule by frame_id
- ✅ Given frame has active schedule
- ✅ When GET /api/v1/media/schedules/frame/{frame_id}
- ✅ Then return active RotationScheduleResponse
- ✅ And include playlist details

**AC2**: No active schedule
- ✅ Given frame has no schedule or is_active=false
- ✅ When getting schedule
- ✅ Then return 404 Not Found

**AC3**: Expand playlist photos
- ✅ Given schedule has playlist_id
- ✅ When getting schedule
- ✅ Then optionally include ?expand_photos=true
- ✅ And return photo_ids array with full photo URLs

---

## Epic 5: Photo Cache Management

### E5-US1: Cache Photo for Frame

**As a** Smart Frame Device
**I want** to cache photos locally
**So that** I can display photos offline

**Priority**: P1
**Story Points**: 5

#### Acceptance Criteria

**AC1**: Request photo cache
- ✅ Given frame_id and photo_id
- ✅ When POST /api/v1/media/cache
- ✅ Then create PhotoCache with status=PENDING
- ✅ And trigger background download
- ✅ And return cache_id

**AC2**: Download and cache photo
- ✅ Background job gets photo from storage service
- ✅ Set cache_status=DOWNLOADING
- ✅ On success: status=CACHED, store cached_url
- ✅ On failure: status=FAILED, store error_message

**AC3**: Cache expiration
- ✅ Cached photos expire after 30 days
- ✅ Set expires_at = created_at + 30 days
- ✅ Expired photos re-downloaded if requested again

**AC4**: LRU eviction
- ✅ When frame storage reaches limit
- ✅ Then evict least-recently-used photos
- ✅ Based on last_accessed_at timestamp

#### Test Scenarios

```python
# Integration Test
@pytest.mark.integration
async def test_cache_photo_lifecycle():
    # Request cache
    cache = await service.create_cache(
        user_id, frame_id="frame_001", photo_id="photo_123"
    )
    assert cache.cache_status == CacheStatus.PENDING

    # Wait for download
    await asyncio.sleep(3)

    # Verify cached
    cache = await service.get_cache(cache.cache_id, user_id)
    assert cache.cache_status == CacheStatus.CACHED
    assert cache.cached_url is not None
```

---

### E5-US2: Get Cached Photos

**As a** Smart Frame Device
**I want** to list all cached photos
**So that** I can display them

**Priority**: P1
**Story Points**: 2

#### Acceptance Criteria

**AC1**: List cached photos for frame
- ✅ Given frame has cached photos
- ✅ When GET /api/v1/media/cache/frame/{frame_id}
- ✅ Then return array of PhotoCacheResponse
- ✅ And filter by cache_status=CACHED (exclude failed/expired)

**AC2**: Track cache hits
- ✅ When frame requests cached photo
- ✅ Then increment hit_count
- ✅ And update last_accessed_at

---

## Non-Functional Requirements

### Performance

| Metric | Target | Priority |
|--------|--------|----------|
| Photo metadata creation | < 5 seconds (p95) | P0 |
| AI analysis latency | < 10 seconds (p95) | P1 |
| AI enhancement latency | < 30 seconds (p95) | P1 |
| Playlist query response | < 500ms (p95) | P0 |
| Cache hit rate | > 90% | P1 |

### Scalability

- Support 1M photos with metadata
- Support 100K active playlists
- Support 10K smart frames with schedules
- Handle 1000 concurrent cache downloads

### Availability

- 99.9% uptime SLA
- Graceful degradation if AI service unavailable
- Cache continues working offline

---

## API Surface Summary

### Photo Versions
- `POST /api/v1/media/photos/{photo_id}/versions` - Create version
- `GET /api/v1/media/photos/{photo_id}/versions` - List versions
- `DELETE /api/v1/media/photos/{photo_id}/versions/{version_id}` - Delete version

### Metadata
- `GET /api/v1/media/metadata/{file_id}` - Get metadata
- `PUT /api/v1/media/metadata/{file_id}` - Update metadata

### Playlists
- `POST /api/v1/media/playlists` - Create playlist
- `GET /api/v1/media/playlists` - List playlists
- `GET /api/v1/media/playlists/{playlist_id}` - Get playlist
- `PUT /api/v1/media/playlists/{playlist_id}` - Update playlist
- `DELETE /api/v1/media/playlists/{playlist_id}` - Delete playlist

### Rotation Schedules
- `POST /api/v1/media/schedules` - Create schedule
- `GET /api/v1/media/schedules/frame/{frame_id}` - Get frame schedule
- `PUT /api/v1/media/schedules/{schedule_id}` - Update schedule
- `DELETE /api/v1/media/schedules/{schedule_id}` - Delete schedule

### Photo Cache
- `POST /api/v1/media/cache` - Cache photo
- `GET /api/v1/media/cache/frame/{frame_id}` - List cached photos
- `DELETE /api/v1/media/cache/{cache_id}` - Clear cache entry

---

## Related Documents

- **Domain**: [docs/domain/media_service.md](../domain/media_service.md)
- **Design**: [docs/design/media_service.md](../design/media_service.md)
- **Data Contract**: [tests/contracts/media/data_contract.py](../../tests/contracts/media/data_contract.py)
- **Logic Contract**: [tests/contracts/media/logic_contract.md](../../tests/contracts/media/logic_contract.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: Product Team
