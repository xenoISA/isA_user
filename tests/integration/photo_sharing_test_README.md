# 📸 Photo Sharing MQTT Integration Test

End-to-end integration test for the complete photo sharing workflow from mobile app → MQTT → smart frame.

## 🎯 Test Coverage

### Complete Workflow:
1. **Mobile App** uploads photo to storage_service
2. **storage_service** processes with AI and publishes `file.uploaded.with_ai` event
3. **album_service** receives NATS event and adds photo to album
4. **album_service** publishes MQTT message to `albums/{album_id}/photo_added`
5. **Smart Frame** (simulated) receives MQTT notification
6. **Smart Frame** fetches metadata from media_service
7. **Smart Frame** downloads photo from storage_service
8. **Smart Frame** displays photo (simulated)
9. **Smart Frame** publishes status to `frames/{frame_id}/status`

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install pytest pytest-asyncio httpx pillow

# Ensure isa_common is installed
pip install -e /path/to/isA_Cloud/isA_common
```

### Setup Test Environment

```bash
# 1. Start all required services
cd /path/to/isA_user

# Start MQTT broker (if using Docker)
docker run -d -p 1883:1883 -p 50053:50053 --name mqtt-broker eclipse-mosquitto

# Start microservices
python -m microservices.storage_service.main &
python -m microservices.album_service.main &
python -m microservices.media_service.main &

# 2. Create test fixtures
cd tests/integration
python test_photo_sharing_mqtt_e2e.py  # Creates test photo
```

### Run Tests

```bash
# Run all integration tests
pytest tests/integration/test_photo_sharing_mqtt_e2e.py -v

# Run specific test
pytest tests/integration/test_photo_sharing_mqtt_e2e.py::test_photo_sharing_e2e_with_mqtt -v

# Run with detailed output
pytest tests/integration/test_photo_sharing_mqtt_e2e.py -v -s
```

---

## 📋 Test Configuration

Edit `test_photo_sharing_mqtt_e2e.py` to configure:

```python
TEST_CONFIG = {
    "storage_service_url": "http://localhost:8220",
    "album_service_url": "http://localhost:8219",
    "media_service_url": "http://localhost:8222",
    "mqtt_host": "localhost",
    "mqtt_port": 50053,
    "test_user_id": "test_user_photo_share_001",
    "test_album_id": "family_album_test_001",
    "test_frame_id": "smart_frame_test_001",
    "test_photo_path": "tests/fixtures/test_photo.jpg"
}
```

---

## 🧪 Available Tests

### 1. `test_photo_sharing_e2e_with_mqtt()`
**Full end-to-end test** covering all 9 steps of the workflow.

**Expected Output:**
```
🚀 Starting End-to-End Photo Sharing Integration Test
================================================================================

📡 Step 1: Connecting Smart Frame to MQTT
🖼️  [Smart Frame smart_frame_test_001] Connecting to MQTT broker...
✅ [Smart Frame smart_frame_test_001] Connected to MQTT (session: xxx)

📱 Step 2: Mobile App Uploads Photo
✅ [Mobile App] Photo uploaded successfully: photo_xyz

⏳ Step 3: Waiting for Event Processing...

🔔 Step 4: Smart Frame Checking for MQTT Notification

📊 Step 5: Smart Frame Fetches Photo Metadata
✅ [Smart Frame] Metadata fetched:
   - Labels: ['family', 'indoor', 'birthday']
   - Versions: 3

📥 Step 6: Smart Frame Downloads Photo
✅ [Smart Frame] Photo downloaded: 245678 bytes

🖼️  Step 7: Smart Frame Displays Photo
✅ [Smart Frame] Photo displayed successfully!

📤 Step 8: Smart Frame Publishes Status
✅ [Smart Frame] Status published to frames/smart_frame_test_001/status

✅ Step 9: Verification Complete
   - File ID: photo_xyz
   - Photo Size: 245678 bytes

🎉 End-to-End Photo Sharing Test PASSED
```

### 2. `test_album_service_adds_photo_to_album()`
Tests that album_service correctly handles `file.uploaded.with_ai` event.

**Verifies:**
- Photo is added to specified album
- NATS event subscription works
- Album repository updated

### 3. `test_media_service_photo_endpoint()`
Tests the new `GET /api/v1/photos/{file_id}` endpoint.

**Verifies:**
- Endpoint returns photo metadata
- AI labels are present
- Multiple photo versions available
- Download URLs provided

---

## 🛠️ Test Components

### `SimulatedMobileApp`
Simulates a mobile application uploading photos.

**Methods:**
- `upload_photo()` - Upload photo with album_id metadata

### `SimulatedSmartFrame`
Simulates smart frame hardware.

**Methods:**
- `connect_mqtt()` - Connect to MQTT broker
- `subscribe_to_album()` - Subscribe to album updates
- `wait_for_photo_notification()` - Wait for MQTT message
- `fetch_photo_metadata()` - GET from media_service
- `download_photo()` - Download from storage_service
- `display_photo()` - Simulate display (delay)
- `publish_status()` - Publish frame status to MQTT

---

## 📊 Test Data Setup

### Create Test Album

```bash
# Create test album via album_service
curl -X POST http://localhost:8219/api/v1/albums \
  -H "Content-Type: application/json" \
  -d '{
    "album_name": "Test Family Album",
    "album_id": "family_album_test_001",
    "owner_id": "test_user_photo_share_001",
    "album_type": "family"
  }'
```

### Create Test User

```bash
# Create test user via account_service
curl -X POST http://localhost:8202/api/v1/accounts/ensure \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_photo_share_001",
    "email": "test@example.com",
    "full_name": "Test User"
  }'
```

### Create Test Frame (Device)

```bash
# Register test frame via device_service
curl -X POST http://localhost:8210/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "smart_frame_test_001",
    "device_name": "Test Smart Frame",
    "device_type": "smart_frame",
    "user_id": "test_user_photo_share_001"
  }'
```

---

## 🔍 Debugging

### Check NATS Events

```bash
# Subscribe to all NATS events
nats sub "events.>"

# Subscribe to specific events
nats sub "events.storage_service.file.uploaded.with_ai"
nats sub "events.album_service.album.photo_added"
```

### Check MQTT Messages

```bash
# Subscribe to all album updates
mosquitto_sub -h localhost -t "albums/#" -v

# Subscribe to specific album
mosquitto_sub -h localhost -t "albums/family_album_test_001/photo_added" -v

# Subscribe to frame status
mosquitto_sub -h localhost -t "frames/smart_frame_test_001/status" -v
```

### Check Service Logs

```bash
# View logs for each service
tail -f logs/storage_service.log
tail -f logs/album_service.log
tail -f logs/media_service.log
```

### Manual API Testing

```bash
# 1. Upload photo
curl -X POST http://localhost:8220/api/v1/storage/photos/upload \
  -F "file=@tests/fixtures/test_photo.jpg" \
  -F "user_id=test_user_photo_share_001" \
  -F "metadata={\"album_id\":\"family_album_test_001\"}"

# 2. Check album
curl http://localhost:8219/api/v1/albums/family_album_test_001

# 3. Get photo metadata from media_service
curl "http://localhost:8222/api/v1/photos/{file_id}?frame_id=smart_frame_test_001"

# 4. Download photo
curl http://localhost:8220/api/v1/files/download/{file_id}?size=hd -o test_download.jpg
```

---

## ⚠️ Common Issues

### 1. MQTT Connection Failed
**Solution:** Ensure MQTT broker is running and accessible:
```bash
# Check if MQTT broker is running
netstat -an | grep 50053

# Start MQTT broker
docker start mqtt-broker
```

### 2. Event Not Received
**Solution:** Check NATS connection:
```bash
# Verify NATS is running
nats server ping

# Check event subscriptions
nats stream ls
```

### 3. Photo Upload Fails
**Solution:** Check storage_service and MinIO:
```bash
# Verify storage_service is running
curl http://localhost:8220/health

# Check MinIO
mc ls local/photos
```

### 4. Album Not Found
**Solution:** Create test album first (see Test Data Setup above)

### 5. Test Photo Missing
**Solution:** Run the test file directly to create fixture:
```bash
python tests/integration/test_photo_sharing_mqtt_e2e.py
```

---

## 📈 Expected Results

### ✅ Success Criteria

- [ ] Photo uploaded successfully to storage_service
- [ ] File ID returned from upload
- [ ] NATS event `file.uploaded.with_ai` published
- [ ] album_service receives event and adds photo to album
- [ ] MQTT message published to `albums/{album_id}/photo_added`
- [ ] Smart frame can fetch metadata from media_service
- [ ] Metadata includes AI labels and photo versions
- [ ] Smart frame can download photo
- [ ] Frame status published to MQTT

### 📊 Performance Benchmarks

- Upload time: < 5 seconds
- Event processing time: < 3 seconds
- MQTT delivery: < 1 second
- Metadata fetch: < 500ms
- Photo download: < 2 seconds (for HD)

---

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Photo Sharing E2E Tests

on: [push, pull_request]

jobs:
  integration-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      mqtt:
        image: eclipse-mosquitto
        ports:
          - 1883:1883
          - 50053:50053

      minio:
        image: minio/minio
        env:
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin
        ports:
          - 9000:9000

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -e isA_common

      - name: Start microservices
        run: |
          python -m microservices.storage_service.main &
          python -m microservices.album_service.main &
          python -m microservices.media_service.main &
          sleep 10

      - name: Run integration tests
        run: |
          pytest tests/integration/test_photo_sharing_mqtt_e2e.py -v
```

---

## 📝 Next Steps

1. **Hardware Integration:** Use this test as reference for real smart frame implementation
2. **Load Testing:** Test with multiple frames and high photo volume
3. **Error Scenarios:** Add tests for network failures, timeouts
4. **Performance:** Benchmark end-to-end latency
5. **Monitoring:** Add metrics collection for production

---

## 🤝 Contributing

When adding new features to the photo sharing workflow:

1. Update the test to cover new functionality
2. Add assertions for new event types
3. Document expected behavior
4. Update this README with new test cases

---

## 📚 Related Documentation

- [Photo Sharing Architecture](../../docs/photo_sharing_mqtt_architecture.md)
- [arch.md Standards](../../arch.md)
- [MQTT Client Guide](../../../isA_Cloud/isA_common/docs/how_to_mqtt_client.md)
- [Integration Test Guide](./README.md)

---

**Last Updated:** 2025-01-11
**Test Coverage:** End-to-end photo sharing with MQTT
**Status:** ✅ Ready for use
