# Telemetry Service - System Contract

## Overview

This document defines HOW telemetry_service implements the 12 standard CDD patterns. It bridges the Logic Contract (business rules) to actual code implementation.

**Service**: telemetry_service
**Port**: 8217
**Schema**: telemetry
**Version**: 1.0.0

---

## Table of Contents

1. [Architecture Pattern](#1-architecture-pattern)
2. [Dependency Injection Pattern](#2-dependency-injection-pattern)
3. [Event Publishing Pattern](#3-event-publishing-pattern)
4. [Error Handling Pattern](#4-error-handling-pattern)
5. [Client Pattern](#5-client-pattern)
6. [Repository Pattern](#6-repository-pattern)
7. [Service Registration Pattern](#7-service-registration-pattern)
8. [Migration Pattern](#8-migration-pattern)
9. [Lifecycle Pattern](#9-lifecycle-pattern)
10. [Configuration Pattern](#10-configuration-pattern)
11. [Logging Pattern](#11-logging-pattern)
12. [Event Subscription Pattern](#12-event-subscription-pattern)

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/telemetry_service/
├── __init__.py
├── main.py                     # FastAPI app, routes, DI setup, lifespan
├── telemetry_service.py        # Business logic layer
├── telemetry_repository.py     # Data access layer (PostgreSQL gRPC)
├── models.py                   # Pydantic request/response models
├── routes_registry.py          # Consul route registration metadata
├── events/
│   ├── __init__.py
│   ├── models.py               # Event Pydantic models
│   ├── publishers.py           # Event publishing functions
│   └── handlers.py             # Event subscription handlers
└── migrations/
    └── 002_migrate_to_telemetry_schema.sql
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **HTTP/Routes** | `main.py` | Request validation, routing, auth | FastAPI, TelemetryService |
| **Business Logic** | `telemetry_service.py` | Data processing, alerting, validation | Repository, EventBus |
| **Data Access** | `telemetry_repository.py` | SQL queries, time-series storage | AsyncPostgresClient |
| **Events** | `events/` | Publishing/subscribing to NATS events | NATSClient |

### Key Entities

| Entity | Table | Primary Key | Description |
|--------|-------|-------------|-------------|
| TelemetryData | telemetry.telemetry_data | (time, device_id, metric_name) | Time-series data points |
| MetricDefinition | telemetry.metric_definitions | metric_id | Metric schemas/configurations |
| AlertRule | telemetry.alert_rules | rule_id | Alert monitoring rules |
| Alert | telemetry.alerts | alert_id | Triggered alert instances |
| RealTimeSubscription | telemetry.real_time_subscriptions | subscription_id | WebSocket subscriptions |
| AggregatedData | telemetry.aggregated_data | id | Pre-computed aggregations |

---

## 2. Dependency Injection Pattern

### Current Implementation

Telemetry service uses constructor injection for the main service class:

```python
# telemetry_service.py
class TelemetryService:
    """Telemetry service business logic"""

    def __init__(self, event_bus=None, config=None):
        # Initialize repository for PostgreSQL storage
        self.repository = TelemetryRepository(config=config)

        # Event bus for publishing events
        self.event_bus = event_bus

        # In-memory structures for real-time features
        self.real_time_subscribers = {}

        # Configuration
        self.max_batch_size = 1000
        self.max_query_points = 10000
        self.default_retention_days = 90
```

### Protocol Definition (Recommended)

```python
# protocols.py (to be created)
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List
from datetime import datetime

@runtime_checkable
class TelemetryRepositoryProtocol(Protocol):
    """Repository interface for telemetry data access"""

    async def ingest_data_points(
        self, device_id: str, data_points: List[Any]
    ) -> Dict[str, Any]:
        """Ingest telemetry data points"""
        ...

    async def query_telemetry_data(
        self,
        device_id: Optional[str] = None,
        metric_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query telemetry data with filters"""
        ...

    async def create_metric_definition(
        self, metric_def: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create metric definition"""
        ...

    async def create_alert_rule(
        self, rule_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create alert rule"""
        ...

    async def create_alert(
        self, alert_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create triggered alert"""
        ...

    async def get_device_stats(self, device_id: str) -> Dict[str, Any]:
        """Get device telemetry statistics"""
        ...

    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global service statistics"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Event bus interface for NATS publishing"""

    async def publish_event(self, event: Any) -> None:
        """Publish event to NATS"""
        ...

    async def subscribe_to_events(
        self, pattern: str, handler: Any, durable: str
    ) -> None:
        """Subscribe to events"""
        ...

    async def close(self) -> None:
        """Close connection"""
        ...
```

### Factory Implementation (Recommended)

```python
# factory.py (to be created)
from typing import Optional
from .telemetry_service import TelemetryService
from .telemetry_repository import TelemetryRepository
from .protocols import TelemetryRepositoryProtocol, EventBusProtocol


class TelemetryFactory:
    """Factory for creating TelemetryService with dependencies"""

    @staticmethod
    def create_service(
        repository: Optional[TelemetryRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        config=None,
    ) -> TelemetryService:
        """
        Create TelemetryService instance.

        Args:
            repository: Repository implementation (default: real repository)
            event_bus: Event bus implementation (default: real NATS)
            config: Configuration manager

        Returns:
            Configured TelemetryService instance
        """
        if repository is None:
            repository = TelemetryRepository(config=config)

        return TelemetryService(
            event_bus=event_bus,
            config=config,
        )

    @staticmethod
    def create_for_testing(
        mock_repository: TelemetryRepositoryProtocol,
        mock_event_bus: Optional[EventBusProtocol] = None,
    ) -> TelemetryService:
        """Create service with mock dependencies for testing"""
        service = TelemetryService(event_bus=mock_event_bus)
        service.repository = mock_repository
        return service
```

---

## 3. Event Publishing Pattern

### Event Models

Located in `events/models.py`:

```python
# Event Types Published by Telemetry Service
class TelemetryDataReceivedEvent(BaseModel):
    """Published when telemetry data is ingested"""
    device_id: str
    metrics_count: int
    points_count: int
    timestamp: str

class MetricDefinedEvent(BaseModel):
    """Published when metric definition is created"""
    metric_id: str
    name: str
    data_type: str
    metric_type: str
    unit: Optional[str]
    created_by: str
    timestamp: str

class AlertRuleCreatedEvent(BaseModel):
    """Published when alert rule is created"""
    rule_id: str
    name: str
    metric_name: str
    condition: str
    threshold_value: str
    level: str
    enabled: bool
    created_by: str
    timestamp: str

class AlertTriggeredEvent(BaseModel):
    """Published when alert is triggered"""
    alert_id: str
    rule_id: str
    rule_name: str
    device_id: str
    metric_name: str
    level: str
    current_value: str
    threshold_value: str
    timestamp: str

class AlertResolvedEvent(BaseModel):
    """Published when alert is resolved"""
    alert_id: str
    rule_id: str
    rule_name: str
    device_id: str
    metric_name: str
    level: str
    resolved_by: str
    resolution_note: Optional[str]
    timestamp: str
```

### Event Publishing Functions

Located in `events/publishers.py`:

```python
async def publish_telemetry_data_received(
    event_bus,
    device_id: str,
    metrics_count: int,
    points_count: int
) -> bool:
    """Publish telemetry.data.received event"""
    event_data = TelemetryDataReceivedEvent(
        device_id=device_id,
        metrics_count=metrics_count,
        points_count=points_count,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    event = Event(
        event_type=EventType.TELEMETRY_DATA_RECEIVED,
        source=ServiceSource.TELEMETRY_SERVICE,
        data=event_data.model_dump(mode='json')
    )

    await event_bus.publish_event(event)
    return True

# Similar functions for:
# - publish_metric_defined()
# - publish_alert_rule_created()
# - publish_alert_triggered()
# - publish_alert_resolved()
```

### Event Subject Mapping

| Event Type | NATS Subject | When Published |
|------------|--------------|----------------|
| TELEMETRY_DATA_RECEIVED | telemetry_service.telemetry.data.received | After successful data ingestion |
| METRIC_DEFINED | telemetry_service.metric.defined | After metric definition created |
| ALERT_RULE_CREATED | telemetry_service.alert.rule.created | After alert rule created |
| ALERT_TRIGGERED | telemetry_service.alert.triggered | When alert condition met |
| ALERT_RESOLVED | telemetry_service.alert.resolved | When alert is resolved |

---

## 4. Error Handling Pattern

### Custom Exceptions (Implicit)

The service uses standard Python exceptions with FastAPI HTTPException:

```python
# Error patterns in telemetry_service.py and main.py

# Not Found - 404
raise HTTPException(status_code=404, detail="Metric definition not found")
raise HTTPException(status_code=404, detail="Alert rule not found")
raise HTTPException(status_code=404, detail="No data found")
raise HTTPException(status_code=404, detail="Device not found or no telemetry data")

# Bad Request - 400
raise HTTPException(status_code=400, detail="Failed to create metric definition")
raise HTTPException(status_code=400, detail="Failed to ingest data")

# Unauthorized - 401
raise HTTPException(status_code=401, detail="Authentication required")
raise HTTPException(status_code=401, detail="Invalid token")
raise HTTPException(status_code=401, detail="API key verification failed")

# Service Unavailable - 503
raise HTTPException(status_code=503, detail="Authentication service unavailable")

# Internal Server Error - 500
raise HTTPException(status_code=500, detail=str(e))
```

### Error Response Format

```json
{
    "detail": "Error message describing what went wrong"
}
```

### Exception Handling Pattern

```python
# Standard try-except pattern used throughout
@app.post("/api/v1/telemetry/metrics")
async def create_metric_definition(
    request: MetricDefinitionRequest,
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    try:
        metric = await microservice.service.create_metric_definition(
            user_context["user_id"],
            request.model_dump()
        )
        if metric:
            return metric
        raise HTTPException(status_code=400, detail="Failed to create metric definition")
    except Exception as e:
        logger.error(f"Error creating metric definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 5. Client Pattern

### Authentication Client (Inline in main.py)

```python
# Located in get_user_context dependency

async def get_user_context(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    x_internal_call: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Get user context with authentication"""

    # Internal service-to-service calls bypass auth
    if x_internal_call == "true":
        return {
            "user_id": "internal_service",
            "organization_id": None,
            "role": "service"
        }

    # Use ConfigManager for service discovery
    auth_host, auth_port = config_manager.discover_service(
        service_name='auth_service',
        default_host='localhost',
        default_port=8201,
        env_host_key='AUTH_SERVICE_HOST',
        env_port_key='AUTH_SERVICE_PORT'
    )
    auth_service_url = f"http://{auth_host}:{auth_port}"

    # Verify JWT token
    if authorization:
        response = requests.post(
            f"{auth_service_url}/api/v1/auth/verify-token",
            json={"token": token}
        )
        # ... process response

    # Verify API key
    elif x_api_key:
        response = requests.post(
            f"{auth_service_url}/api/v1/auth/verify-api-key",
            json={"api_key": x_api_key}
        )
        # ... process response
```

### Service Dependencies

| Dependency | Purpose | Discovery Method |
|------------|---------|------------------|
| auth_service | Token/API key validation | ConfigManager.discover_service() |
| postgres_grpc_service | Database operations | ConfigManager.discover_service() |
| nats | Event publishing/subscription | ConfigManager (NATS_URL) |

---

## 6. Repository Pattern

### Repository Implementation

Located in `telemetry_repository.py`:

```python
class TelemetryRepository:
    """Repository for telemetry operations using PostgresClient"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("telemetry_service")

        # Discover PostgreSQL service
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="telemetry_service"
        )
        self.schema = "telemetry"
```

### Core Repository Methods

| Method | Table | Operation |
|--------|-------|-----------|
| `ingest_data_points()` | telemetry_data | INSERT with upsert |
| `query_telemetry_data()` | telemetry_data | SELECT with filters |
| `create_metric_definition()` | metric_definitions | INSERT |
| `get_metric_definition()` | metric_definitions | SELECT by name |
| `list_metric_definitions()` | metric_definitions | SELECT with pagination |
| `create_alert_rule()` | alert_rules | INSERT |
| `get_alert_rules()` | alert_rules | SELECT with filters |
| `update_alert_rule()` | alert_rules | UPDATE |
| `create_alert()` | alerts | INSERT |
| `get_alerts()` | alerts | SELECT with filters |
| `update_alert()` | alerts | UPDATE |
| `get_device_stats()` | telemetry_data | COUNT/DISTINCT queries |
| `get_global_stats()` | multiple | Aggregation queries |

### Data Point Ingestion Pattern

```python
async def ingest_single_point(self, device_id: str, data_point: TelemetryDataPoint) -> bool:
    """Ingest a single telemetry data point"""

    # Determine value field based on data type
    value_numeric = None
    value_string = None
    value_boolean = None
    value_json = None

    if isinstance(data_point.value, (int, float)):
        value_numeric = float(data_point.value)
    elif isinstance(data_point.value, str):
        value_string = data_point.value
    elif isinstance(data_point.value, bool):
        value_boolean = data_point.value
    elif isinstance(data_point.value, dict):
        value_json = data_point.value

    query = '''
        INSERT INTO telemetry.telemetry_data (
            time, device_id, metric_name, value_numeric, value_string,
            value_boolean, value_json, unit, tags, metadata, quality
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (time, device_id, metric_name) DO UPDATE
        SET value_numeric = EXCLUDED.value_numeric,
            value_string = EXCLUDED.value_string,
            ...
    '''
```

---

## 7. Service Registration Pattern

### Routes Registry

Located in `routes_registry.py`:

```python
SERVICE_ROUTES = [
    # Health checks
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Basic health check"},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False, "description": "Detailed health check"},

    # Data ingestion
    {"path": "/api/v1/devices/{device_id}/telemetry", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/devices/{device_id}/telemetry/batch", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/telemetry/bulk", "methods": ["POST"], "auth_required": True},

    # Metric management
    {"path": "/api/v1/metrics", "methods": ["GET", "POST"], "auth_required": True},
    {"path": "/api/v1/metrics/{metric_name}", "methods": ["GET", "DELETE"], "auth_required": True},

    # Data queries
    {"path": "/api/v1/query", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/devices/{device_id}/metrics/{metric_name}/latest", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/devices/{device_id}/metrics", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/devices/{device_id}/metrics/{metric_name}/range", "methods": ["GET"], "auth_required": True},

    # Aggregation
    {"path": "/api/v1/aggregated", "methods": ["GET"], "auth_required": True},

    # Alert management
    {"path": "/api/v1/alerts/rules", "methods": ["GET", "POST"], "auth_required": True},
    {"path": "/api/v1/alerts/rules/{rule_id}", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/alerts/rules/{rule_id}/enable", "methods": ["PUT"], "auth_required": True},
    {"path": "/api/v1/alerts", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/alerts/{alert_id}/acknowledge", "methods": ["PUT"], "auth_required": True},
    {"path": "/api/v1/alerts/{alert_id}/resolve", "methods": ["PUT"], "auth_required": True},

    # Statistics
    {"path": "/api/v1/devices/{device_id}/stats", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/stats", "methods": ["GET"], "auth_required": True},

    # Real-time streaming
    {"path": "/api/v1/subscribe", "methods": ["POST", "DELETE"], "auth_required": True},
    {"path": "/ws/telemetry/{subscription_id}", "methods": ["WS"], "auth_required": True},

    # Export
    {"path": "/api/v1/export/csv", "methods": ["GET"], "auth_required": True},
]

SERVICE_METADATA = {
    "service_name": "telemetry_service",
    "version": "1.0.0",
    "tags": ["v1", "iot-microservice", "telemetry", "monitoring"],
    "capabilities": [
        "data_ingestion",
        "metric_definitions",
        "time_series_queries",
        "data_aggregation",
        "alert_management",
        "real_time_streaming",
        "statistical_analysis",
        "data_export"
    ]
}
```

### Consul Registration

```python
# In main.py TelemetryMicroservice.initialize()

if config.consul_enabled:
    route_meta = get_routes_for_consul()

    consul_meta = {
        'version': SERVICE_METADATA['version'],
        'capabilities': ','.join(SERVICE_METADATA['capabilities']),
        **route_meta
    }

    self.consul_registry = ConsulRegistry(
        service_name=SERVICE_METADATA['service_name'],
        service_port=config.service_port,
        consul_host=config.consul_host,
        consul_port=config.consul_port,
        tags=SERVICE_METADATA['tags'],
        meta=consul_meta,
        health_check_type='http'
    )
    self.consul_registry.register()
```

---

## 8. Migration Pattern

### Migration File Structure

```
microservices/telemetry_service/migrations/
└── 002_migrate_to_telemetry_schema.sql
```

### Schema Definition

```sql
-- Create telemetry schema
CREATE SCHEMA IF NOT EXISTS telemetry;

-- Main tables
CREATE TABLE telemetry.metric_definitions (
    id SERIAL PRIMARY KEY,
    metric_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    data_type VARCHAR(20) NOT NULL,
    metric_type VARCHAR(20) NOT NULL DEFAULT 'gauge',
    unit VARCHAR(20),
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    retention_days INTEGER DEFAULT 90,
    aggregation_interval INTEGER DEFAULT 60,
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL
);

CREATE TABLE telemetry.telemetry_data (
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value_numeric DOUBLE PRECISION,
    value_string TEXT,
    value_boolean BOOLEAN,
    value_json JSONB,
    unit VARCHAR(20),
    tags JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    quality INTEGER DEFAULT 100,
    PRIMARY KEY (time, device_id, metric_name)
);

CREATE TABLE telemetry.alert_rules (
    rule_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    condition VARCHAR(500) NOT NULL,
    threshold_value TEXT NOT NULL,
    level VARCHAR(20) NOT NULL DEFAULT 'warning',
    device_ids TEXT[],
    enabled BOOLEAN DEFAULT TRUE,
    total_triggers INTEGER DEFAULT 0,
    last_triggered TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL
);

CREATE TABLE telemetry.alerts (
    alert_id VARCHAR(64) NOT NULL UNIQUE,
    rule_id VARCHAR(64) NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    message TEXT NOT NULL,
    current_value TEXT NOT NULL,
    threshold_value TEXT NOT NULL,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);
```

### Key Indexes

```sql
-- Time-series query optimization
CREATE INDEX idx_telemetry_data_device_id ON telemetry.telemetry_data(device_id, time DESC);
CREATE INDEX idx_telemetry_data_metric_name ON telemetry.telemetry_data(metric_name, time DESC);
CREATE INDEX idx_telemetry_data_device_metric ON telemetry.telemetry_data(device_id, metric_name, time DESC);

-- Alert query optimization
CREATE INDEX idx_alerts_status ON telemetry.alerts(status);
CREATE INDEX idx_alerts_device_status ON telemetry.alerts(device_id, status);
CREATE INDEX idx_alerts_active ON telemetry.alerts(status) WHERE status = 'active';
```

---

## 9. Lifecycle Pattern

### Microservice Class

```python
class TelemetryMicroservice:
    """Telemetry microservice core class"""

    def __init__(self):
        self.service = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self, event_bus=None):
        """Initialize the microservice"""
        self.event_bus = event_bus

        # Create service instance
        self.service = TelemetryService(event_bus=event_bus, config=config_manager)

        # Consul registration
        if config.consul_enabled:
            self.consul_registry = ConsulRegistry(...)
            self.consul_registry.register()

    async def shutdown(self):
        """Shutdown the microservice"""
        # Consul deregistration
        if self.consul_registry:
            self.consul_registry.deregister()

        # Close event bus
        if self.event_bus:
            await self.event_bus.close()
```

### FastAPI Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""

    # Startup
    event_bus = None
    try:
        # 1. Initialize NATS event bus
        event_bus = await get_event_bus("telemetry_service")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")

    # 2. Initialize microservice
    await microservice.initialize(event_bus=event_bus)

    # 3. Set up event subscriptions
    if event_bus:
        telemetry_repo = TelemetryRepository()
        event_handler = TelemetryEventHandler(telemetry_repo)

        # Subscribe to device.deleted events
        await event_bus.subscribe_to_events(
            pattern="device_service.device.deleted",
            handler=event_handler.handle_event,
            durable="telemetry_device_deleted"
        )

        # Subscribe to user.deleted events
        await event_bus.subscribe_to_events(
            pattern="account_service.user.deleted",
            handler=event_handler.handle_event,
            durable="telemetry_user_deleted"
        )

    yield  # Application runs

    # Shutdown
    await microservice.shutdown()
```

### Startup Sequence

1. Initialize NATS event bus connection
2. Initialize microservice (service, repository, consul)
3. Set up event subscriptions
4. Start FastAPI server

### Shutdown Sequence

1. Deregister from Consul
2. Close event bus connection
3. Log shutdown complete

---

## 10. Configuration Pattern

### ConfigManager Usage

```python
from core.config_manager import ConfigManager

# Initialize at module level
config_manager = ConfigManager("telemetry_service")
config = config_manager.get_service_config()

# Available config properties
config.service_name      # "telemetry_service"
config.service_port      # 8217
config.service_host      # "0.0.0.0"
config.debug             # True/False
config.log_level         # "INFO"
config.consul_enabled    # True/False
config.consul_host       # "consul"
config.consul_port       # 8500
```

### Service Discovery

```python
# Discovering auth_service
auth_host, auth_port = config_manager.discover_service(
    service_name='auth_service',
    default_host='localhost',
    default_port=8201,
    env_host_key='AUTH_SERVICE_HOST',
    env_port_key='AUTH_SERVICE_PORT'
)

# Discovering postgres_grpc
host, port = config.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061,
    env_host_key='POSTGRES_HOST',
    env_port_key='POSTGRES_PORT'
)
```

### Service Port

| Service | Port |
|---------|------|
| telemetry_service | 8217 |

---

## 11. Logging Pattern

### Logger Setup

```python
from core.logger import setup_service_logger

# Setup at module level
app_logger = setup_service_logger("telemetry_service")
logger = app_logger  # for backward compatibility
```

### Logging Usage

```python
# Info level - successful operations
logger.info("Telemetry service initialized")
logger.info(f"Ingested {result['ingested_count']}/{len(data_points)} data points for device {device_id}")
logger.info(f"Published telemetry.data.received event for device {device_id}")

# Warning level - non-critical issues
logger.warning(f"Failed to initialize event bus: {e}")
logger.warning(f"Validation warning for {device_id}:{data_point.metric_name}: {e}")

# Error level - failures
logger.error(f"Error ingesting single data point: {e}")
logger.error(f"Error creating metric definition: {e}")
logger.error(f"Auth service communication error: {e}")

# Debug level - detailed tracing
logger.debug(f"Received event: {event_type}")
logger.debug(f"Real-time data sent to subscription {sub_id}")
```

### Log Context Pattern

```python
# Include relevant context in log messages
logger.info(f"Alert rule created: {rule_data['name']}")
logger.warning(f"Alert triggered: {rule.name} for device {device_id}")
logger.info(f"Disabled {disabled_count} alert rules for deleted device {device_id}")
```

---

## 12. Event Subscription Pattern

### Event Handler Class

Located in `events/handlers.py`:

```python
class TelemetryEventHandler:
    """Handle events for Telemetry Service"""

    def __init__(self, telemetry_repository):
        self.telemetry_repo = telemetry_repository

    async def handle_device_deleted(self, event_data: Dict[str, Any]) -> bool:
        """Handle device.deleted event"""
        device_id = event_data.get('device_id')
        if not device_id:
            return False

        # Disable alert rules for this device
        disabled_count = await self.telemetry_repo.disable_device_alert_rules(device_id)
        logger.info(f"Disabled {disabled_count} alert rules for deleted device {device_id}")
        return True

    async def handle_user_deleted(self, event_data: Dict[str, Any]) -> bool:
        """Handle user.deleted event"""
        user_id = event_data.get('user_id')
        if not user_id:
            return False

        # Disable alert rules and anonymize data
        disabled_count = await self.telemetry_repo.disable_user_alert_rules(user_id)
        await self.telemetry_repo.anonymize_user_telemetry(user_id)
        return True

    async def handle_event(self, event) -> bool:
        """Route events to appropriate handlers"""
        event_type = event.type
        event_data = event.data

        if event_type == "device.deleted":
            return await self.handle_device_deleted(event_data)
        elif event_type == "user.deleted":
            return await self.handle_user_deleted(event_data)
        return False

    def get_subscriptions(self) -> List[str]:
        """Get list of event types to subscribe to"""
        return [
            "device.deleted",
            "user.deleted",
        ]
```

### Subscription Registration

```python
# In lifespan()
if event_bus:
    telemetry_repo = TelemetryRepository()
    event_handler = TelemetryEventHandler(telemetry_repo)

    await event_bus.subscribe_to_events(
        pattern="device_service.device.deleted",
        handler=event_handler.handle_event,
        durable="telemetry_device_deleted"
    )

    await event_bus.subscribe_to_events(
        pattern="account_service.user.deleted",
        handler=event_handler.handle_event,
        durable="telemetry_user_deleted"
    )
```

### Event Subscription Table

| Source Service | Event Type | Handler | Action |
|----------------|------------|---------|--------|
| device_service | device.deleted | handle_device_deleted | Disable device alert rules |
| account_service | user.deleted | handle_user_deleted | Disable rules, anonymize data |

---

## System Contract Checklist

### Architecture (Section 1)
- [x] Service follows layer structure (main, service, repository, events)
- [x] Clear separation of concerns between layers
- [x] No circular dependencies

### Dependency Injection (Section 2)
- [ ] `protocols.py` defines all dependency interfaces (TO BE CREATED)
- [ ] `factory.py` creates service with DI (TO BE CREATED)
- [x] Service constructor accepts injected dependencies
- [x] Event bus injected via constructor

### Event Publishing (Section 3)
- [x] Event models defined in `events/models.py`
- [x] 5 event types published
- [x] Events published after successful operations
- [x] Timestamps included in all events

### Error Handling (Section 4)
- [x] HTTPException used for API errors
- [x] Consistent 4xx/5xx status code mapping
- [x] Errors logged with context

### Client Pattern (Section 5)
- [x] Auth service integration via requests
- [x] Service discovery via ConfigManager
- [x] X-Internal-Call header supported

### Repository Pattern (Section 6)
- [x] CRUD methods implemented for all entities
- [x] Time-series data ingestion with upsert
- [x] Query filters and pagination
- [x] Statistics aggregation methods

### Service Registration (Section 7)
- [x] `routes_registry.py` defines all routes (25 routes)
- [x] SERVICE_METADATA with version and capabilities
- [x] Consul registration on startup
- [x] Consul deregistration on shutdown

### Migration Pattern (Section 8)
- [x] `migrations/` folder with SQL files
- [x] Schema creation (CREATE SCHEMA IF NOT EXISTS telemetry)
- [x] Indexes for common queries
- [x] Column comments for documentation

### Lifecycle Pattern (Section 9)
- [x] TelemetryMicroservice class with initialize/shutdown
- [x] FastAPI lifespan context manager
- [x] Event bus initialization
- [x] Subscription setup in startup

### Configuration Pattern (Section 10)
- [x] ConfigManager usage at module level
- [x] Service port: 8217
- [x] Service discovery for dependencies

### Logging Pattern (Section 11)
- [x] setup_service_logger usage
- [x] Info/Warning/Error levels used appropriately
- [x] Context included in log messages

### Event Subscription (Section 12)
- [x] `events/handlers.py` with handler class
- [x] handle_event() routes to specific handlers
- [x] Subscriptions registered in lifespan
- [x] 2 event types consumed

---

## Implementation Status

| Pattern | Status | Notes |
|---------|--------|-------|
| Architecture | COMPLETE | Standard layer structure |
| Dependency Injection | PARTIAL | protocols.py and factory.py need creation |
| Event Publishing | COMPLETE | 5 event types |
| Error Handling | COMPLETE | HTTPException pattern |
| Client Pattern | COMPLETE | Auth service integration |
| Repository Pattern | COMPLETE | AsyncPostgresClient |
| Service Registration | COMPLETE | Consul integration |
| Migration Pattern | COMPLETE | SQL migrations |
| Lifecycle Pattern | COMPLETE | Lifespan manager |
| Configuration Pattern | COMPLETE | ConfigManager |
| Logging Pattern | COMPLETE | Structured logging |
| Event Subscription | COMPLETE | 2 event handlers |

---

## Reference Files

- **Main Entry**: `microservices/telemetry_service/main.py`
- **Business Logic**: `microservices/telemetry_service/telemetry_service.py`
- **Repository**: `microservices/telemetry_service/telemetry_repository.py`
- **Models**: `microservices/telemetry_service/models.py`
- **Events**: `microservices/telemetry_service/events/`
- **Routes**: `microservices/telemetry_service/routes_registry.py`
- **Migrations**: `microservices/telemetry_service/migrations/`
- **Data Contract**: `tests/contracts/telemetry_service/data_contract.py`
- **Logic Contract**: `tests/contracts/telemetry_service/logic_contract.md`
