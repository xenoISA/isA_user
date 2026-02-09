# Invitation Service - System Contract

## Overview

This document defines HOW invitation_service implements the 12 standard patterns. It bridges the Logic Contract (business rules) to actual code implementation.

**Service**: invitation_service
**Port**: 8213
**Schema**: invitation
**Primary Table**: organization_invitations

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/invitation_service/
├── __init__.py
├── main.py                    # FastAPI app, routes, lifespan management
├── invitation_service.py      # Business logic layer
├── invitation_repository.py   # Data access layer (PostgreSQL gRPC)
├── models.py                  # Pydantic models
├── protocols.py               # DI interfaces (Protocol classes)
├── factory.py                 # DI factory
├── routes_registry.py         # Consul route definitions
├── clients/
│   ├── __init__.py            # Client exports
│   ├── account_client.py      # Account service client
│   ├── organization_client.py # Organization service client
│   └── invitation_client.py   # Self-client for other services
└── events/
    ├── __init__.py
    ├── models.py              # Event Pydantic models
    ├── publishers.py          # Event publishing logic
    └── handlers.py            # Event subscription handlers
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | main.py | HTTP endpoints, request validation, DI wiring | FastAPI, InvitationService |
| **Service** | invitation_service.py | Business logic, orchestration, validation | Repository, EventBus, OrganizationClient |
| **Repository** | invitation_repository.py | Data access, SQL queries | AsyncPostgresClient (gRPC) |
| **Clients** | clients/ | External service communication | httpx, OrganizationServiceClient |
| **Events** | events/ | Event publishing/subscription | NATS, Event, EventType |

### Component Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                    Invitation Service (Port 8213)                   │
├────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     FastAPI Application                       │  │
│  │                        (main.py)                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐ │  │
│  │  │   Routes    │  │  Lifespan   │  │    get_user_id()      │ │  │
│  │  │ /api/v1/*   │  │  Context    │  │ Header Auth Extractor │ │  │
│  │  └─────────────┘  └─────────────┘  └───────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Service Layer                              │  │
│  │                 (invitation_service.py)                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐ │  │
│  │  │  Business   │  │   Event     │  │   Organization        │ │  │
│  │  │   Logic     │  │  Publisher  │  │   Client (httpx)      │ │  │
│  │  └─────────────┘  └─────────────┘  └───────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Repository Layer                            │  │
│  │                (invitation_repository.py)                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐ │  │
│  │  │   CRUD      │  │   Query     │  │   Token Generation    │ │  │
│  │  │   Methods   │  │   Builder   │  │  secrets.token_urlsafe│ │  │
│  │  └─────────────┘  └─────────────┘  └───────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                 Dependency Injection Layer                    │  │
│  │                    (protocols.py)                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐ │  │
│  │  │ Repository  │  │  EventBus   │  │  OrganizationClient   │ │  │
│  │  │  Protocol   │  │  Protocol   │  │      Protocol         │ │  │
│  │  └─────────────┘  └─────────────┘  └───────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │      NATS       │  │  Organization   │
│   (via gRPC)    │  │   Event Bus     │  │    Service      │
│   Port: 50061   │  │   Port: 4222    │  │   Port: 8212    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
"""
Invitation Service Protocols - DI Interfaces

All dependencies defined as Protocol classes for testability.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List, Tuple
from datetime import datetime

from .models import (
    InvitationStatus, OrganizationRole,
    InvitationResponse, InvitationDetailResponse,
    InvitationListResponse, AcceptInvitationResponse
)


@runtime_checkable
class InvitationRepositoryProtocol(Protocol):
    """Repository interface for invitation data access"""

    async def create_invitation(
        self,
        organization_id: str,
        email: str,
        role: OrganizationRole,
        invited_by: str
    ) -> Optional[InvitationResponse]:
        """Create new invitation and return InvitationResponse"""
        ...

    async def get_invitation_by_id(
        self, invitation_id: str
    ) -> Optional[InvitationResponse]:
        """Get invitation by ID"""
        ...

    async def get_invitation_by_token(
        self, invitation_token: str
    ) -> Optional[InvitationResponse]:
        """Get invitation by token"""
        ...

    async def get_invitation_with_organization_info(
        self, invitation_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get invitation with organization info"""
        ...

    async def get_pending_invitation_by_email_and_organization(
        self, email: str, organization_id: str
    ) -> Optional[InvitationResponse]:
        """Get pending invitation by email and org"""
        ...

    async def get_organization_invitations(
        self, organization_id: str, limit: int, offset: int
    ) -> List[InvitationResponse]:
        """List organization invitations"""
        ...

    async def update_invitation(
        self, invitation_id: str, update_data: Dict[str, Any]
    ) -> bool:
        """Update invitation fields"""
        ...

    async def accept_invitation(self, invitation_token: str) -> bool:
        """Accept invitation by token"""
        ...

    async def cancel_invitation(self, invitation_id: str) -> bool:
        """Cancel invitation"""
        ...

    async def expire_old_invitations(self) -> int:
        """Expire old pending invitations"""
        ...

    async def cancel_organization_invitations(
        self, organization_id: str
    ) -> int:
        """Cancel all pending invitations for an organization"""
        ...

    async def cancel_invitations_by_inviter(self, user_id: str) -> int:
        """Cancel all pending invitations sent by a user"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Event bus interface for NATS publishing"""

    async def publish_event(self, event: Any) -> None:
        """Publish event to NATS"""
        ...

    async def subscribe(
        self, subject: str, callback: Any
    ) -> None:
        """Subscribe to NATS subject"""
        ...

    async def close(self) -> None:
        """Close connection"""
        ...


@runtime_checkable
class OrganizationClientProtocol(Protocol):
    """Client interface for organization service calls"""

    async def get_organization_info(
        self, organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get organization info"""
        ...

    async def can_user_invite(
        self, user_id: str, organization_id: str
    ) -> bool:
        """Check if user can invite to organization"""
        ...

    async def is_user_member(
        self, user_id: str, organization_id: str
    ) -> bool:
        """Check if user is already a member"""
        ...

    async def add_member_to_organization(
        self,
        organization_id: str,
        user_id: str,
        role: str,
        invited_by: Optional[str]
    ) -> bool:
        """Add user as organization member"""
        ...

    async def close(self) -> None:
        """Close client connection"""
        ...
```

### Factory Implementation (`factory.py`)

```python
"""
Invitation Service Factory - Dependency Injection Setup

Creates service instances with real or mock dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager
from core.nats_client import get_event_bus

from .invitation_service import InvitationService
from .invitation_repository import InvitationRepository
from .clients.organization_client import OrganizationClient
from .protocols import (
    InvitationRepositoryProtocol,
    EventBusProtocol,
    OrganizationClientProtocol,
)


class InvitationServiceFactory:
    """Factory for creating InvitationService with dependencies"""

    @staticmethod
    def create_service(
        repository: Optional[InvitationRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        organization_client: Optional[OrganizationClientProtocol] = None,
        config: Optional[ConfigManager] = None,
    ) -> InvitationService:
        """
        Create InvitationService instance.

        Args:
            repository: Repository implementation (default: real repository)
            event_bus: Event bus implementation (default: None, set via lifespan)
            organization_client: Org client (default: None, uses inline httpx)
            config: Config manager (default: creates new one)

        Returns:
            Configured InvitationService instance
        """
        # Use real implementations if not provided
        if repository is None:
            if config is None:
                config = ConfigManager("invitation_service")
            repository = InvitationRepository(config=config)

        return InvitationService(
            repository=repository,
            event_bus=event_bus,
            organization_client=organization_client,
        )

    @staticmethod
    def create_for_testing(
        mock_repository: InvitationRepositoryProtocol,
        mock_event_bus: Optional[EventBusProtocol] = None,
        mock_organization_client: Optional[OrganizationClientProtocol] = None,
    ) -> InvitationService:
        """Create service with mock dependencies for testing"""
        return InvitationService(
            repository=mock_repository,
            event_bus=mock_event_bus,
            organization_client=mock_organization_client,
        )


def create_invitation_service(
    config: Optional[ConfigManager] = None,
    event_bus: Optional[EventBusProtocol] = None,
) -> InvitationService:
    """
    Convenience function to create InvitationService.

    Used by main.py lifespan context.
    """
    return InvitationServiceFactory.create_service(
        config=config,
        event_bus=event_bus,
    )
```

### Service Implementation with DI

```python
class InvitationService:
    """
    Invitation business logic layer.

    All dependencies injected via constructor for testability.
    """

    def __init__(
        self,
        repository: InvitationRepositoryProtocol = None,
        event_bus: Optional[EventBusProtocol] = None,
        organization_client: Optional[OrganizationClientProtocol] = None,
    ):
        # Use default repository if not provided
        self.repository = repository or InvitationRepository()
        self.event_bus = event_bus
        self.organization_client = organization_client
        # Fallback to inline httpx calls if no client provided
        self.invitation_base_url = "https://app.iapro.ai/accept-invitation"
```

---

## 3. Event Publishing Pattern

### Event Model Definition (`events/models.py`)

```python
"""
Invitation Service Event Models

Event data models for NATS publishing.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class InvitationSentEvent(BaseModel):
    """Event published when invitation is sent"""
    invitation_id: str = Field(..., description="Invitation ID")
    organization_id: str = Field(..., description="Organization ID")
    email: str = Field(..., description="Invitee email")
    role: str = Field(..., description="Assigned role")
    invited_by: str = Field(..., description="Inviter user ID")
    email_sent: bool = Field(default=False, description="Email delivery status")
    timestamp: str = Field(..., description="Event timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InvitationExpiredEvent(BaseModel):
    """Event published when invitation expires"""
    invitation_id: str
    organization_id: str
    email: str
    expired_at: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InvitationAcceptedEvent(BaseModel):
    """Event published when invitation is accepted"""
    invitation_id: str
    organization_id: str
    user_id: str = Field(..., description="User who accepted")
    email: str
    role: str
    accepted_at: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InvitationCancelledEvent(BaseModel):
    """Event published when invitation is cancelled"""
    invitation_id: str
    organization_id: str
    email: str
    cancelled_by: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
```

### Event Publishing (`events/publishers.py`)

```python
"""
Invitation Service Event Publishers

Uses core.nats_client Event and EventType for publishing.
"""
from datetime import datetime
from typing import Optional
from core.nats_client import Event, EventType, ServiceSource


async def publish_invitation_sent(
    event_bus,
    invitation_id: str,
    organization_id: str,
    email: str,
    role: str,
    invited_by: str,
    email_sent: bool = False,
    metadata: Optional[dict] = None
):
    """Publish invitation.sent event"""
    if not event_bus:
        return

    event = Event(
        event_type=EventType.INVITATION_SENT,
        source=ServiceSource.INVITATION_SERVICE,
        data={
            "invitation_id": invitation_id,
            "organization_id": organization_id,
            "email": email,
            "role": role,
            "invited_by": invited_by,
            "email_sent": email_sent,
            "timestamp": datetime.utcnow().isoformat()
        },
        metadata=metadata or {}
    )
    await event_bus.publish_event(event)


async def publish_invitation_accepted(
    event_bus,
    invitation_id: str,
    organization_id: str,
    user_id: str,
    email: str,
    role: str,
    accepted_at: str,
    metadata: Optional[dict] = None
):
    """Publish invitation.accepted event"""
    if not event_bus:
        return

    event = Event(
        event_type=EventType.INVITATION_ACCEPTED,
        source=ServiceSource.INVITATION_SERVICE,
        data={
            "invitation_id": invitation_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "email": email,
            "role": role,
            "accepted_at": accepted_at,
            "timestamp": datetime.utcnow().isoformat()
        },
        metadata=metadata or {}
    )
    await event_bus.publish_event(event)


# Similarly: publish_invitation_expired, publish_invitation_cancelled
```

### Published Events Summary

| Event Type | Subject | Trigger | Key Data |
|------------|---------|---------|----------|
| `INVITATION_SENT` | `events.invitation.sent` | After create_invitation() | invitation_id, org_id, email, role, invited_by |
| `INVITATION_ACCEPTED` | `events.invitation.accepted` | After accept_invitation() | invitation_id, org_id, user_id, role, accepted_at |
| `INVITATION_EXPIRED` | `events.invitation.expired` | Token access after expiry | invitation_id, org_id, email, expired_at |
| `INVITATION_CANCELLED` | `events.invitation.cancelled` | After cancel_invitation() | invitation_id, org_id, email, cancelled_by |

---

## 4. Error Handling Pattern

### Custom Exceptions

```python
"""
Invitation Service Exceptions
"""

class InvitationServiceError(Exception):
    """Base exception for invitation service"""
    pass


class InvitationNotFoundError(InvitationServiceError):
    """Raised when invitation is not found"""
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Invitation not found: {identifier}")


class InvitationExpiredError(InvitationServiceError):
    """Raised when invitation has expired"""
    def __init__(self, invitation_id: str):
        self.invitation_id = invitation_id
        super().__init__(f"Invitation has expired: {invitation_id}")


class DuplicateInvitationError(InvitationServiceError):
    """Raised when duplicate invitation exists"""
    def __init__(self, email: str, organization_id: str):
        self.email = email
        self.organization_id = organization_id
        super().__init__(f"Pending invitation already exists for {email}")


class InviterPermissionError(InvitationServiceError):
    """Raised when inviter lacks permission"""
    def __init__(self, user_id: str, organization_id: str):
        self.user_id = user_id
        self.organization_id = organization_id
        super().__init__("You don't have permission to invite users")


class AlreadyMemberError(InvitationServiceError):
    """Raised when invitee is already a member"""
    def __init__(self, email: str, organization_id: str):
        self.email = email
        super().__init__("User is already a member of this organization")
```

### HTTP Error Mapping (main.py)

```python
# Error handling is done via tuple returns and HTTPException raising

@app.post("/api/v1/invitations/organizations/{organization_id}")
async def create_invitation(...):
    try:
        success, invitation, message = await invitation_service.create_invitation(...)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {...}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create invitation")
```

### Error Response Mapping

| Error Condition | HTTP Status | Detail Message |
|----------------|-------------|----------------|
| Invitation not found | 404 | "Invitation not found" |
| Permission denied | 403 | "You don't have permission to..." |
| Duplicate invitation | 400 | "A pending invitation already exists" |
| Already member | 400 | "User is already a member" |
| Expired invitation | 400 | "Invitation has expired" |
| Invalid state | 400 | "Cannot resend {status} invitation" |
| Auth required | 401 | "User authentication required" |
| Server error | 500 | "Failed to {operation}" |

---

## 5. Client Pattern (Sync Communication)

### Organization Client Implementation

```python
"""
Organization Service Client

Used for permission validation and member management.
"""
import httpx
from typing import Optional, Dict, Any


class OrganizationClient:
    """Wrapper client for Organization Service"""

    def __init__(self, base_url: str = None):
        self._client = OrganizationServiceClient(base_url=base_url)

    async def close(self):
        await self._client.close()

    async def can_user_invite(
        self, user_id: str, organization_id: str
    ) -> bool:
        """
        Check if user can send invitations.

        Only admins and owners can invite.
        """
        try:
            member = await self._client.get_organization_member(
                organization_id, user_id
            )
            if member:
                role = member.get("role", "").lower()
                return role in ["admin", "owner"]
            return False
        except Exception:
            return False

    async def add_member_to_organization(
        self,
        organization_id: str,
        user_id: str,
        role: str = "member",
        invited_by: Optional[str] = None
    ) -> bool:
        """Add user to organization after invitation acceptance"""
        try:
            result = await self._client.add_organization_member(
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                metadata={"invited_by": invited_by} if invited_by else None
            )
            return result is not None
        except Exception:
            return False
```

### Inline httpx Usage in Service

The service also uses inline httpx calls for organization validation:

```python
async def _verify_organization_exists(
    self, organization_id: str, user_id: str
) -> bool:
    """Verify organization exists via HTTP call"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._get_service_url('organization_service', 8212)}"
                f"/api/v1/organizations/{organization_id}",
                headers={"X-User-Id": user_id}
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error verifying organization exists: {e}")
        return False
```

### Client Dependencies

| Client | Target Service | Port | Purpose |
|--------|----------------|------|---------|
| OrganizationClient | organization_service | 8212 | Permission validation, member management |
| AccountClient | account_service | 8202 | Email verification (optional) |

---

## 6. Repository Pattern (Database Access)

### Repository Implementation

```python
"""
Invitation Repository - PostgreSQL via gRPC
"""
from isa_common import AsyncPostgresClient
from datetime import datetime, timedelta, timezone
import uuid
import secrets


class InvitationRepository:
    """Data access layer for invitations"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("invitation_service")

        # Service discovery for PostgreSQL
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
            user_id="invitation_service"
        )
        self.schema = "invitation"
        self.invitations_table = "organization_invitations"

    async def create_invitation(
        self,
        organization_id: str,
        email: str,
        role: OrganizationRole,
        invited_by: str
    ) -> Optional[InvitationResponse]:
        """Create invitation with generated token"""
        invitation_id = str(uuid.uuid4())
        invitation_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        now = datetime.now(timezone.utc)

        query = f'''
            INSERT INTO {self.schema}.{self.invitations_table} (
                invitation_id, organization_id, email, role, invited_by,
                invitation_token, status, expires_at, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        '''

        params = [
            invitation_id, organization_id, email, role.value,
            invited_by, invitation_token, InvitationStatus.PENDING.value,
            expires_at, now, now
        ]

        async with self.db:
            results = await self.db.query(query, params, schema=self.schema)

        if results and len(results) > 0:
            return InvitationResponse(**results[0])
        return None
```

### Repository Methods Summary

| Method | SQL Operation | Purpose |
|--------|---------------|---------|
| `create_invitation()` | INSERT | Create new invitation with token |
| `get_invitation_by_id()` | SELECT WHERE invitation_id | Get by ID |
| `get_invitation_by_token()` | SELECT WHERE invitation_token | Get by token |
| `get_pending_invitation_by_email_and_organization()` | SELECT WHERE email AND org_id AND status | Duplicate check |
| `get_organization_invitations()` | SELECT WHERE org_id ORDER BY created_at | List invitations |
| `update_invitation()` | UPDATE SET ... WHERE invitation_id | Generic update |
| `accept_invitation()` | UPDATE SET status, accepted_at WHERE token | Accept flow |
| `cancel_invitation()` | UPDATE SET status='cancelled' | Cancel flow |
| `expire_old_invitations()` | UPDATE SET status='expired' WHERE expires_at < now | Batch expiration |
| `cancel_organization_invitations()` | UPDATE WHERE org_id AND status='pending' | Event handler |
| `cancel_invitations_by_inviter()` | UPDATE WHERE invited_by AND status='pending' | Event handler |

---

## 7. Service Registration Pattern (Consul)

### Routes Registry (`routes_registry.py`)

```python
"""
Invitation Service Routes Registry

Defines all API routes for Consul service registration.
"""
from typing import List, Dict, Any

SERVICE_ROUTES = [
    # Health endpoints
    {"path": "/", "methods": ["GET"], "auth_required": False, "description": "Root health"},
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Health check"},
    {"path": "/info", "methods": ["GET"], "auth_required": False, "description": "Service info"},
    {"path": "/api/v1/invitations/info", "methods": ["GET"], "auth_required": False, "description": "API info"},

    # Invitation Management
    {"path": "/api/v1/invitations/organizations/{organization_id}", "methods": ["GET", "POST"],
     "auth_required": True, "description": "List/create org invitations"},
    {"path": "/api/v1/invitations/{invitation_token}", "methods": ["GET"],
     "auth_required": False, "description": "Get invitation by token"},
    {"path": "/api/v1/invitations/{invitation_id}", "methods": ["DELETE"],
     "auth_required": True, "description": "Delete invitation"},
    {"path": "/api/v1/invitations/accept", "methods": ["POST"],
     "auth_required": True, "description": "Accept invitation"},
    {"path": "/api/v1/invitations/{invitation_id}/resend", "methods": ["POST"],
     "auth_required": True, "description": "Resend invitation"},

    # Admin
    {"path": "/api/v1/admin/expire-invitations", "methods": ["POST"],
     "auth_required": True, "description": "Expire old invitations"},
]


def get_routes_for_consul() -> Dict[str, Any]:
    """Generate compact route metadata for Consul"""
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/invitations",
        "methods": "GET,POST,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


SERVICE_METADATA = {
    "service_name": "invitation_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "invitation-management", "organization"],
    "capabilities": [
        "invitation_creation",
        "invitation_acceptance",
        "invitation_management",
        "organization_invites",
        "email_notifications",
        "invitation_expiration"
    ]
}
```

### Consul Registration in Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global consul_registry

    # Consul registration
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

    yield

    # Cleanup: Consul deregistration
    if consul_registry:
        consul_registry.deregister()
```

---

## 8. Migration Pattern (Database Schema)

### Migration Files

```
microservices/invitation_service/migrations/
├── 002_migrate_to_invitation_schema.sql  # Current schema
└── (future migrations...)
```

### Schema Definition

```sql
-- Create invitation schema
CREATE SCHEMA IF NOT EXISTS invitation;

-- Main invitations table
CREATE TABLE invitation.organization_invitations (
    id SERIAL PRIMARY KEY,
    invitation_id VARCHAR(100) UNIQUE NOT NULL,
    organization_id VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    invited_by VARCHAR(100) NOT NULL,
    invitation_token VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_invitations_organization_id ON invitation.organization_invitations(organization_id);
CREATE INDEX idx_invitations_email ON invitation.organization_invitations(email);
CREATE INDEX idx_invitations_token ON invitation.organization_invitations(invitation_token);
CREATE INDEX idx_invitations_status ON invitation.organization_invitations(status);
CREATE INDEX idx_invitations_invited_by ON invitation.organization_invitations(invited_by);
CREATE INDEX idx_invitations_expires_at ON invitation.organization_invitations(expires_at);

-- Composite indexes
CREATE INDEX idx_invitations_email_org_status ON invitation.organization_invitations(email, organization_id, status);
CREATE INDEX idx_invitations_org_status ON invitation.organization_invitations(organization_id, status);

-- Update trigger
CREATE TRIGGER update_invitations_updated_at
    BEFORE UPDATE ON invitation.organization_invitations
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();
```

### Table Schema Summary

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Auto-increment ID |
| invitation_id | VARCHAR(100) | UNIQUE NOT NULL | UUID identifier |
| organization_id | VARCHAR(100) | NOT NULL | Target organization |
| email | VARCHAR(255) | NOT NULL | Invitee email |
| role | VARCHAR(50) | NOT NULL | Assigned role |
| invited_by | VARCHAR(100) | NOT NULL | Inviter user ID |
| invitation_token | VARCHAR(255) | UNIQUE NOT NULL | Secure token |
| status | VARCHAR(20) | DEFAULT 'pending' | Invitation state |
| expires_at | TIMESTAMPTZ | NOT NULL | Expiration time |
| accepted_at | TIMESTAMPTZ | NULL | Acceptance time |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

---

## 9. Lifecycle Pattern (main.py Setup)

### Lifespan Context Manager

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global consul_registry, invitation_service

    try:
        # 1. Initialize event bus
        event_bus = None
        try:
            event_bus = await get_event_bus("invitation_service")
            logger.info("Event bus initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize event bus: {e}")
            event_bus = None

        # 2. Initialize service with event bus
        invitation_service = InvitationService(event_bus=event_bus)

        # 3. Set up event subscriptions
        if event_bus:
            try:
                invitation_repo = InvitationRepository()
                event_handler = InvitationEventHandler(invitation_repo)

                # Subscribe to organization.deleted
                await event_bus.subscribe(
                    subject="events.organization.deleted",
                    callback=lambda msg: event_handler.handle_event(msg)
                )

                # Subscribe to user.deleted
                await event_bus.subscribe(
                    subject="events.user.deleted",
                    callback=lambda msg: event_handler.handle_event(msg)
                )
            except Exception as e:
                logger.warning(f"Failed to set up event subscriptions: {e}")

        # 4. Consul registration
        if config.consul_enabled:
            # ... (see Consul pattern)

        yield  # Application runs

    except Exception as e:
        logger.error(f"Error during service startup: {e}")
        raise

    finally:
        # Cleanup
        if consul_registry:
            consul_registry.deregister()

        if event_bus:
            await event_bus.close()

        logger.info("Invitation microservice shutdown completed")
```

### Startup Sequence

1. **Event Bus Initialization** - Connect to NATS
2. **Service Creation** - Create InvitationService with event bus
3. **Event Subscriptions** - Subscribe to organization.deleted, user.deleted
4. **Consul Registration** - Register service with metadata
5. **Application Running** - Handle HTTP requests
6. **Shutdown** - Deregister from Consul, close event bus

### Dependency Injection for Routes

```python
def get_invitation_service() -> InvitationService:
    """Get invitation service instance for route injection"""
    global invitation_service
    if invitation_service is None:
        invitation_service = InvitationService()
    return invitation_service


@app.post("/api/v1/invitations/organizations/{organization_id}")
async def create_invitation(
    organization_id: str,
    request_data: InvitationCreateRequest,
    request: Request,
    invitation_service: InvitationService = Depends(get_invitation_service)
):
    ...
```

---

## 10. Configuration Pattern (ConfigManager)

### Configuration Usage

```python
from core.config_manager import ConfigManager

# Initialize at module level
config_manager = ConfigManager("invitation_service")
config = config_manager.get_service_config()

# Available properties
config.service_name      # "invitation_service"
config.service_port      # 8213
config.service_host      # "0.0.0.0"
config.debug             # True/False
config.log_level         # "INFO"
config.consul_enabled    # True/False
config.consul_host       # "consul"
config.consul_port       # 8500
config.nats_url          # "nats://nats:4222"
```

### Service Discovery

```python
# Repository uses config for PostgreSQL discovery
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
| `SERVICE_PORT` | HTTP port | 8213 |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS connection URL | nats://nats:4222 |
| `CONSUL_ENABLED` | Enable Consul | true |
| `CONSUL_HOST` | Consul host | consul |
| `CONSUL_PORT` | Consul port | 8500 |
| `LOG_LEVEL` | Logging level | INFO |

---

## 11. Logging Pattern

### Logger Setup

```python
from core.logger import setup_service_logger

# Setup at module level
app_logger = setup_service_logger("invitation_service")
logger = app_logger  # for backward compatibility
```

### Logging Patterns

```python
# Info level for normal operations
logger.info(f"Creating invitation for {email} to organization {organization_id}")
logger.info(f"Invitation created: {invitation.invitation_id}")

# Warning for non-critical issues
logger.warning("Event bus not available, skipping event publication")
logger.warning(f"Failed to register with Consul: {e}")

# Error with exception info
logger.error(f"Error creating invitation: {e}")
logger.error(f"Error accepting invitation: {e}", exc_info=True)

# Structured logging in event handlers
logger.info(f"Handling organization.deleted event for org {organization_id}")
logger.info(f"Cancelled {cancelled_count} pending invitations for organization {organization_id}")
```

---

## 12. Event Subscription Pattern (Async Communication)

### Event Handler Implementation (`events/handlers.py`)

```python
"""
Invitation Service Event Handlers

Handles incoming events from other services via NATS.
"""
from core.nats_client import Event, EventType


class InvitationEventHandler:
    """
    Handles events subscribed by Invitation Service

    Subscribes to:
    - organization.deleted: Cancel pending invitations for deleted org
    - user.deleted: Cancel invitations sent by deleted user
    """

    def __init__(self, invitation_repository):
        self.invitation_repo = invitation_repository

    async def handle_organization_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle organization.deleted event

        Cancels all pending invitations for the deleted organization.
        """
        try:
            organization_id = event_data.get('organization_id')
            if not organization_id:
                logger.warning("organization.deleted event missing organization_id")
                return False

            cancelled_count = await self.invitation_repo.cancel_organization_invitations(
                organization_id
            )

            logger.info(f"Cancelled {cancelled_count} invitations for org {organization_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle organization.deleted: {e}", exc_info=True)
            return False

    async def handle_user_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle user.deleted event

        Cancels invitations sent by the deleted user.
        """
        try:
            user_id = event_data.get('user_id')
            if not user_id:
                logger.warning("user.deleted event missing user_id")
                return False

            cancelled_count = await self.invitation_repo.cancel_invitations_by_inviter(
                user_id
            )

            logger.info(f"Cancelled {cancelled_count} invitations by user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle user.deleted: {e}", exc_info=True)
            return False

    async def handle_event(self, event: Event) -> bool:
        """Route event to appropriate handler"""
        try:
            event_type = event.type

            if event_type == "organization.deleted":
                return await self.handle_organization_deleted(event.data)
            elif event_type == EventType.USER_DELETED.value:
                return await self.handle_user_deleted(event.data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to handle event: {e}", exc_info=True)
            return False

    def get_subscriptions(self) -> list:
        """Get list of event types this handler subscribes to"""
        return [
            "organization.deleted",
            EventType.USER_DELETED.value,
        ]
```

### Event Subscription Registration

```python
# In main.py lifespan
if event_bus:
    invitation_repo = InvitationRepository()
    event_handler = InvitationEventHandler(invitation_repo)

    await event_bus.subscribe(
        subject="events.organization.deleted",
        callback=lambda msg: event_handler.handle_event(msg)
    )

    await event_bus.subscribe(
        subject="events.user.deleted",
        callback=lambda msg: event_handler.handle_event(msg)
    )
```

### Subscribed Events Summary

| Event | Source | Subject | Handler | Action |
|-------|--------|---------|---------|--------|
| organization.deleted | organization_service | events.organization.deleted | handle_organization_deleted | Cancel org's pending invitations |
| user.deleted | account_service | events.user.deleted | handle_user_deleted | Cancel user's sent invitations |

---

## System Contract Checklist

### Architecture (Section 1)
- [x] Service follows layer structure (main, service, repository, clients, events)
- [x] Clear separation of concerns between layers
- [x] No circular dependencies

### Dependency Injection (Section 2)
- [ ] `protocols.py` defines all dependency interfaces (TO BE CREATED)
- [ ] `factory.py` creates service with DI (TO BE CREATED)
- [x] Service constructor accepts dependencies (event_bus)
- [x] Repository uses config injection

### Event Publishing (Section 3)
- [x] Event models defined in `events/models.py`
- [x] Uses core.nats_client EventType enum
- [x] Events published after successful operations
- [x] Graceful handling when event bus unavailable

### Error Handling (Section 4)
- [x] Custom exception class (InvitationServiceError)
- [x] Tuple-based error returns (success, result, message)
- [x] HTTPException mapping in routes
- [x] Consistent error logging

### Client Pattern (Section 5)
- [x] OrganizationClient for permission validation
- [x] Inline httpx for quick validations
- [x] X-User-Id header for service-to-service calls
- [x] Graceful error handling (returns False on failure)

### Repository Pattern (Section 6)
- [x] Standard CRUD methods implemented
- [x] Timestamps (created_at, updated_at) managed
- [x] UUID generation for invitation_id
- [x] Token generation via secrets.token_urlsafe

### Service Registration (Section 7)
- [x] `routes_registry.py` defines all routes
- [x] SERVICE_METADATA with version and capabilities
- [x] Consul registration on startup
- [x] Consul deregistration on shutdown

### Migration Pattern (Section 8)
- [x] `migrations/` folder with SQL files
- [x] Schema creation (invitation)
- [x] Indexes for common queries
- [x] Column comments for documentation

### Lifecycle Pattern (Section 9)
- [x] asynccontextmanager lifespan
- [x] Event bus initialization
- [x] Event subscription registration
- [x] Graceful shutdown

### Configuration Pattern (Section 10)
- [x] ConfigManager usage at module level
- [x] Service discovery for PostgreSQL
- [x] Environment-based configuration

### Logging Pattern (Section 11)
- [x] setup_service_logger usage
- [x] Info logging for operations
- [x] Error logging with context

### Event Subscription (Section 12)
- [x] InvitationEventHandler class
- [x] Handles organization.deleted
- [x] Handles user.deleted
- [x] Proper error handling in handlers

---

## Implementation TODO

The following files need to be created to complete DI pattern:

1. **`protocols.py`** - Define InvitationRepositoryProtocol, EventBusProtocol, OrganizationClientProtocol
2. **`factory.py`** - Create InvitationServiceFactory with create_service() and create_for_testing()

These are documented in this contract but not yet implemented in the codebase.
