# Media Service - Logic Contract

**Layer 5: Business Rules & State Machines**

This document defines the business logic and rules for the Media Service, serving as the specification for behavior-driven tests.

---

## Business Rules

### Photo Version Rules

#### BR-M001: Version Uniqueness

**Rule**: Each photo can have multiple versions, but only one version can be marked as `is_current=true` at a time.

**Given**: A photo has 3 versions: original, AI-enhanced, AI-styled
**When**: User sets AI-styled as current
**Then**:
- AI-styled version has `is_current=true`
- Original and AI-enhanced have `is_current=false`
- Previous current version automatically unmarked

**Test Markers**: `@pytest.mark.component`, `@pytest.mark.logic_rule("BR-M001")`

**Example Test**:
```python
def test_br_m001_only_one_current_version():
    # Aligns with Domain: "Only one version can be marked is_current=true"
    photo_id = factory.make_photo_id()

    ver1 = service.create_version(user_id, make_version_request(
        photo_id=photo_id, version_type=PhotoVersionType.ORIGINAL
    ))
    assert ver1.is_current == True

    ver2 = service.create_version(user_id, make_version_request(
        photo_id=photo_id, version_type=PhotoVersionType.AI_ENHANCED
    ))
    assert ver2.is_current == True

    # Verify ver1 automatically unmarked
    ver1_updated = service.get_version(user_id, ver1.version_id)
    assert ver1_updated.is_current == False
```

---

#### BR-M002: Version Lifecycle

**Rule**: The original version must always be preserved. Deleting the current version reverts to the original.

**Given**: Photo has original and AI-enhanced versions, AI-enhanced is current
**When**: User deletes AI-enhanced version
**Then**:
- AI-enhanced version deleted from database
- Original version marked as current (`is_current=true`)
- Event published: `media.version.deleted`

**Test Markers**: `@pytest.mark.component`, `@pytest.mark.logic_rule("BR-M002")`

---

### Playlist Rules

#### BR-M003: Playlist Type Behavior

**Rule**: Playlist behavior varies by type (manual, smart, AI-curated).

**Manual Playlists**:
- User explicitly adds/removes photos
- `photo_ids` is read-write
- Max 1000 photos (see BR-M004)

**Smart Playlists**:
- Auto-populated based on `smart_criteria`
- `photo_ids` is read-only (managed by service)
- No hard limit (query-based)
- Auto-updates when new photos match criteria

**AI-Curated Playlists**:
- ML algorithm selects photos
- Criteria opaque to user
- Max 500 photos (performance)

**Test Markers**: `@pytest.mark.component`, `@pytest.mark.logic_rule("BR-M003")`

---

#### BR-M004: Playlist Limits

**Rule**: Manual playlists have a maximum of 1000 photos.

**Given**: Manual playlist with 1000 photos
**When**: User attempts to add another photo
**Then**:
- Request rejected with 400 Bad Request
- Error message: "Playlist exceeds maximum of 1000 photos"

**Test Markers**: `@pytest.mark.component`, `@pytest.mark.logic_rule("BR-M004")`

**Example Test**:
```python
def test_br_m004_manual_playlist_max_1000_photos():
    # Create manual playlist
    request = factory.make_playlist_create_request(
        playlist_type=PlaylistType.MANUAL,
        photo_ids=[f"photo_{i}" for i in range(1000)]
    )
    playlist = service.create_playlist(user_id, request)
    assert len(playlist.photo_ids) == 1000

    # Attempt to add 1001st photo
    update_request = PlaylistUpdateRequest(
        photo_ids=playlist.photo_ids + ["photo_1001"]
    )
    with pytest.raises(ValidationError, match="exceeds maximum"):
        service.update_playlist(user_id, playlist.playlist_id, update_request)
```

---

#### BR-M005: Smart Playlist Criteria Validation

**Rule**: Smart playlist criteria must be valid and supported.

**Supported Criteria**:
- `ai_labels_contains`: Array of required labels
- `ai_scenes_contains`: Array of required scenes
- `quality_score_min`: Minimum quality (0.0-1.0)
- `location_contains`: Location name substring
- `date_range`: {start_date, end_date}

**Given**: User creates smart playlist with unsupported criteria
**When**: Criteria includes `face_count_min` (not supported)
**Then**:
- Request rejected with 400 Bad Request
- Error message lists supported criteria fields

**Test Markers**: `@pytest.mark.component`, `@pytest.mark.logic_rule("BR-M005")`

---

#### BR-M006: Smart Playlist Criteria Combination

**Rule**: All smart playlist criteria are combined with AND logic.

**Given**: Smart playlist with criteria:
```json
{
  "ai_scenes_contains": ["beach"],
  "quality_score_min": 0.7
}
```
**When**: Service queries metadata
**Then**:
- Photos must have `ai_scenes` containing "beach" AND
- Photos must have `quality_score >= 0.7`
- Both conditions required (not OR)

**Test Markers**: `@pytest.mark.integration`, `@pytest.mark.logic_rule("BR-M006")`

---

#### BR-M007: Smart Playlist Auto-Population

**Rule**: Smart playlists auto-populate when created and auto-update when new matching photos are added.

**Scenario 1: Initial Population**

**Given**: 5 existing photos with `ai_scenes` containing "beach"
**When**: User creates smart playlist with criteria `ai_scenes_contains: ["beach"]`
**Then**:
- Playlist created with `photo_ids` containing 5 photo IDs
- All photos match criteria

**Scenario 2: Auto-Update on New Photo**

**Given**: Smart playlist with `ai_scenes_contains: ["beach"]` exists
**When**: New photo uploaded with `ai_scenes: ["beach", "sunset"]`
**Then**:
- New photo automatically added to playlist
- Event published: `media.playlist.updated`

**Test Markers**: `@pytest.mark.integration`, `@pytest.mark.logic_rule("BR-M007")`

**Example Test**:
```python
@pytest.mark.integration
async def test_br_m007_smart_playlist_auto_update():
    # Create smart playlist for beach photos
    playlist_request = factory.make_smart_playlist_request(
        smart_criteria={
            "ai_scenes_contains": ["beach"],
            "quality_score_min": 0.7
        }
    )
    playlist = await service.create_playlist(user_id, playlist_request)
    initial_count = len(playlist.photo_ids)

    # Simulate new photo with matching metadata
    new_photo_id = factory.make_photo_id()
    metadata = PhotoMetadata(
        file_id=factory.make_file_id(),
        user_id=user_id,
        ai_scenes=["beach", "sunset"],
        quality_score=0.85
    )
    await metadata_service.create_metadata(user_id, metadata)

    # Trigger auto-update (via event or direct call)
    await service.check_photo_matches_playlists(user_id, new_photo_id)

    # Verify photo added to playlist
    updated_playlist = await service.get_playlist(user_id, playlist.playlist_id)
    assert len(updated_playlist.photo_ids) == initial_count + 1
    assert new_photo_id in updated_playlist.photo_ids
```

---

### Cache Rules

#### BR-M008: Cache Priority

**Rule**: Active rotation schedules have highest cache priority.

**Given**: Frame has active rotation schedule with playlist
**When**: Cache manager runs
**Then**:
- All photos in active playlist cached first
- Recently viewed playlists cached second
- LRU eviction applied when storage full

**Test Markers**: `@pytest.mark.integration`, `@pytest.mark.logic_rule("BR-M008")`

---

#### BR-M009: Cache Expiration

**Rule**: Cached photos expire after 30 days and must be re-downloaded if still in use.

**Given**: Photo cached 31 days ago
**When**: Frame requests photo
**Then**:
- Cache status checked, found `EXPIRED`
- New cache entry created with status `PENDING`
- Background download triggered
- Old cache entry deleted

**Test Markers**: `@pytest.mark.integration`, `@pytest.mark.logic_rule("BR-M009")`

**Example Test**:
```python
@pytest.mark.integration
async def test_br_m009_cache_expiration():
    # Create cache entry 31 days ago (mock timestamp)
    cache = await service.create_cache_entry(
        user_id, frame_id="frame_001", photo_id="photo_123"
    )

    # Mock created_at to 31 days ago
    await repository.update_cache_timestamp(
        cache.cache_id,
        created_at=datetime.now(timezone.utc) - timedelta(days=31)
    )

    # Request photo (should detect expiration)
    result = await service.get_cached_photo(user_id, "frame_001", "photo_123")

    # Verify new cache entry created
    assert result.cache_status == CacheStatus.PENDING
    assert result.cache_id != cache.cache_id  # New entry
```

---

#### BR-M010: Failed Cache Retry with Exponential Backoff

**Rule**: Failed cache downloads retry up to 3 times with exponential backoff.

**Given**: Photo cache download fails
**When**: Retry logic executes
**Then**:
- Retry 1: Wait 1 second, retry
- Retry 2: Wait 2 seconds, retry
- Retry 3: Wait 4 seconds, retry
- After 3 failures: Mark as `FAILED`, store error_message

**Test Markers**: `@pytest.mark.integration`, `@pytest.mark.logic_rule("BR-M010")`

---

## State Machines

### Photo Cache State Machine

```
┌──────────┐
│ PENDING  │ ◀─── Initial state when cache entry created
└────┬─────┘
     │
     │ (download starts)
     ▼
┌──────────────┐
│ DOWNLOADING  │ ◀─── Background job downloading photo
└────┬────┬────┘
     │    │
     │    │ (download fails, retry < 3)
     │    └─────────────────────┐
     │                          │
     │ (download succeeds)      │ (retry count incremented)
     ▼                          ▼
┌────────┐                 ┌──────────┐
│ CACHED │                 │ PENDING  │
└───┬────┘                 └──────────┘
    │
    │ (30 days pass)
    ▼
┌──────────┐
│ EXPIRED  │ ◀─── Auto-expires after 30 days
└──────────┘

┌────────┐
│ FAILED │ ◀─── Download failed 3 times
└────────┘
```

**Transitions**:
- `PENDING → DOWNLOADING`: Background job starts download
- `DOWNLOADING → CACHED`: Download succeeds, cached_url stored
- `DOWNLOADING → PENDING`: Download fails, retry < 3, retry_count++
- `DOWNLOADING → FAILED`: Download fails, retry >= 3, error_message stored
- `CACHED → EXPIRED`: 30 days since created_at

---

### Rotation Schedule State Machine

```
┌─────────┐
│ CREATED │ ◀─── Initial state (is_active=true by default)
└────┬────┘
     │
     │ (user activates)
     ▼
┌────────┐
│ ACTIVE │ ◀─── Schedule actively rotating photos
└───┬────┘
    │
    │ (user deactivates)
    ▼
┌──────────┐
│ INACTIVE │ ◀─── Schedule paused (is_active=false)
└────┬─────┘
     │
     │ (user activates again)
     └──────────────────▶ ACTIVE
```

---

## Edge Cases

### EC-M001: Empty Smart Playlist

**Scenario**: Smart playlist created but no photos match criteria
**Expected**: Playlist created successfully with `photo_ids=[]`
**Rationale**: Allows future auto-population as matching photos are added

---

### EC-M002: Manual Playlist Photo Duplicates

**Scenario**: User adds same photo_id multiple times to manual playlist
**Expected**: Duplicates allowed (enables extended display time)
**Example**: `photo_ids = ["photo_1", "photo_1", "photo_2"]` is valid

---

### EC-M003: Smart Playlist Criteria Change

**Scenario**: User updates smart_criteria for existing smart playlist
**Expected**:
- Service re-executes metadata query with new criteria
- `photo_ids` completely replaced with new results
- Old photos removed, new matches added

---

### EC-M004: Rotation Schedule Without Playlist

**Scenario**: Playlist deleted while rotation schedule still references it
**Expected**:
- Schedule remains in database (playlist_id references deleted playlist)
- Frame queries schedule, gets 404 when fetching playlist
- User must update or delete schedule

---

### EC-M005: Frame Cache Storage Full

**Scenario**: Frame requests cache, but local storage is full
**Expected**:
- Service evicts least-recently-used (LRU) photos
- Based on `last_accessed_at` timestamp
- Evict until space available for new photo

---

## Test Coverage Requirements

### Per Business Rule

Each business rule (BR-M001 to BR-M010) must have:
- ✅ At least 1 component test (mocked dependencies)
- ✅ At least 1 integration test (real HTTP + DB)
- ✅ Documented in golden tests (captures actual behavior)

### Per State Machine

Each state transition must have:
- ✅ Component test validating state change
- ✅ Integration test with real persistence

### Per Edge Case

Each edge case (EC-M001 to EC-M005) must have:
- ✅ Test validating expected behavior
- ✅ Test validating error handling (if applicable)

---

## Related Documents

- **Domain**: [docs/domain/media_service.md](../../../docs/domain/media_service.md)
- **PRD**: [docs/prd/media_service.md](../../../docs/prd/media_service.md)
- **Design**: [docs/design/media_service.md](../../../docs/design/media_service.md)
- **Data Contract**: [data_contract.py](./data_contract.py)
- **System Contract**: [tests/TDD_CONTRACT.md](../../../tests/TDD_CONTRACT.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: Media Service Team
