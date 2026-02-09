# Membership Service - System Contract

**Implementation Patterns and Architecture for Membership Service**

This document defines HOW membership_service implements the 12 standard patterns.
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
| **Service Name** | `membership_service` |
| **Port** | `8250` |
| **Schema** | `membership` |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/membership_service/` |

---

## Architecture Pattern

### File Structure
```
microservices/membership_service/
├── __init__.py
├── main.py                    # FastAPI app + lifecycle
├── membership_service.py      # Business logic layer
├── membership_repository.py   # Data access layer (PostgreSQL)
├── models.py                  # Pydantic models (Membership, Points, Tier, etc.)
├── protocols.py               # DI interfaces
├── factory.py                 # DI factory
├── routes_registry.py         # Consul route registration
├── clients/
│   ├── __init__.py
│   └── account_client.py      # Optional sync call to account_service
├── events/
│   ├── __init__.py
│   ├── models.py              # Event Pydantic models
│   ├── publishers.py          # NATS publish functions
│   └── handlers.py            # NATS subscribe handlers
└── migrations/
    ├── 001_create_membership_tables.sql
    └── 002_add_tier_benefits.sql
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring |
| Business | `membership_service.py` | Enrollment, points, tiers, benefits |
| Data | `membership_repository.py` | PostgreSQL queries, atomic operations |
| External | `clients/` | HTTP calls to account_service |
| Async | `events/` | NATS event publishing and subscriptions |

---

## Dependency Injection Pattern

### Protocols (`protocols.py`)
```python
from typing import Protocol, runtime_checkable, Dict, Any, Optional, List
from datetime import datetime

@runtime_checkable
class MembershipRepositoryProtocol(Protocol):
    """Repository interface for membership operations"""

    async def create_membership(
        self,
        user_id: str,
        tier_code: str,
        points_balance: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create new membership"""
        ...

    async def get_membership(self, membership_id: str) -> Optional[Dict[str, Any]]:
        """Get membership by ID"""
        ...

    async def get_membership_by_user(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        active_only: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get active membership for user"""
        ...

    async def add_points(
        self,
        membership_id: str,
        points: int,
        tier_points: int,
        source: str,
        reference_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Atomically add points"""
        ...

    async def deduct_points(
        self,
        membership_id: str,
        points: int,
        reward_code: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Atomically deduct points"""
        ...

    async def update_tier(
        self,
        membership_id: str,
        new_tier: str
    ) -> Dict[str, Any]:
        """Update membership tier"""
        ...

    async def update_status(
        self,
        membership_id: str,
        status: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update membership status"""
        ...

    async def get_history(
        self,
        membership_id: str,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get membership history"""
        ...

    async def add_history(
        self,
        membership_id: str,
        action: str,
        points_change: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Record history entry"""
        ...

    async def get_tier_benefits(
        self,
        tier_code: str
    ) -> List[Dict[str, Any]]:
        """Get benefits for tier"""
        ...

    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user data (GDPR)"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Event bus interface for publishing events"""

    async def publish(self, subject: str, data: Dict[str, Any]) -> None:
        """Publish event to NATS"""
        ...
```

### Factory (`factory.py`)
```python
from core.config_manager import ConfigManager
from .membership_service import MembershipService
from .membership_repository import MembershipRepository

def create_membership_service(
    config: ConfigManager,
    event_bus=None,
) -> MembershipService:
    """Create MembershipService with real dependencies"""
    repository = MembershipRepository(config=config)
    return MembershipService(
        repository=repository,
        event_bus=event_bus,
    )
```

---

## Event Publishing Pattern

### Events Published

| Event | Subject | Trigger | Data |
|-------|---------|---------|------|
| `MEMBERSHIP_ENROLLED` | `membership.enrolled` | After enrollment | `membership_id`, `user_id`, `tier_code`, `enrollment_bonus`, `enrolled_at` |
| `MEMBERSHIP_TIER_UPGRADED` | `membership.tier_upgraded` | After tier upgrade | `membership_id`, `user_id`, `previous_tier`, `new_tier`, `tier_points` |
| `MEMBERSHIP_TIER_DOWNGRADED` | `membership.tier_downgraded` | After tier downgrade | `membership_id`, `user_id`, `previous_tier`, `new_tier` |
| `MEMBERSHIP_SUSPENDED` | `membership.suspended` | After suspension | `membership_id`, `user_id`, `reason` |
| `MEMBERSHIP_REACTIVATED` | `membership.reactivated` | After reactivation | `membership_id`, `user_id` |
| `MEMBERSHIP_CANCELED` | `membership.canceled` | After cancellation | `membership_id`, `user_id`, `reason` |
| `POINTS_EARNED` | `points.earned` | After point earning | `membership_id`, `user_id`, `points_earned`, `multiplier`, `source`, `balance_after` |
| `POINTS_REDEEMED` | `points.redeemed` | After point redemption | `membership_id`, `user_id`, `points_redeemed`, `reward_code`, `balance_after` |
| `BENEFIT_USED` | `benefit.used` | After benefit use | `membership_id`, `user_id`, `benefit_code` |

### Event Publishing (`events/publishers.py`)
```python
from datetime import datetime, timezone
from typing import Dict, Any

async def publish_membership_enrolled(
    event_bus,
    membership_id: str,
    user_id: str,
    tier_code: str,
    enrollment_bonus: int
) -> None:
    """Publish membership.enrolled event"""
    await event_bus.publish(
        "membership.enrolled",
        {
            "event_type": "MEMBERSHIP_ENROLLED",
            "source": "membership_service",
            "data": {
                "membership_id": membership_id,
                "user_id": user_id,
                "tier_code": tier_code,
                "enrollment_bonus": enrollment_bonus,
                "enrolled_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )

async def publish_points_earned(
    event_bus,
    membership_id: str,
    user_id: str,
    points_earned: int,
    multiplier: float,
    source: str,
    balance_after: int
) -> None:
    """Publish points.earned event"""
    await event_bus.publish(
        "points.earned",
        {
            "event_type": "POINTS_EARNED",
            "source": "membership_service",
            "data": {
                "membership_id": membership_id,
                "user_id": user_id,
                "points_earned": points_earned,
                "multiplier": multiplier,
                "source": source,
                "balance_after": balance_after,
                "earned_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )

async def publish_membership_tier_upgraded(
    event_bus,
    membership_id: str,
    user_id: str,
    previous_tier: str,
    new_tier: str,
    tier_points: int
) -> None:
    """Publish membership.tier_upgraded event"""
    await event_bus.publish(
        "membership.tier_upgraded",
        {
            "event_type": "MEMBERSHIP_TIER_UPGRADED",
            "source": "membership_service",
            "data": {
                "membership_id": membership_id,
                "user_id": user_id,
                "previous_tier": previous_tier,
                "new_tier": new_tier,
                "tier_points": tier_points,
                "upgraded_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
```

### Event Payload Examples

**membership.enrolled**
```json
{
  "event_type": "MEMBERSHIP_ENROLLED",
  "source": "membership_service",
  "data": {
    "membership_id": "mem_abc123def456",
    "user_id": "usr_xyz789",
    "tier_code": "bronze",
    "enrollment_bonus": 500,
    "enrolled_at": "2025-01-15T10:00:00Z"
  }
}
```

**points.earned**
```json
{
  "event_type": "POINTS_EARNED",
  "source": "membership_service",
  "data": {
    "membership_id": "mem_abc123def456",
    "user_id": "usr_xyz789",
    "points_earned": 1250,
    "multiplier": 1.25,
    "source": "order_completed",
    "balance_after": 5750,
    "earned_at": "2025-01-15T10:30:00Z"
  }
}
```

---

## Event Subscription Pattern

### Events Subscribed

| Event | Source | Handler | Action |
|-------|--------|---------|--------|
| `order.completed` | order_service | `handle_order_completed` | Award points for purchase |
| `user.deleted` | account_service | `handle_user_deleted` | Delete all user membership data (GDPR) |
| `subscription.renewed` | subscription_service | `handle_subscription_renewed` | Sync tier benefits with subscription |

### Handler (`events/handlers.py`)
```python
import logging
from typing import Dict, Callable

logger = logging.getLogger(__name__)

class MembershipEventHandlers:
    """Membership service event handlers"""

    def __init__(self, membership_service):
        self.service = membership_service
        self.repository = membership_service.repository

    def get_event_handler_map(self) -> Dict[str, Callable]:
        return {
            "order.completed": self.handle_order_completed,
            "user.deleted": self.handle_user_deleted,
            "subscription.renewed": self.handle_subscription_renewed,
        }

    async def handle_order_completed(self, event_data: dict):
        """Award points for completed order"""
        user_id = event_data.get("user_id")
        order_total = event_data.get("total_amount", 0)

        if user_id and order_total > 0:
            # Calculate base points: $1 = 100 points
            base_points = int(order_total * 100)

            try:
                await self.service.earn_points({
                    "user_id": user_id,
                    "points_amount": base_points,
                    "source": "order_completed",
                    "reference_id": event_data.get("order_id"),
                    "description": f"Order ${order_total:.2f}"
                })
                logger.info(f"Awarded {base_points} points to {user_id}")
            except Exception as e:
                logger.error(f"Failed to award points: {e}")

    async def handle_user_deleted(self, event_data: dict):
        """GDPR compliance - delete all user data"""
        user_id = event_data.get("user_id")
        if user_id:
            deleted_count = await self.repository.delete_user_data(user_id)
            logger.info(f"Deleted {deleted_count} membership records for user {user_id}")

    async def handle_subscription_renewed(self, event_data: dict):
        """Sync tier benefits when subscription renews"""
        user_id = event_data.get("user_id")
        tier_code = event_data.get("tier_code")

        if user_id and tier_code:
            # Check if membership tier should be synced with subscription
            membership = await self.repository.get_membership_by_user(user_id)
            if membership:
                logger.info(f"Subscription renewed for user {user_id}, tier: {tier_code}")
```

---

## Client Pattern (Sync)

### Dependencies (Outbound HTTP Calls)

| Client | Target Service | Purpose |
|--------|----------------|---------|
| `AccountClient` | `account_service:8202` | Verify user exists (optional) |

### Client Implementation (`clients/account_client.py`)
```python
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AccountClient:
    """Sync HTTP client for account_service"""

    def __init__(self, base_url: str = "http://localhost:8202"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from account_service (optional validation)"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to validate user {user_id}: {e}")
            return None  # Graceful degradation

    async def close(self):
        await self.client.aclose()
```

---

## Repository Pattern

### Schema: `membership`

### Tables

| Table | Purpose |
|-------|---------|
| `membership.memberships` | Main membership storage |
| `membership.membership_history` | Audit trail of all actions |
| `membership.tiers` | Tier reference data |
| `membership.tier_benefits` | Tier-benefit mappings |

### Database Schema (`001_create_membership_tables.sql`)

**memberships**
```sql
CREATE SCHEMA IF NOT EXISTS membership;

CREATE TABLE IF NOT EXISTS membership.memberships (
    id SERIAL PRIMARY KEY,
    membership_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- Tier
    tier_code VARCHAR(20) NOT NULL DEFAULT 'bronze',
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    -- Points
    points_balance BIGINT NOT NULL DEFAULT 0,
    tier_points BIGINT NOT NULL DEFAULT 0,
    lifetime_points BIGINT NOT NULL DEFAULT 0,
    pending_points BIGINT NOT NULL DEFAULT 0,

    -- Dates
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expiration_date TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,

    -- Auto-renewal
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    enrollment_source VARCHAR(50),
    promo_code VARCHAR(50),
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_memberships_user_id ON membership.memberships(user_id);
CREATE INDEX idx_memberships_status ON membership.memberships(status);
CREATE INDEX idx_memberships_tier ON membership.memberships(tier_code);
CREATE UNIQUE INDEX idx_memberships_user_active
    ON membership.memberships(user_id)
    WHERE status IN ('active', 'pending');
```

**membership_history**
```sql
CREATE TABLE IF NOT EXISTS membership.membership_history (
    id SERIAL PRIMARY KEY,
    history_id VARCHAR(50) UNIQUE NOT NULL,
    membership_id VARCHAR(50) NOT NULL,

    -- Action
    action VARCHAR(30) NOT NULL,
    points_change BIGINT NOT NULL DEFAULT 0,
    balance_after BIGINT,
    previous_tier VARCHAR(20),
    new_tier VARCHAR(20),

    -- Context
    source VARCHAR(50),
    reference_id VARCHAR(100),
    reward_code VARCHAR(50),
    benefit_code VARCHAR(50),
    description TEXT,
    initiated_by VARCHAR(20) NOT NULL DEFAULT 'system',
    metadata JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_history_membership ON membership.membership_history(membership_id);
CREATE INDEX idx_history_created ON membership.membership_history(created_at DESC);
```

**tiers**
```sql
CREATE TABLE IF NOT EXISTS membership.tiers (
    id SERIAL PRIMARY KEY,
    tier_code VARCHAR(20) UNIQUE NOT NULL,
    tier_name VARCHAR(50) NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    qualification_threshold BIGINT NOT NULL DEFAULT 0,
    point_multiplier DECIMAL(4, 2) NOT NULL DEFAULT 1.0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data
INSERT INTO membership.tiers (tier_code, tier_name, display_order, qualification_threshold, point_multiplier) VALUES
('bronze', 'Bronze', 1, 0, 1.0),
('silver', 'Silver', 2, 5000, 1.25),
('gold', 'Gold', 3, 20000, 1.5),
('platinum', 'Platinum', 4, 50000, 2.0),
('diamond', 'Diamond', 5, 100000, 3.0);
```

### Indexes
```sql
CREATE INDEX idx_memberships_user_id ON membership.memberships(user_id);
CREATE INDEX idx_memberships_status ON membership.memberships(status);
CREATE INDEX idx_memberships_tier ON membership.memberships(tier_code);
CREATE INDEX idx_history_membership ON membership.membership_history(membership_id);
CREATE INDEX idx_history_created ON membership.membership_history(created_at DESC);
```

---

## Service Registration Pattern

### Routes Registry (`routes_registry.py`)
```python
SERVICE_ROUTES = [
    {"path": "/health", "methods": ["GET"], "auth_required": False},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False},
    {"path": "/api/v1/memberships", "methods": ["GET", "POST"], "auth_required": True},
    {"path": "/api/v1/memberships/{membership_id}", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/memberships/user/{user_id}", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/memberships/{membership_id}/cancel", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/memberships/{membership_id}/suspend", "methods": ["PUT"], "auth_required": True},
    {"path": "/api/v1/memberships/{membership_id}/reactivate", "methods": ["PUT"], "auth_required": True},
    {"path": "/api/v1/memberships/{membership_id}/tier", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/memberships/points/earn", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/memberships/points/redeem", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/memberships/points/balance", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/memberships/{membership_id}/benefits", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/memberships/{membership_id}/benefits/use", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/memberships/{membership_id}/history", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/memberships/stats", "methods": ["GET"], "auth_required": True},
]

SERVICE_METADATA = {
    "service_name": "membership_service",
    "version": "1.0.0",
    "tags": ["v1", "membership", "loyalty", "points"],
    "capabilities": [
        "enrollment",
        "points_management",
        "tier_progression",
        "benefits_tracking",
        "history"
    ]
}
```

### API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/health/detailed` | Detailed health with DB status |
| POST | `/api/v1/memberships` | Enroll membership |
| GET | `/api/v1/memberships` | List memberships |
| GET | `/api/v1/memberships/{id}` | Get membership by ID |
| GET | `/api/v1/memberships/user/{user_id}` | Get membership by user |
| POST | `/api/v1/memberships/{id}/cancel` | Cancel membership |
| PUT | `/api/v1/memberships/{id}/suspend` | Suspend membership |
| PUT | `/api/v1/memberships/{id}/reactivate` | Reactivate membership |
| GET | `/api/v1/memberships/{id}/tier` | Get tier status |
| POST | `/api/v1/memberships/points/earn` | Earn points |
| POST | `/api/v1/memberships/points/redeem` | Redeem points |
| GET | `/api/v1/memberships/points/balance` | Get points balance |
| GET | `/api/v1/memberships/{id}/benefits` | List benefits |
| POST | `/api/v1/memberships/{id}/benefits/use` | Use benefit |
| GET | `/api/v1/memberships/{id}/history` | Get history |
| GET | `/api/v1/memberships/stats` | Get statistics |

---

## Migration Pattern

### Migration Files
```
migrations/
├── 001_create_membership_tables.sql    # Core tables and indexes
└── 002_add_tier_benefits.sql           # Tier benefits table and seed data
```

### Migration Sequence
1. `001_create_membership_tables.sql` - Creates memberships, history, tiers tables
2. `002_add_tier_benefits.sql` - Creates tier_benefits table and seeds data

### Schema Evolution Pattern
- New migrations follow `NNN_description.sql` naming
- Each migration is idempotent (IF NOT EXISTS)
- Triggers auto-update `updated_at` timestamps

---

## Lifecycle Pattern

### Startup Sequence (`main.py`)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize ConfigManager
    config = ConfigManager()

    # 2. Setup logger
    logger = setup_service_logger("membership_service")

    # 3. Initialize event bus (NATS)
    event_bus = NATSClient()
    await event_bus.connect()

    # 4. Create service via factory
    membership_service = create_membership_service(config, event_bus)

    # 5. Load tier cache
    await membership_service.initialize()

    # 6. Register event handlers (subscriptions)
    handlers = MembershipEventHandlers(membership_service)
    for event_type, handler in handlers.get_event_handler_map().items():
        await event_bus.subscribe(event_type, handler)

    # 7. Initialize optional clients
    account_client = AccountClient()

    # 8. Register with Consul
    await register_service_routes(SERVICE_ROUTES, SERVICE_METADATA)

    # 9. Store in app state
    app.state.service = membership_service
    app.state.account_client = account_client

    logger.info("Membership service started on port 8250")

    yield  # App runs

    # Shutdown
    await account_client.close()
    await event_bus.close()
    logger.info("Membership service stopped")
```

### Shutdown Sequence
1. Deregister from Consul
2. Close service clients (AccountClient)
3. Close event bus (NATS)
4. Log shutdown complete

---

## Configuration Pattern

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMBERSHIP_SERVICE_PORT` | `8250` | Service port |
| `MEMBERSHIP_SERVICE_HOST` | `0.0.0.0` | Service host |
| `CONSUL_ENABLED` | `true` | Enable Consul registration |
| `NATS_URL` | `nats://nats:4222` | NATS connection URL |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `TIER_CACHE_TTL` | `3600` | Tier cache TTL in seconds |

### ConfigManager Usage
```python
from core.config_manager import ConfigManager

config = ConfigManager()

# Access configuration
port = config.get("MEMBERSHIP_SERVICE_PORT", 8250)
nats_url = config.get("NATS_URL", "nats://nats:4222")
db_url = config.get("DATABASE_URL")
```

---

## Logging Pattern

### Logger Setup
```python
from core.logger import setup_service_logger

logger = setup_service_logger("membership_service")

# Usage examples
logger.info("Membership enrolled", extra={"membership_id": mem_id, "user_id": user_id})
logger.info(f"Points earned: {points}", extra={"multiplier": 1.25})
logger.warning(f"Insufficient points for {user_id}")
logger.error(f"Failed to update tier: {error}", exc_info=True)
```

### Structured Log Fields
- `membership_id`: Membership identifier
- `user_id`: User identifier
- `tier_code`: Tier code
- `points_amount`: Points in transaction
- `multiplier`: Tier multiplier applied
- `action`: Action type (enrolled, points_earned, etc.)
- `duration_ms`: Operation duration

---

## Compliance Checklist

- [x] `protocols.py` with DI interfaces (MembershipRepositoryProtocol, EventBusProtocol)
- [x] `factory.py` for service creation (create_membership_service)
- [x] `routes_registry.py` for Consul (SERVICE_ROUTES, SERVICE_METADATA)
- [x] `migrations/` folder with SQL files (001, 002)
- [x] `events/handlers.py` for subscriptions (order.completed, user.deleted, subscription.renewed)
- [x] `events/publishers.py` for publishing (membership.*, points.*, benefit.*)
- [x] `clients/` for sync dependencies (account_client.py)
- [x] Error handling with custom exceptions (MembershipServiceError hierarchy)
- [x] Structured logging (setup_service_logger)
- [x] ConfigManager usage

---

**Version**: 1.0.0
**Last Updated**: 2025-12-19
**Pattern Reference**: `.claude/skills/cdd-system-contract/SKILL.md`
