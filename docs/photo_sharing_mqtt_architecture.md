# 📸 Photo Sharing to Smart Frame Architecture

## Overview
Architecture for sharing photos from mobile app → album_service → MQTT → hardware smart frame → media_service

## 🎯 Use Case Flow

```
Mobile App (Upload Photo)
    ↓ HTTP POST
storage_service (Store photo + AI metadata)
    ↓ NATS Event: file.uploaded.with_ai
album_service (Add photo to family album)
    ↓ MQTT Publish
Smart Frame Hardware (Subscribe to album updates)
    ↓ HTTP GET
media_service (Fetch photo metadata + URL)
    ↓ HTTP GET
storage_service (Download photo file)
    ↓
Smart Frame Display
```

---

## 1️⃣ Current Architecture Analysis

### **storage_service** (Port: 8220)
**Role:** File storage and AI metadata extraction

**Publishes Events:**
- `file.uploaded` - Basic file upload
- `file.uploaded.with_ai` - File with AI metadata (faces, labels, objects)
- `file.deleted` - File deletion

**Event Data:**
```python
{
    "file_id": "uuid",
    "user_id": "owner_user_id",
    "file_name": "IMG_1234.jpg",
    "file_size": 2048576,
    "content_type": "image/jpeg",
    "ai_metadata": {
        "labels": ["family", "outdoor", "birthday"],
        "faces": [{"x": 100, "y": 200, "width": 50, "height": 50}],
        "objects": ["cake", "balloons"]
    },
    "storage_path": "photos/2025/01/uuid.jpg"
}
```

---

### **album_service** (Port: 8219)
**Role:** Album management and smart frame sync

**Current Structure:**
```
album_service/
├── events/
│   ├── __init__.py
│   └── handlers.py          # ✅ Has event handlers
├── album_service.py
├── album_repository.py
└── main.py
```

**Subscribed Events:**
- `file.deleted` → Remove photo from all albums

**Missing:**
- ❌ No `events/publishers.py` - Should publish album.photo_added events
- ❌ No `events/models.py` - Should define event data models
- ❌ No `clients/` folder - Should have storage_client, media_client
- ❌ No MQTT integration - Should publish to hardware frames

**Database Tables:**
- `albums` - Album metadata
- `album_photos` - Photos in albums
- `album_sync_status` - Frame sync tracking

---

### **media_service** (Port: 8222)
**Role:** Photo versioning, caching, and serving to frames

**Current Structure:**
```
media_service/
├── events.py               # ✅ Has event handler (monolithic file)
├── media_service.py
├── media_repository.py
└── main.py
```

**Subscribed Events:**
- `file.uploaded.with_ai` → Create photo versions
- `file.deleted` → Remove cached versions
- `device.deleted` → Clean up device cache

**Missing:**
- ❌ No `events/` folder structure
- ❌ No `events/publishers.py`
- ❌ No `events/models.py`
- ❌ No `clients/` folder

**Database Tables:**
- `photo_versions` - Different sizes/formats
- `photo_metadata` - AI labels, faces
- `photo_cache` - Device-specific cache
- `playlists` - Photo collections
- `rotation_schedules` - Display schedules

---

## 2️⃣ MQTT Integration Design

### **MQTT Client Usage**

**Where:** `album_service` publishes MQTT messages when photos are added to albums

**MQTT Topics Hierarchy:**
```
albums/{album_id}/photo_added      # New photo added to album
albums/{album_id}/photo_removed    # Photo removed from album
albums/{album_id}/sync             # Full album sync
frames/{frame_id}/command          # Frame-specific commands
frames/{frame_id}/status           # Frame status updates (from hardware)
```

---

## 3️⃣ Complete Workflow Implementation

### **Step 1: Mobile App Uploads Photo**

```http
POST /api/v1/storage/photos/upload
Content-Type: multipart/form-data

{
    "file": <binary>,
    "user_id": "user_123",
    "metadata": {"album_id": "family_album_001"}
}
```

**storage_service** publishes NATS event:
```python
# EventType.FILE_UPLOADED_WITH_AI
{
    "file_id": "photo_xyz",
    "user_id": "user_123",
    "file_name": "family_photo.jpg",
    "ai_metadata": {
        "labels": ["family", "indoor"],
        "faces": [...]
    }
}
```

---

### **Step 2: album_service Receives Event & Adds to Album**

**File:** `album_service/events/handlers.py` (NEW HANDLER)

```python
async def handle_file_uploaded_with_ai(self, event_data: Dict[str, Any]) -> bool:
    """
    Handle file.uploaded.with_ai event
    Automatically add photo to user's default album or specified album
    """
    file_id = event_data.get('file_id')
    user_id = event_data.get('user_id')
    metadata = event_data.get('metadata', {})
    album_id = metadata.get('album_id')  # From upload request

    if album_id:
        # Add photo to specified album
        await self.album_repo.add_photo_to_album(album_id, file_id)

        # Publish MQTT notification to frames subscribed to this album
        await self.mqtt_publisher.publish_photo_added(album_id, file_id)

        # Publish NATS event for other services
        await self.event_publishers.publish_album_photo_added(album_id, file_id, user_id)
```

---

### **Step 3: album_service Publishes MQTT Message**

**File:** `album_service/mqtt_publisher.py` (NEW FILE)

```python
from isa_common.mqtt_client import MQTTClient
import json

class AlbumMQTTPublisher:
    """MQTT publisher for album service to notify smart frames"""

    def __init__(self):
        self.mqtt_client = MQTTClient(user_id='album_service')
        self.session_id = None

    async def connect(self):
        """Connect to MQTT broker"""
        with self.mqtt_client:
            conn = self.mqtt_client.connect('album-service-001')
            self.session_id = conn['session_id']

    async def publish_photo_added(self, album_id: str, file_id: str, photo_metadata: dict):
        """
        Publish photo_added event to MQTT for smart frames

        Topic: albums/{album_id}/photo_added
        QoS: 1 (at least once delivery)
        """
        if not self.session_id:
            await self.connect()

        with self.mqtt_client:
            message = {
                'event_type': 'photo_added',
                'album_id': album_id,
                'file_id': file_id,
                'photo_metadata': {
                    'file_name': photo_metadata.get('file_name'),
                    'content_type': photo_metadata.get('content_type'),
                    'ai_labels': photo_metadata.get('ai_metadata', {}).get('labels', []),
                    'timestamp': photo_metadata.get('created_at')
                },
                'media_service_url': f'http://media-service:8222/api/v1/photos/{file_id}',
                'timestamp': datetime.utcnow().isoformat()
            }

            # Publish to album-specific topic
            self.mqtt_client.publish_json(
                self.session_id,
                f'albums/{album_id}/photo_added',
                message,
                qos=1,  # At least once delivery
                retained=False
            )

            logger.info(f"Published MQTT photo_added event for album {album_id}")

    async def publish_album_sync(self, album_id: str, frame_id: str, photo_list: list):
        """
        Publish full album sync to specific frame

        Topic: frames/{frame_id}/sync
        QoS: 2 (exactly once delivery)
        Retained: True (frame gets sync on reconnect)
        """
        with self.mqtt_client:
            message = {
                'event_type': 'album_sync',
                'album_id': album_id,
                'frame_id': frame_id,
                'photos': photo_list,  # List of file_ids with metadata
                'total_photos': len(photo_list),
                'timestamp': datetime.utcnow().isoformat()
            }

            self.mqtt_client.publish_json(
                self.session_id,
                f'frames/{frame_id}/sync',
                message,
                qos=2,  # Exactly once
                retained=True  # Frame gets last sync on reconnect
            )
```

---

### **Step 4: Smart Frame Hardware Subscribes to MQTT**

**Hardware Code** (Go or Embedded C):

```go
// Using MQTT adapter from /Users/xenodennis/Documents/Fun/isA_Cloud/adapters/mqtt_adapter.go

func (f *SmartFrame) SubscribeToAlbum(albumID string) error {
    // Subscribe to album photo updates
    topic := fmt.Sprintf("albums/%s/photo_added", albumID)

    err := f.mqttClient.Subscribe(topic, 1, func(msg mqtt.Message) {
        // Parse MQTT message
        var photoEvent PhotoAddedEvent
        json.Unmarshal(msg.Payload(), &photoEvent)

        // Fetch photo from media_service
        photoURL := photoEvent.MediaServiceURL
        f.FetchAndDisplayPhoto(photoEvent.FileID, photoURL)
    })

    return err
}

func (f *SmartFrame) FetchAndDisplayPhoto(fileID string, mediaServiceURL string) error {
    // Step 1: Get photo metadata from media_service
    resp, err := http.Get(mediaServiceURL)
    if err != nil {
        return err
    }

    var photoMeta PhotoMetadata
    json.NewDecoder(resp.Body).Decode(&photoMeta)

    // Step 2: Download photo file from storage_service
    photoResp, err := http.Get(photoMeta.DownloadURL)
    if err != nil {
        return err
    }

    photoData, _ := ioutil.ReadAll(photoResp.Body)

    // Step 3: Display on e-ink/LCD screen
    f.DisplayImage(photoData)

    // Step 4: Update frame status via MQTT
    f.PublishFrameStatus(fileID, "displayed")

    return nil
}

func (f *SmartFrame) PublishFrameStatus(fileID string, status string) {
    statusMsg := map[string]interface{}{
        "frame_id": f.FrameID,
        "file_id": fileID,
        "status": status,
        "timestamp": time.Now().Format(time.RFC3339),
    }

    payload, _ := json.Marshal(statusMsg)
    topic := fmt.Sprintf("frames/%s/status", f.FrameID)

    f.mqttClient.Publish(topic, 1, false, payload)
}
```

---

### **Step 5: media_service Serves Photo Metadata**

**Endpoint:** `GET /api/v1/photos/{file_id}`

**Response:**
```json
{
    "file_id": "photo_xyz",
    "file_name": "family_photo.jpg",
    "content_type": "image/jpeg",
    "versions": [
        {
            "size": "thumbnail",
            "width": 300,
            "height": 200,
            "url": "http://storage-service:8220/api/v1/files/download/photo_xyz?size=thumbnail"
        },
        {
            "size": "hd",
            "width": 1920,
            "height": 1080,
            "url": "http://storage-service:8220/api/v1/files/download/photo_xyz?size=hd"
        },
        {
            "size": "original",
            "width": 4032,
            "height": 3024,
            "url": "http://storage-service:8220/api/v1/files/download/photo_xyz"
        }
    ],
    "ai_metadata": {
        "labels": ["family", "indoor"],
        "faces": [...]
    },
    "cached_for_frames": ["frame_001", "frame_002"]
}
```

---

## 4️⃣ Required Changes for arch.md Compliance

### **album_service** Upgrades

**Create `clients/` folder:**
```
album_service/clients/
├── __init__.py
├── storage_client.py    # Fetch file metadata from storage_service
└── media_client.py      # Trigger photo versioning in media_service
```

**Create `events/` folder structure:**
```
album_service/events/
├── __init__.py
├── models.py            # Event data models (AlbumPhotoAddedEventData, etc.)
├── publishers.py        # NATS event publishers
└── handlers.py          # ✅ Already exists - add file.uploaded.with_ai handler
```

**Create `mqtt/` folder:**
```
album_service/mqtt/
├── __init__.py
└── publisher.py         # MQTT publisher for smart frames
```

**New Events to Publish (NATS):**
- `album.photo_added` → Other services (notification_service, analytics)
- `album.photo_removed` → Other services
- `album.created` → notification_service (notify members)

---

### **media_service** Upgrades

**Refactor `events.py` → `events/` folder:**
```
media_service/events/
├── __init__.py
├── models.py            # Event data models
├── publishers.py        # Event publishers
└── handlers.py          # Move handlers from events.py
```

**Create `clients/` folder:**
```
media_service/clients/
├── __init__.py
└── storage_client.py    # Fetch files from storage_service
```

**New Events to Publish (NATS):**
- `media.version_created` → storage_service (cache optimization)
- `media.cache_ready` → album_service (notify frames)

---

## 5️⃣ MQTT Topic Design

### **Topic Hierarchy:**

```
albums/
  ├── {album_id}/
  │   ├── photo_added       # New photo added (QoS 1)
  │   ├── photo_removed     # Photo removed (QoS 1)
  │   └── config            # Album config updates (QoS 1, retained)
  │
frames/
  ├── {frame_id}/
  │   ├── sync              # Full sync command (QoS 2, retained)
  │   ├── command           # Frame commands (restart, update, etc.) (QoS 2)
  │   ├── status            # Frame status updates (QoS 0)
  │   └── heartbeat         # Keep-alive (QoS 0, retained)
  │
photos/
  ├── {file_id}/
      └── metadata_updated  # Photo metadata changed (QoS 1)
```

### **QoS Levels:**
- **QoS 0:** Frame heartbeats, telemetry (fire and forget)
- **QoS 1:** Photo updates, status changes (at least once)
- **QoS 2:** Sync commands, critical updates (exactly once)

### **Retained Messages:**
- `frames/{frame_id}/sync` - Last known album state
- `frames/{frame_id}/heartbeat` - Last known frame status
- `albums/{album_id}/config` - Current album configuration

---

## 6️⃣ Implementation Checklist

### **album_service:**
- [ ] Create `clients/storage_client.py`
- [ ] Create `clients/media_client.py`
- [ ] Create `events/models.py` with event data models
- [ ] Create `events/publishers.py` for NATS events
- [ ] Add `handle_file_uploaded_with_ai` handler
- [ ] Create `mqtt/publisher.py` for MQTT publishing
- [ ] Update `album_service.py` to initialize MQTT client
- [ ] Add `publish_photo_added_mqtt()` method
- [ ] Add `sync_album_to_frame()` method for full sync
- [ ] Update `main.py` to initialize clients and MQTT

### **media_service:**
- [ ] Refactor `events.py` → `events/handlers.py`
- [ ] Create `events/models.py`
- [ ] Create `events/publishers.py`
- [ ] Create `events/__init__.py`
- [ ] Create `clients/storage_client.py`
- [ ] Update `media_service.py` to use publishers
- [ ] Add endpoint `GET /api/v1/photos/{file_id}` for frames
- [ ] Add photo versioning for frame-specific sizes

### **Smart Frame Hardware:**
- [ ] MQTT subscription to `albums/{album_id}/photo_added`
- [ ] MQTT subscription to `frames/{frame_id}/sync`
- [ ] HTTP client to fetch from media_service
- [ ] HTTP client to download from storage_service
- [ ] Publish status to `frames/{frame_id}/status`
- [ ] Publish heartbeat to `frames/{frame_id}/heartbeat`

---

## 7️⃣ Sequence Diagram

```
Mobile App          storage_service     album_service      NATS        MQTT Broker    Smart Frame     media_service
    |                     |                   |              |               |              |                |
    | Upload Photo        |                   |              |               |              |                |
    |-------------------->|                   |              |               |              |                |
    |                     | file.uploaded     |              |               |              |                |
    |                     |------------------>|              |               |              |                |
    |                     |                   |              |               |              |                |
    |                     |                   | Add to Album |               |              |                |
    |                     |                   |------------  |               |              |                |
    |                     |                   |             ||               |              |                |
    |                     |                   |<------------|                |              |                |
    |                     |                   |              |               |              |                |
    |                     |                   | album.photo_added (NATS)     |              |                |
    |                     |                   |----------------------------->|              |                |
    |                     |                   |              |               |              |                |
    |                     |                   | photo_added (MQTT)           |              |                |
    |                     |                   |----------------------------->|              |                |
    |                     |                   |              |               | Notify Frame |                |
    |                     |                   |              |               |------------->|                |
    |                     |                   |              |               |              | GET /photos/xyz|
    |                     |                   |              |               |              |--------------->|
    |                     |                   |              |               |              |  Photo Metadata|
    |                     |                   |              |               |              |<---------------|
    |                     |                   |              |               |              |                |
    |                     |                   |              |               |              | Download Photo |
    |                     | <-------------------------------------------------------------|                |
    |                     |                   |              |               |              |                |
    |                     |                   |              |               | Frame Status |                |
    |                     |                   |              |               |<-------------|                |
```

---

## 8️⃣ Testing Strategy

### **Unit Tests:**
```python
# Test MQTT publisher
async def test_mqtt_publish_photo_added():
    publisher = AlbumMQTTPublisher()
    await publisher.connect()

    await publisher.publish_photo_added(
        album_id="test_album",
        file_id="test_photo",
        photo_metadata={...}
    )

    # Verify MQTT message was published
```

### **Integration Tests:**
```python
# Test full photo sharing flow
async def test_photo_sharing_flow():
    # 1. Upload photo to storage
    file_id = await storage_client.upload_photo(...)

    # 2. Wait for NATS event
    await wait_for_event("file.uploaded.with_ai")

    # 3. Verify photo added to album
    album = await album_repo.get_album("family_album")
    assert file_id in album.photos

    # 4. Verify MQTT message published
    mqtt_msg = await mqtt_subscriber.wait_for_message("albums/family_album/photo_added")
    assert mqtt_msg['file_id'] == file_id
```

---

## 9️⃣ Benefits of This Architecture

✅ **Event-Driven:** NATS for microservice communication
✅ **Real-Time:** MQTT for instant hardware updates
✅ **Scalable:** Services communicate via message brokers
✅ **Reliable:** QoS levels ensure message delivery
✅ **Flexible:** Smart frames can subscribe to multiple albums
✅ **Resilient:** Retained messages ensure state recovery
✅ **Observable:** All events published for analytics
✅ **Testable:** Each component can be tested independently

---

## 🎉 Summary

This architecture enables:
1. **Mobile app** uploads photo to **storage_service**
2. **storage_service** publishes NATS event `file.uploaded.with_ai`
3. **album_service** receives event, adds photo to album
4. **album_service** publishes MQTT message to `albums/{album_id}/photo_added`
5. **Smart frame hardware** receives MQTT notification
6. **Smart frame** fetches photo from **media_service**
7. **Smart frame** downloads file from **storage_service**
8. **Smart frame** displays photo and publishes status

All compliant with `arch.md` standards! 🚀
