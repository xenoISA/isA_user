# OTA Service Documentation

Complete documentation for the OTA (Over-The-Air) Update Service - Firmware management, update campaigns, device updates, and rollback operations.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [Update Types & Strategies](#update-types--strategies)
5. [Authentication](#authentication)
6. [Service-to-Service Communication](#service-to-service-communication)
7. [Testing](#testing)
8. [Examples](#examples)

## Overview

The OTA Service is a comprehensive microservice for managing firmware updates and over-the-air deployments for IoT devices in the isA ecosystem. It provides:

- **Firmware Management**: Upload, store, and version firmware binaries
- **Update Campaigns**: Create and manage large-scale deployment campaigns
- **Single Device Updates**: Target individual devices for immediate updates
- **Deployment Strategies**: Staged, canary, immediate, and blue-green deployments
- **Rollback Operations**: Automatic and manual rollback capabilities
- **Progress Monitoring**: Real-time update progress tracking
- **Batch Operations**: Efficient bulk device updates
- **Safety Features**: Checksum validation, auto-rollback, failure thresholds

### Service Information

- **Service Name**: ota_service
- **Port**: 8240
- **Version**: 1.0.0
- **Base URL**: `http://localhost:8240`
- **Health Check**: `GET /health`

## Architecture

### Service Dependencies

```
┌─────────────────────┐
│   OTA Service       │
│    (Port 8240)      │
└──────────┬──────────┘
           │
           ├───────────┬────────────┬──────────────┐
           │           │            │              │
    ┌──────▼─────┐ ┌──▼──────┐ ┌──▼─────────┐ ┌──▼─────────┐
    │ Auth       │ │ Device  │ │ Storage    │ │Notification│
    │ Service    │ │ Service │ │ Service    │ │ Service    │
    │ (8201)     │ │ (8220)  │ │ (8230)     │ │ (8250)     │
    └────────────┘ └─────────┘ └────────────┘ └────────────┘
         │             │             │              │
         └─────────────┴─────────────┴──────────────┘
                       PostgreSQL
```

### Key Components

1. **Main Application** (`main.py`): FastAPI application with all endpoints
2. **Service Logic** (`ota_service.py`): Business logic for updates and campaigns
3. **Models** (`models.py`): Pydantic models for request/response validation
4. **Client** (`client.py`): Service clients for external service communication
5. **Tests** (`tests/`): Comprehensive test scripts
6. **Docs** (`docs/`): Documentation and issues tracking

### Service Integrations

#### ✓ Implemented
- **Auth Service**: JWT/API key validation via Consul service discovery

#### ✗ Needed (High Priority)
- **Device Service**: Device validation, firmware compatibility checking
- **Storage Service**: Firmware binary storage (MinIO/S3)
- **Notification Service**: MQTT commands, user notifications

## API Endpoints

### Health & Info

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/health` | Basic health check | No |
| GET | `/health/detailed` | Detailed health with metrics | No |
| GET | `/api/v1/service/stats` | Service statistics and capabilities | No |

### Firmware Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/firmware` | Upload firmware file | Yes |
| GET | `/api/v1/firmware/{firmware_id}` | Get firmware details | Yes |
| GET | `/api/v1/firmware` | List firmware with filters | Yes |
| GET | `/api/v1/firmware/{firmware_id}/download` | Get download URL | Yes |
| DELETE | `/api/v1/firmware/{firmware_id}` | Delete firmware | Yes |

### Update Campaigns

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/campaigns` | Create update campaign | Yes |
| GET | `/api/v1/campaigns/{campaign_id}` | Get campaign details | Yes |
| GET | `/api/v1/campaigns` | List campaigns with filters | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/start` | Start campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/pause` | Pause campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/cancel` | Cancel campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/approve` | Approve campaign | Yes |
| GET | `/api/v1/stats/campaigns/{campaign_id}` | Get campaign stats | Yes |

### Device Updates

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/devices/{device_id}/update` | Update single device | Yes |
| GET | `/api/v1/updates/{update_id}` | Get update progress | Yes |
| GET | `/api/v1/devices/{device_id}/updates` | Get device update history | Yes |
| POST | `/api/v1/updates/{update_id}/cancel` | Cancel update | Yes |
| POST | `/api/v1/updates/{update_id}/retry` | Retry failed update | Yes |

### Rollback Operations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/devices/{device_id}/rollback` | Rollback device firmware | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/rollback` | Rollback entire campaign | Yes |

### Batch Operations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/devices/bulk/update` | Update multiple devices | Yes |

### Statistics & Analytics

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/stats` | Get overall update statistics | Yes |
| GET | `/api/v1/stats/campaigns/{campaign_id}` | Get campaign statistics | Yes |

## Update Types & Strategies

### Update Types

The service supports various update types defined in the `UpdateType` enum:

- **firmware**: Complete firmware updates (FOTA)
- **software**: Software/application updates (SOTA)
- **application**: Specific application updates (AOTA)
- **config**: Configuration updates (COTA)
- **bootloader**: Bootloader updates
- **security_patch**: Security patches

### Deployment Strategies

- **immediate**: Deploy to all devices immediately
- **scheduled**: Deploy at a specific time
- **staged**: Deploy in phases (e.g., 10%, 50%, 100%)
- **canary**: Deploy to small subset first, monitor, then rollout
- **blue_green**: Deploy to standby environment, then switch

### Update Status Flow

```
created → scheduled → in_progress → downloading →
verifying → installing → rebooting → completed
                                   ↓
                              failed/cancelled → rollback
```

## Authentication

### User Authentication

Most endpoints require user authentication via JWT token:

```bash
Authorization: Bearer <jwt_token>
```

Get token from auth_service:
```bash
POST http://localhost:8201/api/v1/auth/dev-token
{
  "user_id": "user_123",
  "email": "user@example.com",
  "expires_in": 3600
}
```

### API Gateway Integration

When deployed behind an API gateway:
- **External requests**: Gateway validates JWT → Forwards to service
- **Internal service calls**: Can bypass auth or use service tokens
- **Recommendation**: Configure gateway to handle all authentication

## Service-to-Service Communication

The OTA service communicates with other services using the client pattern. See `client.py` for implementations.

### Device Service Integration

**Purpose**: Validate devices and check firmware compatibility

```python
from microservices.ota_service.client import DeviceServiceClient

async with DeviceServiceClient() as client:
    # Get device details
    device = await client.get_device(device_id)

    # Check firmware compatibility
    compatible = await client.check_firmware_compatibility(
        device_id=device_id,
        firmware_model="SF-2024-Pro",
        hardware_version="1.0"
    )

    # Send update command
    result = await client.send_update_command(
        device_id=device_id,
        firmware_url="https://cdn.example.com/firmware.bin",
        firmware_version="2.0.0",
        checksum_sha256="abc123..."
    )
```

**Consul Service Discovery**:
```python
from microservices.ota_service.client import get_device_service_client

# Automatically discovers device service via Consul
client = await get_device_service_client(consul_registry)
```

### Storage Service Integration

**Purpose**: Store and retrieve firmware binaries

```python
from microservices.ota_service.client import StorageServiceClient

async with StorageServiceClient() as client:
    # Upload firmware binary
    url = await client.upload_firmware(
        firmware_id="fw_123",
        file_content=binary_data,
        filename="firmware_v2.0.0.bin"
    )

    # Get download URL
    download_url = await client.get_download_url(
        firmware_id="fw_123",
        expires_in=3600
    )

    # Delete firmware
    success = await client.delete_firmware("fw_123")
```

### Notification Service Integration

**Purpose**: Send MQTT commands and user notifications

```python
from microservices.ota_service.client import NotificationServiceClient

async with NotificationServiceClient() as client:
    # Send MQTT command to device
    await client.send_device_command(
        device_id="device_123",
        command={"action": "start_update", "firmware_url": "..."}
    )

    # Notify user of update status
    await client.notify_update_status(
        user_id="user_123",
        device_id="device_123",
        status="completed",
        firmware_version="2.0.0"
    )
```

## Testing

### Test Scripts

Located in `tests/` directory:

1. **ota_test.sh**: Complete OTA workflow testing (15 tests)
   ```bash
   cd microservices/ota_service
   bash tests/ota_test.sh
   ```

### Test Results

Current test pass rate: **12/15 (80%)**

**✓ Passing (12 tests):**
- Health checks
- Firmware upload
- Firmware list
- Campaign creation
- Campaign list
- Device update history
- Update statistics
- Device rollback
- Service statistics

**✗ Failing (3 tests):**
1. Get campaign details (campaign not found)
2. Start campaign (depends on test #1)
3. Update single device (device_id field validation issue)

**Issues Tracked**: See `docs/ota_issues.md` for detailed issue tracking and fixes

## Examples

### Example 1: Upload Firmware

```bash
# Prepare metadata
METADATA='{
  "name": "SmartFrame Firmware",
  "version": "2.1.0",
  "device_model": "SF-2024-Pro",
  "manufacturer": "SmartTech",
  "file_size": 5242880,
  "checksum_md5": "d41d8cd98f00b204e9800998ecf8427e",
  "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "changelog": "Bug fixes and improvements"
}'

# Upload firmware
curl -X POST http://localhost:8240/api/v1/firmware \
  -H "Authorization: Bearer $TOKEN" \
  -F "metadata=$METADATA" \
  -F "file=@firmware_v2.1.0.bin"
```

### Example 2: Create Update Campaign

```bash
curl -X POST http://localhost:8240/api/v1/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q4 2024 Update",
    "firmware_id": "fw_123",
    "target_filters": {
      "device_type": "smart_frame",
      "firmware_version": "<2.0.0"
    },
    "deployment_strategy": "staged",
    "rollout_percentage": 100,
    "max_concurrent_updates": 50,
    "batch_size": 10,
    "auto_rollback": true,
    "failure_threshold_percent": 20
  }'
```

### Example 3: Update Single Device

```bash
curl -X POST http://localhost:8240/api/v1/devices/$DEVICE_ID/update \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "'$DEVICE_ID'",
    "firmware_id": "fw_123",
    "priority": "high",
    "timeout_minutes": 30
  }'
```

### Example 4: Monitor Update Progress

```bash
# Get update progress
curl -X GET http://localhost:8240/api/v1/updates/$UPDATE_ID \
  -H "Authorization: Bearer $TOKEN"

# Get device update history
curl -X GET http://localhost:8240/api/v1/devices/$DEVICE_ID/updates \
  -H "Authorization: Bearer $TOKEN"
```

### Example 5: Rollback Device

```bash
curl -X POST http://localhost:8240/api/v1/devices/$DEVICE_ID/rollback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_version": "1.9.0",
    "reason": "Critical bug in 2.0.0"
  }'
```

### Python Client Examples

See `examples/ota_client_example.py` for comprehensive Python examples:

```python
from microservices.ota_service.client import DeviceServiceClient, StorageServiceClient

# Upload firmware
async with StorageServiceClient(auth_token=token) as storage:
    url = await storage.upload_firmware(
        firmware_id="fw_123",
        file_content=binary_data,
        filename="firmware.bin"
    )

# Update device
async with DeviceServiceClient(auth_token=token) as device:
    result = await device.send_update_command(
        device_id="device_123",
        firmware_url=url,
        firmware_version="2.0.0",
        checksum_sha256="abc123..."
    )
```

### Postman Collection

Import `OTA_Service_Postman_Collection.json` into Postman for interactive API testing.

Collection includes:
- Setup (generate auth token)
- Health checks
- Firmware management
- Campaign operations
- Device updates
- Rollback operations
- Statistics

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Successful operation
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Dependency service unavailable

### Error Response Format

```json
{
  "detail": "Error message describing the issue"
}
```

## Configuration

Service configuration via environment variables or Consul:

- **SERVICE_NAME**: ota_service
- **SERVICE_PORT**: 8240
- **SERVICE_HOST**: 0.0.0.0
- **CONSUL_HOST**: localhost
- **CONSUL_PORT**: 8500
- **LOG_LEVEL**: INFO

## Deployment

### Docker Deployment

The service runs in Docker with supervisord:

```bash
# Restart service
docker exec user-staging-dev supervisorctl restart ota_service

# View logs
docker exec user-staging-dev tail -f /var/log/isa-services/ota_service.log

# View errors
docker exec user-staging-dev tail -f /var/log/isa-services/ota_service_error.log
```

### Local Development

```bash
cd /Users/xenodennis/Documents/Fun/isA_user
python -m microservices.ota_service.main
```

## Database Schema

### Tables

1. **firmware**: Firmware metadata and checksums
2. **update_campaigns**: Campaign definitions and status
3. **device_updates**: Individual device update tracking
4. **firmware_downloads**: Download statistics

### Key Constraints

- `unique_firmware_version`: Unique constraint on (device_model, version)
- Foreign keys to ensure referential integrity

## Security Considerations

### ✓ Implemented
- Authentication via Auth Service
- JWT token validation
- API key support
- Checksum validation (MD5, SHA256)

### ✗ Needed
- Firmware signature verification
- Device ownership validation
- Rate limiting for uploads/downloads
- Access control for campaigns
- Encryption for firmware binaries

## Known Issues

See `docs/ota_issues.md` for detailed issue tracking.

### High Priority
1. ✗ Device Service client integration needed
2. ✗ Campaign creation/retrieval database issues
3. ✗ Device update endpoint validation issue

### Medium Priority
1. ✗ Storage Service integration needed
2. ✗ Campaign workflow implementation incomplete
3. ✗ Rollback functionality needs device communication

### Low Priority
1. ✗ Notification Service integration
2. ✗ Comprehensive logging and metrics
3. ✗ Firmware signature verification

## Performance Considerations

### Optimization Tips

1. **Batch Operations**: Use bulk endpoints for multiple devices
2. **Staged Deployment**: Reduce load with phased rollouts
3. **CDN Integration**: Serve firmware files from CDN
4. **Caching**: Cache firmware metadata
5. **Async Processing**: Use background tasks for long operations

### Scalability

- Horizontal scaling: Multiple OTA service instances
- Database: Read replicas for query load
- Storage: Distributed object storage (MinIO cluster, S3)
- Queue: Message queue for update orchestration

## Monitoring & Observability

### Metrics to Track

- Campaign success rate
- Update failure rate
- Average update time
- Bandwidth usage
- Concurrent updates
- Rollback frequency

### Logging

- All operations logged with Loki integration
- Structured JSON logging
- Request/response tracing
- Error tracking with stack traces

## Support

For issues or questions:
- Check test scripts in `tests/`
- Review examples in `examples/`
- Consult API documentation above
- Check service logs for errors
- Review `docs/ota_issues.md` for known issues

## Version History

### v1.0.0 (Current)
- Firmware upload and management
- Update campaign creation
- Single device updates
- Rollback operations
- Batch operations
- Statistics and monitoring
- Auth service integration
- Consul service discovery
- 80% test coverage
- Complete documentation

### Future Roadmap
- Device service integration
- Storage service integration
- Notification service integration
- Enhanced campaign workflow
- Real-time progress tracking
- Firmware signature verification
- Advanced deployment strategies
