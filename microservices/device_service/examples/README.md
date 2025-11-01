# Device Service Examples

This directory contains example code demonstrating how to use the Device Service.

## Prerequisites

- Python 3.8+
- Running services:
  - Auth Service (localhost:8201)
  - Device Service (localhost:8220)
- Required packages:
  ```bash
  pip install httpx asyncio
  ```

## Examples

### device_client_example.py

Comprehensive examples showing device service usage:

**Example 1: Basic Device Management**
- Generate authentication token
- Register new device
- Get device details
- Update device information
- List devices
- Get device health status

**Example 2: Device Authentication Flow**
- Register device in auth service
- Get device secret (shown only once!)
- Authenticate device and get access token
- Use device token for API calls

**Example 3: Device Commands**
- Send status check command
- Send reboot command
- Send firmware update command
- Monitor command status

**Example 4: Smart Frame Operations**
- Register smart frame device
- Control frame display
- Sync frame content
- Update frame configuration

## Running the Examples

```bash
# Run all examples
cd /Users/xenodennis/Documents/Fun/isA_user
python -m microservices.device_service.examples.device_client_example

# Or run individual functions by modifying main()
```

## Example Output

```
======================================================================
Example 1: Basic Device Management
======================================================================

1. Generating user authentication token...
   ✓ Token generated: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

2. Registering a new smart frame device...
   ✓ Device registered: abc123def456
     Name: Living Room Smart Frame
     Type: smart_frame
     Status: pending

3. Getting device details...
   ✓ Retrieved device: Living Room Smart Frame

4. Updating device...
   ✓ Device updated: firmware v1.1.0

5. Listing all devices...
   ✓ Found 1 device(s)

6. Getting device health...
   ✓ Health score: 95.5
     CPU: 23.4%
     Memory: 45.6%
```

## Service Connections

The examples demonstrate how to connect to multiple services:

### 1. Auth Service (http://localhost:8201)
- Generate user tokens: `POST /api/v1/auth/dev-token`
- Register devices: `POST /api/v1/auth/device/register`
- Authenticate devices: `POST /api/v1/auth/device/authenticate`

### 2. Device Service (http://localhost:8220)
- Register devices: `POST /api/v1/devices`
- Get device: `GET /api/v1/devices/{device_id}`
- Update device: `PUT /api/v1/devices/{device_id}`
- List devices: `GET /api/v1/devices`
- Send commands: `POST /api/v1/devices/{device_id}/commands`
- Get health: `GET /api/v1/devices/{device_id}/health`

### 3. Organization Service (http://localhost:8210) - Implicit
- Smart frame access control (via device service)
- Family sharing permissions

### 4. Storage Service (http://localhost:8230) - Implicit
- Album access for smart frames (via device service)
- Photo sync operations

## Key Concepts

### Device Registration Flow

1. **User authenticates** → Gets JWT token from auth service
2. **Register device** → Create device in device service
3. **Device authentication** → Register device credentials in auth service
4. **Device operation** → Use device token for API calls

### Device Types

- `sensor` - IoT sensors
- `actuator` - Actuators and controllers
- `gateway` - Network gateways
- `smart_frame` - Smart photo frames
- `camera` - Security cameras
- And more...

### Device Status

- `pending` - Waiting for activation
- `active` - Online and operational
- `inactive` - Offline
- `maintenance` - Under maintenance
- `error` - In error state
- `decommissioned` - Removed from service

## Notes

- **Authentication**: Most endpoints require a valid JWT token
- **Device Secrets**: Stored in auth service, shown only once during registration
- **Smart Frames**: Special device type with additional display/sync operations
- **Commands**: Sent via MQTT (or simulated if MQTT not available)
- **Health Monitoring**: Real-time device health metrics

## Troubleshooting

### Services Not Running
```bash
# Check service status
curl http://localhost:8220/health  # Device service
curl http://localhost:8201/health  # Auth service
```

### Authentication Errors
- Ensure you're using a valid token from auth service
- Tokens expire (default: 3600 seconds)
- Generate new token if expired

### Device Not Found
- Verify device was successfully registered
- Check device_id is correct
- Ensure proper authentication/authorization

## Related Documentation

- [Device Service Tests](../tests/) - Test scripts for validation
- [Device Service Docs](../docs/) - API documentation
- [Auth Service Examples](../../auth_service/examples/) - Auth examples
