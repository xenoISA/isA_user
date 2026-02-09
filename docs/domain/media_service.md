# Media Service - Domain Context

**Layer 1: Business Context & Taxonomy**

## Executive Summary

The Media Service handles photo processing, versioning, organization, and delivery for smart digital photo frames. It enables users to:
- Store and process multiple photo versions (original, AI-enhanced, styled)
- Organize photos into playlists with smart curation
- Schedule photo rotations on smart frame devices
- Cache photos for offline display
- Analyze and enrich photo metadata with AI

---

## Business Domain: Digital Photo Management

### Problem Space

**User Pain Points:**
1. **Photo Overload**: Users have thousands of photos but struggle to organize and display them
2. **Quality Inconsistency**: Not all photos are display-ready (poor lighting, composition, backgrounds)
3. **Manual Curation**: Creating photo rotations for frames is time-consuming
4. **Device Limitations**: Smart frames have limited storage and bandwidth
5. **Lack of Context**: Photos lack searchable metadata and organization

**Business Goals:**
1. **Automated Curation**: AI selects best photos based on quality, content, and user preferences
2. **Intelligent Enhancement**: Automatically improve photo quality for display
3. **Effortless Organization**: Smart playlists based on location, time, people, events
4. **Efficient Delivery**: Optimized caching and bandwidth usage for frames
5. **Rich Discovery**: AI-powered metadata enables search and recommendations

---

## Domain Taxonomy

### Core Entities

```
Media Domain
├── Photo Versions
│   ├── Original (source photo from storage service)
│   ├── AI-Enhanced (quality improvements)
│   ├── AI-Styled (artistic filters)
│   ├── AI-Background Removed (subject isolation)
│   └── User-Edited (manual adjustments)
│
├── Photo Metadata
│   ├── EXIF Data (camera, lens, settings)
│   ├── Location (GPS, place names)
│   ├── AI Analysis (labels, objects, scenes, colors)
│   ├── Face Detection (people identification)
│   ├── Text Detection (OCR results)
│   └── Quality Metrics (blur, brightness, contrast)
│
├── Playlists
│   ├── Manual (user-curated)
│   ├── Smart (rule-based selection)
│   └── AI-Curated (ML-powered curation)
│
├── Rotation Schedules
│   ├── Continuous (always on)
│   ├── Time-Based (specific hours/days)
│   └── Event-Based (triggered by events)
│
└── Photo Cache
    ├── Pending (queued for download)
    ├── Downloading (in progress)
    ├── Cached (ready for display)
    ├── Failed (error occurred)
    └── Expired (needs refresh)
```

---

## Business Scenarios

### Scenario 1: New Photo Upload Flow

**Actors**: User, Storage Service, Media Service, AI Service

**Flow**:
1. User uploads photo via Storage Service
2. Storage Service publishes `file.uploaded` event
3. Media Service receives event and creates PhotoMetadata record
4. Media Service requests AI analysis (labels, faces, quality)
5. AI results stored in metadata
6. If quality score high → Photo eligible for auto-playlists
7. If quality score low → Photo candidate for AI enhancement

**Business Value**: Automatic photo enrichment and organization without user effort

---

### Scenario 2: Smart Playlist Creation

**Actors**: User, Media Service

**Flow**:
1. User creates smart playlist: "Best vacation photos from 2024"
2. Media Service defines criteria:
   - `ai_scenes` contains ["beach", "mountain", "landmark"]
   - `quality_score` > 0.7
   - `photo_taken_at` between 2024-01-01 and 2024-12-31
3. Service queries metadata and auto-populates playlist
4. As new photos match criteria, playlist auto-updates

**Business Value**: Zero-effort photo organization that stays current

---

### Scenario 3: Smart Frame Photo Rotation

**Actors**: Smart Frame Device, Media Service

**Flow**:
1. Device connects and requests rotation schedule
2. Media Service returns schedule with playlist
3. Device requests photos from playlist
4. Media Service checks cache:
   - If cached → Return cached URL
   - If not cached → Create cache entry, trigger download
5. Device downloads and displays photos per schedule
6. Media Service tracks cache hits and expires old entries

**Business Value**: Efficient bandwidth usage, offline-ready photos

---

### Scenario 4: AI Photo Enhancement

**Actors**: User, Media Service, AI Service

**Flow**:
1. User selects photo and requests "AI enhance"
2. Media Service creates new PhotoVersion (type=AI_ENHANCED)
3. Service sends original to AI enhancement service
4. AI returns enhanced image
5. Media Service stores enhanced version in Storage Service
6. New version linked to original photo
7. User can compare/switch between versions

**Business Value**: Professional-quality photos from smartphone shots

---

## Key Business Rules

### Photo Version Rules

**BR-M001: Version Uniqueness**
- Each photo can have multiple versions
- Version types can exist multiple times (e.g., multiple AI-styled variants)
- Only one version can be marked `is_current=true`

**BR-M002: Version Lifecycle**
- Original version always preserved
- Deleting current version reverts to original
- All versions track processing parameters for reproducibility

### Playlist Rules

**BR-M003: Playlist Types**
- **Manual**: User explicitly adds/removes photos
- **Smart**: Auto-populated based on criteria, user can view-only
- **AI-Curated**: ML selects photos, criteria opaque to user

**BR-M004: Playlist Limits**
- Manual playlists: max 1000 photos
- Smart playlists: no hard limit (query-based)
- AI-Curated: max 500 photos (performance)

### Caching Rules

**BR-M005: Cache Priority**
- Active rotation schedules have highest priority
- Recently viewed playlists cached proactively
- Least-recently-used (LRU) eviction when storage full

**BR-M006: Cache Expiration**
- Cached photos expire after 30 days
- Expired photos re-downloaded if still in active rotation
- Failed downloads retry with exponential backoff (max 3 retries)

---

## Domain Events

### Published Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `media.version.created` | New photo version created | `photo_id`, `version_id`, `version_type` |
| `media.metadata.updated` | AI analysis complete | `file_id`, `ai_labels`, `quality_score` |
| `media.playlist.updated` | Playlist modified | `playlist_id`, `photo_count` |
| `media.cache.ready` | Photo cached successfully | `cache_id`, `frame_id`, `photo_id` |

### Consumed Events

| Event | Source | Action |
|-------|--------|--------|
| `file.uploaded` | Storage Service | Create metadata, trigger AI analysis |
| `file.deleted` | Storage Service | Delete all photo versions and metadata |
| `device.registered` | Device Service | Initialize cache for new frame |

---

## Success Metrics

### User Experience Metrics
- **Photo Discovery**: % of photos with AI metadata < 5 minutes after upload
- **Auto-Curation Accuracy**: % of AI-curated playlists rated 4+ stars
- **Display Quality**: % of photos with quality_score > 0.7

### Technical Metrics
- **Cache Hit Rate**: % of frame requests served from cache (target: >90%)
- **AI Processing Time**: p95 latency for metadata analysis (target: <10s)
- **Version Creation Time**: p95 latency for AI enhancement (target: <30s)

### Business Metrics
- **Engagement**: Average photos displayed per frame per day
- **Feature Adoption**: % of users with at least 1 smart playlist
- **Quality Improvement**: % of photos using AI-enhanced versions

---

## Domain Glossary

| Term | Definition |
|------|------------|
| **Photo Version** | A specific rendering of a photo (original, enhanced, styled) |
| **EXIF Data** | Embedded camera metadata (make, model, settings, GPS) |
| **AI Labels** | Machine-generated tags describing photo content |
| **Quality Score** | 0.0-1.0 ML-generated score indicating display suitability |
| **Smart Playlist** | Auto-populated collection based on metadata criteria |
| **Rotation Schedule** | Timed rules for displaying photos on a frame |
| **Cache Entry** | Photo pre-downloaded to frame storage |
| **Hit Count** | Number of times a cached photo was displayed |

---

## Related Documents

- **PRD**: [docs/prd/media_service.md](../prd/media_service.md)
- **Design**: [docs/design/media_service.md](../design/media_service.md)
- **Data Contract**: [tests/contracts/media/data_contract.py](../../tests/contracts/media/data_contract.py)
- **Logic Contract**: [tests/contracts/media/logic_contract.md](../../tests/contracts/media/logic_contract.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: Media Service Team
