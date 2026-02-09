# Vault Service Logic Contract

## Overview

This document defines the behavioral contracts for vault_service operations. These contracts specify invariants, preconditions, postconditions, and expected behaviors that must be verified through testing.

## Service Methods

### create_secret

Creates a new encrypted secret in the vault.

#### Signature
```python
async def create_secret(
    user_id: str,
    request: VaultCreateRequest,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[bool, Optional[VaultItemResponse], str]
```

#### Preconditions
- `user_id` must be a non-empty string
- `request.name` must be 1-255 characters
- `request.secret_value` must be non-empty
- `request.secret_type` must be a valid SecretType enum value
- `request.tags` must have at most 10 items
- `request.rotation_days` must be 1-365 if provided

#### Postconditions
- On success:
  - Returns `(True, VaultItemResponse, "Secret created successfully")`
  - Secret is encrypted with AES-256-GCM
  - Vault item is persisted with unique vault_id
  - Access log is created with action=CREATE
  - vault.secret.created event is published
  - If blockchain_verify=True and blockchain enabled, blockchain_reference is set
- On failure:
  - Returns `(False, None, error_message)`
  - Access log is created with success=False

#### Invariants
- Encrypted value is never stored in plaintext
- Encryption metadata (dek_encrypted, kek_salt, nonce) is stored in metadata
- Version starts at 1
- access_count starts at 0
- is_active defaults to True

---

### get_secret

Retrieves and optionally decrypts a secret.

#### Signature
```python
async def get_secret(
    vault_id: str,
    user_id: str,
    decrypt: bool = True,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[bool, Optional[VaultSecretResponse], str]
```

#### Preconditions
- `vault_id` must exist
- User must have access (owner or shared)
- Secret must be active
- Secret must not be expired

#### Postconditions
- On success with decrypt=True:
  - Returns decrypted secret_value
  - access_count is incremented
  - Access log is created with action=READ, success=True
  - vault.secret.accessed event is published
  - If blockchain_reference exists, blockchain_verified is set
- On success with decrypt=False:
  - Returns "[ENCRYPTED]" as secret_value
- On access denied:
  - Returns `(False, None, "Access denied")`
  - Access log is created with success=False
- On not found:
  - Returns `(False, None, "Secret not found")`

#### Invariants
- Access count monotonically increases
- last_accessed_at is updated on successful read

---

### update_secret

Updates a secret's metadata or value.

#### Signature
```python
async def update_secret(
    vault_id: str,
    user_id: str,
    request: VaultUpdateRequest,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[bool, Optional[VaultItemResponse], str]
```

#### Preconditions
- `vault_id` must exist
- User must have write permission (owner or read_write share)
- Secret must be active

#### Postconditions
- On success:
  - Returns updated VaultItemResponse
  - updated_at is set to current time
  - If secret_value changed, version is incremented
  - Access log is created with action=UPDATE
  - vault.secret.updated event is published
- On access denied:
  - Returns `(False, None, "Access denied")`

#### Invariants
- Version only increases when secret_value changes
- Existing metadata is merged with new metadata
- Encryption metadata is preserved unless secret_value changes

---

### delete_secret

Soft-deletes a secret.

#### Signature
```python
async def delete_secret(
    vault_id: str,
    user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[bool, str]
```

#### Preconditions
- `vault_id` must exist
- User must be the owner

#### Postconditions
- On success:
  - is_active is set to False
  - Access log is created with action=DELETE
  - vault.secret.deleted event is published
- On access denied:
  - Returns `(False, "Access denied")`

#### Invariants
- Soft delete preserves data (no physical deletion)
- Audit history is maintained

---

### list_secrets

Lists user's secrets with filtering.

#### Signature
```python
async def list_secrets(
    user_id: str,
    secret_type: Optional[SecretType] = None,
    tags: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[bool, Optional[VaultListResponse], str]
```

#### Preconditions
- `page` >= 1
- `page_size` 1-200

#### Postconditions
- Returns only active secrets owned by user
- Results are ordered by created_at DESC
- Pagination is applied correctly

#### Invariants
- Never returns secrets of other users
- Never returns inactive secrets

---

### share_secret

Shares a secret with another user or organization.

#### Signature
```python
async def share_secret(
    vault_id: str,
    owner_user_id: str,
    request: VaultShareRequest,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[bool, Optional[VaultShareResponse], str]
```

#### Preconditions
- `vault_id` must exist
- User must be the owner
- Either shared_with_user_id or shared_with_org_id must be provided

#### Postconditions
- On success:
  - Share record is created
  - Access log is created with action=SHARE
  - vault.secret.shared event is published
  - Shared user can access secret with permission_level
- On failure:
  - Returns `(False, None, error_message)`

#### Invariants
- Only owner can create shares
- Permission level is enforced on access

---

### get_shared_secrets

Gets secrets shared with a user.

#### Signature
```python
async def get_shared_secrets(
    user_id: str
) -> Tuple[bool, List[VaultShareResponse], str]
```

#### Postconditions
- Returns only active shares where shared_with_user_id matches
- Excludes expired shares

---

### rotate_secret

Rotates a secret with new value.

#### Signature
```python
async def rotate_secret(
    vault_id: str,
    user_id: str,
    new_secret_value: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[bool, Optional[VaultItemResponse], str]
```

#### Preconditions
- `vault_id` must exist
- User must have write permission
- `new_secret_value` must be non-empty

#### Postconditions
- On success:
  - Secret is re-encrypted with new DEK
  - Version is incremented
  - vault.secret.rotated event is published

#### Invariants
- New encryption key is generated
- Old encrypted value is overwritten

---

### get_access_logs

Gets audit logs for vault operations.

#### Signature
```python
async def get_access_logs(
    user_id: str,
    vault_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
) -> Tuple[bool, List[VaultAccessLogResponse], str]
```

#### Postconditions
- Returns logs for user's secrets
- If vault_id provided, filters to that secret
- Results ordered by created_at DESC

---

### get_stats

Gets vault statistics for a user.

#### Signature
```python
async def get_stats(user_id: str) -> Tuple[bool, VaultStatsResponse, str]
```

#### Postconditions
- Returns aggregate statistics for user's secrets
- Includes counts by type, provider, status

---

### test_credential

Tests if a credential is valid.

#### Signature
```python
async def test_credential(
    vault_id: str,
    user_id: str,
    test_endpoint: Optional[str] = None,
) -> Tuple[bool, VaultTestResponse, str]
```

#### Preconditions
- User must have access to secret

#### Postconditions
- Verifies secret can be decrypted
- Returns success=True if decryption succeeds

---

## Access Control Rules

### Permission Matrix

| Action | Owner | read_write | read |
|--------|-------|------------|------|
| create | N/A | N/A | N/A |
| get (decrypt) | Yes | Yes | Yes |
| get (metadata) | Yes | Yes | Yes |
| update (metadata) | Yes | Yes | No |
| update (secret_value) | Yes | Yes | No |
| delete | Yes | No | No |
| share | Yes | No | No |
| rotate | Yes | Yes | No |

### Access Check Logic

```python
def check_access(vault_id, user_id):
    # 1. Check ownership
    if item.user_id == user_id:
        return "owner"

    # 2. Check active shares
    for share in get_shares_for_vault(vault_id):
        if share.shared_with_user_id == user_id:
            if share.expires_at and share.expires_at < now:
                continue  # Expired
            return share.permission_level.value

    return None  # No access
```

---

## Encryption Contract

### Encryption Flow
1. Generate random DEK (AES-256 key)
2. Generate random nonce (96-bit)
3. Encrypt plaintext with AES-GCM(DEK, nonce)
4. Derive KEK from master_key + user_id + salt
5. Encrypt DEK with Fernet(KEK)
6. Store: encrypted_data, encrypted_DEK, salt, nonce

### Decryption Flow
1. Retrieve: encrypted_data, encrypted_DEK, salt, nonce
2. Derive KEK from master_key + user_id + salt
3. Decrypt DEK with Fernet(KEK)
4. Decrypt data with AES-GCM(DEK, nonce)

### Key Derivation
```python
KEK = PBKDF2(
    password=master_key + user_id,
    salt=salt,
    iterations=100000,
    algorithm=SHA256,
    length=32
)
```

---

## Event Contracts

### vault.secret.created
Triggered: After successful secret creation
Required fields: vault_id, user_id, secret_type, name, timestamp

### vault.secret.accessed
Triggered: After successful secret read
Required fields: vault_id, user_id, secret_type, decrypted, timestamp

### vault.secret.updated
Triggered: After successful secret update
Required fields: vault_id, user_id, secret_value_updated, metadata_updated, timestamp

### vault.secret.deleted
Triggered: After successful secret deletion
Required fields: vault_id, user_id, timestamp

### vault.secret.shared
Triggered: After successful share creation
Required fields: vault_id, owner_user_id, permission_level, timestamp

### vault.secret.rotated
Triggered: After successful secret rotation
Required fields: vault_id, user_id, new_version, timestamp

---

## Error Handling Contracts

### Expected Errors

| Scenario | HTTP Status | Message Pattern |
|----------|-------------|-----------------|
| Missing X-User-Id header | 401 | "User authentication required" |
| Access denied | 403 | "Access denied" |
| Secret not found | 404 | "Secret not found" or "not found" |
| Secret inactive | 400 | "Secret is inactive" |
| Secret expired | 400 | "Secret has expired" |
| Invalid request | 400/422 | Validation error details |
| Decryption failure | 400 | "Failed to decrypt secret" |
| Server error | 500 | "Failed to..." |

### Error Response Contract
```json
{
    "detail": "Error message"
}
```

---

## GDPR Contract

### handle_user_deleted

When `user.deleted` event is received:

1. Delete all vault_items where user_id matches
2. Delete all vault_shares where owner_user_id matches
3. Delete all vault_shares where shared_with_user_id matches
4. Delete all vault_access_logs where user_id matches
5. Log total deleted count

Invariant: No user data remains after GDPR deletion
