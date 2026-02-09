# OTA Service - Design Document

## Design Overview

**Service Name**: ota_service
**Port**: 8216
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-18

### Design Principles
1. **Firmware Lifecycle Management**: Complete management from upload to deployment with versioning
2. **Campaign-Based Deployment**: Orchestrated mass updates with sophisticated deployment strategies
3. **Event-Driven Synchronization**: Loose coupling via NATS events for service coordination
4. **Rollback Protection**: Automatic and manual rollback capabilities for failed updates
5. **ACID Guarantees**: PostgreSQL transactions for data integrity
6. **Graceful Degradation**: Event failures don't block operations

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       External Clients                               │
│   (Admin Dashboard, Mobile App, IoT Devices, Other Services)        │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP REST API
                             │ (via API Gateway - JWT validation)
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     OTA Service (Port 8216)                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)                       │ │
│  │  - Request validation (Pydantic models)                        │ │
│  │  - Response formatting                                         │ │
│  │  - Error handling & exception handlers                         │ │
│  │  - Health checks (/health, /health/detailed)                   │ │
│  │  - Lifecycle management (startup/shutdown)                     │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                              │                                       │
│  ┌───────────────────────────▼────────────────────────────────────┐ │
│  │           Service Layer (ota_service.py)                        │ │
│  │  - Firmware upload and management                               │ │
│  │  - Campaign creation and orchestration                          │ │
│  │  - Device update scheduling and tracking                        │ │
│  │  - Rollback operations                                          │ │
│  │  - Statistics aggregation                                       │ │
│  │  - Event publishing coordination                                │ │
│  │  - Cross-service client calls (Device, Storage)                 │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                              │                                       │
│  ┌───────────────────────────▼────────────────────────────────────┐ │
│  │          Repository Layer (ota_repository.py)                   │ │
│  │  - Database CRUD operations                                     │ │
│  │  - PostgreSQL gRPC communication                                │ │
│  │  - Query construction (parameterized)                           │ │
│  │  - Result parsing (proto to Pydantic)                           │ │
│  │  - No business logic                                            │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                              │                                       │
│  ┌───────────────────────────▼────────────────────────────────────┐ │
│  │          Event Publishing (events/publishers.py)                │ │
│  │  - NATS event bus integration                                   │ │
│  │  - Event model construction                                     │ │
│  │  - Async non-blocking publishing                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   PostgreSQL    │   │      NATS       │   │     Consul      │
│    (gRPC)       │   │   Event Bus     │   │   (Discovery)   │
│                 │   │                 │   │                 │
│  Schema: ota    │   │  Subjects:      │   │  Service:       │
│  Tables:        │   │  firmware.*     │   │  ota_service    │
│  - firmware     │   │  campaign.*     │   │                 │
│  - campaigns    │   │  rollback.*     │   │  Health:        │
│  - updates      │   │                 │   │  /health        │
│  - rollbacks    │   │  Publishers:    │   │                 │
│                 │   │  - uploaded     │   │                 │
│  Indexes:       │   │  - created      │   │                 │
│  - firmware_id  │   │  - started      │   │                 │
│  - campaign_id  │   │  - initiated    │   │                 │
│  - device_id    │   │                 │   │                 │
└─────────────────┘   └─────────────────┘   └─────────────────┘
          │                     │
          │                     │
          ▼                     ▼
┌─────────────────┐   ┌─────────────────────────────────────────┐
│ Storage Service │   │         Event Subscribers                │
│  (Port: 8208)   │   │  - device_service (firmware versions)   │
│                 │   │  - audit_service (logging)              │
│  Purpose:       │   │  - notification_service (alerts)        │
│  Firmware       │   │  - telemetry_service (metrics)          │
│  binary storage │   │                                         │
└─────────────────┘   └─────────────────────────────────────────┘
          │
          ▼
┌─────────────────┐
│ Device Service  │  ← Cross-service call for device validation
│  (Port: 8205)   │
└─────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          OTA Service                                 │
│                                                                      │
│  ┌───────────────┐    ┌───────────────┐    ┌────────────────────┐  │
│  │    Models     │───→│    Service    │───→│    Repository      │  │
│  │   (Pydantic)  │    │  (Business)   │    │     (Data)         │  │
│  │               │    │               │    │                    │  │
│  │ - Firmware    │    │ - OTAService  │    │ - OTARepository    │  │
│  │ - Campaign    │    │               │    │                    │  │
│  │ - DeviceUpdate│    │               │    │                    │  │
│  │ - Rollback    │    │               │    │                    │  │
│  │ - Stats       │    │               │    │                    │  │
│  └───────────────┘    └───────────────┘    └────────────────────┘  │
│         ↑                    ↑                        ↑             │
│         │                    │                        │             │
│  ┌──────┴────────────────────┴────────────────────────┴──────────┐ │
│  │                    FastAPI Main (main.py)                      │ │
│  │  - Dependency Injection (get_ota_service)                     │ │
│  │  - Route Handlers (25+ endpoints)                             │ │
│  │  - Exception Handlers (custom errors)                         │ │
│  └────────────────────────────┬──────────────────────────────────┘ │
│                               │                                     │
│  ┌────────────────────────────▼──────────────────────────────────┐ │
│  │                    Event Publishers                            │ │
│  │           (events/publishers.py, events/models.py)             │ │
│  │  - publish_firmware_uploaded                                   │ │
│  │  - publish_campaign_created                                    │ │
│  │  - publish_campaign_started                                    │ │
│  │  - publish_update_cancelled                                    │ │
│  │  - publish_rollback_initiated                                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     Factory Pattern                             │ │
│  │                (factory.py, protocols.py)                       │ │
│  │  - create_ota_service (production)                             │ │
│  │  - OTAServiceProtocol (interface)                              │ │
│  │  - OTARepositoryProtocol (interface)                           │ │
│  │  - Enables dependency injection for tests                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      Client Layer                               │ │
│  │                   (clients/__init__.py)                         │ │
│  │  - DeviceClient (device validation)                            │ │
│  │  - StorageClient (firmware binary upload)                      │ │
│  │  - NotificationClient (alerts - future)                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (25+ endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                    # Basic health check
GET /health/detailed                           # Database connectivity check

# Firmware Management
POST /api/v1/ota/firmware                      # Upload firmware
GET  /api/v1/ota/firmware/{firmware_id}        # Get firmware details
GET  /api/v1/ota/firmware                      # List firmware with filters
GET  /api/v1/ota/firmware/{firmware_id}/download # Get download URL
DELETE /api/v1/ota/firmware/{firmware_id}      # Delete/deprecate firmware

# Campaign Management
POST /api/v1/ota/campaigns                     # Create update campaign
GET  /api/v1/ota/campaigns/{campaign_id}       # Get campaign details
GET  /api/v1/ota/campaigns                     # List campaigns
POST /api/v1/ota/campaigns/{campaign_id}/start # Start campaign
POST /api/v1/ota/campaigns/{campaign_id}/pause # Pause campaign
POST /api/v1/ota/campaigns/{campaign_id}/resume # Resume campaign
POST /api/v1/ota/campaigns/{campaign_id}/cancel # Cancel campaign
POST /api/v1/ota/campaigns/{campaign_id}/approve # Approve campaign
POST /api/v1/ota/campaigns/{campaign_id}/rollback # Rollback campaign

# Device Updates
POST /api/v1/ota/devices/{device_id}/update    # Update single device
GET  /api/v1/ota/updates/{update_id}           # Get update progress
POST /api/v1/ota/updates/{update_id}/cancel    # Cancel update
POST /api/v1/ota/updates/{update_id}/retry     # Retry failed update
POST /api/v1/ota/devices/bulk/update           # Bulk device update
GET  /api/v1/ota/devices/{device_id}/updates   # Get device update history

# Rollback Operations
POST /api/v1/ota/devices/{device_id}/rollback  # Manual device rollback

# Statistics
GET  /api/v1/ota/stats                         # Global statistics
GET  /api/v1/ota/stats/campaigns/{campaign_id} # Campaign statistics
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus("ota_service")
    await ota_microservice.initialize(event_bus=event_bus)

    # Subscribe to events (handlers from events/handlers.py)
    event_handlers = get_event_handlers()
    for event_type, handler in event_handlers.items():
        await event_bus.subscribe_to_events(event_type, handler)

    # Consul registration (metadata includes routes)
    if config.consul_enabled:
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    await ota_microservice.shutdown()
    if event_bus:
        await event_bus.close()
```

### 2. Service Layer (ota_service.py)

**Class**: `OTAService`

**Responsibilities**:
- Business logic execution
- Firmware upload and validation
- Campaign orchestration
- Update scheduling and tracking
- Rollback operations
- Event publishing coordination
- Cross-service integration

**Key Methods**:
```python
class OTAService:
    def __init__(
        self,
        repository: OTARepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        device_client: Optional[DeviceClientProtocol] = None,
        storage_client: Optional[StorageClientProtocol] = None
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.device_client = device_client
        self.storage_client = storage_client

    # Firmware Operations
    async def upload_firmware(
        self,
        file: UploadFile,
        metadata: FirmwareUploadRequest,
        uploaded_by: str
    ) -> Tuple[FirmwareResponse, bool]:
        """
        Upload firmware binary with metadata.
        Returns (firmware_response, was_created: bool)
        """
        # 1. Validate file format and size
        # 2. Calculate checksums (MD5, SHA256)
        # 3. Verify provided checksums if any
        # 4. Generate deterministic firmware_id
        # 5. Check for existing firmware (idempotent)
        # 6. Upload binary to storage service
        # 7. Save metadata to database
        # 8. Publish firmware.uploaded event
        pass

    async def get_firmware(
        self,
        firmware_id: str
    ) -> FirmwareResponse:
        """Get firmware details by ID"""
        firmware = await self.repository.get_firmware_by_id(firmware_id)
        if not firmware:
            raise FirmwareNotFoundError(f"Firmware not found: {firmware_id}")
        return to_response(firmware)

    async def list_firmware(
        self,
        params: FirmwareListParams
    ) -> FirmwareListResponse:
        """List firmware with filtering and pagination"""
        return await self.repository.list_firmware(**params.dict())

    async def get_firmware_download(
        self,
        firmware_id: str
    ) -> FirmwareDownloadResponse:
        """Generate time-limited download URL"""
        firmware = await self.get_firmware(firmware_id)
        # Increment download counter
        await self.repository.increment_download_count(firmware_id)
        # Generate presigned URL from storage service
        download_url = await self.storage_client.get_presigned_url(
            firmware.file_url, expires_in=3600
        )
        return FirmwareDownloadResponse(
            download_url=download_url,
            checksum_md5=firmware.checksum_md5,
            checksum_sha256=firmware.checksum_sha256,
            expires_in=3600
        )

    # Campaign Operations
    async def create_campaign(
        self,
        request: CampaignCreateRequest,
        created_by: str
    ) -> CampaignResponse:
        """Create update campaign"""
        # 1. Validate firmware exists
        # 2. Calculate target device count
        # 3. Create campaign record
        # 4. Publish campaign.created event
        pass

    async def start_campaign(
        self,
        campaign_id: str
    ) -> CampaignResponse:
        """Start campaign deployment"""
        campaign = await self.repository.get_campaign_by_id(campaign_id)
        if not campaign:
            raise CampaignNotFoundError(f"Campaign not found: {campaign_id}")
        if campaign.status != "created":
            raise CampaignStatusError(f"Campaign cannot be started from status: {campaign.status}")

        # Update status to in_progress
        await self.repository.update_campaign_status(campaign_id, "in_progress")

        # Schedule device updates based on deployment strategy
        await self._schedule_campaign_updates(campaign)

        # Publish campaign.started event
        if self.event_bus:
            await publish_campaign_started(self.event_bus, campaign)

        return await self.get_campaign(campaign_id)

    async def _schedule_campaign_updates(self, campaign: Campaign):
        """Schedule device updates based on deployment strategy"""
        # Get target devices
        # Apply deployment strategy (immediate, staged, canary)
        # Create device update records
        # Respect batch_size and max_concurrent_updates
        pass

    # Device Update Operations
    async def update_device(
        self,
        device_id: str,
        request: DeviceUpdateRequest,
        requested_by: str
    ) -> DeviceUpdateResponse:
        """Update single device firmware"""
        # 1. Validate device exists via device_client
        device = await self.device_client.get_device(device_id)
        if not device:
            raise DeviceNotFoundError(f"Device not found: {device_id}")

        # 2. Validate firmware exists
        firmware = await self.get_firmware(request.firmware_id)

        # 3. Check firmware compatibility
        # 4. Create device update record
        # 5. Return update tracking info
        pass

    async def get_update_progress(
        self,
        update_id: str
    ) -> DeviceUpdateResponse:
        """Get update progress"""
        update = await self.repository.get_update_by_id(update_id)
        if not update:
            raise UpdateNotFoundError(f"Update not found: {update_id}")
        return to_update_response(update)

    # Rollback Operations
    async def rollback_device(
        self,
        device_id: str,
        request: RollbackRequest
    ) -> RollbackResponse:
        """Manual device rollback"""
        # 1. Validate device and target version
        # 2. Create rollback record
        # 3. Initiate rollback process
        # 4. Publish rollback.initiated event
        pass

    async def check_failure_threshold(self, campaign_id: str):
        """Check if campaign failure rate exceeds threshold"""
        campaign = await self.repository.get_campaign_by_id(campaign_id)
        stats = await self.repository.get_campaign_stats(campaign_id)

        if stats["total_finished"] > 0:
            failure_rate = (stats["failed_count"] / stats["total_finished"]) * 100
            if failure_rate > campaign.failure_threshold_percent and campaign.auto_rollback:
                await self._trigger_campaign_rollback(campaign)

    # Statistics
    async def get_stats(self) -> OTAStatsResponse:
        """Get global OTA statistics"""
        stats = await self.repository.get_global_stats()
        return OTAStatsResponse(**stats)

    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Database connectivity check"""
        db_connected = await self.repository.check_connection()
        return {
            "status": "healthy" if db_connected else "unhealthy",
            "database_connected": db_connected,
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Custom Exceptions**:
```python
class OTAServiceError(Exception):
    """Base exception for OTA service"""
    pass

class FirmwareNotFoundError(OTAServiceError):
    """Firmware not found"""
    pass

class FirmwareValidationError(OTAServiceError):
    """Firmware validation error"""
    pass

class CampaignNotFoundError(OTAServiceError):
    """Campaign not found"""
    pass

class CampaignStatusError(OTAServiceError):
    """Invalid campaign status transition"""
    pass

class UpdateNotFoundError(OTAServiceError):
    """Update not found"""
    pass

class DeviceNotFoundError(OTAServiceError):
    """Device not found"""
    pass

class RollbackError(OTAServiceError):
    """Rollback operation error"""
    pass

class ChecksumMismatchError(FirmwareValidationError):
    """Checksum verification failed"""
    pass
```

### 3. Repository Layer (ota_repository.py)

**Class**: `OTARepository`

**Responsibilities**:
- PostgreSQL CRUD operations
- gRPC communication with postgres_grpc_service
- Query construction (parameterized)
- Result parsing (proto JSONB to Python dict)
- No business logic

**Key Methods**:
```python
class OTARepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        # Discover PostgreSQL gRPC service via Consul
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id='ota_service')
        self.schema = "ota"
        self.firmware_table = "firmware"
        self.campaigns_table = "update_campaigns"
        self.updates_table = "device_updates"
        self.rollbacks_table = "rollback_logs"

    # Firmware Operations
    async def get_firmware_by_id(self, firmware_id: str) -> Optional[Firmware]:
        """Get firmware by ID"""
        async with self.db:
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.firmware_table} WHERE firmware_id = $1",
                params=[firmware_id]
            )
        if result:
            return self._row_to_firmware(result)
        return None

    async def create_firmware(
        self,
        firmware_id: str,
        name: str,
        version: str,
        device_model: str,
        manufacturer: str,
        file_url: str,
        file_size: int,
        checksum_md5: str,
        checksum_sha256: str,
        **kwargs
    ) -> Firmware:
        """Create firmware record"""
        async with self.db:
            await self.db.execute(
                f"""INSERT INTO {self.schema}.{self.firmware_table}
                    (firmware_id, name, version, device_model, manufacturer,
                     file_url, file_size, checksum_md5, checksum_sha256,
                     description, release_notes, min_hardware_version,
                     max_hardware_version, is_beta, is_security_update,
                     tags, metadata, created_by)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)""",
                params=[
                    firmware_id, name, version, device_model, manufacturer,
                    file_url, file_size, checksum_md5, checksum_sha256,
                    kwargs.get('description'), kwargs.get('release_notes'),
                    kwargs.get('min_hardware_version'), kwargs.get('max_hardware_version'),
                    kwargs.get('is_beta', False), kwargs.get('is_security_update', False),
                    kwargs.get('tags', []), kwargs.get('metadata', {}),
                    kwargs.get('created_by')
                ]
            )
        return await self.get_firmware_by_id(firmware_id)

    async def list_firmware(
        self,
        device_model: Optional[str] = None,
        manufacturer: Optional[str] = None,
        is_beta: Optional[bool] = None,
        is_security_update: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> FirmwareListResponse:
        """List firmware with filters"""
        conditions = ["is_active = TRUE"]
        params = []
        param_idx = 1

        if device_model:
            conditions.append(f"device_model = ${param_idx}")
            params.append(device_model)
            param_idx += 1

        if manufacturer:
            conditions.append(f"manufacturer = ${param_idx}")
            params.append(manufacturer)
            param_idx += 1

        if is_beta is not None:
            conditions.append(f"is_beta = ${param_idx}")
            params.append(is_beta)
            param_idx += 1

        if is_security_update is not None:
            conditions.append(f"is_security_update = ${param_idx}")
            params.append(is_security_update)
            param_idx += 1

        where_clause = " AND ".join(conditions)

        async with self.db:
            results = await self.db.query(
                f"""SELECT * FROM {self.schema}.{self.firmware_table}
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_idx} OFFSET ${param_idx + 1}""",
                params=[*params, limit, offset]
            )
            count_result = await self.db.query_row(
                f"SELECT COUNT(*) as count FROM {self.schema}.{self.firmware_table} WHERE {where_clause}",
                params=params
            )

        return FirmwareListResponse(
            firmware=[self._row_to_firmware(r) for r in results],
            count=count_result['count'],
            limit=limit,
            offset=offset
        )

    # Campaign Operations
    async def get_campaign_by_id(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID"""
        async with self.db:
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.campaigns_table} WHERE campaign_id = $1",
                params=[campaign_id]
            )
        if result:
            return self._row_to_campaign(result)
        return None

    async def create_campaign(self, **kwargs) -> Campaign:
        """Create campaign record"""
        # INSERT INTO campaigns...
        pass

    async def update_campaign_status(
        self,
        campaign_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """Update campaign status"""
        async with self.db:
            await self.db.execute(
                f"""UPDATE {self.schema}.{self.campaigns_table}
                    SET status = $1, updated_at = NOW()
                    WHERE campaign_id = $2""",
                params=[status, campaign_id]
            )
        return True

    # Device Update Operations
    async def get_update_by_id(self, update_id: str) -> Optional[DeviceUpdate]:
        """Get device update by ID"""
        pass

    async def create_device_update(self, **kwargs) -> DeviceUpdate:
        """Create device update record"""
        pass

    async def update_update_status(
        self,
        update_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """Update device update status"""
        pass

    # Statistics Operations
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global OTA statistics"""
        async with self.db:
            results = await asyncio.gather(
                self.db.query_row(
                    f"SELECT COUNT(*) as total FROM {self.schema}.{self.campaigns_table}"
                ),
                self.db.query_row(
                    f"SELECT COUNT(*) as active FROM {self.schema}.{self.campaigns_table} WHERE status = 'in_progress'"
                ),
                self.db.query_row(
                    f"SELECT COUNT(*) as total FROM {self.schema}.{self.updates_table}"
                ),
                self.db.query_row(
                    f"SELECT COUNT(*) as completed FROM {self.schema}.{self.updates_table} WHERE status = 'completed'"
                ),
                self.db.query_row(
                    f"SELECT COUNT(*) as failed FROM {self.schema}.{self.updates_table} WHERE status = 'failed'"
                ),
                self.db.query_row(
                    f"""SELECT COUNT(*) as recent FROM {self.schema}.{self.updates_table}
                        WHERE created_at > NOW() - INTERVAL '24 hours'"""
                ),
            )

        total_finished = results[3]['completed'] + results[4]['failed']
        success_rate = (results[3]['completed'] / total_finished * 100) if total_finished > 0 else 0

        return {
            "total_campaigns": results[0]['total'],
            "active_campaigns": results[1]['active'],
            "total_updates": results[2]['total'],
            "completed_updates": results[3]['completed'],
            "failed_updates": results[4]['failed'],
            "success_rate": round(success_rate, 2),
            "last_24h_updates": results[5]['recent']
        }

    def _row_to_firmware(self, row: Dict[str, Any]) -> Firmware:
        """Convert database row to Firmware model"""
        return Firmware(
            firmware_id=row['firmware_id'],
            name=row['name'],
            version=row['version'],
            device_model=row['device_model'],
            manufacturer=row['manufacturer'],
            file_url=row['file_url'],
            file_size=row['file_size'],
            checksum_md5=row['checksum_md5'],
            checksum_sha256=row['checksum_sha256'],
            description=row.get('description'),
            release_notes=row.get('release_notes'),
            is_beta=row.get('is_beta', False),
            is_security_update=row.get('is_security_update', False),
            download_count=row.get('download_count', 0),
            success_rate=row.get('success_rate', 0.0),
            is_active=row.get('is_active', True),
            created_at=row['created_at'],
            updated_at=row.get('updated_at'),
            created_by=row.get('created_by')
        )

    def _row_to_campaign(self, row: Dict[str, Any]) -> Campaign:
        """Convert database row to Campaign model"""
        pass
```

### 4. Client Layer (clients/)

**External Service Clients**:

| Client | Service | Methods |
|--------|---------|---------|
| `DeviceClient` | device_service | `get_device()`, `get_devices()`, `get_device_firmware_version()` |
| `StorageClient` | storage_service | `upload_file()`, `get_presigned_url()`, `delete_file()` |
| `NotificationClient` | notification_service | `send_alert()` (future) |

```python
class DeviceClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://device_service:8205"
        self.client = httpx.AsyncClient()

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device details"""
        response = await self.client.get(
            f"{self.base_url}/api/v1/devices/{device_id}",
            headers={"X-Internal-Call": "true"}
        )
        if response.status_code == 200:
            return response.json()
        return None

    async def get_device_firmware_version(self, device_id: str) -> Optional[str]:
        """Get device current firmware version"""
        device = await self.get_device(device_id)
        if device:
            return device.get("firmware_version")
        return None


class StorageClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://storage_service:8208"
        self.client = httpx.AsyncClient()

    async def upload_file(
        self,
        file: bytes,
        filename: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Upload file and return storage URL"""
        files = {"file": (filename, file, content_type)}
        response = await self.client.post(
            f"{self.base_url}/api/v1/storage/upload",
            files=files,
            headers={"X-Internal-Call": "true"}
        )
        if response.status_code == 201:
            return response.json().get("file_url")
        raise StorageError(f"Failed to upload file: {response.text}")

    async def get_presigned_url(self, file_url: str, expires_in: int = 3600) -> str:
        """Generate presigned download URL"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/storage/presign",
            json={"file_url": file_url, "expires_in": expires_in},
            headers={"X-Internal-Call": "true"}
        )
        if response.status_code == 200:
            return response.json().get("presigned_url")
        raise StorageError(f"Failed to generate presigned URL: {response.text}")
```

---

## Database Schema Design

### PostgreSQL Schema: `ota`

#### Table: ota.firmware

```sql
-- Create schema
CREATE SCHEMA IF NOT EXISTS ota;

-- Firmware table
CREATE TABLE IF NOT EXISTS ota.firmware (
    -- Primary Key
    firmware_id VARCHAR(64) PRIMARY KEY,

    -- Core Fields
    name VARCHAR(200) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    release_notes TEXT,

    -- Device Compatibility
    device_model VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    min_hardware_version VARCHAR(50),
    max_hardware_version VARCHAR(50),

    -- File Information
    file_url TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    checksum_md5 VARCHAR(32) NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,

    -- Flags
    is_beta BOOLEAN DEFAULT FALSE,
    is_security_update BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,

    -- Metrics
    download_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    -- Audit
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT firmware_version_unique UNIQUE (device_model, version)
);

-- Indexes
CREATE INDEX idx_firmware_device_model ON ota.firmware(device_model);
CREATE INDEX idx_firmware_manufacturer ON ota.firmware(manufacturer);
CREATE INDEX idx_firmware_is_beta ON ota.firmware(is_beta) WHERE is_active = TRUE;
CREATE INDEX idx_firmware_is_security ON ota.firmware(is_security_update) WHERE is_active = TRUE;
CREATE INDEX idx_firmware_created_at ON ota.firmware(created_at DESC);

-- Comments
COMMENT ON TABLE ota.firmware IS 'Stores firmware package metadata';
COMMENT ON COLUMN ota.firmware.firmware_id IS 'SHA256(name:version:device_model)[:32]';
```

#### Table: ota.update_campaigns

```sql
-- Update campaigns table
CREATE TABLE IF NOT EXISTS ota.update_campaigns (
    -- Primary Key
    campaign_id VARCHAR(64) PRIMARY KEY,

    -- Core Fields
    name VARCHAR(200) NOT NULL,
    description TEXT,
    firmware_id VARCHAR(64) NOT NULL REFERENCES ota.firmware(firmware_id),

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'created',

    -- Deployment Configuration
    deployment_strategy VARCHAR(20) NOT NULL DEFAULT 'staged',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    rollout_percentage INTEGER DEFAULT 100,
    max_concurrent_updates INTEGER DEFAULT 10,
    batch_size INTEGER DEFAULT 50,
    timeout_minutes INTEGER DEFAULT 60,

    -- Rollback Configuration
    auto_rollback BOOLEAN DEFAULT TRUE,
    failure_threshold_percent INTEGER DEFAULT 20,

    -- Target Devices
    target_devices TEXT[] DEFAULT '{}',
    target_groups TEXT[] DEFAULT '{}',
    target_filters JSONB DEFAULT '{}',
    target_device_count INTEGER DEFAULT 0,

    -- Progress Counters
    total_devices INTEGER DEFAULT 0,
    pending_devices INTEGER DEFAULT 0,
    in_progress_devices INTEGER DEFAULT 0,
    completed_devices INTEGER DEFAULT 0,
    failed_devices INTEGER DEFAULT 0,
    cancelled_devices INTEGER DEFAULT 0,

    -- Scheduling
    scheduled_at TIMESTAMPTZ,
    maintenance_window JSONB,

    -- Approval
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(255),
    approved_at TIMESTAMPTZ,
    approval_comments TEXT,

    -- Audit
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT campaign_status_check CHECK (status IN ('created', 'in_progress', 'paused', 'completed', 'failed', 'cancelled', 'rollback')),
    CONSTRAINT campaign_strategy_check CHECK (deployment_strategy IN ('immediate', 'scheduled', 'staged', 'canary', 'blue_green')),
    CONSTRAINT campaign_priority_check CHECK (priority IN ('low', 'normal', 'high', 'critical', 'emergency'))
);

-- Indexes
CREATE INDEX idx_campaigns_status ON ota.update_campaigns(status);
CREATE INDEX idx_campaigns_firmware ON ota.update_campaigns(firmware_id);
CREATE INDEX idx_campaigns_created_at ON ota.update_campaigns(created_at DESC);
CREATE INDEX idx_campaigns_scheduled ON ota.update_campaigns(scheduled_at) WHERE status = 'created';

-- Comments
COMMENT ON TABLE ota.update_campaigns IS 'Stores firmware update campaign metadata';
```

#### Table: ota.device_updates

```sql
-- Device updates table
CREATE TABLE IF NOT EXISTS ota.device_updates (
    -- Primary Key
    update_id VARCHAR(64) PRIMARY KEY,

    -- References
    device_id VARCHAR(255) NOT NULL,
    campaign_id VARCHAR(64) REFERENCES ota.update_campaigns(campaign_id),
    firmware_id VARCHAR(64) NOT NULL REFERENCES ota.firmware(firmware_id),

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    current_phase VARCHAR(20) DEFAULT 'scheduled',

    -- Progress
    progress_percentage REAL DEFAULT 0.0,
    download_progress REAL DEFAULT 0.0,
    download_speed REAL DEFAULT 0.0,

    -- Version Information
    from_version VARCHAR(50),
    to_version VARCHAR(50) NOT NULL,

    -- Configuration
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    timeout_minutes INTEGER DEFAULT 60,
    force_update BOOLEAN DEFAULT FALSE,

    -- Pre/Post Commands
    pre_update_commands JSONB DEFAULT '[]',
    post_update_commands JSONB DEFAULT '[]',

    -- Maintenance Window
    maintenance_window JSONB,

    -- Verification
    signature_verified BOOLEAN DEFAULT FALSE,
    checksum_verified BOOLEAN DEFAULT FALSE,

    -- Error Handling
    error_code VARCHAR(50),
    error_message TEXT,

    -- Timestamps
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    download_started_at TIMESTAMPTZ,
    download_completed_at TIMESTAMPTZ,
    install_started_at TIMESTAMPTZ,
    install_completed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT update_status_check CHECK (status IN ('scheduled', 'in_progress', 'downloading', 'verifying', 'installing', 'rebooting', 'completed', 'failed', 'cancelled', 'rollback')),
    CONSTRAINT update_phase_check CHECK (current_phase IN ('scheduled', 'downloading', 'verifying', 'installing', 'rebooting', 'completed', 'failed'))
);

-- Indexes
CREATE INDEX idx_updates_device ON ota.device_updates(device_id);
CREATE INDEX idx_updates_campaign ON ota.device_updates(campaign_id);
CREATE INDEX idx_updates_firmware ON ota.device_updates(firmware_id);
CREATE INDEX idx_updates_status ON ota.device_updates(status);
CREATE INDEX idx_updates_created_at ON ota.device_updates(created_at DESC);
CREATE INDEX idx_updates_device_status ON ota.device_updates(device_id, status);

-- Comments
COMMENT ON TABLE ota.device_updates IS 'Tracks individual device update operations';
```

#### Table: ota.rollback_logs

```sql
-- Rollback logs table
CREATE TABLE IF NOT EXISTS ota.rollback_logs (
    -- Primary Key
    rollback_id VARCHAR(64) PRIMARY KEY,

    -- References
    device_id VARCHAR(255) NOT NULL,
    campaign_id VARCHAR(64) REFERENCES ota.update_campaigns(campaign_id),
    update_id VARCHAR(64) REFERENCES ota.device_updates(update_id),

    -- Rollback Information
    trigger VARCHAR(20) NOT NULL,
    reason TEXT,
    from_version VARCHAR(50) NOT NULL,
    to_version VARCHAR(50) NOT NULL,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,

    -- Timestamps
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT rollback_trigger_check CHECK (trigger IN ('manual', 'failure_rate', 'health_check', 'timeout', 'error_threshold')),
    CONSTRAINT rollback_status_check CHECK (status IN ('in_progress', 'completed', 'failed'))
);

-- Indexes
CREATE INDEX idx_rollbacks_device ON ota.rollback_logs(device_id);
CREATE INDEX idx_rollbacks_campaign ON ota.rollback_logs(campaign_id);
CREATE INDEX idx_rollbacks_created_at ON ota.rollback_logs(created_at DESC);

-- Comments
COMMENT ON TABLE ota.rollback_logs IS 'Logs rollback operations for audit and tracking';
```

### Index Strategy

1. **Primary Keys**: Clustered index for fast lookups by ID
2. **Foreign Keys**: device_id, campaign_id, firmware_id for joins
3. **Status Indexes**: Filter by status for active operations
4. **Created At**: Sort by creation time (most recent first)
5. **Composite Indexes**: (device_id, status) for device update queries

### Database Migrations

| Version | Description | File |
|---------|-------------|------|
| 001 | Initial schema | `001_initial_schema.sql` |
| 002 | Add rollback_logs | `002_add_rollback_logs.sql` |
| 003 | Add campaign progress counters | `003_add_progress_counters.sql` |

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
firmware.uploaded               # New firmware uploaded
campaign.created                # Campaign created
campaign.started                # Campaign deployment started
update.cancelled                # Device update cancelled
rollback.initiated              # Rollback operation started
```

### Event Models (events/models.py)

```python
class FirmwareUploadedEventData(BaseModel):
    """Event: firmware.uploaded"""
    firmware_id: str
    name: str
    version: str
    device_model: str
    manufacturer: str
    file_size: int
    is_security_update: bool
    uploaded_by: str
    timestamp: datetime


class CampaignCreatedEventData(BaseModel):
    """Event: campaign.created"""
    campaign_id: str
    name: str
    firmware_id: str
    firmware_version: str
    target_device_count: int
    deployment_strategy: str
    priority: str
    created_by: str
    timestamp: datetime


class CampaignStartedEventData(BaseModel):
    """Event: campaign.started"""
    campaign_id: str
    name: str
    firmware_id: str
    firmware_version: str
    target_device_count: int
    timestamp: datetime


class UpdateCancelledEventData(BaseModel):
    """Event: update.cancelled"""
    update_id: str
    device_id: str
    firmware_id: str
    firmware_version: str
    campaign_id: Optional[str]
    timestamp: datetime


class RollbackInitiatedEventData(BaseModel):
    """Event: rollback.initiated"""
    rollback_id: str
    device_id: str
    from_version: str
    to_version: str
    trigger: str
    campaign_id: Optional[str]
    timestamp: datetime
```

### Event Publishers

```python
async def publish_firmware_uploaded(
    event_bus: EventBus,
    firmware: Firmware,
    uploaded_by: str
):
    """Publish firmware.uploaded event"""
    try:
        await event_bus.publish_event(Event(
            event_type=EventType.FIRMWARE_UPLOADED,
            source=ServiceSource.OTA_SERVICE,
            data=FirmwareUploadedEventData(
                firmware_id=firmware.firmware_id,
                name=firmware.name,
                version=firmware.version,
                device_model=firmware.device_model,
                manufacturer=firmware.manufacturer,
                file_size=firmware.file_size,
                is_security_update=firmware.is_security_update,
                uploaded_by=uploaded_by,
                timestamp=datetime.now(timezone.utc)
            ).dict()
        ))
    except Exception as e:
        logger.error(f"Failed to publish firmware.uploaded event: {e}")


async def publish_campaign_created(
    event_bus: EventBus,
    campaign: Campaign,
    firmware: Firmware,
    created_by: str
):
    """Publish campaign.created event"""
    try:
        await event_bus.publish_event(Event(
            event_type=EventType.CAMPAIGN_CREATED,
            source=ServiceSource.OTA_SERVICE,
            data=CampaignCreatedEventData(
                campaign_id=campaign.campaign_id,
                name=campaign.name,
                firmware_id=campaign.firmware_id,
                firmware_version=firmware.version,
                target_device_count=campaign.target_device_count,
                deployment_strategy=campaign.deployment_strategy,
                priority=campaign.priority,
                created_by=created_by,
                timestamp=datetime.now(timezone.utc)
            ).dict()
        ))
    except Exception as e:
        logger.error(f"Failed to publish campaign.created event: {e}")


async def publish_campaign_started(event_bus: EventBus, campaign: Campaign):
    """Publish campaign.started event"""
    pass


async def publish_rollback_initiated(
    event_bus: EventBus,
    rollback: RollbackLog
):
    """Publish rollback.initiated event"""
    try:
        await event_bus.publish_event(Event(
            event_type=EventType.ROLLBACK_INITIATED,
            source=ServiceSource.OTA_SERVICE,
            data=RollbackInitiatedEventData(
                rollback_id=rollback.rollback_id,
                device_id=rollback.device_id,
                from_version=rollback.from_version,
                to_version=rollback.to_version,
                trigger=rollback.trigger,
                campaign_id=rollback.campaign_id,
                timestamp=datetime.now(timezone.utc)
            ).dict()
        ))
    except Exception as e:
        logger.error(f"Failed to publish rollback.initiated event: {e}")
```

### Event Subscription (events/handlers.py)

```python
def get_event_handlers() -> Dict[str, Callable]:
    """Return event handlers for OTA service"""
    return {
        "device_service.device.deleted": handle_device_deleted,
        "account_service.user.deleted": handle_user_deleted,
    }


async def handle_device_deleted(event: Event):
    """Handle device.deleted event - cancel pending updates"""
    device_id = event.data.get("device_id")
    if not device_id:
        return

    logger.info(f"Handling device.deleted for {device_id}")

    # Cancel all pending/in-progress updates for this device
    repository = OTARepository()
    await repository.cancel_device_updates(
        device_id=device_id,
        reason="Device deleted"
    )


async def handle_user_deleted(event: Event):
    """Handle user.deleted event - clean up user preferences"""
    user_id = event.data.get("user_id")
    if not user_id:
        return

    logger.info(f"Handling user.deleted for {user_id}")
    # Clean up any user-specific OTA preferences
```

### Event Flow Diagram

```
┌─────────────────────┐
│   Admin Dashboard   │ (Uploads firmware)
└─────────┬───────────┘
          │ POST /api/v1/ota/firmware
          ↓
┌─────────────────────────────────────────────────────────────┐
│                       OTA Service                            │
│                                                              │
│  1. Validate file & metadata                                │
│  2. Calculate checksums                                     │
│  3. Upload to Storage Service ────────────────────────────┐ │
│  4. Save metadata to PostgreSQL ───────────────────────┐  │ │
│  5. Publish event ─────────────────────────────────┐   │  │ │
│                                                    │   │  │ │
└────────────────────────────────────────────────────┼───┼──┼─┘
                                                     │   │  │
                                                     ↓   ↓  ↓
                                          ┌──────────────────────────┐
                                          │        NATS Bus          │
                                          │  Subject:                │
                                          │  firmware.uploaded       │
                                          └──────────┬───────────────┘
                                                     │
          ┌──────────────────────────────────────────┼───────────────────────┐
          │                                          │                       │
          ↓                                          ↓                       ↓
┌─────────────────────┐                    ┌─────────────────────┐ ┌─────────────────────┐
│   Device Service    │                    │   Audit Service     │ │ Notification Service│
│                     │                    │                     │ │                     │
│  - Notify devices   │                    │  - Log firmware     │ │  - Alert admins     │
│    of new firmware  │                    │    upload event     │ │    (optional)       │
└─────────────────────┘                    └─────────────────────┘ └─────────────────────┘
```

---

## Data Flow Diagrams

### 1. Firmware Upload Flow

```
Admin uploads firmware binary
    │
    ↓
POST /api/v1/ota/firmware (multipart)
    │
    ↓
┌───────────────────────────────────────────────────────────────────────┐
│  OTAService.upload_firmware()                                          │
│                                                                        │
│  Step 1: Validate file                                                │
│    - Check file size <= 500MB                                         │
│    - Check file extension (.bin, .hex, .elf, .tar.gz, .zip)           │
│                                                                        │
│  Step 2: Calculate checksums                                          │
│    checksum_md5 = hashlib.md5(file_content).hexdigest()              │
│    checksum_sha256 = hashlib.sha256(file_content).hexdigest()        │
│                                                                        │
│  Step 3: Verify provided checksums (if any)                           │
│    if request.checksum_md5 and request.checksum_md5 != calculated:   │
│        raise ChecksumMismatchError("MD5 checksum mismatch")          │
│                                                                        │
│  Step 4: Generate firmware_id                                         │
│    firmware_id = sha256(f"{name}:{version}:{device_model}")[:32]     │
│                                                                        │
│  Step 5: Check for existing (idempotent)                              │
│    existing = repository.get_firmware_by_id(firmware_id)             │
│    if existing: return (existing, False)                              │
│                                                                        │
│  Step 6: Upload binary to Storage Service ──────────────────────────┐ │
│    file_url = storage_client.upload_file(file_content, filename)    │ │
│                                                                      │ │
│  Step 7: Save to database ──────────────────────────────────────────┼─┤
│    repository.create_firmware(...)                                   │ │
│                                                                      │ │
│  Step 8: Publish event ─────────────────────────────────────────────┼─┤
│    publish_firmware_uploaded(event_bus, firmware, uploaded_by)      │ │
│                                                                      │ │
└──────────────────────────────────────────────────────────────────────┼─┘
    │                                                                   │
    │ Return (FirmwareResponse, was_created=True)                      │
    ↓                                                                   ↓
Admin receives 201 Created                                   NATS: firmware.uploaded
                                                                        │
                                                   ┌────────────────────┼────────────────────┐
                                                   ↓                    ↓                    ↓
                                            device_service      audit_service     notification_service
                                            (notify devices)    (log upload)      (alert admins)
```

### 2. Campaign Creation and Start Flow

```
Admin creates campaign
    │
    ↓
POST /api/v1/ota/campaigns
    │
    ↓
┌───────────────────────────────────────────────────────────────────────┐
│  OTAService.create_campaign()                                          │
│                                                                        │
│  Step 1: Validate firmware exists                                     │
│    firmware = repository.get_firmware_by_id(request.firmware_id)     │
│    if not firmware: raise FirmwareNotFoundError                       │
│                                                                        │
│  Step 2: Calculate target device count                                │
│    target_count = len(request.target_devices)                        │
│                 + len(devices_in_groups)                              │
│                 + len(devices_matching_filters)                       │
│                                                                        │
│  Step 3: Create campaign record ──────────────────────────────────────┤
│    repository.create_campaign(...)                                    │
│                                                                        │
│  Step 4: Publish event ───────────────────────────────────────────────┤
│    publish_campaign_created(event_bus, campaign, firmware, user_id)  │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
    │
    │ Return CampaignResponse (status=created)
    ↓

Admin starts campaign
    │
    ↓
POST /api/v1/ota/campaigns/{campaign_id}/start
    │
    ↓
┌───────────────────────────────────────────────────────────────────────┐
│  OTAService.start_campaign()                                           │
│                                                                        │
│  Step 1: Validate campaign status                                     │
│    if campaign.status != 'created': raise CampaignStatusError        │
│                                                                        │
│  Step 2: Update status to in_progress ────────────────────────────────┤
│    repository.update_campaign_status(campaign_id, 'in_progress')     │
│                                                                        │
│  Step 3: Schedule device updates based on strategy                    │
│    _schedule_campaign_updates(campaign)                               │
│                                                                        │
│    immediate: Schedule all devices immediately                        │
│    staged: Schedule rollout_percentage% in batches                   │
│    canary: Schedule 5% first, wait for success, then rest            │
│                                                                        │
│  Step 4: Create device update records ────────────────────────────────┤
│    for device_batch in batches:                                       │
│        for device_id in device_batch:                                 │
│            repository.create_device_update(                           │
│                device_id=device_id,                                   │
│                campaign_id=campaign_id,                               │
│                firmware_id=firmware_id,                               │
│                status='scheduled'                                     │
│            )                                                          │
│                                                                        │
│  Step 5: Publish event ───────────────────────────────────────────────┤
│    publish_campaign_started(event_bus, campaign)                      │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
    │
    │ Return CampaignResponse (status=in_progress)
    ↓
Admin receives updated campaign
```

### 3. Device Update Progress Flow

```
Device requests update status
    │
    ↓
GET /api/v1/ota/updates/{update_id}
    │
    ↓
┌───────────────────────────────────────────────────────────────────────┐
│  OTAService.get_update_progress()                                      │
│                                                                        │
│  repository.get_update_by_id(update_id) ──────────────────────────────┤
│    Result: DeviceUpdate                                               │
│                                                                        │
│  Return DeviceUpdateResponse:                                         │
│    - update_id                                                        │
│    - device_id                                                        │
│    - status (scheduled/downloading/installing/completed/failed)       │
│    - progress_percentage (0.0 - 100.0)                               │
│    - current_phase                                                    │
│    - download_progress                                                │
│    - download_speed                                                   │
│    - error_code / error_message (if failed)                          │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
    │
    ↓
Client receives update progress
```

### 4. Automatic Rollback Flow

```
Campaign running, device updates completing
    │
    ↓
Device update fails
    │
    ↓
┌───────────────────────────────────────────────────────────────────────┐
│  OTAService.update_device_status(update_id, 'failed')                  │
│                                                                        │
│  Step 1: Update device status ────────────────────────────────────────┤
│    repository.update_update_status(update_id, 'failed', error=...)   │
│                                                                        │
│  Step 2: Update campaign counters ────────────────────────────────────┤
│    repository.increment_campaign_counter(campaign_id, 'failed')      │
│                                                                        │
│  Step 3: Check failure threshold                                      │
│    check_failure_threshold(campaign_id)                               │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
    │
    ↓
┌───────────────────────────────────────────────────────────────────────┐
│  OTAService.check_failure_threshold()                                  │
│                                                                        │
│  campaign = repository.get_campaign_by_id(campaign_id)               │
│  stats = repository.get_campaign_stats(campaign_id)                  │
│                                                                        │
│  total_finished = stats.completed + stats.failed                      │
│  failure_rate = (stats.failed / total_finished) * 100                │
│                                                                        │
│  if failure_rate > campaign.failure_threshold_percent                │
│     AND campaign.auto_rollback == True:                              │
│                                                                        │
│      _trigger_campaign_rollback(campaign)                             │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
    │
    ↓ (if threshold exceeded)
┌───────────────────────────────────────────────────────────────────────┐
│  OTAService._trigger_campaign_rollback()                               │
│                                                                        │
│  Step 1: Update campaign status ──────────────────────────────────────┤
│    repository.update_campaign_status(campaign_id, 'rollback')        │
│                                                                        │
│  Step 2: Cancel pending updates ──────────────────────────────────────┤
│    repository.cancel_pending_updates(campaign_id)                    │
│                                                                        │
│  Step 3: Create rollback records for completed devices ───────────────┤
│    completed_devices = repository.get_completed_updates(campaign_id) │
│    for device in completed_devices:                                   │
│        repository.create_rollback_log(                                │
│            device_id=device.device_id,                                │
│            campaign_id=campaign_id,                                   │
│            from_version=device.to_version,                            │
│            to_version=device.from_version,                            │
│            trigger='failure_rate'                                     │
│        )                                                              │
│                                                                        │
│  Step 4: Publish rollback event ──────────────────────────────────────┤
│    publish_rollback_initiated(event_bus, ...)                        │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
    │
    ↓
NATS: rollback.initiated
    │
    ┌────────────────────┼────────────────────┐
    ↓                    ↓                    ↓
device_service     audit_service     notification_service
(update versions)  (log rollback)    (alert admins)
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server
- **httpx**: Async HTTP client

### Data Storage
- **PostgreSQL 15+**: Primary database
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `ota`
- **Tables**: `firmware`, `update_campaigns`, `device_updates`, `rollback_logs`

### File Storage
- **MinIO/S3**: Firmware binary storage
- **Storage Service**: Intermediary for file operations
- **Presigned URLs**: Time-limited download links

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `firmware.*`, `campaign.*`, `rollback.*`
- **Publishers**: OTA Service
- **Subscribers**: device_service, audit_service, notification_service, telemetry_service

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration

### Dependency Injection
- **Protocols (typing.Protocol)**: Interface definitions
- **Factory Pattern**: Production vs test instances
- **ConfigManager**: Environment-based configuration

### Observability
- **Structured Logging**: JSON format
- **core.logger**: Service logger
- **Health Endpoints**: `/health`, `/health/detailed`

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **File Validation**: Size limits (500MB), format validation
- **Checksum Verification**: MD5/SHA256 for integrity
- **SQL Injection**: Parameterized queries via gRPC
- **XSS Prevention**: Input sanitization

### Access Control
- **JWT Authentication**: Handled by API Gateway
- **Admin Operations**: Campaign creation requires admin role
- **Device Validation**: Cross-service check before updates
- **Internal Calls**: X-Internal-Call header for service-to-service

### Data Privacy
- **Soft Delete**: Firmware/campaigns preserved for audit
- **Audit Trail**: All operations logged with user_id
- **Encryption in Transit**: TLS for all communication
- **Presigned URLs**: Time-limited access to firmware binaries

### Rate Limiting (Future)
- **Per User**: 1000 requests/hour
- **Per IP**: 5000 requests/hour
- **Burst**: 100 requests/minute

---

## Performance Optimization

### Database Optimization
- **Indexes**: Strategic indexes on firmware_id, campaign_id, device_id, status
- **Connection Pooling**: gRPC client pools connections
- **Concurrent Queries**: `asyncio.gather` for statistics
- **Query Optimization**: Avoid N+1, use LIMIT/OFFSET
- **Batch Operations**: Bulk inserts for device updates

### API Optimization
- **Async Operations**: All I/O is async
- **Batch Operations**: Bulk update endpoints
- **Pagination**: Max limit=200 to prevent memory overflow
- **Streaming**: Large file uploads use streaming

### Event Publishing
- **Non-Blocking**: Event failures don't block operations
- **Async Publishing**: Fire-and-forget pattern
- **Error Logging**: Failed publishes logged for retry

### Caching (Future)
- **Firmware Metadata**: Cache frequently accessed firmware info
- **Campaign Status**: Cache campaign progress for dashboard
- **TTL**: 5 minute TTL for cached data

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New firmware/campaign/update created
- `400 Bad Request`: Validation error, file too large, invalid format
- `404 Not Found`: Firmware/campaign/update not found
- `409 Conflict`: Campaign already started
- `422 Unprocessable Entity`: Checksum mismatch
- `500 Internal Server Error`: Database error, unexpected error
- `503 Service Unavailable`: Database/Storage unavailable

### Error Response Format
```json
{
  "detail": "Firmware not found with firmware_id: abc123"
}
```

### Exception Handling
```python
@app.exception_handler(FirmwareValidationError)
async def validation_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(ChecksumMismatchError)
async def checksum_error_handler(request, exc):
    return HTTPException(status_code=422, detail=str(exc))

@app.exception_handler(FirmwareNotFoundError)
async def not_found_error_handler(request, exc):
    return HTTPException(status_code=404, detail=str(exc))

@app.exception_handler(CampaignStatusError)
async def status_error_handler(request, exc):
    return HTTPException(status_code=409, detail=str(exc))

@app.exception_handler(OTAServiceError)
async def service_error_handler(request, exc):
    return HTTPException(status_code=500, detail=str(exc))
```

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation
- **Logic Contract**: Business rule documentation
- **Component Tests**: Factory, builder, validation tests

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **Event Publishing**: Verify events published correctly
- **Cross-Service**: Device, Storage client mocks

### API Testing
- **Endpoint Contracts**: All 25+ endpoints tested
- **Error Handling**: Validation, not found, server errors
- **Pagination**: Page boundaries, empty results
- **File Upload**: Multipart form handling

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Database Connectivity**: PostgreSQL availability
- **Storage Connectivity**: MinIO/S3 availability

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | HTTP port | 8216 |
| `POSTGRES_GRPC_HOST` | DB host | isa-postgres-grpc |
| `POSTGRES_GRPC_PORT` | DB port | 50061 |
| `NATS_URL` | NATS connection | nats://isa-nats:4222 |
| `CONSUL_HOST` | Consul host | localhost |
| `CONSUL_PORT` | Consul port | 8500 |
| `DEVICE_SERVICE_URL` | Device service | http://device_service:8205 |
| `STORAGE_SERVICE_URL` | Storage service | http://storage_service:8208 |
| `MAX_FIRMWARE_SIZE_MB` | Max upload size | 500 |
| `LOG_LEVEL` | Logging level | INFO |

### Health Check

```json
GET /health
{
  "status": "healthy",
  "service": "ota_service",
  "version": "1.0.0"
}

GET /health/detailed
{
  "status": "healthy",
  "service": "ota_service",
  "version": "1.0.0",
  "dependencies": {
    "postgres": "connected",
    "nats": "connected",
    "storage": "connected"
  },
  "timestamp": "2025-12-18T10:00:00Z"
}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ota-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ota-service
  template:
    metadata:
      labels:
        app: ota-service
    spec:
      containers:
      - name: ota-service
        image: ota-service:latest
        ports:
        - containerPort: 8216
        env:
        - name: SERVICE_PORT
          value: "8216"
        - name: POSTGRES_GRPC_HOST
          value: "isa-postgres-grpc"
        - name: NATS_URL
          value: "nats://isa-nats:4222"
        livenessProbe:
          httpGet:
            path: /health
            port: 8216
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/detailed
            port: 8216
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: OTA Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/ota_service.md
- PRD: docs/prd/ota_service.md
- Data Contract: tests/contracts/ota_service/data_contract.py
- Logic Contract: tests/contracts/ota_service/logic_contract.md
