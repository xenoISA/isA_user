# Devices

IoT device management, firmware updates, and telemetry.

## Overview

IoT capabilities are handled by three services:

| Service | Port | Purpose |
|---------|------|---------|
| device_service | 8220 | Device registry, lifecycle |
| ota_service | 8221 | Firmware updates, rollback |
| telemetry_service | 8225 | Metrics collection, analytics |

## Device Service (8220)

### Register Device

```bash
curl -X POST "http://localhost:8220/api/v1/devices" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device_abc123",
    "device_type": "smart_speaker",
    "name": "Living Room Speaker",
    "manufacturer": "Acme",
    "model": "Speaker Pro",
    "firmware_version": "1.0.0",
    "metadata": {
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "location": "living_room"
    }
  }'
```

Response:
```json
{
  "device_id": "device_abc123",
  "name": "Living Room Speaker",
  "status": "registered",
  "registered_at": "2024-01-28T10:30:00Z",
  "auth_token": "dev_token_xyz..."
}
```

### Device Authentication

```bash
# Device authenticates itself
curl -X POST "http://localhost:8220/api/v1/devices/auth" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device_abc123",
    "device_secret": "secret_key",
    "firmware_version": "1.0.0"
  }'
```

### Get Device

```bash
curl "http://localhost:8220/api/v1/devices/device_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "device_id": "device_abc123",
  "name": "Living Room Speaker",
  "device_type": "smart_speaker",
  "status": "online",
  "firmware_version": "1.0.0",
  "last_seen": "2024-01-28T10:30:00Z",
  "metadata": {
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "ip_address": "192.168.1.100"
  }
}
```

### List Devices

```bash
curl "http://localhost:8220/api/v1/devices?status=online&type=smart_speaker" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Device

```bash
curl -X PATCH "http://localhost:8220/api/v1/devices/device_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kitchen Speaker",
    "metadata": {
      "location": "kitchen"
    }
  }'
```

### Device Status

| Status | Description |
|--------|-------------|
| `registered` | Device registered, not yet connected |
| `online` | Device connected and active |
| `offline` | Device not responding |
| `updating` | Firmware update in progress |
| `error` | Device in error state |
| `decommissioned` | Device removed from service |

### Decommission Device

```bash
curl -X POST "http://localhost:8220/api/v1/devices/device_abc123/decommission" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## OTA Service (8221)

### Create Firmware Version

```bash
curl -X POST "http://localhost:8221/api/v1/ota/firmware" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/firmware.bin" \
  -F "version=1.1.0" \
  -F "device_type=smart_speaker" \
  -F "release_notes=Bug fixes and performance improvements"
```

### List Firmware Versions

```bash
curl "http://localhost:8221/api/v1/ota/firmware?device_type=smart_speaker" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Check for Updates

```bash
# Device checks for updates
curl "http://localhost:8221/api/v1/ota/check" \
  -H "X-Device-ID: device_abc123" \
  -H "X-Device-Token: dev_token_xyz" \
  -H "X-Firmware-Version: 1.0.0"
```

Response:
```json
{
  "update_available": true,
  "current_version": "1.0.0",
  "latest_version": "1.1.0",
  "download_url": "https://ota.example.com/firmware/1.1.0.bin",
  "checksum": "sha256:abc123...",
  "size": 15728640,
  "release_notes": "Bug fixes and performance improvements",
  "mandatory": false
}
```

### Trigger Update

```bash
curl -X POST "http://localhost:8221/api/v1/ota/devices/device_abc123/update" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_version": "1.1.0",
    "force": false
  }'
```

### Update Status

```bash
curl "http://localhost:8221/api/v1/ota/devices/device_abc123/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "device_id": "device_abc123",
  "update_status": "in_progress",
  "current_version": "1.0.0",
  "target_version": "1.1.0",
  "progress": 65,
  "stage": "installing",
  "started_at": "2024-01-28T10:30:00Z"
}
```

### Rollback Firmware

```bash
curl -X POST "http://localhost:8221/api/v1/ota/devices/device_abc123/rollback" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_version": "1.0.0",
    "reason": "Stability issues with 1.1.0"
  }'
```

### Batch Update

```bash
curl -X POST "http://localhost:8221/api/v1/ota/batch-update" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_type": "smart_speaker",
    "target_version": "1.1.0",
    "rollout_percentage": 10,
    "schedule": "2024-01-29T02:00:00Z"
  }'
```

## Telemetry Service (8225)

### Send Telemetry (Device)

```bash
curl -X POST "http://localhost:8225/api/v1/telemetry" \
  -H "X-Device-ID: device_abc123" \
  -H "X-Device-Token: dev_token_xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2024-01-28T10:30:00Z",
    "metrics": {
      "cpu_usage": 45.2,
      "memory_usage": 62.1,
      "temperature": 42.5,
      "battery_level": 85,
      "wifi_signal": -65
    },
    "events": [
      {
        "type": "button_press",
        "data": {"button": "play"}
      }
    ]
  }'
```

### Get Device Telemetry

```bash
curl "http://localhost:8225/api/v1/telemetry/device_abc123?from=2024-01-27T00:00:00Z&to=2024-01-28T00:00:00Z" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Aggregated Metrics

```bash
curl "http://localhost:8225/api/v1/telemetry/device_abc123/aggregate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": ["cpu_usage", "memory_usage"],
    "aggregation": "avg",
    "interval": "1h",
    "from": "2024-01-27T00:00:00Z",
    "to": "2024-01-28T00:00:00Z"
  }'
```

Response:
```json
{
  "device_id": "device_abc123",
  "aggregations": [
    {
      "timestamp": "2024-01-27T00:00:00Z",
      "cpu_usage_avg": 42.3,
      "memory_usage_avg": 58.7
    },
    {
      "timestamp": "2024-01-27T01:00:00Z",
      "cpu_usage_avg": 38.1,
      "memory_usage_avg": 55.2
    }
  ]
}
```

### Alerts

```bash
# Create alert rule
curl -X POST "http://localhost:8225/api/v1/telemetry/alerts" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High CPU Alert",
    "device_id": "device_abc123",
    "condition": {
      "metric": "cpu_usage",
      "operator": ">",
      "threshold": 90
    },
    "actions": [
      {"type": "notification", "channel": "email"},
      {"type": "webhook", "url": "https://example.com/alert"}
    ]
  }'
```

### Fleet Analytics

```bash
curl "http://localhost:8225/api/v1/telemetry/fleet/analytics" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_type": "smart_speaker",
    "metrics": ["cpu_usage", "memory_usage"],
    "aggregation": "percentile_95",
    "period": "24h"
  }'
```

## MQTT Integration

Devices can also communicate via MQTT:

```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.username_pw_set("device_abc123", "dev_token_xyz")
client.connect("mqtt.example.com", 1883)

# Publish telemetry
client.publish(
    "devices/device_abc123/telemetry",
    json.dumps({"cpu_usage": 45.2})
)

# Subscribe to commands
client.subscribe("devices/device_abc123/commands")
```

## Python SDK

```python
from isa_user import DeviceClient, OTAClient, TelemetryClient

devices = DeviceClient("http://localhost:8220")
ota = OTAClient("http://localhost:8221")
telemetry = TelemetryClient("http://localhost:8225")

# Register device
device = await devices.register(
    token=access_token,
    device_id="device_abc123",
    device_type="smart_speaker",
    name="Living Room Speaker"
)

# Check for updates
update = await ota.check_update(
    device_id="device_abc123",
    current_version="1.0.0"
)

if update.available:
    await ota.trigger_update(
        token=access_token,
        device_id="device_abc123",
        target_version=update.latest_version
    )

# Get telemetry
metrics = await telemetry.get_metrics(
    token=access_token,
    device_id="device_abc123",
    period="24h"
)
```

## Next Steps

- [Memory](./memory) - AI cognitive memory
- [Architecture](./architecture) - Infrastructure details
- [Organizations](./organizations) - Multi-tenant
