# Event-Driven Microservices Architecture Design

## High-Level Architecture Overview

Your microservices follow a **Hybrid Communication Pattern**:
- **Synchronous** (HTTP/REST) for queries and critical path operations
- **Asynchronous** (NATS JetStream) for state changes and side effects

---

## Communication Patterns Decision Matrix

### When to Use SYNCHRONOUS (Client-based) Communication

Use HTTP client calls for:

| Scenario | Example | Reason |
|----------|---------|--------|
| **Read Operations** | Get user profile, Check device status | Immediate response needed |
| **Validation Checks** | Verify user exists, Check permissions | Must block until validated |
| **Critical Path** | User authentication, Payment authorization | Cannot proceed without result |
| **Transaction Coordination** | Multi-step operations requiring rollback | Need synchronous control flow |
| **Low Latency Requirements** | Real-time device commands, Live session data | Cannot tolerate event propagation delay |

**Pattern:**
```python
# Service A needs data from Service B
from service_b.client import ServiceBClient

result = await service_b_client.get_resource(resource_id)
if result:
    # Proceed with operation
```

---

### When to Use ASYNCHRONOUS (Event-driven) Communication

Use NATS events for:

| Scenario | Example | Reason |
|----------|---------|--------|
| **State Change Broadcasts** | User created, Payment completed | Multiple services need to react |
| **Side Effects** | Send notification, Create audit log | Non-blocking follow-up actions |
| **Long-Running Operations** | Batch processing, Report generation | Don't block caller |
| **Eventually Consistent** | Update caches, Sync read replicas | Consistency can be delayed |
| **Fan-out Notifications** | Notify all devices in family, Broadcast to org members | One-to-many communication |
| **Cross-Boundary Updates** | Update wallet from billing, Trigger OTA from device | Loose coupling between domains |

**Pattern:**
```python
# Service A publishes state change
await event_bus.publish_event(
    Event(
        event_type=EventType.USER_CREATED,
        source=ServiceSource.AUTH_SERVICE,
        data={"user_id": user_id, ...}
    )
)

# Service B, C, D subscribe and react independently
```

---

## Event-Driven Database Update Pattern

### Pattern: Event Sourcing with Eventual Consistency

**Flow:**
```
1. Service A: Operation → Update DB → Publish Event
2. Event Bus: Route event to subscribers
3. Service B: Receive Event → Update DB → Publish Downstream Event
4. Service C: Receive Event → Update DB (final state)
```

### Example: Billing → Wallet Flow

```
┌─────────────────┐
│  isA_Model      │
│  (Usage occurs) │
└────────┬────────┘
         │ publish: usage.recorded.model
         ▼
┌──────────────────────┐
│  Billing Service     │
│  Event Handler       │
├──────────────────────┤
│ 1. Receive event     │
│ 2. Calculate cost    │
│ 3. Update DB         │◄─── DB: billing_records table
│ 4. Publish event     │
└────────┬─────────────┘
         │ publish: billing.calculated
         ▼
┌──────────────────────┐
│  Wallet Service      │
│  Event Handler       │
├──────────────────────┤
│ 1. Receive event     │
│ 2. Check balance     │
│ 3. Deduct tokens     │◄─── DB: wallets table
│ 4. Update DB         │     transactions table
│ 5. Publish event     │
└────────┬─────────────┘
         │ publish: wallet.tokens.deducted
         ▼
┌──────────────────────┐
│ Notification Service │
│ (Optional subscriber)│
├──────────────────────┤
│ 1. Receive event     │
│ 2. Send notification │◄─── DB: notifications table
│ 3. Update DB         │
└──────────────────────┘
```

**Key Implementation:**
- Each service is **autonomous** - owns its DB schema
- Each service **publishes events** after successful DB commit
- Subscribers **idempotently** process events (use event IDs to dedupe)
- Failed events → retry with exponential backoff

---

## Service-to-Service Communication Map

### Core Services Communication Patterns

#### 1. **Account Service**
**Purpose:** User account management

**Synchronous Dependencies (Calls other services):**
- ✅ None (leaf service)

**Asynchronous Dependencies (Publishes events):**
- `user.created` → Auth, Wallet, Notification, Audit
- `user.updated` → Organization, Session
- `user.deleted` → Storage, Wallet, Session (cleanup)

**Who calls it:**
- Auth Service (user validation)
- Wallet Service (account verification)
- Organization Service (member validation)
- Payment Service (user lookup)

---

#### 2. **Auth Service**
**Purpose:** Authentication & device authentication

**Synchronous Dependencies:**
- → Account Service (verify user exists)
- → Device Service (device validation)
- → Organization Service (org membership check)

**Asynchronous Dependencies:**
- `user.logged_in` → Session, Telemetry, Audit
- `user.logged_out` → Session
- `device.authenticated` → Device Service

**Who calls it:**
- API Gateway (auth validation)
- All services (JWT validation - via shared library)

---

#### 3. **Authorization Service**
**Purpose:** RBAC permissions

**Synchronous Dependencies:**
- → Account Service (user validation)
- → Organization Service (role verification)

**Asynchronous Dependencies:**
- `permission.granted` → Audit
- `permission.revoked` → Audit, Session (force logout)

**Who calls it:**
- All services (permission checks)

---

#### 4. **Device Service**
**Purpose:** Smart frame device management

**Synchronous Dependencies:**
- → Organization Service (family/group membership)
- → Storage Service (content for display)
- → OTA Service (firmware check)

**Asynchronous Dependencies:**
- `device.registered` → Telemetry, Notification
- `device.online` → Organization (notify members)
- `device.offline` → Organization (notify members)
- `device.command_sent` → Event Service

**Who calls it:**
- Auth Service (device authentication)
- Organization Service (family device check)
- OTA Service (target device list)

---

#### 5. **Payment Service**
**Purpose:** Stripe payment processing

**Synchronous Dependencies:**
- → Account Service (user validation)
- → Wallet Service (balance check)
- → Order Service (order details)

**Asynchronous Dependencies:**
- `payment.completed` → Order, Wallet, Notification, Audit
- `payment.failed` → Order, Notification
- `payment.refunded` → Wallet, Order
- `subscription.created` → Wallet (add credits)
- `subscription.canceled` → Wallet, Notification

**Who calls it:**
- Order Service (create payment)
- Wallet Service (add balance)
- External: Stripe webhooks

---

#### 6. **Wallet Service**
**Purpose:** Token/credit management

**Synchronous Dependencies:**
- → Account Service (user validation)

**Asynchronous Dependencies (Subscribes):**
- `billing.calculated` → deduct tokens → publish `wallet.tokens.deducted`
- `payment.completed` → add tokens

**Asynchronous Dependencies (Publishes):**
- `wallet.tokens.deducted` → Notification, Compliance
- `wallet.tokens.insufficient` → Notification, Billing
- `wallet.balance.low` → Notification (alert user)

**Who calls it:**
- Payment Service (add balance)
- Order Service (check balance)
- Session Service (usage check)

---

#### 7. **Billing Service**
**Purpose:** Usage billing calculation

**Synchronous Dependencies:**
- → Product Service (pricing info)
- → Account Service (user validation)

**Asynchronous Dependencies (Subscribes):**
- `usage.recorded.*` (from isA_Model, isA_Agent, isA_MCP)

**Asynchronous Dependencies (Publishes):**
- `billing.calculated` → Wallet Service
- `billing.error` → Notification, Compliance

**Who calls it:**
- Compliance Service (billing reports)

---

#### 8. **Order Service**
**Purpose:** E-commerce orders

**Synchronous Dependencies:**
- → Payment Service (create payment intent)
- → Wallet Service (balance check)
- → Account Service (user validation)
- → Storage Service (digital goods delivery)

**Asynchronous Dependencies (Subscribes):**
- `payment.completed` → fulfill order
- `payment.failed` → cancel order

**Asynchronous Dependencies (Publishes):**
- `order.created` → Notification, Audit
- `order.fulfilled` → Notification, Storage
- `order.canceled` → Notification

**Who calls it:**
- User-facing API

---

#### 9. **Organization Service**
**Purpose:** Organization & family sharing management

**Synchronous Dependencies:**
- → Account Service (member validation)
- → Device Service (shared devices)
- → Storage Service (shared albums)
- → Authorization Service (permission check)

**Asynchronous Dependencies (Subscribes):**
- `user.created` → auto-create personal org
- `device.registered` → add to family group

**Asynchronous Dependencies (Publishes):**
- `organization.created` → Notification, Audit
- `organization.member_added` → Notification, Authorization
- `organization.member_removed` → Authorization, Device
- `family.resource_shared` → Notification, Storage

**Who calls it:**
- Auth Service (org membership check)
- Device Service (family device list)
- Storage Service (shared album access)

---

#### 10. **Storage Service**
**Purpose:** File/media storage (MinIO/S3)

**Synchronous Dependencies:**
- → Account Service (user validation)
- → Organization Service (sharing permissions)
- → Authorization Service (access check)

**Asynchronous Dependencies (Subscribes):**
- `user.deleted` → cleanup user files
- `organization.member_removed` → revoke shared access

**Asynchronous Dependencies (Publishes):**
- `file.uploaded` → Intelligence Service (AI processing)
- `file.shared` → Notification
- `file.deleted` → Audit

**Who calls it:**
- Device Service (content delivery)
- Album Service (photo storage)
- Session Service (attachment storage)

---

#### 11. **Notification Service**
**Purpose:** Multi-channel notifications (MQTT, Push, Email)

**Synchronous Dependencies:**
- → Account Service (user preferences)
- → Device Service (MQTT topics)

**Asynchronous Dependencies (Subscribes):**
- `payment.completed` → send receipt
- `wallet.balance.low` → send alert
- `organization.member_added` → send invite
- `device.offline` → send alert
- `task.assigned` → send notification

**Asynchronous Dependencies (Publishes):**
- `notification.sent` → Audit
- `notification.failed` → Retry queue

**Who calls it:**
- None (only event-driven)

---

#### 12. **Session Service**
**Purpose:** AI chat session management

**Synchronous Dependencies:**
- → Account Service (user validation)
- → Wallet Service (token check before session)
- → Storage Service (attachment handling)

**Asynchronous Dependencies (Subscribes):**
- `user.logged_out` → cleanup sessions

**Asynchronous Dependencies (Publishes):**
- `session.started` → Telemetry
- `session.ended` → Telemetry, Billing (usage)
- `message.sent` → Memory Service (context)

**Who calls it:**
- User-facing API
- isA_Model, isA_Agent (AI backends)

---

#### 13. **Event Service**
**Purpose:** Event storage and query (calendar-like)

**Synchronous Dependencies:**
- → Account Service (user validation)
- → Organization Service (shared events)

**Asynchronous Dependencies (Subscribes):**
- All events (stores for audit/replay)

**Asynchronous Dependencies (Publishes):**
- `event.stored` → Audit

**Who calls it:**
- Audit Service (event replay)
- Compliance Service (event analysis)

---

#### 14. **Audit Service**
**Purpose:** Compliance & audit logging

**Synchronous Dependencies:**
- None

**Asynchronous Dependencies (Subscribes):**
- ALL events (audit trail)

**Asynchronous Dependencies (Publishes):**
- None (terminal service)

**Who calls it:**
- Compliance Service (audit reports)

---

#### 15. **OTA Service**
**Purpose:** Firmware over-the-air updates

**Synchronous Dependencies:**
- → Device Service (target device list)
- → Storage Service (firmware file storage)

**Asynchronous Dependencies (Subscribes):**
- `device.online` → trigger pending updates

**Asynchronous Dependencies (Publishes):**
- `ota.update_available` → Device, Notification
- `ota.update_completed` → Device, Telemetry
- `ota.update_failed` → Device, Notification

**Who calls it:**
- Admin API (initiate updates)

---

## Event Subject Hierarchy (NATS)

```
events/
├── auth_service/
│   ├── user.logged_in
│   ├── user.logged_out
│   └── device.authenticated
│
├── payment_service/
│   ├── payment.initiated
│   ├── payment.completed
│   ├── payment.failed
│   ├── payment.refunded
│   ├── subscription.created
│   └── subscription.canceled
│
├── wallet_service/
│   ├── wallet.tokens.deducted
│   ├── wallet.tokens.insufficient
│   └── wallet.balance.low
│
├── billing_service/
│   ├── billing.calculated
│   └── billing.error
│
├── organization_service/
│   ├── organization.created
│   ├── organization.member_added
│   ├── organization.member_removed
│   └── family.resource_shared
│
├── device_service/
│   ├── device.registered
│   ├── device.online
│   ├── device.offline
│   └── device.command_sent
│
├── storage_service/
│   ├── file.uploaded
│   ├── file.shared
│   └── file.deleted
│
└── external/
    ├── usage.recorded.model      (from isA_Model)
    ├── usage.recorded.agent      (from isA_Agent)
    └── usage.recorded.mcp        (from isA_MCP)
```

**Subscribe patterns:**
```python
# Subscribe to all payment events
await event_bus.subscribe_to_events("payment_service.*", handler)

# Subscribe to specific event
await event_bus.subscribe_to_events("payment_service.payment.completed", handler)

# Subscribe to all usage events
await event_bus.subscribe_to_events("external.usage.recorded.*", handler)
```

---

## Event-Driven DB Update Best Practices

### 1. **Transactional Outbox Pattern**

```python
async def update_and_publish(self, data):
    async with self.db.transaction():
        # 1. Update database
        record = await self.repository.create(data)

        # 2. Store event in outbox table
        await self.repository.store_outbox_event({
            "event_type": "user.created",
            "payload": record.to_dict(),
            "status": "pending"
        })

        # 3. Commit transaction

    # 4. Publish event (separate process reads outbox)
    await self.publish_pending_events()
```

**Why:** Ensures event is published even if service crashes

### 2. **Idempotent Event Handlers**

```python
async def handle(self, event: Event) -> bool:
    # Check if already processed
    existing = await self.repository.get_by_event_id(event.id)
    if existing:
        logger.info(f"Event {event.id} already processed, skipping")
        return True  # Already handled

    # Process event
    result = await self.process(event)

    # Store event ID to prevent duplicate processing
    await self.repository.store_processed_event(event.id)

    return result
```

**Why:** NATS may deliver events more than once

### 3. **Eventual Consistency with Reconciliation**

```python
# Background job runs every hour
async def reconcile_wallet_balances(self):
    # Compare wallet.balance with sum(transactions)
    for wallet in await self.get_all_wallets():
        calculated_balance = await self.sum_transactions(wallet.id)
        if wallet.balance != calculated_balance:
            logger.error(f"Balance mismatch for {wallet.id}")
            await self.fix_balance(wallet.id, calculated_balance)
```

**Why:** Catch inconsistencies from failed event processing

### 4. **Event Versioning**

```python
class Event:
    def __init__(self, ...):
        self.version = "1.0.0"  # Schema version

async def handle(self, event: Event):
    if event.version == "1.0.0":
        return await self.handle_v1(event)
    elif event.version == "2.0.0":
        return await self.handle_v2(event)
```

**Why:** Allow schema evolution without breaking consumers

---

## Migration Strategy: Add Event-Driven to Existing Services

### Phase 1: Infrastructure (✅ DONE)
- NATS JetStream configured
- Event models defined (core/nats_client.py)
- Base EventHandler class available

### Phase 2: Add Event Publishers (Current)
For services that change state, add event publishing:

```python
# Example: auth_service/auth_service.py

from core.nats_client import get_event_bus, Event, EventType, ServiceSource

class AuthService:
    async def login(self, credentials):
        user = await self.repository.authenticate(credentials)

        # Existing: Update session in DB
        session = await self.repository.create_session(user.id)

        # NEW: Publish event
        event_bus = await get_event_bus("auth_service")
        await event_bus.publish_event(
            Event(
                event_type=EventType.USER_LOGGED_IN,
                source=ServiceSource.AUTH_SERVICE,
                data={
                    "user_id": user.id,
                    "session_id": session.id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        )

        return session
```

### Phase 3: Add Event Subscribers
For services that need to react to events:

```python
# Example: notification_service/events/handlers.py

from core.nats_client import Event

class UserLoggedInHandler:
    def event_type(self) -> str:
        return "user.logged_in"

    async def handle(self, event: Event) -> bool:
        # Send "welcome back" notification
        await self.notification_service.send(
            user_id=event.data["user_id"],
            title="Welcome back!",
            body=f"You logged in at {event.data['timestamp']}"
        )
        return True

# In main.py
event_bus = await get_event_bus("notification_service")
await event_bus.subscribe_to_events(
    "auth_service.user.logged_in",
    UserLoggedInHandler(notification_service).handle
)
```

### Phase 4: Replace Synchronous with Async (Where appropriate)

**Before (Synchronous):**
```python
# order_service calls wallet_service directly
balance = await wallet_client.deduct_balance(user_id, amount)
if balance < 0:
    raise InsufficientFundsError()
```

**After (Event-driven):**
```python
# order_service publishes event
await event_bus.publish_event(
    Event(
        event_type=EventType.ORDER_CREATED,
        source=ServiceSource.ORDER_SERVICE,
        data={"order_id": order_id, "amount": amount, "user_id": user_id}
    )
)

# wallet_service subscribes and processes
class OrderCreatedHandler:
    async def handle(self, event: Event):
        result = await self.wallet_service.deduct(
            event.data["user_id"],
            event.data["amount"]
        )
        if result.success:
            await self.publish_event("wallet.deducted", {...})
        else:
            await self.publish_event("wallet.insufficient", {...})
```

---

## Monitoring & Observability

### Event Metrics to Track

```python
# Prometheus metrics
event_published_total = Counter("event_published_total", ["service", "event_type"])
event_processed_total = Counter("event_processed_total", ["service", "event_type", "status"])
event_processing_duration = Histogram("event_processing_duration_seconds", ["service", "event_type"])
```

### Event Tracing

Use correlation IDs to trace event chains:

```python
event = Event(
    event_type=EventType.USER_CREATED,
    source=ServiceSource.AUTH_SERVICE,
    data={...},
    metadata={
        "correlation_id": str(uuid.uuid4()),  # Track across services
        "trace_id": span.trace_id  # OpenTelemetry integration
    }
)
```

---

## Summary: Decision Tree

```
Need to interact with another service?
│
├─ Is this a READ operation?
│  ├─ YES → Use HTTP Client (synchronous)
│  └─ NO → Continue
│
├─ Do you need immediate response?
│  ├─ YES → Use HTTP Client (synchronous)
│  └─ NO → Continue
│
├─ Is this a state change that others need to know?
│  ├─ YES → Publish Event (asynchronous)
│  └─ NO → Continue
│
├─ Do multiple services need to react?
│  ├─ YES → Publish Event (asynchronous)
│  └─ NO → Continue
│
├─ Can this be eventually consistent?
│  ├─ YES → Publish Event (asynchronous)
│  └─ NO → Use HTTP Client (synchronous)
│
└─ Default: Use HTTP Client (safer choice)
```

---

## Current Implementation Status

| Service | Has Client | Publishes Events | Subscribes to Events |
|---------|-----------|------------------|---------------------|
| account_service | ✅ | ❌ | ❌ |
| auth_service | ✅ | ❌ | ❌ |
| authorization_service | ✅ | ❌ | ❌ |
| device_service | ✅ | ❌ | ❌ |
| payment_service | ✅ | ❌ | ❌ (webhook only) |
| wallet_service | ✅ | ✅ | ✅ (billing.calculated) |
| billing_service | ✅ | ✅ | ✅ (usage.recorded.*) |
| order_service | ✅ | ❌ | ❌ |
| organization_service | ✅ | ❌ | ❌ |
| storage_service | ✅ | ❌ | ❌ |
| notification_service | ✅ | ❌ | ❌ |
| session_service | ✅ | ❌ | ❌ |
| event_service | ✅ | ✅ | ✅ (all events) |

**Next Steps:**
1. Add event publishing to: auth, payment, organization, device
2. Add event subscribers to: notification (all user events), audit (all events)
3. Implement transactional outbox pattern for critical events
4. Add event monitoring and alerting
