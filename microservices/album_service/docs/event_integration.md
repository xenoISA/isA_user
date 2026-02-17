# Album Service Event Integration

**Service:** Album Service
**Port:** 8219
**Event Integration Status:** ✅ Complete
**Last Updated:** 2025-10-30

---

## Overview

The Album Service has been fully integrated into the event-driven architecture, enabling it to:
- **Publish events** when album operations occur (create, update, delete, photo management, sync)
- **Subscribe to events** from other services (file deletions, device deletions)

This integration enables:
- Real-time notifications when albums are modified
- Automatic cleanup when photos are deleted from storage
- Automatic cleanup when smart frames are removed
- Complete audit trail of all album operations
- Cross-service data consistency

---

## Published Events

Album Service publishes the following 6 event types:

### 1. `album.created`
Published when a new album is created.

**Event Data:**
```json
{
  "album_id": "album_abc123",
  "user_id": "user_456",
  "name": "Summer Vacation",
  "organization_id": "org_789",
  "is_family_shared": true,
  "auto_sync": true,
  "sync_frames": ["frame_123", "frame_456"],
  "timestamp": "2025-10-30T12:00:00Z"
}
```

**Subscribers:**
- Notification Service (notify album owner and family members)
- Audit Service (log album creation)

---

### 2. `album.updated`
Published when album details are updated (name, description, settings, etc.).

**Event Data:**
```json
{
  "album_id": "album_abc123",
  "user_id": "user_456",
  "updates": {
    "name": "Updated Album Name",
    "description": "New description",
    "tags": ["vacation", "2025"]
  },
  "timestamp": "2025-10-30T12:05:00Z"
}
```

**Subscribers:**
- Notification Service (notify family members if shared)
- Audit Service (log changes)

---

### 3. `album.deleted`
Published when an album is deleted.

**Event Data:**
```json
{
  "album_id": "album_abc123",
  "user_id": "user_456",
  "timestamp": "2025-10-30T12:10:00Z"
}
```

**Subscribers:**
- Notification Service (notify family members if shared)
- Audit Service (log deletion)
- Storage Service (optional cleanup of album-specific metadata)

---

### 4. `album.photo.added`
Published when photos are added to an album.

**Event Data:**
```json
{
  "album_id": "album_abc123",
  "user_id": "user_456",
  "photo_ids": ["photo_1", "photo_2", "photo_3"],
  "added_count": 3,
  "timestamp": "2025-10-30T12:15:00Z"
}
```

**Subscribers:**
- Notification Service (notify album members)
- Device Service (trigger sync if auto_sync enabled)
- Audit Service (log additions)

---

### 5. `album.photo.removed`
Published when photos are removed from an album.

**Event Data:**
```json
{
  "album_id": "album_abc123",
  "user_id": "user_456",
  "photo_ids": ["photo_1", "photo_2"],
  "removed_count": 2,
  "timestamp": "2025-10-30T12:20:00Z"
}
```

**Subscribers:**
- Notification Service (notify album members)
- Device Service (update sync status)
- Audit Service (log removals)

---

### 6. `album.synced`
Published when an album is synced to a smart frame device.

**Event Data:**
```json
{
  "album_id": "album_abc123",
  "user_id": "user_456",
  "frame_id": "frame_123",
  "sync_status": "in_progress",
  "total_photos": 25,
  "timestamp": "2025-10-30T12:25:00Z"
}
```

**Subscribers:**
- Device Service (initiate actual sync)
- Notification Service (notify user of sync status)
- Telemetry Service (track sync metrics)
- Audit Service (log sync operations)

---

## Subscribed Events

Album Service subscribes to the following events:

### 1. `file.deleted` (from Storage Service)
When a photo file is deleted from storage, automatically remove it from all albums.

**Handler:** `AlbumEventHandler.handle_file_deleted()`

**Actions:**
1. Extract `file_id` from event
2. Query all albums containing this photo
3. Remove photo from all albums
4. Update album photo counts
5. Log cleanup operation

**Expected Event Data:**
```json
{
  "file_id": "photo_123",
  "user_id": "user_456",
  "timestamp": "2025-10-30T12:30:00Z"
}
```

**Error Handling:**
- If `file_id` is missing: Log warning, return false
- If removal fails: Log error but don't throw (graceful degradation)
- Transaction isolation: Uses database transactions

---

### 2. `device.offline` / `device.deleted` (from Device Service)
When a smart frame device is deleted or goes permanently offline, clean up sync status records.

**Handler:** `AlbumEventHandler.handle_device_deleted()`

**Actions:**
1. Extract `device_id` from event
2. Find all sync status records for this device
3. Delete sync status records
4. Log cleanup operation

**Expected Event Data:**
```json
{
  "device_id": "frame_123",
  "user_id": "user_456",
  "timestamp": "2025-10-30T12:35:00Z"
}
```

**Error Handling:**
- If `device_id` is missing: Log warning, return false
- If deletion fails: Log error but don't throw
- Idempotent: Safe to call multiple times

---

## Event Flow Examples

### Example 1: Album Creation Flow

```
User → Album Service → album.created event
                     ↓
                     ├→ Notification Service → Push notification
                     ├→ Audit Service → Log creation
                     └→ Organization Service → Update shared resource count
```

### Example 2: Photo Deletion Flow

```
User → Storage Service → file.deleted event
                       ↓
                       → Album Service → Remove from all albums
                                       ↓
                                       → album.photo.removed events
                                          ↓
                                          ├→ Notification Service
                                          └→ Device Service → Update sync
```

### Example 3: Album Sync Flow

```
User → Album Service → album.synced event
                     ↓
                     ├→ Device Service → Initiate frame sync
                     ├→ Notification Service → "Syncing..." notification
                     └→ Telemetry Service → Record sync metrics
```

---

## Implementation Details

### Event Publishing

Events are published in `album_service.py` using the NATS event bus:

```python
if self.event_bus:
    try:
        event = Event(
            event_type=EventType.ALBUM_CREATED,
            source=ServiceSource.ALBUM_SERVICE,
            data={...}
        )
        await self.event_bus.publish_event(event)
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
```

**Key Points:**
- Event publishing is **non-blocking** and **asynchronous**
- Failures are logged but don't affect core operations
- All events include timestamps and source information
- Event bus is optional (graceful degradation)

---

### Event Subscription

Event subscriptions are set up in `main.py` during service startup:

```python
if event_bus:
    album_repo = AlbumRepository()
    event_handler = AlbumEventHandler(album_repo)

    await event_bus.subscribe(
        subject="events.file.deleted",
        callback=lambda msg: event_handler.handle_event(msg)
    )
```

**Key Points:**
- Subscriptions are established at startup
- Each handler has direct database access
- Handlers are designed to be **idempotent**
- Failed event handling is logged but doesn't crash service

---

## Database Operations

### Repository Methods for Event Handling

#### `remove_photo_from_all_albums(photo_id: str) -> int`
Removes a photo from all albums where it appears.

**SQL:**
```sql
DELETE FROM albums.album_photos
WHERE photo_id = $1
```

**Returns:** Number of albums affected

---

#### `delete_sync_status_by_frame(frame_id: str) -> int`
Deletes all sync status records for a specific frame.

**SQL:**
```sql
DELETE FROM albums.album_sync_status
WHERE frame_id = $1
```

**Returns:** Number of records deleted

---

## Testing

### Unit Tests: Event Publishing

**File:** `tests/test_event_publishing.py`

**Tests:**
1. ✅ Album created event is published with correct data
2. ✅ Album updated event is published with correct data
3. ✅ Album deleted event is published with correct data
4. ✅ Photo added event is published with correct data
5. ✅ Photo removed event is published with correct data
6. ✅ Album synced event is published with correct data

**Run:** `python microservices/album_service/tests/test_event_publishing.py`

**Results:** 6/6 tests passing ✅

---

### Integration Tests: Event Subscriptions

**File:** `tests/test_event_subscriptions.py`

**Tests:**
1. ✅ file.deleted event removes photo from all albums
2. ✅ device.deleted event cleans up sync status
3. ✅ Missing file_id is handled gracefully
4. ✅ Missing device_id is handled gracefully
5. ✅ Event routing works correctly
6. ✅ Subscriptions are configured correctly

**Run:** `python microservices/album_service/tests/test_event_subscriptions.py`

**Results:** 6/6 tests passing ✅

---

## Performance Considerations

### Event Publishing
- **Latency:** < 5ms overhead per operation
- **Throughput:** Does not limit album operations
- **Reliability:** Events published asynchronously, failures logged

### Event Subscription
- **Concurrency:** Handles multiple events in parallel
- **Batching:** Not currently implemented (future optimization)
- **Idempotency:** Safe to process same event multiple times

---

## Error Handling & Monitoring

### Event Publishing Failures
```python
logger.error(f"Failed to publish album.created event: {e}")
# Service continues operating normally
```

### Event Subscription Failures
```python
logger.error(f"Failed to handle file.deleted event: {e}", exc_info=True)
# Returns false but doesn't crash service
```

### Monitoring Points
- Count of events published per type
- Count of events received per type
- Event processing latency
- Failed event handling attempts

**Recommended Alerts:**
- Event publishing failure rate > 5%
- Event processing latency > 1s
- Event queue depth > 1000

---

## Configuration

### Environment Variables

```bash
# NATS Configuration (from core config)
NATS_URL=nats://localhost:4222
NATS_CLUSTER_ID=isa_cloud_cluster
NATS_CLIENT_ID=album_service_001

# Service Configuration
ALBUM_SERVICE_PORT=8219
```

### Service Config

Event bus initialization is handled by `ConfigManager` and `get_event_bus()`:

```python
event_bus = await get_event_bus("album_service")
album_service = AlbumService(event_bus=event_bus)
```

---

## Migration Notes

### Before Event Integration
- Album operations were isolated
- No notifications on album changes
- Manual cleanup required for deleted photos
- No audit trail of album operations

### After Event Integration
- Real-time notifications enabled
- Automatic cleanup on file/device deletion
- Complete audit trail
- Cross-service consistency maintained

### Breaking Changes
- None (backward compatible)

---

## Future Enhancements

### Planned Features
1. **Batch Event Publishing:** Publish multiple photo additions as single event
2. **Event Replay:** Ability to replay events for debugging
3. **Event Versioning:** Support for event schema evolution
4. **Dead Letter Queue:** Handle persistently failing events

### Potential Subscriptions
1. `organization.member.removed` - Remove access to shared albums
2. `user.deleted` - Clean up all albums for deleted user
3. `storage.quota.exceeded` - Prevent adding more photos

---

## Troubleshooting

### Event Not Published

**Symptoms:** Operation succeeds but no event appears in logs

**Possible Causes:**
1. Event bus not initialized
2. NATS server not running
3. Network connectivity issues

**Solution:**
```bash
# Check NATS connection
curl http://localhost:8219/health

# Check service logs
tail -f logs/album_service.log | grep "Event"
```

---

### Event Not Received

**Symptoms:** Event published but subscriber doesn't process it

**Possible Causes:**
1. Subscription not set up
2. Event handler error
3. Subject mismatch

**Solution:**
```python
# Verify subscriptions in logs
"✅ Subscribed to file.deleted events"

# Check event handler logs
logger.info(f"Handling file.deleted event for file {file_id}")
```

---

## Summary

**Status:** ✅ **Production Ready**

**Published Events:** 6/6 implemented and tested
- album.created ✅
- album.updated ✅
- album.deleted ✅
- album.photo.added ✅
- album.photo.removed ✅
- album.synced ✅

**Subscribed Events:** 2/2 implemented and tested
- file.deleted ✅
- device.deleted ✅

**Test Coverage:** 12/12 tests passing (100%)

**Integration Status:** Fully integrated with event-driven architecture

---

## References

- [NATS JetStream Documentation](https://docs.nats.io/nats-concepts/jetstream)
- [Event-Driven Architecture Guide](../../docs/event_driven_architecture_design.md)
- [Service Event Status](../../docs/service_event_status.md)
- [Core NATS Client](../../core/nats_client.py)
