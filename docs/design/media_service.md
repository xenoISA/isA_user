# Media Service - Technical Design

**Layer 3: Architecture & Technical Specifications**

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                      MEDIA SERVICE                             │
│                         (Port 8222)                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Version    │  │  Metadata    │  │   Playlist   │        │
│  │  Management  │  │  Management  │  │  Management  │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                  │                  │                │
│         └──────────────────┴──────────────────┘                │
│                            │                                   │
│              ┌─────────────▼──────────────┐                    │
│              │   Media Repository         │                    │
│              │  (PostgreSQL Interface)    │                    │
│              └─────────────┬──────────────┘                    │
│                            │                                   │
│              ┌─────────────▼──────────────┐                    │
│              │   Event Publisher          │                    │
│              │   (NATS Integration)       │                    │
│              └────────────────────────────┘                    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌──────────────┐  ┌─────────────┐  ┌────────────┐
    │   Storage    │  │  AI Service │  │   Device   │
    │   Service    │  │  (Vision)   │  │  Service   │
    │  (MinIO)     │  │             │  │ (Frames)   │
    └──────────────┘  └─────────────┘  └────────────┘
```

---

## Component Architecture

### 1. Photo Version Management

**Responsibilities**:
- Create and manage photo versions (original, AI-enhanced, styled)
- Track version lifecycle and relationships
- Coordinate with AI service for enhancements

**Key Classes**:
```python
class PhotoVersionService:
    async def create_version(user_id, photo_id, request) -> PhotoVersion
    async def list_versions(user_id, photo_id) -> List[PhotoVersion]
    async def set_current_version(user_id, version_id) -> PhotoVersion
    async def delete_version(user_id, version_id) -> bool
```

**Database Schema**:
```sql
CREATE TABLE photo_versions (
    version_id VARCHAR(50) PRIMARY KEY,
    photo_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    version_name VARCHAR(255) NOT NULL,
    version_type VARCHAR(50) NOT NULL,  -- Enum: ORIGINAL, AI_ENHANCED, etc.
    processing_mode VARCHAR(100),
    file_id VARCHAR(50) NOT NULL,
    cloud_url TEXT,
    local_path VARCHAR(500),
    file_size BIGINT,
    processing_params JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    is_current BOOLEAN DEFAULT false,
    version_number INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_photo_versions_photo_id ON photo_versions(photo_id);
CREATE INDEX idx_photo_versions_user_id ON photo_versions(user_id);
CREATE INDEX idx_photo_versions_is_current ON photo_versions(is_current) WHERE is_current = true;
```

---

### 2. Photo Metadata Management

**Responsibilities**:
- Extract EXIF data from photos
- Coordinate AI analysis (labels, faces, quality)
- Store and query rich metadata

**Key Classes**:
```python
class PhotoMetadataService:
    async def create_metadata(user_id, file_id) -> PhotoMetadata
    async def get_metadata(user_id, file_id) -> PhotoMetadata
    async def update_ai_analysis(file_id, ai_results) -> PhotoMetadata
    async def query_by_criteria(user_id, criteria) -> List[str]  # Returns photo_ids
```

**Database Schema**:
```sql
CREATE TABLE photo_metadata (
    file_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- EXIF Data
    camera_make VARCHAR(100),
    camera_model VARCHAR(100),
    lens_model VARCHAR(100),
    focal_length VARCHAR(50),
    aperture VARCHAR(50),
    shutter_speed VARCHAR(50),
    iso INT,
    flash_used BOOLEAN,

    -- Location
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_name VARCHAR(255),
    photo_taken_at TIMESTAMP,

    -- AI Analysis
    ai_labels JSONB DEFAULT '[]',
    ai_objects JSONB DEFAULT '[]',
    ai_scenes JSONB DEFAULT '[]',
    ai_colors JSONB DEFAULT '[]',
    face_detection JSONB,
    text_detection JSONB,

    -- Quality Metrics
    quality_score DECIMAL(3, 2),  -- 0.00 to 1.00
    blur_score DECIMAL(3, 2),
    brightness DECIMAL(3, 2),
    contrast DECIMAL(3, 2),

    full_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_photo_metadata_user_id ON photo_metadata(user_id);
CREATE INDEX idx_photo_metadata_quality_score ON photo_metadata(quality_score);
CREATE INDEX idx_photo_metadata_ai_labels ON photo_metadata USING GIN(ai_labels);
CREATE INDEX idx_photo_metadata_ai_scenes ON photo_metadata USING GIN(ai_scenes);
```

---

### 3. Playlist Management

**Responsibilities**:
- Create and manage playlists (manual, smart, AI-curated)
- Execute smart playlist criteria queries
- Auto-update smart playlists on new photos

**Key Classes**:
```python
class PlaylistService:
    async def create_playlist(user_id, request) -> Playlist
    async def get_playlist(user_id, playlist_id) -> Playlist
    async def update_playlist(user_id, playlist_id, request) -> Playlist
    async def auto_populate_smart_playlist(playlist_id) -> Playlist
    async def check_photo_matches_playlists(user_id, photo_id) -> List[str]
```

**Database Schema**:
```sql
CREATE TABLE playlists (
    playlist_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    playlist_type VARCHAR(50) NOT NULL,  -- MANUAL, SMART, AI_CURATED
    smart_criteria JSONB,
    photo_ids JSONB DEFAULT '[]',
    shuffle BOOLEAN DEFAULT false,
    loop BOOLEAN DEFAULT true,
    transition_duration INT DEFAULT 5,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_playlists_user_id ON playlists(user_id);
CREATE INDEX idx_playlists_type ON playlists(playlist_type);
```

---

### 4. Rotation Schedule Management

**Responsibilities**:
- Manage photo rotation schedules for smart frames
- Determine active photos based on time/events
- Support continuous, time-based, event-based schedules

**Key Classes**:
```python
class RotationScheduleService:
    async def create_schedule(user_id, request) -> RotationSchedule
    async def get_frame_schedule(user_id, frame_id) -> RotationSchedule
    async def get_current_photos_for_frame(frame_id) -> List[str]
    async def is_schedule_active_now(schedule) -> bool
```

**Database Schema**:
```sql
CREATE TABLE rotation_schedules (
    schedule_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    frame_id VARCHAR(50) NOT NULL,
    playlist_id VARCHAR(50),
    schedule_type VARCHAR(50) NOT NULL,  -- CONTINUOUS, TIME_BASED, EVENT_BASED
    start_time VARCHAR(5),  -- HH:MM
    end_time VARCHAR(5),    -- HH:MM
    days_of_week JSONB DEFAULT '[]',  -- [0,1,2,3,4,5,6]
    rotation_interval INT DEFAULT 10,
    shuffle BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rotation_schedules_frame_id ON rotation_schedules(frame_id);
CREATE INDEX idx_rotation_schedules_user_id ON rotation_schedules(user_id);
CREATE INDEX idx_rotation_schedules_active ON rotation_schedules(is_active) WHERE is_active = true;
```

---

### 5. Photo Cache Management

**Responsibilities**:
- Manage photo caching for smart frames
- Track cache status and hits
- Implement LRU eviction policy

**Key Classes**:
```python
class PhotoCacheService:
    async def create_cache_entry(user_id, frame_id, photo_id) -> PhotoCache
    async def get_cached_photos(user_id, frame_id) -> List[PhotoCache]
    async def update_cache_status(cache_id, status, url) -> PhotoCache
    async def record_cache_hit(cache_id) -> None
    async def evict_lru_caches(frame_id, keep_count) -> List[str]
```

**Database Schema**:
```sql
CREATE TABLE photo_cache (
    cache_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    frame_id VARCHAR(50) NOT NULL,
    photo_id VARCHAR(50) NOT NULL,
    version_id VARCHAR(50),
    cache_status VARCHAR(50) NOT NULL,  -- PENDING, DOWNLOADING, CACHED, FAILED, EXPIRED
    cached_url TEXT,
    local_path VARCHAR(500),
    cache_size BIGINT,
    cache_format VARCHAR(50),
    cache_quality VARCHAR(50),
    hit_count INT DEFAULT 0,
    last_accessed_at TIMESTAMP,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '30 days')
);

CREATE INDEX idx_photo_cache_frame_id ON photo_cache(frame_id);
CREATE INDEX idx_photo_cache_status ON photo_cache(cache_status);
CREATE INDEX idx_photo_cache_expires_at ON photo_cache(expires_at);
CREATE INDEX idx_photo_cache_last_accessed ON photo_cache(last_accessed_at);
```

---

## Event-Driven Architecture

### Published Events

```python
# media.version.created
{
    "event_type": "media.version.created",
    "photo_id": "photo_abc123",
    "version_id": "ver_xyz789",
    "version_type": "AI_ENHANCED",
    "user_id": "user_001",
    "file_id": "file_new456",
    "timestamp": "2025-12-11T12:00:00Z"
}

# media.metadata.updated
{
    "event_type": "media.metadata.updated",
    "file_id": "file_abc123",
    "user_id": "user_001",
    "ai_labels": ["person", "outdoor", "smile"],
    "quality_score": 0.85,
    "timestamp": "2025-12-11T12:00:00Z"
}

# media.playlist.updated
{
    "event_type": "media.playlist.updated",
    "playlist_id": "pl_abc123",
    "user_id": "user_001",
    "photo_count": 42,
    "playlist_type": "SMART",
    "timestamp": "2025-12-11T12:00:00Z"
}

# media.cache.ready
{
    "event_type": "media.cache.ready",
    "cache_id": "cache_abc123",
    "frame_id": "frame_001",
    "photo_id": "photo_xyz",
    "cached_url": "https://cdn.example.com/cached/photo_xyz.jpg",
    "timestamp": "2025-12-11T12:00:00Z"
}
```

### Consumed Events

```python
# file.uploaded (from storage_service)
async def handle_file_uploaded(event):
    """
    Triggered when user uploads new photo to storage.
    Creates metadata record and triggers AI analysis.
    """
    file_id = event["file_id"]
    user_id = event["user_id"]

    # Create metadata record
    metadata = await metadata_service.create_metadata(user_id, file_id)

    # Trigger AI analysis (async)
    await ai_service.analyze_photo(file_id, user_id)

# file.deleted (from storage_service)
async def handle_file_deleted(event):
    """
    Triggered when file deleted from storage.
    Cascades delete to all versions and metadata.
    """
    file_id = event["file_id"]
    user_id = event["user_id"]

    # Delete all versions
    versions = await version_service.list_versions_by_file(user_id, file_id)
    for version in versions:
        await version_service.delete_version(user_id, version.version_id)

    # Delete metadata
    await metadata_service.delete_metadata(user_id, file_id)
```

---

## API Design

### REST Endpoints

**Photo Versions**:
```
POST   /api/v1/media/photos/{photo_id}/versions
GET    /api/v1/media/photos/{photo_id}/versions
GET    /api/v1/media/photos/{photo_id}/versions/{version_id}
PUT    /api/v1/media/photos/{photo_id}/versions/{version_id}/current
DELETE /api/v1/media/photos/{photo_id}/versions/{version_id}
```

**Metadata**:
```
GET    /api/v1/media/metadata/{file_id}
PUT    /api/v1/media/metadata/{file_id}
POST   /api/v1/media/metadata/query  # Search by criteria
```

**Playlists**:
```
POST   /api/v1/media/playlists
GET    /api/v1/media/playlists
GET    /api/v1/media/playlists/{playlist_id}
PUT    /api/v1/media/playlists/{playlist_id}
DELETE /api/v1/media/playlists/{playlist_id}
POST   /api/v1/media/playlists/{playlist_id}/photos  # Add photos
DELETE /api/v1/media/playlists/{playlist_id}/photos/{photo_id}
```

**Rotation Schedules**:
```
POST   /api/v1/media/schedules
GET    /api/v1/media/schedules/frame/{frame_id}
PUT    /api/v1/media/schedules/{schedule_id}
DELETE /api/v1/media/schedules/{schedule_id}
GET    /api/v1/media/schedules/{schedule_id}/photos  # Current active photos
```

**Photo Cache**:
```
POST   /api/v1/media/cache
GET    /api/v1/media/cache/frame/{frame_id}
GET    /api/v1/media/cache/{cache_id}
DELETE /api/v1/media/cache/{cache_id}
PUT    /api/v1/media/cache/{cache_id}/hit  # Record access
```

---

## Data Flow Diagrams

### Flow 1: Photo Upload → AI Analysis

```
User                Storage Service      Media Service         AI Service
 │                        │                    │                    │
 │──Upload Photo──────────▶│                    │                    │
 │                        │                    │                    │
 │                        │──file.uploaded────▶│                    │
 │                        │   event            │                    │
 │                        │                    │──Analyze Photo────▶│
 │                        │                    │   (async)          │
 │                        │                    │                    │
 │                        │                    │◀─AI Results────────│
 │                        │                    │  (labels, quality) │
 │                        │                    │                    │
 │                        │                    │──Store Metadata────▶DB
 │                        │                    │                    │
 │                        │◀──metadata.updated─│                    │
 │                        │   event            │                    │
```

### Flow 2: Smart Playlist Auto-Update

```
Media Service              Metadata DB          Playlist DB
     │                          │                    │
     │──New Photo Metadata─────▶│                    │
     │   (ai_scenes: beach)     │                    │
     │                          │                    │
     │──Query Smart Playlists───────────────────────▶│
     │   WHERE criteria          │                    │
     │   CONTAINS "beach"        │                    │
     │                          │                    │
     │◀─Matching Playlists──────────────────────────│
     │  [pl_vacation, pl_beach]  │                    │
     │                          │                    │
     │──Update photo_ids────────────────────────────▶│
     │  ADD photo_123 TO         │                    │
     │  [pl_vacation, pl_beach]  │                    │
     │                          │                    │
     │──Publish Event────────────▶NATS
     │  media.playlist.updated
```

### Flow 3: Frame Photo Rotation

```
Smart Frame           Media Service         Playlist DB       Cache DB       Storage Service
     │                      │                    │               │                  │
     │──Get Schedule────────▶│                    │               │                  │
     │  for frame_001       │                    │               │                  │
     │                      │──Get Playlist──────▶│               │                  │
     │                      │                    │               │                  │
     │◀─Schedule────────────│                    │               │                  │
     │  playlist_id         │                    │               │                  │
     │  rotation_interval   │                    │               │                  │
     │                      │                    │               │                  │
     │──Get Photos──────────▶│                    │               │                  │
     │                      │──Check Cache───────────────────────▶│                  │
     │                      │                    │               │                  │
     │                      │◀─Cache Hit─────────────────────────│                  │
     │                      │  (cached_url)      │               │                  │
     │                      │                    │               │                  │
     │◀─Photo URLs──────────│                    │               │                  │
     │  [url1, url2, ...]   │                    │               │                  │
     │                      │                    │               │                  │
     │──Download────────────────────────────────────────────────────────────────────▶│
     │  from cached_url     │                    │               │                  │
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|----------|-----------|
| **Web Framework** | FastAPI | Async support, Pydantic validation, OpenAPI |
| **Database** | PostgreSQL 15 | JSONB for flexible metadata, GIN indexes |
| **Event Bus** | NATS JetStream | Reliable async event delivery |
| **Storage** | MinIO (via Storage Service) | S3-compatible object storage |
| **AI Integration** | HTTP REST to AI Service | Vision API for analysis, enhancement |
| **Caching** | PostgreSQL (cache table) | Centralized, queryable cache state |
| **ORM** | SQLAlchemy 2.0 | Async support, type safety |
| **Task Queue** | NATS (work queue) | Background jobs (AI analysis, cache downloads) |

---

## Performance Optimization

### Query Optimization

```sql
-- Smart playlist query with GIN indexes
SELECT file_id FROM photo_metadata
WHERE user_id = $1
  AND ai_scenes @> '["beach"]'::jsonb  -- GIN index used
  AND quality_score >= 0.7              -- B-tree index used
  AND photo_taken_at BETWEEN $2 AND $3  -- B-tree index used
ORDER BY quality_score DESC
LIMIT 100;

-- Execution plan shows index usage
Limit (cost=0.42..12.85 rows=100 width=22)
  -> Bitmap Heap Scan on photo_metadata (cost=0.42..124.56 rows=1000 width=22)
        Recheck Cond: (ai_scenes @> '["beach"]'::jsonb)
        Filter: (quality_score >= 0.7)
        -> Bitmap Index Scan on idx_photo_metadata_ai_scenes (cost=0.00..0.42 rows=10 width=0)
```

### Caching Strategy

- **Metadata Cache**: Cache AI analysis results for 1 hour (avoid re-computation)
- **Playlist Cache**: Cache smart playlist results for 5 minutes (reduce DB load)
- **Photo Cache**: Pre-cache photos for active rotation schedules

---

## Security

### Authorization

- All endpoints require `user_id` parameter
- X-Internal-Call header bypasses auth for internal services
- Users can only access their own resources (or organization resources if member)

### Data Privacy

- Photo metadata includes location data (PII)
- Face detection results include biometric data
- Comply with GDPR/CCPA for data deletion

---

## Monitoring & Observability

### Key Metrics

```python
# Prometheus metrics
media_photo_versions_total = Counter("media_photo_versions_total", ["version_type"])
media_ai_analysis_duration_seconds = Histogram("media_ai_analysis_duration_seconds")
media_playlist_query_duration_seconds = Histogram("media_playlist_query_duration_seconds")
media_cache_hit_rate = Gauge("media_cache_hit_rate", ["frame_id"])
media_smart_playlist_update_total = Counter("media_smart_playlist_update_total")
```

### Logging

```python
# Structured logging
logger.info(
    "photo_version_created",
    version_id=version.version_id,
    version_type=version.version_type,
    user_id=user_id,
    processing_duration_ms=duration
)
```

---

## Related Documents

- **Domain**: [docs/domain/media_service.md](../domain/media_service.md)
- **PRD**: [docs/prd/media_service.md](../prd/media_service.md)
- **Data Contract**: [tests/contracts/media/data_contract.py](../../tests/contracts/media/data_contract.py)
- **Logic Contract**: [tests/contracts/media/logic_contract.md](../../tests/contracts/media/logic_contract.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: Engineering Team
