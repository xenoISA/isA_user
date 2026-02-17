# Security

Secure credential and secret management.

## Overview

Security capabilities are handled by the vault service:

| Service | Port | Purpose |
|---------|------|---------|
| vault_service | 8214 | Encrypted secrets, credentials |

## Vault Service (8214)

### Create Secret

```bash
curl -X POST "http://localhost:8214/api/v1/vault/secrets" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Database",
    "type": "database_credential",
    "value": {
      "host": "db.example.com",
      "port": 5432,
      "username": "admin",
      "password": "super_secret_password"
    },
    "encryption": "aes256",
    "tags": ["production", "database"],
    "expires_at": "2025-01-28T00:00:00Z"
  }'
```

Response:
```json
{
  "vault_id": "vault_abc123",
  "name": "Production Database",
  "type": "database_credential",
  "encryption": "aes256",
  "created_at": "2024-01-28T10:30:00Z",
  "expires_at": "2025-01-28T00:00:00Z",
  "version": 1
}
```

### Get Secret

```bash
curl "http://localhost:8214/api/v1/vault/secrets/vault_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "vault_id": "vault_abc123",
  "name": "Production Database",
  "type": "database_credential",
  "value": {
    "host": "db.example.com",
    "port": 5432,
    "username": "admin",
    "password": "super_secret_password"
  },
  "version": 1,
  "accessed_at": "2024-01-28T10:30:00Z"
}
```

### List Secrets

```bash
curl "http://localhost:8214/api/v1/vault/secrets?type=api_key&tags=production" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "secrets": [
    {
      "vault_id": "vault_abc123",
      "name": "Production Database",
      "type": "database_credential",
      "tags": ["production", "database"],
      "created_at": "2024-01-28T10:30:00Z"
    },
    {
      "vault_id": "vault_def456",
      "name": "Stripe API Key",
      "type": "api_key",
      "tags": ["production", "payments"],
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 2
}
```

### Update Secret

```bash
curl -X PUT "http://localhost:8214/api/v1/vault/secrets/vault_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": {
      "host": "db.example.com",
      "port": 5432,
      "username": "admin",
      "password": "new_rotated_password"
    },
    "rotation_reason": "scheduled_rotation"
  }'
```

Response:
```json
{
  "vault_id": "vault_abc123",
  "version": 2,
  "previous_version": 1,
  "updated_at": "2024-01-28T11:00:00Z"
}
```

### Delete Secret

```bash
curl -X DELETE "http://localhost:8214/api/v1/vault/secrets/vault_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Share Secret

```bash
curl -X POST "http://localhost:8214/api/v1/vault/secrets/vault_abc123/share" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": ["user_456", "user_789"],
    "permission": "read",
    "expires_at": "2024-02-28T00:00:00Z"
  }'
```

Response:
```json
{
  "shares": [
    {
      "share_id": "share_xyz",
      "user_id": "user_456",
      "permission": "read",
      "expires_at": "2024-02-28T00:00:00Z"
    },
    {
      "share_id": "share_abc",
      "user_id": "user_789",
      "permission": "read",
      "expires_at": "2024-02-28T00:00:00Z"
    }
  ]
}
```

### Get Access Logs

```bash
curl "http://localhost:8214/api/v1/vault/secrets/vault_abc123/access-logs" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "logs": [
    {
      "log_id": "log_123",
      "action": "read",
      "user_id": "user_123",
      "ip_address": "192.168.1.1",
      "timestamp": "2024-01-28T10:30:00Z"
    },
    {
      "log_id": "log_124",
      "action": "update",
      "user_id": "user_123",
      "ip_address": "192.168.1.1",
      "timestamp": "2024-01-28T11:00:00Z"
    }
  ],
  "total": 2
}
```

### Get Vault Statistics

```bash
curl "http://localhost:8214/api/v1/vault/stats" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "total_secrets": 150,
  "by_type": {
    "api_key": 45,
    "database_credential": 30,
    "ssh_key": 25,
    "certificate": 20,
    "generic": 30
  },
  "expiring_soon": 5,
  "shared_secrets": 12,
  "total_accesses_today": 250
}
```

## Secret Types

| Type | Description | Fields |
|------|-------------|--------|
| `api_key` | API keys and tokens | key, provider |
| `database_credential` | Database credentials | host, port, username, password, database |
| `ssh_key` | SSH private keys | private_key, public_key, passphrase |
| `certificate` | TLS/SSL certificates | certificate, private_key, chain |
| `oauth_credential` | OAuth tokens | client_id, client_secret, refresh_token |
| `encryption_key` | Encryption keys | key, algorithm |
| `generic` | Generic secrets | custom fields |

## Secret Templates

### API Key

```bash
curl -X POST "http://localhost:8214/api/v1/vault/secrets" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI API Key",
    "type": "api_key",
    "value": {
      "key": "sk-...",
      "provider": "openai"
    },
    "tags": ["ai", "production"]
  }'
```

### SSH Key

```bash
curl -X POST "http://localhost:8214/api/v1/vault/secrets" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Server SSH",
    "type": "ssh_key",
    "value": {
      "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n...",
      "public_key": "ssh-rsa AAAA...",
      "passphrase": "optional_passphrase"
    },
    "tags": ["production", "server"]
  }'
```

### TLS Certificate

```bash
curl -X POST "http://localhost:8214/api/v1/vault/secrets" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "api.example.com Certificate",
    "type": "certificate",
    "value": {
      "certificate": "-----BEGIN CERTIFICATE-----\n...",
      "private_key": "-----BEGIN PRIVATE KEY-----\n...",
      "chain": "-----BEGIN CERTIFICATE-----\n..."
    },
    "expires_at": "2025-01-28T00:00:00Z",
    "tags": ["production", "tls"]
  }'
```

### OAuth Credentials

```bash
curl -X POST "http://localhost:8214/api/v1/vault/secrets" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google OAuth",
    "type": "oauth_credential",
    "value": {
      "client_id": "123456789.apps.googleusercontent.com",
      "client_secret": "GOCSPX-...",
      "refresh_token": "1//..."
    },
    "tags": ["google", "oauth"]
  }'
```

## Encryption Methods

| Method | Description |
|--------|-------------|
| `aes256` | AES-256-GCM encryption |
| `aes128` | AES-128-GCM encryption |
| `chacha20` | ChaCha20-Poly1305 |

## Permission Levels

| Permission | Capabilities |
|------------|--------------|
| `read` | View secret value |
| `write` | Update secret value |
| `admin` | Full control, delete, share |

## Rotation

### Manual Rotation

```bash
curl -X PUT "http://localhost:8214/api/v1/vault/secrets/vault_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": {"password": "new_password"},
    "rotation_reason": "manual"
  }'
```

### Auto-Rotation Policy

```bash
curl -X POST "http://localhost:8214/api/v1/vault/secrets/vault_abc123/rotation-policy" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "interval_days": 90,
    "notification_days_before": 7,
    "auto_rotate": false
  }'
```

## Blockchain Verification

The vault service supports optional blockchain verification for audit trails:

```bash
curl "http://localhost:8214/api/v1/vault/secrets/vault_abc123/blockchain-proof" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "vault_id": "vault_abc123",
  "hash": "0x...",
  "block_number": 12345678,
  "transaction_id": "0x...",
  "timestamp": "2024-01-28T10:30:00Z",
  "verified": true
}
```

## Python SDK

```python
from isa_user import VaultClient

vault = VaultClient("http://localhost:8214")

# Create secret
secret = await vault.create(
    token=access_token,
    name="Production Database",
    type="database_credential",
    value={
        "host": "db.example.com",
        "username": "admin",
        "password": "secret"
    },
    tags=["production"]
)

# Get secret
data = await vault.get(
    token=access_token,
    vault_id=secret.vault_id
)

# Update/rotate secret
await vault.update(
    token=access_token,
    vault_id=secret.vault_id,
    value={"password": "new_password"}
)

# Share secret
await vault.share(
    token=access_token,
    vault_id=secret.vault_id,
    user_ids=["user_456"],
    permission="read"
)

# Get access logs
logs = await vault.get_access_logs(
    token=access_token,
    vault_id=secret.vault_id
)

# Delete secret
await vault.delete(
    token=access_token,
    vault_id=secret.vault_id
)
```

## Best Practices

### Naming Conventions

```
{environment}-{service}-{type}

Examples:
- prod-api-stripe-key
- staging-db-postgres-cred
- dev-aws-access-key
```

### Tagging Strategy

```json
{
  "tags": [
    "environment:production",
    "service:api",
    "team:backend",
    "rotation:quarterly"
  ]
}
```

### Access Control

1. **Principle of Least Privilege**: Grant minimum necessary permissions
2. **Time-Limited Access**: Use expiring shares for temporary access
3. **Audit Regularly**: Review access logs periodically
4. **Rotate Frequently**: Implement rotation policies

### Security Recommendations

- Enable MFA for vault access
- Use strong encryption (AES-256)
- Set expiration dates on secrets
- Monitor access logs for anomalies
- Implement rotation policies
- Use separate secrets per environment

## Next Steps

- [Authentication](./authentication) - Auth services
- [Operations](./operations) - Audit & compliance
- [Architecture](./architecture) - System design
