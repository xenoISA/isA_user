# Notification Service - System Contract (Layer 6)

## Overview

This document defines HOW notification_service implements the 12 standard system patterns.

**Service**: notification_service
**Port**: 8206
**Category**: User Microservice (Messaging)
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/notification_service/
├── __init__.py
├── main.py                     # FastAPI app, routes, DI setup, lifespan
├── notification_service.py     # Business logic layer
├── notification_repository.py  # Data access layer
├── mqtt_channel.py             # MQTT push channel
├── models.py                   # Pydantic models (Notification, Template, etc.)
├── protocols.py                # DI interfaces (Protocol classes)
├── factory.py                  # DI factory (create_notification_service)
├── routes_registry.py          # Consul route metadata
├── clients/                    # Service client implementations
│   ├── __init__.py
│   ├── notification_client.py
│   ├── account_client.py
│   └── organization_client.py
└── events/
    ├── __init__.py
    ├── models.py
    ├── handlers.py
    └── publishers.py
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| MQTT | Native | Push notification delivery | mqtt broker |
| Resend | HTTP | Email delivery | api.resend.com |
| account_service | HTTP | User data lookup | localhost:8202 |
| organization_service | HTTP | Org member lookup | localhost:8212 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class NotificationServiceError(Exception): ...
class NotificationNotFoundError(NotificationServiceError): ...
class TemplateNotFoundError(NotificationServiceError): ...
class NotificationValidationError(NotificationServiceError): ...

@runtime_checkable
class NotificationRepositoryProtocol(Protocol):
    # Template operations
    async def create_template(self, template: Any) -> Any: ...
    async def get_template(self, template_id: str) -> Optional[Any]: ...
    async def list_templates(self, type=None, status=None, limit=100, offset=0) -> List[Any]: ...
    async def update_template(self, template_id: str, updates: Dict) -> bool: ...
    # Notification operations
    async def create_notification(self, notification: Any) -> Any: ...
    async def update_notification_status(self, notification_id: str, status: Any, ...) -> bool: ...
    # Batch operations
    async def create_batch(self, batch: Any) -> Any: ...
    async def update_batch_stats(self, batch_id: str, ...) -> bool: ...
    # In-app notification operations
    async def create_in_app_notification(self, notification: Any) -> Any: ...
    async def list_user_in_app_notifications(self, user_id: str, ...) -> List[Any]: ...
    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> bool: ...
    async def get_unread_count(self, user_id: str) -> int: ...
    # Push subscription operations
    async def register_push_subscription(self, subscription: Any) -> Any: ...
    async def get_user_push_subscriptions(self, user_id: str, ...) -> List[Any]: ...
    async def unsubscribe_push(self, user_id: str, device_token: str) -> bool: ...
    # Stats
    async def get_notification_stats(self, ...) -> Dict[str, Any]: ...
    async def get_pending_notifications(self, limit: int = 50) -> List[Any]: ...

class EventBusProtocol(Protocol): ...
class AccountClientProtocol(Protocol): ...
class OrganizationClientProtocol(Protocol): ...
class EmailClientProtocol(Protocol): ...
```

### Factory Implementation (`factory.py`)

```python
def create_notification_service(event_bus=None, config_manager=None) -> NotificationService:
    from .notification_repository import NotificationRepository
    from .clients import AccountServiceClient, OrganizationServiceClient
    repository = NotificationRepository(config=config_manager)
    account_client = AccountServiceClient(config_manager)
    organization_client = OrganizationServiceClient(config_manager)
    return NotificationService(
        event_bus=event_bus, config_manager=config_manager,
        repository=repository, account_client=account_client,
        organization_client=organization_client,
    )
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Trigger |
|-------|---------|
| `notification.sent` | Notification delivered |
| `notification.failed` | Notification delivery failed |
| `notification.batch_completed` | Batch processing completed |

### Subscribed Events

Event handlers registered via `get_event_handlers(service)` returning a map of event patterns to handler functions.

---

## 4. Error Handling Pattern

Per-endpoint try/except blocks. No global exception-to-status mapping beyond generic 500 handler.

---

## 5-6. Client & Repository Pattern

Account and organization clients for user/member lookup. Repository handles notifications, templates, batches, in-app notifications, and push subscriptions.

**Background Processing:**

```python
async def process_pending_notifications_task():
    """Background task: processes pending notifications every 30 seconds"""
    while True:
        if service:
            count = await service.process_pending_notifications()
        await asyncio.sleep(30)
```

---

## 7. Service Registration Pattern (Consul)

```python
SERVICE_METADATA = {
    "service_name": "notification_service",
    "version": "1.0.0",
    "tags": ["v1", "notification", "messaging", "user-microservice"],
    "capabilities": [
        "email_notifications", "sms_notifications", "push_notifications",
        "in_app_notifications", "template_management",
        "batch_notifications", "notification_scheduling"
    ]
}
```

25 routes: health (3), templates (6), notification ops (6), in-app (4), push (3), stats (1), test (2).

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/health` | No | Basic health check |
| `/api/v1/notifications/health` | No | API-versioned health check |
| `/info` | No | Service information and capabilities |

---

## 9-12. Event System, Configuration, Logging, Deployment

- NATS event bus for notification lifecycle events
- ConfigManager("notification_service") with port 8206
- `setup_service_logger("notification_service")`
- GracefulShutdown with signal handlers
- Background task for pending notification processing (30s interval)
- Test endpoints available only in DEBUG + development mode

---

## System Contract Checklist

- [x] `protocols.py` defines 5 protocols (Repository, EventBus, Account, Organization, Email clients)
- [x] `factory.py` creates service with account and organization clients
- [x] Multi-channel delivery (email, in-app, push, webhook)
- [x] Template management with variable rendering
- [x] Batch notification support
- [x] Background processing of pending notifications
- [x] Push subscription management (per-platform)
- [x] Consul TTL registration with 25 routes and 7 capabilities

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/notification_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/notification_service/notification_service.py` | Business logic |
| `microservices/notification_service/notification_repository.py` | Data access |
| `microservices/notification_service/protocols.py` | DI interfaces |
| `microservices/notification_service/factory.py` | DI factory |
| `microservices/notification_service/mqtt_channel.py` | MQTT push channel |
| `microservices/notification_service/routes_registry.py` | Consul metadata |
| `microservices/notification_service/events/` | Event handlers, models, publishers |
