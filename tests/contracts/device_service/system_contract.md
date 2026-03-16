# Device Service - System Contract (Layer 6)

## Overview

This document defines HOW device_service implements the 12 standard system patterns.

**Service**: device_service
**Port**: 8220
**Category**: User Microservice (IoT)
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/device_service/
├── __init__.py
├── main.py                 # FastAPI app, routes, DI setup, lifespan
├── device_service.py       # Business logic layer
├── device_repository.py    # Data access layer
├── models.py               # Pydantic models (DeviceResponse, etc.)
├── protocols.py            # DI interfaces (Protocol classes)
├── factory.py              # DI factory (create_device_service)
├── routes_registry.py      # Consul route metadata
├── client.py               # HTTP client for inter-service calls
├── clients/                # Service client implementations
├── events.py               # Legacy events (deprecated)
└── events/
    ├── __init__.py
    ├── models.py
    ├── handlers.py
    └── publishers.py
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| MQTT | Native | Device command delivery | mqtt broker |
| auth_service | HTTP | Device authentication | localhost:8201 |
| organization_service | HTTP | Family sharing permissions | localhost:8212 |
| telemetry_service | HTTP | Device telemetry | via service discovery |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class DeviceNotFoundError(Exception): ...
class DeviceAlreadyExistsError(Exception): ...
class DeviceGroupNotFoundError(Exception): ...

@runtime_checkable
class DeviceRepositoryProtocol(Protocol):
    async def create_device(self, device_data: Dict[str, Any]) -> Optional[DeviceResponse]: ...
    async def get_device_by_id(self, device_id: str) -> Optional[DeviceResponse]: ...
    async def list_user_devices(self, user_id: str, ...) -> List[DeviceResponse]: ...
    async def update_device(self, device_id: str, update_data: Dict[str, Any]) -> bool: ...
    async def update_device_status(self, device_id: str, status: DeviceStatus, last_seen: datetime) -> bool: ...
    async def delete_device(self, device_id: str) -> bool: ...
    async def create_device_group(self, group_data: Dict[str, Any]) -> Optional[DeviceGroupResponse]: ...
    async def create_device_command(self, command_data: Dict[str, Any]) -> bool: ...
    async def check_connection(self) -> bool: ...

@runtime_checkable
class EventBusProtocol(Protocol): ...
class TelemetryClientProtocol(Protocol): ...
class MQTTCommandClientProtocol(Protocol): ...
```

### Factory Implementation (`factory.py`)

```python
def create_device_service(config=None, event_bus=None) -> DeviceService:
    from .device_repository import DeviceRepository
    repository = DeviceRepository(config=config)
    return DeviceService(repository=repository, event_bus=event_bus, mqtt_client=None)
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Trigger |
|-------|---------|
| `device.registered` | New device registered |
| `device.paired` | Device paired with user |
| `device.status_changed` | Device status updated |
| `device.decommissioned` | Device decommissioned |

### Subscribed Events

```python
await microservice.event_bus.subscribe(pattern="events.firmware.uploaded", handler=...)
await microservice.event_bus.subscribe(pattern="events.update.completed", handler=...)
await microservice.event_bus.subscribe(pattern="events.telemetry.data.received", handler=...)
```

---

## 4. Error Handling Pattern

No global exception-to-status mapping; errors handled per-endpoint with try/except blocks returning appropriate HTTP status codes (400, 401, 403, 404, 500, 503).

---

## 5. Client Pattern

Uses `AuthServiceClient` (async context manager) for device authentication token verification. Uses `OrganizationServiceClient` for family sharing permissions.

---

## 6. Repository Pattern

Standard AsyncPostgresClient via gRPC with device CRUD, group management, and command tracking.

---

## 7. Service Registration Pattern (Consul)

```python
SERVICE_METADATA = {
    "service_name": "device_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "device", "iot"],
    "capabilities": [
        "device_registration", "device_authentication", "device_lifecycle",
        "device_commands", "device_groups", "bulk_operations",
        "frame_management", "telemetry_integration", "firmware_updates"
    ]
}
```

22 routes: health (3), device CRUD (5), auth (1), commands (1), groups (3), bulk (2), frames (4), stats (2), debug (1).

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/health` | No | Basic health check |
| `/api/v1/devices/health` | No | API-versioned health check |
| `/health/detailed` | No | Detailed component health |

---

## 9-12. Event System, Configuration, Logging, Deployment

- NATS events for firmware, telemetry, and update lifecycle
- ConfigManager("device_service") with port 8220
- `setup_service_logger("device_service")`
- DeviceMicroservice class encapsulates service + event_bus + consul_registry lifecycle
- GracefulShutdown with signal handlers
- Smart frame endpoints leverage existing device infrastructure with additional permission checks

---

## System Contract Checklist

- [x] `protocols.py` defines Device, EventBus, Telemetry, MQTT protocols
- [x] `factory.py` creates service with repository and optional MQTT
- [x] DeviceMicroservice class pattern (not global variables)
- [x] Auth via AuthServiceClient (async context manager)
- [x] Smart frame endpoints (display, sync, config) on top of device infrastructure
- [x] Device pairing flow (QR code based)
- [x] Consul TTL registration with 22 routes and 9 capabilities

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/device_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/device_service/device_service.py` | Business logic |
| `microservices/device_service/device_repository.py` | Data access |
| `microservices/device_service/protocols.py` | DI interfaces |
| `microservices/device_service/factory.py` | DI factory |
| `microservices/device_service/routes_registry.py` | Consul metadata |
| `microservices/device_service/events/` | Event handlers, models, publishers |
