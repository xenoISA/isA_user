# Auth Service - System Contract (Layer 6)

## Overview

This document defines HOW auth_service implements the 12 standard system patterns. It bridges the Logic Contract (business rules) to actual code implementation.

**Service**: auth_service
**Port**: 8201
**Category**: User Microservice
**Version**: 2.1.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/auth_service/
├── __init__.py
├── main.py                     # FastAPI app, routes, DI setup, lifespan
├── auth_service.py             # Core authentication business logic
├── auth_repository.py          # Auth data access layer
├── api_key_service.py          # API key management logic
├── api_key_repository.py       # API key data access
├── device_auth_service.py      # Device authentication logic
├── device_auth_repository.py   # Device auth data access
├── oauth_client_repository.py  # OAuth client data access
├── password_utils.py           # Password hashing utilities
├── models.py                   # Pydantic models (AuthUser, AuthSession, etc.)
├── protocols.py                # DI interfaces (Protocol classes)
├── factory.py                  # DI factory (create_auth_service)
├── routes_registry.py          # Consul route metadata
├── client.py                   # HTTP client for inter-service calls
├── clients/                    # Service client implementations
└── events/
    ├── __init__.py
    ├── models.py               # Event Pydantic models
    ├── handlers.py             # NATS event handlers
    └── publishers.py           # Event publishing helpers
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, JWT verification, DI wiring | FastAPI, AuthenticationService |
| **Service** | `auth_service.py` | Authentication logic, token generation | JWTManager, AccountClient, Repository |
| **API Key** | `api_key_service.py` | API key CRUD, verification | ApiKeyRepository |
| **Device Auth** | `device_auth_service.py` | Device registration, authentication | DeviceAuthRepository |
| **Repository** | `auth_repository.py` | Auth data access | AsyncPostgresClient |
| **Events** | `events/handlers.py` | NATS subscription processing | AuthenticationService |
| **Models** | `models.py` | Pydantic schemas, enums | pydantic |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| account_service | HTTP | Account management | localhost:8202 |
| notification_service | HTTP | Email notifications | localhost:8206 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class AuthenticationError(Exception): ...
class InvalidTokenError(AuthenticationError): ...
class UserNotFoundError(AuthenticationError): ...
class SessionNotFoundError(AuthenticationError): ...
class RegistrationError(AuthenticationError): ...
class VerificationError(AuthenticationError): ...
class InvalidCredentialsError(AuthenticationError): ...
class AccountDisabledError(AuthenticationError): ...

@runtime_checkable
class AuthRepositoryProtocol(Protocol):
    async def get_user_by_id(self, user_id: str) -> Optional[AuthUser]: ...
    async def get_user_by_email(self, email: str) -> Optional[AuthUser]: ...
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[AuthUser]: ...
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool: ...
    async def create_session(self, session_data: Dict[str, Any]) -> Optional[AuthSession]: ...
    async def get_session(self, session_id: str) -> Optional[AuthSession]: ...
    async def invalidate_session(self, session_id: str) -> bool: ...
    async def check_connection(self) -> bool: ...
    async def get_user_for_login(self, email: str) -> Optional[Dict[str, Any]]: ...
    async def update_last_login(self, user_id: str) -> bool: ...
    async def set_password_hash(self, user_id: str, password_hash: str) -> bool: ...
    async def set_email_verified(self, user_id: str, verified: bool = True) -> bool: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...

@runtime_checkable
class AccountClientProtocol(Protocol):
    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def ensure_account(self, user_id: str, email: str, name: str) -> Optional[Dict[str, Any]]: ...

@runtime_checkable
class NotificationClientProtocol(Protocol):
    async def send_email(self, recipient_email: str, subject: str, content: str, html_content: Optional[str] = None, **kwargs) -> bool: ...

@runtime_checkable
class JWTManagerProtocol(Protocol):
    def verify_token(self, token: str) -> Dict[str, Any]: ...
    def create_access_token(self, claims: Any, expires_delta: Any = None) -> str: ...
    def create_token_pair(self, claims: Any) -> Dict[str, Any]: ...
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]: ...
```

### Factory Implementation (`factory.py`)

```python
def create_auth_service(config=None, event_bus=None) -> AuthenticationService:
    from core.jwt_manager import get_jwt_manager
    from microservices.account_service.client import AccountServiceClient
    from microservices.notification_service.clients.notification_client import NotificationServiceClient
    from .auth_repository import AuthRepository
    from .oauth_client_repository import OAuthClientRepository

    jwt_manager = get_jwt_manager(secret_key=jwt_secret, algorithm="HS256", issuer="isA_user", ...)
    account_client = AccountServiceClient()
    notification_client = NotificationServiceClient()
    auth_repository = AuthRepository(config)
    oauth_client_repository = OAuthClientRepository(config)

    return AuthenticationService(
        jwt_manager=jwt_manager,
        account_client=account_client,
        notification_client=notification_client,
        event_bus=event_bus,
        auth_repository=auth_repository,
        oauth_client_repository=oauth_client_repository,
        config=config,
    )
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `user.logged_in` | `user.logged_in` | Successful login | UserLoggedInEventData |
| `user.registered` | `user.registered` | User registration completed | UserRegisteredEventData |
| `user.token_refreshed` | `user.token_refreshed` | Token refresh | TokenRefreshedEventData |
| `apikey.created` | `apikey.created` | API key created | ApiKeyCreatedEventData |
| `device.authenticated` | `device.authenticated` | Device authenticated | DeviceAuthenticatedEventData |

---

## 4. Error Handling Pattern

### HTTP Status Code Mapping

| Exception | HTTP Status | Error Type |
|-----------|-------------|------------|
| InvalidTokenError | 401 | UNAUTHORIZED |
| InvalidCredentialsError | 401 | UNAUTHORIZED |
| AccountDisabledError | 403 | FORBIDDEN |
| UserNotFoundError | 404 | NOT_FOUND |
| RegistrationError | 400 | BAD_REQUEST |
| VerificationError | 400 | BAD_REQUEST |
| AuthenticationError | 500 | INTERNAL_ERROR |

---

## 5. Client Pattern (Sync Communication)

### Service Clients

| Client | Target Service | Purpose |
|--------|---------------|---------|
| AccountServiceClient | account_service (8202) | Account ensure/profile lookup |
| NotificationServiceClient | notification_service (8206) | Email sending for verification |

---

## 6. Repository Pattern (Database Access)

### Repositories

| Repository | Purpose | Schema |
|------------|---------|--------|
| `AuthRepository` | User auth records, sessions | auth |
| `ApiKeyRepository` | API key CRUD | auth |
| `DeviceAuthRepository` | Device auth records | auth |
| `OAuthClientRepository` | OAuth client credentials | auth |

---

## 7. Service Registration Pattern (Consul)

### Routes Registry (`routes_registry.py`)

```python
SERVICE_METADATA = {
    "service_name": "auth_service",
    "version": "2.1.0",
    "tags": ["v2", "user-microservice", "authentication"],
    "capabilities": [
        "jwt_verification",
        "api_key_management",
        "token_generation",
        "oauth2_client_credentials",
        "device_authentication",
        "user_registration",
        "user_login"
    ]
}
```

28 routes registered across categories: health, token management, registration, API keys, OAuth clients, device authentication.

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/health` | No | Basic health check |
| `/api/v1/auth/health` | No | API-versioned health check |
| `/api/v1/auth/info` | No | Service information |
| `/api/v1/auth/stats` | No | Service statistics |

---

## 9. Event System Contract (NATS)

Event handlers are registered during lifespan startup. The auth service subscribes to relevant events and publishes authentication-related events.

---

## 10. Configuration Contract

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTH_SERVICE_PORT` | HTTP port | 8201 |
| `JWT_SECRET` | JWT signing secret | (required) |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS server URL | nats://nats:4222 |
| `CONSUL_HOST` | Consul host | consul |
| `CONSUL_PORT` | Consul port | 8500 |

---

## 11. Logging Contract

```python
from core.logger import setup_service_logger
app_logger = setup_service_logger("auth_service")
```

---

## 12. Deployment Contract

### Startup Order

1. Install signal handlers (GracefulShutdown)
2. Initialize NATS event bus
3. Initialize sub-services (AuthenticationService, ApiKeyService, DeviceAuthService)
4. Subscribe to events
5. Register with Consul (TTL health check)

### Shutdown Order

1. Initiate graceful shutdown, wait for drain
2. Deregister from Consul
3. Close event bus

---

## System Contract Checklist

- [x] `protocols.py` defines all dependency interfaces (AuthRepository, EventBus, AccountClient, NotificationClient, JWTManager)
- [x] `factory.py` creates service with DI
- [x] Event models defined in `events/models.py`
- [x] Custom exceptions hierarchy (AuthenticationError base)
- [x] Multiple repositories (auth, api_key, device_auth, oauth_client)
- [x] `routes_registry.py` defines 28 routes with SERVICE_METADATA
- [x] Consul TTL health check
- [x] GracefulShutdown with signal handlers

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/auth_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/auth_service/auth_service.py` | Core authentication logic |
| `microservices/auth_service/api_key_service.py` | API key management |
| `microservices/auth_service/device_auth_service.py` | Device authentication |
| `microservices/auth_service/protocols.py` | DI interfaces |
| `microservices/auth_service/factory.py` | DI factory |
| `microservices/auth_service/routes_registry.py` | Consul metadata |
| `microservices/auth_service/events/` | Event handlers, models, publishers |
