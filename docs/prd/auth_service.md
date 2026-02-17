# Authentication Service - Product Requirements Document (PRD)

## Document Information
- **Service Name**: auth_service
- **Version**: 2.0.0
- **Last Updated**: 2025-12-13
- **Document Type**: Layer 2 CDD - Product Requirements Document
- **Domain**: User Services

---

## Product Overview

### Purpose
The Authentication Service is a centralized authentication microservice responsible for identity verification, token management, and secure access control across the isA_user platform. It provides multi-provider JWT verification, API key management for organizations, device authentication for IoT devices, and user registration with email verification.

### Core Responsibilities
- **JWT Token Verification**: Verify tokens from multiple providers (Auth0, isa_user custom JWT)
- **Token Generation**: Generate access tokens, refresh tokens, and token pairs
- **User Registration**: Email-based registration with verification code flow
- **API Key Management**: Create, verify, and manage organization API keys
- **Device Authentication**: Register, authenticate, and manage IoT device credentials
- **Session Management**: Track user sessions and authentication activity

### Key Capabilities
1. **Multi-Provider Token Support**: Auth0 OAuth integration and custom isa_user JWT tokens
2. **Self-Issued JWT Tokens**: Primary authentication method using HS256 signed tokens
3. **Stateless Authentication**: JWT-based authentication without session storage requirements
4. **Device Pairing Flow**: QR code-based device-to-user pairing for IoT devices
5. **Event-Driven Architecture**: Publishes authentication events via NATS for audit trails

### Provider Architecture
- **Primary Provider**: `isa_user` - Custom self-issued JWT tokens with full claim control
- **Secondary Provider**: `auth0` - OAuth integration for enterprise SSO
- **Token Issuer**: Service acts as identity authority, issues user_ids during registration
- **Claims Structure**: Standardized claims including user_id, email, organization_id, permissions

---

## Target Users

### Primary User Personas

#### 1. Application Developers
**Profile**: Backend and frontend developers integrating authentication into isA_user platform services

**Needs**:
- Verify incoming JWT tokens from client requests
- Generate test tokens for local development
- Understand token claim structures
- Integrate device authentication for IoT products

**Pain Points**:
- Managing multiple authentication providers
- Testing authentication flows locally
- Understanding token expiration and refresh cycles

#### 2. End Users (Application Users)
**Profile**: Individuals registering and using isA_user platform applications

**Needs**:
- Simple email-based registration process
- Secure password-based authentication
- Email verification for account security
- Immediate access after verification

**Pain Points**:
- Complex registration processes
- Delayed email verification codes
- Lost or expired verification tokens

#### 3. Organization Administrators
**Profile**: Managers overseeing organization-level API access and integrations

**Needs**:
- Create API keys with specific permissions
- Manage and revoke compromised keys
- View API key usage and activity
- Control organization-level access

**Pain Points**:
- API key sprawl and tracking
- Security concerns with key sharing
- Lack of visibility into key usage

#### 4. IoT Device Manufacturers
**Profile**: Hardware vendors integrating isA_user authentication into devices (EmoFrame, smart displays)

**Needs**:
- Register devices with secure credentials
- Device-to-user pairing mechanism (QR codes)
- Long-lived device tokens (24 hour expiry)
- Device secret rotation capabilities

**Pain Points**:
- Complex device provisioning flows
- User pairing UX challenges
- Device credential security

#### 5. Platform Administrators
**Profile**: Operations team managing platform security and authentication infrastructure

**Needs**:
- Monitor authentication activity
- Investigate security incidents
- Revoke compromised credentials
- Audit authentication logs

**Pain Points**:
- Distributed authentication state
- Limited visibility into auth failures
- Manual credential revocation processes

---

## Epics and User Stories

### Epic 1: JWT Token Verification
**Description**: Core capability to verify and validate JWT tokens from multiple providers

**Business Value**: Enables secure API access across all microservices

**User Stories**:

#### US-1.1: Verify Custom JWT Tokens
**As a** backend developer
**I want to** verify isa_user custom JWT tokens
**So that** I can authenticate user API requests

**Acceptance Criteria**:
- Service verifies HS256-signed JWT tokens
- Extracts standard claims: user_id, email, organization_id
- Validates token signature and expiration
- Returns validation result with user claims
- Handles expired tokens gracefully

**Technical Notes**:
- Uses core/jwt_manager for token operations
- Supports issuer validation (iss=isA_user)
- Checks token expiration (exp claim)

#### US-1.2: Verify Auth0 Tokens
**As a** backend developer
**I want to** verify Auth0 JWT tokens
**So that** enterprise SSO users can access the platform

**Acceptance Criteria**:
- Service fetches Auth0 public keys from JWKS endpoint
- Verifies RS256-signed tokens
- Validates audience and issuer claims
- Returns standardized verification response
- Caches public keys for performance

**Technical Notes**:
- Uses httpx async client for JWKS fetching
- Implements kid (key ID) matching
- Supports Auth0 domain configuration

#### US-1.3: Auto-Detect Token Provider
**As a** backend developer
**I want to** verify tokens without specifying the provider
**So that** I can simplify my integration code

**Acceptance Criteria**:
- Service inspects token issuer claim
- Routes to appropriate verification method
- Defaults to isa_user for unknown issuers
- Returns provider information in response

**Technical Notes**:
- Decodes token without signature verification for issuer check
- Uses issuer string matching (auth0.com, isA_user)

#### US-1.4: Extract User Claims from Tokens
**As a** backend developer
**I want to** extract user information from verified tokens
**So that** I can enforce user-specific business logic

**Acceptance Criteria**:
- Service extracts user_id, email, organization_id
- Returns subscription level from metadata
- Provides permissions array
- Includes token expiration timestamp

**Technical Notes**:
- Standardizes claim structure across providers
- Handles optional claims gracefully

#### US-1.5: Handle Token Expiration Gracefully
**As a** system
**I need to** return clear error messages for expired tokens
**So that** clients can request token refresh

**Acceptance Criteria**:
- Returns valid=false for expired tokens
- Error message indicates "Token expired"
- Does not throw exceptions for expired tokens
- Client receives 200 status with error details

---

### Epic 2: User Registration and Identity
**Description**: Email-based user registration with verification code flow

**Business Value**: Enables self-service user onboarding with email verification

**User Stories**:

#### US-2.1: Start Email Registration
**As a** new user
**I want to** register with my email and password
**So that** I can create a platform account

**Acceptance Criteria**:
- User provides email, password, and optional name
- System validates email format
- System enforces password strength (min 8 characters)
- System generates 6-digit verification code
- System sends verification email via notification service
- Returns pending_registration_id for verification step

**Technical Notes**:
- Verification code expires in 10 minutes
- Stored in-memory (production should use Redis)
- Password not hashed until verification completes

#### US-2.2: Receive Verification Email
**As a** new user
**I want to** receive a verification code by email
**So that** I can complete my registration

**Acceptance Criteria**:
- Email sent within 10 seconds of registration
- Email contains 6-digit code
- Email explains 10-minute expiration
- Email includes branded subject and content
- Service continues if email fails (code still valid)

**Technical Notes**:
- Uses notification_service for email delivery
- Includes HTML and plain text versions
- Tagged with "registration" for tracking

#### US-2.3: Verify Registration Code
**As a** new user
**I want to** enter my verification code
**So that** I can activate my account and receive tokens

**Acceptance Criteria**:
- User provides pending_registration_id and code
- System validates code matches registration
- System checks code hasn't expired (10 min)
- System generates new user_id (usr_xxx format)
- System creates account in account_service
- System issues token pair (access + refresh)
- Returns user_id, email, and tokens immediately

**Technical Notes**:
- Auth service acts as ID authority (generates user_id)
- Calls account_service ensure endpoint
- Cleans up pending registration after verification

#### US-2.4: Prevent Duplicate Registrations
**As a** system
**I want to** detect duplicate email registrations
**So that** each email has only one account

**Acceptance Criteria**:
- Check if email exists before starting registration
- Return clear error for duplicate emails
- Suggest password reset flow for existing users
- Log duplicate registration attempts for analytics

**Technical Notes**:
- Query account_service for existing email
- Consider case-insensitive email matching

#### US-2.5: Notify Account Service on Registration
**As a** system
**I need to** create account profile on successful verification
**So that** user data is consistent across services

**Acceptance Criteria**:
- Call account_service ensure endpoint
- Pass user_id, email, name, subscription_plan
- Default to "free" subscription plan
- Handle account service failures gracefully
- Rollback registration if account creation fails

**Technical Notes**:
- Uses AccountServiceClient with service discovery
- Retry logic for transient failures
- Account service uses ensure endpoint (idempotent)

#### US-2.6: Immediate Token Issuance After Verification
**As a** new user
**I want to** receive access tokens immediately after verification
**So that** I can start using the platform without re-authentication

**Acceptance Criteria**:
- Generate token pair after successful verification
- Include user_id, email in token claims
- Set appropriate token expiration (1 hour access, 7 days refresh)
- Return tokens in verification response
- Publish user.logged_in event for session tracking

---

### Epic 3: Token Generation and Management
**Description**: Generate development tokens, token pairs, and handle token refresh

**Business Value**: Enables flexible token management for development and production use cases

**User Stories**:

#### US-3.1: Generate Development Tokens
**As a** developer
**I want to** generate test tokens with custom claims
**So that** I can test my API integration locally

**Acceptance Criteria**:
- Specify user_id, email, and custom expiration
- Include organization_id and permissions
- Add metadata like subscription_level
- Returns access token only (no refresh token)
- Token valid for specified duration (default 1 hour)

**Technical Notes**:
- No password/credential verification required
- Validates user exists in account_service (optional)
- Uses isa_user provider (HS256)

#### US-3.2: Generate Token Pairs (Access + Refresh)
**As a** user
**I want to** receive both access and refresh tokens on login
**So that** I can maintain long-lived sessions

**Acceptance Criteria**:
- Issues access token (1 hour expiry)
- Issues refresh token (7 day expiry)
- Both tokens signed with same secret
- Refresh token includes token_type=refresh claim
- Returns token_type=Bearer, expires_in metadata

**Technical Notes**:
- Uses jwt_manager.create_token_pair()
- Access token for API requests
- Refresh token for obtaining new access tokens

#### US-3.3: Refresh Access Token
**As a** user
**I want to** obtain a new access token using my refresh token
**So that** I can continue my session without re-authentication

**Acceptance Criteria**:
- Accept valid refresh token
- Verify token signature and expiration
- Extract user claims from refresh token
- Issue new access token with same claims
- Return new access token with 1 hour expiry
- Refresh token remains valid (not rotated)

**Technical Notes**:
- Uses jwt_manager.refresh_access_token()
- Validates token_type=refresh claim
- Does not rotate refresh token (stateless)

#### US-3.4: Publish Login Events for Audit
**As a** system
**I need to** publish user.logged_in events
**So that** other services can track sessions and activity

**Acceptance Criteria**:
- Publish event when token pair generated
- Include user_id, email, organization_id
- Include timestamp and provider (isa_user)
- Include permissions and metadata
- Event published to NATS subjects

**Technical Notes**:
- Uses NATSEventBus for event publishing
- Event type: user.logged_in
- Source: auth_service
- Non-blocking (doesn't fail login if event fails)

#### US-3.5: Extract User Info from Tokens
**As a** backend developer
**I want to** extract user information from a token
**So that** I can display user context without database queries

**Acceptance Criteria**:
- Accept JWT token as query parameter
- Verify token and extract claims
- Return user_id, email, organization_id
- Return permissions and provider
- Return token expiration timestamp
- Handle invalid/expired tokens gracefully

---

### Epic 4: API Key Management
**Description**: Organization-scoped API keys for server-to-server authentication

**Business Value**: Enables secure programmatic access for integrations and automation

**User Stories**:

#### US-4.1: Create API Key with Permissions
**As an** organization administrator
**I want to** create API keys with specific permissions
**So that** I can grant granular access to integrations

**Acceptance Criteria**:
- Provide organization_id, name, and permissions list
- Specify optional expiration (days)
- System generates random API key (URL-safe)
- System stores hashed key in database
- Returns plain API key only once (at creation)
- Returns key_id for management operations

**Technical Notes**:
- Stored in organizations.api_keys JSONB field
- Uses secrets.token_urlsafe(32) for generation
- Hashes key with SHA256 before storage

#### US-4.2: Verify API Keys for Authentication
**As a** developer
**I want to** verify API keys in my server-to-server requests
**So that** I can authenticate machine clients

**Acceptance Criteria**:
- Accept API key in request
- Hash key and lookup in database
- Verify key not expired
- Verify key not revoked
- Return organization_id and permissions
- Update last_used timestamp
- Return validation result with key metadata

**Technical Notes**:
- Compares SHA256 hash against stored hash
- Returns key_id for logging/auditing
- Performance: indexed lookup on hashed_key

#### US-4.3: Revoke Compromised API Keys
**As an** organization administrator
**I want to** immediately revoke API keys
**So that** I can prevent unauthorized access if keys are compromised

**Acceptance Criteria**:
- Specify key_id and organization_id
- Verify key belongs to organization
- Mark key as revoked (soft delete)
- Revoked keys fail verification immediately
- Return success confirmation
- Cannot un-revoke keys (create new instead)

**Technical Notes**:
- Sets is_active=false in database
- Keeps revoked keys for audit trail
- Revocation is immediate (no cache invalidation needed)

#### US-4.4: List All Active API Keys
**As an** organization administrator
**I want to** view all active API keys for my organization
**So that** I can audit and manage access

**Acceptance Criteria**:
- Accept organization_id
- Return all active keys (exclude revoked)
- Display key_id, name, permissions
- Show creation date and last used date
- Show expiration date if set
- Do not return plain API keys (only hashes stored)

**Technical Notes**:
- Queries organizations.api_keys JSONB array
- Filters where is_active=true
- Sorted by created_at descending

---

### Epic 5: Device Authentication
**Description**: IoT device registration, authentication, and pairing with user accounts

**Business Value**: Enables secure device-to-platform authentication for hardware products

**User Stories**:

#### US-5.1: Register IoT Device
**As an** IoT device manufacturer
**I want to** register devices with the platform
**So that** they can authenticate and access services

**Acceptance Criteria**:
- Provide device_id, organization_id, device_name
- Optionally specify device_type (display, sensor, etc)
- System generates device secret (32-byte random)
- System stores hashed secret in database
- Returns device credentials including plain secret (once)
- Supports optional expiration date for credentials

**Technical Notes**:
- Device secret: secrets.token_urlsafe(32)
- Secret hashed with SHA256 before storage
- Stored in auth.device_credentials table
- Publishes device.registered event

#### US-5.2: Authenticate Device with Credentials
**As an** IoT device
**I want to** authenticate using my device_id and secret
**So that** I can obtain access tokens for API requests

**Acceptance Criteria**:
- Provide device_id and device_secret
- System verifies secret hash matches stored hash
- System checks device not revoked
- System checks credentials not expired
- Issues device JWT token (24 hour expiry)
- Token includes device_id, organization_id, type=device
- Returns Bearer token for subsequent requests

**Technical Notes**:
- Device tokens separate from user tokens
- Token claim: type=device (distinguishes from user tokens)
- HS256 signing with JWT_SECRET
- Publishes device.authenticated event

#### US-5.3: Pair Device with User Account
**As a** device owner
**I want to** pair my device with my user account
**So that** the device can access my personal data

**Acceptance Criteria**:
- Device generates pairing token (5-minute expiry)
- Device displays QR code with pairing token
- User scans QR code with mobile app
- App calls pairing verification with user_id
- System validates pairing token not expired/used
- System links device to user in device_service
- Pairing token can only be used once

**Technical Notes**:
- Pairing token: secrets.token_urlsafe(32)
- Stored in auth.device_pairing_tokens table
- Publishes device.pairing_completed event
- Device service listens to event and creates device-user link

#### US-5.4: Revoke Device Credentials
**As an** administrator
**I want to** revoke compromised device credentials
**So that** unauthorized devices cannot access the platform

**Acceptance Criteria**:
- Specify device_id and organization_id
- Verify device belongs to organization
- Mark credentials as revoked (status=revoked)
- Device authentication fails immediately
- Existing device tokens remain valid until expiry
- Return revocation confirmation

**Technical Notes**:
- Sets status=revoked in device_credentials
- Does not invalidate existing tokens (stateless JWT)
- Consider short token expiry for quicker revocation

#### US-5.5: Refresh Device Secret
**As a** device administrator
**I want to** rotate device secrets periodically
**So that** I can maintain security best practices

**Acceptance Criteria**:
- Specify device_id and organization_id
- Verify device ownership
- Generate new device secret
- Replace old secret hash with new hash
- Return new plain secret (client must update)
- Old secret invalid immediately after refresh

**Technical Notes**:
- Generates new secrets.token_urlsafe(32)
- Updates device_secret hash in database
- Clients must securely store new secret

#### US-5.6: List Organization Devices
**As an** organization administrator
**I want to** view all registered devices
**So that** I can manage device fleet

**Acceptance Criteria**:
- Accept organization_id
- Return all devices for organization
- Show device_id, name, type, status
- Show registration date and last authentication
- Filter by status (active/revoked)
- Do not return device secrets

---

### Epic 6: Session Management
**Description**: Track active user sessions and authentication activity

**Business Value**: Enables security monitoring and user session control

**User Stories**:

#### US-6.1: Track Active User Sessions
**As a** system
**I want to** track when users generate tokens
**So that** I can monitor active sessions

**Acceptance Criteria**:
- Create session record on token pair generation
- Store session_id, user_id, access_token (hashed)
- Store refresh_token (hashed) for validation
- Store session expiration based on refresh token
- Store creation timestamp and last activity
- Publish session.created event

**Technical Notes**:
- Stored in auth.user_sessions table
- Session_id: uuid4 format
- Tokens hashed before storage for security

#### US-6.2: Invalidate Session on Logout
**As a** user
**I want to** explicitly logout and invalidate my session
**So that** my tokens cannot be used after logout

**Acceptance Criteria**:
- Accept session_id or refresh_token
- Mark session as inactive (is_active=false)
- Set invalidated_at timestamp
- Publish session.invalidated event
- Return logout confirmation

**Technical Notes**:
- Note: JWT tokens remain valid until expiry (stateless)
- Services can check session status via auth_service
- Consider token blacklist for immediate invalidation

#### US-6.3: Track Session Activity
**As a** system
**I need to** update session last_activity timestamp
**So that** I can detect stale sessions

**Acceptance Criteria**:
- Update last_activity on token verification
- Update last_activity on token refresh
- Store activity timestamp in UTC
- Enable session timeout policies (future)

**Technical Notes**:
- Async update (doesn't block verification)
- Used for idle session detection

#### US-6.4: View Authentication Logs
**As an** administrator
**I want to** view authentication logs for a user
**So that** I can investigate security incidents

**Acceptance Criteria**:
- Accept user_id or device_id
- Return authentication attempts (success/failure)
- Show timestamps, IP addresses, user agents
- Show token types and providers
- Filter by date range
- Paginate results (limit 100 per page)

**Technical Notes**:
- Queries auth.user_sessions and auth.device_auth_logs
- Joins with audit events from audit_service
- Consider log retention policies

---

## API Surface Documentation

### Base URL
```
/api/v1/auth
```

### Authentication
Most endpoints are public (for verification purposes). Protected endpoints require JWT token in Authorization header:
```
Authorization: Bearer <token>
```

---

### Token Operations

#### 1. Verify JWT Token
**Endpoint**: `POST /api/v1/auth/verify-token`

**Description**: Verify JWT token from any supported provider

**Request Body**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "provider": "isa_user"  // Optional: "auth0", "isa_user", "local"
}
```

**Response 200**:
```json
{
  "valid": true,
  "provider": "isa_user",
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "subscription_level": "pro",
  "organization_id": "org_xyz789",
  "expires_at": "2025-12-13T15:30:00Z",
  "error": null
}
```

**Response 200 (Invalid)**:
```json
{
  "valid": false,
  "error": "Token expired"
}
```

**Error Cases**:
- Invalid token format
- Expired token
- Invalid signature
- Provider not supported

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/verify-token \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJ...", "provider": "isa_user"}'
```

---

#### 2. Generate Development Token
**Endpoint**: `POST /api/v1/auth/dev-token`

**Description**: Generate test token for development (access token only)

**Request Body**:
```json
{
  "user_id": "usr_test123",
  "email": "dev@example.com",
  "expires_in": 3600,  // seconds, max 86400 (24h)
  "subscription_level": "pro",
  "organization_id": "org_test456",
  "permissions": ["read:albums", "write:photos"],
  "metadata": {
    "environment": "development"
  }
}
```

**Response 200**:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "user_id": "usr_test123",
  "email": "dev@example.com",
  "provider": "isa_user"
}
```

**Error Cases**:
- Invalid user_id format
- expires_in out of range (1-86400)
- Invalid email format

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/dev-token \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_test",
    "email": "dev@example.com",
    "expires_in": 7200
  }'
```

---

#### 3. Generate Token Pair
**Endpoint**: `POST /api/v1/auth/token-pair`

**Description**: Generate access and refresh token pair (login flow)

**Request Body**:
```json
{
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "organization_id": "org_xyz789",
  "permissions": ["read:albums", "write:photos"],
  "metadata": {
    "login_method": "email_password"
  }
}
```

**Response 200**:
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,  // access token expiry
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "provider": "isa_user"
}
```

**Error Cases**:
- Invalid user_id
- User not found in account_service (warning only)
- JWT manager not available

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/token-pair \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_abc123",
    "email": "user@example.com"
  }'
```

---

#### 4. Refresh Access Token
**Endpoint**: `POST /api/v1/auth/refresh`

**Description**: Get new access token using refresh token

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 200**:
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "provider": "isa_user"
}
```

**Response 401**:
```json
{
  "detail": "Invalid or expired refresh token"
}
```

**Error Cases**:
- Refresh token expired
- Refresh token invalid signature
- Refresh token not of type=refresh

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ..."
  }'
```

---

#### 5. Get User Info from Token
**Endpoint**: `GET /api/v1/auth/user-info`

**Description**: Extract user information from token

**Query Parameters**:
- `token` (required): JWT token to extract info from

**Response 200**:
```json
{
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "provider": "isa_user",
  "expires_at": "2025-12-13T15:30:00Z"
}
```

**Response 401**:
```json
{
  "detail": "Invalid token"
}
```

**Error Cases**:
- Token expired
- Token invalid
- Missing token parameter

**Example**:
```bash
curl -X GET "http://localhost:8003/api/v1/auth/user-info?token=eyJ..."
```

---

### Registration Endpoints

#### 6. Start Registration
**Endpoint**: `POST /api/v1/auth/register`

**Description**: Begin user registration with email verification

**Request Body**:
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "name": "Alice Smith"  // Optional
}
```

**Response 200**:
```json
{
  "pending_registration_id": "a1b2c3d4e5f6",
  "verification_required": true,
  "expires_at": "2025-12-13T14:40:00Z"  // 10 minutes
}
```

**Response 400**:
```json
{
  "detail": "Email already registered"
}
```

**Error Cases**:
- Invalid email format
- Password too short (< 8 characters)
- Email already exists
- Email service unavailable (warning, continues)

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "name": "Alice"
  }'
```

---

#### 7. Verify Registration
**Endpoint**: `POST /api/v1/auth/verify`

**Description**: Complete registration with verification code

**Request Body**:
```json
{
  "pending_registration_id": "a1b2c3d4e5f6",
  "code": "123456"
}
```

**Response 200**:
```json
{
  "success": true,
  "user_id": "usr_newuser789",
  "email": "newuser@example.com",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "error": null
}
```

**Response 200 (Failure)**:
```json
{
  "success": false,
  "error": "Invalid verification code"
}
```

**Error Cases**:
- Invalid pending_registration_id
- Verification code expired (>10 minutes)
- Incorrect verification code
- Account creation failed

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "pending_registration_id": "a1b2c3d4e5f6",
    "code": "123456"
  }'
```

---

### API Key Management Endpoints

#### 8. Create API Key
**Endpoint**: `POST /api/v1/auth/api-keys`

**Description**: Create organization API key

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "organization_id": "org_xyz789",
  "name": "Production Integration",
  "permissions": ["read:albums", "write:photos", "read:devices"],
  "expires_days": 365  // Optional, null = no expiration
}
```

**Response 200**:
```json
{
  "success": true,
  "api_key": "isa_live_1234567890abcdef...",  // Only shown once!
  "key_id": "key_abc123",
  "name": "Production Integration",
  "expires_at": "2026-12-13T14:30:00Z"
}
```

**Error Cases**:
- Organization not found
- Unauthorized (not org admin)
- Invalid permissions
- API key creation failed

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "organization_id": "org_xyz789",
    "name": "Production Integration",
    "permissions": ["read:albums"]
  }'
```

---

#### 9. Verify API Key
**Endpoint**: `POST /api/v1/auth/verify-api-key`

**Description**: Verify API key validity

**Request Body**:
```json
{
  "api_key": "isa_live_1234567890abcdef..."
}
```

**Response 200**:
```json
{
  "valid": true,
  "key_id": "key_abc123",
  "organization_id": "org_xyz789",
  "name": "Production Integration",
  "permissions": ["read:albums", "write:photos"],
  "error": null
}
```

**Response 200 (Invalid)**:
```json
{
  "valid": false,
  "error": "Invalid or expired API key"
}
```

**Error Cases**:
- API key not found
- API key revoked
- API key expired
- Invalid key format

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/verify-api-key \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "isa_live_1234567890abcdef..."
  }'
```

---

#### 10. List API Keys
**Endpoint**: `GET /api/v1/auth/api-keys/{organization_id}`

**Description**: List all active API keys for organization

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `organization_id`: Organization ID

**Response 200**:
```json
{
  "success": true,
  "api_keys": [
    {
      "key_id": "key_abc123",
      "name": "Production Integration",
      "permissions": ["read:albums", "write:photos"],
      "created_at": "2025-01-01T00:00:00Z",
      "expires_at": "2026-01-01T00:00:00Z",
      "last_used": "2025-12-13T10:00:00Z"
    }
  ],
  "total": 1
}
```

**Error Cases**:
- Organization not found
- Unauthorized access

**Example**:
```bash
curl -X GET http://localhost:8003/api/v1/auth/api-keys/org_xyz789 \
  -H "Authorization: Bearer eyJ..."
```

---

#### 11. Revoke API Key
**Endpoint**: `DELETE /api/v1/auth/api-keys/{key_id}`

**Description**: Revoke API key

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `key_id`: API key ID

**Query Parameters**:
- `organization_id` (required): Organization ID for authorization

**Response 200**:
```json
{
  "success": true,
  "message": "API key revoked"
}
```

**Error Cases**:
- Key not found
- Unauthorized (wrong organization)
- Already revoked

**Example**:
```bash
curl -X DELETE "http://localhost:8003/api/v1/auth/api-keys/key_abc123?organization_id=org_xyz789" \
  -H "Authorization: Bearer eyJ..."
```

---

### Device Authentication Endpoints

#### 12. Register Device
**Endpoint**: `POST /api/v1/auth/device/register`

**Description**: Register IoT device and receive credentials

**Authentication**: Required (Bearer token with org permissions)

**Request Body**:
```json
{
  "device_id": "emoframe_001",
  "organization_id": "org_xyz789",
  "device_name": "Living Room Display",
  "device_type": "display",
  "metadata": {
    "model": "EmoFrame Gen2",
    "firmware": "v2.1.0"
  },
  "expires_days": 365  // Optional
}
```

**Response 200**:
```json
{
  "success": true,
  "device_id": "emoframe_001",
  "device_secret": "abc123...xyz789",  // Only shown once!
  "organization_id": "org_xyz789",
  "device_name": "Living Room Display",
  "device_type": "display",
  "status": "active",
  "created_at": "2025-12-13T14:30:00Z"
}
```

**Error Cases**:
- Device ID already exists
- Organization not found
- Unauthorized

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/device/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "device_id": "emoframe_001",
    "organization_id": "org_xyz789",
    "device_name": "Living Room Display",
    "device_type": "display"
  }'
```

---

#### 13. Authenticate Device
**Endpoint**: `POST /api/v1/auth/device/authenticate`

**Description**: Device authentication to receive access token

**Request Body**:
```json
{
  "device_id": "emoframe_001",
  "device_secret": "abc123...xyz789"
}
```

**Response 200**:
```json
{
  "success": true,
  "authenticated": true,
  "device_id": "emoframe_001",
  "organization_id": "org_xyz789",
  "device_name": "Living Room Display",
  "device_type": "display",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400  // 24 hours
}
```

**Response 401**:
```json
{
  "detail": "Invalid device credentials"
}
```

**Error Cases**:
- Device not found
- Invalid secret
- Device revoked
- Credentials expired

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/device/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "emoframe_001",
    "device_secret": "abc123...xyz789"
  }'
```

---

#### 14. Verify Device Token
**Endpoint**: `POST /api/v1/auth/device/verify-token`

**Description**: Verify device JWT token

**Request Body**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 200**:
```json
{
  "valid": true,
  "device_id": "emoframe_001",
  "organization_id": "org_xyz789",
  "device_type": "display",
  "expires_at": "2025-12-14T14:30:00Z"
}
```

**Response 200 (Invalid)**:
```json
{
  "valid": false,
  "error": "Token has expired"
}
```

**Error Cases**:
- Token expired
- Invalid signature
- Device not found
- Wrong token type (not device token)

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/device/verify-token \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJ..."
  }'
```

---

#### 15. Refresh Device Secret
**Endpoint**: `POST /api/v1/auth/device/{device_id}/refresh-secret`

**Description**: Rotate device secret

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `device_id`: Device ID

**Query Parameters**:
- `organization_id` (required): Organization ID

**Response 200**:
```json
{
  "success": true,
  "device_id": "emoframe_001",
  "device_secret": "newSecret123...xyz",  // New secret
  "message": "Device secret refreshed successfully"
}
```

**Error Cases**:
- Device not found
- Unauthorized (wrong organization)

**Example**:
```bash
curl -X POST "http://localhost:8003/api/v1/auth/device/emoframe_001/refresh-secret?organization_id=org_xyz789" \
  -H "Authorization: Bearer eyJ..."
```

---

#### 16. Revoke Device
**Endpoint**: `DELETE /api/v1/auth/device/{device_id}`

**Description**: Revoke device credentials

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `device_id`: Device ID

**Query Parameters**:
- `organization_id` (required): Organization ID

**Response 200**:
```json
{
  "success": true,
  "message": "Device emoframe_001 has been revoked"
}
```

**Error Cases**:
- Device not found
- Unauthorized

**Example**:
```bash
curl -X DELETE "http://localhost:8003/api/v1/auth/device/emoframe_001?organization_id=org_xyz789" \
  -H "Authorization: Bearer eyJ..."
```

---

#### 17. List Organization Devices
**Endpoint**: `GET /api/v1/auth/device/list`

**Description**: List all devices for organization

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `organization_id` (required): Organization ID

**Response 200**:
```json
{
  "success": true,
  "devices": [
    {
      "device_id": "emoframe_001",
      "device_name": "Living Room Display",
      "device_type": "display",
      "status": "active",
      "organization_id": "org_xyz789",
      "created_at": "2025-12-01T00:00:00Z",
      "last_authenticated": "2025-12-13T10:00:00Z"
    }
  ],
  "count": 1
}
```

**Error Cases**:
- Organization not found
- Unauthorized

**Example**:
```bash
curl -X GET "http://localhost:8003/api/v1/auth/device/list?organization_id=org_xyz789" \
  -H "Authorization: Bearer eyJ..."
```

---

#### 18. Generate Device Pairing Token
**Endpoint**: `POST /api/v1/auth/device/{device_id}/pairing-token`

**Description**: Generate temporary pairing token for device-user pairing (QR code flow)

**Path Parameters**:
- `device_id`: Device ID

**Response 200**:
```json
{
  "success": true,
  "pairing_token": "pairing_abc123xyz789...",
  "expires_at": "2025-12-13T14:35:00Z",  // 5 minutes
  "expires_in": 300
}
```

**Error Cases**:
- Device not found
- Token generation failed

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/device/emoframe_001/pairing-token
```

---

#### 19. Verify Device Pairing Token
**Endpoint**: `POST /api/v1/auth/device/pairing-token/verify`

**Description**: Verify pairing token and link device to user

**Request Body**:
```json
{
  "device_id": "emoframe_001",
  "pairing_token": "pairing_abc123xyz789...",
  "user_id": "usr_alice123"
}
```

**Response 200**:
```json
{
  "valid": true,
  "device_id": "emoframe_001",
  "user_id": "usr_alice123"
}
```

**Response 200 (Invalid)**:
```json
{
  "valid": false,
  "error": "Token has expired"
}
```

**Error Cases**:
- Token not found
- Token expired (>5 minutes)
- Token already used
- Device ID mismatch

**Example**:
```bash
curl -X POST http://localhost:8003/api/v1/auth/device/pairing-token/verify \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "emoframe_001",
    "pairing_token": "pairing_abc123xyz789...",
    "user_id": "usr_alice123"
  }'
```

---

### Health & Info Endpoints

#### 20. Root Health Check
**Endpoint**: `GET /`

**Description**: Basic service health check

**Response 200**:
```json
{
  "service": "auth_microservice",
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-12-13T14:30:00Z"
}
```

---

#### 21. Health Check
**Endpoint**: `GET /health`

**Description**: Detailed service health information

**Response 200**:
```json
{
  "status": "healthy",
  "service": "auth_microservice",
  "port": 8003,
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

---

#### 22. Service Info
**Endpoint**: `GET /api/v1/auth/info`

**Description**: Authentication service information and capabilities

**Response 200**:
```json
{
  "service": "auth_microservice",
  "version": "2.0.0",
  "description": "Pure authentication microservice with custom JWT",
  "capabilities": {
    "jwt_verification": ["auth0", "isa_user"],
    "api_key_management": true,
    "token_generation": true,
    "device_authentication": true
  },
  "endpoints": {
    "verify_token": "/api/v1/auth/verify-token",
    "verify_api_key": "/api/v1/auth/verify-api-key",
    "generate_dev_token": "/api/v1/auth/dev-token",
    "manage_api_keys": "/api/v1/auth/api-keys"
  }
}
```

---

#### 23. Service Statistics
**Endpoint**: `GET /api/v1/auth/stats`

**Description**: Service statistics and operational metrics

**Response 200**:
```json
{
  "service": "auth_microservice",
  "version": "2.0.0",
  "status": "operational",
  "capabilities": {
    "jwt_providers": ["auth0", "isa_user"],
    "api_key_management": true,
    "token_generation": true,
    "device_authentication": true
  },
  "stats": {
    "uptime": "running",
    "endpoints_count": 8
  }
}
```

---

#### 24. Get Pending Registration (Development Only)
**Endpoint**: `GET /api/v1/auth/dev/pending-registration/{pending_id}`

**Description**: Development endpoint to retrieve verification code

**Path Parameters**:
- `pending_id`: Pending registration ID

**Response 200**:
```json
{
  "found": true,
  "expired": false,
  "email": "newuser@example.com",
  "verification_code": "123456",
  "expires_at": "2025-12-13T14:40:00Z",
  "verified": false
}
```

**Notes**:
- Only available when `debug=true` in config
- Returns 403 Forbidden in production
- Used for automated testing

---

## Functional Requirements

### Authentication and Identity (FR-001 to FR-007)

**FR-001: Multi-Provider Token Verification**
- System MUST support JWT token verification from Auth0 and isa_user providers
- System MUST auto-detect provider from token issuer claim if not specified
- System MUST verify token signature using provider-specific keys (RS256 for Auth0, HS256 for isa_user)
- System MUST validate token expiration (exp claim)
- System MUST return standardized verification response across all providers

**FR-002: Custom JWT Token Generation**
- System MUST generate HS256-signed JWT tokens as primary authentication method
- System MUST include standard claims: iss, sub, iat, exp, email, user_id
- System MUST support custom claims: organization_id, permissions, metadata
- System MUST use configurable JWT secret from environment
- System MUST set default issuer as "isA_user"

**FR-003: Token Expiration Management**
- System MUST issue access tokens with 1 hour expiration
- System MUST issue refresh tokens with 7 day expiration
- System MUST issue device tokens with 24 hour expiration
- System MUST issue pairing tokens with 5 minute expiration
- System MUST validate expiration on every token verification

**FR-004: Email-Based Registration**
- System MUST accept email, password, and optional name for registration
- System MUST validate email format using standard email regex
- System MUST enforce minimum password length (8 characters)
- System MUST generate 6-digit random verification code
- System MUST send verification code via notification_service
- System MUST store pending registration with 10-minute TTL

**FR-005: Registration Verification and Account Creation**
- System MUST verify registration code matches pending registration
- System MUST check code not expired (10 minutes from generation)
- System MUST generate unique user_id in format usr_{uuid}
- System MUST call account_service ensure endpoint to create account
- System MUST issue token pair immediately after successful verification
- System MUST cleanup pending registration after verification

**FR-006: Identity Authority**
- System MUST act as authoritative source for user_id generation
- System MUST ensure user_id uniqueness across platform
- System MUST use UUID-based user_id format (usr_{hex})
- System MUST validate user_id format in all operations

**FR-007: Session Tracking**
- System MUST create session record on token pair generation
- System MUST store session_id, user_id, token hashes, expiration
- System MUST update last_activity timestamp on token operations
- System MUST support session invalidation (logout)

### API Key Management (FR-008 to FR-011)

**FR-008: API Key Generation**
- System MUST generate cryptographically random API keys (32 bytes, URL-safe)
- System MUST hash API keys with SHA256 before storage
- System MUST store keys in organizations.api_keys JSONB field
- System MUST support optional expiration date
- System MUST return plain key only once at creation time

**FR-009: API Key Verification**
- System MUST hash provided key and compare with stored hash
- System MUST validate key not expired
- System MUST validate key not revoked (is_active=true)
- System MUST return organization_id and permissions on valid key
- System MUST update last_used timestamp on successful verification

**FR-010: API Key Revocation**
- System MUST support immediate API key revocation
- System MUST verify organization ownership before revocation
- System MUST set is_active=false (soft delete)
- System MUST retain revoked keys for audit trail
- System MUST prevent further verification of revoked keys

**FR-011: API Key Listing**
- System MUST return all active keys for organization
- System MUST filter out revoked keys
- System MUST include key_id, name, permissions, dates
- System MUST NOT return plain API keys (only stored hashes)

### Device Authentication (FR-012 to FR-017)

**FR-012: Device Registration**
- System MUST generate cryptographically random device secret (32 bytes)
- System MUST hash device secret with SHA256 before storage
- System MUST support device_id, organization_id, name, type, metadata
- System MUST support optional credential expiration
- System MUST return plain secret only once at registration
- System MUST publish device.registered event

**FR-013: Device Authentication**
- System MUST verify device_id and secret hash match
- System MUST validate device not revoked
- System MUST validate credentials not expired
- System MUST generate device JWT with type=device claim
- System MUST set device token expiration to 24 hours
- System MUST publish device.authenticated event

**FR-014: Device Token Verification**
- System MUST verify device token signature
- System MUST validate type=device claim present
- System MUST check device still exists and active
- System MUST return device_id, organization_id, device_type

**FR-015: Device Secret Rotation**
- System MUST generate new random secret on refresh request
- System MUST verify organization ownership before refresh
- System MUST replace old secret hash immediately
- System MUST return new plain secret to client

**FR-016: Device Revocation**
- System MUST support immediate device credential revocation
- System MUST set status=revoked in database
- System MUST prevent device authentication after revocation
- System MUST retain revoked devices for audit

**FR-017: Device Pairing Flow**
- System MUST generate random pairing token (32 bytes, URL-safe)
- System MUST set pairing token expiration to 5 minutes
- System MUST support single-use pairing tokens
- System MUST verify device_id matches pairing token
- System MUST mark token as used after successful verification
- System MUST publish device.pairing_completed event

### Event Publishing (FR-018 to FR-020)

**FR-018: User Login Events**
- System MUST publish user.logged_in event on token pair generation
- Event MUST include user_id, email, organization_id, timestamp
- Event MUST include provider and metadata
- Publishing MUST NOT block login flow (fire-and-forget)

**FR-019: Device Events**
- System MUST publish device.registered on device registration
- System MUST publish device.authenticated on device authentication
- System MUST publish device.pairing_completed on successful pairing
- Events MUST include device_id, organization_id, timestamp

**FR-020: Event Bus Integration**
- System MUST use NATS event bus for event publishing
- System MUST handle event bus unavailability gracefully
- System MUST log event publishing failures
- System MUST continue operation if event publishing fails

---

## Non-Functional Requirements

### Performance (NFR-001 to NFR-004)

**NFR-001: Token Verification Latency**
- Token verification MUST complete in under 100ms (p95)
- JWT signature verification MUST use optimized crypto libraries
- Auth0 public key fetching MUST be cached
- Token parsing MUST handle malformed tokens without exceptions

**NFR-002: Throughput**
- Service MUST support 1000 token verifications per second
- Service MUST handle 100 token generations per second
- Service MUST handle 50 device authentications per second
- Service MUST support horizontal scaling for increased load

**NFR-003: Database Performance**
- API key verification MUST complete in under 50ms
- Device credential lookup MUST complete in under 50ms
- Session queries MUST use indexed lookups
- Pending registrations SHOULD use in-memory storage (Redis)

**NFR-004: Event Publishing Performance**
- Event publishing MUST NOT block authentication operations
- Events MUST be published asynchronously
- Event publishing failures MUST be logged but not retried

### Security (NFR-005 to NFR-009)

**NFR-005: Token Expiration**
- Access tokens MUST expire in 1 hour (3600 seconds)
- Refresh tokens MUST expire in 7 days (604800 seconds)
- Device tokens MUST expire in 24 hours (86400 seconds)
- Pairing tokens MUST expire in 5 minutes (300 seconds)
- Verification codes MUST expire in 10 minutes (600 seconds)

**NFR-006: Credential Hashing**
- API key hashes MUST use SHA256
- Device secret hashes MUST use SHA256
- Password hashing SHOULD use bcrypt or Argon2 (future)
- Hashing MUST occur before database storage

**NFR-007: Token Security**
- JWT tokens MUST be signed with HMAC-SHA256 (HS256)
- JWT secret MUST be loaded from environment variable
- JWT secret MUST be minimum 32 bytes
- Token signatures MUST be verified on every request

**NFR-008: Credential Generation**
- API keys MUST use secrets.token_urlsafe(32)
- Device secrets MUST use secrets.token_urlsafe(32)
- Pairing tokens MUST use secrets.token_urlsafe(32)
- Verification codes MUST use random 6-digit numbers
- All random generation MUST use cryptographically secure RNG

**NFR-009: Access Control**
- API key operations MUST verify organization ownership
- Device operations MUST verify organization ownership
- Session operations MUST verify user ownership
- Protected endpoints MUST require valid JWT token

### Availability (NFR-010 to NFR-012)

**NFR-010: Service Availability**
- Service MUST maintain 99.9% uptime (8.76 hours downtime/year)
- Service MUST support rolling deployments with zero downtime
- Service MUST handle database connection failures gracefully
- Service MUST implement health check endpoints

**NFR-011: Dependency Resilience**
- Service MUST operate if notification_service unavailable (registration continues)
- Service MUST operate if account_service unavailable (warns, continues)
- Service MUST operate if event_bus unavailable (logs, continues)
- Service MUST cache Auth0 public keys (1 hour TTL)

**NFR-012: Service Discovery**
- Service MUST register with Consul on startup
- Service MUST deregister from Consul on shutdown
- Service MUST publish route metadata to Consul
- Service MUST support dynamic service discovery for clients

### Observability (NFR-013 to NFR-015)

**NFR-013: Logging**
- Service MUST log all authentication attempts (success/failure)
- Service MUST log API key and device credential operations
- Service MUST log event publishing failures
- Logs MUST include correlation IDs for request tracing
- Logs MUST NOT include sensitive data (secrets, passwords, tokens)

**NFR-014: Metrics**
- Service MUST track token verification count and latency
- Service MUST track token generation count
- Service MUST track authentication failure count
- Service MUST track API key and device operation counts

**NFR-015: Health Checks**
- Service MUST provide /health endpoint
- Service MUST provide / root health check
- Health checks MUST return response in under 1 second
- Health checks MUST validate critical dependencies

### Scalability (NFR-016)

**NFR-016: Horizontal Scaling**
- Service MUST be stateless (except in-memory pending registrations)
- Service MUST support multiple replicas behind load balancer
- Service MUST share JWT secret across replicas
- Pending registrations SHOULD use external cache (Redis) for multi-replica support

---

## Success Metrics

### Performance Metrics

**Token Verification Latency**
- **Target**: p50 < 20ms, p95 < 100ms, p99 < 200ms
- **Measurement**: Application performance monitoring (APM)
- **Baseline**: Current p95 latency
- **Goal**: Maintain under 100ms as traffic scales

**Authentication Throughput**
- **Target**: 1000 verifications/sec per replica
- **Measurement**: Request rate metrics
- **Goal**: Linear scaling with replica count

### Reliability Metrics

**Service Availability**
- **Target**: 99.9% uptime (< 8.76 hours downtime/year)
- **Measurement**: Health check monitoring, incident tracking
- **Baseline**: Current uptime SLA
- **Goal**: Maintain 99.9% or improve to 99.95%

**Authentication Success Rate**
- **Target**: > 99.5% successful authentications (excluding invalid credentials)
- **Measurement**: Success vs error ratio
- **Goal**: < 0.5% authentication errors due to service issues

### User Experience Metrics

**Registration Completion Rate**
- **Target**: > 80% of started registrations complete verification
- **Measurement**: (verified / started) * 100
- **Baseline**: Establish baseline in first month
- **Goal**: Improve completion rate over time
- **Factors**: Email delivery time, code expiration, UX clarity

**Email Verification Time**
- **Target**: p95 < 60 seconds from registration to code receipt
- **Measurement**: notification_service delivery metrics
- **Goal**: Minimize user waiting time

**Device Pairing Success Rate**
- **Target**: > 95% successful pairings
- **Measurement**: (successful pairings / pairing attempts) * 100
- **Factors**: Token expiration (5 min), QR code UX, network issues

### Security Metrics

**API Key Usage**
- **Metric**: Number of active API keys per organization
- **Target**: Track growth and distribution
- **Alerts**: Unusual spike in API key creation
- **Goal**: Understand organization integration patterns

**API Key Revocation Rate**
- **Metric**: Percentage of API keys revoked within 30 days
- **Target**: < 5% (indicates good key management practices)
- **High rate**: May indicate security issues or poor key hygiene

**Device Authentication Frequency**
- **Metric**: Device authentications per day
- **Target**: Baseline device activity patterns
- **Alerts**: Unusual authentication patterns (potential compromise)

**Session Duration**
- **Metric**: Average session length (time between token pair generation and last refresh)
- **Target**: Baseline 1-7 days (limited by refresh token expiry)
- **Goal**: Understand user session behavior

**Authentication Error Rate**
- **Metric**: Failed authentications / total attempts
- **Target**: < 1% (excluding legitimate invalid credentials)
- **Categories**: Expired tokens, invalid signatures, revoked credentials
- **Goal**: Identify security incidents or integration issues

### Business Metrics

**New User Registration Rate**
- **Metric**: Successful registrations per day/week/month
- **Target**: Track growth trends
- **Goal**: Understand user acquisition

**API Key Adoption**
- **Metric**: Percentage of organizations with active API keys
- **Target**: Track enterprise integration adoption
- **Goal**: > 20% of organizations using API keys within 6 months

**Device Integration Count**
- **Metric**: Number of registered devices
- **Target**: Track IoT device adoption
- **Goal**: Grow device ecosystem

**Multi-Provider Usage**
- **Metric**: Auth0 vs isa_user token verification ratio
- **Target**: Understand provider preference
- **Goal**: Optimize provider support based on usage

---

## Dependencies and Integration Points

### Internal Service Dependencies

**account_service**
- **Purpose**: Create and manage user account profiles
- **Integration**: HTTP client (AccountServiceClient)
- **Endpoints Used**:
  - POST /api/v1/accounts/ensure (create account on registration)
  - GET /api/v1/accounts/{user_id}/profile (validate user exists)
- **Failure Mode**: Registration continues with warning, tokens still issued

**notification_service**
- **Purpose**: Send verification emails
- **Integration**: HTTP client (NotificationServiceClient)
- **Endpoints Used**:
  - POST /api/v1/notifications/send (email verification codes)
- **Failure Mode**: Registration continues, code still valid for manual verification

**organization_service**
- **Purpose**: Validate organization existence for API keys and devices
- **Integration**: HTTP client (OrganizationServiceClient)
- **Endpoints Used**:
  - GET /api/v1/organizations/{org_id} (validate organization)
- **Failure Mode**: Operations fail if organization invalid

**device_service**
- **Purpose**: Receive device pairing events, manage device-user links
- **Integration**: NATS event bus
- **Events Published**:
  - device.registered
  - device.authenticated
  - device.pairing_completed
- **Failure Mode**: Event publishing failures logged, operations continue

### External Service Dependencies

**Auth0**
- **Purpose**: OAuth provider for enterprise SSO
- **Integration**: HTTPS (Auth0 JWKS endpoint)
- **Endpoints Used**:
  - GET https://{domain}/.well-known/jwks.json (fetch public keys)
- **Failure Mode**: Auth0 token verification fails, isa_user tokens unaffected

**NATS (Event Bus)**
- **Purpose**: Event-driven architecture messaging
- **Integration**: NATS client library
- **Subjects Published**:
  - auth.user.logged_in
  - auth.device.registered
  - auth.device.authenticated
  - auth.device.pairing_completed
- **Failure Mode**: Event publishing fails, logged, operations continue

**Consul**
- **Purpose**: Service registration and discovery
- **Integration**: Consul HTTP API
- **Operations**:
  - Register service on startup with health check
  - Deregister on shutdown
  - Publish route metadata
- **Failure Mode**: Registration fails, logged, service continues (manual discovery fallback)

### Database Dependencies

**PostgreSQL (auth schema)**
- **Tables**:
  - auth.users (minimal user identity)
  - auth.user_sessions (session tracking)
  - auth.device_credentials (device secrets)
  - auth.device_pairing_tokens (pairing flow)
  - auth.device_auth_logs (audit trail)
- **Failure Mode**: Service cannot operate without database

**PostgreSQL (organizations schema)**
- **Tables**:
  - organizations.organizations (organization lookup)
  - organizations.api_keys (stored in JSONB field)
- **Failure Mode**: API key and device operations fail

### Configuration Dependencies

**Environment Variables**
- JWT_SECRET (required): Secret for HS256 token signing
- AUTH0_DOMAIN (optional): Auth0 tenant domain
- AUTH0_AUDIENCE (optional): Auth0 API audience
- CONSUL_HOST (optional): Consul server address
- CONSUL_PORT (optional): Consul server port
- NATS_URL (optional): NATS server URL

**ConfigManager**
- service_host, service_port
- consul_enabled
- debug (enables dev endpoints)
- local_jwt_secret, jwt_expiration

---

## Future Enhancements

### Phase 2: Advanced Security

**Password Authentication**
- Implement password hashing (bcrypt/Argon2)
- Add password reset flow
- Support password strength requirements
- Implement account lockout after failed attempts

**MFA (Multi-Factor Authentication)**
- TOTP (Time-based One-Time Password) support
- SMS verification as second factor
- Backup codes for account recovery

**OAuth2 Provider**
- Implement full OAuth2 server
- Support authorization code grant
- Support client credentials grant
- Third-party app integration

### Phase 3: Session Management

**Active Session Management**
- List all active sessions for user
- Revoke specific sessions
- Revoke all sessions (force logout)
- Session device fingerprinting

**Token Blacklist**
- Implement token revocation before expiry
- Use Redis for blacklist cache
- Support immediate logout (current: tokens valid until expiry)

### Phase 4: Enterprise Features

**SAML Support**
- SAML 2.0 authentication provider
- Enterprise SSO integration
- Identity provider metadata management

**LDAP/Active Directory**
- LDAP authentication integration
- AD group mapping to permissions
- User provisioning from directory

**Audit Logging**
- Comprehensive authentication audit trail
- Compliance reporting (SOC2, HIPAA)
- Log export and archival

### Phase 5: Developer Experience

**Token Introspection**
- RFC 7662 token introspection endpoint
- Real-time token status checking
- Token metadata retrieval

**Webhook Support**
- Webhook notifications for authentication events
- Configurable webhook endpoints
- Retry logic and delivery guarantees

**SDK Support**
- Python SDK for auth integration
- JavaScript/TypeScript SDK
- Mobile SDK (iOS, Android)

---

## Appendix

### Token Claim Structure

**isa_user Access Token**:
```json
{
  "iss": "isA_user",
  "sub": "usr_abc123",
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "organization_id": "org_xyz789",
  "scope": "user",
  "token_type": "access",
  "permissions": ["read:albums", "write:photos"],
  "metadata": {
    "subscription_level": "pro"
  },
  "iat": 1702468800,
  "exp": 1702472400,
  "jti": "token_unique_id"
}
```

**isa_user Refresh Token**:
```json
{
  "iss": "isA_user",
  "sub": "usr_abc123",
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "token_type": "refresh",
  "iat": 1702468800,
  "exp": 1703073600,
  "jti": "refresh_unique_id"
}
```

**Device Token**:
```json
{
  "device_id": "emoframe_001",
  "organization_id": "org_xyz789",
  "device_type": "display",
  "type": "device",
  "iat": 1702468800,
  "exp": 1702555200
}
```

### Error Response Format

All error responses follow this structure:
```json
{
  "detail": "Error message description",
  "error_code": "OPTIONAL_ERROR_CODE",
  "timestamp": "2025-12-13T14:30:00Z"
}
```

### Event Payload Structures

**user.logged_in**:
```json
{
  "event_type": "user.logged_in",
  "source": "auth_service",
  "data": {
    "user_id": "usr_abc123",
    "email": "user@example.com",
    "organization_id": "org_xyz789",
    "timestamp": "2025-12-13T14:30:00Z",
    "provider": "isa_user"
  },
  "metadata": {
    "permissions": "read:albums,write:photos",
    "has_organization": "true"
  }
}
```

**device.registered**:
```json
{
  "event_type": "device.registered",
  "source": "auth_service",
  "data": {
    "device_id": "emoframe_001",
    "organization_id": "org_xyz789",
    "device_name": "Living Room Display",
    "device_type": "display",
    "status": "active",
    "timestamp": "2025-12-13T14:30:00Z"
  }
}
```

**device.pairing_completed**:
```json
{
  "event_type": "device.pairing_completed",
  "source": "auth_service",
  "data": {
    "device_id": "emoframe_001",
    "user_id": "usr_alice123",
    "timestamp": "2025-12-13T14:30:00Z"
  }
}
```

---

## Glossary

**Access Token**: Short-lived JWT token (1 hour) used for API authentication

**API Key**: Long-lived credential for server-to-server authentication

**Auth0**: Third-party OAuth authentication provider

**Device Pairing**: Process of linking IoT device to user account via QR code

**Device Secret**: Credential used by IoT device to authenticate

**isa_user**: Custom JWT provider, primary authentication method

**JWT (JSON Web Token)**: Compact token format for authentication claims

**Organization**: Group entity owning API keys and devices

**Pairing Token**: Temporary token (5 minutes) for device-user pairing

**Pending Registration**: Temporary registration record awaiting email verification

**Provider**: Token issuer (auth0, isa_user)

**Refresh Token**: Long-lived token (7 days) used to obtain new access tokens

**Token Pair**: Access token + refresh token issued together

**Verification Code**: 6-digit code sent by email to verify registration

---

**Document End**
