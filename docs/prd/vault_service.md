# Vault Service PRD (Product Requirements Document)

## Product Overview

### Vision
Provide a secure, enterprise-grade secret management solution that protects sensitive credentials with multi-layer encryption while maintaining auditability and optional blockchain verification.

### Problem Statement
Applications need to store and manage sensitive credentials (API keys, passwords, tokens) securely. Traditional storage methods expose credentials to security risks. Users need a centralized, secure vault with access control, audit logging, and optional tamper-proof verification.

### Target Users
1. **Developers**: Store API keys, database credentials, environment variables
2. **DevOps Engineers**: Manage infrastructure secrets, SSH keys, certificates
3. **Security Teams**: Audit credential access, enforce rotation policies
4. **Organizations**: Share secrets across teams with controlled access

## Requirements

### Functional Requirements

#### FR-1: Secret Storage
- **FR-1.1**: Store secrets with AES-256-GCM encryption
- **FR-1.2**: Support multiple secret types (API key, database, SSH, etc.)
- **FR-1.3**: Support multiple providers (AWS, OpenAI, Stripe, etc.)
- **FR-1.4**: Allow metadata and tags for organization
- **FR-1.5**: Support optional expiration dates

#### FR-2: Secret Access
- **FR-2.1**: Retrieve and decrypt secrets with proper authorization
- **FR-2.2**: Support encrypted-only retrieval (without decryption)
- **FR-2.3**: Track access count and last access time
- **FR-2.4**: Verify blockchain hash when available

#### FR-3: Secret Management
- **FR-3.1**: Update secret metadata without re-encryption
- **FR-3.2**: Update secret value with version increment
- **FR-3.3**: Soft delete secrets (preserve audit history)
- **FR-3.4**: List secrets with filtering by type, tags, status

#### FR-4: Secret Sharing
- **FR-4.1**: Share secrets with specific users
- **FR-4.2**: Share secrets with organizations
- **FR-4.3**: Support read-only and read-write permissions
- **FR-4.4**: Support share expiration
- **FR-4.5**: Revoke shares

#### FR-5: Secret Rotation
- **FR-5.1**: Manual secret rotation
- **FR-5.2**: Configure auto-rotation schedule
- **FR-5.3**: Version tracking for rotated secrets

#### FR-6: Blockchain Verification
- **FR-6.1**: Store secret hash on blockchain
- **FR-6.2**: Verify secret integrity against blockchain
- **FR-6.3**: Detect tampering through hash mismatch

#### FR-7: Audit Logging
- **FR-7.1**: Log all vault operations
- **FR-7.2**: Capture IP address and user agent
- **FR-7.3**: Record success/failure with error details
- **FR-7.4**: Query logs by vault item or user

#### FR-8: Statistics
- **FR-8.1**: Total secrets count by user
- **FR-8.2**: Secrets by type and provider
- **FR-8.3**: Expired and expiring secrets
- **FR-8.4**: Total access counts
- **FR-8.5**: Blockchain verification status

#### FR-9: GDPR Compliance
- **FR-9.1**: Complete user data deletion
- **FR-9.2**: Handle user.deleted events automatically
- **FR-9.3**: Remove all vault items, shares, and logs

### Non-Functional Requirements

#### NFR-1: Security
- **NFR-1.1**: Multi-layer encryption (Master Key -> KEK -> DEK)
- **NFR-1.2**: Keys never stored in plaintext
- **NFR-1.3**: Encryption at rest and in transit
- **NFR-1.4**: No secrets in logs or error messages

#### NFR-2: Performance
- **NFR-2.1**: Secret retrieval < 100ms (excluding blockchain)
- **NFR-2.2**: Encryption/decryption < 50ms
- **NFR-2.3**: List operations < 200ms

#### NFR-3: Availability
- **NFR-3.1**: 99.9% service uptime
- **NFR-3.2**: Graceful degradation without blockchain
- **NFR-3.3**: Event bus failures don't block operations

#### NFR-4: Auditability
- **NFR-4.1**: Complete audit trail for all operations
- **NFR-4.2**: Tamper-proof logging
- **NFR-4.3**: Retention per compliance requirements

#### NFR-5: Scalability
- **NFR-5.1**: Support 100K+ secrets per user
- **NFR-5.2**: Horizontal scaling capability
- **NFR-5.3**: Efficient pagination

## API Endpoints

### Health & Info
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/detailed` | Detailed health with dependencies |
| GET | `/info` | Service information |

### Secret Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/vault/secrets` | Create new secret |
| GET | `/api/v1/vault/secrets` | List user's secrets |
| GET | `/api/v1/vault/secrets/{vault_id}` | Get specific secret |
| PUT | `/api/v1/vault/secrets/{vault_id}` | Update secret |
| DELETE | `/api/v1/vault/secrets/{vault_id}` | Delete secret |
| POST | `/api/v1/vault/secrets/{vault_id}/rotate` | Rotate secret |
| POST | `/api/v1/vault/secrets/{vault_id}/test` | Test credential |

### Sharing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/vault/secrets/{vault_id}/share` | Share secret |
| GET | `/api/v1/vault/shared` | Get shared secrets |

### Utility
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/vault/audit-logs` | Get audit logs |
| GET | `/api/v1/vault/stats` | Get vault statistics |

## Success Metrics

### Key Performance Indicators
1. **Security**: Zero credential leaks
2. **Availability**: 99.9% uptime
3. **Performance**: P95 response time < 100ms
4. **Adoption**: Active users storing secrets
5. **Compliance**: 100% GDPR deletion success rate

### Quality Metrics
1. Unit test coverage: 75-85%
2. Component test coverage: 75-85%
3. Integration test coverage: 30-35 tests
4. API test coverage: 25-30 tests
5. Smoke test coverage: 15-18 tests

## Acceptance Criteria

### AC-1: Secret Creation
- Given valid secret data
- When user creates a secret
- Then secret is encrypted and stored
- And access log is created
- And event is published

### AC-2: Secret Access
- Given user has access to secret
- When user requests secret with decrypt=true
- Then decrypted value is returned
- And access count is incremented
- And access log is created

### AC-3: Access Denied
- Given user has no access to secret
- When user requests secret
- Then 403 Forbidden is returned
- And access attempt is logged with failure

### AC-4: Secret Sharing
- Given user owns a secret
- When user shares with another user
- Then share record is created
- And recipient can access secret

### AC-5: GDPR Deletion
- Given user.deleted event is received
- When handler processes event
- Then all user vault data is deleted
- And compliance is logged

## Release Criteria

1. All functional requirements implemented
2. All acceptance criteria passing
3. Security review completed
4. Performance benchmarks met
5. Documentation complete
6. Test coverage targets met
