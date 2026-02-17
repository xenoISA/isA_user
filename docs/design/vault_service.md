# Vault Service Design Document

## Architecture Overview

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Vault Service                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   main.py   │  │   routes    │  │      FastAPI App        │ │
│  │  (FastAPI)  │──│  registry   │──│   /api/v1/vault/*       │ │
│  └──────┬──────┘  └─────────────┘  └─────────────────────────┘ │
│         │                                                        │
│  ┌──────▼──────────────────────────────────────────────────────┐│
│  │                    VaultService                              ││
│  │  - create_secret()    - share_secret()                      ││
│  │  - get_secret()       - rotate_secret()                     ││
│  │  - update_secret()    - get_stats()                         ││
│  │  - delete_secret()    - test_credential()                   ││
│  │  - list_secrets()     - get_access_logs()                   ││
│  └──────┬────────────────────┬────────────────────┬────────────┘│
│         │                    │                    │              │
│  ┌──────▼──────┐    ┌───────▼───────┐    ┌──────▼──────┐       │
│  │   Vault     │    │    Vault      │    │  Blockchain │       │
│  │ Repository  │    │  Encryption   │    │ Integration │       │
│  └──────┬──────┘    └───────────────┘    └──────┬──────┘       │
│         │                                        │              │
└─────────┼────────────────────────────────────────┼──────────────┘
          │                                        │
   ┌──────▼──────┐                         ┌──────▼──────┐
   │  PostgreSQL │                         │  Blockchain │
   │ (via gRPC)  │                         │   Gateway   │
   └─────────────┘                         └─────────────┘
```

### Dependency Injection Architecture

```
protocols.py (Interfaces)
├── VaultRepositoryProtocol
├── VaultEncryptionProtocol
├── BlockchainIntegrationProtocol
└── EventBusProtocol

factory.py (Production Dependencies)
├── create_vault_service()
├── create_vault_repository()
├── create_vault_encryption()
└── create_blockchain_integration()

vault_service.py (Business Logic)
└── VaultService(repository, encryption, blockchain, event_bus)
```

## Encryption Architecture

### Multi-Layer Encryption

```
┌─────────────────────────────────────────────────────────────────┐
│                     Encryption Layers                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: Master Key (from environment/KMS)                     │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  VAULT_MASTER_KEY (Fernet key, base64 encoded)       │       │
│  │  - Stored securely in environment/secrets manager    │       │
│  │  - Used to derive User KEKs                          │       │
│  └──────────────────────────────────────────────────────┘       │
│                           │                                      │
│                           ▼                                      │
│  Layer 2: User KEK (Key Encryption Key)                         │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Derived using PBKDF2-SHA256:                        │       │
│  │  KEK = PBKDF2(master_key + user_id, salt, 100000)    │       │
│  │  - Per-user key encryption key                       │       │
│  │  - Salt stored with each secret                      │       │
│  └──────────────────────────────────────────────────────┘       │
│                           │                                      │
│                           ▼                                      │
│  Layer 3: DEK (Data Encryption Key)                             │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  AES-256 key generated per secret:                   │       │
│  │  - Random 256-bit key for each secret                │       │
│  │  - Encrypted with KEK using Fernet                   │       │
│  │  - Stored alongside encrypted data                   │       │
│  └──────────────────────────────────────────────────────┘       │
│                           │                                      │
│                           ▼                                      │
│  Layer 4: Data Encryption                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  AES-256-GCM encryption:                             │       │
│  │  - 96-bit nonce (random per encryption)              │       │
│  │  - Authenticated encryption with tag                 │       │
│  │  - Encrypted data stored in database                 │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Encryption Flow

```python
# Encryption
1. Generate DEK = random_256_bit_key()
2. Generate nonce = random_96_bit()
3. encrypted_data = AES_GCM_encrypt(DEK, nonce, plaintext)
4. KEK, salt = derive_kek(master_key, user_id)
5. encrypted_DEK = Fernet_encrypt(KEK, DEK)
6. Store: encrypted_data, encrypted_DEK, salt, nonce

# Decryption
1. Retrieve: encrypted_data, encrypted_DEK, salt, nonce
2. KEK = derive_kek(master_key, user_id, salt)
3. DEK = Fernet_decrypt(KEK, encrypted_DEK)
4. plaintext = AES_GCM_decrypt(DEK, nonce, encrypted_data)
```

## Data Model

### Database Schema

```sql
-- Schema: vault

CREATE TABLE vault.vault_items (
    vault_id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    secret_type VARCHAR(50) NOT NULL,
    provider VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    encrypted_value TEXT NOT NULL,  -- Base64 encoded
    encryption_method VARCHAR(50) DEFAULT 'aes_256_gcm',
    encryption_key_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    version INTEGER DEFAULT 1,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    rotation_enabled BOOLEAN DEFAULT FALSE,
    rotation_days INTEGER,
    blockchain_reference VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE vault.vault_access_logs (
    log_id UUID PRIMARY KEY,
    vault_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE vault.vault_shares (
    share_id UUID PRIMARY KEY,
    vault_id UUID NOT NULL,
    owner_user_id VARCHAR(255) NOT NULL,
    shared_with_user_id VARCHAR(255),
    shared_with_org_id VARCHAR(255),
    permission_level VARCHAR(20) DEFAULT 'read',
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_vault_items_user_id ON vault.vault_items(user_id);
CREATE INDEX idx_vault_items_org_id ON vault.vault_items(organization_id);
CREATE INDEX idx_vault_items_type ON vault.vault_items(secret_type);
CREATE INDEX idx_vault_items_tags ON vault.vault_items USING GIN(tags);
CREATE INDEX idx_vault_logs_vault_id ON vault.vault_access_logs(vault_id);
CREATE INDEX idx_vault_logs_user_id ON vault.vault_access_logs(user_id);
CREATE INDEX idx_vault_shares_vault_id ON vault.vault_shares(vault_id);
CREATE INDEX idx_vault_shares_shared_user ON vault.vault_shares(shared_with_user_id);
```

## API Design

### Request/Response Schemas

#### Create Secret
```json
// Request
{
    "secret_type": "api_key",
    "provider": "openai",
    "name": "Production OpenAI Key",
    "description": "API key for production environment",
    "secret_value": "sk-xxxxxxxxxxxxx",
    "organization_id": null,
    "metadata": {"environment": "production"},
    "tags": ["production", "ai"],
    "expires_at": "2024-12-31T23:59:59Z",
    "rotation_enabled": true,
    "rotation_days": 90,
    "blockchain_verify": false
}

// Response (201 Created)
{
    "vault_id": "uuid",
    "user_id": "user_123",
    "organization_id": null,
    "secret_type": "api_key",
    "provider": "openai",
    "name": "Production OpenAI Key",
    "description": "API key for production environment",
    "encryption_method": "aes_256_gcm",
    "metadata": {"environment": "production"},
    "tags": ["production", "ai"],
    "version": 1,
    "expires_at": "2024-12-31T23:59:59Z",
    "last_accessed_at": null,
    "access_count": 0,
    "is_active": true,
    "rotation_enabled": true,
    "rotation_days": 90,
    "blockchain_reference": null,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Get Secret (Decrypted)
```json
// Response (200 OK)
{
    "vault_id": "uuid",
    "name": "Production OpenAI Key",
    "secret_type": "api_key",
    "provider": "openai",
    "secret_value": "sk-xxxxxxxxxxxxx",
    "metadata": {"environment": "production"},
    "expires_at": "2024-12-31T23:59:59Z",
    "blockchain_verified": false
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Invalid request data |
| 401 | UNAUTHORIZED | Missing authentication |
| 403 | FORBIDDEN | Access denied to secret |
| 404 | NOT_FOUND | Secret not found |
| 422 | VALIDATION_ERROR | Validation failed |
| 500 | INTERNAL_ERROR | Server error |

## Event Architecture

### Published Events

```python
# vault.secret.created
{
    "event_type": "vault.secret.created",
    "source": "vault_service",
    "data": {
        "vault_id": "uuid",
        "user_id": "user_123",
        "organization_id": null,
        "secret_type": "api_key",
        "provider": "openai",
        "name": "Production OpenAI Key",
        "blockchain_verified": false,
        "timestamp": "2024-01-01T00:00:00Z"
    }
}

# vault.secret.accessed
{
    "event_type": "vault.secret.accessed",
    "source": "vault_service",
    "data": {
        "vault_id": "uuid",
        "user_id": "user_123",
        "secret_type": "api_key",
        "decrypted": true,
        "blockchain_verified": false,
        "timestamp": "2024-01-01T00:00:00Z"
    }
}
```

### Subscribed Events

```python
# account_service.user.deleted / *.user.deleted
# Triggers: GDPR data deletion
# Handler: handle_user_deleted()
```

## Security Considerations

### Threat Model

1. **Database Compromise**: Multi-layer encryption ensures data is useless without master key
2. **Memory Inspection**: DEKs are short-lived, cleared after use
3. **Unauthorized Access**: Access control with audit logging
4. **Tampering**: Blockchain verification for integrity
5. **Key Compromise**: Key rotation supported at all layers

### Security Controls

1. **Authentication**: X-User-Id header required
2. **Authorization**: Owner/share permission checks
3. **Encryption**: AES-256-GCM with unique DEK per secret
4. **Audit**: Comprehensive access logging
5. **Expiration**: Automatic secret expiration
6. **Rotation**: Manual and automatic key rotation

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| VAULT_MASTER_KEY | Master encryption key | Generated (dev only) |
| BLOCKCHAIN_ENABLED | Enable blockchain verification | false |
| GATEWAY_URL | Blockchain gateway URL | http://localhost:8000 |
| POSTGRES_HOST | PostgreSQL gRPC host | isa-postgres-grpc |
| POSTGRES_PORT | PostgreSQL gRPC port | 50061 |
| SERVICE_PORT | Vault service port | 8214 |

### Service Discovery

- **Consul Registration**: vault_service on port 8214
- **Health Check**: HTTP /health endpoint
- **Tags**: vault, security, secrets, v1

## Testing Strategy

### Test Pyramid

```
        ┌─────────┐
        │  Smoke  │  ~20 tests (E2E sanity)
        ├─────────┤
      ┌─┴─────────┴─┐
      │     API     │  ~30 tests (HTTP contracts)
      ├─────────────┤
    ┌─┴─────────────┴─┐
    │   Integration   │  ~35 tests (DB + Service)
    ├─────────────────┤
  ┌─┴─────────────────┴─┐
  │      Component      │  ~60 tests (Service logic)
  ├─────────────────────┤
┌─┴─────────────────────┴─┐
│          Unit           │  ~80 tests (Models, utils)
└─────────────────────────┘
```

### Test Categories

1. **Unit Tests**: Model validation, encryption utilities, pure functions
2. **Component Tests**: VaultService with mocked repository
3. **Integration Tests**: Real database operations
4. **API Tests**: HTTP endpoint contracts
5. **Smoke Tests**: Deployment verification

## Deployment

### Resource Requirements

- **CPU**: 0.5 cores minimum
- **Memory**: 512MB minimum
- **Storage**: Minimal (DB external)

### Health Endpoints

- `GET /health`: Basic liveness
- `GET /health/detailed`: Dependency status
- `GET /info`: Service metadata

### Monitoring

- Access patterns and counts
- Encryption/decryption latency
- Error rates by operation
- Blockchain verification status
