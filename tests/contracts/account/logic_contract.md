# Account Service Logic Contract

**Business Rules and Specifications for Account Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for account service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Data Consistency Rules](#data-consistency-rules)
5. [Integration Contracts](#integration-contracts)
6. [Error Handling Contracts](#error-handling-contracts)
7. [Performance SLAs](#performance-slas)

---

## Business Rules

### Account Creation Rules

### BR-ACC-001: User ID Uniqueness
**Given**: Valid account ensure request with user_id
**When**: Account is created via ensure_account
**Then**:
- User ID must be unique across all accounts
- Duplicate user_id returns existing account (idempotent)
- No error thrown if user_id already exists
- Second call returns `was_created=False`

**Validation Rules**:
- `user_id`: Required, non-empty string
- Must not contain only whitespace
- No format restrictions (determined by auth_service)

**Edge Cases**:
- Empty user_id → **AccountValidationError**
- Whitespace-only user_id → **AccountValidationError**
- Duplicate user_id → Returns existing account

---

### BR-ACC-002: Email Uniqueness
**Given**: Valid account ensure request with email
**When**: Account is created
**Then**:
- Email must be unique across all accounts
- Email already used by different user_id → **AccountValidationError** (DuplicateEntryError)
- Same user_id with same email → Returns existing account
- Email comparison is case-sensitive in database

**Validation Rules**:
- `email`: Required, valid email format
- Format: `^[^\s@]+@[^\s@]+\.[^\s@]+$`
- No whitespace characters allowed
- Must have @ symbol and domain

**Edge Cases**:
- Empty email → **AccountValidationError**
- Email without @ → **AccountValidationError**
- Email with spaces → **AccountValidationError**
- Email already used → **AccountValidationError** (wrapped DuplicateEntryError)

---

### BR-ACC-003: Email Format Validation
**Given**: Email field in any account request
**When**: Email is validated
**Then**:
- Must match regex pattern: `^[^\s@]+@[^\s@]+\.[^\s@]+$`
- No whitespace characters anywhere in email
- Must have exactly one @ symbol
- Must have domain with at least one dot

**Validation Rules**:
- Applied on account creation
- Applied on profile update
- Case-sensitive storage (no normalization)

**Edge Cases**:
- `user@domain` (no TLD) → **AccountValidationError**
- `userdomain.com` (no @) → **AccountValidationError**
- `user @domain.com` (space before @) → **AccountValidationError**
- `user@ domain.com` (space after @) → **AccountValidationError**

---

### BR-ACC-004: Name Validation
**Given**: Name field in account request
**When**: Name is validated
**Then**:
- Must be non-empty after stripping whitespace
- Length: 1-100 characters (enforced in AccountUpdateRequest)
- Empty string after strip → **AccountValidationError**

**Validation Rules**:
- `name`: Required on creation
- Cannot be empty or whitespace-only
- No maximum length on creation (repository handles)
- Update: min_length=1, max_length=100

**Edge Cases**:
- Empty name on creation → **AccountValidationError**
- Whitespace-only name → **AccountValidationError**
- Name with spaces (valid) → Accepted
- Name > 100 chars on update → **422 Validation Error** (Pydantic)

---

### BR-ACC-005: Default Values on Creation
**Given**: New account creation via ensure_account
**When**: Account is created
**Then**:
- `is_active` = `true` (always)
- `preferences` = `{}` (empty dict)
- `created_at` = current timestamp (UTC)
- `updated_at` = current timestamp (UTC)

**Default Values**:
```python
{
    "is_active": True,
    "preferences": {},
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc)
}
```

---

### BR-ACC-006: Idempotent Ensure Behavior
**Given**: Multiple calls to ensure_account with same user_id
**When**: ensure_account called repeatedly
**Then**:
- First call: Creates account, returns `was_created=True`
- Subsequent calls: Returns existing account, `was_created=False`
- No error thrown
- No duplicate records created
- Account data remains unchanged (no overwrite)

**Implementation**:
- Check existing account by user_id first
- Return immediately if found
- Only create if not exists

---

### BR-ACC-007: Concurrent Creation Handling
**Given**: Multiple concurrent ensure_account calls with same user_id
**When**: Calls execute simultaneously
**Then**:
- Only one account created
- Database primary key constraint prevents duplicates
- Other calls return existing account
- No race condition issues

**Solution**: Database-level uniqueness constraint on user_id

---

### Profile Update Rules

### BR-PRO-001: Email Uniqueness on Update
**Given**: Account profile update with new email
**When**: Email is changed via update_account_profile
**Then**:
- New email must not exist for different user
- Email already used by different user → **UserNotFoundError**
- Same user updating to same email → Allowed (no-op)

**Validation Rules**:
- Check email uniqueness before update
- Email format validation applied
- Database constraint enforces uniqueness

---

### BR-PRO-002: Name Validation on Update
**Given**: Account profile update with new name
**When**: Name is updated
**Then**:
- Name cannot be empty string
- Whitespace-only name → **AccountValidationError**
- `None` value → Keeps existing name (no update)

**Validation Rules**:
- Only validate if name is provided (not None)
- Must pass `name.strip()` check

---

### BR-PRO-003: Field Filtering
**Given**: Account profile update request
**When**: Update is applied
**Then**:
- Only allowed fields are updated: `name`, `email`
- All other fields in update_data are filtered out
- Preferences updated via separate endpoint
- Subscription fields not allowed (managed by subscription_service)

**Allowed Fields**:
- `name`: User display name
- `email`: User email address

**Filtered Fields** (ignored):
- `user_id`: Immutable
- `is_active`: Updated via status change endpoint
- `created_at`: Immutable
- `subscription_plan`: Managed by subscription_service

---

### BR-PRO-004: Updated_at Timestamp Management
**Given**: Any account update operation
**When**: Update is saved to database
**Then**:
- `updated_at` automatically set to current UTC timestamp
- Happens for: profile updates, preference updates, status changes
- Always uses `datetime.now(timezone.utc)`

**Implementation**:
```python
updated_at = datetime.now(tz=timezone.utc)
```

---

### BR-PRO-005: Empty Value Rejection
**Given**: Account update with empty values
**When**: update_account_profile called
**Then**:
- Empty name string → **AccountValidationError**
- Empty email string → **AccountValidationError**
- `None` values → Field not updated (filtered out)

**Behavior**:
- Empty string ≠ None
- Empty strings are invalid
- None means "don't update this field"

---

### BR-PRO-006: Updated Fields Tracking
**Given**: Profile update succeeds
**When**: user.profile_updated event is published
**Then**:
- Event includes `updated_fields` list
- Contains only fields that were actually updated
- Example: `["name", "email"]`
- Used for audit trail and downstream subscribers

**Event Data**:
```json
{
  "user_id": "user_123",
  "email": "new@example.com",
  "name": "New Name",
  "updated_fields": ["name", "email"],
  "updated_at": "2025-12-12T10:00:00Z"
}
```

---

### Preferences Rules

### BR-PRF-001: JSONB Structure Validation
**Given**: Account preferences update
**When**: Preferences are saved
**Then**:
- Must be valid JSON object (dict)
- Stored as JSONB in PostgreSQL
- No schema validation (flexible structure)
- Empty dict `{}` is valid

**Storage**:
- PostgreSQL JSONB column
- Automatic JSON validation by database
- Supports nested objects

---

### BR-PRF-002: Merge Strategy
**Given**: Preferences update via update_account_preferences
**When**: Preferences are updated
**Then**:
- Existing preferences are **merged**, not replaced
- New keys added to existing preferences
- Existing keys updated with new values
- Unspecified keys remain unchanged

**Merge Logic**:
```python
current_prefs = {"theme": "dark", "lang": "en"}
update_prefs = {"lang": "fr", "timezone": "UTC"}
result_prefs = {"theme": "dark", "lang": "fr", "timezone": "UTC"}
```

**Implementation**:
```python
updated_prefs = {**current_prefs, **preferences}
```

---

### BR-PRF-003: Invalid JSON Rejection
**Given**: Preferences field in update request
**When**: Invalid JSON structure provided
**Then**:
- Pydantic validation fails → **422 Validation Error**
- Must be dict type
- String values not auto-parsed

**Edge Cases**:
- String instead of dict → **422 Validation Error**
- List instead of dict → **422 Validation Error**
- Invalid JSON syntax → **422 Validation Error**

---

### BR-PRF-004: Size Limits
**Given**: Preferences JSONB field
**When**: Large preferences object stored
**Then**:
- No explicit size limit enforced by application
- PostgreSQL JSONB column handles size
- Recommended: Keep preferences < 10KB for performance

**Best Practice**:
- Store small config values only
- Don't store large binary data
- Don't store arrays of 1000+ items

---

### BR-PRF-005: Default Empty Object
**Given**: New account creation
**When**: No preferences provided
**Then**:
- Preferences default to `{}`
- Never null/None
- Always valid JSON object

**Default**:
```python
preferences: Dict[str, Any] = Field(default_factory=dict)
```

---

### Account Status Rules

### BR-STS-001: Admin-Only Status Changes
**Given**: Account status change request
**When**: Status is changed via change_account_status
**Then**:
- Only admin/system can change status
- Regular users cannot deactivate accounts
- Authorization enforced at API layer (not shown in business logic)

**Operations**:
- `activate_account(user_id)` → Sets `is_active=True`
- `deactivate_account(user_id)` → Sets `is_active=False`

---

### BR-STS-002: Soft Delete Behavior
**Given**: Account deletion request
**When**: delete_account is called
**Then**:
- Account is NOT removed from database
- `is_active` set to `False` (soft delete)
- Account data preserved for audit/recovery
- User cannot login but data remains

**Implementation**:
```python
async def delete_account(self, user_id: str) -> bool:
    return await self.deactivate_account(user_id)
```

---

### BR-STS-003: Reactivation Allowed
**Given**: Deactivated account
**When**: activate_account is called
**Then**:
- `is_active` set back to `True`
- Account fully restored
- User can login again
- All data intact

**Valid Transitions**:
- Inactive → Active (reactivation)
- Active → Inactive (deactivation)
- Active → Active (no-op, success)
- Inactive → Inactive (no-op, success)

---

### BR-STS-004: Reason Tracking
**Given**: Status change operation
**When**: Status is changed
**Then**:
- Optional `reason` field captured
- Included in user.status_changed event
- Used for audit trail
- Not stored in database (only in event)

**Event Data**:
```json
{
  "user_id": "user_123",
  "is_active": false,
  "reason": "Suspected fraudulent activity",
  "changed_by": "admin"
}
```

---

### BR-STS-005: Event Publishing for Status Changes
**Given**: Status change succeeds
**When**: activate_account or deactivate_account completes
**Then**:
- Event `user.status_changed` published to NATS
- Event includes: user_id, is_active, email, reason, changed_by
- Event failure logged but doesn't block status change
- Subject: `account_service.user.status_changed`

---

### BR-STS-006: Inactive Account Query Exclusion
**Given**: Account query operations
**When**: get_account_by_id or get_account_by_email called
**Then**:
- Only returns active accounts (`is_active=TRUE`)
- Inactive accounts not returned
- Special method `get_account_by_id_include_inactive` for admin queries

**SQL Filter**:
```sql
WHERE is_active = TRUE
```

**Exception**: `get_account_by_id_include_inactive` returns all accounts

---

### Search & Query Rules

### BR-QRY-001: Default Active-Only Filtering
**Given**: Account search or list operation
**When**: No `is_active` filter specified
**Then**:
- Only active accounts returned
- Inactive accounts excluded by default
- Must explicitly request inactive with `include_inactive=True`

**Queries Affected**:
- `get_account_by_id`
- `get_account_by_email`
- `search_accounts` (unless `include_inactive=True`)

---

### BR-QRY-002: ILIKE Case-Insensitive Search
**Given**: Account search with query string
**When**: search_accounts or list_accounts called
**Then**:
- Uses PostgreSQL `ILIKE` operator
- Case-insensitive matching
- Searches both `name` and `email` fields
- Pattern: `%query%` (substring match)

**SQL Example**:
```sql
WHERE (name ILIKE '%john%' OR email ILIKE '%john%')
```

---

### BR-QRY-003: Name and Email Search Scope
**Given**: Search query parameter
**When**: Searching accounts
**Then**:
- Searches in `name` field
- Searches in `email` field
- Returns account if either field matches
- Logical OR between fields

**Example**:
- Query: "john"
- Matches: name="John Doe", email="john@example.com", name="Jane Smith" + email="john.smith@test.com"

---

### BR-QRY-004: Pagination Max Limit
**Given**: List accounts request with pagination
**When**: page_size specified
**Then**:
- Maximum page_size: 100 (enforced by Pydantic)
- Minimum page_size: 1
- Default page_size: 50
- Page numbers start at 1 (not 0)

**Validation**:
```python
page: int = Field(1, ge=1)
page_size: int = Field(50, ge=1, le=100)
```

---

### BR-QRY-005: Ordering by Created Date
**Given**: List or search accounts
**When**: Results are returned
**Then**:
- Ordered by `created_at DESC`
- Newest accounts first
- Consistent ordering for pagination

**SQL**:
```sql
ORDER BY created_at DESC
```

---

### BR-QRY-006: Email Lookup Exact Match
**Given**: Email lookup via get_account_by_email
**When**: Email is queried
**Then**:
- Exact match only (not ILIKE)
- Case-sensitive match
- Returns single account or None
- Does not use pattern matching

**SQL**:
```sql
WHERE email = $1 AND is_active = TRUE
```

---

### Event Publishing Rules

### BR-EVT-001: All Mutations Publish Events
**Given**: Any account mutation operation
**When**: Operation succeeds
**Then**:
- Event published to NATS
- Event type matches operation
- Event contains full context data

**Events Published**:
- `user.created` → After ensure_account (only if new)
- `user.profile_updated` → After update_account_profile
- `user.status_changed` → After activate/deactivate
- `user.deleted` → After delete_account

---

### BR-EVT-002: Event Failures Don't Block Operations
**Given**: Account operation succeeds
**When**: Event publishing fails
**Then**:
- Operation completes successfully
- Error logged but not raised
- Response returned to client
- Event failure doesn't rollback transaction

**Implementation**:
```python
try:
    await event_bus.publish_event(event)
except Exception as e:
    logger.error(f"Failed to publish event: {e}")
    # Don't raise - event publishing is best-effort
```

---

### BR-EVT-003: ISO 8601 Timestamps
**Given**: Event published
**When**: Event data includes timestamps
**Then**:
- All timestamps in ISO 8601 format
- UTC timezone
- Generated by `datetime.utcnow()` or `datetime.now(timezone.utc)`

**Format**: `2025-12-12T10:00:00Z`

---

### BR-EVT-004: user.created Published Once Only
**Given**: Multiple ensure_account calls for same user_id
**When**: First call creates account
**Then**:
- `user.created` event published once
- Subsequent calls don't publish event
- Detection: Check if `was_created` flag is True
- Detection: `(now - created_at) < 60 seconds`

**Logic**:
```python
was_created = (
    user.created_at and
    (datetime.now(timezone.utc) - user.created_at).total_seconds() < 60
)
if was_created and self.event_bus:
    await publish_user_created(...)
```

---

### BR-EVT-005: Updated Fields List in profile_updated
**Given**: Profile update succeeds
**When**: user.profile_updated event published
**Then**:
- Event includes `updated_fields` array
- Contains keys from update_data dict
- Example: `["name", "email"]` or `["name"]`
- Used for selective cache invalidation

**Event Structure**:
```json
{
  "event_type": "USER_PROFILE_UPDATED",
  "source": "account_service",
  "data": {
    "user_id": "user_123",
    "updated_fields": ["name", "email"]
  }
}
```

---

## State Machines

### Account Lifecycle State Machine

```
┌─────────┐
│   NEW   │ Account creation initiated
└────┬────┘
     │
     ▼
┌─────────┐
│ ACTIVE  │ Account active and operational
└────┬────┘
     │
     ├────► INACTIVE  (deactivated by admin/system)
     │
     └────► INACTIVE  (deleted by user - soft delete)

From INACTIVE:
     │
     └────► ACTIVE    (reactivated by admin)
```

**States**:
- **NEW**: Temporary state during account creation (not persisted)
- **ACTIVE**: Account is active, `is_active=true`
- **INACTIVE**: Account is deactivated or soft-deleted, `is_active=false`

**Valid Transitions**:
- `NEW` → `ACTIVE` (account creation)
- `ACTIVE` → `INACTIVE` (deactivation/deletion)
- `INACTIVE` → `ACTIVE` (reactivation)
- `ACTIVE` → `ACTIVE` (update operations - no state change)

**Invalid Transitions**: None - all states are reachable

**Transition Triggers**:
- `ensure_account()` → NEW → ACTIVE
- `deactivate_account()` → ACTIVE → INACTIVE
- `delete_account()` → ACTIVE → INACTIVE (soft delete)
- `activate_account()` → INACTIVE → ACTIVE

---

### Email Update State Machine

```
┌──────────────┐
│CURRENT EMAIL │ Existing email in account
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VALIDATION   │ New email validated (format, uniqueness)
└──────┬───────┘
       │
       ├────► REJECTED (duplicate email)
       │
       ├────► REJECTED (invalid format)
       │
       └────► NEW EMAIL (validation passed, email updated)
```

**States**:
- **CURRENT_EMAIL**: Existing verified email
- **VALIDATION**: New email being validated
- **REJECTED**: Validation failed
- **NEW_EMAIL**: Email successfully updated

**Validation Steps**:
1. Format validation (regex pattern)
2. Uniqueness check (not used by other user)
3. Update database
4. Publish event

**Rejection Reasons**:
- Email format invalid → **AccountValidationError**
- Email already exists → **AccountValidationError** (DuplicateEntryError)

---

## Edge Cases

### Idempotency Edge Cases

### EC-001: Multiple Concurrent Ensure Calls
**Scenario**: Two requests call ensure_account with same user_id simultaneously
**Expected**:
- Only one account created in database
- Both requests return success
- One gets `was_created=True`, other gets `was_created=False`
- No duplicate key violation errors

**Solution**:
- Database primary key constraint on user_id
- First call creates, second call retrieves existing
- `ensure_account_exists` checks before creating

---

### EC-002: Ensure Called After Account Created
**Scenario**: User account already exists, ensure_account called again
**Expected**:
- Returns existing account
- `was_created=False`
- No changes to existing data
- No event published

**Detection**:
```python
existing_user = await self.get_account_by_id(user_id)
if existing_user:
    return existing_user
```

---

### EC-003: Email Already Used by Different User
**Scenario**: ensure_account called with email that exists for different user_id
**Expected**:
- **AccountValidationError** raised
- Wrapped **DuplicateEntryError**
- No account created
- Error message: "Email {email} already exists for different user"

**Implementation**:
```python
email_user = await self.get_account_by_email(email)
if email_user:
    raise DuplicateEntryException(f"Email {email} already exists for different user")
```

---

### Validation Edge Cases

### EC-004: Empty String Email
**Scenario**: Account creation with email=""
**Expected**:
- **AccountValidationError** raised
- Error message: "email is required"
- No account created

**Validation**:
```python
if not request.email or not request.email.strip():
    raise AccountValidationError("email is required")
```

---

### EC-005: Email with Invalid Format
**Scenario**: Account creation with email="notanemail"
**Expected**:
- **AccountValidationError** raised
- Error message: "Invalid email format"
- Rejected by regex pattern

**Invalid Examples**:
- `notanemail` (no @)
- `user@domain` (no TLD)
- `user @domain.com` (space)
- `@domain.com` (no local part)

---

### EC-006: Name with Only Whitespace
**Scenario**: Account creation or update with name="   "
**Expected**:
- **AccountValidationError** raised
- Error message: "name is required" or "name cannot be empty"
- No account created/updated

**Validation**:
```python
if not request.name or not request.name.strip():
    raise AccountValidationError("name is required")
```

---

### EC-007: Extremely Long Name
**Scenario**: Account update with name length > 100 characters
**Expected**:
- **422 Validation Error** from Pydantic
- Rejected before reaching business logic
- Error in response validation

**Validation** (AccountUpdateRequest):
```python
name: Optional[str] = Field(None, min_length=1, max_length=100)
```

---

### Preferences Edge Cases

### EC-008: Invalid JSON in Preferences
**Scenario**: Preferences field contains invalid JSON structure
**Expected**:
- **422 Validation Error** from Pydantic
- Rejected at request parsing stage
- Error message indicates validation failure

**Invalid Examples**:
- `preferences="not a dict"` (string instead of dict)
- `preferences=["array"]` (list instead of dict)

---

### EC-009: Nested Preferences Depth
**Scenario**: Preferences with deeply nested objects (10+ levels)
**Expected**:
- Accepted by application (no depth limit)
- PostgreSQL JSONB handles storage
- Performance may degrade with extreme nesting
- Recommended: Keep nesting < 5 levels

**Example**:
```json
{
  "level1": {
    "level2": {
      "level3": {
        "value": "deep"
      }
    }
  }
}
```

---

### EC-010: Large Preferences Object
**Scenario**: Preferences object > 10KB
**Expected**:
- Accepted (no size validation)
- PostgreSQL stores up to 1GB JSONB
- Warning: Performance impact on queries
- Best practice: Keep < 10KB

---

### Status Edge Cases

### EC-011: Deactivate Already Inactive Account
**Scenario**: deactivate_account called on account with is_active=false
**Expected**:
- Operation succeeds (returns True)
- No state change
- `updated_at` timestamp updated
- Event published (idempotent operation)

**SQL**:
```sql
UPDATE account.users SET is_active = FALSE, updated_at = $1 WHERE user_id = $2
```
(Succeeds even if already FALSE)

---

### EC-012: Activate Already Active Account
**Scenario**: activate_account called on account with is_active=true
**Expected**:
- Operation succeeds (returns True)
- No state change
- `updated_at` timestamp updated
- Event published

**Behavior**: Same as EC-011, idempotent operations

---

## Data Consistency Rules

### Transaction Boundaries

**Rule**: Each repository method operates in its own transaction
- `ensure_account_exists`: Single transaction (create account)
- `update_account_profile`: Single transaction (update + timestamp)
- `update_account_preferences`: Single transaction (merge + update)
- No cross-service transactions

**Implementation**:
```python
async with self.db:
    await self.db.execute(...)
```

---

### Concurrent Update Handling

**Rule**: Last write wins (no optimistic locking)
- No version tracking on User model
- Concurrent updates to different fields: Both succeed
- Concurrent updates to same field: Last update wins
- No conflict detection

**Edge Case**: Two concurrent name updates
- Request A: name="Alice"
- Request B: name="Bob"
- Result: Whichever commits last (non-deterministic)

---

### Updated_at Timestamp Precision

**Rule**: Timestamps use UTC timezone with microsecond precision
- Format: `datetime.now(timezone.utc)`
- Stored as PostgreSQL TIMESTAMP WITH TIME ZONE
- Precision: microseconds (6 decimal places)

**Consistency**:
- All timestamps in UTC
- Created_at never changes after creation
- Updated_at changes on every update

---

### Soft Delete Data Preservation

**Rule**: Soft deleted accounts preserve all data
- No fields cleared on deletion
- `is_active=False` is only change
- Email remains (prevents reuse)
- Preferences preserved
- Can be fully restored via activation

**Recovery**:
```python
await account_service.change_account_status(
    user_id="user_123",
    request=AccountStatusChangeRequest(is_active=True, reason="Restored by admin")
)
```

---

## Integration Contracts

### PostgreSQL gRPC Service

**Expectations**:
- Service name: `postgres_grpc_service`
- Default host: `isa-postgres-grpc`
- Default port: `50061`
- Protocol: gRPC with AsyncPostgresClient
- Schema: `account`
- Table: `account.users`

**Connection**:
```python
self.db = AsyncPostgresClient(host=host, port=port, user_id='account_service')
```

**Query Format**:
- Parameterized queries with `$1`, `$2`, etc.
- JSONB support for preferences field
- Async context manager for connection pooling

---

### NATS Event Publishing

**Expectations**:
- Event bus provided via dependency injection
- Events published asynchronously
- Event failures logged but don't block operations
- Subject format: `account_service.{event_type}`

**Event Types**:
- `USER_CREATED` → `account_service.user.created`
- `USER_PROFILE_UPDATED` → `account_service.user.profile_updated`
- `USER_UPDATED` → `account_service.user.status_changed`
- `USER_DELETED` → `account_service.user.deleted`

**Event Structure**:
```python
Event(
    event_type=EventType.USER_CREATED,
    source=ServiceSource.ACCOUNT_SERVICE,
    data={...}
)
```

---

### Consul Service Discovery

**Expectations**:
- Service registered at startup
- Service name: `account_service`
- Health check endpoint: `/health`
- Discovers `postgres_grpc_service` via Consul

**Configuration**:
```python
host, port = config.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061
)
```

---

### Subscription Service Client (Deprecated)

**Status**: Subscription data moved to subscription_service
- No subscription fields in User model
- subscription_client used only for initial subscription creation
- Query subscription data from subscription_service directly

**Legacy Usage**:
```python
# Only used in ensure_account for initial subscription creation
sub_result = await self.subscription_client.get_or_create_subscription(
    user_id=request.user_id,
    tier_code="free"
)
```

---

## Error Handling Contracts

### AccountNotFoundError

**When Raised**:
- `get_account_profile`: User ID not found
- `update_account_profile`: User ID not found (wrapped from UserNotFoundError)

**HTTP Status**: 404 Not Found

**Response**:
```json
{
  "detail": "Account not found: user_123"
}
```

---

### AccountValidationError

**When Raised**:
- Email format invalid
- Name is empty or whitespace-only
- User ID is empty
- Email already exists (wrapped DuplicateEntryError)

**HTTP Status**: 400 Bad Request

**Response Examples**:
```json
{"detail": "email is required"}
{"detail": "Invalid email format"}
{"detail": "name cannot be empty"}
{"detail": "Account with email already exists: user@example.com"}
```

---

### DuplicateEntryError

**When Raised**:
- Email already exists for different user
- Raised from repository layer
- Wrapped in AccountValidationError at service layer

**HTTP Status**: 400 Bad Request (via AccountValidationError)

**Source**: Repository layer (database constraint violation)

---

### AccountServiceError

**When Raised**:
- Unexpected errors during operations
- Database connection failures
- Generic operation failures

**HTTP Status**: 500 Internal Server Error

**Response**:
```json
{
  "detail": "Failed to ensure account: {error_message}"
}
```

---

### HTTP Status Code Mappings

| Error Type | HTTP Status | Example Scenario |
|------------|-------------|------------------|
| AccountNotFoundError | 404 | User ID not found |
| AccountValidationError | 400 | Invalid email format |
| DuplicateEntryError | 400 | Email already exists |
| AccountServiceError | 500 | Database connection failure |
| Pydantic ValidationError | 422 | Name too long (>100 chars) |

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| ensure_account | < 100ms | < 500ms |
| get_account_profile | < 50ms | < 200ms |
| update_account_profile | < 100ms | < 300ms |
| update_account_preferences | < 100ms | < 300ms |
| change_account_status | < 100ms | < 300ms |
| delete_account | < 100ms | < 300ms |
| list_accounts | < 150ms | < 500ms |
| search_accounts | < 150ms | < 500ms |
| get_account_by_email | < 50ms | < 200ms |

### Throughput Targets

- Account creation: 100 req/s
- Profile queries: 1000 req/s
- Profile updates: 200 req/s
- Search operations: 500 req/s

### Resource Limits

- Max concurrent connections: 100
- Max accounts per query: 100 (page_size limit)
- Max search results: 100
- Preferences size: 10KB recommended

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-XXX success scenarios)
- ✅ Validation errors (400, 422)
- ✅ Not found errors (404)
- ✅ State transitions (activation/deactivation)
- ✅ Event publishing (verify published)
- ✅ Edge cases (EC-XXX scenarios)
- ✅ Idempotency (multiple ensure_account calls)
- ✅ Concurrent operations (race conditions)
- ✅ Email uniqueness constraints
- ✅ Preferences merge behavior
- ✅ Soft delete and reactivation
- ✅ Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-12
**Owner**: Account Service Team
