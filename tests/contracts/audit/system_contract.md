# Audit Service - System Contract (Layer 6)

## Overview

This document defines HOW audit_service implements the 12 standard system patterns. It bridges the Logic Contract (business rules) to actual code implementation.

**Service**: audit_service
**Port**: 8204
**Category**: Governance Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/audit_service/
├── __init__.py
├── main.py                 # FastAPI app, routes, DI setup, lifespan
├── audit_service.py        # Business logic layer
├── audit_repository.py     # Data access layer (AsyncPostgresClient)
├── models.py               # Pydantic models (AuditEvent, SecurityEvent, etc.)
├── protocols.py            # DI interfaces (Protocol classes)
├── factory.py              # DI factory (create_audit_service)
├── routes_registry.py      # Consul route metadata
└── events/
    ├── __init__.py
    ├── models.py           # Event Pydantic models (AuditEventRecordedEventData)
    └── handlers.py         # NATS event handlers (AuditEventHandlers)
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, request validation, DI wiring | FastAPI, AuditService |
| **Service** | `audit_service.py` | Business logic, event orchestration | Repository, EventBus |
| **Repository** | `audit_repository.py` | Data access, SQL queries | AsyncPostgresClient |
| **Events** | `events/handlers.py` | NATS subscription processing | AuditService |
| **Models** | `models.py` | Pydantic schemas, enums | pydantic |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event subscription (wildcard) | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
"""
Audit Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

from .models import AuditEvent, SecurityEvent, EventType, EventSeverity


# Custom exceptions - defined here to avoid importing repository
class AuditNotFoundError(Exception):
    """Audit event not found error"""
    pass


class AuditValidationError(Exception):
    """Audit validation error"""
    pass


class AuditServiceError(Exception):
    """Base exception for audit service errors"""
    pass


@runtime_checkable
class AuditRepositoryProtocol(Protocol):
    """
    Interface for Audit Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...

    async def create_audit_event(self, event: AuditEvent) -> Optional[AuditEvent]:
        """Create audit event"""
        ...

    async def get_audit_events(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """Get audit events list"""
        ...

    async def query_audit_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events"""
        ...

    async def get_user_activities(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user activities"""
        ...

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get user activity summary"""
        ...

    async def create_security_event(self, security_event: SecurityEvent) -> Optional[SecurityEvent]:
        """Create security event"""
        ...

    async def get_security_events(
        self,
        days: int = 7,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get security events"""
        ...

    async def get_event_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get event statistics"""
        ...

    async def cleanup_old_events(self, retention_days: int = 365) -> int:
        """Cleanup old events"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...
```

### Factory Implementation (`factory.py`)

```python
"""
Audit Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules (repository).

Usage:
    from .factory import create_audit_service
    service = create_audit_service(config)
"""
from typing import Optional

from core.config_manager import ConfigManager
from .audit_service import AuditService


def create_audit_service(
    config: Optional[ConfigManager] = None,
) -> AuditService:
    """
    Create AuditService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Optional ConfigManager instance

    Returns:
        AuditService: Configured service instance with real repository
    """
    # Import real repository here (not at module level)
    from .audit_repository import AuditRepository

    repository = AuditRepository(config=config)

    return AuditService(
        repository=repository,
    )
```

### Service Constructor Pattern

```python
class AuditService:
    """
    Audit business logic layer.

    All dependencies injected via constructor for testability.
    """

    def __init__(
        self,
        repository: AuditRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ):
        self.repository = repository
        self.event_bus = event_bus
```

### Testing with Mocks

```python
# In tests, use mock dependencies:
from unittest.mock import AsyncMock

mock_repository = AsyncMock(spec=AuditRepositoryProtocol)
mock_event_bus = AsyncMock(spec=EventBusProtocol)

service = AuditService(
    repository=mock_repository,
    event_bus=mock_event_bus,
)
```

---

## 3. Event Publishing Pattern

### Event Model Definition (`events/models.py`)

```python
"""
Audit Service Event Models

Event data models for audit-related events.
Note: Audit service primarily consumes events from other services.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AuditEventRecordedEventData(BaseModel):
    """
    Event: audit.event_recorded
    Triggered when a critical audit event is recorded
    """

    event_id: str = Field(..., description="Audit event ID")
    event_type: str = Field(..., description="Event type")
    category: str = Field(..., description="Audit category")
    severity: str = Field(..., description="Event severity")
    user_id: Optional[str] = Field(None, description="User ID if applicable")
    action: str = Field(..., description="Action performed")
    success: bool = Field(..., description="Whether action succeeded")
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
```

### Published Events

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `audit.event_recorded` | `audit.event.recorded` | Critical/security event logged | AuditEventRecordedEventData |

### Publishing Flow

```python
# In audit_service.py
async def log_event(self, request: AuditEventCreateRequest) -> Optional[AuditEventResponse]:
    # 1. Create audit event in database
    event = await self.repository.create_audit_event(audit_event)

    # 2. Publish event for critical/high severity
    if event and event.severity in [EventSeverity.CRITICAL, EventSeverity.HIGH]:
        if self.event_bus:
            await self.event_bus.publish_event(
                AuditEventRecordedEventData(
                    event_id=event.id,
                    event_type=event.event_type.value,
                    category=event.category.value,
                    severity=event.severity.value,
                    user_id=event.user_id,
                    action=event.action,
                    success=event.success,
                )
            )

    return response
```

---

## 4. Error Handling Pattern

### Custom Exceptions (`protocols.py`)

```python
class AuditNotFoundError(Exception):
    """Audit event not found error"""
    pass


class AuditValidationError(Exception):
    """Audit validation error"""
    pass


class AuditServiceError(Exception):
    """Base exception for audit service errors"""
    pass
```

### HTTP Error Mapping (`main.py`)

```python
# Exception to HTTP status mapping
EXCEPTION_STATUS_MAP = {
    AuditNotFoundError: 404,
    AuditValidationError: 422,
    AuditServiceError: 500,
}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )
```

### Error Response Format

```json
{
  "detail": "Error message description",
  "status_code": 422
}
```

### HTTP Status Code Mapping

| Exception | HTTP Status | Error Type |
|-----------|-------------|------------|
| AuditNotFoundError | 404 | NOT_FOUND |
| AuditValidationError | 422 | VALIDATION_ERROR |
| AuditServiceError | 500 | INTERNAL_ERROR |
| HTTPException | varies | varies |

---

## 5. Client Pattern (Sync Communication)

### Note on Audit Service Clients

Audit service is primarily a **consumer** of events, not a caller of other services. It does not have external service clients. However, the pattern for adding clients would be:

```python
# microservices/audit_service/clients/__init__.py
"""
Service Clients - Export all client classes

Note: Audit service currently has no external service clients.
It receives data via NATS events from all services.
"""

# If needed in future:
# from .account_client import AccountClient
# __all__ = ["AccountClient"]
```

### Service Discovery Pattern (if needed)

```python
import httpx
from typing import Optional, Dict, Any
import os


class AccountClient:
    """Async client for account_service (example)"""

    def __init__(self, base_url: Optional[str] = None):
        self._base_url = base_url or os.getenv(
            "ACCOUNT_SERVICE_URL",
            "http://localhost:8201"
        )
        self._client: Optional[httpx.AsyncClient] = None

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

    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        client = await self._get_client()
        response = await client.get(f"/api/v1/accounts/{account_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
```

---

## 6. Repository Pattern (Database Access)

### Repository Implementation (`audit_repository.py`)

```python
"""
Audit Repository - Async Version

Data access layer for audit service using AsyncPostgresClient.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    AuditEvent, UserActivity, SecurityEvent, ComplianceReport,
    EventType, EventSeverity, EventStatus, AuditCategory
)


class AuditRepository:
    """Audit data repository - AsyncPostgresClient"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("audit_service")

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
            user_id="audit_service"
        )
        self.schema = "audit"
        self.audit_events_table = "audit_events"
```

### Database Schema

| Field | Type | Description |
|-------|------|-------------|
| event_id | VARCHAR(255) | Primary key |
| event_type | VARCHAR(50) | Event type enum value |
| event_category | VARCHAR(50) | Audit category |
| event_severity | VARCHAR(20) | Severity level |
| event_status | VARCHAR(20) | Status (pending, processed, etc.) |
| user_id | VARCHAR(255) | Acting user ID |
| organization_id | VARCHAR(255) | Organization context |
| session_id | VARCHAR(255) | Session identifier |
| ip_address | VARCHAR(50) | Client IP |
| user_agent | TEXT | Client user agent |
| action | VARCHAR(255) | Action performed |
| resource_type | VARCHAR(100) | Resource type |
| resource_id | VARCHAR(255) | Resource identifier |
| resource_name | VARCHAR(255) | Resource name |
| metadata | JSONB | Additional metadata |
| tags | TEXT[] | Event tags |
| event_timestamp | TIMESTAMPTZ | Event occurrence time |
| created_at | TIMESTAMPTZ | Record creation time |

### Key Repository Methods

| Method | Purpose | SQL Operation |
|--------|---------|---------------|
| `create_audit_event()` | Log new audit event | INSERT |
| `get_audit_events()` | List events with filters | SELECT |
| `query_audit_events()` | Complex query | SELECT |
| `get_user_activities()` | User-specific events | SELECT WHERE user_id |
| `get_user_activity_summary()` | Aggregated stats | SELECT COUNT, MAX |
| `get_security_events()` | Security events only | SELECT WHERE type |
| `cleanup_old_events()` | Data retention | DELETE WHERE timestamp |

---

## 7. Service Registration Pattern (Consul)

### Routes Registry (`routes_registry.py`)

```python
"""
Audit Service Routes Registry
Defines all API routes for Consul service registration
"""
from typing import List, Dict, Any


SERVICE_ROUTES = [
    # Health checks
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Basic health check"},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False, "description": "Detailed health check"},

    # Service info
    {"path": "/api/v1/audit/info", "methods": ["GET"], "auth_required": False, "description": "Service information"},
    {"path": "/api/v1/audit/stats", "methods": ["GET"], "auth_required": True, "description": "Service statistics"},

    # Audit event management
    {"path": "/api/v1/audit/events", "methods": ["GET", "POST"], "auth_required": True, "description": "List/create audit events"},
    {"path": "/api/v1/audit/events/query", "methods": ["POST"], "auth_required": True, "description": "Query audit events"},
    {"path": "/api/v1/audit/events/batch", "methods": ["POST"], "auth_required": True, "description": "Batch log events"},

    # User activity tracking
    {"path": "/api/v1/audit/users/{user_id}/activities", "methods": ["GET"], "auth_required": True, "description": "Get user activities"},
    {"path": "/api/v1/audit/users/{user_id}/summary", "methods": ["GET"], "auth_required": True, "description": "User activity summary"},

    # Security event management
    {"path": "/api/v1/audit/security/alerts", "methods": ["POST"], "auth_required": True, "description": "Create security alert"},
    {"path": "/api/v1/audit/security/events", "methods": ["GET"], "auth_required": True, "description": "Get security events"},

    # Compliance reporting
    {"path": "/api/v1/audit/compliance/reports", "methods": ["POST"], "auth_required": True, "description": "Generate compliance report"},
    {"path": "/api/v1/audit/compliance/standards", "methods": ["GET"], "auth_required": False, "description": "Get compliance standards"},

    # System maintenance
    {"path": "/api/v1/audit/maintenance/cleanup", "methods": ["POST"], "auth_required": True, "description": "Cleanup old data"},
]


def get_routes_for_consul() -> Dict[str, Any]:
    """Generate compact route metadata for Consul"""
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/audit",
        "methods": "GET,POST",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


SERVICE_METADATA = {
    "service_name": "audit_service",
    "version": "1.0.0",
    "tags": ["v1", "governance-microservice", "audit", "compliance"],
    "capabilities": [
        "event_logging",
        "event_querying",
        "user_activity_tracking",
        "security_alerting",
        "compliance_reporting",
        "real_time_analysis",
        "data_retention"
    ]
}
```

### Consul Registration (in `main.py`)

```python
# Consul service registration
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
    except Exception as e:
        logger.warning(f"Failed to register with Consul: {e}")
```

---

## 8. Migration Pattern (Database Schema)

### Migration File Structure

```
microservices/audit_service/migrations/
├── 001_create_audit_events_table.sql    # Initial schema
├── 002_add_compliance_fields.sql        # Compliance columns
├── 003_add_security_indexes.sql         # Performance indexes
└── seed_test_data.sql                   # Test data (dev only)
```

### Initial Migration (`001_create_audit_events_table.sql`)

```sql
-- Audit Service Migration: Create audit_events table
-- Version: 001
-- Date: 2025-01-01

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS audit;

-- Create audit_events table
CREATE TABLE IF NOT EXISTS audit.audit_events (
    event_id VARCHAR(255) PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    event_severity VARCHAR(20) NOT NULL DEFAULT 'low',
    event_status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- Actor information
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    session_id VARCHAR(255),
    ip_address VARCHAR(50),
    user_agent TEXT,

    -- Action details
    action VARCHAR(255) NOT NULL,
    description TEXT,
    api_endpoint VARCHAR(500),
    http_method VARCHAR(10),

    -- Resource information
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_name VARCHAR(255),

    -- Result information
    success BOOLEAN DEFAULT true,
    status_code INTEGER,
    error_code VARCHAR(50),
    error_message TEXT,
    changes_made JSONB DEFAULT '{}',

    -- Security and compliance
    risk_score FLOAT DEFAULT 0.0,
    threat_indicators JSONB DEFAULT '[]',
    compliance_flags JSONB DEFAULT '[]',
    retention_policy VARCHAR(50) DEFAULT 'standard',

    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],

    -- Timestamps
    event_timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT audit_event_type_check CHECK (event_type IN (
        'user_login', 'user_logout', 'user_register', 'user_update', 'user_delete',
        'resource_access', 'resource_create', 'resource_update', 'resource_delete',
        'permission_grant', 'permission_revoke', 'permission_check',
        'security_alert', 'security_event', 'security_violation',
        'organization_create', 'organization_update', 'organization_delete',
        'organization_join', 'organization_leave',
        'system_startup', 'system_shutdown', 'system_error', 'system_config_change'
    )),
    CONSTRAINT audit_severity_check CHECK (event_severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT audit_category_check CHECK (event_category IN (
        'authentication', 'authorization', 'data_access', 'security',
        'system', 'compliance', 'configuration'
    ))
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit.audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_organization_id ON audit.audit_events(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit.audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_category ON audit.audit_events(event_category);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_severity ON audit.audit_events(event_severity);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit.audit_events(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource ON audit.audit_events(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_metadata ON audit.audit_events USING GIN(metadata);

-- Partitioning index for data retention
CREATE INDEX IF NOT EXISTS idx_audit_events_retention ON audit.audit_events(event_timestamp, retention_policy);

-- Comments for documentation
COMMENT ON TABLE audit.audit_events IS 'Comprehensive audit trail for all system activities';
COMMENT ON COLUMN audit.audit_events.event_id IS 'Unique audit event identifier';
COMMENT ON COLUMN audit.audit_events.risk_score IS 'Calculated risk score (0.0-1.0)';
COMMENT ON COLUMN audit.audit_events.compliance_flags IS 'Applicable compliance standards (GDPR, SOX, HIPAA)';
```

---

## 9. Lifecycle Pattern (main.py Setup)

### Microservice Lifespan Management

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global audit_service, event_bus, consul_registry

    logger.info("🚀 Audit Service starting up...")

    try:
        # 1. Initialize service (using factory method)
        audit_service = create_audit_service(config=config_manager)

        # 2. Check database connection
        if await audit_service.repository.check_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.warning("⚠️ Database connection failed")

        # 3. Initialize event bus
        try:
            event_bus = await get_event_bus("audit_service")
            logger.info("✅ Event bus initialized successfully")

            # 4. Initialize event handlers
            event_handlers = AuditEventHandlers(audit_service)

            # 5. Subscribe to ALL events using wildcard pattern
            await event_bus.subscribe_to_events(
                pattern="*.*",  # Subscribe to all events from all services
                handler=event_handlers.handle_nats_event
            )
            logger.info("✅ Subscribed to all NATS events (*.*)")

        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize event bus: {e}")
            event_bus = None

        # 6. Consul service registration
        if config.consul_enabled:
            # ... (see Service Registration Pattern)

        logger.info("✅ Audit Service started successfully")

    except Exception as e:
        logger.error(f"❌ Audit Service startup failed: {e}")
        audit_service = None

    yield  # Application runs

    logger.info("🛑 Audit Service shutting down...")

    # Shutdown sequence
    # 1. Consul deregistration
    if consul_registry:
        consul_registry.deregister()

    # 2. Close event bus
    if event_bus:
        await event_bus.close()

    logger.info("✅ Audit Service cleanup completed")
```

### Dependency Injection for Routes

```python
def get_audit_service() -> AuditService:
    """Get audit service instance"""
    if not audit_service:
        raise HTTPException(status_code=503, detail="Audit service unavailable")
    return audit_service


# Usage in routes:
@app.post("/api/v1/audit/events", response_model=AuditEventResponse)
async def log_audit_event(
    request: AuditEventCreateRequest,
    svc: AuditService = Depends(get_audit_service)
):
    result = await svc.log_event(request)
    return result
```

---

## 10. Configuration Pattern (ConfigManager)

### ConfigManager Usage

```python
from core.config_manager import ConfigManager

# Initialize at module level
config_manager = ConfigManager("audit_service")
config = config_manager.get_service_config()

# Available config properties:
config.service_name      # "audit_service"
config.service_port      # 8204 (from env or default)
config.service_host      # "0.0.0.0"
config.debug             # True/False
config.log_level         # "INFO"
config.consul_enabled    # True/False
config.consul_host       # "consul"
config.consul_port       # 8500
config.nats_url          # "nats://nats:4222"
```

### Service Discovery via ConfigManager

```python
# In audit_repository.py
host, port = config.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061,
    env_host_key='POSTGRES_HOST',
    env_port_key='POSTGRES_PORT'
)
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUDIT_SERVICE_PORT` | HTTP port | 8204 |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS server URL | nats://nats:4222 |
| `CONSUL_HOST` | Consul host | consul |
| `CONSUL_PORT` | Consul port | 8500 |
| `LOG_LEVEL` | Logging level | INFO |

---

## 11. Logging Pattern

### Logger Setup

```python
from core.logger import setup_service_logger

# Setup at module level
app_logger = setup_service_logger("audit_service")
logger = app_logger  # for backward compatibility
```

### Logging Patterns

```python
# Info level - normal operations
logger.info(f"Recording audit event: {request.event_type.value} - {request.action}")

# Warning level - degraded operations
logger.warning(f"⚠️ Failed to initialize event bus: {e}. Continuing without event subscriptions.")

# Error level - failures
logger.error(f"Audit event recording failed: {e}")

# Structured logging with context
logger.info(
    "Logged NATS event to audit trail",
    extra={
        "event_id": event.id,
        "event_type": event_type_str,
        "user_id": user_id,
    }
)
```

### Log Categories

| Category | Level | Example |
|----------|-------|---------|
| Startup | INFO | "🚀 Audit Service starting up..." |
| Connection | INFO | "✅ Database connection successful" |
| Event Processing | INFO | "Logged NATS event {id} to audit trail" |
| Degraded | WARNING | "⚠️ Event bus init failed" |
| Failure | ERROR | "❌ Audit Service startup failed: {e}" |

---

## 12. Event Subscription Pattern (Async Communication)

### Event Handlers (`events/handlers.py`)

```python
"""
Audit Service Event Handlers

Event subscription handlers - subscribes to ALL services' events for audit logging.
"""
import logging
from typing import Optional
from ..models import (
    AuditEventCreateRequest, EventType, EventSeverity,
    EventStatus, AuditCategory
)

logger = logging.getLogger(__name__)


class AuditEventHandlers:
    """Audit service event handlers"""

    def __init__(self, audit_service):
        """
        Initialize event handlers

        Args:
            audit_service: AuditService instance
        """
        self.audit_service = audit_service
        self.processed_event_ids = set()  # For idempotency (max 10,000)

    async def handle_nats_event(self, event):
        """
        Handle events from NATS event bus.
        Logs ALL events to audit trail for compliance and security monitoring.

        Subscribed to: *.*  (wildcard - all events from all services)
        """
        try:
            # Check idempotency
            if event.id in self.processed_event_ids:
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            # Extract event details
            event_type_str = event.type
            source = event.source
            data = event.data
            timestamp = event.timestamp
            metadata = event.metadata or {}

            # Map NATS event to audit event type
            audit_event_type = self._map_nats_event_to_audit_type(event_type_str)
            category = self._determine_audit_category(event_type_str)
            severity = self._determine_event_severity(event_type_str, data)

            # Extract user_id from event data
            user_id = data.get("user_id") or data.get("shared_by") or "system"
            organization_id = data.get("organization_id")

            # Determine resource information
            resource_type, resource_id, resource_name = self._extract_resource_info(event_type_str, data)

            # Create audit event request
            audit_request = AuditEventCreateRequest(
                event_type=audit_event_type,
                category=category,
                severity=severity,
                action=event_type_str,
                description=f"NATS event: {event_type_str} from {source}",
                user_id=user_id,
                organization_id=organization_id,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                success=True,
                metadata={
                    "nats_event_id": event.id,
                    "nats_event_source": source,
                    "nats_event_type": event_type_str,
                    "nats_timestamp": timestamp,
                    "original_data": data,
                    **metadata
                },
                tags=["nats_event", source, event_type_str]
            )

            # Log the audit event
            result = await self.audit_service.log_event(audit_request)

            if result:
                # Mark as processed (idempotency)
                self.processed_event_ids.add(event.id)
                # Limit cache size to 10,000 entries
                if len(self.processed_event_ids) > 10000:
                    self.processed_event_ids = set(list(self.processed_event_ids)[5000:])

                logger.info(f"Logged NATS event {event.id} ({event_type_str}) to audit trail")
            else:
                logger.error(f"Failed to log NATS event {event.id} to audit trail")

        except Exception as e:
            logger.error(f"Failed to handle NATS event {event.id}: {e}")
```

### Event Type Mapping

```python
def _map_nats_event_to_audit_type(self, nats_event_type: str) -> EventType:
    """Map NATS event type to audit EventType"""
    # User events
    if "user." in nats_event_type:
        if "created" in nats_event_type:
            return EventType.USER_REGISTER
        elif "logged_in" in nats_event_type:
            return EventType.USER_LOGIN
        elif "updated" in nats_event_type:
            return EventType.USER_UPDATE
        elif "deleted" in nats_event_type:
            return EventType.USER_DELETE

    # Organization events
    elif "organization." in nats_event_type:
        if "created" in nats_event_type:
            return EventType.ORGANIZATION_CREATE
        elif "member_added" in nats_event_type:
            return EventType.ORGANIZATION_JOIN
        elif "member_removed" in nats_event_type:
            return EventType.ORGANIZATION_LEAVE
        else:
            return EventType.ORGANIZATION_UPDATE

    # Resource events
    elif "file." in nats_event_type:
        if "uploaded" in nats_event_type:
            return EventType.RESOURCE_CREATE
        elif "deleted" in nats_event_type:
            return EventType.RESOURCE_DELETE
        elif "shared" in nats_event_type:
            return EventType.PERMISSION_GRANT

    # Default to resource access
    return EventType.RESOURCE_ACCESS
```

### Category Determination

```python
def _determine_audit_category(self, nats_event_type: str) -> AuditCategory:
    """Determine audit category based on event type"""
    if "user." in nats_event_type or "device.authenticated" in nats_event_type:
        return AuditCategory.AUTHENTICATION
    elif "permission" in nats_event_type or "member" in nats_event_type:
        return AuditCategory.AUTHORIZATION
    elif "payment" in nats_event_type or "subscription" in nats_event_type:
        return AuditCategory.CONFIGURATION
    elif "file." in nats_event_type or "device." in nats_event_type:
        return AuditCategory.DATA_ACCESS
    return AuditCategory.SYSTEM
```

### Severity Determination

```python
def _determine_event_severity(self, nats_event_type: str, data: dict) -> EventSeverity:
    """Determine event severity"""
    # High severity events
    if any(kw in nats_event_type for kw in ["deleted", "removed", "failed", "offline"]):
        return EventSeverity.HIGH
    # Medium severity events
    elif any(kw in nats_event_type for kw in ["updated", "shared", "member_added"]):
        return EventSeverity.MEDIUM
    # Low severity events
    else:
        return EventSeverity.LOW
```

### Subscribed Events (Wildcard)

| Pattern | Source | Description |
|---------|--------|-------------|
| `*.*` | All services | Captures ALL events from ALL services |

### Key Event Mappings

| Source Event | Audit EventType | Audit Category | Typical Severity |
|--------------|-----------------|----------------|------------------|
| `user.created` | USER_REGISTER | AUTHENTICATION | LOW |
| `user.logged_in` | USER_LOGIN | AUTHENTICATION | LOW |
| `user.deleted` | USER_DELETE | AUTHENTICATION | HIGH |
| `file.uploaded` | RESOURCE_CREATE | DATA_ACCESS | LOW |
| `file.shared` | PERMISSION_GRANT | AUTHORIZATION | MEDIUM |
| `organization.member_removed` | ORGANIZATION_LEAVE | AUTHORIZATION | HIGH |
| `payment.failed` | RESOURCE_UPDATE | CONFIGURATION | HIGH |

---

## System Contract Checklist

### Architecture (Section 1)
- [x] Service follows layer structure (main, service, repository, events)
- [x] Clear separation of concerns between layers
- [x] No circular dependencies

### Dependency Injection (Section 2)
- [x] `protocols.py` defines all dependency interfaces
- [x] `factory.py` creates service with DI
- [x] Service constructor accepts protocol types
- [x] No hardcoded dependencies in service layer

### Event Publishing (Section 3)
- [x] Event models defined in `events/models.py`
- [x] `audit.event_recorded` event for critical events
- [x] Events published after successful operations (for high severity)
- [x] Correlation ID propagated through metadata

### Error Handling (Section 4)
- [x] Custom exceptions (AuditNotFoundError, AuditValidationError, AuditServiceError)
- [x] Exception to HTTP status mapping
- [x] Consistent error response format

### Client Pattern (Section 5)
- [x] Pattern documented (audit service is primarily a consumer)
- [x] X-Internal-Call header pattern available if needed

### Repository Pattern (Section 6)
- [x] Standard CRUD methods implemented
- [x] Timestamps (event_timestamp, created_at) managed
- [x] UUID generation for event IDs
- [x] Consistent query patterns with parameterized queries

### Service Registration - Consul (Section 7)
- [x] `routes_registry.py` defines all 15 routes
- [x] SERVICE_METADATA with version and 7 capabilities
- [x] Consul registration on startup
- [x] Consul deregistration on shutdown

### Migration Pattern (Section 8)
- [x] `migrations/` folder structure defined
- [x] Schema creation (CREATE SCHEMA IF NOT EXISTS audit)
- [x] 10+ indexes for common queries
- [x] Column comments for documentation
- [x] Constraints for enum validation

### Lifecycle Pattern (Section 9)
- [x] FastAPI lifespan context manager
- [x] Event bus initialization with wildcard subscription
- [x] Database connection check on startup
- [x] Graceful shutdown sequence

### Configuration Pattern (Section 10)
- [x] ConfigManager usage at module level
- [x] Service port: 8204
- [x] Environment-based configuration
- [x] Service discovery via ConfigManager

### Logging Pattern (Section 11)
- [x] setup_service_logger usage
- [x] Structured logging with context
- [x] Emoji indicators for log categories (🚀, ✅, ⚠️, ❌)

### Event Subscription (Section 12)
- [x] `events/handlers.py` with AuditEventHandlers class
- [x] Wildcard subscription pattern `*.*`
- [x] Event type mapping logic
- [x] Category and severity determination
- [x] Idempotency via processed_event_ids cache (max 10,000)

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/audit_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/audit_service/audit_service.py` | Business logic |
| `microservices/audit_service/audit_repository.py` | Data access |
| `microservices/audit_service/protocols.py` | DI interfaces |
| `microservices/audit_service/factory.py` | DI factory |
| `microservices/audit_service/models.py` | Pydantic schemas |
| `microservices/audit_service/routes_registry.py` | Consul metadata |
| `microservices/audit_service/events/handlers.py` | NATS handlers |
| `microservices/audit_service/events/models.py` | Event schemas |
| `tests/contracts/audit_service/data_contract.py` | Test data factory |
| `tests/contracts/audit_service/logic_contract.md` | Business rules |
