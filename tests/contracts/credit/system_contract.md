# Credit Service - System Contract

**Implementation Patterns and Architecture for Credit Service**

This document defines HOW credit_service implements the 12 standard patterns.
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
| **Service Name** | `credit_service` |
| **Port** | `8229` |
| **Schema** | `credit` |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/credit_service/` |

---

## Architecture Pattern

### File Structure
```
microservices/credit_service/
├── __init__.py
├── main.py                    # FastAPI app + lifecycle
├── credit_service.py          # Business logic layer
├── credit_repository.py       # Data access layer (PostgreSQL)
├── models.py                  # Pydantic models (CreditAccount, Transaction, etc.)
├── protocols.py               # DI interfaces
├── factory.py                 # DI factory
├── routes_registry.py         # Consul route registration
├── clients/
│   ├── __init__.py
│   ├── account_client.py      # Sync call to account_service
│   └── subscription_client.py # Sync call to subscription_service
├── events/
│   ├── __init__.py
│   ├── models.py              # Event Pydantic models
│   ├── publishers.py          # NATS publish helpers
│   └── handlers.py            # NATS subscribe handlers
└── migrations/
    ├── 001_create_credit_tables.sql
    └── 002_add_indexes.sql
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring |
| Business | `credit_service.py` | Account CRUD, allocation, consumption, FIFO logic |
| Data | `credit_repository.py` | PostgreSQL queries, schema operations |
| External | `clients/` | HTTP calls to account_service, subscription_service |
| Async | `events/` | NATS event publishing and subscriptions |

---

## Dependency Injection Pattern

### Protocols (`protocols.py`)
```python
from typing import Protocol, runtime_checkable, Dict, Any, Optional, List
from datetime import datetime

@runtime_checkable
class CreditRepositoryProtocol(Protocol):
    """Repository interface for credit operations"""

    async def create_account(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new credit account"""
        ...

    async def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account by ID"""
        ...

    async def get_account_by_user_type(self, user_id: str, credit_type: str) -> Optional[Dict[str, Any]]:
        """Get account by user and type"""
        ...

    async def get_user_accounts(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """Get all accounts for user"""
        ...

    async def update_account_balance(self, account_id: str, balance_delta: int) -> bool:
        """Update account balance atomically"""
        ...

    async def create_transaction(self, txn_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create transaction record"""
        ...

    async def get_user_transactions(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """Get transactions for user"""
        ...

    async def create_allocation(self, alloc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create allocation record"""
        ...

    async def get_expiring_allocations(self, before: datetime) -> List[Dict[str, Any]]:
        """Get allocations expiring before date"""
        ...

    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create campaign"""
        ...

    async def get_campaign_by_id(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign by ID"""
        ...

    async def update_campaign_budget(self, campaign_id: str, amount: int) -> bool:
        """Update campaign allocated_amount"""
        ...

    async def get_aggregated_balance(self, user_id: str) -> Dict[str, int]:
        """Get aggregated balance by credit type"""
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


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for account_service client"""

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from account_service"""
        ...

    async def validate_user(self, user_id: str) -> bool:
        """Validate user exists and is active"""
        ...


@runtime_checkable
class SubscriptionClientProtocol(Protocol):
    """Interface for subscription_service client"""

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active subscription for user"""
        ...

    async def get_subscription_credits(self, subscription_id: str) -> Optional[int]:
        """Get credits included in subscription"""
        ...
```

### Factory (`factory.py`)
```python
from core.config_manager import ConfigManager
from .credit_service import CreditService
from .credit_repository import CreditRepository
from .clients.account_client import AccountClient
from .clients.subscription_client import SubscriptionClient

def create_credit_service(
    config: ConfigManager,
    event_bus=None,
    account_client=None,
    subscription_client=None,
) -> CreditService:
    """Create CreditService with real dependencies"""
    repository = CreditRepository(config=config)

    if account_client is None:
        account_client = AccountClient(config=config)

    if subscription_client is None:
        subscription_client = SubscriptionClient(config=config)

    return CreditService(
        repository=repository,
        event_bus=event_bus,
        account_client=account_client,
        subscription_client=subscription_client,
    )
```

---

## Event Publishing Pattern

### Events Published

| Event | Subject | Trigger | Data |
|-------|---------|---------|------|
| `CREDIT_ALLOCATED` | `credit.allocated` | After credit allocation | `allocation_id`, `user_id`, `credit_type`, `amount`, `expires_at`, `balance_after` |
| `CREDIT_CONSUMED` | `credit.consumed` | After credit consumption | `transaction_ids`, `user_id`, `amount`, `billing_record_id`, `balance_after` |
| `CREDIT_EXPIRED` | `credit.expired` | After expiration processing | `user_id`, `amount`, `credit_type`, `balance_after` |
| `CREDIT_TRANSFERRED` | `credit.transferred` | After credit transfer | `transfer_id`, `from_user_id`, `to_user_id`, `amount`, `credit_type` |
| `CREDIT_EXPIRING_SOON` | `credit.expiring_soon` | 7 days before expiration | `user_id`, `amount`, `expires_at`, `credit_type` |
| `CAMPAIGN_BUDGET_EXHAUSTED` | `credit.campaign.budget_exhausted` | Budget depleted | `campaign_id`, `name`, `total_budget`, `allocated_amount` |

### Event Publishing (`events/publishers.py`)
```python
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class CreditEventPublisher:
    """Helper for publishing credit events"""

    def __init__(self, event_bus):
        self.event_bus = event_bus

    async def publish_credit_allocated(
        self,
        allocation_id: str,
        user_id: str,
        credit_type: str,
        amount: int,
        campaign_id: Optional[str],
        expires_at: datetime,
        balance_after: int,
    ) -> None:
        """Publish credit.allocated event"""
        if self.event_bus:
            await self.event_bus.publish(
                "credit.allocated",
                {
                    "event_type": "CREDIT_ALLOCATED",
                    "source": "credit_service",
                    "data": {
                        "allocation_id": allocation_id,
                        "user_id": user_id,
                        "credit_type": credit_type,
                        "amount": amount,
                        "campaign_id": campaign_id,
                        "expires_at": expires_at.isoformat(),
                        "balance_after": balance_after,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )

    async def publish_credit_consumed(
        self,
        transaction_ids: list,
        user_id: str,
        amount: int,
        billing_record_id: Optional[str],
        balance_before: int,
        balance_after: int,
    ) -> None:
        """Publish credit.consumed event"""
        if self.event_bus:
            await self.event_bus.publish(
                "credit.consumed",
                {
                    "event_type": "CREDIT_CONSUMED",
                    "source": "credit_service",
                    "data": {
                        "transaction_ids": transaction_ids,
                        "user_id": user_id,
                        "amount": amount,
                        "billing_record_id": billing_record_id,
                        "balance_before": balance_before,
                        "balance_after": balance_after,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )

    async def publish_credit_expired(
        self,
        user_id: str,
        amount: int,
        credit_type: str,
        balance_after: int,
    ) -> None:
        """Publish credit.expired event"""
        if self.event_bus:
            await self.event_bus.publish(
                "credit.expired",
                {
                    "event_type": "CREDIT_EXPIRED",
                    "source": "credit_service",
                    "data": {
                        "user_id": user_id,
                        "amount": amount,
                        "credit_type": credit_type,
                        "balance_after": balance_after,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
```

### Event Payload Examples

**credit.allocated**
```json
{
  "event_type": "CREDIT_ALLOCATED",
  "source": "credit_service",
  "data": {
    "allocation_id": "cred_alloc_abc123def456",
    "user_id": "usr_xyz789",
    "credit_type": "bonus",
    "amount": 1000,
    "campaign_id": "camp_signup2025",
    "expires_at": "2026-03-18T00:00:00Z",
    "balance_after": 2500,
    "timestamp": "2025-12-18T10:00:00Z"
  }
}
```

**credit.consumed**
```json
{
  "event_type": "CREDIT_CONSUMED",
  "source": "credit_service",
  "data": {
    "transaction_ids": ["cred_txn_abc123", "cred_txn_def456"],
    "user_id": "usr_xyz789",
    "amount": 500,
    "billing_record_id": "bill_xyz789",
    "balance_before": 2500,
    "balance_after": 2000,
    "timestamp": "2025-12-18T11:00:00Z"
  }
}
```

---

## Event Subscription Pattern

### Events Subscribed

| Event | Source | Handler | Action |
|-------|--------|---------|--------|
| `user.created` | account_service | `handle_user_created` | Allocate sign-up bonus credits |
| `subscription.created` | subscription_service | `handle_subscription_created` | Allocate initial subscription credits |
| `subscription.renewed` | subscription_service | `handle_subscription_renewed` | Allocate monthly subscription credits |
| `order.completed` | order_service | `handle_order_completed` | Process referral credits |
| `user.deleted` | account_service | `handle_user_deleted` | Archive credit accounts (GDPR) |

### Handler (`events/handlers.py`)
```python
import logging
from typing import Dict, Callable

logger = logging.getLogger(__name__)

class CreditEventHandlers:
    """Credit service event handlers"""

    def __init__(self, credit_service):
        self.service = credit_service
        self.repository = credit_service.repository

    def get_event_handler_map(self) -> Dict[str, Callable]:
        return {
            "user.created": self.handle_user_created,
            "subscription.created": self.handle_subscription_created,
            "subscription.renewed": self.handle_subscription_renewed,
            "order.completed": self.handle_order_completed,
            "user.deleted": self.handle_user_deleted,
        }

    async def handle_user_created(self, event_data: dict):
        """Allocate sign-up bonus for new users"""
        user_id = event_data.get("user_id")
        if not user_id:
            logger.warning("user.created event missing user_id")
            return

        # Find active sign-up bonus campaign
        campaign = await self.service.get_active_signup_campaign()
        if campaign:
            try:
                await self.service.allocate_from_campaign(
                    user_id=user_id,
                    campaign_id=campaign["campaign_id"]
                )
                logger.info(f"Sign-up bonus allocated for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to allocate sign-up bonus: {e}")

    async def handle_subscription_created(self, event_data: dict):
        """Allocate initial subscription credits"""
        user_id = event_data.get("user_id")
        subscription_id = event_data.get("subscription_id")
        credits_included = event_data.get("credits_included", 0)

        if user_id and credits_included > 0:
            try:
                await self.service.allocate_credits(
                    user_id=user_id,
                    credit_type="subscription",
                    amount=credits_included,
                    description=f"Subscription credits: {subscription_id}",
                    reference_id=subscription_id,
                    reference_type="subscription",
                )
                logger.info(f"Subscription credits allocated for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to allocate subscription credits: {e}")

    async def handle_subscription_renewed(self, event_data: dict):
        """Allocate monthly subscription credits on renewal"""
        user_id = event_data.get("user_id")
        subscription_id = event_data.get("subscription_id")
        credits_included = event_data.get("credits_included", 0)
        period_end = event_data.get("period_end")

        if user_id and credits_included > 0:
            try:
                await self.service.allocate_credits(
                    user_id=user_id,
                    credit_type="subscription",
                    amount=credits_included,
                    description=f"Monthly subscription credits: {subscription_id}",
                    reference_id=subscription_id,
                    reference_type="subscription",
                    expires_at=period_end,  # Expire with subscription period
                )
                logger.info(f"Monthly credits allocated for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to allocate monthly credits: {e}")

    async def handle_order_completed(self, event_data: dict):
        """Process referral credits when order completed with referral code"""
        user_id = event_data.get("user_id")
        referral_code = event_data.get("referral_code")

        if not referral_code:
            return  # Not a referred order

        # Find referrer by code
        referrer = await self.service.get_referrer_by_code(referral_code)
        if referrer:
            try:
                # Allocate to referee (new customer)
                await self.service.allocate_credits(
                    user_id=user_id,
                    credit_type="referral",
                    amount=500,  # Configurable
                    description="Referral welcome bonus",
                )
                # Allocate to referrer
                await self.service.allocate_credits(
                    user_id=referrer["user_id"],
                    credit_type="referral",
                    amount=500,  # Configurable
                    description=f"Referral reward for {user_id}",
                )
                logger.info(f"Referral credits allocated for {user_id} and {referrer['user_id']}")
            except Exception as e:
                logger.error(f"Failed to process referral credits: {e}")

    async def handle_user_deleted(self, event_data: dict):
        """GDPR compliance - archive all user credit data"""
        user_id = event_data.get("user_id")
        if user_id:
            try:
                deleted_count = await self.repository.delete_user_data(user_id)
                logger.info(f"Deleted {deleted_count} credit records for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to delete user credit data: {e}")
```

---

## Client Pattern (Sync)

### Dependencies (Outbound HTTP Calls)

| Client | Target Service | Purpose |
|--------|----------------|---------|
| `AccountClient` | `account_service:8202` | Verify user exists, get user tier |
| `SubscriptionClient` | `subscription_service:8228` | Get subscription status, credits included |

### Client Implementation (`clients/account_client.py`)
```python
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AccountClient:
    """Sync HTTP client for account_service"""

    def __init__(self, base_url: str = "http://localhost:8202", config=None):
        if config:
            base_url = config.get("ACCOUNT_SERVICE_URL", base_url)
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from account_service"""
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
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def validate_user(self, user_id: str) -> bool:
        """Validate user exists and is active"""
        user = await self.get_user(user_id)
        return user is not None and user.get("is_active", False)

    async def close(self):
        await self.client.aclose()
```

### Client Implementation (`clients/subscription_client.py`)
```python
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SubscriptionClient:
    """Sync HTTP client for subscription_service"""

    def __init__(self, base_url: str = "http://localhost:8228", config=None):
        if config:
            base_url = config.get("SUBSCRIPTION_SERVICE_URL", base_url)
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active subscription for user"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/user/{user_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get subscription for user {user_id}: {e}")
            return None

    async def get_subscription_credits(self, subscription_id: str) -> Optional[int]:
        """Get credits included in subscription plan"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/{subscription_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("credits_included", 0)
        except Exception as e:
            logger.error(f"Failed to get subscription credits: {e}")
            return None

    async def close(self):
        await self.client.aclose()
```

---

## Repository Pattern

### Schema: `credit`

### Tables

| Table | Purpose |
|-------|---------|
| `credit.credit_accounts` | Credit account storage per user per type |
| `credit.credit_transactions` | Immutable transaction log |
| `credit.credit_campaigns` | Promotional campaign definitions |
| `credit.credit_allocations` | Campaign-to-user allocation tracking |

### Database Schema (`001_create_credit_tables.sql`)

**credit_accounts**
```sql
CREATE SCHEMA IF NOT EXISTS credit;

CREATE TABLE IF NOT EXISTS credit.credit_accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    credit_type VARCHAR(30) NOT NULL,
    balance INTEGER DEFAULT 0,
    total_allocated INTEGER DEFAULT 0,
    total_consumed INTEGER DEFAULT 0,
    total_expired INTEGER DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'CREDIT',
    expiration_policy VARCHAR(30) DEFAULT 'fixed_days',
    expiration_days INTEGER DEFAULT 90,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, credit_type)
);
```

**credit_transactions**
```sql
CREATE TABLE IF NOT EXISTS credit.credit_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    reference_id VARCHAR(100),
    reference_type VARCHAR(30),
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**credit_campaigns**
```sql
CREATE TABLE IF NOT EXISTS credit.credit_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    credit_type VARCHAR(30) NOT NULL,
    credit_amount INTEGER NOT NULL,
    total_budget INTEGER NOT NULL,
    allocated_amount INTEGER DEFAULT 0,
    eligibility_rules JSONB DEFAULT '{}'::jsonb,
    allocation_rules JSONB DEFAULT '{}'::jsonb,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiration_days INTEGER DEFAULT 90,
    max_allocations_per_user INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**credit_allocations**
```sql
CREATE TABLE IF NOT EXISTS credit.credit_allocations (
    id SERIAL PRIMARY KEY,
    allocation_id VARCHAR(50) UNIQUE NOT NULL,
    campaign_id VARCHAR(50),
    user_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50),
    amount INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    expires_at TIMESTAMP WITH TIME ZONE,
    expired_amount INTEGER DEFAULT 0,
    consumed_amount INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Indexes (`002_add_indexes.sql`)
```sql
-- Account indexes
CREATE INDEX IF NOT EXISTS idx_credit_accounts_user_id ON credit.credit_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_type ON credit.credit_accounts(credit_type);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_user_type ON credit.credit_accounts(user_id, credit_type);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_active ON credit.credit_accounts(is_active) WHERE is_active = TRUE;

-- Transaction indexes
CREATE INDEX IF NOT EXISTS idx_credit_transactions_account_id ON credit.credit_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit.credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit.credit_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON credit.credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_expires_at ON credit.credit_transactions(expires_at) WHERE expires_at IS NOT NULL;

-- Campaign indexes
CREATE INDEX IF NOT EXISTS idx_credit_campaigns_active ON credit.credit_campaigns(is_active);
CREATE INDEX IF NOT EXISTS idx_credit_campaigns_dates ON credit.credit_campaigns(start_date, end_date);

-- Allocation indexes
CREATE INDEX IF NOT EXISTS idx_credit_allocations_user_id ON credit.credit_allocations(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_allocations_campaign ON credit.credit_allocations(campaign_id);
CREATE INDEX IF NOT EXISTS idx_credit_allocations_expires_at ON credit.credit_allocations(expires_at);
CREATE INDEX IF NOT EXISTS idx_credit_allocations_user_campaign ON credit.credit_allocations(user_id, campaign_id);
```

---

## Service Registration Pattern

### Routes Registry (`routes_registry.py`)
```python
SERVICE_ROUTES = [
    {"path": "/health", "methods": ["GET"], "auth_required": False},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False},
    {"path": "/api/v1/credits/accounts", "methods": ["GET", "POST"], "auth_required": True},
    {"path": "/api/v1/credits/accounts/{account_id}", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/credits/balance", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/credits/allocate", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/credits/consume", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/credits/check-availability", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/credits/transfer", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/credits/transactions", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/credits/campaigns", "methods": ["GET", "POST"], "auth_required": True},
    {"path": "/api/v1/credits/campaigns/{campaign_id}", "methods": ["GET", "PUT"], "auth_required": True},
    {"path": "/api/v1/credits/statistics", "methods": ["GET"], "auth_required": True},
]

SERVICE_METADATA = {
    "service_name": "credit_service",
    "version": "1.0.0",
    "tags": ["v1", "credit", "promotional", "bonus"],
    "capabilities": [
        "credit_accounts",
        "credit_allocation",
        "credit_consumption",
        "credit_expiration",
        "credit_transfer",
        "campaign_management",
        "fifo_expiration",
        "event_driven"
    ]
}
```

### API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/detailed` | Detailed health with dependencies |
| POST | `/api/v1/credits/accounts` | Create credit account |
| GET | `/api/v1/credits/accounts` | List user accounts |
| GET | `/api/v1/credits/accounts/{account_id}` | Get account by ID |
| GET | `/api/v1/credits/balance` | Get aggregated balance |
| POST | `/api/v1/credits/allocate` | Allocate credits |
| POST | `/api/v1/credits/consume` | Consume credits (FIFO) |
| POST | `/api/v1/credits/check-availability` | Check credit availability |
| POST | `/api/v1/credits/transfer` | Transfer credits |
| GET | `/api/v1/credits/transactions` | List transactions |
| POST | `/api/v1/credits/campaigns` | Create campaign |
| GET | `/api/v1/credits/campaigns` | List campaigns |
| GET | `/api/v1/credits/campaigns/{campaign_id}` | Get campaign |
| PUT | `/api/v1/credits/campaigns/{campaign_id}` | Update campaign |
| GET | `/api/v1/credits/statistics` | Get credit statistics |

---

## Migration Pattern

### Migration Files
```
migrations/
├── 001_create_credit_tables.sql    # Initial schema creation
└── 002_add_indexes.sql             # Performance indexes
```

### Migration Sequence
1. `001_create_credit_tables.sql` - Creates schema and all tables
2. `002_add_indexes.sql` - Adds performance indexes

### Schema Evolution Pattern
- New migrations follow `NNN_description.sql` naming
- Each migration is idempotent (IF NOT EXISTS)
- Triggers auto-update `updated_at` timestamps

---

## Lifecycle Pattern

### Startup Sequence (`main.py`)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import NATSClient
from .factory import create_credit_service
from .events.handlers import CreditEventHandlers
from .clients.account_client import AccountClient
from .clients.subscription_client import SubscriptionClient
from .routes_registry import SERVICE_ROUTES, SERVICE_METADATA

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize ConfigManager
    config = ConfigManager()

    # 2. Setup logger
    logger = setup_service_logger("credit_service")

    # 3. Initialize event bus (NATS)
    event_bus = NATSClient()
    await event_bus.connect()

    # 4. Initialize service clients
    account_client = AccountClient(config=config)
    subscription_client = SubscriptionClient(config=config)

    # 5. Create service via factory
    credit_service = create_credit_service(
        config=config,
        event_bus=event_bus,
        account_client=account_client,
        subscription_client=subscription_client,
    )

    # 6. Register event handlers (subscriptions)
    handlers = CreditEventHandlers(credit_service)
    for event_type, handler in handlers.get_event_handler_map().items():
        await event_bus.subscribe(event_type, handler)

    # 7. Start expiration scheduler (APScheduler)
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        credit_service.process_expirations,
        'cron',
        hour=0,
        minute=0,
        id='credit_expiration_job'
    )
    scheduler.start()

    # 8. Register with Consul
    await register_service_routes(SERVICE_ROUTES, SERVICE_METADATA)

    # 9. Store in app state
    app.state.service = credit_service
    app.state.account_client = account_client
    app.state.subscription_client = subscription_client
    app.state.scheduler = scheduler

    logger.info("Credit service started")

    yield  # App runs

    # Shutdown
    scheduler.shutdown()
    await account_client.close()
    await subscription_client.close()
    await event_bus.close()
    logger.info("Credit service stopped")
```

### Shutdown Sequence
1. Stop expiration scheduler
2. Close service clients (AccountClient, SubscriptionClient)
3. Close event bus (NATS)
4. Deregister from Consul
5. Log shutdown complete

---

## Configuration Pattern

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CREDIT_SERVICE_PORT` | `8229` | Service port |
| `CREDIT_SERVICE_HOST` | `0.0.0.0` | Service host |
| `CONSUL_ENABLED` | `true` | Enable Consul registration |
| `NATS_URL` | `nats://nats:4222` | NATS connection URL |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `ACCOUNT_SERVICE_URL` | `http://account_service:8202` | Account service URL |
| `SUBSCRIPTION_SERVICE_URL` | `http://subscription_service:8228` | Subscription service URL |
| `DEFAULT_EXPIRATION_DAYS` | `90` | Default credit expiration |
| `EXPIRATION_WARNING_DAYS` | `7` | Days before expiration to warn |
| `TRANSFER_ENABLED` | `true` | Enable credit transfers |

### ConfigManager Usage
```python
from core.config_manager import ConfigManager

config = ConfigManager()

# Access configuration
port = config.get("CREDIT_SERVICE_PORT", 8229)
nats_url = config.get("NATS_URL", "nats://nats:4222")
db_url = config.get("DATABASE_URL")
default_expiration = config.get("DEFAULT_EXPIRATION_DAYS", 90)
```

---

## Logging Pattern

### Logger Setup
```python
from core.logger import setup_service_logger

logger = setup_service_logger("credit_service")

# Usage examples
logger.info("Credits allocated", extra={"allocation_id": allocation_id, "user_id": user_id, "amount": amount})
logger.info("Credits consumed", extra={"transaction_ids": txn_ids, "user_id": user_id, "amount": amount})
logger.warning(f"Credit expiration warning for user: {user_id}")
logger.error(f"Failed to allocate credits: {error}", exc_info=True)
```

### Structured Log Fields
- `account_id`: Credit account identifier
- `allocation_id`: Allocation record identifier
- `transaction_id`: Transaction identifier
- `campaign_id`: Campaign identifier
- `user_id`: User performing action
- `credit_type`: Type of credit
- `amount`: Credit amount
- `operation`: CRUD operation type
- `duration_ms`: Operation duration

---

## Compliance Checklist

- [ ] `protocols.py` with DI interfaces (CreditRepositoryProtocol, EventBusProtocol, AccountClientProtocol, SubscriptionClientProtocol)
- [ ] `factory.py` for service creation (create_credit_service)
- [ ] `routes_registry.py` for Consul (SERVICE_ROUTES, SERVICE_METADATA)
- [ ] `migrations/` folder with SQL files (001, 002)
- [ ] `events/handlers.py` for subscriptions (user.created, subscription.*, order.completed, user.deleted)
- [ ] `events/publishers.py` for publishing (credit.allocated, credit.consumed, credit.expired, etc.)
- [ ] `clients/` for sync dependencies (account_client.py, subscription_client.py)
- [ ] Error handling with custom exceptions (CreditServiceError hierarchy)
- [ ] Structured logging (setup_service_logger)
- [ ] ConfigManager usage
- [ ] Expiration job scheduling (APScheduler)
- [ ] FIFO consumption logic

---

**Version**: 1.0.0
**Last Updated**: 2025-12-18
**Pattern Reference**: `.claude/skills/cdd-system-contract/SKILL.md`
