# Document Service - Logic Contract

## Business Rules (50 rules)

### Document Creation Rules (BR-DOC-001 to BR-DOC-012)

**BR-DOC-001: Title Required**
- **Given**: A document creation request
- **When**: The title field is empty, null, or whitespace-only
- **Then**: System MUST reject with validation error
- **Error**: "Document title is required"

**BR-DOC-002: Title Length Limit**
- **Given**: A document creation request
- **When**: The title exceeds 500 characters
- **Then**: System MUST reject with validation error
- **Error**: "Title too long (max 500 characters)"

**BR-DOC-003: File ID Required**
- **Given**: A document creation request
- **When**: The file_id field is empty or null
- **Then**: System MUST reject with validation error
- **Error**: "file_id is required"

**BR-DOC-004: Valid Document Type Required**
- **Given**: A document creation request
- **When**: The doc_type is not one of: pdf, docx, pptx, xlsx, txt, markdown, html, json
- **Then**: System MUST reject with validation error
- **Error**: "Invalid document type"

**BR-DOC-005: Default Access Level**
- **Given**: A document creation request without access_level
- **When**: Document is created
- **Then**: access_level MUST default to PRIVATE

**BR-DOC-006: Default Chunking Strategy**
- **Given**: A document creation request without chunking_strategy
- **When**: Document is created
- **Then**: chunking_strategy MUST default to SEMANTIC

**BR-DOC-007: Unique Document ID Generation**
- **Given**: A document creation request
- **When**: Document is created
- **Then**: System MUST generate unique doc_id with format: doc_{hex12}
- **Example**: doc_a1b2c3d4e5f6

**BR-DOC-008: Initial Version Number**
- **Given**: A document creation request
- **When**: Document is created
- **Then**: version MUST be set to 1

**BR-DOC-009: Initial Latest Flag**
- **Given**: A document creation request
- **When**: Document is created
- **Then**: is_latest MUST be set to true

**BR-DOC-010: Initial Status**
- **Given**: A document creation request
- **When**: Document is created
- **Then**: status MUST be set to DRAFT

**BR-DOC-011: Collection Name Assignment**
- **Given**: A document creation request with user_id
- **When**: Document is created
- **Then**: collection_name MUST be set to "user_{user_id}"

**BR-DOC-012: Timestamp Recording**
- **Given**: A document creation request
- **When**: Document is created
- **Then**: created_at and updated_at MUST be set to current UTC timestamp

### Permission Rules (BR-PER-001 to BR-PER-012)

**BR-PER-001: Owner Always Has Access**
- **Given**: A document with user_id = X
- **When**: User X performs any operation
- **Then**: Operation MUST be allowed regardless of access_level

**BR-PER-002: Deny List Precedence**
- **Given**: A document with denied_users containing user X
- **When**: User X attempts to access the document
- **Then**: Access MUST be denied regardless of access_level or allowed_users
- **Error**: "Access denied to this document"

**BR-PER-003: Allowed Users Override**
- **Given**: A document with access_level = PRIVATE and allowed_users containing user X
- **When**: User X (not owner) attempts to access
- **Then**: Access MUST be allowed

**BR-PER-004: Private Access Enforcement**
- **Given**: A document with access_level = PRIVATE
- **When**: Non-owner user not in allowed_users attempts access
- **Then**: Access MUST be denied
- **Error**: "Access denied to this document"

**BR-PER-005: Public Access Enforcement**
- **Given**: A document with access_level = PUBLIC
- **When**: Any user attempts to access
- **Then**: Access MUST be allowed

**BR-PER-006: Team Access Enforcement**
- **Given**: A document with access_level = TEAM
- **When**: User attempts to access
- **Then**: Authorization service MUST verify team membership

**BR-PER-007: Organization Access Enforcement**
- **Given**: A document with access_level = ORGANIZATION
- **When**: User attempts to access
- **Then**: Authorization service MUST verify organization membership

**BR-PER-008: Permission Update Authorization**
- **Given**: A permission update request
- **When**: User is not the document owner
- **Then**: Request MUST be rejected with 403 Forbidden
- **Error**: "Only document owner can update permissions"

**BR-PER-009: Permission History Recording**
- **Given**: A permission update request
- **When**: Permissions are successfully updated
- **Then**: System MUST record history entry with old_state, new_state, changed_by, timestamp

**BR-PER-010: User List Deduplication**
- **Given**: A permission update adding duplicate users
- **When**: Permissions are updated
- **Then**: allowed_users MUST contain unique entries only

**BR-PER-011: Group List Deduplication**
- **Given**: A permission update adding duplicate groups
- **When**: Permissions are updated
- **Then**: allowed_groups MUST contain unique entries only

**BR-PER-012: Read Permission Required for Operations**
- **Given**: A document access request (get, list permissions, search)
- **When**: User does not have read permission
- **Then**: Request MUST be rejected with 403 Forbidden

### Query Rules (BR-QRY-001 to BR-QRY-008)

**BR-QRY-001: Query Text Required**
- **Given**: A RAG query or search request
- **When**: Query field is empty or whitespace-only
- **Then**: System MUST reject with validation error
- **Error**: "Query cannot be empty"

**BR-QRY-002: Permission Filtering Required**
- **Given**: A RAG query or search request
- **When**: Results are returned
- **Then**: Results MUST only include documents user has permission to access

**BR-QRY-003: Collection Scoping**
- **Given**: A RAG query request for user X
- **When**: Query is sent to Digital Analytics
- **Then**: collection_name MUST be set to "user_X"

**BR-QRY-004: Top K Limit for RAG**
- **Given**: A RAG query request
- **When**: top_k exceeds 50
- **Then**: System MUST reject with validation error
- **Error**: "top_k must be between 1 and 50"

**BR-QRY-005: Top K Limit for Search**
- **Given**: A search request
- **When**: top_k exceeds 100
- **Then**: System MUST reject with validation error
- **Error**: "top_k must be between 1 and 100"

**BR-QRY-006: Min Score Filtering**
- **Given**: A search request with min_score
- **When**: Results are filtered
- **Then**: Results with score < min_score MUST be excluded

**BR-QRY-007: Temperature Range**
- **Given**: A RAG query request
- **When**: temperature is outside [0.0, 2.0]
- **Then**: System MUST reject with validation error
- **Error**: "temperature must be between 0.0 and 2.0"

**BR-QRY-008: Max Tokens Range**
- **Given**: A RAG query request
- **When**: max_tokens is outside [50, 4000]
- **Then**: System MUST reject with validation error
- **Error**: "max_tokens must be between 50 and 4000"

### Update Rules (BR-UPD-001 to BR-UPD-008)

**BR-UPD-001: New File ID Required**
- **Given**: A document update request
- **When**: new_file_id is empty or null
- **Then**: System MUST reject with validation error
- **Error**: "new_file_id is required"

**BR-UPD-002: Version Increment**
- **Given**: A document at version N
- **When**: Document is updated
- **Then**: New version MUST be N+1

**BR-UPD-003: Latest Flag Transfer**
- **Given**: A document update request
- **When**: New version is created
- **Then**: New version MUST have is_latest=true, old version MUST have is_latest=false

**BR-UPD-004: Parent Version Link**
- **Given**: A document update creating version N+1
- **When**: New version is created
- **Then**: parent_version_id MUST reference the previous doc_id

**BR-UPD-005: Status During Update**
- **Given**: A document update request
- **When**: Update processing begins
- **Then**: Document status MUST be set to UPDATING

**BR-UPD-006: Status After Successful Update**
- **Given**: A document update that completes successfully
- **When**: Update finishes
- **Then**: New version status MUST be set to INDEXED

**BR-UPD-007: Status After Failed Update**
- **Given**: A document update that fails
- **When**: Update fails
- **Then**: Document status MUST be set to FAILED

**BR-UPD-008: Update Permission Check**
- **Given**: A document update request
- **When**: User is not the document owner
- **Then**: Request MUST be rejected with 403 Forbidden
- **Error**: "No permission to update document"

### Delete Rules (BR-DEL-001 to BR-DEL-006)

**BR-DEL-001: Soft Delete Default**
- **Given**: A delete request without permanent flag
- **When**: Document is deleted
- **Then**: Document status MUST be set to DELETED (soft delete)

**BR-DEL-002: Permanent Delete**
- **Given**: A delete request with permanent=true
- **When**: Document is deleted
- **Then**: Document record MUST be removed from database (hard delete)

**BR-DEL-003: Delete Permission Check**
- **Given**: A delete request
- **When**: User is not the document owner
- **Then**: Request MUST be rejected with 403 Forbidden
- **Error**: "Access denied to delete this document"

**BR-DEL-004: Delete Non-Existent Document**
- **Given**: A delete request for doc_id that doesn't exist
- **When**: Delete is attempted
- **Then**: Request MUST be rejected with 404 Not Found
- **Error**: "Document {doc_id} not found"

**BR-DEL-005: Delete Event Publishing**
- **Given**: A successful delete operation
- **When**: Delete completes
- **Then**: System MUST publish document.deleted event with {doc_id, user_id, permanent, timestamp}

**BR-DEL-006: Soft Deleted Document Access**
- **Given**: A document with status = DELETED
- **When**: User attempts to access
- **Then**: Document MUST NOT appear in list queries with default filters

### Statistics Rules (BR-STA-001 to BR-STA-004)

**BR-STA-001: User Scope**
- **Given**: A stats request for user X
- **When**: Statistics are calculated
- **Then**: Only documents owned by user X MUST be included

**BR-STA-002: Latest Version Only**
- **Given**: A stats request
- **When**: Statistics are calculated
- **Then**: Only documents with is_latest=true MUST be counted

**BR-STA-003: Organization Filter**
- **Given**: A stats request with organization_id
- **When**: Statistics are calculated
- **Then**: Only documents in that organization MUST be included

**BR-STA-004: Aggregate Consistency**
- **Given**: A stats response
- **When**: Response is returned
- **Then**: Sum of by_type values MUST equal total_documents

---

## State Machines (4 machines)

### Document Lifecycle State Machine

```
States:
- DRAFT: Document created, not yet indexed
- INDEXING: Document being indexed by Digital Analytics
- INDEXED: Document successfully indexed and searchable
- UPDATE_PENDING: Document marked for update
- UPDATING: Document being re-indexed
- ARCHIVED: Document archived (inactive)
- FAILED: Indexing/update failed
- DELETED: Soft deleted

Transitions:
DRAFT -> INDEXING (on indexing_start)
INDEXING -> INDEXED (on indexing_success)
INDEXING -> FAILED (on indexing_error)
INDEXED -> UPDATE_PENDING (on update_request)
INDEXED -> ARCHIVED (on archive_request)
INDEXED -> DELETED (on delete_request)
UPDATE_PENDING -> UPDATING (on update_start)
UPDATING -> INDEXED (on update_success)
UPDATING -> FAILED (on update_error)
FAILED -> INDEXING (on retry_indexing)
FAILED -> DELETED (on delete_request)
ARCHIVED -> INDEXED (on restore_request)
DELETED -> [terminal state]

Rules:
- Only INDEXED documents are searchable via RAG
- DELETED status is terminal for soft delete
- FAILED documents can be retried
- ARCHIVED documents can be restored
```

### Access Level State Machine

```
States:
- PRIVATE: Only owner access
- TEAM: Team member access
- ORGANIZATION: Organization member access
- PUBLIC: Anyone can access

Transitions:
PRIVATE -> TEAM (on set_team_access)
PRIVATE -> ORGANIZATION (on set_org_access)
PRIVATE -> PUBLIC (on set_public_access)
TEAM -> PRIVATE (on set_private_access)
TEAM -> ORGANIZATION (on set_org_access)
TEAM -> PUBLIC (on set_public_access)
ORGANIZATION -> PRIVATE (on set_private_access)
ORGANIZATION -> TEAM (on set_team_access)
ORGANIZATION -> PUBLIC (on set_public_access)
PUBLIC -> PRIVATE (on set_private_access)
PUBLIC -> TEAM (on set_team_access)
PUBLIC -> ORGANIZATION (on set_org_access)

Rules:
- Only document owner can change access level
- Transition is immediate and takes effect on next access check
- All transitions are bidirectional
- History recorded for all transitions
```

### Version State Machine

```
States:
- CURRENT: Latest version (is_latest=true)
- HISTORICAL: Previous version (is_latest=false)

Transitions:
CURRENT -> HISTORICAL (on new_version_created)
[no transition from HISTORICAL]

Rules:
- Only one version can be CURRENT at a time
- HISTORICAL versions are immutable
- CURRENT version can be updated
- Version numbers strictly increment
```

### Permission Check Flow State Machine

```
States:
- CHECK_OWNER: Verify if user is owner
- CHECK_DENIED: Check denied_users list
- CHECK_ALLOWED: Check allowed_users list
- CHECK_ACCESS_LEVEL: Evaluate access_level
- GRANTED: Access granted
- DENIED: Access denied

Transitions:
[START] -> CHECK_OWNER
CHECK_OWNER -> GRANTED (if is_owner)
CHECK_OWNER -> CHECK_DENIED (if not_owner)
CHECK_DENIED -> DENIED (if in_denied_list)
CHECK_DENIED -> CHECK_ALLOWED (if not_in_denied_list)
CHECK_ALLOWED -> GRANTED (if in_allowed_list)
CHECK_ALLOWED -> CHECK_ACCESS_LEVEL (if not_in_allowed_list)
CHECK_ACCESS_LEVEL -> GRANTED (if access_level_allows)
CHECK_ACCESS_LEVEL -> DENIED (if access_level_denies)

Rules:
- Owner check has highest priority
- Deny list takes precedence over allow list
- Allow list takes precedence over access_level
```

---

## Edge Cases (15 cases)

**EC-001: Empty Document Title with Spaces**
- **Input**: title = "   " (whitespace only)
- **Expected**: Validation error "Title cannot be empty or whitespace only"
- **Actual behavior**: Pydantic validator strips and rejects

**EC-002: Concurrent Version Updates**
- **Input**: Two simultaneous update requests for same document
- **Expected**: First completes, second fails with version conflict
- **Actual behavior**: Database handles with row locking

**EC-003: Delete During Indexing**
- **Input**: Delete request while document status = INDEXING
- **Expected**: Delete proceeds, indexing job should handle gracefully
- **Actual behavior**: Status set to DELETED, background job checks status

**EC-004: Permission Update After Delete**
- **Input**: Permission update request for DELETED document
- **Expected**: 404 Not Found (or treat as inaccessible)
- **Actual behavior**: Returns 404 Not Found

**EC-005: RAG Query on Empty Collection**
- **Input**: RAG query when user has no documents
- **Expected**: Empty response with no answer
- **Actual behavior**: Returns empty sources, generic no-result message

**EC-006: Self-Deny (Owner in Denied List)**
- **Input**: Owner adds themselves to denied_users
- **Expected**: Owner still has access (owner check has priority)
- **Actual behavior**: Owner access bypasses deny list

**EC-007: Duplicate User in Allowed List**
- **Input**: Permission update with same user_id twice in add_users
- **Expected**: List deduplicated, user appears once
- **Actual behavior**: Python set() deduplication applied

**EC-008: Very Large File Reference**
- **Input**: Document with file_size > 100MB
- **Expected**: Creation succeeds, indexing may take longer
- **Actual behavior**: No size limit enforced at document level

**EC-009: Unicode Characters in Title**
- **Input**: title = "机器学习指南 🤖"
- **Expected**: UTF-8 handling, stored correctly
- **Actual behavior**: PostgreSQL handles unicode, stored as-is

**EC-010: Maximum Tags**
- **Input**: Document with 100+ tags
- **Expected**: Stored successfully (no hard limit)
- **Actual behavior**: JSONB array accepts any length

**EC-011: Search with Zero Results**
- **Input**: Search query matching no documents
- **Expected**: Empty results array, total_count = 0
- **Actual behavior**: Returns empty list with latency_ms

**EC-012: Update to Same File ID**
- **Input**: Update request with new_file_id = current file_id
- **Expected**: New version created anyway (may be re-processed content)
- **Actual behavior**: Processes as normal update

**EC-013: Permission Update with Empty Lists**
- **Input**: Permission update with empty add_users, remove_users, etc.
- **Expected**: No changes made, response reflects current state
- **Actual behavior**: No-op update, returns current permissions

**EC-014: Query with Special Characters**
- **Input**: query = "What's the 'best' approach? (ML/AI)"
- **Expected**: Query processed, special chars handled
- **Actual behavior**: Digital Analytics handles query sanitization

**EC-015: Deleted User Documents**
- **Input**: User deletion event received
- **Expected**: All user's documents marked as deleted
- **Actual behavior**: Event handler processes cascade delete

---

## Data Consistency Rules

**DC-001: Document ID Uniqueness**
- All doc_id values MUST be unique across the system
- Format: doc_{hex12} ensures uniqueness via UUID

**DC-002: Version Ordering**
- Version numbers MUST strictly increment within a document lineage
- No gaps allowed in version sequence

**DC-003: Single Latest Version**
- Exactly one version per document lineage can have is_latest=true
- Query for documents defaults to is_latest=true filter

**DC-004: Collection Naming**
- Collection name MUST follow pattern: user_{user_id}
- Ensures data isolation between users

**DC-005: Permission List Consistency**
- denied_users, allowed_users, allowed_groups MUST be stored as JSON arrays
- Empty lists stored as []

**DC-006: Timestamp Consistency**
- All timestamps MUST be in UTC timezone
- created_at MUST never be modified after initial set
- updated_at MUST be updated on any modification

---

## Integration Contracts

### Storage Service Integration

- **Endpoint**: GET /api/v1/files/{file_id}/info
- **When**: Document creation, validating file exists
- **Payload**: `{file_id, user_id}`
- **Expected Response**: `{file_id, file_size, mime_type, ...}` or 404
- **Error Handling**: Log warning if unavailable, proceed with creation

### Digital Analytics Integration

- **Endpoint**: POST /api/v1/content/store
- **When**: Document indexing
- **Payload**: `{user_id, content, content_type, collection_name, metadata}`
- **Expected Response**: `{chunks_stored, point_ids}` or error
- **Error Handling**: Set document status to FAILED

### Authorization Service Integration

- **Endpoint**: POST /api/v1/permissions/check
- **When**: TEAM or ORGANIZATION access level check
- **Payload**: `{user_id, resource_type, resource_id, action}`
- **Expected Response**: `{allowed: bool}` or error
- **Error Handling**: Default to denied if service unavailable

### NATS Event Publishing

- **Subject Pattern**: `document.document.{event_type}`
- **Events**: created, updated, deleted, permission.updated
- **Payload Format**: `{doc_id, user_id, timestamp, ...event_specific}`
- **Error Handling**: Log error, continue operation

---

## Error Handling Contracts

### HTTP Error Codes

| Error | HTTP Code | Response Format |
|-------|-----------|-----------------|
| Document Not Found | 404 | `{"error": "Document {doc_id} not found", "status_code": 404}` |
| Permission Denied | 403 | `{"error": "Access denied to this document", "status_code": 403}` |
| Validation Error | 400 | `{"error": "Validation error message", "status_code": 400}` |
| Validation Error (Pydantic) | 422 | `{"detail": [...validation errors...]}` |
| Service Unavailable | 503 | `{"error": "Service not initialized", "status_code": 503}` |
| Internal Error | 500 | `{"error": "Internal server error", "status_code": 500}` |

### Exception Hierarchy

```
DocumentServiceError (base)
├── DocumentNotFoundError -> 404
├── DocumentValidationError -> 400
└── DocumentPermissionError -> 403
```

### Error Response Contract

```json
{
  "error": "Human-readable error message",
  "status_code": 400
}
```

---

## Performance Contracts

### Response Time Targets

| Operation | P95 Target | P99 Target |
|-----------|------------|------------|
| Health Check | 50ms | 100ms |
| Get Document | 100ms | 200ms |
| List Documents | 200ms | 500ms |
| Create Document | 500ms | 1000ms |
| RAG Query | 3000ms | 5000ms |
| Semantic Search | 1000ms | 2000ms |
| Permission Update | 200ms | 500ms |

### Pagination Limits

| Parameter | Min | Max | Default |
|-----------|-----|-----|---------|
| limit (list) | 1 | 100 | 50 |
| top_k (RAG) | 1 | 50 | 5 |
| top_k (search) | 1 | 100 | 10 |

---

**End of Logic Contract**
