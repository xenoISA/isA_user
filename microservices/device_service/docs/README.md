# Device Service Documentation

Complete documentation for the Device Management Service - IoT device registration, authentication, lifecycle management, and smart frame operations.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [Device Types](#device-types)
5. [Authentication](#authentication)
6. [Smart Frame Features](#smart-frame-features)
7. [Testing](#testing)
8. [Examples](#examples)

## Overview

The Device Service is a comprehensive microservice for managing IoT devices in the isA ecosystem. It provides:

- **Device Registration & Lifecycle Management**: Complete CRUD operations for devices
- **Device Authentication**: Secure device credential management via auth_service integration
- **Command & Control**: Send commands to devices via MQTT
- **Health Monitoring**: Real-time device health and metrics
- **Smart Frame Support**: Specialized operations for smart photo frames
- **Family Sharing**: Integration with organization_service for shared device access
- **Bulk Operations**: Efficient batch operations for multiple devices

### Service Information

- **Service Name**: device_service
- **Port**: 8220
- **Version**: 1.0.0
- **Base URL**: `http://localhost:8220`
- **Health Check**: `GET /health`

## Architecture

### Service Dependencies

```
┌─────────────────────┐
│  Device Service     │
│    (Port 8220)      │
└──────────┬──────────┘
           │
           ├──────────────┐
           │              │
    ┌──────▼─────┐  ┌────▼──────────┐
    │ Auth       │  │ Organization  │
    │ Service    │  │ Service       │
    │ (8201)     │  │ (8210)        │
    └────────────┘  └───────────────┘
           │              │
           │         ┌────▼──────────┐
           │         │ Storage       │
           │         │ Service       │
           └─────────│ (8230)        │
                     └───────────────┘
```

### Key Components

1. **Main Application** (`main.py`): FastAPI application with all endpoints
2. **Service Logic** (`device_service.py`): Business logic and device operations
3. **Models** (`models.py`): Pydantic models for request/response validation
4. **Client** (`client.py`): Service clients for external service communication
5. **Tests** (`tests/`): Comprehensive test scripts
6. **Examples** (`examples/`): Usage examples and client code

## API Endpoints

### Health & Info

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/health` | Basic health check | No |
| GET | `/health/detailed` | Detailed health with component status | No |
| GET | `/api/v1/service/stats` | Service statistics and capabilities | No |
| GET | `/api/v1/debug/consul` | Consul registry debug info | No |

### Device CRUD Operations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/devices` | Register new device | Yes |
| GET | `/api/v1/devices/{device_id}` | Get device details | Yes |
| PUT | `/api/v1/devices/{device_id}` | Update device information | Yes |
| DELETE | `/api/v1/devices/{device_id}` | Decommission device | Yes |
| GET | `/api/v1/devices` | List devices with filters | Yes |

### Device Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/devices/auth` | Authenticate device and get token | No |

Note: Device authentication requires device credentials (device_id + device_secret) registered in auth_service.

### Device Commands

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/devices/{device_id}/commands` | Send command to device | Yes |
| POST | `/api/v1/devices/bulk/commands` | Send command to multiple devices | Yes |

### Device Monitoring

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/devices/{device_id}/health` | Get device health status | Yes |
| GET | `/api/v1/devices/stats` | Get device statistics | Yes |

### Smart Frame Operations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/devices/frames` | List smart frames with sharing permissions | Yes |
| POST | `/api/v1/devices/frames/{frame_id}/display` | Control frame display | Yes |
| POST | `/api/v1/devices/frames/{frame_id}/sync` | Sync content to frame | Yes |
| PUT | `/api/v1/devices/frames/{frame_id}/config` | Update frame configuration | Yes |

### Device Groups

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/groups` | Create device group | Yes |
| GET | `/api/v1/groups/{group_id}` | Get group details | Yes |
| PUT | `/api/v1/groups/{group_id}/devices/{device_id}` | Add device to group | Yes |

### Bulk Operations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/devices/bulk/register` | Register multiple devices | Yes |
| POST | `/api/v1/devices/bulk/commands` | Send commands to multiple devices | Yes |

## Device Types

The service supports various device types defined in the `DeviceType` enum:

- **sensor**: IoT sensors (temperature, humidity, motion, etc.)
- **actuator**: Actuators and controllers
- **gateway**: Network gateways and hubs
- **smart_home**: Smart home devices
- **smart_frame**: Smart photo frames (tablets with display)
- **camera**: Security and monitoring cameras
- **industrial**: Industrial IoT devices
- **medical**: Medical IoT devices
- **automotive**: Automotive devices
- **wearable**: Wearable devices
- **controller**: Control devices

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

### Device Authentication

Devices authenticate using device credentials:

1. **Register device in auth_service**:
```bash
POST http://localhost:8201/api/v1/auth/device/register
{
  "device_id": "device_123",
  "organization_id": "org_123",
  "device_name": "My Device",
  "device_type": "smart_frame"
}
```

2. **Authenticate device**:
```bash
POST http://localhost:8220/api/v1/devices/auth
{
  "device_id": "device_123",
  "device_secret": "<secret_from_registration>"
}
```

3. **Use device token** for subsequent requests

## Smart Frame Features

Smart frames are special devices with additional capabilities:

### Display Control
- Display specific photos
- Control slideshow
- Set transitions and effects
- Configure display modes

### Content Sync
- Sync photos from albums
- Incremental or full sync
- Automatic sync scheduling
- Wi-Fi only sync option

### Configuration
- Brightness and contrast control
- Auto-brightness
- Slideshow interval
- Sleep schedule
- Orientation (portrait/landscape/auto)

### Family Sharing
- Share frames with family members via organization_service
- Permission-based access (read/read_write)
- Multi-user content access

### Example Smart Frame Operations

```python
# Register smart frame
POST /api/v1/devices
{
  "device_name": "Living Room Frame",
  "device_type": "smart_frame",
  "manufacturer": "SmartTech",
  "model": "SF-2024-Pro",
  "serial_number": "SN123456789",
  "firmware_version": "1.0.0",
  "connectivity_type": "wifi",
  "metadata": {
    "screen_size": "10.1 inch",
    "resolution": "1920x1080",
    "frame_config": {
      "brightness": 80,
      "slideshow_interval": 30,
      "display_mode": "photo_slideshow"
    }
  }
}

# Control display
POST /api/v1/devices/frames/{frame_id}/display
{
  "action": "display_photo",
  "photo_id": "photo_123",
  "transition": "fade",
  "duration": 10
}

# Sync content
POST /api/v1/devices/frames/{frame_id}/sync
{
  "album_ids": ["album_001", "album_002"],
  "sync_type": "incremental",
  "force": false
}

# Update config
PUT /api/v1/devices/frames/{frame_id}/config
{
  "brightness": 85,
  "slideshow_interval": 60,
  "display_mode": "photo_slideshow"
}
```

## Testing

### Test Scripts

Located in `tests/` directory:

1. **device_test.sh**: Complete CRUD operations (11 tests)
   ```bash
   cd microservices/device_service
   bash tests/device_test.sh
   ```

2. **device_auth_test.sh**: Authentication flow (6 tests)
   ```bash
   bash tests/device_auth_test.sh [org_id]
   ```

3. **device_commands_test.sh**: Commands and smart frames (8 tests)
   ```bash
   bash tests/device_commands_test.sh
   ```

### Test Results

All tests pass ✅:
- Device registration: PASSED
- Device retrieval: PASSED
- Device update: PASSED
- Device listing: PASSED
- Device health: PASSED
- Device decommissioning: PASSED
- Authentication: PASSED
- Unauthorized access rejection: PASSED

## Examples

### Python Client

See `examples/device_client_example.py` for comprehensive Python client examples:

```python
from device_client_example import DeviceServiceClient, AuthServiceClient

# Get auth token
async with AuthServiceClient() as auth_client:
    token_response = await auth_client.generate_dev_token(
        user_id="user_123",
        email="user@example.com"
    )
    token = token_response["token"]

# Use device service
async with DeviceServiceClient(auth_token=token) as client:
    # Register device
    device = await client.register_device({
        "device_name": "My Smart Frame",
        "device_type": "smart_frame",
        # ... other fields
    })

    # Get device
    details = await client.get_device(device["device_id"])

    # Send command
    result = await client.send_command(
        device["device_id"],
        {"command": "status_check", "parameters": {}}
    )
```

### Postman Collection

Import `Device_Service_Postman_Collection.json` into Postman for interactive API testing.

Collection includes:
- Setup (generate auth token)
- Health checks
- Device CRUD operations
- Authentication flow
- Command operations
- Monitoring
- Smart frame operations
- Device groups

### Shell Scripts

See `tests/` directory for shell script examples using curl.

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Successful operation
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Device not found
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

- **SERVICE_NAME**: device_service
- **SERVICE_PORT**: 8220
- **SERVICE_HOST**: 0.0.0.0
- **CONSUL_HOST**: localhost
- **CONSUL_PORT**: 8500
- **LOG_LEVEL**: INFO

## Deployment

### Docker Deployment

The service runs in Docker with supervisord:

```bash
# Restart service
docker exec user-staging-dev supervisorctl restart device_service

# View logs
docker exec user-staging-dev tail -f /var/log/isa-services/device_service.log

# View errors
docker exec user-staging-dev tail -f /var/log/isa-services/device_service_error.log
```

### Local Development

```bash
cd /Users/xenodennis/Documents/Fun/isA_user
python -m microservices.device_service.main
```

## Support

For issues or questions:
- Check test scripts in `tests/`
- Review examples in `examples/`
- Consult API documentation above
- Check service logs for errors

## Version History

### v1.0.0 (Current)
- Device CRUD operations
- Device authentication integration
- Command sending via MQTT
- Health monitoring
- Smart frame support
- Family sharing integration
- Bulk operations
- Comprehensive testing
- Complete documentation
