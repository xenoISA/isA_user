# Authentication Service - Component Design Document

## Architecture Overview

### Service Architecture (ASCII Diagram)
```
┌──────────────────────────────────────────────────────────────────────────┐
│                     Authentication Service                                │
├──────────────────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                                           │
│  ├─ Token Verification Routes        (/api/v1/auth/verify-token)        │
│  ├─ Registration Routes               (/api/v1/auth/register, /verify)   │
│  ├─ Token Generation Routes           (/api/v1/auth/dev-token,           │
│  │                                      /token-pair, /refresh)            │
│  ├─ API Key Routes                    (/api/v1/auth/api-keys/*)          │
│  └─ Device Authentication Routes      (/api/v1/auth/device/*)            │
├──────────────────────────────────────────────────────────────────────────┤
│  Service Layer (Dependency Injection via Protocols)                      │
│  ├─ AuthenticationService             (JWT verification, registration)   │
│  │   └─ Dependencies: JWTManager, AccountClient, NotificationClient      │
│  ├─ ApiKeyService                     (API key management)               │
│  │   └─ Dependencies: ApiKeyRepository                                   │
│  └─ DeviceAuthService                 (Device auth & pairing)            │
│      └─ Dependencies: DeviceAuthRepository, EventBus                     │
├──────────────────────────────────────────────────────────────────────────┤
│  Repository Layer (Data Access)                                          │
│  ├─ AuthRepository                    (auth.users, auth.user_sessions)   │
│  ├─ ApiKeyRepository                  (organizations.api_keys JSONB)     │
│  └─ DeviceAuthRepository              (auth.device_credentials,          │
│                                         auth.device_pairing_tokens)       │
├──────────────────────────────────────────────────────────────────────────┤
│  Factory Layer (factory.py)                                              │
│  └─ create_auth_service()             (wires real dependencies)          │
├──────────────────────────────────────────────────────────────────────────┤
│  Protocol Layer (protocols.py)                                           │
│  ├─ JWTManagerProtocol                (token operations interface)       │
│  ├─ AccountClientProtocol             (account service interface)        │
│  ├─ NotificationClientProtocol        (notification interface)           │
│  ├─ EventBusProtocol                  (event publishing interface)       │
│  └─ AuthRepositoryProtocol            (data access interface)            │
└──────────────────────────────────────────────────────────────────────────┘

External Dependencies:
┌────────────────────────────────────────────────────────────────────┐
│ Core Services                                                      │
│ ├─ core.jwt_manager        → JWT token operations (HS256)         │
│ ├─ core.nats_client        → Event publishing (NATS)              │
│ ├─ core.config_manager     → Configuration management             │
│ └─ isa_common              → AsyncPostgresClient, ConsulRegistry  │
│                                                                    │
│ Microservices (HTTP Clients)                                      │
│ ├─ account_service         → Account creation on registration     │
│ ├─ notification_service    → Email verification codes             │
│ └─ organization_service    → API key JSONB storage                │
│                                                                    │
│ Infrastructure                                                     │
│ ├─ PostgreSQL (gRPC)       → Data persistence                     │
│ ├─ NATS                    → Event bus                            │
│ └─ Consul                  → Service registration & discovery     │
└────────────────────────────────────────────────────────────────────┘
```

### Component Design

#### AuthenticationService
**Responsibilities:**
- JWT token verification (Auth0 + isa_user providers)
- User registration flow with email verification
- Token generation (dev-token, token-pair, refresh)
- User info extraction from tokens
- Identity authentication (not authorization)

**Key Features:**
- Dependency injection for testability
- Auto-detection of token provider (Auth0 vs isa_user)
- In-memory pending registration store (10-minute TTL)
- Integration with Account Service for user creation
- Event publishing for user.logged_in events

**Dependencies:**
- `JWTManagerProtocol`: Token creation and verification
- `AccountClientProtocol`: Account creation and validation
- `NotificationClientProtocol`: Email verification codes
- `EventBusProtocol`: Event publishing (optional)

#### ApiKeyService
**Responsibilities:**
- API key creation with permissions
- API key verification and validation
- API key revocation and deletion
- Organization-scoped key management
- Last-used timestamp tracking

**Key Features:**
- Stores keys in organizations.api_keys JSONB field
- SHA-256 hashing before storage
- Permission-based access control
- Expiration date enforcement
- Audit trail (created_at, last_used)

**Dependencies:**
- `ApiKeyRepository`: Data access layer

#### DeviceAuthService
**Responsibilities:**
- Device registration with secret generation
- Device authentication with JWT tokens
- Device pairing with temporary tokens (5-minute TTL)
- Device credential management
- Device revocation and secret refresh

**Key Features:**
- SHA-256 hashed secrets (never stored in plaintext)
- Device JWT tokens (24-hour expiry)
- Pairing token flow for QR code scanning
- Organization-scoped device management
- Event publishing (device.registered, device.authenticated)

**Dependencies:**
- `DeviceAuthRepository`: Data access layer
- `EventBusProtocol`: Event publishing (optional)

### Database Schemas

#### auth.users table
```sql
CREATE TABLE IF NOT EXISTS auth.users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    subscription_status VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_auth_users_email ON auth.users(email);
CREATE INDEX idx_auth_users_active ON auth.users(is_active);
```

**Purpose:** Minimal user identity for authentication. Full profile managed by account_service.

**Fields:**
- `user_id`: Primary key (format: usr_*)
- `email`: Unique email address (normalized to lowercase)
- `name`: Display name
- `subscription_status`: Subscription tier (free, basic, pro, enterprise)
- `is_active`: Account status flag
- `created_at`, `updated_at`: Audit timestamps

#### auth.user_sessions table
```sql
CREATE TABLE IF NOT EXISTS auth.user_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES auth.users(user_id),
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invalidated_at TIMESTAMP
);

CREATE INDEX idx_auth_sessions_user ON auth.user_sessions(user_id);
CREATE INDEX idx_auth_sessions_active ON auth.user_sessions(is_active);
CREATE INDEX idx_auth_sessions_expires ON auth.user_sessions(expires_at);
```

**Purpose:** Track user authentication sessions for token management.

**Fields:**
- `session_id`: Primary key
- `user_id`: Foreign key to auth.users
- `access_token`: JWT access token (optional storage)
- `refresh_token`: JWT refresh token (optional storage)
- `expires_at`: Session expiration timestamp
- `is_active`: Session validity flag
- `last_activity`: Last request timestamp
- `invalidated_at`: Manual invalidation timestamp

#### auth.device_credentials table
```sql
CREATE TABLE IF NOT EXISTS auth.device_credentials (
    device_id VARCHAR(100) PRIMARY KEY,
    device_secret VARCHAR(255) NOT NULL,  -- SHA-256 hash
    organization_id VARCHAR(50) NOT NULL,
    device_name VARCHAR(255),
    device_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_auth TIMESTAMP
);

CREATE INDEX idx_device_creds_org ON auth.device_credentials(organization_id);
CREATE INDEX idx_device_creds_status ON auth.device_credentials(status);
CREATE INDEX idx_device_creds_type ON auth.device_credentials(device_type);
```

**Purpose:** Store device authentication credentials for IoT/device access.

**Fields:**
- `device_id`: Primary key (client-provided unique identifier)
- `device_secret`: SHA-256 hash of device secret (never plaintext)
- `organization_id`: Organization ownership
- `device_name`: Human-readable device name
- `device_type`: Device category (e.g., "emoframe", "sensor")
- `status`: active | revoked | expired
- `metadata`: Custom JSONB data (firmware version, hardware info)
- `expires_at`: Optional credential expiration
- `last_auth`: Last successful authentication timestamp

#### auth.device_pairing_tokens table
```sql
CREATE TABLE IF NOT EXISTS auth.device_pairing_tokens (
    pairing_token VARCHAR(255) PRIMARY KEY,
    device_id VARCHAR(100) REFERENCES auth.device_credentials(device_id),
    user_id VARCHAR(50),
    used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP
);

CREATE INDEX idx_pairing_device ON auth.device_pairing_tokens(device_id);
CREATE INDEX idx_pairing_expires ON auth.device_pairing_tokens(expires_at);
CREATE INDEX idx_pairing_used ON auth.device_pairing_tokens(used);
```

**Purpose:** Temporary tokens for device-user pairing (QR code flow).

**Fields:**
- `pairing_token`: URL-safe random token (32 bytes)
- `device_id`: Device being paired
- `user_id`: User who completed pairing (set after verification)
- `used`: One-time use flag
- `expires_at`: 5-minute expiration from creation
- `used_at`: Timestamp when token was verified

#### organizations.api_keys (JSONB field)
Stored as JSONB array in organizations table:
```json
{
  "api_keys": [
    {
      "key_id": "key_abc123",
      "key_hash": "sha256_hash_of_api_key",
      "name": "Production API",
      "permissions": ["read:users", "write:data", "admin:billing"],
      "created_at": "2024-01-01T00:00:00Z",
      "created_by": "usr_admin123",
      "expires_at": "2025-01-01T00:00:00Z",
      "last_used": "2024-06-01T12:00:00Z",
      "is_active": true
    }
  ]
}
```

**Purpose:** Organization-scoped API keys for programmatic access.

**Fields:**
- `key_id`: Unique identifier (key_*)
- `key_hash`: SHA-256 hash of API key (never plaintext)
- `name`: Human-readable key name
- `permissions`: Array of permission strings
- `created_at`, `created_by`: Audit fields
- `expires_at`: Optional expiration (null = no expiration)
- `last_used`: Updated on each verification
- `is_active`: Revocation flag

## Data Flow Diagrams

### Registration Flow
```
┌──────┐                                                    ┌──────────────┐
│ User │                                                    │ Auth Service │
└───┬──┘                                                    └──────┬───────┘
    │                                                              │
    │ 1. POST /register                                           │
    │    {email, password, name}                                  │
    ├────────────────────────────────────────────────────────────►│
    │                                                              │
    │                    2. Generate verification code (6 digits) │
    │                       Store in memory (10min TTL)           │
    │                       pending_id = uuid()                   │
    │                       code = random(000000-999999)          │
    │                                                              │
    │                    3. Call NotificationClient               │
    │                       send_email(email, code)               │
    │                                                              │
    │ 4. Return pending_registration_id                           │
    │◄────────────────────────────────────────────────────────────┤
    │                                                              │
    │ 5. User receives email with code                            │
    │                                                              │
    │ 6. POST /verify                                             │
    │    {pending_registration_id, code}                          │
    ├────────────────────────────────────────────────────────────►│
    │                                                              │
    │                    7. Validate code + expiry                │
    │                       Generate user_id (usr_*)              │
    │                                                              │
    │                    8. Call AccountClient                    │
    │                       ensure_account(user_id, email, name)  │
    │                                                              │
    │                    9. Generate token pair                   │
    │                       access_token (1hr)                    │
    │                       refresh_token (7d)                    │
    │                                                              │
    │                   10. Publish user.registered event         │
    │                       EventBus.publish(user_id, email)      │
    │                                                              │
    │ 11. Return {user_id, tokens}                                │
    │◄────────────────────────────────────────────────────────────┤
    │                                                              │
    │ 12. Cleanup pending registration                            │
    │                                                              │
    └──────────────────────────────────────────────────────────────┘
```

**Security Notes:**
- Verification codes expire in 10 minutes
- Codes are 6 digits (1M combinations, sufficient for short TTL)
- Email normalization (lowercase, trimmed)
- Password validation (min 8 characters)
- One-time use: pending registration deleted after verification

### Token Verification Flow
```
┌────────┐                                              ┌──────────────┐
│ Client │                                              │ Auth Service │
└───┬────┘                                              └──────┬───────┘
    │                                                          │
    │ 1. POST /verify-token                                   │
    │    {token, provider?}                                   │
    ├─────────────────────────────────────────────────────────►│
    │                                                          │
    │                          2. Detect provider              │
    │                             if not specified:            │
    │                             decode header → check issuer │
    │                             "isA_user" = isa_user        │
    │                             "auth0.com" = auth0          │
    │                                                          │
    │                          3a. If Auth0:                   │
    │                              Fetch JWKS from Auth0       │
    │                              Get public key by kid       │
    │                              Validate with RS256         │
    │                              Check audience + issuer     │
    │                                                          │
    │                          3b. If isa_user:                │
    │                              JWTManager.verify_token()   │
    │                              Validate signature (HS256)  │
    │                              Check expiration            │
    │                              Extract claims              │
    │                                                          │
    │ 4. Return verification result                            │
    │    {valid, user_id, email,                               │
    │     organization_id, permissions,                        │
    │     expires_at}                                          │
    │◄─────────────────────────────────────────────────────────┤
    │                                                          │
    └──────────────────────────────────────────────────────────┘
```

**Provider Detection:**
- Checks JWT `iss` (issuer) claim without verification
- `iss: "isA_user"` → isa_user provider (HS256)
- `iss: "https://*.auth0.com/"` → auth0 provider (RS256)
- Default: isa_user if detection fails

**Token Claims (isa_user):**
```json
{
  "iss": "isA_user",
  "sub": "usr_abc123",
  "email": "user@example.com",
  "organization_id": "org_xyz789",
  "scope": "user",
  "permissions": ["read:profile", "write:data"],
  "metadata": {"subscription_level": "pro"},
  "jti": "unique-token-id",
  "iat": 1704067200,
  "exp": 1704070800
}
```

### Device Pairing Flow
```
┌─────────┐          ┌──────────────┐          ┌──────────────┐
│ Device  │          │ Auth Service │          │ Mobile App   │
│(Display)│          │              │          │  (User)      │
└────┬────┘          └──────┬───────┘          └──────┬───────┘
     │                      │                         │
     │ 1. POST /device/{id}/pairing-token             │
     ├─────────────────────►│                         │
     │                      │                         │
     │                      │ 2. Generate random token│
     │                      │    (32-byte URL-safe)   │
     │                      │    expires_at = now+5min│
     │                      │                         │
     │                      │ 3. Store in DB          │
     │                      │    device_pairing_tokens│
     │                      │                         │
     │                      │ 4. Publish event        │
     │                      │    pairing_token.generated
     │                      │                         │
     │ 5. Return {pairing_token, expires_at}          │
     │◄─────────────────────┤                         │
     │                      │                         │
     │ 6. Display QR code   │                         │
     │    with token        │                         │
     │                      │                         │
     │                      │         7. User scans QR│
     │                      │◄────────────────────────┤
     │                      │                         │
     │                      │ 8. Validate token       │
     │                      │    - Check expiry       │
     │                      │    - Check not used     │
     │                      │    - Match device_id    │
     │                      │                         │
     │                      │ 9. Mark token used      │
     │                      │    UPDATE used=true     │
     │                      │    SET user_id          │
     │                      │                         │
     │                      │10. Publish event        │
     │                      │   device.paired         │
     │                      │                         │
     │                      │11. Return success       │
     │                      ├────────────────────────►│
     │                      │                         │
     │12. Device Service    │                         │
     │    links user to     │                         │
     │    device            │                         │
     │                      │                         │
     └──────────────────────┴─────────────────────────┘
```

**Pairing Security:**
- Tokens expire in 5 minutes (prevents stale QR codes)
- One-time use only (prevents replay attacks)
- Device ownership verified before token generation
- User authentication required to scan QR (mobile app)

### API Key Verification Flow
```
┌────────┐                                            ┌──────────────┐
│ Client │                                            │ Auth Service │
└───┬────┘                                            └──────┬───────┘
    │                                                        │
    │ 1. POST /verify-api-key                               │
    │    {api_key: "sk_live_abc123..."}                     │
    ├───────────────────────────────────────────────────────►│
    │                                                        │
    │                        2. Hash provided key (SHA-256)  │
    │                           key_hash = sha256(api_key)   │
    │                                                        │
    │                        3. ApiKeyRepository             │
    │                           validate_api_key(api_key)    │
    │                                                        │
    │                        4. Load org JSONB               │
    │                           SELECT api_keys FROM         │
    │                           organizations WHERE ...      │
    │                                                        │
    │                        5. Find matching key_hash       │
    │                           Filter by is_active=true     │
    │                           Check expiration             │
    │                                                        │
    │                        6. Update last_used             │
    │                           UPDATE organizations SET     │
    │                           api_keys[i].last_used=now    │
    │                                                        │
    │ 7. Return verification result                          │
    │    {valid, organization_id,                            │
    │     permissions, name, key_id}                         │
    │◄───────────────────────────────────────────────────────┤
    │                                                        │
    └────────────────────────────────────────────────────────┘
```

**API Key Format:**
- Prefix: `sk_live_` (production) or `sk_test_` (development)
- Length: 32-48 characters (URL-safe base64)
- Generation: `secrets.token_urlsafe(32)`
- Storage: SHA-256 hash only (never plaintext)

**Verification Performance:**
- JSONB query optimized with GIN indexes
- Last-used update is async (non-blocking)
- Cache consideration: Add Redis for high-traffic scenarios

## Technology Stack

### Core Technologies
- **FastAPI**: HTTP REST API framework (async ASGI)
- **Pydantic**: Request/response validation and serialization
- **PyJWT**: JWT token operations (HS256, RS256)
- **PostgreSQL**: Data persistence via gRPC client
- **NATS**: Event publishing and subscription
- **Consul**: Service registration and discovery

### Dependencies

#### Core Libraries
- `core.jwt_manager`: JWT operations (TokenClaims, TokenScope, TokenType)
- `core.nats_client`: Event publishing (Event, EventType, ServiceSource)
- `core.config_manager`: Configuration management with Consul integration
- `core.logger`: Structured logging with service context
- `isa_common`: AsyncPostgresClient, ConsulRegistry utilities

#### Service Clients
- `account_service.client.AccountServiceClient`: Account creation on registration
- `notification_service.clients.NotificationServiceClient`: Email verification codes
- `organization_service.client.OrganizationServiceClient`: API key storage access

#### External Libraries
- `httpx`: Async HTTP client for Auth0 JWKS fetching
- `secrets`: Cryptographically secure random number generation
- `hashlib`: SHA-256 hashing for secrets and API keys
- `python-jose`: Alternative JWT library (not currently used)

### Configuration

#### Environment Variables
```bash
# JWT Configuration
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600
JWT_REFRESH_EXPIRATION=604800

# Auth0 Configuration (Optional)
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=https://api.example.com
AUTH0_ALGORITHMS=RS256

# Service Configuration
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8002
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061
POSTGRES_GRPC_URL=isa-postgres-grpc:50061

# Event Bus Configuration
NATS_URL=nats://isa-nats:4222
NATS_ENABLED=true

# Service Discovery
CONSUL_HOST=isa-consul
CONSUL_PORT=8500
CONSUL_ENABLED=true

# Downstream Services
ACCOUNT_SERVICE_URL=http://isa-account:8001
NOTIFICATION_SERVICE_URL=http://isa-notification:8010
ORGANIZATION_SERVICE_URL=http://isa-organization:8004
```

#### Service Metadata (routes_registry.py)
```python
SERVICE_METADATA = {
    'service_name': 'auth_service',
    'version': '2.0.0',
    'tags': ['authentication', 'jwt', 'api-keys', 'device-auth'],
    'capabilities': [
        'jwt_verification',
        'api_key_management',
        'token_generation',
        'device_authentication',
        'user_registration'
    ]
}
```

## Security Considerations

### Token Security

#### JWT Token Best Practices
- **Algorithm**: HS256 for isa_user tokens (shared secret)
- **Expiration**: Access tokens 1 hour, refresh tokens 7 days
- **Claims**: Minimal PII (user_id, email only)
- **Signature**: HMAC-SHA256 with 256-bit secret
- **JTI**: Unique token ID for tracking/revocation

#### Token Rotation
- Refresh tokens are single-use (generate new pair on refresh)
- Access tokens cannot be refreshed after expiration
- Session invalidation clears both access and refresh tokens

#### Auth0 Integration
- RS256 algorithm with public key verification
- JWKS caching (15-minute TTL) for performance
- Issuer validation (`https://{domain}/`)
- Audience validation against configured value

### Device Security

#### Device Secret Management
- **Generation**: 32-byte URL-safe random (256 bits entropy)
- **Storage**: SHA-256 hash only (never plaintext)
- **Transmission**: HTTPS only, one-time display on registration
- **Rotation**: Manual refresh generates new secret
- **Revocation**: Instant via status=revoked flag

#### Device Token Security
- Device JWT tokens scoped to organization
- 24-hour expiration (shorter than user tokens)
- Device type metadata included for audit
- IP address logging on authentication

#### Pairing Token Security
- 5-minute expiration (very short for QR code usage)
- One-time use only (prevents replay attacks)
- URL-safe random generation (secrets.token_urlsafe)
- Device ownership verified before generation
- User authentication required to complete pairing

### API Key Security

#### API Key Generation
- **Format**: `sk_live_` prefix + 32-byte random
- **Storage**: SHA-256 hash in JSONB field
- **Transmission**: Returned once on creation, never again
- **Rotation**: Manual deletion + recreation required

#### API Key Validation
- Hash comparison (constant-time to prevent timing attacks)
- Expiration date enforcement
- Active flag check (soft deletion)
- Organization scoping (no cross-org access)
- Permission list validation on each request

#### Audit Trail
- `created_at`, `created_by`: Creation audit
- `last_used`: Updated on each verification
- Organization-scoped listing for key management
- Soft deletion preserves audit history

### Registration Security

#### Email Verification
- 6-digit codes (1M combinations, sufficient for 10min TTL)
- In-memory storage (not persisted to database)
- Expiration after 10 minutes
- One-time use (deleted after verification)
- Email normalization (lowercase, trimmed)

#### Password Security
- **Minimum Length**: 8 characters (validated by Pydantic)
- **Storage**: NOT stored in auth_service (placeholder only)
- **Future**: Delegate to dedicated credential service
- **Recommendation**: bcrypt/argon2 hashing with salt

#### Registration Limits
- **Future Enhancement**: Rate limiting per email/IP
- **Future Enhancement**: CAPTCHA for bot prevention
- **Future Enhancement**: Email domain validation

### Transport Security
- **HTTPS Only**: All production endpoints (enforced by Gateway)
- **CORS**: Handled by API Gateway (not at service level)
- **Headers**: No sensitive data in query params or headers
- **Logging**: Tokens redacted in logs (first 8 chars only)

## Event-Driven Architecture

### Published Events

#### 1. user.registered (EventType.USER_REGISTERED)
**Trigger**: After successful email verification and account creation

**Data:**
```json
{
  "event_type": "user.registered",
  "source": "auth_service",
  "data": {
    "user_id": "usr_abc123",
    "email": "user@example.com",
    "registration_method": "email_code",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "metadata": {
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

**Consumers:**
- account_service: Initialize user profile
- notification_service: Send welcome email
- audit_service: Log registration event
- analytics_service: Track new user metric

#### 2. user.logged_in (EventType.USER_LOGGED_IN)
**Trigger**: After token pair generation (login or registration)

**Data:**
```json
{
  "event_type": "user.logged_in",
  "source": "auth_service",
  "data": {
    "user_id": "usr_abc123",
    "email": "user@example.com",
    "organization_id": "org_xyz789",
    "provider": "isa_user",
    "timestamp": "2024-01-01T12:05:00Z"
  },
  "metadata": {
    "permissions": "read:profile,write:data",
    "has_organization": "true"
  }
}
```

**Consumers:**
- session_service: Create user session
- audit_service: Log login event
- analytics_service: Track active users

#### 3. device.registered (EventType.DEVICE_REGISTERED)
**Trigger**: After device credential creation

**Data:**
```json
{
  "event_type": "device.registered",
  "source": "auth_service",
  "data": {
    "device_id": "dev_sensor123",
    "organization_id": "org_xyz789",
    "device_name": "Living Room Sensor",
    "device_type": "emoframe",
    "status": "active",
    "timestamp": "2024-01-01T12:10:00Z"
  }
}
```

**Consumers:**
- device_service: Initialize device profile
- notification_service: Alert organization admin
- audit_service: Log device registration

#### 4. device.authenticated (EventType.DEVICE_AUTHENTICATED)
**Trigger**: After successful device login

**Data:**
```json
{
  "event_type": "device.authenticated",
  "source": "auth_service",
  "data": {
    "device_id": "dev_sensor123",
    "organization_id": "org_xyz789",
    "device_name": "Living Room Sensor",
    "device_type": "emoframe",
    "timestamp": "2024-01-01T12:15:00Z",
    "ip_address": "192.168.1.100"
  },
  "metadata": {
    "user_agent": "EmoFrame/1.0"
  }
}
```

**Consumers:**
- device_service: Update last_seen timestamp
- audit_service: Log device authentication
- security_service: Check for anomalous access patterns

#### 5. device.pairing_token.generated (Custom Event)
**Trigger**: After pairing token creation for QR code flow

**Data:**
```json
{
  "event_type": "device.pairing_token.generated",
  "source": "auth_service",
  "data": {
    "device_id": "dev_display456",
    "pairing_token": "abc123xyz...",
    "expires_at": "2024-01-01T12:20:00Z",
    "timestamp": "2024-01-01T12:15:00Z"
  }
}
```

**Consumers:**
- device_service: Track pairing requests
- notification_service: Alert device owner

#### 6. device.paired (Custom Event)
**Trigger**: After pairing token verification (user scans QR)

**Data:**
```json
{
  "event_type": "device.paired",
  "source": "auth_service",
  "data": {
    "device_id": "dev_display456",
    "user_id": "usr_abc123",
    "pairing_token": "abc123xyz...",
    "timestamp": "2024-01-01T12:16:00Z"
  }
}
```

**Consumers:**
- device_service: Link device to user account
- notification_service: Confirm pairing to user
- audit_service: Log pairing event

### Consumed Events
**None** - Auth service is a leaf service (publishes only, no subscriptions)

### Event Schema Versioning
- Current version: v1 (implicit)
- Future: Add `schema_version` field for backwards compatibility
- Event evolution: Add new fields (never remove/rename)

## Error Handling

### Exception Hierarchy
```
AuthenticationError (base)
├─ InvalidTokenError
│  ├─ TokenExpiredError
│  └─ TokenSignatureError
├─ RegistrationError
│  ├─ DuplicateEmailError
│  └─ InvalidPasswordError
├─ VerificationError
│  ├─ CodeExpiredError
│  └─ CodeMismatchError
├─ UserNotFoundError
└─ SessionNotFoundError
```

### HTTP Status Codes

#### Success Codes
- **200 OK**: Successful operation (verification, token generation)
- **201 Created**: Resource created (registration, API key)

#### Client Error Codes
- **400 Bad Request**: Validation errors, malformed requests
- **401 Unauthorized**: Invalid credentials, expired tokens
- **403 Forbidden**: Debug endpoint accessed in production
- **404 Not Found**: User, session, or device not found
- **409 Conflict**: Duplicate email during registration
- **422 Unprocessable Entity**: Pydantic validation errors

#### Server Error Codes
- **500 Internal Server Error**: Unexpected failures
- **503 Service Unavailable**: Database or downstream service failure

### Error Response Format
```json
{
  "detail": "Token has expired",
  "error_code": "TOKEN_EXPIRED",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_abc123"
}
```

### Error Handling Strategies

#### Token Verification Errors
```python
try:
    result = await auth_service.verify_token(token)
    if not result.get("valid"):
        return TokenVerificationResponse(
            valid=False,
            error=result.get("error")
        )
except Exception as e:
    logger.error(f"Token verification failed: {e}")
    return TokenVerificationResponse(
        valid=False,
        error="Verification failed"
    )
```

#### Registration Errors
```python
try:
    result = await auth_service.start_registration(email, password, name)
    return RegistrationStartResponse(**result)
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    logger.error(f"Registration failed: {e}")
    raise HTTPException(
        status_code=500,
        detail="Registration failed"
    )
```

#### Graceful Degradation
- Event publishing failures: Log error, continue operation
- Account service failures: Proceed with minimal account data
- Notification failures: Complete registration, retry email async

### Logging Best Practices
- **Structured Logging**: JSON format with context
- **Log Levels**: DEBUG (dev), INFO (prod), ERROR (always)
- **Sensitive Data**: Redact tokens (show first 8 chars only)
- **Correlation IDs**: Include request_id for tracing

## Performance Considerations

### Token Verification Performance

#### Benchmarks
- **Target**: < 100ms per verification (p99)
- **isa_user tokens**: 10-20ms (CPU-bound signature check)
- **Auth0 tokens**: 50-100ms (includes JWKS fetch + RSA verification)

#### Optimization Strategies
1. **JWKS Caching**: Cache Auth0 public keys for 15 minutes
2. **Signature Verification**: PyJWT optimized C bindings
3. **Connection Pooling**: Reuse httpx client for JWKS
4. **No I/O**: isa_user verification is pure computation

#### Bottlenecks
- Auth0 JWKS fetch: 30-50ms network latency
- RSA verification: 2-5x slower than HMAC (acceptable)
- Database lookups: Not required for stateless JWT verification

### Registration Flow Performance

#### Benchmarks
- **Target**: < 2 seconds for start_registration
- **Target**: < 1 second for verify_registration

#### Optimization Strategies
1. **Async Email Sending**: Non-blocking notification call
2. **In-Memory Storage**: Pending registrations in dict (no DB)
3. **Account Creation**: HTTP client with connection pooling
4. **Event Publishing**: Fire-and-forget async

#### Bottlenecks
- Notification service: 200-500ms for email delivery
- Account service: 100-300ms for account creation
- Event publishing: 10-50ms (async, non-blocking)

### API Key Verification Performance

#### Benchmarks
- **Target**: < 50ms per verification (p99)
- **Current**: 20-40ms (JSONB query + hash comparison)

#### Optimization Strategies
1. **JSONB Indexing**: GIN index on api_keys field
2. **Hash Comparison**: Constant-time comparison (security)
3. **Last-Used Update**: Async update (non-blocking)
4. **Caching**: Redis cache for hot keys (future)

#### Bottlenecks
- JSONB query: 10-20ms (PostgreSQL JSONB is fast)
- Organization lookup: 5-10ms (indexed on organization_id)
- Hash computation: 1-2ms (SHA-256 is fast)

### Device Authentication Performance

#### Benchmarks
- **Target**: < 200ms for device authentication
- **Current**: 100-150ms (credential lookup + JWT generation)

#### Optimization Strategies
1. **Database Indexing**: Index on device_id, organization_id, status
2. **JWT Generation**: PyJWT optimized (HS256 is fast)
3. **Event Publishing**: Async, non-blocking
4. **Connection Pooling**: Reuse gRPC connections

#### Bottlenecks
- Device credential lookup: 50-80ms (gRPC + database)
- SHA-256 hashing: 5-10ms (verification)
- JWT encoding: 10-20ms (HMAC signature)

### Scalability

#### Horizontal Scaling
- **Stateless**: No local state (except pending registrations)
- **Load Balancing**: Round-robin across instances
- **Session Affinity**: Not required (stateless)
- **Database Connections**: Pool per instance (async gRPC)

#### Bottleneck: In-Memory Pending Registrations
- **Current**: Dict in each instance (not shared)
- **Problem**: User must verify on same instance
- **Solution 1**: Redis for shared pending registrations
- **Solution 2**: Sticky sessions during registration flow
- **Recommendation**: Redis for production (10min TTL)

#### Database Connection Pooling
- **gRPC Client**: Connection pooling via isa_common
- **Pool Size**: 10 connections per instance (configurable)
- **Timeout**: 10 seconds for queries
- **Retry**: Automatic retry on connection failure

## Deployment Configuration

### Container Configuration

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

CMD ["uvicorn", "microservices.auth_service.main:app", \
     "--host", "0.0.0.0", "--port", "8002"]
```

#### Docker Compose
```yaml
auth_service:
  image: isa-auth-service:latest
  container_name: isa-auth
  environment:
    - JWT_SECRET=${JWT_SECRET}
    - POSTGRES_HOST=isa-postgres-grpc
    - NATS_URL=nats://isa-nats:4222
    - CONSUL_HOST=isa-consul
    - ACCOUNT_SERVICE_URL=http://isa-account:8001
  ports:
    - "8002:8002"
  depends_on:
    - isa-postgres-grpc
    - isa-nats
    - isa-consul
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Kubernetes Configuration

#### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
  labels:
    app: auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
      - name: auth-service
        image: isa-auth-service:2.0.0
        ports:
        - containerPort: 8002
        env:
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: auth-secrets
              key: jwt-secret
        - name: POSTGRES_HOST
          value: isa-postgres-grpc
        - name: NATS_URL
          value: nats://isa-nats:4222
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 5
          periodSeconds: 10
```

#### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: auth-service
spec:
  selector:
    app: auth-service
  ports:
  - protocol: TCP
    port: 8002
    targetPort: 8002
  type: ClusterIP
```

### Health Checks

#### Root Health Check
```
GET /
Response: 200 OK
{
  "service": "auth_microservice",
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Service Health Check
```
GET /health
Response: 200 OK
{
  "status": "healthy",
  "service": "auth_microservice",
  "port": 8002,
  "version": "2.0.0",
  "capabilities": [
    "jwt_verification",
    "api_key_management",
    "token_generation",
    "device_authentication"
  ],
  "providers": ["auth0", "isa_user"]
}
```

#### Dependency Health Check (Future)
```
GET /health/dependencies
Response: 200 OK
{
  "database": "healthy",
  "nats": "healthy",
  "jwt_manager": "healthy",
  "account_service": "healthy",
  "notification_service": "degraded"
}
```

### Service Registration (Consul)

#### Registration Metadata
```json
{
  "ID": "auth-service-1",
  "Name": "auth_service",
  "Tags": ["authentication", "jwt", "api-keys", "device-auth"],
  "Address": "isa-auth",
  "Port": 8002,
  "Meta": {
    "version": "2.0.0",
    "capabilities": "jwt_verification,api_key_management,token_generation,device_authentication",
    "all_routes": "/api/v1/auth/verify-token|/api/v1/auth/register|..."
  },
  "Check": {
    "HTTP": "http://isa-auth:8002/health",
    "Interval": "10s",
    "Timeout": "5s"
  }
}
```

#### Deregistration
- Automatic on graceful shutdown
- Manual cleanup on crash (Consul TTL)
- Health check failures trigger deregistration after 3 retries

### Scaling Strategy

#### Vertical Scaling
- **CPU**: 100m-500m (JWT verification is CPU-bound)
- **Memory**: 128Mi-512Mi (in-memory pending registrations)
- **Storage**: Not required (stateless)

#### Horizontal Scaling
- **Initial**: 2 replicas (high availability)
- **Production**: 3-5 replicas (load distribution)
- **Autoscaling**: HPA based on CPU (target 70% utilization)

#### Load Balancing
- **Strategy**: Round-robin (stateless)
- **Session Affinity**: Not required (except registration flow)
- **Health Checks**: Remove unhealthy instances automatically

## API Reference

### Token Verification

#### POST /api/v1/auth/verify-token
Verify JWT token (Auth0 or isa_user)

**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "provider": "isa_user"  // optional: auth0, isa_user, local
}
```

**Response (Success):**
```json
{
  "valid": true,
  "provider": "isa_user",
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "subscription_level": "pro",
  "organization_id": "org_xyz789",
  "expires_at": "2024-01-01T13:00:00Z",
  "error": null
}
```

**Response (Failure):**
```json
{
  "valid": false,
  "provider": null,
  "user_id": null,
  "email": null,
  "subscription_level": null,
  "organization_id": null,
  "expires_at": null,
  "error": "Token has expired"
}
```

### Registration

#### POST /api/v1/auth/register
Start user registration with email verification

**Request:**
```json
{
  "email": "user@example.com",
  "password": "StrongP@ss123",
  "name": "Alice Smith"  // optional
}
```

**Response:**
```json
{
  "pending_registration_id": "a1b2c3d4e5f6",
  "verification_required": true,
  "expires_at": "2024-01-01T12:10:00Z"
}
```

#### POST /api/v1/auth/verify
Verify registration code and create account

**Request:**
```json
{
  "pending_registration_id": "a1b2c3d4e5f6",
  "code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "error": null
}
```

### Token Generation

#### POST /api/v1/auth/dev-token
Generate development token (access token only)

**Request:**
```json
{
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "expires_in": 3600,
  "subscription_level": "pro",
  "organization_id": "org_xyz789",
  "permissions": ["read:profile", "write:data"],
  "metadata": {"custom_field": "value"}
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "provider": "isa_user"
}
```

#### POST /api/v1/auth/token-pair
Generate token pair (access + refresh)

**Request:**
```json
{
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "organization_id": "org_xyz789",
  "permissions": ["read:profile"],
  "metadata": {}
}
```

**Response:**
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "provider": "isa_user"
}
```

#### POST /api/v1/auth/refresh
Refresh access token

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "provider": "isa_user"
}
```

### API Key Management

#### POST /api/v1/auth/api-keys
Create API key

**Request:**
```json
{
  "organization_id": "org_xyz789",
  "name": "Production API",
  "permissions": ["read:users", "write:data"],
  "expires_days": 365  // optional, null = no expiration
}
```

**Response:**
```json
{
  "success": true,
  "api_key": "sk_live_abc123xyz...",  // only returned once!
  "key_id": "key_abc123",
  "name": "Production API",
  "expires_at": "2025-01-01T00:00:00Z"
}
```

#### POST /api/v1/auth/verify-api-key
Verify API key

**Request:**
```json
{
  "api_key": "sk_live_abc123xyz..."
}
```

**Response:**
```json
{
  "valid": true,
  "key_id": "key_abc123",
  "organization_id": "org_xyz789",
  "name": "Production API",
  "permissions": ["read:users", "write:data"],
  "error": null
}
```

#### GET /api/v1/auth/api-keys/{organization_id}
List API keys for organization

**Response:**
```json
{
  "success": true,
  "api_keys": [
    {
      "key_id": "key_abc123",
      "name": "Production API",
      "permissions": ["read:users", "write:data"],
      "created_at": "2024-01-01T00:00:00Z",
      "expires_at": "2025-01-01T00:00:00Z",
      "last_used": "2024-06-01T12:00:00Z",
      "is_active": true
    }
  ],
  "total": 1
}
```

#### DELETE /api/v1/auth/api-keys/{key_id}?organization_id={org_id}
Revoke API key

**Response:**
```json
{
  "success": true,
  "message": "API key revoked"
}
```

### Device Authentication

#### POST /api/v1/auth/device/register
Register device and get credentials

**Request:**
```json
{
  "device_id": "dev_sensor123",
  "organization_id": "org_xyz789",
  "device_name": "Living Room Sensor",
  "device_type": "emoframe",
  "metadata": {"firmware": "1.0.0"},
  "expires_days": 365  // optional
}
```

**Response:**
```json
{
  "success": true,
  "device_id": "dev_sensor123",
  "device_secret": "abc123xyz...",  // only returned once!
  "organization_id": "org_xyz789",
  "device_name": "Living Room Sensor",
  "device_type": "emoframe",
  "status": "active",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### POST /api/v1/auth/device/authenticate
Authenticate device and get JWT token

**Request:**
```json
{
  "device_id": "dev_sensor123",
  "device_secret": "abc123xyz..."
}
```

**Response:**
```json
{
  "success": true,
  "authenticated": true,
  "device_id": "dev_sensor123",
  "organization_id": "org_xyz789",
  "device_name": "Living Room Sensor",
  "device_type": "emoframe",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

#### POST /api/v1/auth/device/verify-token
Verify device JWT token

**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "valid": true,
  "device_id": "dev_sensor123",
  "organization_id": "org_xyz789",
  "device_type": "emoframe",
  "expires_at": "2024-01-02T12:00:00Z"
}
```

#### POST /api/v1/auth/device/{device_id}/pairing-token
Generate pairing token for QR code

**Response:**
```json
{
  "success": true,
  "pairing_token": "abc123xyz...",
  "expires_at": "2024-01-01T12:05:00Z",
  "expires_in": 300
}
```

#### POST /api/v1/auth/device/pairing-token/verify
Verify pairing token (user scans QR)

**Request:**
```json
{
  "device_id": "dev_display456",
  "pairing_token": "abc123xyz...",
  "user_id": "usr_abc123"
}
```

**Response:**
```json
{
  "valid": true,
  "device_id": "dev_display456",
  "user_id": "usr_abc123"
}
```

## Testing Strategy

### Unit Testing
- **AuthenticationService**: Mock JWT manager, account client, notification client
- **ApiKeyService**: Mock API key repository
- **DeviceAuthService**: Mock device auth repository
- **Repositories**: Mock AsyncPostgresClient

### Integration Testing
- **Registration Flow**: End-to-end with real database
- **Token Verification**: Test Auth0 and isa_user providers
- **Device Pairing**: QR code flow with real tokens

### Test Files
- `tests/unit/services/test_auth_service.py`
- `tests/integration/services/test_auth_integration.py`
- `tests/fixtures/auth_fixtures.py`

## Future Enhancements

### Security
1. **Rate Limiting**: Prevent brute-force attacks on registration
2. **CAPTCHA**: Bot prevention for registration
3. **2FA/MFA**: Multi-factor authentication support
4. **Redis for Pending Registrations**: Shared state across instances

### Features
1. **OAuth2 Providers**: Google, GitHub, Apple sign-in
2. **Password Reset**: Email-based password recovery
3. **Session Management**: List and revoke active sessions
4. **Device Groups**: Organize devices by location/function

### Performance
1. **Redis Caching**: Cache JWKS, API keys, device credentials
2. **Connection Pooling**: Optimize gRPC connection reuse
3. **Async Event Publishing**: Queue-based event publishing

### Observability
1. **Metrics**: Prometheus metrics for token verification latency
2. **Tracing**: OpenTelemetry distributed tracing
3. **Dashboards**: Grafana dashboards for auth service health
