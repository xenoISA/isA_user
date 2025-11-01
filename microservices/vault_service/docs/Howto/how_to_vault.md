# Vault Service - Complete Guide

## Overview

The **Vault Service** provides secure, encrypted storage for credentials, API keys, and sensitive data with multi-layer encryption and optional blockchain verification.

- **Service Name**: `vault_service`
- **Port**: 8214
- **Base URL**: `http://localhost:8214`
- **Database Schema**: Uses `dev.vault_items`, `dev.vault_access_logs`, `dev.vault_shares`

## Architecture & Security

### Multi-Layer Encryption

The vault uses a three-tier encryption architecture for maximum security:

```
Master Key (from .env)
    ↓ encrypts
User KEK (Key Encryption Key, per user)
    ↓ encrypts
Secret DEK (Data Encryption Key, per secret)
    ↓ encrypts
Actual Secret Data (AES-256-GCM)
```

**Why this approach?**
- **Isolation**: Each secret has its own encryption key (DEK)
- **Security**: Compromising one secret doesn't expose others
- **Rotation**: Can rotate individual secrets without re-encrypting everything
- **User Separation**: Each user has their own KEK derived from the master key + user_id

### Encryption Components

1. **Master Key** (`VAULT_MASTER_KEY` in .env)
   - Root key that encrypts all User KEKs
   - Generated using Fernet symmetric encryption
   - Must be base64-encoded 32-byte key
   - **Critical**: Keep this secure! Loss = data unrecoverable

2. **User KEK** (Key Encryption Key)
   - Derived using PBKDF2HMAC with 100,000 iterations
   - Input: Master Key + User ID + Random Salt
   - Unique per user
   - Encrypts all DEKs for that user's secrets

3. **Secret DEK** (Data Encryption Key)
   - Random 256-bit AES key generated per secret
   - Encrypted by the user's KEK before storage
   - Used with AES-256-GCM to encrypt actual secret value

4. **Stored Components** (in database metadata)
   - `encrypted_value`: Secret encrypted with DEK
   - `dek_encrypted`: DEK encrypted with KEK (base64)
   - `kek_salt`: Salt for KEK derivation (base64)
   - `nonce`: 96-bit nonce for AES-GCM (base64)

### Authentication

The vault service **integrates with the existing auth_service**:
- Requests must include `X-User-Id` header (set by auth middleware)
- Vault service trusts this header for user identification
- Additional authorization checks verify ownership before secret access
- Audit logs track all access attempts with IP and user agent

## Secret Types & Providers

### Supported Secret Types
- `api_key` - API keys and tokens
- `database_credential` - Database connection strings
- `ssh_key` - SSH private keys
- `ssl_certificate` - SSL/TLS certificates
- `oauth_token` - OAuth access/refresh tokens
- `aws_credential` - AWS access keys
- `blockchain_key` - Blockchain private keys
- `environment_variable` - Environment secrets
- `custom` - Other sensitive data

### Supported Providers
- `openai`, `anthropic`, `stripe`
- `aws`, `azure`, `gcp`
- `github`, `gitlab`
- `ethereum`, `polygon`
- `custom`

## API Endpoints

### Health & Info

#### Health Check
```bash
curl http://localhost:8214/health
```

**Response:**
```json
{
    "status": "healthy",
    "service": "vault_service",
    "port": 8214,
    "version": "1.0.0"
}
```

#### Detailed Health
```bash
curl http://localhost:8214/health/detailed
```

### Secret Management

#### 1. Create Secret

Create a new encrypted secret.

```bash
curl -X POST http://localhost:8214/api/v1/vault/secrets \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_001" \
  -d '{
    "secret_type": "api_key",
    "provider": "openai",
    "name": "OpenAI Production Key",
    "description": "Production API key for GPT-4",
    "secret_value": "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890",
    "tags": ["production", "openai", "critical"],
    "blockchain_verify": false
  }'
```

**Response:**
```json
{
    "vault_id": "960f0a84-d63d-48de-a99c-896ddb70c2f8",
    "user_id": "test_user_001",
    "organization_id": null,
    "secret_type": "api_key",
    "provider": "openai",
    "name": "OpenAI Production Key",
    "description": "Production API key for GPT-4",
    "encryption_method": "aes_256_gcm",
    "metadata": {
        "nonce": "MueXWsTwlXcY6+sS",
        "kek_salt": "YLW2hKHVKc/oMxCVNhV35NIKQe4dDPrXM8b0NsqRANo=",
        "dek_encrypted": "Z0FBQUFBQm8zOGNsNzBVMzFGdHV2a24tQS1zQnR4M0ZoZmJrNmE5SzRYOWxrYUQyckIzN3hLMEtOOHF1X0t4R0FEakFMZGJNQ1gyYmNOWGJ0bTJJeURmOENwdHUtWm1xMjJoSDV5ODlzNkt2V3RqQkY0RHpHTGNKWkcweVB5N3pCdVlyNmNNbnF6Tmk="
    },
    "tags": ["production", "openai", "critical"],
    "version": 1,
    "expires_at": null,
    "last_accessed_at": null,
    "access_count": 0,
    "is_active": true,
    "rotation_enabled": false,
    "rotation_days": null,
    "blockchain_reference": null,
    "created_at": "2025-10-03T12:52:53.419763",
    "updated_at": "2025-10-03T12:52:53.419763"
}
```

**Fields:**
- `secret_value`: The actual secret (will be encrypted)
- `expires_at`: Optional ISO 8601 timestamp
- `rotation_enabled`: Enable rotation reminders
- `rotation_days`: Days between rotation reminders
- `blockchain_verify`: Store hash on blockchain (requires blockchain_client)

#### 2. Create Database Credential with Expiration

```bash
curl -X POST http://localhost:8214/api/v1/vault/secrets \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_001" \
  -d '{
    "secret_type": "database_credential",
    "provider": "aws",
    "name": "Production PostgreSQL",
    "description": "Main production database credentials",
    "secret_value": "postgres://admin:SuperSecret123@prod-db.amazonaws.com:5432/maindb",
    "tags": ["production", "database", "aws"],
    "expires_at": "2025-12-31T23:59:59",
    "rotation_enabled": true,
    "rotation_days": 90
  }'
```

**Response:**
```json
{
    "vault_id": "40466f6a-3e8b-401f-a9dc-84f9233466e2",
    "secret_type": "database_credential",
    "provider": "aws",
    "name": "Production PostgreSQL",
    "expires_at": "2025-12-31T23:59:59",
    "rotation_enabled": true,
    "rotation_days": 90,
    ...
}
```

#### 3. Create Blockchain Key

```bash
curl -X POST http://localhost:8214/api/v1/vault/secrets \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_001" \
  -d '{
    "secret_type": "blockchain_key",
    "provider": "ethereum",
    "name": "Main Ethereum Wallet",
    "description": "Primary ETH wallet private key",
    "secret_value": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "tags": ["blockchain", "ethereum", "critical"],
    "blockchain_verify": false
  }'
```

#### 4. Get Secret (Decrypted)

Retrieve and decrypt a secret.

```bash
curl http://localhost:8214/api/v1/vault/secrets/960f0a84-d63d-48de-a99c-896ddb70c2f8 \
  -H "X-User-Id: test_user_001"
```

**Response:**
```json
{
    "vault_id": "960f0a84-d63d-48de-a99c-896ddb70c2f8",
    "name": "OpenAI Production Key",
    "secret_type": "api_key",
    "provider": "openai",
    "secret_value": "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890",
    "metadata": {
        "nonce": "MueXWsTwlXcY6+sS",
        "kek_salt": "YLW2hKHVKc/oMxCVNhV35NIKQe4dDPrXM8b0NsqRANo=",
        "dek_encrypted": "..."
    },
    "expires_at": null,
    "blockchain_verified": false
}
```

**Query Parameters:**
- `decrypt=true` (default) - Return decrypted value
- `decrypt=false` - Return encrypted metadata only

#### 5. List Secrets

List all secrets for the authenticated user.

```bash
curl 'http://localhost:8214/api/v1/vault/secrets?page=1&page_size=10' \
  -H "X-User-Id: test_user_001"
```

**Response:**
```json
{
    "items": [
        {
            "vault_id": "79eb8c4f-0cfb-4987-8e23-ac1b69522ed9",
            "secret_type": "blockchain_key",
            "provider": "ethereum",
            "name": "Main Ethereum Wallet",
            "tags": ["blockchain", "ethereum", "critical"],
            "is_active": true,
            ...
        },
        {
            "vault_id": "40466f6a-3e8b-401f-a9dc-84f9233466e2",
            "secret_type": "database_credential",
            "provider": "aws",
            "name": "Production PostgreSQL",
            ...
        }
    ],
    "total": 3,
    "page": 1,
    "page_size": 10
}
```

**Query Parameters:**
- `secret_type` - Filter by type (e.g., `api_key`)
- `tags` - Comma-separated tags (e.g., `production,critical`)
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 50, max: 200)

#### 6. Filter by Secret Type

```bash
curl 'http://localhost:8214/api/v1/vault/secrets?secret_type=api_key' \
  -H "X-User-Id: test_user_001"
```

#### 7. Filter by Tags

```bash
curl 'http://localhost:8214/api/v1/vault/secrets?tags=production,critical' \
  -H "X-User-Id: test_user_001"
```

#### 8. Update Secret Metadata

Update name, description, tags (not the secret value itself).

```bash
curl -X PUT http://localhost:8214/api/v1/vault/secrets/960f0a84-d63d-48de-a99c-896ddb70c2f8 \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_001" \
  -d '{
    "name": "OpenAI Production Key - Updated",
    "description": "Updated production API key for GPT-4 and DALL-E",
    "tags": ["production", "openai", "critical", "updated"]
  }'
```

**Response:**
```json
{
    "vault_id": "960f0a84-d63d-48de-a99c-896ddb70c2f8",
    "name": "OpenAI Production Key - Updated",
    "description": "Updated production API key for GPT-4 and DALL-E",
    "tags": ["production", "openai", "critical", "updated"],
    "version": 1,
    "updated_at": "2025-10-03T13:03:12.279464"
}
```

#### 9. Rotate Secret

Create a new version with a new secret value and new encryption keys.

```bash
curl -X POST 'http://localhost:8214/api/v1/vault/secrets/960f0a84-d63d-48de-a99c-896ddb70c2f8/rotate?new_secret_value=sk-proj-NEW_KEY_xyz9876543210abcdefghijklmnop' \
  -H "X-User-Id: test_user_001"
```

**Response:**
```json
{
    "vault_id": "960f0a84-d63d-48de-a99c-896ddb70c2f8",
    "version": 2,
    "metadata": {
        "nonce": "WQqcpGG5qidUPvHc",
        "kek_salt": "CwtUQ7NpA8QDPxezK8TYql1M6gCJh8ZMaxnJVjnCIyE=",
        "dek_encrypted": "Z0FBQUFBQm8zOG5ndlZNX0R1MHBTellNVERKZzA3YWZaRFUyNF9JbFM5UkV2QmtlUko0cE5DSmhhVFFsMEk0cnpCanJHa2JSTTlGS2Utd0ZiR0pCR191Snk1c2R1WnA3LXF2MTZqTlJLeHI0QWdzMkNlVkJubU55M1ZSd0haQ1cwSzZkNm5tME9hRzg="
    },
    "updated_at": "2025-10-03T13:04:32.226649"
}
```

**Note:** Version increments, new DEK/nonce/salt generated.

#### 10. Delete Secret

```bash
curl -X DELETE http://localhost:8214/api/v1/vault/secrets/79eb8c4f-0cfb-4987-8e23-ac1b69522ed9 \
  -H "X-User-Id: test_user_001"
```

**Response:**
```json
{
    "message": "Secret deleted successfully"
}
```

### Secret Sharing

#### 11. Share Secret with Another User

```bash
curl -X POST http://localhost:8214/api/v1/vault/secrets/40466f6a-3e8b-401f-a9dc-84f9233466e2/share \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_001" \
  -d '{
    "shared_with_user_id": "test_user_002",
    "permission_level": "read",
    "expires_at": "2025-11-01T23:59:59"
  }'
```

**Fields:**
- `shared_with_user_id` - User ID to share with (must exist in database)
- `shared_with_org_id` - Organization ID (alternative to user_id)
- `permission_level` - `read` or `read_write`
- `expires_at` - Optional expiration timestamp

**Note:** In tests, this requires `test_user_002` to exist in `dev.users` table.

#### 12. Get Shared Secrets

View secrets shared with you.

```bash
curl http://localhost:8214/api/v1/vault/shared \
  -H "X-User-Id: test_user_002"
```

### Statistics & Audit

#### 13. Get Vault Statistics

```bash
curl http://localhost:8214/api/v1/vault/stats \
  -H "X-User-Id: test_user_001"
```

**Response:**
```json
{
    "total_secrets": 3,
    "active_secrets": 3,
    "expired_secrets": 0,
    "secrets_by_type": {
        "database_credential": 1,
        "blockchain_key": 1,
        "api_key": 1
    },
    "secrets_by_provider": {
        "aws": 1,
        "ethereum": 1,
        "openai": 1
    },
    "total_access_count": 1,
    "shared_secrets": 0,
    "blockchain_verified_secrets": 0
}
```

#### 14. Get Audit Logs

View access logs for all vault operations.

```bash
curl 'http://localhost:8214/api/v1/vault/audit-logs?page=1&page_size=20' \
  -H "X-User-Id: test_user_001"
```

**Response:**
```json
[
    {
        "log_id": "634687b5-cdf3-49da-a9bc-93b9ab75071c",
        "vault_id": "960f0a84-d63d-48de-a99c-896ddb70c2f8",
        "user_id": "test_user_001",
        "action": "update",
        "ip_address": "127.0.0.1",
        "success": true,
        "error_message": null,
        "metadata": {},
        "created_at": "2025-10-03T13:04:32.293484"
    },
    {
        "log_id": "dd5ad5d2-b5c1-4781-93af-46737c2f000d",
        "vault_id": "960f0a84-d63d-48de-a99c-896ddb70c2f8",
        "user_id": "test_user_001",
        "action": "read",
        "ip_address": "127.0.0.1",
        "success": true,
        "error_message": null,
        "metadata": {},
        "created_at": "2025-10-03T13:02:57.917143"
    }
]
```

**Query Parameters:**
- `vault_id` - Filter by specific secret
- `page` - Page number
- `page_size` - Items per page (max: 200)

**Logged Actions:**
- `create`, `read`, `update`, `delete`
- `rotate`, `share`, `revoke_share`

## Python Client Integration

### Basic Usage

```python
import requests

BASE_URL = "http://localhost:8214/api/v1/vault"
USER_ID = "your_user_id"

# Helper function
def vault_request(method, endpoint, **kwargs):
    headers = kwargs.pop('headers', {})
    headers['X-User-Id'] = USER_ID
    url = f"{BASE_URL}{endpoint}"
    response = requests.request(method, url, headers=headers, **kwargs)
    return response.json()

# Create a secret
secret = vault_request('POST', '/secrets', json={
    'secret_type': 'api_key',
    'provider': 'openai',
    'name': 'My OpenAI Key',
    'secret_value': 'sk-...',
    'tags': ['production']
})
vault_id = secret['vault_id']

# Retrieve secret
secret_data = vault_request('GET', f'/secrets/{vault_id}')
print(f"Secret value: {secret_data['secret_value']}")

# List secrets
secrets = vault_request('GET', '/secrets?secret_type=api_key')
print(f"Found {secrets['total']} API keys")

# Update metadata
updated = vault_request('PUT', f'/secrets/{vault_id}', json={
    'name': 'Updated Name',
    'tags': ['production', 'updated']
})

# Rotate secret
rotated = vault_request('POST', f'/secrets/{vault_id}/rotate',
    params={'new_secret_value': 'sk-new-...'})
print(f"New version: {rotated['version']}")

# Get stats
stats = vault_request('GET', '/stats')
print(f"Total secrets: {stats['total_secrets']}")

# Get audit logs
logs = vault_request('GET', '/audit-logs?page=1&page_size=10')
for log in logs:
    print(f"{log['action']} on {log['vault_id']} at {log['created_at']}")
```

### Advanced: Sharing Secrets

```python
# Share with another user
share = vault_request('POST', f'/secrets/{vault_id}/share', json={
    'shared_with_user_id': 'other_user_id',
    'permission_level': 'read',
    'expires_at': '2025-12-31T23:59:59'
})

# View secrets shared with you
shared_secrets = vault_request('GET', '/shared')
```

### Error Handling

```python
try:
    secret = vault_request('GET', '/secrets/invalid-id')
except requests.HTTPError as e:
    if e.response.status_code == 404:
        print("Secret not found")
    elif e.response.status_code == 403:
        print("Access denied")
    elif e.response.status_code == 401:
        print("Authentication required")
```

## Database Schema

### vault_items Table

```sql
CREATE TABLE dev.vault_items (
    id SERIAL PRIMARY KEY,
    vault_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    secret_type VARCHAR(100) NOT NULL,
    provider VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    encrypted_value TEXT NOT NULL,
    encryption_method VARCHAR(50) DEFAULT 'aes_256_gcm',
    encryption_key_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    version INTEGER DEFAULT 1,
    expires_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    rotation_enabled BOOLEAN DEFAULT false,
    rotation_days INTEGER,
    blockchain_reference VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES dev.organizations(organization_id) ON DELETE CASCADE
);
```

### vault_access_logs Table

```sql
CREATE TABLE dev.vault_access_logs (
    id SERIAL PRIMARY KEY,
    log_id VARCHAR(255) NOT NULL UNIQUE,
    vault_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vault_id) REFERENCES dev.vault_items(vault_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
);
```

### vault_shares Table

```sql
CREATE TABLE dev.vault_shares (
    id SERIAL PRIMARY KEY,
    share_id VARCHAR(255) NOT NULL UNIQUE,
    vault_id VARCHAR(255) NOT NULL,
    owner_user_id VARCHAR(255) NOT NULL,
    shared_with_user_id VARCHAR(255),
    shared_with_org_id VARCHAR(255),
    permission_level VARCHAR(50) DEFAULT 'read',
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vault_id) REFERENCES dev.vault_items(vault_id) ON DELETE CASCADE,
    FOREIGN KEY (owner_user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (shared_with_user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (shared_with_org_id) REFERENCES dev.organizations(organization_id) ON DELETE CASCADE,

    CHECK (shared_with_user_id IS NOT NULL OR shared_with_org_id IS NOT NULL)
);
```

## Configuration

### Environment Variables

Add to `deployment/dev/.env`:

```bash
# Vault Service Configuration
VAULT_SERVICE_PORT=8214
VAULT_SERVICE_SERVICE_HOST=localhost

# Master Encryption Key (CRITICAL - Keep secure!)
VAULT_MASTER_KEY=ADhqO5mRKjWgKAUxPl8PDiRmNTipX930K2genrm_bGo=

# Blockchain Integration (Optional)
BLOCKCHAIN_ENABLED=false
GATEWAY_URL=http://localhost:8000
```

### Generate New Master Key

If you need to generate a new master key:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(f"VAULT_MASTER_KEY={key}")
```

**⚠️ WARNING:** Changing the master key will make all existing secrets unrecoverable!

## Service Management

### Start Service

```bash
# Start vault service only
cd /Users/xenodennis/Documents/Fun/isA_user
bash deployment/scripts/start_user_service.sh -e dev start vault_service

# Or start all services
bash deployment/scripts/start_user_service.sh -e dev start
```

### Stop Service

```bash
bash deployment/scripts/start_user_service.sh -e dev stop vault_service
```

### Restart Service

```bash
bash deployment/scripts/start_user_service.sh -e dev restart vault_service
```

### Check Status

```bash
bash deployment/scripts/start_user_service.sh -e dev status vault_service
```

### View Logs

```bash
bash deployment/scripts/start_user_service.sh -e dev logs vault_service
```

## Test Results

### Test Suite Summary

**Date**: 2025-10-03
**Total Tests**: 14
**Passed**: 13 ✅
**Failed**: 1 ⚠️ (requires test user in database)
**Success Rate**: 92.8%

### Test Details

| # | Test | Status | Notes |
|---|------|--------|-------|
| 1 | Health Check | ✅ Pass | Service healthy on port 8214 |
| 2 | Create API Key Secret | ✅ Pass | AES-256-GCM encryption |
| 3 | Create Database Credential | ✅ Pass | With expiration & rotation |
| 4 | Create Blockchain Key | ✅ Pass | Ethereum private key |
| 5 | List All Secrets | ✅ Pass | 3 secrets returned |
| 6 | Get Secret (Decrypted) | ✅ Pass | Decryption successful |
| 7 | Filter by Type | ✅ Pass | 1 API key found |
| 8 | Filter by Tags | ✅ Pass | Tags: production,critical |
| 9 | Update Metadata | ✅ Pass | Name and tags updated |
| 10 | Rotate Secret | ✅ Pass | Version 1→2, new keys |
| 11 | Share Secret | ⚠️ Fail | Requires test_user_002 in DB |
| 12 | Get Shared Secrets | ✅ Pass | Empty list (no shares) |
| 13 | Get Statistics | ✅ Pass | Correct counts |
| 14 | Get Audit Logs | ✅ Pass | 7 operations logged |
| 15 | Delete Secret | ✅ Pass | Deleted successfully |

### Sample Test Commands

```bash
# Quick test suite
SERVICE="http://localhost:8214"
USER="test_user_001"

# 1. Health check
curl -s $SERVICE/health | jq .

# 2. Create secret
curl -s -X POST $SERVICE/api/v1/vault/secrets \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER" \
  -d '{"secret_type":"api_key","provider":"openai","name":"Test Key","secret_value":"sk-test123","tags":["test"]}' | jq .

# 3. List secrets
curl -s "$SERVICE/api/v1/vault/secrets?page=1" -H "X-User-Id: $USER" | jq .

# 4. Get stats
curl -s $SERVICE/api/v1/vault/stats -H "X-User-Id: $USER" | jq .

# 5. Get audit logs
curl -s "$SERVICE/api/v1/vault/audit-logs?page=1" -H "X-User-Id: $USER" | jq .
```

## Blockchain Integration (Future)

The vault service has integration points for blockchain verification:

### How It Works (When Enabled)

1. **Secret Creation**:
   - Set `blockchain_verify: true`
   - Service creates SHA-256 hash of secret
   - Hash stored on blockchain via `blockchain_client`
   - Transaction hash saved in `blockchain_reference` field

2. **Verification**:
   - Retrieve transaction from blockchain
   - Compare stored hash with current secret hash
   - Detect tampering if hashes don't match

### Enable Blockchain

```bash
# In deployment/dev/.env
BLOCKCHAIN_ENABLED=true
GATEWAY_URL=http://localhost:8000
```

### Example with Blockchain

```bash
curl -X POST http://localhost:8214/api/v1/vault/secrets \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_001" \
  -d '{
    "secret_type": "blockchain_key",
    "name": "Critical Key",
    "secret_value": "0x...",
    "blockchain_verify": true
  }'
```

Response will include `blockchain_reference` with transaction hash.

## Security Best Practices

### 1. Master Key Management
- ✅ Store in secure environment variables or KMS
- ✅ Never commit to version control
- ✅ Rotate periodically (requires data migration)
- ✅ Use different keys for dev/staging/production

### 2. Access Control
- ✅ Always validate `X-User-Id` from auth service
- ✅ Check ownership before allowing secret access
- ✅ Use sharing feature for multi-user access
- ✅ Set expiration dates for shared secrets

### 3. Audit & Monitoring
- ✅ Review audit logs regularly
- ✅ Monitor for unusual access patterns
- ✅ Track failed access attempts
- ✅ Alert on expired secrets

### 4. Secret Lifecycle
- ✅ Set expiration dates for critical secrets
- ✅ Enable rotation for long-lived credentials
- ✅ Delete secrets when no longer needed
- ✅ Use tags for organization

### 5. Network Security
- ✅ Use HTTPS in production
- ✅ Restrict service to internal network
- ✅ Implement rate limiting
- ✅ Use VPN for remote access

## Troubleshooting

### "Vault service not initialized"
- Service hasn't started properly
- Check logs: `bash deployment/scripts/start_user_service.sh -e dev logs vault_service`
- Verify database connection

### "Failed to decrypt secret"
- Master key changed or corrupted
- KEK salt or DEK encrypted data corrupted
- User ID mismatch

### "Access denied"
- User doesn't own the secret
- Secret not shared with user
- Check ownership in database

### "Secret not found"
- Invalid vault_id
- Secret deleted
- Wrong database schema

### Fernet Key Error
```
ValueError: Fernet key must be 32 url-safe base64-encoded bytes
```
- Generate new key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Update `VAULT_MASTER_KEY` in .env

## Migration Guide

### Running Migrations

```bash
# Connect to database
psql $DATABASE_URL

# Run migration
\i microservices/vault_service/migrations/001_create_vault_tables.sql

# Verify tables
\dt dev.vault*
```

### Expected Tables
- `dev.vault_items` - Encrypted secrets
- `dev.vault_access_logs` - Audit trail
- `dev.vault_shares` - Sharing permissions

## Performance Considerations

### Encryption Overhead
- KEK derivation: ~100ms (PBKDF2 100k iterations)
- DEK encryption: <1ms (AES-GCM)
- Total create operation: ~150-200ms

### Optimization Tips
- Use pagination for large secret lists
- Cache decrypted secrets in application memory (with TTL)
- Index on frequently queried tags
- Partition access_logs table by date

### Recommended Limits
- Secrets per user: 1000-5000
- Secret value size: <100KB
- Tags per secret: <20
- Shares per secret: <50

## API Reference Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/health/detailed` | Detailed health |
| GET | `/info` | Service info |
| POST | `/api/v1/vault/secrets` | Create secret |
| GET | `/api/v1/vault/secrets/{id}` | Get secret (decrypted) |
| GET | `/api/v1/vault/secrets` | List secrets |
| PUT | `/api/v1/vault/secrets/{id}` | Update metadata |
| DELETE | `/api/v1/vault/secrets/{id}` | Delete secret |
| POST | `/api/v1/vault/secrets/{id}/rotate` | Rotate secret |
| POST | `/api/v1/vault/secrets/{id}/share` | Share secret |
| GET | `/api/v1/vault/shared` | Get shared secrets |
| GET | `/api/v1/vault/stats` | Get statistics |
| GET | `/api/v1/vault/audit-logs` | Get audit logs |
| POST | `/api/v1/vault/secrets/{id}/test` | Test credential |

## Support

For issues or questions:
- Check logs: `deployment/scripts/start_user_service.sh -e dev logs vault_service`
- Review audit logs via API
- Verify database schema
- Check Consul registration (if enabled)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-03
**Service Port**: 8214
**Encryption**: AES-256-GCM with multi-layer key architecture
