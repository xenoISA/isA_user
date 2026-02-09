# Authentication Service - Domain Context

## Overview

The Authentication Service is the **identity verification gateway** for the entire isA_user platform. It provides centralized authentication, token management, identity verification, API key management, and device authentication. Every authenticated request passes through this service's verification logic.

**Business Context**: Enable secure, scalable identity verification that validates user credentials and issues secure tokens for access control. Authentication Service owns the "who are you?" verification of the system - ensuring every request comes from a legitimate, verified identity.

**Core Value Proposition**: Transform authentication challenges into secure, verified sessions using multi-provider JWT verification, self-issued tokens, API keys, and device credentials - providing flexible authentication for users, applications, and IoT devices.

---

## Business Taxonomy

### Core Entities

#### 1. JWT Token
**Definition**: A JSON Web Token used to verify user identity and authorize access to platform resources.

**Business Purpose**:
- Establish authenticated session for users
- Carry user identity claims and permissions
- Enable stateless authentication across microservices
- Support token refresh for continuous sessions

**Token Types**:
- **Access Token**: Short-lived token (1 hour) for API access
- **Refresh Token**: Long-lived token (7 days) for obtaining new access tokens

**Key Claims**:
- user_id: Unique user identifier
- email: User email address
- organization_id: Optional organization context
- permissions: List of granted permissions
- scope: Token scope (user, device, service)
- token_type: Type identifier (access, refresh)
- iat: Issued at timestamp
- exp: Expiration timestamp
- jti: Unique token identifier

#### 2. Token Provider
**Definition**: Authentication provider that issues and validates JWT tokens.

**Business Purpose**:
- Support multiple authentication sources
- Enable OAuth integration
- Allow custom identity providers
- Provide provider-specific verification logic

**Supported Providers**:
- **isa_user**: Custom self-issued JWT tokens (primary provider)
- **auth0**: Auth0 OAuth integration (optional)
- **local**: Alias for isa_user (development)

**Provider Detection**:
- Automatic detection from token issuer claim (`iss`)
- Manual provider specification in verification requests
- Fallback to isa_user for unknown providers

#### 3. Registration Flow
**Definition**: Email-based user registration with verification code authentication.

**Business Purpose**:
- Onboard new users securely
- Verify email ownership before account creation
- Generate initial authentication tokens
- Trigger downstream account provisioning

**Registration Stages**:
1. **Start Registration**: User provides email, password, optional name
2. **Code Generation**: System generates 6-digit verification code
3. **Email Delivery**: Verification code sent to user's email
4. **Code Verification**: User submits code within 10 minutes
5. **Account Creation**: Account Service creates user profile
6. **Token Issuance**: Access and refresh tokens generated
7. **Event Publishing**: `user.registered` event published

**Security Features**:
- 6-digit numeric verification code (000000-999999)
- 10-minute expiration window
- One-time code usage
- Password validation requirements
- Email uniqueness check

#### 4. API Key
**Definition**: Long-lived credential for programmatic API access by applications and services.

**Business Purpose**:
- Enable server-to-server authentication
- Provide organization-scoped access control
- Support automated workflows and integrations
- Track API usage by application

**Key Attributes**:
- key_id: Unique identifier for the API key
- api_key: Secret credential (prefix: `isa_ak_`)
- organization_id: Owning organization
- name: Human-readable key identifier
- permissions: List of granted permissions
- status: active, revoked, expired
- expires_at: Optional expiration timestamp
- created_at: Key creation timestamp
- created_by: User who created the key
- last_used: Last usage timestamp

**Lifecycle States**:
- **Active**: Key is valid for authentication
- **Revoked**: Key permanently disabled by admin
- **Expired**: Key passed expiration timestamp

#### 5. Device Credential
**Definition**: Authentication credential for IoT devices and embedded systems.

**Business Purpose**:
- Enable device-to-server authentication
- Secure IoT device access to platform APIs
- Track device identity and activity
- Support device lifecycle management

**Key Attributes**:
- device_id: Unique device identifier
- device_secret: Hashed secret (SHA-256)
- organization_id: Owning organization
- device_name: Human-readable device name
- device_type: Device category (display, camera, sensor, gateway)
- status: active, inactive, revoked
- metadata: Flexible device properties (JSONB)
- expires_at: Optional credential expiration
- created_at: Registration timestamp
- last_authenticated: Last successful login

**Security Model**:
- Device secret hashed with SHA-256
- Plain secret only returned during registration
- Secret rotation supported via refresh endpoint
- Device tokens scoped to organization

#### 6. Device Pairing
**Definition**: Temporary token-based mechanism for binding a device to a user account.

**Business Purpose**:
- Enable user-device association
- Support QR code pairing workflow
- Provide time-limited pairing window
- Trigger device provisioning events

**Pairing Flow**:
1. Display device generates pairing token (5-minute expiry)
2. Device displays QR code containing pairing token
3. Mobile user scans QR code
4. Mobile app verifies pairing token with user_id
5. Device Service creates device-user binding
6. `device.paired` event published

**Security Features**:
- URL-safe random token (32 bytes)
- 5-minute expiration window
- One-time token usage
- User ID verification required
- Device ID validation

#### 7. Token Claims
**Definition**: Structured data embedded in JWT tokens describing the authenticated entity.

**Business Purpose**:
- Carry identity information
- Encode permissions and scopes
- Enable stateless authorization
- Support audit trails

**Standard Claims**:
- **sub** (subject): User ID or device ID
- **iss** (issuer): Token provider (isA_user, auth0)
- **iat** (issued at): Token creation timestamp
- **exp** (expires): Token expiration timestamp
- **jti** (JWT ID): Unique token identifier

**Custom Claims**:
- **user_id**: User identifier (for user tokens)
- **email**: User email address
- **organization_id**: Organization context
- **permissions**: Granted permission list
- **scope**: Token scope (user, device, service)
- **token_type**: Type (access, refresh)
- **metadata**: Flexible custom data (JSONB)

#### 8. Session
**Definition**: Authenticated user session consisting of access and refresh token pair.

**Business Purpose**:
- Track active user sessions
- Enable session management and invalidation
- Support "logout everywhere" functionality
- Monitor concurrent session limits

**Session Components**:
- **Access Token**: Short-lived (1 hour) for API calls
- **Refresh Token**: Long-lived (7 days) for token renewal
- **Session ID**: Unique session identifier
- **Expiration**: Session expiry timestamp
- **Last Activity**: Last token usage timestamp

**Session Lifecycle**:
1. **Creation**: Login generates token pair
2. **Active**: User makes authenticated requests
3. **Refresh**: Access token renewed using refresh token
4. **Expiration**: Session expires after 7 days
5. **Invalidation**: Manual logout destroys session

---

## Domain Scenarios

### Scenario 1: User Registration with Email Verification
**Actor**: New User, Mobile App
**Trigger**: User completes registration form
**Flow**:
1. User enters email (alice@example.com), password (Strong#123), name (Alice)
2. App calls `POST /api/v1/auth/register` with credentials
3. Auth Service validates:
   - Email format is valid
   - Password meets strength requirements (min 8 chars)
4. Auth Service generates:
   - pending_registration_id: `abc123`
   - 6-digit verification code: `724851`
   - Expiration: 10 minutes from now
5. Verification code stored in-memory with TTL
6. Notification Service sends email with code
7. Auth Service returns `pending_registration_id` and `expires_at`
8. User receives email, enters code `724851`
9. App calls `POST /api/v1/auth/verify` with pending_id and code
10. Auth Service validates:
    - pending_registration_id exists
    - Code matches stored value
    - Not expired (within 10 minutes)
11. Auth Service generates user_id: `usr_def456`
12. Account Service `/ensure` endpoint called:
    - Creates account record with user_id, email, name
    - Sets is_active = true
    - Initializes default preferences
13. Account Service publishes `user.created` event
14. Auth Service generates token pair:
    - Access token (1 hour expiry)
    - Refresh token (7 days expiry)
15. Auth Service publishes `user.logged_in` event
16. Returns tokens, user_id, email to app
17. User immediately authenticated, app stores tokens

**Outcome**: New user registered, email verified, account created, tokens issued, downstream services notified

### Scenario 2: JWT Token Verification (Multi-Provider)
**Actor**: API Gateway, User Request
**Trigger**: User makes authenticated API request
**Flow**:
1. User's mobile app makes request with Bearer token
2. API Gateway extracts JWT from Authorization header
3. Gateway calls `POST /api/v1/auth/verify-token` with token
4. Auth Service decodes token header without signature verification
5. Examines issuer (`iss`) claim:
   - `iss: "isA_user"` → Custom JWT verification
   - `iss: "https://yourapp.auth0.com/"` → Auth0 verification
6. **If isa_user provider**:
   - Retrieves JWT_SECRET from environment
   - Verifies signature using HS256 algorithm
   - Validates expiration timestamp
   - Extracts claims: user_id, email, organization_id, permissions
   - Returns verification result with extracted claims
7. **If auth0 provider**:
   - Fetches Auth0 JWKS from `/.well-known/jwks.json`
   - Extracts `kid` from token header
   - Finds matching public key from JWKS
   - Verifies signature using RS256 algorithm
   - Validates audience and issuer
   - Extracts standard claims: sub, email
   - Returns verification result
8. Gateway receives verification response:
   ```json
   {
     "valid": true,
     "provider": "isa_user",
     "user_id": "usr_abc123",
     "email": "alice@example.com",
     "organization_id": "org_xyz789",
     "permissions": ["read:photos", "write:albums"],
     "expires_at": "2025-12-13T15:30:00Z"
   }
   ```
9. Gateway allows request to proceed if valid=true
10. Request forwarded to downstream microservice

**Outcome**: Token verified, user identity confirmed, request authorized

### Scenario 3: Token Pair Generation with Login Event
**Actor**: Auth Service, Login Flow
**Trigger**: User successfully authenticates (email/password or OAuth)
**Flow**:
1. User provides valid credentials
2. Auth Service validates user identity
3. Retrieves user account from Account Service
4. Prepares token claims:
   - user_id: `usr_abc123`
   - email: `alice@example.com`
   - organization_id: `org_xyz789` (if user has org)
   - permissions: Fetched from Authorization Service
   - scope: `user`
5. JWT Manager creates access token:
   - Claims encoded with user context
   - Expiration: 1 hour (3600 seconds)
   - Signed with JWT_SECRET using HS256
   - Token format: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
6. JWT Manager creates refresh token:
   - Minimal claims (user_id, token_type=refresh)
   - Expiration: 7 days (604800 seconds)
   - Signed with same secret
7. Auth Service publishes `user.logged_in` event to NATS:
   ```json
   {
     "event_type": "user.logged_in",
     "source": "auth_service",
     "data": {
       "user_id": "usr_abc123",
       "email": "alice@example.com",
       "organization_id": "org_xyz789",
       "timestamp": "2025-12-13T12:00:00Z",
       "provider": "isa_user"
     },
     "metadata": {
       "permissions": "read:photos,write:albums",
       "has_organization": "true"
     }
   }
   ```
8. Session Service receives event, creates session record
9. Audit Service logs login event
10. Analytics Service tracks active user
11. Auth Service returns token pair:
    ```json
    {
      "success": true,
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 3600,
      "user_id": "usr_abc123",
      "email": "alice@example.com",
      "provider": "isa_user"
    }
    ```

**Outcome**: User authenticated, tokens issued, session tracked, downstream services notified

### Scenario 4: API Key Lifecycle Management
**Actor**: Developer, Admin Dashboard
**Trigger**: Developer needs programmatic API access for integration
**Flow**:
1. Developer navigates to API Keys section in dashboard
2. Clicks "Create API Key" for organization `org_xyz789`
3. Provides:
   - name: "Production Integration"
   - permissions: ["read:photos", "write:albums", "read:users"]
   - expires_days: 365 (1 year)
4. Dashboard calls `POST /api/v1/auth/api-keys`:
   ```json
   {
     "organization_id": "org_xyz789",
     "name": "Production Integration",
     "permissions": ["read:photos", "write:albums", "read:users"],
     "expires_days": 365
   }
   ```
5. Auth Service generates:
   - key_id: `key_abc123`
   - api_key: `isa_ak_live_1234567890abcdef`
   - secret_hash: SHA-256 hash of api_key
   - expires_at: 365 days from now
6. API key stored in `organizations.api_keys` JSONB field:
   ```json
   {
     "key_id": "key_abc123",
     "key_hash": "sha256_hash_here",
     "name": "Production Integration",
     "permissions": ["read:photos", "write:albums", "read:users"],
     "status": "active",
     "created_at": "2025-12-13T12:00:00Z",
     "created_by": "usr_dev123",
     "expires_at": "2026-12-13T12:00:00Z",
     "last_used": null
   }
   ```
7. Auth Service publishes `api_key.created` event
8. Returns API key to dashboard:
   ```json
   {
     "success": true,
     "api_key": "isa_ak_live_1234567890abcdef",
     "key_id": "key_abc123",
     "name": "Production Integration",
     "expires_at": "2026-12-13T12:00:00Z"
   }
   ```
9. Dashboard displays key with warning: "Save this key - it won't be shown again"
10. Developer copies key, stores in secure environment variables
11. **Later: API Key Usage**
    - Application makes request with `Authorization: Bearer isa_ak_live_1234567890abcdef`
    - Gateway calls `POST /api/v1/auth/verify-api-key`
    - Auth Service hashes provided key, looks up in database
    - Validates: status=active, not expired, organization exists
    - Updates last_used timestamp
    - Returns permissions and organization_id
12. **Later: Key Revocation**
    - Developer suspects key compromise
    - Calls `DELETE /api/v1/auth/api-keys/{key_id}?organization_id=org_xyz789`
    - Auth Service sets status=revoked
    - Publishes `api_key.revoked` event
    - All future requests with that key rejected

**Outcome**: Secure programmatic access enabled, key lifecycle tracked, revocation supported

### Scenario 5: Device Registration and Authentication
**Actor**: EmoFrame Display Device, Admin
**Trigger**: New device unboxed and powered on
**Flow**:
1. Device boots up, displays "Device Registration Required"
2. Admin connects to device's local setup WiFi
3. Admin opens setup wizard, provides organization_id: `org_xyz789`
4. Device generates unique device_id: `dev_emoframe_001`
5. Device calls `POST /api/v1/auth/device/register`:
   ```json
   {
     "device_id": "dev_emoframe_001",
     "organization_id": "org_xyz789",
     "device_name": "Living Room Display",
     "device_type": "display",
     "metadata": {
       "model": "EmoFrame Pro",
       "firmware_version": "2.1.0"
     },
     "expires_days": 365
   }
   ```
6. Auth Service validates organization exists (via Organization Service)
7. Auth Service generates:
   - device_secret: Random 32-byte URL-safe string
   - device_secret_hash: SHA-256 hash of device_secret
8. Stores device credential in `auth.device_credentials` table:
   ```sql
   INSERT INTO auth.device_credentials (
     device_id, device_secret, organization_id, device_name,
     device_type, status, metadata, expires_at
   )
   ```
9. Publishes `device.registered` event to NATS
10. Returns device_secret to device (only time it's visible):
    ```json
    {
      "success": true,
      "device_id": "dev_emoframe_001",
      "device_secret": "abc123xyz789secretkey",
      "organization_id": "org_xyz789",
      "device_name": "Living Room Display",
      "status": "active"
    }
    ```
11. Device securely stores device_secret in encrypted storage
12. **Later: Device Authentication**
    - Device calls `POST /api/v1/auth/device/authenticate`:
      ```json
      {
        "device_id": "dev_emoframe_001",
        "device_secret": "abc123xyz789secretkey"
      }
      ```
13. Auth Service hashes provided secret, compares with stored hash
14. Validates: status=active, not expired
15. Generates device JWT token:
    - Payload: device_id, organization_id, device_type, type=device
    - Expiration: 24 hours
    - Signed with JWT_SECRET
16. Publishes `device.authenticated` event
17. Returns device token:
    ```json
    {
      "success": true,
      "authenticated": true,
      "device_id": "dev_emoframe_001",
      "organization_id": "org_xyz789",
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 86400
    }
    ```
18. Device uses token for API requests for next 24 hours

**Outcome**: Device registered, credentials secured, authenticated access enabled

### Scenario 6: Device Pairing Flow
**Actor**: EmoFrame Display, Mobile User
**Trigger**: User wants to pair mobile app with display device
**Flow**:
1. User taps "Add Device" in mobile app
2. Display device is in pairing mode, shows "Ready to Pair"
3. Display calls `POST /api/v1/auth/device/{device_id}/pairing-token`
4. Auth Service generates:
   - pairing_token: Random 32-byte URL-safe string
   - expires_at: 5 minutes from now
5. Stores pairing token in `auth.device_pairing_tokens` table:
   ```sql
   INSERT INTO auth.device_pairing_tokens (
     device_id, pairing_token, expires_at, used
   ) VALUES (
     'dev_emoframe_001', 'pair_abc123xyz789', NOW() + INTERVAL '5 minutes', false
   )
   ```
6. Publishes `device.pairing_token_generated` event
7. Returns pairing token to device:
   ```json
   {
     "success": true,
     "pairing_token": "pair_abc123xyz789",
     "expires_at": "2025-12-13T12:05:00Z",
     "expires_in": 300
   }
   ```
8. Display generates QR code containing pairing token
9. User scans QR code with mobile app
10. App extracts pairing_token, retrieves user_id from stored session
11. App calls `POST /api/v1/auth/device/pairing-token/verify`:
    ```json
    {
      "device_id": "dev_emoframe_001",
      "pairing_token": "pair_abc123xyz789",
      "user_id": "usr_alice123"
    }
    ```
12. Auth Service validates:
    - Pairing token exists
    - device_id matches token record
    - Token not expired (within 5 minutes)
    - Token not already used
13. Marks token as used, stores user_id:
    ```sql
    UPDATE auth.device_pairing_tokens
    SET used = true, paired_user_id = 'usr_alice123', paired_at = NOW()
    WHERE pairing_token = 'pair_abc123xyz789'
    ```
14. Publishes `device.paired` event:
    ```json
    {
      "event_type": "device.paired",
      "source": "auth_service",
      "data": {
        "device_id": "dev_emoframe_001",
        "user_id": "usr_alice123",
        "timestamp": "2025-12-13T12:03:00Z"
      }
    }
    ```
15. Device Service receives event, creates device-user binding
16. Auth Service returns success:
    ```json
    {
      "valid": true,
      "device_id": "dev_emoframe_001",
      "user_id": "usr_alice123"
    }
    ```
17. Mobile app shows "Device Paired Successfully"
18. Display shows "Paired to Alice's Account"

**Outcome**: Device-user pairing completed, relationship established, downstream services notified

### Scenario 7: Token Refresh
**Actor**: Mobile App, Background Service
**Trigger**: Access token expired (after 1 hour)
**Flow**:
1. Mobile app makes API request with expired access token
2. Gateway returns 401 Unauthorized, error: "Token expired"
3. App detects expired access token
4. App retrieves stored refresh_token from secure storage
5. App calls `POST /api/v1/auth/refresh`:
   ```json
   {
     "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   }
   ```
6. Auth Service validates refresh token:
   - Verifies signature using JWT_SECRET
   - Checks token_type claim is "refresh"
   - Validates not expired (within 7 days)
   - Extracts user_id from claims
7. JWT Manager retrieves original token claims
8. Generates new access token:
   - Same claims as original token
   - New expiration: 1 hour from now
   - New jti (token ID)
9. Publishes `token.refreshed` event
10. Returns new access token:
    ```json
    {
      "success": true,
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 3600,
      "provider": "isa_user"
    }
    ```
11. App stores new access token
12. Retries original API request with new token
13. Request succeeds

**Outcome**: Seamless token renewal, user session continues without re-login

### Scenario 8: Session Management and Invalidation
**Actor**: User, Web Application
**Trigger**: User clicks "Logout" or "Logout from all devices"
**Flow**:
1. **Normal Logout**:
   - User clicks "Logout" on web app
   - App discards access and refresh tokens from local storage
   - App calls `POST /api/v1/auth/logout` (if endpoint exists)
   - Session Service marks session inactive
   - Publishes `session.invalidated` event
   - User redirected to login page
2. **Logout from All Devices**:
   - User clicks "Logout Everywhere" in account settings
   - App calls `POST /api/v1/auth/logout-all`
   - Session Service retrieves all active sessions for user_id
   - Invalidates all sessions in database
   - Publishes `session.invalidated` events for each session
   - All devices with old tokens receive 401 on next request
   - Devices forced to re-authenticate
3. **Automatic Session Expiration**:
   - Refresh token expires after 7 days
   - User attempts to refresh access token
   - Auth Service returns error: "Refresh token expired"
   - Session Service marks session expired
   - App redirects user to login
4. **Session Activity Tracking**:
   - Each authenticated API request updates session.last_activity
   - Session Service tracks concurrent session count
   - Analytics Service monitors active session metrics

**Outcome**: Controlled session lifecycle, security through token invalidation, audit trail maintained

---

## Domain Events

### Published Events

#### 1. user.registered
**Trigger**: New user successfully completes email verification and account creation
**Subject**: `events.user.registered`
**Payload**:
```json
{
  "event_type": "user.registered",
  "source": "auth_service",
  "data": {
    "user_id": "usr_abc123",
    "email": "alice@example.com",
    "name": "Alice",
    "registration_method": "email_verification",
    "timestamp": "2025-12-13T12:00:00Z"
  },
  "metadata": {
    "verification_code_used": "true",
    "provider": "isa_user"
  }
}
```
**Subscribers**:
- **Account Service**: Ensure account exists (idempotent)
- **Subscription Service**: Create default free tier subscription
- **Wallet Service**: Initialize user wallet
- **Audit Service**: Log registration event
- **Analytics Service**: Track user acquisition
- **Notification Service**: Send welcome email

#### 2. user.logged_in
**Trigger**: User successfully authenticates and token pair generated
**Subject**: `events.user.logged_in`
**Payload**:
```json
{
  "event_type": "user.logged_in",
  "source": "auth_service",
  "data": {
    "user_id": "usr_abc123",
    "email": "alice@example.com",
    "organization_id": "org_xyz789",
    "timestamp": "2025-12-13T12:00:00Z",
    "provider": "isa_user"
  },
  "metadata": {
    "permissions": "read:photos,write:albums",
    "has_organization": "true"
  }
}
```
**Subscribers**:
- **Session Service**: Create or update session record
- **Audit Service**: Log authentication event
- **Analytics Service**: Track daily active users
- **Notification Service**: Send login notification (if configured)

#### 3. device.registered
**Trigger**: New device credential successfully created
**Subject**: `events.device.registered`
**Payload**:
```json
{
  "event_type": "device.registered",
  "source": "auth_service",
  "data": {
    "device_id": "dev_emoframe_001",
    "organization_id": "org_xyz789",
    "device_name": "Living Room Display",
    "device_type": "display",
    "status": "active",
    "timestamp": "2025-12-13T12:00:00Z"
  }
}
```
**Subscribers**:
- **Device Service**: Create device profile record
- **Organization Service**: Update device count for organization
- **Audit Service**: Log device registration
- **Analytics Service**: Track device adoption metrics

#### 4. device.authenticated
**Trigger**: Device successfully authenticates with device credentials
**Subject**: `events.device.authenticated`
**Payload**:
```json
{
  "event_type": "device.authenticated",
  "source": "auth_service",
  "data": {
    "device_id": "dev_emoframe_001",
    "organization_id": "org_xyz789",
    "device_name": "Living Room Display",
    "device_type": "display",
    "timestamp": "2025-12-13T12:00:00Z",
    "ip_address": "192.168.1.100"
  },
  "metadata": {
    "user_agent": "EmoFrame/2.1.0"
  }
}
```
**Subscribers**:
- **Device Service**: Update last_authenticated timestamp
- **Audit Service**: Log device access
- **Telemetry Service**: Track device connectivity
- **Analytics Service**: Monitor device uptime

#### 5. device.paired
**Trigger**: Device successfully paired with user account via pairing token
**Subject**: `events.device.paired`
**Payload**:
```json
{
  "event_type": "device.paired",
  "source": "auth_service",
  "data": {
    "device_id": "dev_emoframe_001",
    "user_id": "usr_alice123",
    "timestamp": "2025-12-13T12:03:00Z"
  }
}
```
**Subscribers**:
- **Device Service**: Create device-user relationship
- **Organization Service**: Grant user access to device organization
- **Notification Service**: Send pairing success notification
- **Audit Service**: Log pairing event

#### 6. api_key.created
**Trigger**: New API key generated for organization
**Subject**: `events.api_key.created`
**Payload**:
```json
{
  "event_type": "api_key.created",
  "source": "auth_service",
  "data": {
    "key_id": "key_abc123",
    "organization_id": "org_xyz789",
    "name": "Production Integration",
    "permissions": ["read:photos", "write:albums"],
    "created_by": "usr_dev123",
    "expires_at": "2026-12-13T12:00:00Z",
    "timestamp": "2025-12-13T12:00:00Z"
  }
}
```
**Subscribers**:
- **Audit Service**: Log API key creation
- **Organization Service**: Update API key count
- **Analytics Service**: Track API key usage patterns

#### 7. api_key.revoked
**Trigger**: API key permanently revoked by admin
**Subject**: `events.api_key.revoked`
**Payload**:
```json
{
  "event_type": "api_key.revoked",
  "source": "auth_service",
  "data": {
    "key_id": "key_abc123",
    "organization_id": "org_xyz789",
    "name": "Production Integration",
    "revoked_by": "usr_admin456",
    "reason": "Security incident",
    "timestamp": "2025-12-13T15:00:00Z"
  }
}
```
**Subscribers**:
- **Audit Service**: Log revocation for compliance
- **Notification Service**: Alert API key owner
- **Analytics Service**: Track revocation reasons

#### 8. session.created
**Trigger**: New authentication session established (token pair issued)
**Subject**: `events.session.created`
**Payload**:
```json
{
  "event_type": "session.created",
  "source": "auth_service",
  "data": {
    "session_id": "sess_xyz789",
    "user_id": "usr_abc123",
    "expires_at": "2025-12-20T12:00:00Z",
    "timestamp": "2025-12-13T12:00:00Z"
  }
}
```
**Subscribers**:
- **Session Service**: Track active session
- **Analytics Service**: Monitor concurrent sessions

#### 9. session.invalidated
**Trigger**: User logs out or session manually invalidated
**Subject**: `events.session.invalidated`
**Payload**:
```json
{
  "event_type": "session.invalidated",
  "source": "auth_service",
  "data": {
    "session_id": "sess_xyz789",
    "user_id": "usr_abc123",
    "reason": "user_logout",
    "timestamp": "2025-12-13T18:00:00Z"
  }
}
```
**Subscribers**:
- **Session Service**: Mark session inactive
- **Audit Service**: Log logout event
- **Analytics Service**: Track session duration

#### 10. token.refreshed
**Trigger**: Access token successfully refreshed using refresh token
**Subject**: `events.token.refreshed`
**Payload**:
```json
{
  "event_type": "token.refreshed",
  "source": "auth_service",
  "data": {
    "user_id": "usr_abc123",
    "session_id": "sess_xyz789",
    "timestamp": "2025-12-13T13:00:00Z"
  }
}
```
**Subscribers**:
- **Session Service**: Update session activity timestamp
- **Analytics Service**: Track token refresh patterns

---

## Core Concepts

### Authentication vs Authorization
**Separation of Concerns**:
- **Auth Service** handles **identity verification** ("Who are you?")
  - Verify JWT tokens
  - Validate API keys
  - Authenticate device credentials
  - Issue access tokens
- **Authorization Service** handles **permission checks** ("What can you do?")
  - Check role-based permissions
  - Evaluate resource ownership
  - Apply organization policies
  - Enforce access control rules

**Clean Boundary**:
- Auth Service never makes authorization decisions
- Auth Service carries permissions in token claims but doesn't interpret them
- Authorization Service receives verified identity from Auth Service
- Microservices call both services: Auth for identity, Authorization for permissions

### Token Strategy
**Primary Provider: isa_user (Custom JWT)**:
- Self-issued tokens using HS256 symmetric signing
- Full control over token lifecycle
- No external dependencies
- Secret key stored in JWT_SECRET environment variable
- Supports custom claims structure

**Secondary Provider: Auth0 (OAuth Integration)**:
- OAuth 2.0 / OpenID Connect support
- RS256 asymmetric signature verification
- JWKS (JSON Web Key Set) public key retrieval
- Supports social login providers (Google, Facebook, Apple)
- Optional integration for enterprise customers

**Token Lifecycle**:
- **Access Token**: 1 hour lifespan, used for API requests
- **Refresh Token**: 7 days lifespan, used to obtain new access tokens
- **Device Token**: 24 hour lifespan, used by IoT devices
- **Pairing Token**: 5 minutes lifespan, one-time use for device pairing

### Identity Authority
**Auth Service as Identity Generator**:
- Auth Service generates user_id after successful verification
- Format: `usr_{uuid_hex}` (e.g., `usr_abc123def456`)
- Auth Service is the **source of truth** for user_id assignment
- Account Service creates profile with Auth-provided user_id

**Account Service as Profile Owner**:
- Account Service stores full user profile (email, name, preferences)
- Account Service manages account lifecycle (creation, updates, deactivation)
- Auth Service notifies Account Service when new user verified

**Idempotent Coordination**:
- Auth Service calls Account Service `/api/v1/accounts/ensure` endpoint
- If user_id already exists, Account Service returns existing account
- No duplicate accounts created even with retry/failure scenarios

### Device Security
**Secret Management**:
- Device secret generated with `secrets.token_urlsafe(32)` (256-bit entropy)
- Secret hashed with SHA-256 before storage
- Plain secret only shown once during registration
- No way to retrieve original secret after registration
- Secret rotation supported via `/refresh-secret` endpoint

**Token Scoping**:
- Device tokens scoped to organization_id
- Device cannot access resources outside its organization
- Device type encoded in token for service-level access control
- Device tokens have `type: "device"` claim for identification

**Pairing Security**:
- Pairing tokens expire in 5 minutes
- One-time use enforced by `used` flag
- User ID verification required for pairing completion
- QR code contains only pairing token, not credentials

---

## High-Level Business Rules

### Token Verification Rules
- **BR-AUTH-001**: All tokens must have valid signature from configured JWT_SECRET
- **BR-AUTH-002**: Expired tokens rejected with "Token expired" error
- **BR-AUTH-003**: Malformed tokens rejected with "Invalid token format" error
- **BR-AUTH-004**: Token issuer (`iss`) must match supported providers (isa_user, auth0)
- **BR-AUTH-005**: Auto-detection tries isa_user if provider not specified
- **BR-AUTH-006**: Token must contain required claims: sub, iat, exp
- **BR-AUTH-007**: Access tokens validated by checking token_type claim
- **BR-AUTH-008**: Refresh tokens can only be used for token refresh endpoint
- **BR-AUTH-009**: Device tokens must have `type: "device"` claim
- **BR-AUTH-010**: Token jti (JWT ID) should be unique per issuance

### Registration Rules
- **BR-REG-001**: Email must be valid format (RFC 5322 compliant)
- **BR-REG-002**: Email must be unique across all registered users
- **BR-REG-003**: Password minimum length is 8 characters
- **BR-REG-004**: Password must contain mix of uppercase, lowercase, numbers, special chars
- **BR-REG-005**: Verification code is 6-digit numeric (000000-999999)
- **BR-REG-006**: Verification code expires in 10 minutes from generation
- **BR-REG-007**: Each verification code is single-use only
- **BR-REG-008**: Pending registration ID is random 32-character hex string
- **BR-REG-009**: Maximum 3 verification code attempts per pending registration
- **BR-REG-010**: Name field optional, defaults to email prefix if not provided
- **BR-REG-011**: Expired pending registrations cleaned up automatically
- **BR-REG-012**: Successful verification generates user_id with `usr_` prefix

### Token Generation Rules
- **BR-TKN-001**: Access token expires in 1 hour (3600 seconds)
- **BR-TKN-002**: Refresh token expires in 7 days (604800 seconds)
- **BR-TKN-003**: Device token expires in 24 hours (86400 seconds)
- **BR-TKN-004**: All tokens must include iat (issued at) timestamp
- **BR-TKN-005**: All tokens must include exp (expiration) timestamp
- **BR-TKN-006**: All tokens must include jti (unique token ID)
- **BR-TKN-007**: User tokens must include user_id, email claims
- **BR-TKN-008**: Device tokens must include device_id, organization_id, type=device
- **BR-TKN-009**: Token issuer (`iss`) always set to "isA_user" for custom tokens
- **BR-TKN-010**: Token metadata can include custom claims as JSONB
- **BR-TKN-011**: Token permissions array encoded as JSON array in claims
- **BR-TKN-012**: Organization_id claim optional, null if user not in organization

### API Key Rules
- **BR-API-001**: API keys prefixed with `isa_ak_` for identification
- **BR-API-002**: API key minimum length 32 characters (cryptographically secure)
- **BR-API-003**: API keys scoped to organization_id
- **BR-API-004**: API key name must be unique within organization
- **BR-API-005**: API key permissions validated against defined permission set
- **BR-API-006**: API keys can have optional expiration timestamp
- **BR-API-007**: Expired API keys rejected even if status=active
- **BR-API-008**: Revoked API keys cannot be reactivated
- **BR-API-009**: API key secret hashed before storage (never stored plaintext)
- **BR-API-010**: API key last_used timestamp updated on each verification
- **BR-API-011**: Organization must exist before creating API key
- **BR-API-012**: Only organization admins can create/revoke API keys

### Device Authentication Rules
- **BR-DEV-001**: Device ID must be unique globally
- **BR-DEV-002**: Device secret minimum length 32 characters
- **BR-DEV-003**: Device secret hashed with SHA-256 before storage
- **BR-DEV-004**: Device credentials scoped to organization_id
- **BR-DEV-005**: Device must belong to valid organization
- **BR-DEV-006**: Device type must be one of: display, camera, sensor, gateway
- **BR-DEV-007**: Device status must be "active" to authenticate
- **BR-DEV-008**: Expired device credentials rejected
- **BR-DEV-009**: Device secret rotation invalidates old secret immediately
- **BR-DEV-010**: Device metadata stored as JSONB (flexible schema)
- **BR-DEV-011**: Device token contains organization_id for access scoping
- **BR-DEV-012**: Device tokens cannot be used for user endpoints

### Device Pairing Rules
- **BR-PAIR-001**: Pairing token generated with 256-bit cryptographic randomness
- **BR-PAIR-002**: Pairing token expires in 5 minutes (300 seconds)
- **BR-PAIR-003**: Pairing token is single-use only
- **BR-PAIR-004**: Pairing token verification requires matching device_id
- **BR-PAIR-005**: Pairing token verification requires valid user_id
- **BR-PAIR-006**: Expired pairing tokens rejected
- **BR-PAIR-007**: Used pairing tokens cannot be reused
- **BR-PAIR-008**: Device must exist before generating pairing token
- **BR-PAIR-009**: Pairing success publishes device.paired event
- **BR-PAIR-010**: Pairing token stored in auth.device_pairing_tokens table

### Session Management Rules
- **BR-SESS-001**: Session created when token pair issued
- **BR-SESS-002**: Session ID is unique identifier for token pair
- **BR-SESS-003**: Session expiration matches refresh token expiration (7 days)
- **BR-SESS-004**: Session activity tracked on each authenticated request
- **BR-SESS-005**: Session invalidation destroys both access and refresh tokens
- **BR-SESS-006**: User can invalidate all sessions ("logout everywhere")
- **BR-SESS-007**: Inactive sessions (no activity for 7 days) auto-expire
- **BR-SESS-008**: Session metadata includes last_activity timestamp
- **BR-SESS-009**: Maximum concurrent sessions per user configurable (default: unlimited)

### Provider Routing Rules
- **BR-PROV-001**: Provider auto-detected from token issuer (`iss`) claim
- **BR-PROV-002**: `iss: "isA_user"` routes to custom JWT verification
- **BR-PROV-003**: `iss: "https://*.auth0.com/"` routes to Auth0 verification
- **BR-PROV-004**: Unknown issuer defaults to isa_user provider
- **BR-PROV-005**: Manual provider specification overrides auto-detection
- **BR-PROV-006**: Auth0 tokens verified using RS256 algorithm
- **BR-PROV-007**: Custom tokens verified using HS256 algorithm
- **BR-PROV-008**: JWKS fetched from Auth0 `/.well-known/jwks.json` endpoint
- **BR-PROV-009**: JWKS cached with 15-minute TTL

---

## Authentication Service in the Ecosystem

### Upstream Dependencies
- **PostgreSQL gRPC Service**: Persistent storage for device credentials, pairing tokens
- **NATS Event Bus**: Event publishing infrastructure
- **Account Service**: User profile creation and validation
- **Organization Service**: Organization validation for API keys and devices
- **Notification Service**: Verification code email delivery
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and initial token extraction

### Downstream Consumers
- **All Microservices**: Token verification for authenticated requests
- **Session Service**: Session tracking and management
- **Audit Service**: Authentication event logging
- **Analytics Service**: Login metrics and session analytics
- **Device Service**: Device-user relationship management
- **Subscription Service**: New user subscription provisioning
- **Wallet Service**: User wallet initialization
- **Compliance Service**: GDPR and regulatory event tracking

### Integration Patterns
- **Synchronous REST**: Authentication endpoints via FastAPI
- **Asynchronous Events**: NATS for authentication events
- **Service Discovery**: Consul for dynamic service location
- **Dependency Injection**: Protocol-based interfaces for testability
- **Health Checks**: `/health` endpoint for load balancer

### Dependency Injection
- **JWTManagerProtocol**: Interface for token operations
- **AccountClientProtocol**: Interface for account service calls
- **NotificationClientProtocol**: Interface for notification service
- **EventBusProtocol**: Interface for event publishing
- **Factory Pattern**: `create_auth_service()` for production instances

---

## Success Metrics

### Authentication Quality Metrics
- **Token Verification Success Rate**: % of valid tokens verified (target: >99.9%)
- **Registration Completion Rate**: % of started registrations completed (target: >80%)
- **Email Verification Rate**: % of codes verified within 10 minutes (target: >75%)
- **Token Refresh Success Rate**: % of refresh requests succeeded (target: >99.5%)

### Security Metrics
- **Invalid Token Attempts**: Rate of invalid token attempts (monitor for attacks)
- **API Key Revocation Rate**: % of API keys revoked due to compromise (target: <1%)
- **Device Authentication Failure Rate**: % of device auth failures (target: <5%)
- **Pairing Token Expiration Rate**: % of tokens expired before use (target: <30%)

### Performance Metrics
- **Token Verification Latency**: Time to verify JWT token (target: <20ms)
- **Token Generation Latency**: Time to create token pair (target: <50ms)
- **API Key Verification Latency**: Time to validate API key (target: <30ms)
- **Device Authentication Latency**: Time to authenticate device (target: <100ms)

### Availability Metrics
- **Service Uptime**: Auth Service availability (target: 99.95%)
- **Event Publishing Success**: % of events successfully published (target: >99%)
- **Notification Delivery Rate**: % of verification emails delivered (target: >95%)

### Business Metrics
- **Daily Registrations**: New users registered per day
- **Active Sessions**: Concurrent authenticated sessions
- **API Key Usage**: Active API keys per organization
- **Device Authentication Volume**: Device logins per day

---

## Glossary

**Access Token**: Short-lived JWT (1 hour) used for API authentication
**Refresh Token**: Long-lived JWT (7 days) used to obtain new access tokens
**Device Token**: 24-hour JWT for IoT device authentication
**Pairing Token**: 5-minute temporary token for device-user binding
**Token Claims**: Structured data embedded in JWT payload
**Token Provider**: Authentication system that issues tokens (isa_user, auth0)
**JWT**: JSON Web Token - cryptographically signed authentication token
**HS256**: HMAC-SHA256 symmetric signature algorithm
**RS256**: RSA-SHA256 asymmetric signature algorithm
**JWKS**: JSON Web Key Set - public keys for OAuth token verification
**API Key**: Long-lived credential for programmatic access
**Device Credential**: Authentication credential for IoT device (device_id + device_secret)
**Device Secret**: Shared secret for device authentication (hashed with SHA-256)
**Verification Code**: 6-digit numeric code for email verification
**Pending Registration**: Temporary registration record awaiting verification
**Session**: Authenticated user session with token pair
**Identity Authority**: Service responsible for generating user_id
**Idempotent**: Operation producing same result when called multiple times
**Token Scope**: Context in which token is valid (user, device, service)
**Protocol Interface**: Abstract contract for dependency injection

---

**Document Version**: 1.0
**Last Updated**: 2025-12-13
**Maintained By**: Authentication Service Team
