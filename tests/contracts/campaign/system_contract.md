# Campaign Service - System Contract

**Implementation Patterns and Architecture for Campaign Service**

This document defines HOW campaign_service implements the 12 standard patterns.
Pattern Reference: `.claude/skills/cdd-system-contract/SKILL.md`

---

## Table of Contents

1. [Service Identity](#service-identity)
2. [Architecture Overview](#architecture-overview)
3. [Service Initialization (Lifespan Pattern)](#1-service-initialization-lifespan-pattern)
4. [Dependency Injection Pattern](#2-dependency-injection-pattern)
5. [Health Checks Pattern](#3-health-checks-pattern)
6. [Configuration Management Pattern](#4-configuration-management-pattern)
7. [Error Handling Pattern](#5-error-handling-pattern)
8. [Logging Strategy Pattern](#6-logging-strategy-pattern)
9. [API Patterns](#7-api-patterns)
10. [Event Publishing Pattern](#8-event-publishing-pattern)
11. [Event Subscription Pattern](#9-event-subscription-pattern)
12. [Service Discovery Pattern](#10-service-discovery-pattern)
13. [Database Access Pattern](#11-database-access-pattern)
14. [Client SDK Pattern](#12-client-sdk-pattern)

---

## Service Identity

| Property | Value |
|----------|-------|
| **Service Name** | `campaign_service` |
| **Port** | `8240` |
| **Schema** | `campaign` |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/campaign_service/` |
| **Description** | Marketing automation campaign management with multi-channel delivery, A/B testing, and performance analytics |

---

## Architecture Overview

### High-Level Architecture

```
+-------------------+    +-------------------+    +-------------------+
|   Web Client      |    |   Mobile App      |    |  Other Services   |
+--------+----------+    +--------+----------+    +--------+----------+
         |                        |                        |
         +------------------------+------------------------+
                                  |
                     +------------+------------+
                     |      API Gateway        |
                     +------------+------------+
                                  |
                     +------------+------------+
                     |   Campaign Service      |
                     |   (FastAPI + PostgreSQL)|
                     |       Port: 8240        |
                     +------------+------------+
                                  |
         +------------------------+------------------------+
         |                        |                        |
+--------+--------+      +--------+--------+      +--------+--------+
|      NATS       |      |   PostgreSQL    |      |     Redis       |
|   (Event Bus)   |      |   (campaign)    |      |    (Cache)      |
+--------+--------+      +-----------------+      +-----------------+
         |
+--------+--------------------------------------------------------+
|        |                |                |                       |
+--------+---+  +---------+--+  +----------+-+  +---------+  +-----+------+
|task_service|  |notif_svc   |  |event_svc   |  |isA_Data |  |isA_Creative|
+------------+  +------------+  +------------+  +---------+  +------------+
```

### File Structure

```
microservices/campaign_service/
|-- __init__.py
|-- main.py                       # FastAPI app + lifecycle management
|-- campaign_service.py           # Core business logic layer
|-- audience_service.py           # Audience resolution and holdout
|-- variant_service.py            # A/B test variant management
|-- execution_service.py          # Campaign execution orchestration
|-- trigger_service.py            # Event trigger evaluation
|-- metrics_service.py            # Metric aggregation and reporting
|-- throttle_service.py           # Rate limiting and scheduling
|-- campaign_repository.py        # Data access layer (PostgreSQL via gRPC)
|-- models.py                     # Pydantic models (Campaign, Variant, etc.)
|-- routes_registry.py            # Consul route registration
|-- client.py                     # HTTP client SDK (CampaignServiceClient)
|-- factory.py                    # Service factory for dependency injection
|-- protocols.py                  # Protocol definitions for type safety
|-- clients/
|   |-- __init__.py
|   |-- account_client.py         # Sync call to account_service
|   |-- task_client.py            # Sync call to task_service
|   |-- notification_client.py    # Sync call to notification_service
|   |-- isa_data_client.py        # Sync call to isA_Data (intelligent_query, user_360)
|   |-- isa_creative_client.py    # Sync call to isA_Creative
|-- events/
|   |-- __init__.py
|   |-- models.py                 # Event payload models
|   |-- publishers.py             # NATS publish functions
|   |-- handlers.py               # NATS subscribe handlers
|-- migrations/
|   |-- 001_create_campaign_tables.sql
|   |-- 002_create_execution_tables.sql
|   |-- 003_create_metrics_tables.sql
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring, lifespan |
| Business | `campaign_service.py` | Campaign CRUD, lifecycle management |
| Business | `audience_service.py` | Segment resolution, holdout calculation |
| Business | `variant_service.py` | A/B test variant assignment, statistics |
| Business | `execution_service.py` | Campaign execution orchestration |
| Business | `trigger_service.py` | Trigger evaluation, frequency limiting |
| Business | `metrics_service.py` | Metric aggregation, conversion tracking |
| Business | `throttle_service.py` | Rate limiting, quiet hours |
| Data | `campaign_repository.py` | PostgreSQL queries via AsyncPostgresClient (gRPC) |
| External | `clients/` | HTTP calls to other services |
| Async | `events/` | NATS event publishing and subscriptions |
| SDK | `client.py` | Client library for other services |

---

## 1. Service Initialization (Lifespan Pattern)

### Lifespan Context Manager (`main.py`)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config_manager import ConfigManager
from core.nats_client import get_event_bus
from core.consul_registry import ConsulRegistry

# Global service instances
campaign_service: Optional[CampaignService] = None
campaign_repository: Optional[CampaignRepository] = None
execution_service: Optional[ExecutionService] = None
trigger_service: Optional[TriggerService] = None
metrics_service: Optional[MetricsService] = None
audience_service: Optional[AudienceService] = None
event_bus = None
consul_registry: Optional[ConsulRegistry] = None

config_manager = ConfigManager("campaign_service")
config = config_manager.get_service_config()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global campaign_service, campaign_repository, execution_service
    global trigger_service, metrics_service, audience_service
    global event_bus, consul_registry

    try:
        # 1. Initialize centralized NATS event bus
        try:
            event_bus = await get_event_bus("campaign_service")
            logger.info("Centralized event bus initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize event bus: {e}")
            event_bus = None

        # 2. Initialize repositories
        campaign_repository = CampaignRepository(config=config_manager)
        await campaign_repository.initialize()

        # 3. Initialize service layer
        audience_service = AudienceService(
            repository=campaign_repository,
            config_manager=config_manager
        )
        metrics_service = MetricsService(
            repository=campaign_repository,
            event_bus=event_bus
        )
        trigger_service = TriggerService(
            repository=campaign_repository,
            event_bus=event_bus
        )
        execution_service = ExecutionService(
            repository=campaign_repository,
            audience_service=audience_service,
            metrics_service=metrics_service,
            event_bus=event_bus,
            config_manager=config_manager
        )
        campaign_service = CampaignService(
            repository=campaign_repository,
            execution_service=execution_service,
            trigger_service=trigger_service,
            metrics_service=metrics_service,
            audience_service=audience_service,
            event_bus=event_bus,
            config_manager=config_manager
        )

        # 4. Subscribe to NATS events
        if event_bus:
            await subscribe_to_nats_events()

        # 5. Start background tasks
        asyncio.create_task(metrics_aggregation_loop())
        asyncio.create_task(trigger_evaluation_loop())

        # 6. Register with Consul (if enabled)
        if config.consul_enabled:
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

        logger.info(f"Campaign service started on port {config.service_port}")
        yield  # App runs

    finally:
        # Shutdown sequence
        logger.info("Shutting down campaign service...")
        if event_bus:
            await event_bus.close()
        if consul_registry:
            consul_registry.deregister()
        if campaign_repository:
            await campaign_repository.close()
        logger.info("Campaign service shutdown complete")

app = FastAPI(lifespan=lifespan)
```

### Startup Sequence

| Step | Action | Details |
|------|--------|---------|
| 1 | Initialize NATS | `get_event_bus("campaign_service")` via gRPC |
| 2 | Create Repository | `CampaignRepository(config=config_manager)` |
| 3 | Initialize Repository | `await campaign_repository.initialize()` |
| 4 | Create Services | Inject repository and event_bus to all services |
| 5 | Subscribe to Events | NATS subscriptions for external events |
| 6 | Start Background Tasks | Metrics aggregation, trigger evaluation loops |
| 7 | Consul Registration | Register routes and metadata |
| 8 | Log Startup | "Campaign service started successfully" |

### Shutdown Sequence

| Step | Action | Details |
|------|--------|---------|
| 1 | Log Shutdown | "Shutting down campaign service..." |
| 2 | Close Event Bus | `await event_bus.close()` |
| 3 | Deregister Consul | `consul_registry.deregister()` |
| 4 | Close Repository | `await campaign_repository.close()` |
| 5 | Log Complete | "Campaign service shutdown complete" |

---

## 2. Dependency Injection Pattern

### Service Initialization

```python
# main.py - Global service instances
campaign_service: Optional[CampaignService] = None
campaign_repository: Optional[CampaignRepository] = None
execution_service: Optional[ExecutionService] = None
trigger_service: Optional[TriggerService] = None
metrics_service: Optional[MetricsService] = None
audience_service: Optional[AudienceService] = None
variant_service: Optional[VariantService] = None
throttle_service: Optional[ThrottleService] = None
event_bus = None
consul_registry: Optional[ConsulRegistry] = None
```

### FastAPI Dependency Functions

```python
from fastapi import Depends, HTTPException

async def get_campaign_service() -> CampaignService:
    """Get campaign service instance"""
    if not campaign_service:
        raise HTTPException(status_code=503, detail="Campaign service not initialized")
    return campaign_service

async def get_execution_service() -> ExecutionService:
    """Get execution service instance"""
    if not execution_service:
        raise HTTPException(status_code=503, detail="Execution service not initialized")
    return execution_service

async def get_metrics_service() -> MetricsService:
    """Get metrics service instance"""
    if not metrics_service:
        raise HTTPException(status_code=503, detail="Metrics service not initialized")
    return metrics_service

async def get_audience_service() -> AudienceService:
    """Get audience service instance"""
    if not audience_service:
        raise HTTPException(status_code=503, detail="Audience service not initialized")
    return audience_service
```

### Usage in Endpoints

```python
@app.post("/api/v1/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    request: CampaignCreateRequest = Body(...),
    service: CampaignService = Depends(get_campaign_service)
):
    campaign = await service.create_campaign(request)
    return CampaignResponse(campaign=campaign, message="Campaign created successfully")

@app.get("/api/v1/campaigns/{campaign_id}/metrics", response_model=CampaignMetricsResponse)
async def get_campaign_metrics(
    campaign_id: str,
    breakdown_by: Optional[str] = Query(None),
    service: MetricsService = Depends(get_metrics_service)
):
    metrics = await service.get_campaign_metrics(campaign_id, breakdown_by=breakdown_by)
    return metrics
```

### CampaignService Constructor Pattern

```python
class CampaignService:
    """Core campaign management service"""

    def __init__(
        self,
        repository: CampaignRepository,
        execution_service: ExecutionService,
        trigger_service: TriggerService,
        metrics_service: MetricsService,
        audience_service: AudienceService,
        event_bus=None,
        config_manager: Optional[ConfigManager] = None
    ):
        self.repository = repository
        self.execution_service = execution_service
        self.trigger_service = trigger_service
        self.metrics_service = metrics_service
        self.audience_service = audience_service
        self.event_bus = event_bus
        self.config_manager = config_manager or ConfigManager("campaign_service")

        # Initialize external clients
        self.task_client = TaskServiceClient()
        self.notification_client = NotificationServiceClient()
```

### Factory Pattern (`factory.py`)

```python
from typing import Optional
from core.config_manager import ConfigManager

class CampaignServiceFactory:
    """Factory for creating campaign service instances"""

    @staticmethod
    async def create(
        config_manager: Optional[ConfigManager] = None,
        event_bus=None
    ) -> CampaignService:
        """Create fully initialized campaign service"""
        config = config_manager or ConfigManager("campaign_service")

        # Create repository
        repository = CampaignRepository(config=config)
        await repository.initialize()

        # Create dependent services
        audience_service = AudienceService(repository=repository, config_manager=config)
        metrics_service = MetricsService(repository=repository, event_bus=event_bus)
        trigger_service = TriggerService(repository=repository, event_bus=event_bus)

        execution_service = ExecutionService(
            repository=repository,
            audience_service=audience_service,
            metrics_service=metrics_service,
            event_bus=event_bus,
            config_manager=config
        )

        # Create main service
        return CampaignService(
            repository=repository,
            execution_service=execution_service,
            trigger_service=trigger_service,
            metrics_service=metrics_service,
            audience_service=audience_service,
            event_bus=event_bus,
            config_manager=config
        )
```

---

## 3. Health Checks Pattern

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Basic health check |
| `/health/ready` | GET | Readiness check with dependency status |
| `/health/live` | GET | Liveness probe |

### Health Check Response

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "campaign_service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/ready")
async def readiness_check():
    checks = {
        "database": await check_database_health(),
        "nats": await check_nats_health(),
        "redis": await check_redis_health()
    }

    is_ready = all(c["status"] == "healthy" for c in checks.values())

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/live")
async def liveness_check():
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Dependency Health Checks

```python
async def check_database_health() -> dict:
    """Check PostgreSQL connection"""
    try:
        if campaign_repository:
            await campaign_repository.health_check()
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": "Repository not initialized"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_nats_health() -> dict:
    """Check NATS connection"""
    try:
        if event_bus and event_bus.is_connected:
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": "NATS not connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_redis_health() -> dict:
    """Check Redis connection"""
    try:
        # Redis health check implementation
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

---

## 4. Configuration Management Pattern

### ConfigManager Usage

```python
from core.config_manager import ConfigManager

# Initialize configuration
config_manager = ConfigManager("campaign_service")
config = config_manager.get_service_config()
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMPAIGN_SERVICE_PORT` | `8240` | Service port |
| `CAMPAIGN_SERVICE_HOST` | `0.0.0.0` | Service host |
| `CONSUL_ENABLED` | `true` | Enable Consul registration |
| `CONSUL_HOST` | `localhost` | Consul host |
| `CONSUL_PORT` | `8500` | Consul port |
| `POSTGRES_HOST` | `isa-postgres-grpc` | PostgreSQL gRPC host |
| `POSTGRES_PORT` | `50061` | PostgreSQL gRPC port |
| `NATS_GRPC_HOST` | `isa-nats-grpc` | NATS gRPC host |
| `NATS_GRPC_PORT` | `50056` | NATS gRPC port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for caching |
| `ISA_DATA_URL` | `http://isa-data:8300` | isA_Data service URL |
| `ISA_CREATIVE_URL` | `http://isa-creative:8310` | isA_Creative service URL |
| `NOTIFICATION_SERVICE_URL` | `http://notification-service:8208` | Notification service URL |
| `TASK_SERVICE_URL` | `http://task-service:8229` | Task service URL |
| `EVENT_SERVICE_URL` | `http://event-service:8230` | Event service URL |
| `MESSAGE_RATE_LIMIT_PER_MINUTE` | `10000` | Default message rate limit |
| `MESSAGE_RATE_LIMIT_PER_HOUR` | `100000` | Default hourly rate limit |
| `SEGMENT_CACHE_TTL` | `300` | Segment cache TTL in seconds |
| `METRICS_AGGREGATION_INTERVAL` | `60` | Metrics aggregation interval in seconds |

### Service Discovery Pattern

```python
# In CampaignRepository
host, port = config.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061,
    env_host_key='POSTGRES_HOST',
    env_port_key='POSTGRES_PORT'
)
```

### Priority Order

1. Environment variables (highest)
2. Consul service discovery
3. Localhost fallback (lowest)

---

## 5. Error Handling Pattern

### HTTP Status Codes

| Status | When Used | Example |
|--------|-----------|---------|
| `200` | Success | Campaign retrieved, metrics returned |
| `201` | Created | Campaign created, variant added |
| `400` | Bad Request | Invalid configuration, missing required fields |
| `401` | Unauthorized | Missing or invalid authentication |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Campaign/variant/execution not found |
| `409` | Conflict | Invalid state transition |
| `422` | Validation Error | Field validation failed |
| `500` | Internal Error | General exception |
| `503` | Service Unavailable | Service not initialized |

### Exception Handling Pattern

```python
@app.post("/api/v1/campaigns/{campaign_id}/schedule", response_model=CampaignResponse)
async def schedule_campaign(
    campaign_id: str,
    request: ScheduleRequest = Body(...),
    service: CampaignService = Depends(get_campaign_service)
):
    try:
        # Check campaign exists
        campaign = await service.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Check state transition
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(
                status_code=409,
                detail="Only draft campaigns can be scheduled"
            )

        # Validate schedule
        if request.scheduled_at < datetime.now(timezone.utc) + timedelta(minutes=5):
            raise HTTPException(
                status_code=400,
                detail="Scheduled time must be at least 5 minutes in the future"
            )

        # Perform operation
        updated = await service.schedule_campaign(campaign_id, request)
        return CampaignResponse(campaign=updated, message="Campaign scheduled successfully")

    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error scheduling campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Service Layer Exception Handling

```python
class CampaignService:
    async def create_campaign(self, request: CampaignCreateRequest) -> Campaign:
        try:
            # Validate audiences exist
            for audience in request.audiences:
                if audience.segment_id:
                    exists = await self._validate_segment_exists(audience.segment_id)
                    if not exists:
                        raise ValueError(f"Segment not found: {audience.segment_id}")

            # Create campaign
            campaign = Campaign(
                campaign_id=self._generate_campaign_id(),
                organization_id=request.organization_id,
                name=request.name,
                # ... other fields
            )

            # Save to database
            saved = await self.repository.save_campaign(campaign)

            # Publish event
            if self.event_bus:
                await self._publish_campaign_created(saved)

            return saved

        except ValueError as e:
            logger.warning(f"Validation error creating campaign: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            raise
```

### Repository Layer Error Handling

```python
class CampaignRepository:
    async def save_campaign(self, campaign: Campaign) -> Campaign:
        try:
            campaign_dict = campaign.model_dump()
            async with self.db:
                await self.db.insert_into(
                    self.campaigns_table,
                    [campaign_dict],
                    schema=self.schema
                )
            return campaign
        except Exception as e:
            logger.error(f"Error saving campaign {campaign.campaign_id}: {e}")
            raise
```

---

## 6. Logging Strategy Pattern

### Logger Setup

```python
from core.logger import setup_service_logger

app_logger = setup_service_logger("campaign_service")
logger = app_logger  # backward compatibility
```

### Logging Patterns

```python
# Info - successful operations
logger.info(f"Campaign created: {campaign.campaign_id} - {campaign.name}")
logger.info(f"Campaign scheduled: {campaign_id} for {scheduled_at}")
logger.info(f"Campaign execution started: {execution_id}, audience_size={audience_size}")
logger.info(f"Service registered with Consul: {route_meta.get('route_count')} routes")

# Warning - non-critical issues
logger.warning(f"Failed to initialize event bus: {e}. Continuing without event publishing.")
logger.warning(f"Segment resolution using cached data: {segment_id}")
logger.warning(f"Rate limit reached for campaign {campaign_id}, queueing messages")

# Error - failures
logger.error(f"Error creating campaign: {e}")
logger.error(f"Failed to publish campaign.created event: {e}")
logger.error(f"Trigger evaluation failed for campaign {campaign_id}: {e}")
logger.error(f"Message delivery failed for {message_id}: {e}")

# Debug - detailed tracing
logger.debug(f"Resolving audience for campaign {campaign_id}")
logger.debug(f"Variant assignment: user={user_id}, campaign={campaign_id}, variant={variant_id}")
logger.debug(f"Throttle check: rate={current_rate}, limit={rate_limit}")
```

### Structured Log Fields

| Field | Purpose |
|-------|---------|
| `campaign_id` | Campaign identifier |
| `execution_id` | Execution identifier |
| `message_id` | Message identifier |
| `user_id` | User performing action or recipient |
| `organization_id` | Organization context |
| `variant_id` | Variant identifier |
| `channel_type` | Delivery channel |
| `duration_ms` | Processing duration |
| `audience_size` | Resolved audience size |
| `error_type` | Error classification |

---

## 7. API Patterns

### Request/Response Models

#### Campaign Create Request

```python
class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    campaign_type: CampaignType
    schedule_type: Optional[ScheduleType] = None
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    timezone: str = Field(default="UTC")
    throttle: Optional[ThrottleConfig] = None
    audiences: List[CampaignAudience] = Field(default_factory=list)
    channels: List[CampaignChannel] = Field(default_factory=list)
    enable_ab_testing: bool = Field(default=False)
    variants: List[CampaignVariant] = Field(default_factory=list)
    triggers: List[CampaignTrigger] = Field(default_factory=list)
    conversion_event_type: Optional[str] = None
    attribution_window_days: int = Field(default=7)
    holdout_percentage: Decimal = Field(default=Decimal("0"))
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### Campaign Response

```python
class CampaignResponse(BaseModel):
    campaign: Campaign
    message: str = "Success"

class Campaign(BaseModel):
    campaign_id: str
    organization_id: str
    name: str
    description: Optional[str]
    campaign_type: CampaignType
    status: CampaignStatus
    schedule_type: Optional[ScheduleType]
    scheduled_at: Optional[datetime]
    timezone: str
    audiences: List[CampaignAudience]
    variants: List[CampaignVariant]
    triggers: List[CampaignTrigger]
    holdout_percentage: Decimal
    ab_test: ABTestConfig
    conversion: ConversionConfig
    task_id: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
```

#### Campaign List Response (Pagination)

```python
class CampaignListResponse(BaseModel):
    campaigns: List[Campaign]
    total: int
    limit: int
    offset: int
    has_more: bool
```

### Pagination Pattern

```python
class CampaignQueryRequest(BaseModel):
    status: Optional[List[CampaignStatus]] = None
    campaign_type: Optional[CampaignType] = None
    channel: Optional[ChannelType] = None
    search: Optional[str] = Field(None, description="Search by name")
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    scheduled_after: Optional[datetime] = None
    scheduled_before: Optional[datetime] = None
    tags: Optional[List[str]] = None
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

### Filtering Pattern

```python
async def list_campaigns(self, query: CampaignQueryRequest) -> CampaignListResponse:
    campaigns, total = await self.repository.query_campaigns(
        status=query.status,
        campaign_type=query.campaign_type,
        channel=query.channel,
        search=query.search,
        created_after=query.created_after,
        created_before=query.created_before,
        scheduled_after=query.scheduled_after,
        scheduled_before=query.scheduled_before,
        tags=query.tags,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        limit=query.limit,
        offset=query.offset
    )
    return CampaignListResponse(
        campaigns=campaigns,
        total=total,
        limit=query.limit,
        offset=query.offset,
        has_more=(query.offset + query.limit) < total
    )
```

### API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/health/ready` | Readiness check | No |
| GET | `/health/live` | Liveness probe | No |
| POST | `/api/v1/campaigns` | Create campaign | Yes |
| GET | `/api/v1/campaigns` | List campaigns | Yes |
| GET | `/api/v1/campaigns/{campaign_id}` | Get campaign | Yes |
| PATCH | `/api/v1/campaigns/{campaign_id}` | Update campaign | Yes |
| DELETE | `/api/v1/campaigns/{campaign_id}` | Delete campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/schedule` | Schedule campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/activate` | Activate triggered campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/pause` | Pause campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/resume` | Resume campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/cancel` | Cancel campaign | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/clone` | Clone campaign | Yes |
| GET | `/api/v1/campaigns/{campaign_id}/metrics` | Get metrics | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/variants` | Add variant | Yes |
| PATCH | `/api/v1/campaigns/{campaign_id}/variants/{variant_id}` | Update variant | Yes |
| DELETE | `/api/v1/campaigns/{campaign_id}/variants/{variant_id}` | Delete variant | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/audiences/estimate` | Estimate audience | Yes |
| POST | `/api/v1/campaigns/{campaign_id}/preview` | Preview content | Yes |
| GET | `/api/v1/campaigns/{campaign_id}/executions` | List executions | Yes |
| GET | `/api/v1/campaigns/{campaign_id}/executions/{execution_id}` | Get execution | Yes |
| GET | `/api/v1/campaigns/{campaign_id}/messages` | List messages | Yes |

---

## 8. Event Publishing Pattern

### Published Events

| Event Type | Subject | Trigger | Data |
|------------|---------|---------|------|
| `campaign.created` | `campaign.created` | After campaign creation | campaign_id, name, type, status, created_by, organization_id |
| `campaign.updated` | `campaign.updated` | After campaign update | campaign_id, changed_fields, updated_by |
| `campaign.scheduled` | `campaign.scheduled` | After campaign scheduled | campaign_id, scheduled_at, task_id |
| `campaign.activated` | `campaign.activated` | After triggered campaign activated | campaign_id, activated_at, trigger_count |
| `campaign.started` | `campaign.started` | When execution begins | campaign_id, execution_id, audience_size, holdout_size |
| `campaign.paused` | `campaign.paused` | When campaign paused | campaign_id, paused_by, messages_sent, messages_remaining |
| `campaign.resumed` | `campaign.resumed` | When campaign resumed | campaign_id, resumed_by, messages_remaining |
| `campaign.completed` | `campaign.completed` | When execution finishes | campaign_id, execution_id, total_sent, total_delivered, duration_minutes |
| `campaign.cancelled` | `campaign.cancelled` | When campaign cancelled | campaign_id, cancelled_by, reason, messages_sent_before_cancel |
| `campaign.message.queued` | `campaign.message.queued` | When message queued | campaign_id, execution_id, message_id, user_id, channel_type, variant_id |
| `campaign.message.sent` | `campaign.message.sent` | When message sent | campaign_id, message_id, notification_id, provider_id |
| `campaign.message.delivered` | `campaign.message.delivered` | When delivery confirmed | campaign_id, message_id, delivered_at |
| `campaign.message.opened` | `campaign.message.opened` | When message opened | campaign_id, message_id, opened_at, user_agent |
| `campaign.message.clicked` | `campaign.message.clicked` | When link clicked | campaign_id, message_id, link_id, link_url, clicked_at |
| `campaign.message.converted` | `campaign.message.converted` | When conversion attributed | campaign_id, message_id, conversion_event, conversion_value, attribution_model |
| `campaign.message.bounced` | `campaign.message.bounced` | When message bounces | campaign_id, message_id, bounce_type, reason |
| `campaign.message.unsubscribed` | `campaign.message.unsubscribed` | When user unsubscribes | campaign_id, message_id, user_id, channel_type, reason |
| `campaign.metric.updated` | `campaign.metric.updated` | When metrics aggregated | campaign_id, metric_type, count, rate |

### EventPublisher Class (`events/publishers.py`)

```python
from typing import Any, Dict, Optional
from datetime import datetime
from core.nats_client import NATSEvent

class CampaignEventPublisher:
    """Publisher for campaign service events"""

    def __init__(self, event_bus):
        self.event_bus = event_bus

    async def publish_campaign_created(
        self,
        campaign_id: str,
        organization_id: str,
        name: str,
        campaign_type: str,
        status: str,
        created_by: str
    ) -> bool:
        if not self.event_bus:
            logger.warning("Event bus not available")
            return False

        try:
            event = NATSEvent(
                event_type="campaign.created",
                source="campaign_service",
                data={
                    "campaign_id": campaign_id,
                    "organization_id": organization_id,
                    "name": name,
                    "campaign_type": campaign_type,
                    "status": status,
                    "created_by": created_by,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            await self.event_bus.publish_event(event)
            logger.info(f"Published campaign.created event: {campaign_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish campaign.created: {e}")
            return False

    async def publish_campaign_started(
        self,
        campaign_id: str,
        execution_id: str,
        audience_size: int,
        holdout_size: int
    ) -> bool:
        if not self.event_bus:
            return False

        try:
            event = NATSEvent(
                event_type="campaign.started",
                source="campaign_service",
                data={
                    "campaign_id": campaign_id,
                    "execution_id": execution_id,
                    "audience_size": audience_size,
                    "holdout_size": holdout_size,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            await self.event_bus.publish_event(event)
            return True
        except Exception as e:
            logger.error(f"Failed to publish campaign.started: {e}")
            return False

    async def publish_message_delivered(
        self,
        campaign_id: str,
        message_id: str,
        delivered_at: datetime
    ) -> bool:
        if not self.event_bus:
            return False

        try:
            event = NATSEvent(
                event_type="campaign.message.delivered",
                source="campaign_service",
                data={
                    "campaign_id": campaign_id,
                    "message_id": message_id,
                    "delivered_at": delivered_at.isoformat(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            await self.event_bus.publish_event(event)
            return True
        except Exception as e:
            logger.error(f"Failed to publish campaign.message.delivered: {e}")
            return False

    # Additional publish methods for other events...
```

### Event Payload Models (`events/models.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

class CampaignCreatedEvent(BaseModel):
    campaign_id: str
    organization_id: str
    name: str
    campaign_type: str
    status: str
    created_by: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CampaignStartedEvent(BaseModel):
    campaign_id: str
    execution_id: str
    audience_size: int
    holdout_size: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CampaignCompletedEvent(BaseModel):
    campaign_id: str
    execution_id: str
    total_sent: int
    total_delivered: int
    total_failed: int
    duration_minutes: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageStatusEvent(BaseModel):
    campaign_id: str
    message_id: str
    status: str
    channel_type: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ConversionEvent(BaseModel):
    campaign_id: str
    message_id: str
    user_id: str
    conversion_event: str
    conversion_value: Optional[float] = None
    attribution_model: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### Stream Configuration

```python
class CampaignStreamConfig:
    STREAM_NAME = "campaign-stream"
    SUBJECTS = ["campaign.>"]
    MAX_MESSAGES = 1000000
    CONSUMER_PREFIX = "campaign"
```

---

## 9. Event Subscription Pattern

### Events Subscribed (via NATS)

| Subject Pattern | Handler | Action |
|-----------------|---------|--------|
| `user.created` | `handle_user_created` | Add to welcome campaign audiences |
| `user.deleted` | `handle_user_deleted` | GDPR cleanup, remove from campaigns |
| `user.preferences.updated` | `handle_preferences_updated` | Update channel eligibility |
| `subscription.created` | `handle_subscription_created` | Trigger onboarding campaigns |
| `subscription.upgraded` | `handle_subscription_upgraded` | Trigger upsell thank-you campaigns |
| `subscription.cancelled` | `handle_subscription_cancelled` | Trigger win-back campaigns |
| `order.completed` | `handle_order_completed` | Trigger post-purchase campaigns |
| `notification.delivered` | `handle_notification_delivered` | Update message status |
| `notification.failed` | `handle_notification_failed` | Update message status |
| `notification.opened` | `handle_notification_opened` | Update message status |
| `notification.clicked` | `handle_notification_clicked` | Update message status |
| `task.executed` | `handle_task_executed` | Start scheduled campaign execution |
| `event.stored` | `handle_event_stored` | Evaluate triggered campaigns |

### Event Handlers (`events/handlers.py`)

```python
from typing import Dict, Any
from datetime import datetime

class CampaignEventHandlers:
    """Event handlers for the campaign service"""

    def __init__(
        self,
        campaign_service=None,
        execution_service=None,
        trigger_service=None,
        metrics_service=None
    ):
        self.campaign_service = campaign_service
        self.execution_service = execution_service
        self.trigger_service = trigger_service
        self.metrics_service = metrics_service

    async def handle_task_executed(self, event_data: Dict[str, Any]) -> bool:
        """Handle task.executed events for scheduled campaigns"""
        try:
            config = event_data.get("config", {})
            campaign_id = config.get("campaign_id")

            if not campaign_id:
                logger.warning("task.executed event missing campaign_id")
                return False

            logger.info(f"Starting scheduled campaign execution: {campaign_id}")

            if self.execution_service:
                await self.execution_service.start_execution(campaign_id)

            return True
        except Exception as e:
            logger.error(f"Error handling task.executed: {e}")
            return False

    async def handle_event_stored(self, event_data: Dict[str, Any]) -> bool:
        """Handle event.stored events for triggered campaigns"""
        try:
            event_type = event_data.get("event_type")
            user_id = event_data.get("user_id")

            if not event_type or not user_id:
                return False

            logger.debug(f"Evaluating triggers for event: {event_type}, user: {user_id}")

            if self.trigger_service:
                await self.trigger_service.evaluate_triggers(event_type, event_data)

            return True
        except Exception as e:
            logger.error(f"Error handling event.stored: {e}")
            return False

    async def handle_notification_delivered(self, event_data: Dict[str, Any]) -> bool:
        """Handle notification.delivered events"""
        try:
            notification_id = event_data.get("notification_id")
            metadata = event_data.get("metadata", {})
            campaign_id = metadata.get("campaign_id")
            message_id = metadata.get("message_id")

            if not campaign_id or not message_id:
                return True  # Not a campaign message

            if self.metrics_service:
                await self.metrics_service.record_delivery(
                    campaign_id=campaign_id,
                    message_id=message_id,
                    delivered_at=datetime.utcnow()
                )

            return True
        except Exception as e:
            logger.error(f"Error handling notification.delivered: {e}")
            return False

    async def handle_notification_clicked(self, event_data: Dict[str, Any]) -> bool:
        """Handle notification.clicked events"""
        try:
            metadata = event_data.get("metadata", {})
            campaign_id = metadata.get("campaign_id")
            message_id = metadata.get("message_id")
            link_id = metadata.get("link_id")

            if not campaign_id or not message_id:
                return True

            if self.metrics_service:
                await self.metrics_service.record_click(
                    campaign_id=campaign_id,
                    message_id=message_id,
                    link_id=link_id,
                    clicked_at=datetime.utcnow()
                )

            return True
        except Exception as e:
            logger.error(f"Error handling notification.clicked: {e}")
            return False

    async def handle_user_deleted(self, event_data: Dict[str, Any]) -> bool:
        """Handle user.deleted events for GDPR cleanup"""
        try:
            user_id = event_data.get("user_id")

            if not user_id:
                return False

            logger.info(f"GDPR cleanup for user: {user_id}")

            if self.campaign_service:
                await self.campaign_service.gdpr_cleanup_user(user_id)

            return True
        except Exception as e:
            logger.error(f"Error handling user.deleted: {e}")
            return False
```

### NATS Subscription Setup (in `main.py`)

```python
async def subscribe_to_nats_events():
    """Subscribe to NATS events"""
    if not event_bus:
        logger.warning("Event bus not available, skipping subscriptions")
        return

    handlers = CampaignEventHandlers(
        campaign_service=campaign_service,
        execution_service=execution_service,
        trigger_service=trigger_service,
        metrics_service=metrics_service
    )

    # Subscribe to task service events
    await event_bus.subscribe(
        subject="task.executed.campaign",
        handler=handlers.handle_task_executed,
        durable="campaign-task-handler"
    )

    # Subscribe to event service events (for triggers)
    await event_bus.subscribe(
        subject="event.stored",
        handler=handlers.handle_event_stored,
        durable="campaign-trigger-handler"
    )

    # Subscribe to notification service events
    await event_bus.subscribe(
        subject="notification.delivered",
        handler=handlers.handle_notification_delivered,
        durable="campaign-delivery-handler"
    )
    await event_bus.subscribe(
        subject="notification.failed",
        handler=handlers.handle_notification_failed,
        durable="campaign-failure-handler"
    )
    await event_bus.subscribe(
        subject="notification.opened",
        handler=handlers.handle_notification_opened,
        durable="campaign-open-handler"
    )
    await event_bus.subscribe(
        subject="notification.clicked",
        handler=handlers.handle_notification_clicked,
        durable="campaign-click-handler"
    )

    # Subscribe to account service events
    await event_bus.subscribe(
        subject="user.deleted",
        handler=handlers.handle_user_deleted,
        durable="campaign-gdpr-handler"
    )

    logger.info("Campaign service subscribed to NATS events")
```

---

## 10. Service Discovery Pattern

### Consul Registration (`routes_registry.py`)

```python
SERVICE_ROUTES = [
    # Health endpoints
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Health check"},
    {"path": "/health/ready", "methods": ["GET"], "auth_required": False, "description": "Readiness check"},
    {"path": "/health/live", "methods": ["GET"], "auth_required": False, "description": "Liveness probe"},

    # Campaign CRUD
    {"path": "/api/v1/campaigns", "methods": ["GET", "POST"], "auth_required": True, "description": "List/Create campaigns"},
    {"path": "/api/v1/campaigns/{campaign_id}", "methods": ["GET", "PATCH", "DELETE"], "auth_required": True, "description": "Campaign by ID"},

    # Campaign lifecycle
    {"path": "/api/v1/campaigns/{campaign_id}/schedule", "methods": ["POST"], "auth_required": True, "description": "Schedule campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/activate", "methods": ["POST"], "auth_required": True, "description": "Activate triggered campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/pause", "methods": ["POST"], "auth_required": True, "description": "Pause campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/resume", "methods": ["POST"], "auth_required": True, "description": "Resume campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/cancel", "methods": ["POST"], "auth_required": True, "description": "Cancel campaign"},
    {"path": "/api/v1/campaigns/{campaign_id}/clone", "methods": ["POST"], "auth_required": True, "description": "Clone campaign"},

    # Metrics and analytics
    {"path": "/api/v1/campaigns/{campaign_id}/metrics", "methods": ["GET"], "auth_required": True, "description": "Get campaign metrics"},

    # Variants
    {"path": "/api/v1/campaigns/{campaign_id}/variants", "methods": ["POST"], "auth_required": True, "description": "Add variant"},
    {"path": "/api/v1/campaigns/{campaign_id}/variants/{variant_id}", "methods": ["PATCH", "DELETE"], "auth_required": True, "description": "Variant by ID"},

    # Audiences
    {"path": "/api/v1/campaigns/{campaign_id}/audiences/estimate", "methods": ["POST"], "auth_required": True, "description": "Estimate audience size"},

    # Content preview
    {"path": "/api/v1/campaigns/{campaign_id}/preview", "methods": ["POST"], "auth_required": True, "description": "Preview content"},

    # Executions
    {"path": "/api/v1/campaigns/{campaign_id}/executions", "methods": ["GET"], "auth_required": True, "description": "List executions"},
    {"path": "/api/v1/campaigns/{campaign_id}/executions/{execution_id}", "methods": ["GET"], "auth_required": True, "description": "Get execution"},

    # Messages
    {"path": "/api/v1/campaigns/{campaign_id}/messages", "methods": ["GET"], "auth_required": True, "description": "List messages"},
]

SERVICE_METADATA = {
    "service_name": "campaign_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "marketing-automation", "campaign-management"],
    "capabilities": [
        "campaign_crud",
        "campaign_scheduling",
        "campaign_triggers",
        "ab_testing",
        "multi_channel_delivery",
        "audience_segmentation",
        "conversion_tracking",
        "metrics_analytics",
        "throttling",
        "quiet_hours"
    ]
}

def get_routes_for_consul() -> Dict[str, Any]:
    """Generate compact route metadata for Consul (512 char limit)"""
    health_routes = [r["path"] for r in SERVICE_ROUTES if "health" in r["path"]]
    campaign_routes = [r["path"] for r in SERVICE_ROUTES if "/campaigns" in r["path"] and "health" not in r["path"]]

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/campaigns",
        "health": ",".join(health_routes),
        "campaigns": "|".join(campaign_routes[:10]),
        "methods": "GET,POST,PATCH,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }
```

### Consul Registration in Lifespan

```python
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

## 11. Database Access Pattern

### Repository Pattern (`campaign_repository.py`)

```python
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from core.config_manager import ConfigManager
from core.postgres_client import AsyncPostgresClient

class CampaignRepository:
    """Campaign Repository - using PostgresClient via gRPC"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("campaign_service")

        # Service discovery for PostgreSQL
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        self.db = AsyncPostgresClient(host=host, port=port, user_id="campaign_service")
        self.schema = "campaign"

        # Table names
        self.campaigns_table = "campaigns"
        self.audiences_table = "campaign_audiences"
        self.variants_table = "campaign_variants"
        self.channels_table = "campaign_channels"
        self.triggers_table = "campaign_triggers"
        self.executions_table = "campaign_executions"
        self.messages_table = "campaign_messages"
        self.metrics_table = "campaign_metrics"
        self.conversions_table = "campaign_conversions"
        self.unsubscribes_table = "campaign_unsubscribes"
        self.trigger_history_table = "campaign_trigger_history"

    async def initialize(self):
        """Initialize database connection"""
        # Connection pool is managed by AsyncPostgresClient
        logger.info("Campaign repository initialized")

    async def close(self):
        """Close database connection"""
        # Connection cleanup handled by AsyncPostgresClient
        logger.info("Campaign repository closed")

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.db:
                result = await self.db.query_row("SELECT 1", [], schema=self.schema)
            return result is not None
        except Exception:
            return False
```

### Schema: `campaign`

### Tables

| Table | Purpose |
|-------|---------|
| `campaign.campaigns` | Core campaign entity storage |
| `campaign.campaign_audiences` | Audience segment configuration |
| `campaign.campaign_variants` | A/B test variant configuration |
| `campaign.campaign_channels` | Channel-specific content |
| `campaign.campaign_triggers` | Event trigger configuration |
| `campaign.campaign_executions` | Execution history |
| `campaign.campaign_messages` | Individual message tracking (partitioned) |
| `campaign.campaign_metrics` | Aggregated metrics |
| `campaign.campaign_conversions` | Conversion attribution records |
| `campaign.campaign_unsubscribes` | Unsubscribe tracking |
| `campaign.campaign_trigger_history` | Trigger evaluation history |

### Key Database Operations

```python
async def save_campaign(self, campaign: Campaign) -> Campaign:
    """Save campaign to database"""
    campaign_dict = {
        'campaign_id': campaign.campaign_id,
        'organization_id': campaign.organization_id,
        'name': campaign.name,
        'description': campaign.description,
        'campaign_type': campaign.campaign_type.value,
        'status': campaign.status.value,
        'schedule_type': campaign.schedule_type.value if campaign.schedule_type else None,
        'scheduled_at': campaign.scheduled_at,
        'cron_expression': campaign.cron_expression,
        'timezone': campaign.timezone,
        'holdout_percentage': float(campaign.holdout_percentage),
        'enable_ab_testing': campaign.ab_test.enabled,
        'created_by': campaign.created_by,
        'created_at': campaign.created_at,
        'updated_at': campaign.updated_at,
        'metadata': campaign.metadata,
        'tags': campaign.tags,
    }
    async with self.db:
        await self.db.insert_into(self.campaigns_table, [campaign_dict], schema=self.schema)
    return campaign

async def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
    """Get campaign by ID"""
    query = f'''
        SELECT * FROM {self.schema}.{self.campaigns_table}
        WHERE campaign_id = $1 AND deleted_at IS NULL
    '''
    async with self.db:
        result = await self.db.query_row(query, [campaign_id], schema=self.schema)
    return self._row_to_campaign(result) if result else None

async def query_campaigns(
    self,
    status: Optional[List[str]] = None,
    campaign_type: Optional[str] = None,
    search: Optional[str] = None,
    organization_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Tuple[List[Campaign], int]:
    """Query campaigns with filters"""
    conditions = ["deleted_at IS NULL"]
    params = []
    param_idx = 1

    if organization_id:
        conditions.append(f"organization_id = ${param_idx}")
        params.append(organization_id)
        param_idx += 1

    if status:
        placeholders = ", ".join([f"${param_idx + i}" for i in range(len(status))])
        conditions.append(f"status IN ({placeholders})")
        params.extend(status)
        param_idx += len(status)

    if campaign_type:
        conditions.append(f"campaign_type = ${param_idx}")
        params.append(campaign_type)
        param_idx += 1

    if search:
        conditions.append(f"name ILIKE ${param_idx}")
        params.append(f"{search}%")
        param_idx += 1

    where_clause = " AND ".join(conditions)

    # Count query
    count_query = f'''
        SELECT COUNT(*) as total
        FROM {self.schema}.{self.campaigns_table}
        WHERE {where_clause}
    '''

    # Data query
    query = f'''
        SELECT * FROM {self.schema}.{self.campaigns_table}
        WHERE {where_clause}
        ORDER BY {sort_by} {sort_order}
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    '''
    params.extend([limit, offset])

    async with self.db:
        count_result = await self.db.query_row(count_query, params[:-2], schema=self.schema)
        results = await self.db.query(query, params, schema=self.schema)

    total = count_result.get('total', 0) if count_result else 0
    campaigns = [self._row_to_campaign(row) for row in results]

    return campaigns, total

async def update_campaign_status(
    self,
    campaign_id: str,
    status: str,
    updated_by: str,
    **kwargs
) -> bool:
    """Update campaign status"""
    updates = {
        'status': status,
        'updated_by': updated_by,
        'updated_at': datetime.utcnow(),
        **kwargs
    }

    set_clauses = []
    params = []
    param_idx = 1

    for key, value in updates.items():
        set_clauses.append(f"{key} = ${param_idx}")
        params.append(value)
        param_idx += 1

    params.append(campaign_id)

    query = f'''
        UPDATE {self.schema}.{self.campaigns_table}
        SET {", ".join(set_clauses)}
        WHERE campaign_id = ${param_idx}
    '''

    async with self.db:
        result = await self.db.execute(query, params, schema=self.schema)
    return result > 0
```

### Row to Model Conversion

```python
def _row_to_campaign(self, row: Dict) -> Campaign:
    """Convert database row to Campaign model"""
    # Handle enum fields
    campaign_type = CampaignType(row['campaign_type'])
    status = CampaignStatus(row['status'])
    schedule_type = ScheduleType(row['schedule_type']) if row.get('schedule_type') else None

    # Handle JSON fields
    metadata = row.get('metadata', {})
    if isinstance(metadata, str):
        metadata = json.loads(metadata)

    tags = row.get('tags', [])
    if isinstance(tags, str):
        tags = json.loads(tags)

    return Campaign(
        campaign_id=row['campaign_id'],
        organization_id=row['organization_id'],
        name=row['name'],
        description=row.get('description'),
        campaign_type=campaign_type,
        status=status,
        schedule_type=schedule_type,
        scheduled_at=row.get('scheduled_at'),
        cron_expression=row.get('cron_expression'),
        timezone=row.get('timezone', 'UTC'),
        holdout_percentage=Decimal(str(row.get('holdout_percentage', 0))),
        task_id=row.get('task_id'),
        created_by=row['created_by'],
        created_at=row['created_at'],
        updated_at=row['updated_at'],
        metadata=metadata,
        tags=tags,
        # Load related entities separately
        audiences=[],
        variants=[],
        triggers=[]
    )
```

---

## 12. Client SDK Pattern

### CampaignServiceClient (`client.py`)

```python
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
from core.service_discovery import get_service_discovery

class CampaignServiceClient:
    """Campaign Service HTTP client for use by other services"""

    def __init__(self, base_url: str = None):
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("campaign_service")
            except Exception as e:
                logger.warning(f"Service discovery failed: {e}")
                import os
                self.base_url = os.getenv("CAMPAIGN_SERVICE_URL", "http://localhost:8240")

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

### Client Methods

| Method | Endpoint | Description |
|--------|----------|-------------|
| `create_campaign()` | POST `/api/v1/campaigns` | Create campaign |
| `get_campaign()` | GET `/api/v1/campaigns/{id}` | Get campaign by ID |
| `list_campaigns()` | GET `/api/v1/campaigns` | List campaigns with filters |
| `update_campaign()` | PATCH `/api/v1/campaigns/{id}` | Update campaign |
| `delete_campaign()` | DELETE `/api/v1/campaigns/{id}` | Delete campaign |
| `schedule_campaign()` | POST `/api/v1/campaigns/{id}/schedule` | Schedule campaign |
| `activate_campaign()` | POST `/api/v1/campaigns/{id}/activate` | Activate triggered campaign |
| `pause_campaign()` | POST `/api/v1/campaigns/{id}/pause` | Pause campaign |
| `resume_campaign()` | POST `/api/v1/campaigns/{id}/resume` | Resume campaign |
| `cancel_campaign()` | POST `/api/v1/campaigns/{id}/cancel` | Cancel campaign |
| `clone_campaign()` | POST `/api/v1/campaigns/{id}/clone` | Clone campaign |
| `get_metrics()` | GET `/api/v1/campaigns/{id}/metrics` | Get campaign metrics |
| `add_variant()` | POST `/api/v1/campaigns/{id}/variants` | Add A/B test variant |
| `estimate_audience()` | POST `/api/v1/campaigns/{id}/audiences/estimate` | Estimate audience size |
| `preview_content()` | POST `/api/v1/campaigns/{id}/preview` | Preview rendered content |
| `health_check()` | GET `/health` | Health check |

### Client Implementation

```python
async def create_campaign(
    self,
    name: str,
    campaign_type: str,
    audiences: List[Dict[str, Any]],
    channels: List[Dict[str, Any]],
    schedule_type: Optional[str] = None,
    scheduled_at: Optional[datetime] = None,
    triggers: Optional[List[Dict[str, Any]]] = None,
    holdout_percentage: float = 0,
    **kwargs
) -> Dict[str, Any]:
    """Create a new campaign"""
    payload = {
        "name": name,
        "campaign_type": campaign_type,
        "audiences": audiences,
        "channels": channels,
        "holdout_percentage": holdout_percentage,
        **kwargs
    }

    if schedule_type:
        payload["schedule_type"] = schedule_type
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at.isoformat()
    if triggers:
        payload["triggers"] = triggers

    response = await self.client.post(
        f"{self.base_url}/api/v1/campaigns",
        json=payload
    )
    response.raise_for_status()
    return response.json()

async def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
    """Get campaign by ID"""
    response = await self.client.get(
        f"{self.base_url}/api/v1/campaigns/{campaign_id}"
    )
    response.raise_for_status()
    return response.json()

async def schedule_campaign(
    self,
    campaign_id: str,
    scheduled_at: datetime,
    timezone: str = "UTC"
) -> Dict[str, Any]:
    """Schedule a campaign for execution"""
    response = await self.client.post(
        f"{self.base_url}/api/v1/campaigns/{campaign_id}/schedule",
        json={
            "scheduled_at": scheduled_at.isoformat(),
            "timezone": timezone
        }
    )
    response.raise_for_status()
    return response.json()

async def get_metrics(
    self,
    campaign_id: str,
    breakdown_by: Optional[str] = None
) -> Dict[str, Any]:
    """Get campaign metrics"""
    params = {}
    if breakdown_by:
        params["breakdown_by"] = breakdown_by

    response = await self.client.get(
        f"{self.base_url}/api/v1/campaigns/{campaign_id}/metrics",
        params=params
    )
    response.raise_for_status()
    return response.json()

async def health_check(self) -> Dict[str, Any]:
    """Check service health"""
    response = await self.client.get(f"{self.base_url}/health")
    response.raise_for_status()
    return response.json()
```

### Usage Example

```python
async with CampaignServiceClient() as client:
    # Create campaign
    campaign = await client.create_campaign(
        name="New Year Promotion 2026",
        campaign_type="scheduled",
        audiences=[
            {"segment_type": "include", "segment_id": "seg_premium_users"}
        ],
        channels=[
            {
                "channel_type": "email",
                "email_content": {
                    "subject": "Happy New Year!",
                    "body_text": "Special offer for you..."
                }
            }
        ],
        holdout_percentage=5
    )

    campaign_id = campaign["campaign"]["campaign_id"]

    # Schedule campaign
    await client.schedule_campaign(
        campaign_id=campaign_id,
        scheduled_at=datetime(2026, 1, 1, 9, 0, 0),
        timezone="America/New_York"
    )

    # Get metrics (after execution)
    metrics = await client.get_metrics(
        campaign_id=campaign_id,
        breakdown_by="variant,channel"
    )
    print(f"Sent: {metrics['metrics']['total']['sent']}")
    print(f"Delivered: {metrics['metrics']['total']['delivered']}")
```

---

## Data Models Reference

### Campaign Enums

```python
class CampaignType(str, Enum):
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ScheduleType(str, Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"

class ChannelType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"
    WEBHOOK = "webhook"

class MessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

---

## Background Processing

### Metrics Aggregation Loop

```python
async def metrics_aggregation_loop():
    """Periodically aggregate metrics from pending updates"""
    interval = int(config.get("METRICS_AGGREGATION_INTERVAL", 60))

    while True:
        try:
            if metrics_service:
                await metrics_service.aggregate_pending_metrics()
        except Exception as e:
            logger.error(f"Error in metrics aggregation loop: {e}")
        await asyncio.sleep(interval)
```

### Trigger Evaluation Loop

```python
async def trigger_evaluation_loop():
    """Process queued trigger evaluations"""
    while True:
        try:
            if trigger_service:
                await trigger_service.process_pending_triggers()
        except Exception as e:
            logger.error(f"Error in trigger evaluation loop: {e}")
        await asyncio.sleep(1)  # Check every second
```

### Execution Processor

```python
async def process_campaign_execution(execution_id: str):
    """Process campaign execution in background"""
    try:
        if execution_service:
            await execution_service.process_execution(execution_id)
    except Exception as e:
        logger.error(f"Error processing execution {execution_id}: {e}")
        if execution_service:
            await execution_service.mark_execution_failed(execution_id, str(e))
```

---

## Compliance Checklist

- [x] `main.py` with lifespan management
- [x] `campaign_service.py` with business logic
- [x] `campaign_repository.py` with PostgreSQL via gRPC
- [x] `models.py` with Pydantic models
- [x] `routes_registry.py` for Consul (SERVICE_ROUTES, SERVICE_METADATA)
- [x] `client.py` with CampaignServiceClient SDK
- [x] `factory.py` for dependency injection factory
- [x] `protocols.py` for type safety
- [x] `events/models.py` for event payload models
- [x] `events/publishers.py` for NATS publish (CampaignEventPublisher)
- [x] `events/handlers.py` for NATS subscriptions (CampaignEventHandlers)
- [x] `clients/` directory for external service clients
- [x] Health check endpoints (`/health`, `/health/ready`, `/health/live`)
- [x] ConfigManager usage for configuration
- [x] Service discovery pattern
- [x] Structured logging (setup_service_logger)
- [x] Background processing (metrics aggregation, trigger evaluation)
- [x] Pagination support (limit, offset, has_more)
- [x] Error handling with HTTPException

---

**Version**: 1.0.0
**Last Updated**: 2026-02-02
**Pattern Reference**: `.claude/skills/cdd-system-contract/SKILL.md`
