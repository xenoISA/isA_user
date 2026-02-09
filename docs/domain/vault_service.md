# Vault Service Domain Documentation

## Overview

The Vault Service is responsible for secure credential and secret management within the isA platform. It provides enterprise-grade encryption, access control, and optional blockchain verification for sensitive credentials like API keys, database passwords, SSH keys, and OAuth tokens.

## Domain Concepts

### Core Entities

#### VaultItem
A secure container for storing encrypted credentials:
- `vault_id`: Unique identifier
- `user_id`: Owner of the secret
- `organization_id`: Optional organization association
- `secret_type`: Type of secret (api_key, database_credential, ssh_key, etc.)
- `provider`: Service provider (openai, aws, stripe, etc.)
- `name`: User-friendly name
- `description`: Optional description
- `encrypted_value`: Encrypted secret data
- `encryption_method`: Encryption algorithm used
- `metadata`: Additional structured data
- `tags`: Searchable tags
- `version`: Secret version number
- `expires_at`: Optional expiration timestamp
- `access_count`: Number of times accessed
- `is_active`: Active status
- `rotation_enabled`: Auto-rotation enabled
- `rotation_days`: Rotation interval
- `blockchain_reference`: Blockchain transaction hash

#### VaultAccessLog
Audit trail for vault operations:
- `log_id`: Unique identifier
- `vault_id`: Referenced vault item
- `user_id`: User who performed action
- `action`: Action type (create, read, update, delete, share, rotate)
- `ip_address`: Client IP address
- `user_agent`: Client user agent
- `success`: Operation success status
- `error_message`: Error details if failed
- `metadata`: Additional context

#### VaultShare
Secret sharing configuration:
- `share_id`: Unique identifier
- `vault_id`: Referenced vault item
- `owner_user_id`: Owner who created share
- `shared_with_user_id`: User share recipient
- `shared_with_org_id`: Organization share recipient
- `permission_level`: Access level (read, read_write)
- `expires_at`: Share expiration
- `is_active`: Share active status

### Value Objects

#### SecretType
Types of secrets that can be stored:
- `api_key`: API keys
- `database_credential`: Database credentials
- `ssh_key`: SSH private keys
- `ssl_certificate`: SSL/TLS certificates
- `oauth_token`: OAuth tokens
- `aws_credential`: AWS access credentials
- `blockchain_key`: Blockchain private keys
- `environment_variable`: Environment variables
- `custom`: Custom secret type

#### SecretProvider
Supported service providers:
- `openai`: OpenAI API
- `anthropic`: Anthropic API
- `stripe`: Stripe payments
- `aws`: Amazon Web Services
- `azure`: Microsoft Azure
- `gcp`: Google Cloud Platform
- `github`: GitHub
- `gitlab`: GitLab
- `ethereum`: Ethereum blockchain
- `polygon`: Polygon blockchain
- `custom`: Custom provider

#### EncryptionMethod
Supported encryption algorithms:
- `aes_256_gcm`: AES-256 with Galois/Counter Mode
- `fernet`: Fernet symmetric encryption
- `blockchain_encrypted`: Future blockchain-based encryption

#### VaultAction
Actions performed on vault items:
- `create`: Create new secret
- `read`: Read/access secret
- `update`: Update secret
- `delete`: Delete secret
- `rotate`: Rotate secret
- `share`: Share secret
- `revoke_share`: Revoke share
- `export`: Export secret
- `import`: Import secret

#### PermissionLevel
Permission levels for shared secrets:
- `read`: Read-only access
- `read_write`: Read and modify access

## Domain Rules

### Security Rules
1. Secrets must be encrypted at rest using AES-256-GCM
2. Multi-layer encryption: Master Key -> User KEK -> DEK -> Data
3. Users can only access their own secrets or shared secrets
4. All access attempts must be logged for audit
5. Expired secrets cannot be decrypted
6. Inactive secrets cannot be accessed

### Access Control Rules
1. Owner has full control over their secrets
2. Shared secrets respect permission levels
3. Share recipients cannot re-share secrets
4. Organization shares grant access to all org members
5. Expired shares are automatically invalidated

### Lifecycle Rules
1. Soft delete preserves audit history
2. Secret rotation creates new version
3. Blockchain-verified secrets maintain integrity hash
4. GDPR deletion removes all user vault data

## Bounded Context

### Internal Dependencies
- `VaultRepository`: Data persistence
- `VaultEncryption`: Multi-layer encryption
- `BlockchainVaultIntegration`: Blockchain verification

### External Dependencies
- `PostgreSQL (via gRPC)`: Primary data store
- `NATS JetStream`: Event publishing
- `Consul`: Service discovery
- `Blockchain Gateway`: Optional verification

### Events Published
- `vault.secret.created`: New secret created
- `vault.secret.accessed`: Secret accessed/decrypted
- `vault.secret.updated`: Secret updated
- `vault.secret.deleted`: Secret deleted
- `vault.secret.shared`: Secret shared
- `vault.secret.rotated`: Secret rotated

### Events Subscribed
- `account_service.user.deleted`: Trigger GDPR data deletion
- `*.user.deleted`: Universal user deletion handler

## Use Cases

### UC-1: Create Secret
Actor: Authenticated User
Flow:
1. User provides secret details (name, type, value)
2. System encrypts secret with multi-layer encryption
3. Optionally stores hash on blockchain
4. Creates vault item in database
5. Logs creation access
6. Publishes vault.secret.created event

### UC-2: Access Secret
Actor: Authenticated User
Flow:
1. User requests secret by vault_id
2. System verifies user access permission
3. Checks secret is active and not expired
4. Decrypts secret using user's KEK
5. Optionally verifies blockchain hash
6. Logs access attempt
7. Publishes vault.secret.accessed event
8. Returns decrypted secret

### UC-3: Share Secret
Actor: Secret Owner
Flow:
1. Owner specifies recipient (user or org)
2. System verifies ownership
3. Creates share record with permissions
4. Logs share action
5. Publishes vault.secret.shared event

### UC-4: Rotate Secret
Actor: Authenticated User
Flow:
1. User provides new secret value
2. System verifies write permission
3. Re-encrypts with new DEK
4. Increments version number
5. Updates blockchain hash if enabled
6. Logs rotation action
7. Publishes vault.secret.rotated event

### UC-5: GDPR Deletion
Actor: System (triggered by user.deleted event)
Flow:
1. Receives user.deleted event
2. Deletes all user's vault items
3. Deletes all shares (as owner and recipient)
4. Deletes access logs
5. Logs compliance action

## Glossary

| Term | Definition |
|------|------------|
| DEK | Data Encryption Key - encrypts actual secret data |
| KEK | Key Encryption Key - encrypts DEKs, derived per user |
| Master Key | Root key that encrypts KEKs |
| Vault Item | Encrypted container for a single secret |
| Secret Rotation | Process of updating secret value with version increment |
| Blockchain Verification | Storing secret hash on blockchain for tamper detection |
| GDPR | General Data Protection Regulation |
| Soft Delete | Marking record as inactive instead of physical deletion |
