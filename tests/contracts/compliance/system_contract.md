# Compliance Service - System Contract

**Implementation Patterns and Architecture for Compliance Service**

This document defines HOW compliance_service implements the 12 standard patterns.
Pattern Reference: `.claude/skills/cdd-system-contract/SKILL.md`

---

## Table of Contents

1. [Service Identity](#service-identity)
2. [Architecture Pattern](#architecture-pattern)
3. [Dependency Injection Pattern](#dependency-injection-pattern)
4. [Event Publishing Pattern](#event-publishing-pattern)
5. [Event Subscription Pattern](#event-subscription-pattern)
6. [Client Pattern (Sync)](#client-pattern-sync)
7. [Repository Pattern](#repository-pattern)
8. [Service Registration Pattern](#service-registration-pattern)
9. [Migration Pattern](#migration-pattern)
10. [Lifecycle Pattern](#lifecycle-pattern)
11. [Configuration Pattern](#configuration-pattern)
12. [Logging Pattern](#logging-pattern)

---

## Service Identity

| Property | Value |
|----------|-------|
| **Service Name** | `compliance_service` |
| **Port** | `8226` |
| **Schema** | `compliance` |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/compliance_service/` |

---

## Architecture Pattern

### File Structure
```
microservices/compliance_service/
├── __init__.py
├── main.py                    # FastAPI app + lifecycle
├── compliance_service.py      # Business logic layer
├── compliance_repository.py   # Data access layer (PostgreSQL gRPC)
├── models.py                  # Pydantic models + Enums
├── protocols.py               # DI interfaces (TODO)
├── factory.py                 # DI factory (TODO)
├── routes_registry.py         # Consul route registration
├── clients/
│   ├── __init__.py
│   └── account_client.py      # Sync call to account_service
├── events/
│   ├── __init__.py
│   ├── models.py              # Event Pydantic models + EventTypes
│   ├── publishers.py          # NATS publish functions
│   └── handlers.py            # NATS subscribe handlers
└── migrations/
    └── 001_migrate_to_compliance_schema.sql
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring, lifecycle |
| Business | `compliance_service.py` | Core compliance logic (moderation, PII, injection) |
| Data | `compliance_repository.py` | PostgreSQL queries via gRPC |
| External | `clients/` | HTTP calls to account_service |
| Async | `events/` | NATS publish/subscribe |

### Core Components

| Component | Purpose |
|-----------|---------|
| `ComplianceService` | Content moderation, PII detection, prompt injection |
| `ComplianceRepository` | CRUD for compliance_checks, policies |
| `ComplianceEventPublisher` | Publish compliance events to NATS |
| `AccountClient` | Verify user existence |

---

## Dependency Injection Pattern

### Protocols (`protocols.py`)

```python
from typing import Protocol, runtime_checkable, Dict, Any, Optional, List
from datetime import datetime
from .models import ComplianceCheck, CompliancePolicy, ComplianceStatus, RiskLevel

@runtime_checkable
class ComplianceRepositoryProtocol(Protocol):
    """Repository interface for compliance_service"""

    async def create_check(self, check: ComplianceCheck) -> Optional[ComplianceCheck]:
        """Create a new compliance check record"""
        ...

    async def get_check_by_id(self, check_id: str) -> Optional[ComplianceCheck]:
        """Get compliance check by ID"""
        ...

    async def get_checks_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        status: Optional[ComplianceStatus] = None,
        risk_level: Optional[RiskLevel] = None
    ) -> List[ComplianceCheck]:
        """Get compliance checks for a user"""
        ...

    async def update_review_status(
        self,
        check_id: str,
        reviewed_by: str,
        status: ComplianceStatus,
        review_notes: Optional[str] = None
    ) -> bool:
        """Update review status for a check"""
        ...

    async def get_pending_reviews(self, limit: int = 50) -> List[ComplianceCheck]:
        """Get checks pending human review"""
        ...

    async def create_policy(self, policy: CompliancePolicy) -> Optional[CompliancePolicy]:
        """Create a compliance policy"""
        ...

    async def get_active_policies(self, organization_id: str) -> List[CompliancePolicy]:
        """Get active policies for an organization"""
        ...

    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user compliance data (GDPR)"""
        ...

    async def get_statistics(
        self,
        organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get compliance statistics"""
        ...


@runtime_checkable
class ComplianceServiceProtocol(Protocol):
    """Service interface for compliance_service"""

    async def perform_compliance_check(self, request) -> Dict[str, Any]:
        """Perform compliance check on content"""
        ...

    async def check_content_moderation(self, content: str, content_type: str) -> Dict[str, Any]:
        """Check content for moderation issues"""
        ...

    async def detect_pii(self, content: str) -> Dict[str, Any]:
        """Detect PII in content"""
        ...

    async def detect_prompt_injection(self, content: str) -> Dict[str, Any]:
        """Detect prompt injection attempts"""
        ...
```

### Factory (`factory.py`)

```python
from core.config_manager import ConfigManager
from .compliance_service import ComplianceService
from .compliance_repository import ComplianceRepository

def create_compliance_service(
    config: ConfigManager,
    event_bus=None,
) -> ComplianceService:
    """Create ComplianceService with real dependencies"""
    repository = ComplianceRepository(config=config)
    return ComplianceService(
        repository=repository,
        event_bus=event_bus,
        config=config,
    )


def create_compliance_service_for_testing(
    repository=None,
    event_bus=None,
    config=None,
) -> ComplianceService:
    """Create ComplianceService with mock dependencies for testing"""
    return ComplianceService(
        repository=repository,
        event_bus=event_bus,
        config=config,
    )
```

---

## Event Publishing Pattern

### Architecture Overview

Events are managed per-service (NOT in core/nats_client):
- Transport: `core.nats_client.EventBus` (connection + publish)
- Event Types: `compliance_service/events/models.py` (service-specific)
- Stream: `compliance-stream` (derived from event prefix)

### Events Published

| Event | Subject | Trigger | Data |
|-------|---------|---------|------|
| `CHECK_PERFORMED` | `compliance.check.performed` | After compliance check completes | check_id, user_id, status, risk_level |
| `VIOLATION_DETECTED` | `compliance.violation.detected` | When violations found | check_id, user_id, violations, action_taken |
| `WARNING_ISSUED` | `compliance.warning.issued` | When warnings issued | check_id, user_id, warnings, risk_level |

### Event Model (`events/models.py`)

```python
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class ComplianceEventType(str, Enum):
    """
    Events published by compliance_service.

    Stream: compliance-stream
    Subjects: compliance.>
    """
    CHECK_PERFORMED = "compliance.check.performed"
    VIOLATION_DETECTED = "compliance.violation.detected"
    WARNING_ISSUED = "compliance.warning.issued"


class ComplianceSubscribedEventType(str, Enum):
    """Events that compliance_service subscribes to from other services."""
    USER_CREATED = "user.created"
    USER_DELETED = "account_service.user.deleted"
    CONTENT_CREATED = "content.created"
    FILE_UPLOADED = "storage.file_uploaded"
    PAYMENT_COMPLETED = "payment_service.payment.completed"


class ComplianceStreamConfig:
    """Stream configuration for compliance_service"""
    STREAM_NAME = "compliance-stream"
    SUBJECTS = ["compliance.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "compliance"


# =============================================================================
# Event Data Models
# =============================================================================

class ComplianceCheckPerformedEvent(BaseModel):
    """compliance.check.performed event data"""
    check_id: str = Field(..., description="Compliance check ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = None
    check_type: str = Field(..., description="Type of check performed")
    content_type: str = Field(..., description="Content type checked")
    status: str = Field(..., description="Check status (pass/fail/flagged)")
    risk_level: str = Field(..., description="Risk level assessed")
    violations_count: int = Field(default=0)
    warnings_count: int = Field(default=0)
    action_taken: Optional[str] = None
    processing_time_ms: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ComplianceViolationDetectedEvent(BaseModel):
    """compliance.violation.detected event data"""
    check_id: str
    user_id: str
    organization_id: Optional[str] = None
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str
    action_taken: Optional[str] = None
    requires_review: bool = False
    blocked_content: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ComplianceWarningIssuedEvent(BaseModel):
    """compliance.warning.issued event data"""
    check_id: str
    user_id: str
    organization_id: Optional[str] = None
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    warning_types: List[str] = Field(default_factory=list)
    risk_level: str = "low"
    allowed_with_warning: bool = True
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

### Publisher (`events/publishers.py`)

```python
from core.nats_client import Event
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def publish_compliance_check_performed(
    event_bus,
    check_id: str,
    user_id: str,
    check_type: str,
    content_type: str,
    status: str,
    risk_level: str,
    violations_count: int = 0,
    warnings_count: int = 0,
    action_taken: Optional[str] = None,
    organization_id: Optional[str] = None,
    processing_time_ms: Optional[float] = None,
    metadata: Optional[dict] = None
) -> bool:
    """Publish compliance.check.performed event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping event publication")
        return False

    try:
        event = Event(
            event_type="compliance.check.performed",
            source="compliance_service",
            data={
                "check_id": check_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "check_type": check_type,
                "content_type": content_type,
                "status": status,
                "risk_level": risk_level,
                "violations_count": violations_count,
                "warnings_count": warnings_count,
                "action_taken": action_taken,
                "processing_time_ms": processing_time_ms,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.info(f"Published compliance.check.performed for check {check_id}")
        return True

    except Exception as e:
        logger.error(f"Error publishing compliance check performed event: {e}")
        return False


async def publish_compliance_violation_detected(
    event_bus,
    check_id: str,
    user_id: str,
    violations: list,
    risk_level: str,
    action_taken: Optional[str] = None,
    organization_id: Optional[str] = None,
    requires_review: bool = False,
    blocked_content: bool = False,
    metadata: Optional[dict] = None
) -> bool:
    """Publish compliance.violation.detected event"""
    if not event_bus:
        return False

    try:
        event = Event(
            event_type="compliance.violation.detected",
            source="compliance_service",
            data={
                "check_id": check_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "violations": violations,
                "violations_count": len(violations),
                "risk_level": risk_level,
                "action_taken": action_taken,
                "requires_review": requires_review,
                "blocked_content": blocked_content,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.warning(f"Published compliance.violation.detected for check {check_id}")
        return True

    except Exception as e:
        logger.error(f"Error publishing compliance violation detected event: {e}")
        return False
```

---

## Event Subscription Pattern

### Events Subscribed

| Event | Source | Handler | Action |
|-------|--------|---------|--------|
| `content.created` | Various | `handle_content_created` | Auto-check new content |
| `storage.file_uploaded` | storage_service | `handle_user_content_uploaded` | Check uploaded files |
| `account_service.user.deleted` | account_service | `handle_user_deleted` | GDPR cleanup |
| `payment_service.payment.completed` | payment_service | `handle_payment_transaction` | AML monitoring |

### Handler (`events/handlers.py`)

```python
import logging
from typing import Callable, Dict
from core.nats_client import Event

logger = logging.getLogger(__name__)

async def handle_user_deleted(event: Event, compliance_service, event_bus):
    """
    Handle user.deleted event - GDPR Article 17 compliance

    Cleans up all compliance records for deleted user.
    """
    try:
        user_id = event.data.get("user_id")
        if not user_id:
            logger.warning(f"Missing user_id in user.deleted event: {event.id}")
            return

        logger.info(f"Processing user.deleted for compliance cleanup: {user_id}")

        if hasattr(compliance_service, 'repository'):
            # Delete compliance check history
            deleted_checks = await compliance_service.repository.delete_user_data(user_id)
            logger.info(f"Deleted {deleted_checks} compliance records for user {user_id}")

        logger.info(f"✅ Compliance cleanup completed for user {user_id} (GDPR Article 17)")

    except Exception as e:
        logger.error(f"Error handling user.deleted event: {e}", exc_info=True)


async def handle_content_created(event: Event, compliance_service, event_bus):
    """Handle content.created - auto-trigger compliance check"""
    try:
        user_id = event.data.get("user_id")
        content = event.data.get("content")
        content_type = event.data.get("content_type", "text")

        if not user_id or not content:
            return

        logger.info(f"Triggering compliance check for content.created (user: {user_id})")
        # Perform async compliance check
        # Result published via compliance.check.performed event

    except Exception as e:
        logger.error(f"Error handling content.created event: {e}")


async def handle_payment_transaction(event: Event, compliance_service, event_bus):
    """Handle payment events for AML compliance monitoring"""
    try:
        user_id = event.data.get("user_id")
        amount = event.data.get("amount", 0)
        currency = event.data.get("currency", "USD")

        if not user_id:
            return

        # AML threshold check (example: $10,000)
        if float(amount) >= 10000:
            logger.warning(f"Large transaction detected for user {user_id}: {currency} {amount}")
            # Flag for review

    except Exception as e:
        logger.error(f"Error handling payment transaction: {e}")


def get_event_handlers(compliance_service, event_bus) -> Dict[str, Callable]:
    """Get all event handlers for compliance_service"""
    return {
        "content.created": lambda event: handle_content_created(
            event, compliance_service, event_bus
        ),
        "storage.file_uploaded": lambda event: handle_user_content_uploaded(
            event, compliance_service, event_bus
        ),
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event, compliance_service, event_bus
        ),
        "payment_service.payment.completed": lambda event: handle_payment_transaction(
            event, compliance_service, event_bus
        ),
    }
```

---

## Client Pattern (Sync)

### Dependencies (Outbound HTTP Calls)

| Client | Target Service | Purpose |
|--------|----------------|---------|
| `AccountClient` | `account_service:8202` | Verify user exists, get user info |

### Client Implementation (`clients/account_client.py`)

```python
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AccountClient:
    """Async HTTP client for account_service"""

    def __init__(self, base_url: str = "http://localhost:8202"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_account(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get account from account_service"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/accounts/{user_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get account {user_id}: {e}")
            return None

    async def verify_user_exists(self, user_id: str) -> bool:
        """Check if user exists in account_service"""
        account = await self.get_account(user_id)
        return account is not None

    async def close(self):
        await self.client.aclose()
```

---

## Repository Pattern

### Schema: `compliance`

### Tables

| Table | Purpose |
|-------|---------|
| `compliance.compliance_checks` | Compliance check records |
| `compliance.compliance_policies` | Policy configurations |
| `compliance.user_consents` | GDPR consent records (optional) |

### Repository Implementation

```python
from isa_common import AsyncPostgresClient
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from .models import ComplianceCheck, CompliancePolicy, ComplianceStatus, RiskLevel

class ComplianceRepository:
    def __init__(self, config=None):
        # Service discovery via ConfigManager
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )

        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="compliance_service"
        )
        self.schema = "compliance"
        self.checks_table = "compliance_checks"
        self.policies_table = "compliance_policies"

    async def create_check(self, check: ComplianceCheck) -> Optional[ComplianceCheck]:
        query = f'''
            INSERT INTO {self.schema}.{self.checks_table} (
                check_id, check_type, content_type, status, risk_level,
                user_id, organization_id, content_hash, confidence_score,
                violations, warnings, human_review_required,
                checked_at, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            RETURNING *
        '''
        # Execute and return ComplianceCheck model

    async def get_check_by_id(self, check_id: str) -> Optional[ComplianceCheck]:
        query = f'''
            SELECT * FROM {self.schema}.{self.checks_table}
            WHERE check_id = $1
        '''
        # Execute and return ComplianceCheck model

    async def delete_user_data(self, user_id: str) -> int:
        """GDPR Article 17: Right to Erasure"""
        query = f'''
            DELETE FROM {self.schema}.{self.checks_table}
            WHERE user_id = $1
        '''
        # Execute and return count
```

---

## Service Registration Pattern

### Routes Registry (`routes_registry.py`)

```python
COMPLIANCE_SERVICE_ROUTES = [
    # Health & Status
    {"path": "/health", "methods": ["GET"], "auth_required": False},
    {"path": "/status", "methods": ["GET"], "auth_required": False},

    # Compliance Checks
    {"path": "/api/v1/compliance/check", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/compliance/check/batch", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/compliance/checks/{check_id}", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/compliance/checks/user/{user_id}", "methods": ["GET"], "auth_required": True},

    # Human Review
    {"path": "/api/v1/compliance/reviews/pending", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/compliance/reviews/{check_id}", "methods": ["PUT"], "auth_required": True},

    # Policies
    {"path": "/api/v1/compliance/policies", "methods": ["GET", "POST"], "auth_required": True},
    {"path": "/api/v1/compliance/policies/{policy_id}", "methods": ["GET"], "auth_required": True},

    # Reports & Stats
    {"path": "/api/v1/compliance/reports", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/compliance/stats", "methods": ["GET"], "auth_required": True},

    # GDPR Endpoints
    {"path": "/api/v1/compliance/user/{user_id}/data-export", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/compliance/user/{user_id}/data", "methods": ["DELETE"], "auth_required": True},
    {"path": "/api/v1/compliance/user/{user_id}/data-summary", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/compliance/user/{user_id}/consent", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/compliance/user/{user_id}/audit-log", "methods": ["GET"], "auth_required": True},

    # PCI-DSS
    {"path": "/api/v1/compliance/pci/card-data-check", "methods": ["POST"], "auth_required": True},
]

SERVICE_METADATA = {
    "service_name": "compliance_service",
    "version": "1.0.0",
    "tags": ["v1", "compliance", "moderation", "gdpr", "pci"],
    "capabilities": [
        "content_moderation",
        "pii_detection",
        "prompt_injection_detection",
        "gdpr_compliance",
        "pci_dss_compliance",
        "policy_management",
        "human_review"
    ]
}

def get_routes_for_consul() -> Dict[str, Any]:
    """Get route metadata for Consul registration"""
    return {
        "routes": json.dumps(COMPLIANCE_SERVICE_ROUTES),
        "route_count": str(len(COMPLIANCE_SERVICE_ROUTES))
    }
```

---

## Migration Pattern

### Migration Files
```
migrations/
└── 001_migrate_to_compliance_schema.sql    # Initial schema
```

### Initial Migration (`001_migrate_to_compliance_schema.sql`)

```sql
-- Compliance Service Migration: Create compliance schema and tables
-- Version: 001

CREATE SCHEMA IF NOT EXISTS compliance;

-- Compliance Checks Table
CREATE TABLE IF NOT EXISTS compliance.compliance_checks (
    id SERIAL,
    check_id VARCHAR(255) PRIMARY KEY,
    check_type VARCHAR(100) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    risk_level VARCHAR(50) NOT NULL DEFAULT 'none',

    -- User/Context
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    content_id VARCHAR(255),

    -- Content Analysis
    content_hash VARCHAR(64),
    content_size INTEGER,
    confidence_score NUMERIC(5,4) DEFAULT 0.0,

    -- Results (JSONB)
    violations JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    detected_issues JSONB DEFAULT '[]'::jsonb,
    moderation_categories JSONB DEFAULT '{}'::jsonb,
    detected_pii JSONB DEFAULT '[]'::jsonb,

    -- Actions
    action_taken VARCHAR(100),
    blocked_reason TEXT,
    human_review_required BOOLEAN DEFAULT FALSE,
    reviewed_by VARCHAR(255),
    review_notes TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    provider VARCHAR(100),

    -- Timestamps
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Compliance Policies Table
CREATE TABLE IF NOT EXISTS compliance.compliance_policies (
    id SERIAL,
    policy_id VARCHAR(255) PRIMARY KEY,
    policy_name VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Configuration
    content_types TEXT[] NOT NULL,
    check_types TEXT[] NOT NULL,
    rules JSONB NOT NULL DEFAULT '{}'::jsonb,
    thresholds JSONB DEFAULT '{}'::jsonb,

    -- Behavior
    auto_block BOOLEAN DEFAULT TRUE,
    require_human_review BOOLEAN DEFAULT FALSE,
    notification_enabled BOOLEAN DEFAULT TRUE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,

    -- Metadata
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_compliance_checks_user_id
    ON compliance.compliance_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_org_id
    ON compliance.compliance_checks(organization_id);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_status
    ON compliance.compliance_checks(status);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_risk_level
    ON compliance.compliance_checks(risk_level);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_check_type
    ON compliance.compliance_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_checked_at
    ON compliance.compliance_checks(checked_at);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_review_pending
    ON compliance.compliance_checks(human_review_required, status)
    WHERE human_review_required = TRUE AND reviewed_by IS NULL;

CREATE INDEX IF NOT EXISTS idx_compliance_policies_org_id
    ON compliance.compliance_policies(organization_id);
CREATE INDEX IF NOT EXISTS idx_compliance_policies_active
    ON compliance.compliance_policies(is_active);
```

---

## Lifecycle Pattern

### Startup Sequence
1. Initialize ConfigManager with `compliance_service`
2. Setup logger via `setup_service_logger("compliance_service")`
3. Initialize NATS event bus (`get_event_bus("compliance_service")`)
4. Create ComplianceService with event_bus and config
5. Initialize ComplianceRepository
6. Register event handlers (subscriptions via `get_event_handlers`)
7. Register with Consul (if enabled)
8. Start FastAPI app on port 8226

### Shutdown Sequence
1. Deregister from Consul
2. Close event bus connection
3. Log shutdown complete

### Lifecycle Code Example (`main.py`)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.nats_client import get_event_bus
from core.logger import setup_service_logger
from core.config_manager import ConfigManager
from isa_common.consul_client import ConsulRegistry

from .compliance_service import ComplianceService
from .compliance_repository import ComplianceRepository
from .events.handlers import get_event_handlers
from .routes_registry import get_routes_for_consul, SERVICE_METADATA

config_manager = ConfigManager("compliance_service")
config = config_manager.get_service_config()
logger = setup_service_logger("compliance_service")

compliance_service: Optional[ComplianceService] = None
event_bus = None
consul_registry = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global compliance_service, event_bus, consul_registry

    try:
        logger.info("[compliance_service] Initializing...")

        # Initialize NATS event bus
        try:
            event_bus = await get_event_bus("compliance_service")
            logger.info("✅ Event bus initialized")
        except Exception as e:
            logger.warning(f"⚠️ Event bus initialization failed: {e}")
            event_bus = None

        # Initialize service
        compliance_service = ComplianceService(
            event_bus=event_bus,
            config=config_manager
        )
        await compliance_service.repository.initialize()

        # Register event handlers
        if event_bus:
            handlers = get_event_handlers(compliance_service, event_bus)
            for pattern, handler in handlers.items():
                await event_bus.subscribe_to_events(pattern=pattern, handler=handler)
                logger.info(f"Subscribed to {pattern}")

        # Consul registration
        if config.consul_enabled:
            route_meta = get_routes_for_consul()
            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA['service_name'],
                service_port=SERVICE_PORT,
                tags=SERVICE_METADATA['tags'],
                meta={**route_meta, 'version': SERVICE_METADATA['version']}
            )
            consul_registry.register()
            logger.info(f"✅ Registered with Consul")

        logger.info(f"[compliance_service] Started on port {SERVICE_PORT}")

        yield

    finally:
        # Cleanup
        logger.info("[compliance_service] Shutting down...")

        if consul_registry:
            consul_registry.deregister()

        if event_bus:
            await event_bus.close()

        logger.info("[compliance_service] Shutdown complete")
```

---

## Configuration Pattern

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPLIANCE_SERVICE_PORT` | `8226` | Service port |
| `COMPLIANCE_SERVICE_HOST` | `0.0.0.0` | Service host |
| `CONSUL_ENABLED` | `true` | Enable Consul registration |
| `CONSUL_HOST` | `consul` | Consul server host |
| `CONSUL_PORT` | `8500` | Consul server port |
| `NATS_URL` | `nats://nats:4222` | NATS connection URL |
| `POSTGRES_HOST` | `isa-postgres-grpc` | PostgreSQL gRPC host |
| `POSTGRES_PORT` | `50061` | PostgreSQL gRPC port |
| `OPENAI_API_KEY` | (none) | OpenAI API key for moderation |

### ConfigManager Usage

```python
from core.config_manager import ConfigManager

config_manager = ConfigManager("compliance_service")
config = config_manager.get_service_config()

# Service discovery
host, port = config_manager.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061,
    env_host_key='POSTGRES_HOST',
    env_port_key='POSTGRES_PORT'
)
```

---

## Logging Pattern

### Logger Setup

```python
from core.logger import setup_service_logger

logger = setup_service_logger("compliance_service")

# Usage patterns
logger.info(f"Compliance check completed", extra={
    "check_id": check_id,
    "user_id": user_id,
    "status": status,
    "risk_level": risk_level
})

logger.warning(f"Violation detected: {violation_type}", extra={
    "check_id": check_id,
    "category": category,
    "confidence": confidence
})

logger.error(f"Compliance check failed: {error}", exc_info=True)
```

### Log Levels by Operation

| Operation | Level | Example |
|-----------|-------|---------|
| Check completed (pass) | INFO | "Compliance check passed" |
| Check completed (warning) | INFO | "Compliance check issued warnings" |
| Violation detected | WARNING | "Violation detected: hate_speech" |
| Check failed | ERROR | "Compliance check failed" |
| GDPR operation | INFO | "User data deleted (GDPR Article 17)" |
| PCI violation | WARNING | "PCI-DSS violation: card data exposed" |

---

## Error Handling Pattern

### Custom Exceptions

```python
class ComplianceError(Exception):
    """Base exception for compliance service"""
    pass


class ComplianceCheckError(ComplianceError):
    """Error during compliance check execution"""
    pass


class CompliancePolicyError(ComplianceError):
    """Error with policy configuration or application"""
    pass


class ComplianceValidationError(ComplianceError):
    """Validation error for compliance requests"""
    pass


class ComplianceNotFoundError(ComplianceError):
    """Resource not found error"""
    pass
```

### HTTP Status Mapping

| Exception | HTTP Status | Response |
|-----------|-------------|----------|
| `ComplianceValidationError` | 422 | `{"detail": "Validation error: {message}"}` |
| `ComplianceNotFoundError` | 404 | `{"detail": "Not found: {resource}"}` |
| `CompliancePolicyError` | 400 | `{"detail": "Policy error: {message}"}` |
| `ComplianceCheckError` | 500 | `{"detail": "Check failed: {message}"}` |
| `Exception` | 500 | `{"detail": "Internal server error"}` |

---

## Compliance Checklist

- [x] `main.py` with lifecycle management
- [x] `compliance_service.py` with business logic
- [x] `compliance_repository.py` with PostgreSQL queries
- [x] `models.py` with Pydantic models and enums
- [ ] `protocols.py` with DI interfaces (TODO)
- [ ] `factory.py` for service creation (TODO)
- [x] `routes_registry.py` for Consul registration
- [x] `migrations/` folder with SQL files
- [x] `events/models.py` with event types
- [x] `events/publishers.py` for publishing
- [x] `events/handlers.py` for subscriptions
- [ ] `clients/account_client.py` for dependencies (TODO)
- [x] Structured logging with `setup_service_logger`
- [x] ConfigManager usage for configuration
- [x] GDPR endpoints implemented
- [x] PCI-DSS card detection implemented

---

**Version**: 1.0.0
**Last Updated**: 2025-12-22
**Pattern Reference**: `.claude/skills/cdd-system-contract/SKILL.md`
