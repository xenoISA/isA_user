# OTA Service System Contract

This document defines HOW the OTA Service implements the 12 standard microservice patterns. It bridges the Logic Contract (business rules) to actual code implementation.

---

## Table of Contents

1. [Architecture Pattern](#1-architecture-pattern)
2. [Dependency Injection Pattern](#2-dependency-injection-pattern)
3. [Event Publishing Pattern](#3-event-publishing-pattern)
4. [Error Handling Pattern](#4-error-handling-pattern)
5. [Client Pattern (Sync Communication)](#5-client-pattern-sync-communication)
6. [Repository Pattern (Database Access)](#6-repository-pattern-database-access)
7. [Service Registration Pattern (Consul)](#7-service-registration-pattern-consul)
8. [Migration Pattern (Database Schema)](#8-migration-pattern-database-schema)
9. [Lifecycle Pattern (main.py Setup)](#9-lifecycle-pattern-mainpy-setup)
10. [Configuration Pattern (ConfigManager)](#10-configuration-pattern-configmanager)
11. [Logging Pattern](#11-logging-pattern)
12. [Event Subscription Pattern (Async Communication)](#12-event-subscription-pattern-async-communication)

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/ota_service/
├── __init__.py
├── main.py                    # FastAPI app, routes, DI setup, lifespan
├── ota_service.py             # Business logic layer
├── ota_repository.py          # Data access layer (PostgreSQL gRPC)
├── models.py                  # Pydantic request/response models
├── routes_registry.py         # Consul route metadata
├── clients/
│   ├── __init__.py            # Client exports
│   ├── device_client.py       # Device Service client
│   ├── storage_client.py      # Storage Service client (MinIO)
│   └── notification_client.py # Notification Service client
└── events/
    ├── __init__.py            # Event exports
    ├── models.py              # Event Pydantic models
    ├── publishers.py          # Event publishing functions
    └── handlers.py            # Event subscription handlers
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, request validation, auth | FastAPI, OTAService |
| **Service** | `ota_service.py` | Business logic, orchestration | Repository, EventBus, Clients |
| **Repository** | `ota_repository.py` | Data access, SQL queries | PostgreSQL gRPC |
| **Clients** | `clients/*.py` | External service HTTP calls | httpx, ConfigManager |
| **Events** | `events/*.py` | Event publishing/subscription | NATS |

### Data Flow

```
HTTP Request
     ↓
[main.py] FastAPI Routes
     ↓ (validates request, extracts user context)
[ota_service.py] Business Logic
     ↓ (applies business rules)
     ├──→ [ota_repository.py] Database Operations
     ├──→ [clients/] External Service Calls
     └──→ [events/publishers.py] Event Publishing
     ↓
HTTP Response
```

---

## 2. Dependency Injection Pattern

### Current Implementation

The OTA Service uses constructor injection for dependencies:

```python
# ota_service.py
class OTAService:
    def __init__(
        self,
        event_bus=None,
        config=None,
        device_client: Optional[DeviceClient] = None,
        storage_client: Optional[StorageClient] = None,
        notification_client: Optional[NotificationClient] = None
    ):
        self.repository = OTARepository(config=config)
        self.device_client = device_client
        self.storage_client = storage_client
        self.notification_client = notification_client
        self.event_bus = event_bus
```

### Microservice Class Pattern

```python
# main.py
class OTAMicroservice:
    def __init__(self):
        self.service = None
        self.event_bus = None

    async def initialize(
        self,
        event_bus=None,
        config=None,
        device_client=None,
        storage_client=None,
        notification_client=None
    ):
        self.event_bus = event_bus
        self.service = OTAService(
            event_bus=event_bus,
            config=config,
            device_client=device_client,
            storage_client=storage_client,
            notification_client=notification_client
        )

    async def shutdown(self):
        if self.event_bus:
            await self.event_bus.close()
```

### Dependency Injection for Routes

```python
# main.py - Route dependency
def get_service() -> OTAService:
    """Get service instance for route handlers"""
    if not microservice.service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    return microservice.service

# Usage in routes
@app.post("/api/v1/ota/firmware", response_model=FirmwareResponse)
async def upload_firmware(
    metadata: str = Body(...),
    file: UploadFile = File(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    # microservice.service is used directly
    firmware = await microservice.service.upload_firmware(...)
```

### Future Enhancement: Protocol-Based DI

To improve testability, define protocols in `protocols.py`:

```python
# protocols.py (to be created)
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List

@runtime_checkable
class OTARepositoryProtocol(Protocol):
    """Repository interface for OTA data access"""

    async def create_firmware(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    async def get_firmware_by_id(self, firmware_id: str) -> Optional[Dict[str, Any]]: ...
    async def create_campaign(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    async def create_device_update(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...


@runtime_checkable
class DeviceClientProtocol(Protocol):
    """Device service client interface"""

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_device_firmware_version(self, device_id: str) -> Optional[str]: ...
    async def check_firmware_compatibility(self, device_id: str, model: str, min_version: str) -> bool: ...


@runtime_checkable
class StorageClientProtocol(Protocol):
    """Storage service client interface"""

    async def upload_firmware(self, firmware_id: str, content: bytes, filename: str, user_id: str, metadata: Dict) -> Dict[str, Any]: ...
```

---

## 3. Event Publishing Pattern

### Event Types

The OTA Service publishes the following events:

| Event Type | Subject | Trigger |
|------------|---------|---------|
| `FIRMWARE_UPLOADED` | `ota.firmware.uploaded` | After firmware upload success |
| `CAMPAIGN_CREATED` | `ota.campaign.created` | After campaign creation |
| `CAMPAIGN_STARTED` | `ota.campaign.started` | After campaign start |
| `UPDATE_CANCELLED` | `ota.update.cancelled` | After update cancellation |
| `ROLLBACK_INITIATED` | `ota.rollback.initiated` | After rollback initiation |

### Event Models

```python
# events/models.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FirmwareUploadedEvent(BaseModel):
    """Event published when firmware is uploaded"""
    firmware_id: str
    name: str
    version: str
    device_model: str
    file_size: int
    is_security_update: bool
    uploaded_by: str
    timestamp: str

class CampaignCreatedEvent(BaseModel):
    """Event published when campaign is created"""
    campaign_id: str
    name: str
    firmware_id: str
    firmware_version: str
    target_device_count: int
    deployment_strategy: str
    priority: str
    created_by: str
    timestamp: str

class CampaignStartedEvent(BaseModel):
    """Event published when campaign starts"""
    campaign_id: str
    name: str
    firmware_id: str
    firmware_version: str
    target_device_count: int
    timestamp: str

class UpdateCancelledEvent(BaseModel):
    """Event published when update is cancelled"""
    update_id: str
    device_id: str
    firmware_id: str
    firmware_version: str
    campaign_id: Optional[str]
    timestamp: str

class RollbackInitiatedEvent(BaseModel):
    """Event published when rollback starts"""
    rollback_id: str
    device_id: str
    from_version: str
    to_version: str
    trigger: str
    timestamp: str
```

### Event Publishing Functions

```python
# events/publishers.py
from core.nats_client import Event, EventType, ServiceSource

async def publish_firmware_uploaded(
    event_bus,
    firmware_id: str,
    name: str,
    version: str,
    device_model: str,
    file_size: int,
    is_security_update: bool,
    uploaded_by: str
) -> bool:
    """Publish firmware.uploaded event"""
    try:
        event_data = FirmwareUploadedEvent(
            firmware_id=firmware_id,
            name=name,
            version=version,
            device_model=device_model,
            file_size=file_size,
            is_security_update=is_security_update,
            uploaded_by=uploaded_by,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.FIRMWARE_UPLOADED,
            source=ServiceSource.OTA_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        return True
    except Exception as e:
        logger.error(f"Failed to publish firmware.uploaded event: {e}")
        return False
```

### Event Publishing in Service Layer

```python
# ota_service.py - Publishing pattern
async def upload_firmware(self, user_id: str, firmware_data: Dict, file_content: bytes):
    # 1. Business logic and database operations
    db_result = await self.repository.create_firmware(firmware_db_data)

    # 2. Publish event after successful operation
    if self.event_bus:
        try:
            await publish_firmware_uploaded(
                event_bus=self.event_bus,
                firmware_id=firmware_id,
                name=firmware.name,
                version=firmware.version,
                device_model=firmware.device_model,
                file_size=firmware.file_size,
                is_security_update=firmware.is_security_update,
                uploaded_by=user_id
            )
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            # Do NOT rollback - eventual consistency pattern

    return firmware
```

---

## 4. Error Handling Pattern

### Exception Handling in Routes

```python
# main.py - Route error handling
@app.post("/api/v1/ota/devices/{device_id}/update", response_model=DeviceUpdateResponse)
async def update_device(
    device_id: str = Path(...),
    request: DeviceUpdateRequest = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    try:
        device_update = await microservice.service.update_single_device(
            device_id,
            request.model_dump()
        )
        if device_update:
            return device_update
        raise HTTPException(status_code=400, detail="Failed to start device update")
    except ValueError as ve:
        # Validation errors (device not found, firmware incompatible)
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating device: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### HTTP Status Mapping

| Exception Type | HTTP Status | Use Case |
|---------------|-------------|----------|
| `ValueError` | 404 or 422 | Validation failures, not found |
| `HTTPException` | As specified | Explicit HTTP errors |
| `json.JSONDecodeError` | 400 | Invalid JSON input |
| `requests.RequestException` | 503 | Auth service unavailable |
| Generic `Exception` | 500 | Internal server errors |

### Error Response Format

```json
{
  "detail": "Error message describing the issue"
}
```

### Logging Pattern for Errors

```python
# Error logging with context
logger.error(f"Error uploading firmware: {e}")
logger.warning(f"Validation error: {ve}")
logger.error(f"Auth service communication error: {e}")
```

---

## 5. Client Pattern (Sync Communication)

### Service Clients

The OTA Service communicates with three external services:

| Client | Target Service | Purpose |
|--------|---------------|---------|
| `DeviceClient` | device_service | Device validation, firmware compatibility |
| `StorageClient` | storage_service | Firmware binary storage (MinIO) |
| `NotificationClient` | notification_service | Campaign notifications |

### Client Implementation Pattern

```python
# clients/device_client.py
class DeviceClient:
    """Async client for device_service"""

    def __init__(self, config: Optional[ConfigManager] = None):
        self._config = config or ConfigManager("ota_service")
        self._client: Optional[httpx.AsyncClient] = None

        # Service discovery
        host, port = self._config.discover_service(
            service_name='device_service',
            default_host='localhost',
            default_port=8204,
            env_host_key='DEVICE_SERVICE_HOST',
            env_port_key='DEVICE_SERVICE_PORT'
        )
        self._base_url = f"http://{host}:{port}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
                headers={"X-Internal-Call": "true"}
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by ID"""
        client = await self._get_client()
        response = await client.get(f"/api/v1/devices/{device_id}")

        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def get_device_firmware_version(self, device_id: str) -> Optional[str]:
        """Get current firmware version for device"""
        device = await self.get_device(device_id)
        if device:
            return device.get("firmware_version")
        return None

    async def check_firmware_compatibility(
        self,
        device_id: str,
        device_model: str,
        min_hardware_version: Optional[str]
    ) -> bool:
        """Check if firmware is compatible with device"""
        device = await self.get_device(device_id)
        if not device:
            return False

        # Check model compatibility
        if device.get("device_model") != device_model:
            return False

        # Check hardware version if specified
        if min_hardware_version:
            device_hw = device.get("hardware_version", "0.0.0")
            # Version comparison logic
            return self._version_gte(device_hw, min_hardware_version)

        return True
```

### Client Usage in Service

```python
# ota_service.py
async def update_single_device(self, device_id: str, update_data: Dict) -> Optional[DeviceUpdateResponse]:
    # Validate device exists via Device Service
    if self.device_client:
        try:
            device = await self.device_client.get_device(device_id)
            if not device:
                raise ValueError(f"Device '{device_id}' not found")

            # Get current firmware version
            from_version = await self.device_client.get_device_firmware_version(device_id)

            # Check compatibility
            is_compatible = await self.device_client.check_firmware_compatibility(
                device_id,
                firmware.device_model,
                firmware.min_hardware_version
            )
            if not is_compatible:
                logger.warning(f"Firmware may not be compatible with device {device_id}")

        except Exception as e:
            logger.error(f"Device Service validation failed: {e}")
            # Graceful degradation - proceed without validation
            logger.warning("Proceeding without device validation")
```

### Client Initialization in Lifespan

```python
# main.py - lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    global device_client, storage_client, notification_client

    # Initialize clients
    try:
        from .clients import DeviceClient, StorageClient, NotificationClient

        device_client = DeviceClient(config=config_manager)
        storage_client = StorageClient(config=config_manager)
        notification_client = NotificationClient(config=config_manager)

        logger.info("Service clients initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize service clients: {e}")
        device_client = None
        storage_client = None
        notification_client = None

    # ... rest of initialization

    yield

    # Shutdown - close clients
    if device_client:
        await device_client.close()
    if storage_client:
        await storage_client.close()
    if notification_client:
        await notification_client.close()
```

---

## 6. Repository Pattern (Database Access)

### Repository Configuration

```python
# ota_repository.py
class OTARepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("ota_service")

        # Discover PostgreSQL service
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        self.db = AsyncPostgresClient(host=host, port=port, user_id="ota_service")
        self.schema = "ota"
        self.firmware_table = "firmware"
        self.campaigns_table = "update_campaigns"
        self.device_updates_table = "device_updates"
        self.downloads_table = "firmware_downloads"
        self.rollback_table = "rollback_logs"
```

### CRUD Operations

```python
# Create operation
async def create_firmware(self, firmware_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        now = datetime.now(timezone.utc)

        query = f'''
            INSERT INTO {self.schema}.{self.firmware_table} (
                firmware_id, name, version, description, device_model, ...
            ) VALUES ($1, $2, $3, $4, $5, ...)
            RETURNING *
        '''

        params = [firmware_data["firmware_id"], firmware_data["name"], ...]

        async with self.db:
            results = await self.db.query(query, params, schema=self.schema)

        return results[0] if results else None
    except Exception as e:
        logger.error(f"Error creating firmware: {e}")
        raise

# Read operation
async def get_firmware_by_id(self, firmware_id: str) -> Optional[Dict[str, Any]]:
    try:
        query = f'SELECT * FROM {self.schema}.{self.firmware_table} WHERE firmware_id = $1 LIMIT 1'

        async with self.db:
            results = await self.db.query(query, [firmware_id], schema=self.schema)

        return results[0] if results else None
    except Exception as e:
        logger.error(f"Error getting firmware: {e}")
        return None

# List operation with filters
async def list_firmware(
    self,
    device_model: Optional[str] = None,
    manufacturer: Optional[str] = None,
    is_beta: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    try:
        conditions = []
        params = []
        param_count = 0

        if device_model:
            param_count += 1
            conditions.append(f"device_model = ${param_count}")
            params.append(device_model)

        # ... more filters

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f'''
            SELECT * FROM {self.schema}.{self.firmware_table}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
        '''

        async with self.db:
            results = await self.db.query(query, params, schema=self.schema)

        return results if results else []
    except Exception as e:
        logger.error(f"Error listing firmware: {e}")
        return []

# Update operation
async def update_firmware_stats(self, firmware_id: str, download_count_delta: int = 0) -> bool:
    try:
        now = datetime.now(timezone.utc)

        query = f'''
            UPDATE {self.schema}.{self.firmware_table}
            SET download_count = download_count + $1, updated_at = $2
            WHERE firmware_id = $3
        '''

        async with self.db:
            count = await self.db.execute(query, [download_count_delta, now, firmware_id], schema=self.schema)

        return count > 0
    except Exception as e:
        logger.error(f"Error updating firmware stats: {e}")
        return False
```

### Timestamp Management

All repository operations manage timestamps automatically:

```python
# On create
now = datetime.now(timezone.utc)
data["created_at"] = now
data["updated_at"] = now

# On update
data["updated_at"] = datetime.now(timezone.utc)
```

---

## 7. Service Registration Pattern (Consul)

### Routes Registry

```python
# routes_registry.py
SERVICE_ROUTES = [
    # Health endpoints
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Basic health check"},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False, "description": "Detailed health check"},

    # Firmware Management
    {"path": "/api/v1/firmware", "methods": ["POST", "GET"], "auth_required": True, "description": "Create/list firmware"},
    {"path": "/api/v1/firmware/{firmware_id}", "methods": ["GET", "DELETE"], "auth_required": True, "description": "Get/delete firmware"},
    {"path": "/api/v1/firmware/{firmware_id}/download", "methods": ["GET"], "auth_required": True, "description": "Download firmware"},

    # Update Campaigns
    {"path": "/api/v1/campaigns", "methods": ["POST", "GET"], "auth_required": True, "description": "Create/list campaigns"},
    {"path": "/api/v1/campaigns/{campaign_id}", "methods": ["GET"], "auth_required": True, "description": "Get campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/start", "methods": ["POST"], "auth_required": True, "description": "Start campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/pause", "methods": ["POST"], "auth_required": True, "description": "Pause campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/cancel", "methods": ["POST"], "auth_required": True, "description": "Cancel campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/approve", "methods": ["POST"], "auth_required": True, "description": "Approve campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/rollback", "methods": ["POST"], "auth_required": True, "description": "Rollback campaign"},

    # Device Updates
    {"path": "/api/v1/devices/{device_id}/update", "methods": ["POST"], "auth_required": True, "description": "Update device"},
    {"path": "/api/v1/devices/{device_id}/updates", "methods": ["GET"], "auth_required": True, "description": "Device update history"},
    {"path": "/api/v1/devices/{device_id}/rollback", "methods": ["POST"], "auth_required": True, "description": "Rollback device"},
    {"path": "/api/v1/devices/bulk/update", "methods": ["POST"], "auth_required": True, "description": "Bulk update"},

    # Update Management
    {"path": "/api/v1/updates/{update_id}", "methods": ["GET"], "auth_required": True, "description": "Get update"},
    {"path": "/api/v1/updates/{update_id}/cancel", "methods": ["POST"], "auth_required": True, "description": "Cancel update"},
    {"path": "/api/v1/updates/{update_id}/retry", "methods": ["POST"], "auth_required": True, "description": "Retry update"},

    # Statistics
    {"path": "/api/v1/stats", "methods": ["GET"], "auth_required": True, "description": "Update statistics"},
    {"path": "/api/v1/stats/campaigns/{campaign_id}", "methods": ["GET"], "auth_required": True, "description": "Campaign stats"},
    {"path": "/api/v1/service/stats", "methods": ["GET"], "auth_required": True, "description": "Service stats"},
]

SERVICE_METADATA = {
    "service_name": "ota_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "ota", "firmware"],
    "capabilities": [
        "firmware_management",
        "update_campaigns",
        "device_updates",
        "rollback_management",
        "update_statistics"
    ]
}
```

### Consul Registration in Lifespan

```python
# main.py
if config.consul_enabled:
    try:
        route_meta = get_routes_for_consul()

        consul_meta = {
            'version': SERVICE_METADATA['version'],
            'capabilities': ','.join(SERVICE_METADATA['capabilities']),
            **route_meta
        }

        consul_registry = ConsulRegistry(
            service_name=SERVICE_METADATA['service_name'],
            service_port=config.service_port,
            consul_host=config.consul_host,
            consul_port=config.consul_port,
            tags=SERVICE_METADATA['tags'],
            meta=consul_meta,
            health_check_type='http'
        )
        consul_registry.register()
        logger.info(f"Service registered with Consul: {route_meta.get('route_count')} routes")
    except Exception as e:
        logger.warning(f"Failed to register with Consul: {e}")
```

---

## 8. Migration Pattern (Database Schema)

### Migration File Structure

```
microservices/ota_service/migrations/
├── 001_create_ota_schema.sql           # Schema creation
├── 002_create_firmware_table.sql       # Firmware table
├── 003_create_campaigns_table.sql      # Campaigns table
├── 004_create_device_updates_table.sql # Device updates table
├── 005_create_rollback_logs_table.sql  # Rollback logs table
└── 006_create_indexes.sql              # Performance indexes
```

### Schema Definition

```sql
-- 001_create_ota_schema.sql
CREATE SCHEMA IF NOT EXISTS ota;

-- 002_create_firmware_table.sql
CREATE TABLE IF NOT EXISTS ota.firmware (
    firmware_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    device_model VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    min_hardware_version VARCHAR(50),
    max_hardware_version VARCHAR(50),
    file_size BIGINT NOT NULL,
    file_url TEXT NOT NULL,
    checksum_md5 VARCHAR(32) NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_beta BOOLEAN DEFAULT FALSE,
    is_security_update BOOLEAN DEFAULT FALSE,
    changelog TEXT,
    download_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 003_create_campaigns_table.sql
CREATE TABLE IF NOT EXISTS ota.update_campaigns (
    campaign_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    firmware_id VARCHAR(255) NOT NULL REFERENCES ota.firmware(firmware_id),
    status VARCHAR(50) DEFAULT 'created',
    deployment_strategy VARCHAR(50) DEFAULT 'staged',
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    target_devices JSONB DEFAULT '[]'::jsonb,
    target_criteria JSONB DEFAULT '{}'::jsonb,
    rollout_percentage INTEGER DEFAULT 100,
    auto_rollback BOOLEAN DEFAULT TRUE,
    rollback_threshold DECIMAL(5,2) DEFAULT 10.00,
    force_update BOOLEAN DEFAULT FALSE,
    priority VARCHAR(20) DEFAULT 'normal',
    pending_devices INTEGER DEFAULT 0,
    in_progress_devices INTEGER DEFAULT 0,
    completed_devices INTEGER DEFAULT 0,
    failed_devices INTEGER DEFAULT 0,
    cancelled_devices INTEGER DEFAULT 0,
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 004_create_device_updates_table.sql
CREATE TABLE IF NOT EXISTS ota.device_updates (
    update_id VARCHAR(255) PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    campaign_id VARCHAR(255) NOT NULL,
    firmware_id VARCHAR(255) NOT NULL REFERENCES ota.firmware(firmware_id),
    status VARCHAR(50) DEFAULT 'pending',
    progress DECIMAL(5,2) DEFAULT 0.00,
    error_message TEXT,
    error_code VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 005_create_rollback_logs_table.sql
CREATE TABLE IF NOT EXISTS ota.rollback_logs (
    rollback_id VARCHAR(255) PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    campaign_id VARCHAR(255),
    from_firmware_id VARCHAR(255) NOT NULL,
    to_firmware_id VARCHAR(255) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    triggered_by VARCHAR(255) NOT NULL,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 006_create_indexes.sql
CREATE INDEX IF NOT EXISTS idx_firmware_device_model ON ota.firmware(device_model);
CREATE INDEX IF NOT EXISTS idx_firmware_version ON ota.firmware(version);
CREATE INDEX IF NOT EXISTS idx_firmware_created_at ON ota.firmware(created_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON ota.update_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_firmware_id ON ota.update_campaigns(firmware_id);
CREATE INDEX IF NOT EXISTS idx_device_updates_device_id ON ota.device_updates(device_id);
CREATE INDEX IF NOT EXISTS idx_device_updates_campaign_id ON ota.device_updates(campaign_id);
CREATE INDEX IF NOT EXISTS idx_device_updates_status ON ota.device_updates(status);
CREATE INDEX IF NOT EXISTS idx_rollback_device_id ON ota.rollback_logs(device_id);
```

---

## 9. Lifecycle Pattern (main.py Setup)

### Lifespan Context Manager

```python
# main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global device_client, storage_client, notification_client
    consul_registry = None

    # ====== STARTUP ======

    # 1. Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("ota_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")
        event_bus = None

    # 2. Initialize service clients
    try:
        from .clients import DeviceClient, StorageClient, NotificationClient
        device_client = DeviceClient(config=config_manager)
        storage_client = StorageClient(config=config_manager)
        notification_client = NotificationClient(config=config_manager)
        logger.info("Service clients initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize service clients: {e}")

    # 3. Initialize microservice
    await microservice.initialize(
        event_bus=event_bus,
        config=config_manager,
        device_client=device_client,
        storage_client=storage_client,
        notification_client=notification_client
    )

    # 4. Set up event subscriptions
    if event_bus:
        try:
            ota_repo = OTARepository(config=config_manager)
            handler_map = get_event_handlers(ota_repo)

            for event_pattern, handler_func in handler_map.items():
                await event_bus.subscribe_to_events(
                    pattern=event_pattern, handler=handler_func
                )
                logger.info(f"Subscribed to {event_pattern} events")
        except Exception as e:
            logger.warning(f"Failed to set up event subscriptions: {e}")

    # 5. Consul service registration
    if config.consul_enabled:
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                'version': SERVICE_METADATA['version'],
                'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                **route_meta
            }
            consul_registry = ConsulRegistry(...)
            consul_registry.register()
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")

    logger.info(f"OTA Service started on port {config.service_port}")

    yield  # Application runs here

    # ====== SHUTDOWN ======

    try:
        # 1. Deregister from Consul
        if consul_registry:
            consul_registry.deregister()

        # 2. Close service clients
        if device_client:
            await device_client.close()
        if storage_client:
            await storage_client.close()
        if notification_client:
            await notification_client.close()

        # 3. Close event bus
        if event_bus:
            await event_bus.close()

        # 4. Shutdown microservice
        await microservice.shutdown()
        logger.info("OTA Service shutting down...")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
```

### FastAPI Application Setup

```python
# Create FastAPI app
app = FastAPI(
    title="OTA Service",
    description="IoT OTA更新微服务 - 固件管理和设备更新",
    version="1.0.0",
    lifespan=lifespan
)
```

---

## 10. Configuration Pattern (ConfigManager)

### Configuration Initialization

```python
# main.py
from core.config_manager import ConfigManager

# Initialize at module level
config_manager = ConfigManager("ota_service")
config = config_manager.get_service_config()
```

### Available Configuration Properties

| Property | Default | Environment Variable | Description |
|----------|---------|---------------------|-------------|
| `service_name` | `"ota_service"` | - | Service identifier |
| `service_port` | `8220` | `OTA_SERVICE_PORT` | HTTP port |
| `service_host` | `"0.0.0.0"` | `OTA_SERVICE_HOST` | Bind address |
| `debug` | `False` | `DEBUG` | Debug mode |
| `log_level` | `"INFO"` | `LOG_LEVEL` | Logging level |
| `consul_enabled` | `True` | `CONSUL_ENABLED` | Consul registration |
| `consul_host` | `"consul"` | `CONSUL_HOST` | Consul host |
| `consul_port` | `8500` | `CONSUL_PORT` | Consul port |
| `nats_url` | `"nats://nats:4222"` | `NATS_URL` | NATS connection |

### Service Discovery Pattern

```python
# Using ConfigManager for service discovery
host, port = config_manager.discover_service(
    service_name='device_service',
    default_host='localhost',
    default_port=8204,
    env_host_key='DEVICE_SERVICE_HOST',
    env_port_key='DEVICE_SERVICE_PORT'
)
```

### OTA Service Port: 8220

---

## 11. Logging Pattern

### Logger Setup

```python
# main.py
from core.logger import setup_service_logger

# Setup at module level
app_logger = setup_service_logger("ota_service")
logger = app_logger  # for backward compatibility
```

### Logging Patterns

```python
# Info - successful operations
logger.info(f"Firmware uploaded successfully: {firmware_id}")
logger.info(f"Campaign created: {campaign_id}")
logger.info(f"Device update created: {update_id}")

# Warning - degraded operations
logger.warning(f"Failed to initialize event bus: {e}")
logger.warning(f"Storage service error: {error}, continuing with local storage")
logger.warning(f"Proceeding with update without device validation")

# Error - failed operations
logger.error(f"Error uploading firmware: {e}")
logger.error(f"Failed to publish event: {e}")
logger.error(f"Database connection check failed: {e}")

# Startup/shutdown messages with emojis
logger.info("✅ Event bus initialized successfully")
logger.info("✅ Service clients initialized successfully")
logger.info("✅ Service registered with Consul")
logger.warning("⚠️  Failed to initialize event bus")
logger.error("❌ Failed to close device client: {e}")
```

### Structured Logging

```python
# Include context in log messages
logger.info(f"Created firmware: {firmware_data['firmware_id']}")
logger.info(f"Campaign {campaign_id} targets {target_device_count} devices")
logger.error(f"Error getting firmware {firmware_id}: {e}")
```

---

## 12. Event Subscription Pattern (Async Communication)

### Event Handlers

```python
# events/handlers.py
async def handle_device_deleted(event_data: Dict[str, Any], ota_repository):
    """
    Handle device.deleted event from device_service

    When a device is deleted, cancel all pending updates for that device
    """
    try:
        device_id = event_data.get('device_id')
        if not device_id:
            logger.warning("device.deleted event missing device_id")
            return

        logger.info(f"Received device.deleted event for device {device_id}")

        # Cancel all pending/in-progress updates for this device
        cancelled_count = await ota_repository.cancel_device_updates(device_id)

        logger.info(f"Cancelled {cancelled_count} OTA updates for deleted device {device_id}")

    except Exception as e:
        logger.error(f"Error handling device.deleted event: {e}", exc_info=True)


async def handle_user_deleted(event_data: Dict[str, Any], ota_repository):
    """
    Handle user.deleted event from account_service

    When a user is deleted, cancel all pending updates for all their devices
    """
    try:
        user_id = event_data.get('user_id')
        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Received user.deleted event for user {user_id}")

        # Cancel all pending OTA updates for all user's devices
        cancelled_count = await ota_repository.cancel_user_updates(user_id)

        # Clean up user's firmware preferences if any
        await ota_repository.delete_user_firmware_preferences(user_id)

        logger.info(f"Cancelled {cancelled_count} OTA updates for deleted user {user_id}")

    except Exception as e:
        logger.error(f"Error handling user.deleted event: {e}", exc_info=True)
```

### Event Handler Registry

```python
# events/handlers.py
def get_event_handlers(ota_repository) -> Dict[str, callable]:
    """
    Return a mapping of event patterns to handler functions
    """
    return {
        "device_service.device.deleted": lambda event: handle_device_deleted(event.data, ota_repository),
        "account_service.user.deleted": lambda event: handle_user_deleted(event.data, ota_repository),
    }
```

### Event Subscription in Lifespan

```python
# main.py - lifespan
if event_bus:
    try:
        ota_repo = OTARepository(config=config_manager)
        handler_map = get_event_handlers(ota_repo)

        for event_pattern, handler_func in handler_map.items():
            await event_bus.subscribe_to_events(
                pattern=event_pattern, handler=handler_func
            )
            logger.info(f"Subscribed to {event_pattern} events")

        logger.info(f"Event handlers registered - Subscribed to {len(handler_map)} event types")
    except Exception as e:
        logger.warning(f"Failed to set up event subscriptions: {e}")
```

### Subscribed Events

| Event Pattern | Source Service | Handler | Action |
|--------------|----------------|---------|--------|
| `device_service.device.deleted` | device_service | `handle_device_deleted` | Cancel pending updates for device |
| `account_service.user.deleted` | account_service | `handle_user_deleted` | Cancel updates for all user's devices |

---

## System Contract Checklist

### Architecture (Section 1)
- [x] Service follows layer structure (main, service, repository, clients, events)
- [x] Clear separation of concerns between layers
- [x] No circular dependencies

### Dependency Injection (Section 2)
- [x] OTAMicroservice class with initialize/shutdown
- [x] Service constructor accepts dependencies
- [ ] `protocols.py` defines all dependency interfaces (future enhancement)
- [ ] `factory.py` creates service with DI (future enhancement)

### Event Publishing (Section 3)
- [x] Event models defined in `events/models.py`
- [x] EventType enum for all event types
- [x] Events published after successful operations
- [x] Error handling for event publishing failures

### Error Handling (Section 4)
- [x] Exception handling in routes
- [x] HTTP status mapping
- [x] Consistent error response format
- [x] Errors logged with context

### Client Pattern - Sync (Section 5)
- [x] Async HTTP clients for dependencies
- [x] X-Internal-Call header for service-to-service
- [x] Service discovery via ConfigManager
- [x] Graceful error handling

### Repository Pattern - DB (Section 6)
- [x] Standard CRUD methods implemented
- [x] Timestamps (created_at, updated_at) managed
- [x] PostgreSQL gRPC client integration
- [x] Parameterized queries for security

### Service Registration - Consul (Section 7)
- [x] `routes_registry.py` defines all routes
- [x] SERVICE_METADATA with version and capabilities
- [x] Consul registration on startup
- [x] Consul deregistration on shutdown

### Migration Pattern - Schema (Section 8)
- [x] Schema definition documented
- [x] Tables for firmware, campaigns, updates, rollbacks
- [x] Indexes for common queries

### Lifecycle Pattern - main.py (Section 9)
- [x] Lifespan context manager
- [x] Event bus initialization
- [x] Service client initialization
- [x] Graceful shutdown

### Configuration Pattern (Section 10)
- [x] ConfigManager usage at module level
- [x] Service port: 8220
- [x] Service discovery for dependencies

### Logging Pattern (Section 11)
- [x] setup_service_logger usage
- [x] Structured logging with context
- [x] Error logging with details

### Event Subscription - Async (Section 12)
- [x] `events/handlers.py` with handler functions
- [x] `get_event_handlers()` returns handler dict
- [x] Handlers registered in lifespan
- [x] Subscribed to: device.deleted, user.deleted

---

This system contract provides comprehensive documentation of how the OTA Service implements all 12 standard microservice patterns. Each pattern is explained with actual code examples from the service implementation.
