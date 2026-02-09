# Document Service - Domain Context

## Overview

The Document Service is the **knowledge base management** layer of the isA platform. It enables users to store, organize, index, and query documents using RAG (Retrieval-Augmented Generation) technology with fine-grained access control.

**Port**: 8227

---

## Business Taxonomy

### Core Entities

- **KnowledgeDocument**: A document stored in the knowledge base for RAG indexing. Contains metadata, content reference, version information, and access permissions.

- **DocumentVersion**: A specific version of a document. The system maintains version history with parent-child relationships.

- **DocumentPermission**: Access control rules for a document, defining who can read, update, or delete it.

- **PermissionHistory**: Audit trail of permission changes for compliance and debugging.

- **DocumentChunk**: A segment of document content indexed for vector search (managed externally by Digital Analytics Service).

### Core Concepts

- **RAG (Retrieval-Augmented Generation)**: AI technique that combines document retrieval with generation to provide contextual answers from user's knowledge base.

- **Semantic Search**: Vector-based search that finds documents by meaning rather than exact keyword match.

- **Access Level**: Four-tier permission model (PRIVATE, TEAM, ORGANIZATION, PUBLIC) controlling document visibility.

- **Incremental Update**: Efficient document re-indexing that only processes changed content rather than full reindex.

- **Collection**: A Qdrant vector database collection scoped to a user for storing document embeddings.

### Document Types

- **PDF**: Portable Document Format files
- **DOCX**: Microsoft Word documents
- **PPTX**: Microsoft PowerPoint presentations
- **XLSX**: Microsoft Excel spreadsheets
- **TXT**: Plain text files
- **MARKDOWN**: Markdown formatted documents
- **HTML**: HTML web pages
- **JSON**: JSON structured data files

### Document Statuses

- **DRAFT**: Document created but not yet indexed
- **INDEXING**: Currently being indexed by Digital Analytics
- **INDEXED**: Successfully indexed and searchable
- **UPDATE_PENDING**: Pending incremental update
- **UPDATING**: Currently being updated
- **ARCHIVED**: Archived and not active
- **FAILED**: Indexing or update failed
- **DELETED**: Soft deleted

---

## Domain Scenarios

### Scenario 1: Document Upload and Indexing

**Trigger**: User uploads a document file via storage service

**Flow**:
1. User uploads file to storage_service, receives file_id
2. User calls document_service to create knowledge document
3. Document service validates request and creates document record
4. Document service triggers async indexing via Digital Analytics
5. Digital Analytics chunks document and creates vector embeddings
6. Document status updated to INDEXED when complete

**Outcome**: Document is searchable via RAG queries

**Events**:
- `document.created`

### Scenario 2: RAG Query with Permission Filtering

**Trigger**: User submits a query to the knowledge base

**Flow**:
1. User sends query to `/api/v1/documents/rag/query`
2. Service builds permission filter based on user's access rights
3. Query sent to Digital Analytics with user's collection
4. Results filtered by document permissions in PostgreSQL
5. Relevant answer generated from accessible documents

**Outcome**: User receives answer from their accessible documents

**Events**: None

### Scenario 3: Document Permission Update

**Trigger**: Document owner changes access permissions

**Flow**:
1. Owner calls PUT `/api/v1/documents/{doc_id}/permissions`
2. Service validates owner has admin permission
3. Permission changes applied to database record
4. Permission history recorded for audit
5. Event published for downstream consumers

**Outcome**: Document visibility changes take effect

**Events**:
- `document.permission.updated`

### Scenario 4: Incremental Document Update

**Trigger**: User updates document content

**Flow**:
1. User uploads new file version to storage_service
2. User calls PUT `/api/v1/documents/{doc_id}/update` with new_file_id
3. Service downloads new content
4. Service re-indexes via Digital Analytics
5. New document version created with incremented version number
6. Old version marked as not latest

**Outcome**: Document updated with new content, version history preserved

**Events**:
- `document.updated`

### Scenario 5: Document Deletion

**Trigger**: User deletes a document

**Flow**:
1. User calls DELETE `/api/v1/documents/{doc_id}`
2. Service validates user has delete permission
3. If soft delete: status changed to DELETED
4. If permanent: record removed from database
5. Digital Analytics notified to clean up vectors

**Outcome**: Document no longer accessible

**Events**:
- `document.deleted`

### Scenario 6: Semantic Search

**Trigger**: User searches for documents by meaning

**Flow**:
1. User calls POST `/api/v1/documents/search`
2. Service sends query to Digital Analytics
3. Vector similarity search performed
4. Results filtered by user permissions
5. Matching documents returned with relevance scores

**Outcome**: User finds semantically similar documents

**Events**: None

### Scenario 7: User Statistics

**Trigger**: User requests document usage statistics

**Flow**:
1. User calls GET `/api/v1/documents/stats`
2. Service aggregates user's document counts
3. Statistics returned by type and status

**Outcome**: User sees their document usage metrics

**Events**: None

### Scenario 8: Cross-Service Event Handling

**Trigger**: External service publishes relevant event (file deleted, user deleted)

**Flow**:
1. Document service receives event via NATS
2. Event handler identifies affected documents
3. Appropriate action taken (cascade delete, update status)

**Outcome**: Document state stays consistent with source systems

**Events**: None (consumer)

---

## Domain Events

### Published Events

1. **document.created** (EventType.DOCUMENT_CREATED)
   - **When**: After document record created and indexing started
   - **Data**: `{doc_id, user_id, title, doc_type, timestamp}`
   - **Consumers**: audit_service, notification_service

2. **document.updated** (EventType.DOCUMENT_UPDATED)
   - **When**: After document content updated and new version created
   - **Data**: `{doc_id, old_doc_id, version, user_id, timestamp}`
   - **Consumers**: audit_service, notification_service

3. **document.deleted** (EventType.DOCUMENT_DELETED)
   - **When**: After document deleted
   - **Data**: `{doc_id, user_id, permanent, timestamp}`
   - **Consumers**: audit_service, storage_service

4. **document.permission.updated** (EventType.DOCUMENT_PERMISSION_UPDATED)
   - **When**: After document permissions changed
   - **Data**: `{doc_id, user_id, access_level, timestamp}`
   - **Consumers**: audit_service, authorization_service

5. **document.indexed** (EventType.DOCUMENT_INDEXED)
   - **When**: After document successfully indexed
   - **Data**: `{doc_id, user_id, chunk_count, timestamp}`
   - **Consumers**: notification_service

6. **document.failed** (EventType.DOCUMENT_FAILED)
   - **When**: After document indexing fails
   - **Data**: `{doc_id, user_id, error, timestamp}`
   - **Consumers**: notification_service, audit_service

### Consumed Events

1. **file.deleted** (from storage_service)
   - **Action**: Mark associated document as deleted or remove reference

2. **user.deleted** (from account_service)
   - **Action**: Delete all user's documents

3. **organization.deleted** (from organization_service)
   - **Action**: Update organization_id references or delete org documents

---

## Core Concepts

### Concept 1: Access Control Model

Document access is controlled by a four-tier model:

```
PRIVATE      - Only document owner can access
TEAM         - Team members can access (via authorization_service)
ORGANIZATION - All organization members can access
PUBLIC       - Anyone can access
```

Additional fine-grained control:
- `allowed_users[]` - Explicit user whitelist
- `allowed_groups[]` - Explicit group whitelist
- `denied_users[]` - Explicit user blacklist (overrides other permissions)

Permission hierarchy: **denied_users > allowed_users > access_level**

### Concept 2: Document Versioning

Documents maintain version history:
- `version` - Integer version number (starts at 1)
- `parent_version_id` - Reference to previous version
- `is_latest` - Boolean flag for current version

When updating:
1. New version created with incremented version number
2. Old version's `is_latest` set to false
3. Parent-child relationship established

### Concept 3: Chunking Strategies

Documents are chunked for vector embedding:

- **FIXED_SIZE**: Split by character/token count
- **SEMANTIC**: Split by semantic boundaries (sentences, paragraphs)
- **PARAGRAPH**: Split by paragraph breaks
- **RECURSIVE**: Recursive character splitting with overlap

Default: SEMANTIC for best retrieval quality

### Concept 4: Update Strategies

Three strategies for document updates:

- **FULL**: Delete old vectors, re-index entire document
- **SMART**: Compare old/new, only update changed chunks
- **DIFF**: Precise diff-based update (most efficient)

All strategies currently use FULL approach via Digital Analytics.

### Concept 5: Collection Scoping

Each user has a dedicated Qdrant collection: `user_{user_id}`

This provides:
- Data isolation between users
- Efficient permission filtering
- Scalable multi-tenant architecture

---

## High-Level Business Rules (35 rules)

### Document Creation Rules (BR-DOC-001 to BR-DOC-010)

**BR-DOC-001: Title Required**
- Document title MUST be provided
- Title cannot be empty or whitespace-only
- Maximum length: 500 characters

**BR-DOC-002: File ID Required**
- Document MUST reference a valid file_id from storage_service
- File must exist and be accessible by user

**BR-DOC-003: Valid Document Type**
- Document type MUST be one of: PDF, DOCX, PPTX, XLSX, TXT, MARKDOWN, HTML, JSON

**BR-DOC-004: Default Status**
- New documents start with status DRAFT
- Status transitions to INDEXING when processing begins

**BR-DOC-005: Default Access Level**
- New documents default to PRIVATE access
- Only owner can access until explicitly shared

**BR-DOC-006: Owner Assignment**
- Document owner is the user_id who created it
- Owner cannot be changed after creation

**BR-DOC-007: Version Initialization**
- New documents start at version 1
- Version increments on each update

**BR-DOC-008: Unique Document ID**
- Each document gets a unique doc_id: `doc_{random_hex}`
- ID format: `doc_` prefix + 12-char hex

**BR-DOC-009: Collection Assignment**
- Documents assigned to user's collection: `user_{user_id}`
- Organization documents may have shared collections

**BR-DOC-010: Timestamp Recording**
- created_at and updated_at MUST be recorded
- Timestamps use UTC timezone

### Permission Rules (BR-PER-001 to BR-PER-010)

**BR-PER-001: Owner Always Has Access**
- Document owner ALWAYS has full access (read, update, delete, admin)
- Owner permission cannot be revoked

**BR-PER-002: Deny List Priority**
- `denied_users` takes precedence over all other permissions
- User in deny list cannot access regardless of access_level

**BR-PER-003: Allowed Users Override**
- Users in `allowed_users` bypass access_level restrictions
- Except when in `denied_users`

**BR-PER-004: Access Level Enforcement**
- PUBLIC: No authentication required
- ORGANIZATION: User must be in same organization
- TEAM: User must be in same team (via authorization_service)
- PRIVATE: Only owner and allowed_users

**BR-PER-005: Permission Update Authorization**
- Only document owner can update permissions
- Admin users may also update via authorization_service

**BR-PER-006: Permission History**
- All permission changes MUST be recorded in history
- History includes: old_state, new_state, changed_by, timestamp

**BR-PER-007: Group Permissions**
- `allowed_groups` grants access to all group members
- Group membership verified via authorization_service

**BR-PER-008: Read Permission for Operations**
- User must have read permission to view document
- User must have read permission to view permissions

**BR-PER-009: Update Permission**
- Only owner can update document content
- Update creates new version

**BR-PER-010: Delete Permission**
- Only owner can delete document
- Admin may delete via authorization_service

### Query Rules (BR-QRY-001 to BR-QRY-005)

**BR-QRY-001: Permission Filtering**
- RAG queries MUST filter results by user permissions
- User only sees documents they have access to

**BR-QRY-002: Collection Scoping**
- Queries scoped to user's collection
- Cross-collection queries require special permissions

**BR-QRY-003: Minimum Score Filtering**
- Semantic search respects `min_score` threshold
- Results below threshold excluded

**BR-QRY-004: Result Limiting**
- `top_k` parameter limits result count
- Maximum: 100 for search, 50 for RAG

**BR-QRY-005: Query Validation**
- Query text MUST be non-empty
- Query length: minimum 1 character

### Update Rules (BR-UPD-001 to BR-UPD-005)

**BR-UPD-001: Version Increment**
- Each update creates new version
- Version number increments by 1

**BR-UPD-002: Latest Flag Management**
- New version gets `is_latest = true`
- Old version set to `is_latest = false`

**BR-UPD-003: Parent Version Link**
- New version stores `parent_version_id`
- Links to previous version's doc_id

**BR-UPD-004: Status During Update**
- Document status set to UPDATING during process
- Status set to INDEXED on success, FAILED on error

**BR-UPD-005: File ID Required**
- Update MUST provide new file_id
- Cannot update without new content

### Deletion Rules (BR-DEL-001 to BR-DEL-005)

**BR-DEL-001: Soft Delete Default**
- Delete operations are soft delete by default
- Status changed to DELETED

**BR-DEL-002: Permanent Delete**
- `permanent=true` triggers hard delete
- Record removed from database

**BR-DEL-003: Owner Only**
- Only document owner can delete
- Admin override via authorization_service

**BR-DEL-004: Vector Cleanup**
- Permanent delete should trigger vector cleanup
- Handled by Digital Analytics service

**BR-DEL-005: Event Publishing**
- Delete operation MUST publish document.deleted event
- Event includes permanent flag

---

## Domain Invariants

1. **Document ID Uniqueness**: No two documents share the same doc_id
2. **Version Ordering**: Version numbers strictly increment within a document
3. **Single Latest Version**: Only one version per document has `is_latest = true`
4. **Owner Immutability**: Document owner cannot be changed after creation
5. **Permission Consistency**: denied_users always overrides other permissions
6. **Collection Isolation**: User documents stored in user-specific collection
7. **Status Validity**: Document status is always a valid DocumentStatus enum value
8. **Access Level Validity**: Access level is always a valid AccessLevel enum value

---

## Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation - AI technique combining retrieval with generation |
| **Embedding** | Vector representation of text for similarity search |
| **Chunk** | A segment of document content indexed separately |
| **Collection** | A Qdrant database collection storing vectors |
| **Qdrant** | Vector database used for semantic search |
| **Soft Delete** | Marking record as deleted without removing from database |
| **Hard Delete** | Permanently removing record from database |
| **Point** | A vector entry in Qdrant collection |
| **NATS** | Message broker for event-driven communication |

---

**End of Domain Context**
