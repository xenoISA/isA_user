# Storage Service - Domain Context

## Overview

The Storage Service is the **file management backbone** for the entire isA_user platform. It provides centralized file storage, metadata management, access control, and sharing capabilities. Every file in the system is managed through this service with secure, scalable storage operations.

**Business Context**: Enable secure, scalable file management that serves as the foundation for all file-centric services. Storage Service owns the "what" and "where" of files - ensuring every file has secure storage, proper metadata, and controlled access.

**Core Value Proposition**: Transform disparate file operations into a unified storage layer with quota management, secure sharing, event-driven synchronization, and multi-provider abstraction.

---

## Business Taxonomy

### Core Entities

#### 1. File
**Definition**: A unique digital asset stored in the system with associated metadata and access controls.

**Business Purpose**:
- Establish single source of truth for file storage
- Track file lifecycle (upload, availability, deletion, archival)
- Maintain file metadata and organization
- Enforce access controls and quotas
- Enable file sharing with permissions

**Key Attributes**:
- File ID (unique identifier, format: `file_[0-9a-f]{32}`)
- User ID (file owner)
- Organization ID (optional, for team files)
- File Name (original filename)
- File Path (storage object path)
- File Size (in bytes)
- Content Type (MIME type)
- Status (uploading, available, deleted, failed, archived)
- Access Level (private, restricted, shared, public)
- Download URL (presigned, with expiry)
- Metadata (flexible JSONB)
- Tags (array of strings)
- Auto-delete configuration
- Indexing preferences
- Created/Updated timestamps

**File Statuses**:
- **UPLOADING**: File being uploaded to storage backend
- **AVAILABLE**: File successfully uploaded and accessible
- **DELETED**: File marked as deleted (soft delete)
- **FAILED**: Upload or processing failed
- **ARCHIVED**: File moved to cold storage

**Access Levels**:
- **PRIVATE**: Only file owner can access
- **RESTRICTED**: Owner and org members can access
- **SHARED**: Owner + explicitly shared users can access
- **PUBLIC**: Any authenticated user can access

#### 2. File Share
**Definition**: A secure, time-limited access mechanism for sharing files with external users.

**Business Purpose**:
- Enable secure file sharing without compromising original file permissions
- Provide granular access controls (view, download, delete)
- Track share usage and enforce limits
- Support multiple access methods (token, password)

**Key Attributes**:
- Share ID (unique identifier, format: `share_[0-9a-f]{12}`)
- File ID (referenced file)
- Shared By (user who created share)
- Shared With (target user ID, optional)
- Shared With Email (target email, optional)
- Permissions (view, download, delete)
- Access Control (password or token)
- Expiration Time
- Download Limits
- Usage Tracking (download count, last accessed)
- Active Status
- Created/Updated timestamps

**Permission Model**:
```json
{
  "view": true,       // Can view file metadata
  "download": false,  // Can download file
  "delete": false     // Can delete file (dangerous!)
}
```

#### 3. User Quota
**Definition**: Storage allocation limits and usage tracking for each user.

**Business Purpose**:
- Enforce fair usage policies
- Track storage consumption
- Enable tiered storage plans
- Provide quota monitoring and alerts

**Key Attributes**:
- User ID (quota owner)
- Total Quota Bytes (allocation limit)
- Used Bytes (current consumption)
- File Count (number of files owned)
- Created/Updated timestamps

**Default Quotas**:
- **Free Tier**: 10GB (10,737,418,240 bytes)
- **Max File Size**: 500MB (524,288,000 bytes)
- **Max Files**: 100,000 per user

#### 4. Storage Statistics
**Definition**: Aggregated storage metrics for monitoring and reporting.

**Business Purpose**:
- Provide storage health monitoring
- Enable usage analytics and reporting
- Support capacity planning
- Track file type distribution

**Key Attributes**:
- User/Organization scope
- Total quota bytes
- Used bytes
- Available bytes
- Usage percentage
- File count
- Statistics by file type
- Statistics by status

---

## Domain Scenarios

### Scenario 1: File Upload with Quota Validation
**Actor**: User, Mobile App
**Trigger**: User uploads a photo from mobile device
**Flow**:
1. User selects photo.jpg (2MB) in mobile app
2. App calls `POST /api/v1/storage/files/upload` with multipart data
3. Storage Service validates user quota (10GB total, 5GB used)
4. Storage Service validates file type (image/jpeg allowed)
5. Storage Service validates file size (2MB < 500MB limit)
6. Service generates file_id and object path
7. Service uploads file to MinIO bucket `isa-storage`
8. Service creates metadata record in PostgreSQL
9. Service updates user quota (+2MB, +1 file)
10. Service generates presigned download URL (24h expiry)
11. Service publishes `storage.file.uploaded` event
12. Service returns file upload response with metadata
13. Media Service receives event, creates thumbnail and runs AI analysis
14. Notification Service sends upload confirmation

**Outcome**: File securely stored, metadata tracked, quota updated, downstream services notified

### Scenario 2: Presigned URL Regeneration
**Actor**: User, Web Application
**Trigger**: User tries to download file after URL expired
**Flow**:
1. User clicks download link for file_abc123
2. App calls `GET /api/v1/storage/files/file_abc123?user_id=user_123`
3. Storage Service retrieves file record
4. Service checks download_url_expires_at (expired yesterday)
5. Service generates new presigned URL from MinIO (24h expiry)
6. Service updates database with new URL and expiry
7. Service returns file info with fresh download URL
8. User downloads file via presigned URL (direct to MinIO)

**Outcome**: Seamless user experience with automatic URL refresh, no service interruption

### Scenario 3: File Sharing with Permissions
**Actor**: User, Email Recipient
**Trigger**: User shares vacation photo with friend via email
**Flow**:
1. User selects file_abc123 and clicks "Share"
2. User enters friend@example.com, sets permissions (view+download), expiry 48h
3. App calls `POST /api/v1/storage/shares` with share request
4. Storage Service validates file ownership (user_123 owns file_abc123)
5. Service creates share record with access_token and expiry
6. Service generates share URL with token
7. Service publishes `storage.file.shared` event
8. Service returns share response with URL
9. Notification Service receives event, sends email to friend@example.com
10. Friend clicks share link, visits share URL
11. Storage Service validates share (active, not expired, token valid)
12. Service generates short-lived presigned URL (15min)
13. Friend downloads file via short-lived URL
14. Service increments download count for share

**Outcome**: Secure file sharing with granular permissions, automatic expiry, usage tracking

### Scenario 4: File Deletion with Share Validation
**Actor**: User, Admin Dashboard
**Trigger**: User wants to delete file that has active shares
**Flow**:
1. User selects file_abc123 in admin dashboard and clicks "Delete"
2. Dashboard calls `DELETE /api/v1/storage/files/file_abc123?user_id=user_123`
3. Storage Service retrieves file record (owned by user_123)
4. Service checks for active shares (finds 2 active shares)
5. Service returns error: "Cannot delete file with 2 active shares"
6. User dashboard shows error and lists active shares
7. User deactivates shares first, then deletes file
8. Service performs soft delete (marks status = 'deleted')
9. Service updates user quota (-file_size, -1 file)
10. Service publishes `storage.file.deleted` event
11. Media Service receives event, removes related media records
12. Document Service removes file from RAG index

**Outcome**: Protected deletion preventing broken share links, proper cleanup of related data

### Scenario 5: Batch File Listing with URL Management
**Actor**: User, File Manager Application
**Trigger**: User views their file library with 50 files
**Flow**:
1. App calls `GET /api/v1/storage/files?user_id=user_123&limit=50&offset=0`
2. Storage Service queries database for user's files
3. Service checks each file's download URL expiry
4. Service batch regenerates expired URLs (3 files had expired URLs)
5. Service updates database with new URLs and expiries
6. Service returns list with fresh download URLs
7. App displays file list with working download links
8. User can immediately download any file without URL errors

**Outcome**: Efficient batch URL management, seamless user experience, reduced API calls

### Scenario 6: Quota Enforcement and Monitoring
**Actor**: User, System Monitor
**Trigger**: User approaches storage limit
**Flow**:
1. User has used 9.8GB of 10GB quota
2. User tries to upload 500MB video file
3. Storage Service checks quota: 9.8GB + 500MB > 10GB
4. Service rejects upload with error: "Storage quota exceeded: 9.8GB/10GB"
5. App shows quota warning to user
6. User deletes some old files to free space
7. Service updates quota on deletion (-2GB freed)
8. User retries upload, now succeeds (7.8GB + 500MB < 10GB)
9. Monitoring dashboard shows quota usage trends
10. System alerts admin when users approach 90% quota

**Outcome**: Proactive quota management, user guidance, system capacity planning

### Scenario 7: Organization File Management
**Actor**: Organization Admin, Team Members
**Trigger**: Organization admin manages team files
**Flow**:
1. Organization admin uploads project_document.pdf with organization_id=org_456
2. Service stores file with org association
3. Admin sets access_level=restricted (org members only)
4. Team member user_789 lists files with organization_id=org_456
5. Service returns org files accessible to member
6. Admin calls `GET /api/v1/storage/stats?organization_id=org_456`
7. Service returns org-wide storage statistics
8. Admin sees team usage: 25GB total, 180 files, 3 users

**Outcome**: Team-based file management with proper access controls, org-wide visibility

---

## Domain Events

### Published Events

#### 1. storage.file.uploaded
**Trigger**: File successfully uploaded via `/api/v1/storage/files/upload`
**Payload**:
- file_id: Unique file identifier
- file_name: Original filename
- file_size: File size in bytes
- content_type: MIME type
- user_id: File owner
- organization_id: Optional organization ID
- access_level: File access permissions
- download_url: Initial presigned download URL
- bucket_name: MinIO bucket name
- object_name: Storage object path
- timestamp: Upload timestamp

**Subscribers**:
- **Media Service**: Create thumbnails, AI analysis for images/videos
- **Document Service**: Index documents for RAG if enable_indexing=true
- **Audit Service**: Log file upload for compliance
- **Analytics Service**: Track storage usage patterns
- **Notification Service**: Send upload confirmations

#### 2. storage.file.deleted
**Trigger**: File deleted via `DELETE /api/v1/storage/files/{file_id}`
**Payload**:
- file_id: Unique file identifier
- file_name: Original filename
- file_size: File size in bytes
- user_id: File owner
- permanent: Boolean indicating hard vs soft delete
- timestamp: Deletion timestamp

**Subscribers**:
- **Media Service**: Clean up related media records
- **Document Service**: Remove from RAG index
- **Album Service**: Remove from photo albums
- **Audit Service**: Log deletion for compliance
- **Analytics Service**: Update storage metrics

#### 3. storage.file.shared
**Trigger**: File share created via `POST /api/v1/storage/shares`
**Payload**:
- share_id: Unique share identifier
- file_id: Referenced file ID
- file_name: Original filename
- shared_by: User who created share
- shared_with: Target user ID (optional)
- shared_with_email: Target email (optional)
- expires_at: Share expiration time
- timestamp: Share creation timestamp

**Subscribers**:
- **Notification Service**: Send share notification email
- **Audit Service**: Log file sharing for compliance
- **Analytics Service**: Track sharing patterns

---

## Core Concepts

### File Lifecycle Management
1. **Upload**: Client uploads file → Service validates → Store in MinIO → Create metadata
2. **Availability**: File marked as available, download URL generated
3. **Access**: Users access via presigned URLs, automatic URL refresh
4. **Sharing**: Optional secure sharing with permissions and expiry
5. **Deletion**: Soft delete by default, hard delete optional
6. **Archival**: Future feature for cold storage migration

### Storage Architecture
- **Multi-Provider**: Abstracted backend (MinIO primary, S3/Azure future)
- **Object Storage**: Files stored as objects in buckets
- **Hierarchical Paths**: `users/{user_id}/{YYYY}/{MM}/{DD}/{timestamp}_{uuid}_{filename}`
- **Metadata Separation**: File metadata in PostgreSQL, objects in storage backend
- **Presigned URLs**: Direct access to storage backend, bypassing service

### Access Control Model
- **Ownership**: Files owned by specific users
- **Access Levels**: private, restricted, shared, public
- **Sharing**: Secure, time-limited access with granular permissions
- **Authorization**: JWT-based authentication, user-scoped data access
- **Permission Model**: View, download, delete permissions per share

### Quota Management
- **Per-User Quotas**: Individual storage allocations
- **Real-time Tracking**: Atomic quota updates on file operations
- **Usage Monitoring**: Percentage-based utilization tracking
- **Enforcement**: Upload validation against available quota
- **Organization Tracking**: Optional org-level aggregation

### Event-Driven Integration
- **Async Publishing**: Non-blocking event publication
- **Loose Coupling**: Downstream services subscribe to events
- **Event Context**: Rich event payloads for subscriber needs
- **Error Isolation**: Event failures don't block file operations

### Security Model
- **Presigned URLs**: Time-limited, cryptographically signed URLs
- **Access Tokens**: Share-specific tokens for password-less access
- **Password Protection**: Optional password-based share access
- **URL Expiry**: Automatic URL expiration (24h for owners, 15min for shares)
- **File Isolation**: User-based object paths prevent access leakage

---

## Business Rules (High-Level)

### File Upload Rules
- **BR-STO-001**: File ID must follow format `file_[0-9a-f]{32}`
- **BR-STO-002**: User quota must accommodate file size (used_bytes + file_size ≤ total_quota_bytes)
- **BR-STO-003**: Content type must be in allowed types list
- **BR-STO-004**: File size must not exceed maximum (500MB)
- **BR-STO-005**: Object path format: `users/{user_id}/{YYYY}/{MM}/{DD}/{timestamp}_{uuid}_{filename}`
- **BR-STO-006**: Default access_level = private
- **BR-STO-007**: Default enable_indexing = true
- **BR-STO-008**: Upload to MinIO must succeed before database record creation

### File Access Rules
- **BR-STO-009**: Users can only access their own files by default
- **BR-STO-010**: Org members can access restricted files in same org
- **BR-STO-011**: Presigned URLs expire after 24 hours for owners
- **BR-STO-012**: Expired URLs automatically regenerated on access
- **BR-STO-013**: Deleted files not returned in default queries
- **BR-STO-014**: File access validates ownership or valid share

### File Sharing Rules
- **BR-STO-015**: Only file owners can create shares
- **BR-STO-016**: Share ID must follow format `share_[0-9a-f]{12}`
- **BR-STO-017**: Share expiry must be 1-720 hours (max 30 days)
- **BR-STO-018**: Shares require either password or access token
- **BR-STO-019**: Share permissions: view always true, download/delete configurable
- **BR-STO-020**: Presigned URLs for shares expire after 15 minutes
- **BR-STO-021**: Download limits enforced when max_downloads set
- **BR-STO-022**: Expired shares treated as not found (security)

### File Deletion Rules
- **BR-STO-023**: File owners can delete their own files
- **BR-STO-024**: Org admins can delete org files
- **BR-STO-025**: Files with active shares cannot be deleted
- **BR-STO-026**: Default deletion is soft delete (status = deleted)
- **BR-STO-027**: Hard deletion removes object from storage backend
- **BR-STO-028**: Deletion updates user quota immediately
- **BR-STO-029**: Deleted files excluded from list/search by default

### Quota Management Rules
- **BR-STO-030**: Default user quota = 10GB
- **BR-STO-031**: Quota records created automatically on first upload
- **BR-STO-032**: Quota updates are atomic (used_bytes, file_count)
- **BR-STO-033**: Upload validation uses current quota + file_size
- **BR-STO-034**: Quota usage tracked in real-time
- **BR-STO-035**: Organization quotas aggregated from user quotas

### Metadata and Organization Rules
- **BR-STO-036**: File metadata stored as flexible JSONB
- **BR-STO-037**: Tags stored as text array for efficient searching
- **BR-STO-038**: File path includes timestamp for uniqueness
- **BR-STO-039**: Organization assignment optional (personal vs team files)
- **BR-STO-040**: Indexing flag controls RAG processing

### Event Publishing Rules
- **BR-STO-041**: All file mutations publish corresponding events
- **BR-STO-042**: Event publishing failures logged but don't block operations
- **BR-STO-043**: Events include complete context for subscribers
- **BR-STO-044**: Events use ISO 8601 timestamps
- **BR-STO-045**: storage.file.uploaded published only after successful storage

### Data Consistency Rules
- **BR-STO-046**: File upload is atomic (MinIO + PostgreSQL transaction-like)
- **BR-STO-047**: Quota updates use database atomic operations
- **BR-STO-048**: Share creation and file validation in single transaction
- **BR-STO-049**: Soft delete preserves audit trail
- **BR-STO-050**: Object path generation uses UUID for uniqueness

---

## Storage Service in the Ecosystem

### Upstream Dependencies
- **Auth Service**: Provides JWT validation and user context
- **PostgreSQL gRPC Service**: Persistent metadata storage
- **MinIO**: S3-compatible object storage backend
- **NATS Event Bus**: Event publishing infrastructure
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and authentication

### Downstream Consumers
- **Media Service**: Image/video processing and AI analysis
- **Document Service**: Document indexing for RAG and search
- **Album Service**: Photo album organization
- **Notification Service**: Share notifications and confirmations
- **Audit Service**: Compliance and change tracking
- **Analytics Service**: Usage metrics and reporting
- **Organization Service**: Team file management

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time updates
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/health/detailed` endpoints
- **Direct Storage Access**: Presigned URLs to MinIO

### Dependency Injection
- **Repository Pattern**: StorageRepository for data access
- **Backend Pattern**: StorageBackend for storage operations
- **Protocol Interfaces**: StorageRepositoryProtocol, StorageBackendProtocol
- **Factory Pattern**: create_storage_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks

---

## Success Metrics

### Storage Quality Metrics
- **Upload Success Rate**: % of successful file uploads (target: >99.5%)
- **URL Availability**: % of working download URLs (target: >99.9%)
- **Share Success Rate**: % of successful share accesses (target: >99%)
- **Quota Accuracy**: Storage usage calculation accuracy (target: 100%)

### Performance Metrics
- **Upload Latency**: Time from upload start to completion (target: <2s p95)
- **File Info Latency**: Time to retrieve file metadata (target: <100ms p95)
- **Share Access Latency**: Time to access shared file (target: <300ms p95)
- **URL Generation**: Presigned URL generation time (target: <50ms p95)

### Usage Metrics
- **Daily Uploads**: New files uploaded per day
- **Storage Growth**: Monthly storage consumption growth
- **Share Activity**: Number of shares created/accessed per day
- **Quota Utilization**: Average user quota percentage (target: <80%)

### System Health Metrics
- **Storage Availability**: MinIO backend availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success rate (target: 99.99%)
- **Event Publishing**: % of events successfully published (target: >99.5%)
- **Error Rate**: HTTP error responses (target: <1%)

### Business Metrics
- **User Storage Adoption**: % of users with uploaded files
- **File Type Distribution**: Breakdown by content type
- **Sharing Patterns**: Average shares per user, share duration
- **Organization Usage**: Org vs personal file ratios

---

## Glossary

**File**: Digital asset stored in the system with metadata
**File ID**: Unique identifier (format: `file_[0-9a-f]{32}`)
**Object Storage**: Scalable storage system for binary data
**Presigned URL**: Time-limited, cryptographically signed URL for direct access
**File Share**: Secure, time-limited access mechanism for files
**Share ID**: Unique share identifier (format: `share_[0-9a-f]{12}`)
**Access Token**: Cryptographic token for password-less share access
**User Quota**: Storage allocation limits per user
**Soft Delete**: Marking file as deleted while preserving metadata
**Hard Delete**: Permanently removing file and metadata
**Access Level**: File visibility permissions (private, restricted, shared, public)
**Metadata**: Structured data about files (JSONB)
**Tags**: Categorical labels for file organization
**RAG**: Retrieval-Augmented Generation for AI indexing
**MinIO**: S3-compatible object storage system
**Event Bus**: NATS messaging system for asynchronous communication
**Repository Pattern**: Data access abstraction layer
**Backend Pattern**: Storage operation abstraction layer
**Protocol Interface**: Abstract contract for dependency injection
**Object Path**: Hierarchical storage location for files
**Download URL Expiry**: Automatic URL expiration for security
**Share Expiration**: Time-limited access for shared files
**Permission Model**: Granular access controls (view, download, delete)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Storage Service Team
**Related Documents**:
- Design Document: docs/design/storage_service.md
- PRD: docs/prd/storage_service.md
- Data Contract: tests/contracts/storage/data_contract.py
- Logic Contract: tests/contracts/storage/logic_contract.md
