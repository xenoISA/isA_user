# Authentication

Identity and access management services.

## Overview

Authentication in isA User is handled by four core services:

| Service | Port | Purpose |
|---------|------|---------|
| auth_service | 8201 | JWT tokens, API keys, device auth |
| account_service | 8202 | User profiles, settings |
| session_service | 8203 | Session tracking, context |
| authorization_service | 8204 | RBAC, permissions |

## Auth Service (8201)

### JWT Authentication

```bash
# Login and get token
curl -X POST "http://localhost:8201/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Token Refresh

```bash
curl -X POST "http://localhost:8201/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### API Key Management

```bash
# Create API key
curl -X POST "http://localhost:8201/api/v1/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App Key",
    "scopes": ["read:storage", "write:storage"],
    "expires_in_days": 365
  }'
```

Response:
```json
{
  "key_id": "ak_123456789",
  "api_key": "sk_live_abc123xyz...",
  "name": "My App Key",
  "scopes": ["read:storage", "write:storage"],
  "expires_at": "2026-01-28T00:00:00Z"
}
```

### Device Authentication

```bash
# Register device
curl -X POST "http://localhost:8201/api/v1/auth/devices" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device_abc123",
    "device_type": "mobile",
    "device_name": "iPhone 15"
  }'
```

## Account Service (8202)

### Create Account

```bash
curl -X POST "http://localhost:8202/api/v1/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "password": "secure_password",
    "metadata": {
      "source": "web_signup"
    }
  }'
```

### Get Profile

```bash
curl "http://localhost:8202/api/v1/accounts/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Profile

```bash
curl -X PATCH "http://localhost:8202/api/v1/accounts/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "avatar_url": "https://example.com/avatar.jpg",
    "preferences": {
      "theme": "dark",
      "notifications": true
    }
  }'
```

### Change Password

```bash
curl -X POST "http://localhost:8202/api/v1/accounts/me/password" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "old_password",
    "new_password": "new_secure_password"
  }'
```

## Session Service (8203)

### Create Session

```bash
curl -X POST "http://localhost:8203/api/v1/sessions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device_abc123",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }'
```

### Get Active Sessions

```bash
curl "http://localhost:8203/api/v1/sessions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "device_name": "iPhone 15",
      "ip_address": "192.168.1.1",
      "last_active": "2024-01-28T10:30:00Z",
      "is_current": true
    }
  ],
  "max_sessions": 5
}
```

### Revoke Session

```bash
curl -X DELETE "http://localhost:8203/api/v1/sessions/sess_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Session Context

Store context within a session:

```bash
curl -X PUT "http://localhost:8203/api/v1/sessions/current/context" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_organization": "org_123",
    "active_project": "proj_456"
  }'
```

## Authorization Service (8204)

### Role-Based Access Control

```bash
# Get user roles
curl "http://localhost:8204/api/v1/authorization/roles" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Check Permission

```bash
curl -X POST "http://localhost:8204/api/v1/authorization/check" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource": "storage",
    "action": "write",
    "resource_id": "file_123"
  }'
```

Response:
```json
{
  "allowed": true,
  "reason": "User has write permission via 'editor' role"
}
```

### Assign Role

```bash
curl -X POST "http://localhost:8204/api/v1/authorization/roles/assign" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_456",
    "role": "editor",
    "resource_type": "organization",
    "resource_id": "org_123"
  }'
```

### Built-in Roles

| Role | Description |
|------|-------------|
| `owner` | Full access, can delete resource |
| `admin` | Manage users and settings |
| `editor` | Read and write access |
| `viewer` | Read-only access |
| `guest` | Limited temporary access |

## Python SDK

```python
from isa_user import AuthClient, AccountClient

# Initialize clients
auth = AuthClient("http://localhost:8201")
account = AccountClient("http://localhost:8202")

# Login
tokens = await auth.login("user@example.com", "password")

# Get profile
profile = await account.get_profile(tokens.access_token)

# Create API key
api_key = await auth.create_api_key(
    token=tokens.access_token,
    name="My App",
    scopes=["read:storage"]
)

# Check permission
allowed = await auth.check_permission(
    token=tokens.access_token,
    resource="storage",
    action="write"
)
```

## Security Features

### Multi-Factor Authentication

```bash
# Enable MFA
curl -X POST "http://localhost:8201/api/v1/auth/mfa/enable" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Verify MFA code
curl -X POST "http://localhost:8201/api/v1/auth/mfa/verify" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"code": "123456"}'
```

### Rate Limiting

| Endpoint | Limit |
|----------|-------|
| Login | 5/minute |
| Token refresh | 10/minute |
| API calls | 1000/hour |

### Token Security

- Access tokens expire in 1 hour
- Refresh tokens expire in 30 days
- Tokens are signed with RS256 or HS256
- Device binding for sensitive operations

## Next Steps

- [Payments](./payments) - Payment processing
- [Storage](./storage) - File management
- [Organizations](./organizations) - Multi-tenant
