# Document Service - Product Requirements Document (PRD)

## Product Overview

The Document Service provides **knowledge base management** for the isA platform, enabling users to store, index, and query documents using RAG (Retrieval-Augmented Generation) technology. Users can build personal or organizational knowledge bases with fine-grained access control and semantic search capabilities.

**Key Value Propositions**:
- Build searchable knowledge bases from uploaded documents
- Query documents using natural language (RAG)
- Fine-grained permission control for document sharing
- Version history for document changes
- Semantic search across document collections

---

## Target Users

- **End Users**: Individuals building personal knowledge bases from documents
- **Teams**: Groups sharing documents with team-level access control
- **Organizations**: Enterprises with organization-wide document repositories
- **Developers**: API consumers building document-powered applications
- **Administrators**: Users managing document permissions and access

---

## Epics and User Stories

### Epic 1: Document Management

**User stories**:

1. As a user, I want to upload a document to my knowledge base so that I can query it later
2. As a user, I want to view details of my documents so that I can manage my knowledge base
3. As a user, I want to list all my documents with filters so that I can find specific items
4. As a user, I want to delete documents so that I can remove outdated content
5. As a user, I want to update document content so that my knowledge base stays current

### Epic 2: RAG Querying

**User stories**:

1. As a user, I want to ask questions about my documents so that I get contextual answers
2. As a user, I want to search my documents semantically so that I find relevant content by meaning
3. As a user, I want to filter RAG queries by document type so that I get targeted results
4. As a user, I want to see source documents in RAG responses so that I can verify information

### Epic 3: Permission Management

**User stories**:

1. As a document owner, I want to set access levels so that I control who sees my documents
2. As a document owner, I want to share with specific users so that I can collaborate
3. As a document owner, I want to share with groups so that entire teams get access
4. As a document owner, I want to revoke access so that I can protect sensitive information
5. As a document owner, I want to see permission history so that I can audit access changes

### Epic 4: Document Versioning

**User stories**:

1. As a user, I want to see version history so that I can track document changes
2. As a user, I want to update documents incrementally so that indexing is efficient
3. As a user, I want to access previous versions so that I can review historical content

### Epic 5: Statistics and Insights

**User stories**:

1. As a user, I want to see document statistics so that I understand my knowledge base
2. As a user, I want to see documents by status so that I can monitor indexing progress
3. As a user, I want to see total storage used so that I can manage quotas

### Epic 6: Cross-Service Integration

**User stories**:

1. As a system, I want to react to file deletions so that documents stay consistent
2. As a system, I want to react to user deletions so that orphan documents are cleaned
3. As a system, I want to publish events so that other services stay informed

---

## API Surface Documentation

### Health Check Endpoints

#### GET /health
- **Description**: Service health check
- **Request Schema**: None
- **Response Schema**:
  ```json
  {
    "service": "document_service",
    "status": "healthy",
    "database": "connected",
    "timestamp": "2025-12-17T10:30:00Z"
  }
  ```
- **Error Codes**: 503 (Service Unavailable)

#### GET /
- **Description**: Service status with detailed information
- **Request Schema**: None
- **Response Schema**:
  ```json
  {
    "service": "document_service",
    "status": "operational",
    "port": 8227,
    "version": "1.0.0",
    "database_connected": true,
    "timestamp": "2025-12-17T10:30:00Z"
  }
  ```
- **Error Codes**: 503 (Service Unavailable)

---

### Document CRUD Endpoints

#### POST /api/v1/documents
- **Description**: Create a new knowledge document
- **Query Parameters**:
  - `user_id` (required): User ID
  - `organization_id` (optional): Organization ID
- **Request Schema**:
  ```json
  {
    "title": "Document Title",
    "description": "Optional description",
    "doc_type": "pdf",
    "file_id": "file_abc123",
    "access_level": "private",
    "allowed_users": ["user_123"],
    "allowed_groups": ["group_456"],
    "tags": ["tag1", "tag2"],
    "chunking_strategy": "semantic",
    "metadata": {"key": "value"}
  }
  ```
- **Response Schema**:
  ```json
  {
    "doc_id": "doc_abc123def456",
    "user_id": "user_123",
    "organization_id": null,
    "title": "Document Title",
    "description": "Optional description",
    "doc_type": "pdf",
    "file_id": "file_abc123",
    "file_size": 1024000,
    "version": 1,
    "is_latest": true,
    "status": "draft",
    "chunk_count": 0,
    "access_level": "private",
    "indexed_at": null,
    "created_at": "2025-12-17T10:30:00Z",
    "updated_at": "2025-12-17T10:30:00Z",
    "tags": ["tag1", "tag2"]
  }
  ```
- **Error Codes**: 400 (Validation Error), 500 (Server Error)

#### GET /api/v1/documents/{doc_id}
- **Description**: Get document by ID
- **Path Parameters**:
  - `doc_id`: Document ID
- **Query Parameters**:
  - `user_id` (required): User ID for permission check
- **Response Schema**: Same as create response
- **Error Codes**: 404 (Not Found), 403 (Forbidden), 500 (Server Error)

#### GET /api/v1/documents
- **Description**: List user's documents with filters
- **Query Parameters**:
  - `user_id` (required): User ID
  - `organization_id` (optional): Filter by organization
  - `status` (optional): Filter by status (draft, indexing, indexed, etc.)
  - `doc_type` (optional): Filter by document type
  - `limit` (optional): Max results (default 50, max 100)
  - `offset` (optional): Pagination offset (default 0)
- **Response Schema**:
  ```json
  [
    {
      "doc_id": "doc_abc123",
      "user_id": "user_123",
      "title": "Document 1",
      "doc_type": "pdf",
      "status": "indexed",
      "created_at": "2025-12-17T10:30:00Z"
    }
  ]
  ```
- **Error Codes**: 500 (Server Error)

#### DELETE /api/v1/documents/{doc_id}
- **Description**: Delete document
- **Path Parameters**:
  - `doc_id`: Document ID
- **Query Parameters**:
  - `user_id` (required): User ID
  - `permanent` (optional): Hard delete if true (default false)
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Document deleted"
  }
  ```
- **Error Codes**: 404 (Not Found), 403 (Forbidden), 500 (Server Error)

---

### RAG Update Endpoints

#### PUT /api/v1/documents/{doc_id}/update
- **Description**: Update document content with incremental RAG re-indexing
- **Path Parameters**:
  - `doc_id`: Document ID
- **Query Parameters**:
  - `user_id` (required): User ID
- **Request Schema**:
  ```json
  {
    "new_file_id": "file_xyz789",
    "update_strategy": "smart",
    "title": "Updated Title",
    "description": "Updated description",
    "tags": ["new-tag"]
  }
  ```
- **Response Schema**: Same as create response with incremented version
- **Error Codes**: 404 (Not Found), 403 (Forbidden), 400 (Validation Error), 500 (Server Error)

---

### Permission Management Endpoints

#### PUT /api/v1/documents/{doc_id}/permissions
- **Description**: Update document permissions
- **Path Parameters**:
  - `doc_id`: Document ID
- **Query Parameters**:
  - `user_id` (required): User ID (must be owner)
- **Request Schema**:
  ```json
  {
    "access_level": "team",
    "add_users": ["user_456", "user_789"],
    "remove_users": ["user_old"],
    "add_groups": ["group_new"],
    "remove_groups": ["group_old"]
  }
  ```
- **Response Schema**:
  ```json
  {
    "doc_id": "doc_abc123",
    "access_level": "team",
    "allowed_users": ["user_456", "user_789"],
    "allowed_groups": ["group_new"],
    "denied_users": []
  }
  ```
- **Error Codes**: 404 (Not Found), 403 (Forbidden), 500 (Server Error)

#### GET /api/v1/documents/{doc_id}/permissions
- **Description**: Get document permissions
- **Path Parameters**:
  - `doc_id`: Document ID
- **Query Parameters**:
  - `user_id` (required): User ID
- **Response Schema**: Same as update permissions response
- **Error Codes**: 404 (Not Found), 403 (Forbidden), 500 (Server Error)

---

### RAG Query Endpoints

#### POST /api/v1/documents/rag/query
- **Description**: RAG query with permission filtering
- **Query Parameters**:
  - `user_id` (required): User ID
  - `organization_id` (optional): Organization scope
- **Request Schema**:
  ```json
  {
    "query": "What is the main topic of the document?",
    "top_k": 5,
    "doc_types": ["pdf", "docx"],
    "tags": ["important"],
    "temperature": 0.7,
    "max_tokens": 500
  }
  ```
- **Response Schema**:
  ```json
  {
    "query": "What is the main topic?",
    "answer": "The main topic is...",
    "sources": [
      {
        "doc_id": "doc_abc123",
        "title": "Document Title",
        "doc_type": "pdf",
        "relevance_score": 0.95,
        "snippet": "Relevant text...",
        "file_id": "file_123",
        "chunk_id": "chunk_456",
        "metadata": {}
      }
    ],
    "confidence": 0.85,
    "latency_ms": 234.5
  }
  ```
- **Error Codes**: 500 (Server Error)

#### POST /api/v1/documents/search
- **Description**: Semantic search with permission filtering
- **Query Parameters**:
  - `user_id` (required): User ID
  - `organization_id` (optional): Organization scope
- **Request Schema**:
  ```json
  {
    "query": "machine learning algorithms",
    "top_k": 10,
    "doc_types": ["pdf"],
    "tags": [],
    "min_score": 0.5
  }
  ```
- **Response Schema**:
  ```json
  {
    "query": "machine learning algorithms",
    "results": [
      {
        "doc_id": "doc_abc123",
        "title": "ML Guide",
        "doc_type": "pdf",
        "relevance_score": 0.92,
        "snippet": "Machine learning...",
        "file_id": "file_123"
      }
    ],
    "total_count": 5,
    "latency_ms": 123.4
  }
  ```
- **Error Codes**: 500 (Server Error)

---

### Statistics Endpoints

#### GET /api/v1/documents/stats
- **Description**: Get user's document statistics
- **Query Parameters**:
  - `user_id` (required): User ID
  - `organization_id` (optional): Organization scope
- **Response Schema**:
  ```json
  {
    "user_id": "user_123",
    "total_documents": 42,
    "indexed_documents": 40,
    "total_chunks": 1250,
    "total_size_bytes": 52428800,
    "by_type": {
      "pdf": 20,
      "docx": 15,
      "txt": 7
    },
    "by_status": {
      "indexed": 40,
      "draft": 1,
      "failed": 1
    }
  }
  ```
- **Error Codes**: 500 (Server Error)

---

## Functional Requirements

### FR-001: Document Creation
The system MUST allow users to create knowledge documents by providing title, document type, and file reference. Documents MUST be assigned unique IDs and associated with the creating user.

### FR-002: Document Retrieval
The system MUST allow users to retrieve documents they have permission to access. Retrieval MUST respect access level and explicit permissions.

### FR-003: Document Listing
The system MUST allow users to list their documents with filtering by status, type, and organization. Pagination MUST be supported.

### FR-004: Document Deletion
The system MUST support both soft and hard delete operations. Soft delete MUST be the default behavior.

### FR-005: RAG Query Processing
The system MUST process natural language queries against user's document collection. Responses MUST include relevant answers and source references.

### FR-006: Semantic Search
The system MUST support semantic (vector-based) search across documents. Results MUST be ranked by relevance score.

### FR-007: Permission Management
The system MUST allow document owners to manage access permissions including access level, allowed users, allowed groups, and denied users.

### FR-008: Version Control
The system MUST maintain version history when documents are updated. Previous versions MUST be accessible for audit purposes.

### FR-009: Incremental Updates
The system MUST support incremental document updates without requiring full re-indexing of unchanged content.

### FR-010: Statistics Reporting
The system MUST provide usage statistics including document counts, storage usage, and breakdown by type/status.

### FR-011: Event Publishing
The system MUST publish events for document lifecycle changes (created, updated, deleted, permissions changed).

### FR-012: Event Consumption
The system MUST handle external events (file deleted, user deleted) to maintain data consistency.

### FR-013: Access Level Enforcement
The system MUST enforce four access levels: PRIVATE (owner only), TEAM, ORGANIZATION, and PUBLIC.

### FR-014: Permission History
The system MUST record all permission changes with audit trail including who changed what and when.

### FR-015: Document Type Support
The system MUST support PDF, DOCX, PPTX, XLSX, TXT, MARKDOWN, HTML, and JSON document types.

---

## Non-Functional Requirements

### NFR-001: Performance
- RAG queries MUST complete within 5 seconds for 95th percentile
- Document creation MUST complete within 1 second (excluding indexing)
- List operations MUST complete within 500ms

### NFR-002: Scalability
- Support up to 10,000 documents per user
- Support up to 1 million total documents
- Handle concurrent RAG queries without degradation

### NFR-003: Availability
- Service MUST maintain 99.9% uptime
- Graceful degradation when Digital Analytics unavailable

### NFR-004: Security
- All API endpoints MUST require user_id authentication
- Permission checks MUST be enforced at service layer
- Sensitive data MUST not be logged

### NFR-005: Reliability
- Document creation MUST be atomic (all-or-nothing)
- Failed indexing MUST not corrupt document state

### NFR-006: Auditability
- All permission changes MUST be logged
- All document operations MUST publish events

### NFR-007: Consistency
- Permission changes MUST take effect immediately
- Version history MUST be accurate and complete

### NFR-008: Recoverability
- Failed indexing operations MUST be retryable
- Service MUST recover gracefully from crashes

### NFR-009: Observability
- Health check endpoints MUST report accurate status
- Latency metrics MUST be included in query responses

### NFR-010: Integration
- MUST integrate with storage_service for file access
- MUST integrate with authorization_service for team/org permissions
- MUST integrate with digital_analytics for RAG operations

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Query Success Rate | > 99% |
| Average RAG Query Latency | < 2 seconds |
| Document Indexing Success Rate | > 95% |
| API Availability | > 99.9% |
| User Adoption | 50% of active users using documents |
| Documents per Active User | > 10 average |

---

## Dependencies

| Service | Purpose |
|---------|---------|
| **storage_service** | File storage and retrieval |
| **authorization_service** | Team/org permission verification |
| **digital_analytics** | RAG indexing and querying |
| **account_service** | User validation |
| **NATS** | Event publishing/subscription |
| **PostgreSQL** | Document metadata storage |
| **Qdrant** | Vector storage (via digital_analytics) |

---

## Constraints

1. **Digital Analytics Dependency**: RAG functionality requires Digital Analytics service to be operational
2. **Storage Dependency**: Documents require valid file references in storage_service
3. **Collection Naming**: Collections follow `user_{user_id}` naming convention
4. **Version Immutability**: Document versions are immutable once created
5. **Owner Immutability**: Document ownership cannot be transferred

---

**End of PRD**
