# Storage Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Storage Service
**Version**: 1.0.0
**Status**: Production
**Owner**: Storage & Platform Team
**Last Updated**: 2025-12-15

### Vision
Establish the most reliable, scalable file storage platform for the isA_user ecosystem with secure access controls, intelligent quota management, and seamless sharing capabilities.

### Mission
Provide a production-grade file storage service that guarantees secure file management, serves as the backbone for all file-centric operations, and enables powerful sharing and collaboration features.

### Target Users
- **Internal Services**: Media, Document, Album, Organization, Notification services
- **Platform Users**: Mobile app users uploading photos, documents, videos
- **Team Administrators**: Managing organization files and quotas
- **External Collaborators**: Accessing shared files via secure links
- **System Administrators**: Monitoring storage health and capacity

### Key Differentiators
1. **Secure File Sharing**: Time-limited, permission-based sharing with granular controls
2. **Presigned URL Architecture**: Direct storage access with automatic URL refresh
3. **Multi-Provider Support**: Abstracted storage backend (MinIO primary, cloud providers future)
4. **Real-time Quota Management**: Atomic quota tracking with enforcement
5. **Event-Driven Integration**: Seamless synchronization with 10+ downstream services

---

## Product Goals

### Primary Goals
1. **Secure File Storage**: 99.9% file availability with zero data loss
2. **Fast Upload Performance**: Sub-2 second uploads for files up to 100MB
3. **Reliable Sharing**: 99.5%+ share access success rate with proper expiration
4. **Quota Accuracy**: 100% accurate storage tracking with real-time updates
5. **Multi-format Support**: Support for images, documents, videos, and audio formats

### Secondary Goals
1. **Team Collaboration**: Organization-based file management and access controls
2. **Smart Indexing**: Optional RAG integration for document search
3. **Storage Analytics**: Comprehensive usage metrics and reporting
4. **Mobile Optimization**: Efficient uploads and access for mobile devices
5. **Cost Efficiency**: Optimized storage patterns and automatic cleanup

---

## Epics and User Stories

### Epic 1: Core File Management

**Objective**: Enable secure file upload, storage, and retrieval with proper access controls.

#### E1-US1: Secure File Upload
**As a** Mobile User
**I want to** upload photos and documents from my device
**So that** I can store them securely and access them anywhere

**Acceptance Criteria**:
- AC1: POST /api/v1/storage/files/upload accepts multipart/form-data
- AC2: File size validation (max 500MB) enforced
- AC3: File type validation against allowed MIME types
- AC4: Quota validation prevents over-usage
- AC5: File stored in MinIO with hierarchical path structure
- AC6: Metadata record created in PostgreSQL with all attributes
- AC7: Presigned download URL generated (24h expiry)
- AC8: storage.file.uploaded event published on success
- AC9: Upload response includes file_id, download_url, file_size, content_type
- AC10: Upload time <2s for files up to 100MB

**API Reference**: `POST /api/v1/storage/files/upload`

**Example Request**:
```
POST /api/v1/storage/files/upload
Content-Type: multipart/form-data

file: [binary file data]
user_id: "user_123"
access_level: "private"
metadata: {"source": "mobile_app", "location": "vacation"}
tags: ["photo", "beach"]
auto_delete_after_days: 30
enable_indexing: true
```

**Example Response**:
```json
{
  "file_id": "file_abc123def4567890123456789012345678",
  "file_path": "users/user_123/2025/12/15/20251215_143000_a1b2c3d4_vacation_photo.jpg",
  "download_url": "https://minio.example.com/presigned-url-24h",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "uploaded_at": "2025-12-15T14:30:00Z",
  "message": "File uploaded successfully"
}
```

#### E1-US2: File Information Retrieval
**As a** Web App User
**I want to** get file metadata and download URL
**So that** I can access and manage my stored files

**Acceptance Criteria**:
- AC1: GET /api/v1/storage/files/{file_id} returns file information
- AC2: User authorization validated (user owns file or has access)
- AC3: Automatic presigned URL regeneration if expired
- AC4: Response includes all metadata: file_name, file_size, content_type, status, access_level
- AC5: Tags and metadata returned in original format
- AC6: Response time <100ms
- AC7: 404 response for non-existent or inaccessible files

**API Reference**: `GET /api/v1/storage/files/{file_id}?user_id={user_id}`

**Example Response**:
```json
{
  "file_id": "file_abc123def4567890123456789012345678",
  "user_id": "user_123",
  "file_name": "vacation_photo.jpg",
  "file_path": "users/user_123/2025/12/15/20251215_143000_a1b2c3d4_vacation_photo.jpg",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "status": "available",
  "access_level": "private",
  "download_url": "https://minio.example.com/presigned-url-24h",
  "metadata": {"source": "mobile_app", "location": "vacation"},
  "tags": ["photo", "beach"],
  "uploaded_at": "2025-12-15T14:30:00Z",
  "updated_at": "2025-12-15T14:30:00Z"
}
```

#### E1-US3: File Listing with Pagination
**As a** User
**I want to** browse my stored files with pagination
**So that** I can find and manage my files efficiently

**Acceptance Criteria**:
- AC1: GET /api/v1/storage/files returns paginated file list
- AC2: Supports filters: user_id, organization_id, prefix, status, access_level
- AC3: Pagination with limit (1-1000) and offset parameters
- AC4: Results sorted by uploaded_at DESC (newest first)
- AC5: Batch presigned URL regeneration for expired URLs
- AC6: Returns only files user has access to
- AC7: Response time <200ms for 100 files
- AC8: Empty array returned for no matching files

**API Reference**: `GET /api/v1/storage/files?user_id={user_id}&limit={limit}&offset={offset}`

**Example Request**:
```
GET /api/v1/storage/files?user_id=user_123&limit=20&offset=0&status=available
```

**Example Response**:
```json
[
  {
    "file_id": "file_abc123...",
    "user_id": "user_123",
    "file_name": "vacation_photo.jpg",
    "file_path": "users/user_123/2025/12/15/...",
    "file_size": 2097152,
    "content_type": "image/jpeg",
    "status": "available",
    "access_level": "private",
    "download_url": "https://minio.example.com/presigned-url",
    "metadata": {"location": "vacation"},
    "tags": ["photo"],
    "uploaded_at": "2025-12-15T14:30:00Z",
    "updated_at": "2025-12-15T14:30:00Z"
  }
]
```

#### E1-US4: File Deletion with Validation
**As a** User
**I want to** delete files I no longer need
**So that** I can manage my storage usage

**Acceptance Criteria**:
- AC1: DELETE /api/v1/storage/files/{file_id} supports soft and hard delete
- AC2: User ownership validation before deletion
- AC3: Deletion blocked if file has active shares
- AC4: Soft delete marks status = 'deleted', preserves metadata
- AC5: Hard delete removes from MinIO and database
- AC6: User quota updated immediately (-file_size, -1 file)
- AC7: storage.file.deleted event published with permanent flag
- AC8: Response includes success status and deletion type
- AC9: Response time <500ms

**API Reference**: `DELETE /api/v1/storage/files/{file_id}?user_id={user_id}&permanent={boolean}`

**Example Request**:
```
DELETE /api/v1/storage/files/file_abc123...?user_id=user_123&permanent=false
```

**Example Response**:
```json
{
  "success": true,
  "message": "File deleted successfully",
  "permanent": false
}
```

---

### Epic 2: Secure File Sharing

**Objective**: Enable secure, time-limited file sharing with granular permissions.

#### E2-US1: Create File Share
**As a** User
**I want to** share files with friends and colleagues
**So that** I can collaborate and share content securely

**Acceptance Criteria**:
- AC1: POST /api/v1/storage/shares creates secure share link
- AC2: Share ID generation (format: `share_[0-9a-f]{12}`)
- AC3: Permission model: view, download, delete (default: view only)
- AC4: Access control: password OR access token (required)
- AC5: Expiration validation: 1-720 hours (max 30 days)
- AC6: Optional download limits
- AC7: Share URL generation with token or password indication
- AC8: storage.file.shared event published
- AC9: Response includes share URL, expiry, permissions
- AC10: Response time <200ms

**API Reference**: `POST /api/v1/storage/shares`

**Example Request**:
```json
{
  "file_id": "file_abc123def4567890123456789012345678",
  "shared_by": "user_123",
  "shared_with_email": "friend@example.com",
  "permissions": {"view": true, "download": true, "delete": false},
  "password": "secret123",
  "expires_hours": 48,
  "max_downloads": 5
}
```

**Example Response**:
```json
{
  "share_id": "share_a1b2c3d4e5f6",
  "share_url": "http://localhost:8209/api/v1/storage/shares/share_a1b2c3d4e5f6",
  "access_token": null,
  "expires_at": "2025-12-17T14:30:00Z",
  "permissions": {"view": true, "download": true, "delete": false},
  "message": "File shared successfully"
}
```

#### E2-US2: Access Shared File
**As an** External Recipient
**I want to** access a shared file securely
**So that** I can view or download the content

**Acceptance Criteria**:
- AC1: GET /api/v1/storage/shares/{share_id} validates access
- AC2: Share validation: active, not expired, proper authentication
- AC3: Password authentication for password-protected shares
- AC4: Token authentication for token-based shares
- AC5: Download limit enforcement (max_downloads)
- AC6: Short-lived presigned URL generation (15min expiry)
- AC7: Download count increment on successful download access
- AC8: Owner privacy: user_id not exposed in shared access
- AC9: 404 response for invalid/expired shares (security)
- AC10: Response time <300ms

**API Reference**: `GET /api/v1/storage/shares/{share_id}?token={token}&password={password}`

**Example Request**:
```
GET /api/v1/storage/shares/share_a1b2c3d4e5f6?password=secret123
```

**Example Response**:
```json
{
  "file_id": "file_abc123...",
  "user_id": null,
  "file_name": "vacation_photo.jpg",
  "file_path": "users/user_123/2025/12/15/...",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "status": "available",
  "access_level": "private",
  "download_url": "https://minio.example.com/presigned-url-15min",
  "metadata": {"location": "vacation"},
  "tags": ["photo"],
  "uploaded_at": "2025-12-15T14:30:00Z",
  "updated_at": "2025-12-15T14:30:00Z"
}
```

---

### Epic 3: Quota Management

**Objective**: Implement fair usage policies with real-time quota tracking and enforcement.

#### E3-US1: Quota Validation on Upload
**As a** System
**I want to** enforce storage quotas during file upload
**So that** system resources are used fairly

**Acceptance Criteria**:
- AC1: Default user quota = 10GB (10,737,418,240 bytes)
- AC2: Quota records created automatically on first upload
- AC3: Upload validation: used_bytes + file_size ≤ total_quota_bytes
- AC4: Quota exceeded error with current usage information
- AC5: Atomic quota updates (used_bytes, file_count)
- AC6: Real-time quota tracking with immediate updates
- AC7: Quota recovery on file deletion
- AC8: Maximum file size = 500MB enforced
- AC9: Maximum files per user = 100,000

**Error Response (Quota Exceeded)**:
```json
{
  "detail": "Storage quota exceeded: 10GB/10GB. Delete files to free up space."
}
```

#### E3-US2: Storage Statistics
**As a** User
**I want to** see my storage usage and remaining space
**So that** I can manage my storage effectively

**Acceptance Criteria**:
- AC1: GET /api/v1/storage/stats returns comprehensive statistics
- AC2: Supports user_id and organization_id scopes
- AC3: Returns: total_quota_bytes, used_bytes, available_bytes, usage_percentage
- AC4: File count and statistics by type/status
- AC5: Usage percentage calculation (used/total * 100)
- AC6: Response time <200ms
- AC7: Organization stats aggregate from user quotas

**API Reference**: `GET /api/v1/storage/stats?user_id={user_id}`

**Example Response**:
```json
{
  "user_id": "user_123",
  "total_quota_bytes": 10737418240,
  "used_bytes": 5368709120,
  "available_bytes": 5368709120,
  "usage_percentage": 50.0,
  "file_count": 42,
  "by_type": {
    "image/jpeg": {"count": 30, "bytes": 4000000000},
    "application/pdf": {"count": 12, "bytes": 1368709120}
  },
  "by_status": {
    "available": 40,
    "deleted": 2
  }
}
```

---

### Epic 4: Organization and Team Support

**Objective**: Enable organization-based file management with team access controls.

#### E4-US1: Organization File Management
**As an** Organization Admin
**I want to** upload and manage team files
**So that** our team can collaborate effectively

**Acceptance Criteria**:
- AC1: File upload supports organization_id parameter
- AC2: Organization files visible to all org members when access_level=restricted
- AC3: Organization statistics aggregated from all user quotas
- AC4: File listing supports organization_id filter
- AC5: Organization admins can manage org files
- AC6: Team-based access controls enforced
- AC7: Organization quotas calculated as sum of user quotas

**Example Upload with Organization**:
```json
{
  "user_id": "user_123",
  "organization_id": "org_456",
  "access_level": "restricted",
  "file": [binary data]
}
```

---

### Epic 5: Advanced Features

**Objective**: Provide intelligent file management and optimization features.

#### E5-US1: Auto-Delete Configuration
**As a** User
**I want to** set files to auto-delete after a period
**So that** I can manage storage automatically

**Acceptance Criteria**:
- AC1: auto_delete_after_days parameter supported (1-365 days)
- AC2: Background job processes auto-deletion
- AC3: Notification before auto-deletion (configurable)
- AC4: Auto-deletion respects share status (warn if active shares exist)
- AC5: Quota recovery on auto-deletion
- AC6: Audit log of auto-deleted files

#### E5-US2: File Tagging and Metadata
**As a** User
**I want to** organize files with tags and metadata
**So that** I can find files easily

**Acceptance Criteria**:
- AC1: Flexible metadata storage (JSONB) supported
- AC2: Tag array support for categorization
- AC3: File listing supports tag filtering (future enhancement)
- AC4: Metadata searchable via file listing (future enhancement)
- AC5: Tags preserved in file sharing

**Example Metadata and Tags**:
```json
{
  "metadata": {
    "source": "mobile_app",
    "location": "beach_vacation",
    "camera": "iPhone_14_Pro",
    "gps_coordinates": {"lat": 25.7617, "lng": -80.1918}
  },
  "tags": ["photo", "vacation", "beach", "2025"]
}
```

#### E5-US3: RAG Integration
**As a** System
**I want to** enable document indexing for AI search
**So that** users can search document content

**Acceptance Criteria**:
- AC1: enable_indexing parameter controls RAG processing
- AC2: Default enable_indexing = true for document types
- AC3: Document Service subscribes to storage.file.uploaded events
- AC4: Only documents with enable_indexing=true sent for indexing
- AC5: Indexing failure doesn't block file operations
- AC6: Status tracking for indexing progress (future)

---

### Epic 6: Event-Driven Integration

**Objective**: Enable real-time synchronization with downstream services.

#### E6-US1: File Upload Events
**As a** Media Service
**I want to** receive notifications when files are uploaded
**So that** I can process images and videos

**Acceptance Criteria**:
- AC1: storage.file.uploaded event published on successful upload
- AC2: Event payload includes: file_id, file_name, file_size, content_type, user_id, organization_id, access_level, download_url, bucket_name, object_name
- AC3: Event published only after successful MinIO upload and database record creation
- AC4: Event publishing failures logged but don't block upload
- AC5: Event timestamp in ISO 8601 format
- AC6: Media Service processes images for thumbnails and AI analysis
- AC7: Document Service indexes documents if enable_indexing=true

#### E6-US2: File Deletion Events
**As an** Audit Service
**I want to** receive notifications when files are deleted
**So that** I can maintain compliance records

**Acceptance Criteria**:
- AC1: storage.file.deleted event published on file deletion
- AC2: Event payload includes: file_id, file_name, file_size, user_id, permanent, timestamp
- AC3: Event includes deletion type (soft vs hard)
- AC4: Media Service cleans up related media records
- AC5: Document Service removes from RAG index
- AC6: Album Service removes from photo albums

#### E6-US3: File Share Events
**As a** Notification Service
**I want to** receive notifications when files are shared
**So that** I can send share notifications

**Acceptance Criteria**:
- AC1: storage.file.shared event published on share creation
- AC2: Event payload includes: share_id, file_id, file_name, shared_by, shared_with, shared_with_email, expires_at
- AC3: Notification Service sends email to shared_with_email
- AC4: Audit Service logs sharing for compliance
- AC5: Analytics Service tracks sharing patterns

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8209`
- **Staging**: `https://staging-storage.isa.ai`
- **Production**: `https://storage.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Current**: Handled by API Gateway (JWT validation)
- **Header**: `Authorization: Bearer <token>`
- **User Context**: user_id extracted from JWT claims

### Core Endpoints Summary

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| POST | `/api/v1/storage/files/upload` | Multipart file upload | <2s |
| GET | `/api/v1/storage/files/{file_id}` | Get file info + download URL | <100ms |
| GET | `/api/v1/storage/files` | List files with pagination | <200ms |
| DELETE | `/api/v1/storage/files/{file_id}` | Delete file (soft/hard) | <500ms |
| POST | `/api/v1/storage/shares` | Create file share | <200ms |
| GET | `/api/v1/storage/shares/{share_id}` | Access shared file | <300ms |
| GET | `/api/v1/storage/stats` | Get storage statistics | <200ms |
| GET | `/health` | Health check | <20ms |
| GET | `/health/detailed` | Detailed health | <50ms |

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New file uploaded
- `400 Bad Request`: Validation error, quota exceeded, file type not allowed
- `401 Unauthorized`: Invalid share access
- `403 Forbidden`: Download limit exceeded, no permission
- `404 Not Found`: File/share not found
- `422 Validation Error`: Invalid input parameters
- `500 Internal Server Error`: Storage backend error, database error
- `503 Service Unavailable`: Database or MinIO unavailable

### Common Response Format

**Success Response**:
```json
{
  "file_id": "file_abc123...",
  "file_name": "photo.jpg",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "uploaded_at": "2025-12-15T14:30:00Z"
}
```

**Error Response**:
```json
{
  "detail": "Storage quota exceeded: 10GB/10GB"
}
```

### Rate Limits (Future)
- **Per User**: 1000 requests/hour
- **Per IP**: 5000 requests/hour
- **Upload**: 10 files/hour per user
- **Share Access**: 100 requests/hour per share

---

## Functional Requirements

### FR-1: File Upload
System SHALL provide secure multipart file upload with quota validation and metadata storage

### FR-2: File Access
System SHALL provide file metadata retrieval with automatic presigned URL regeneration

### FR-3: File Listing
System SHALL support paginated file listing with filtering capabilities

### FR-4: File Deletion
System SHALL support soft and hard file deletion with quota updates

### FR-5: File Sharing
System SHALL provide secure file sharing with permissions and expiration controls

### FR-6: Share Access
System SHALL validate share access and provide time-limited download URLs

### FR-7: Quota Management
System SHALL enforce user quotas with real-time tracking and validation

### FR-8: Storage Statistics
System SHALL provide comprehensive storage usage statistics and metrics

### FR-9: Organization Support
System SHALL support organization-based file management and access controls

### FR-10: Event Publishing
System SHALL publish events for all file lifecycle operations to NATS

---

## Non-Functional Requirements

### NFR-1: Performance
- **File Upload**: <2s (p95) for files up to 100MB
- **File Info Retrieval**: <100ms (p95)
- **File List**: <200ms for 100 results (p95)
- **Share Access**: <300ms (p95)
- **Statistics**: <200ms (p95)
- **Health Check**: <20ms (p99)

### NFR-2: Availability
- **Uptime**: 99.9% (excluding planned maintenance)
- **File Availability**: 99.95% for uploaded files
- **Share Availability**: 99.5% for active shares
- **Database Failover**: Automatic with <30s recovery
- **Graceful Degradation**: MinIO failures don't corrupt metadata

### NFR-3: Scalability
- **Concurrent Uploads**: 1000+ simultaneous uploads
- **Total Files**: 100M+ files supported
- **Storage Capacity**: 10PB+ storage supported
- **Users**: 10M+ users supported
- **Throughput**: 10K requests/second

### NFR-4: Security
- **Authentication**: JWT validation by API Gateway
- **Authorization**: User-scoped data access
- **Share Security**: Time-limited, permission-based access
- **URL Security**: Presigned URLs with automatic expiration
- **Data Privacy**: File isolation by user paths
- **Input Validation**: SQL injection prevention via parameterized queries

### NFR-5: Data Integrity
- **ACID Transactions**: Database operations wrapped in transactions
- **Atomic Quota Updates**: Quota changes are atomic
- **File Validation**: Checksum validation for uploads (future)
- **Backup Strategy**: Daily backups with point-in-time recovery
- **Audit Trail**: Complete file lifecycle tracking

### NFR-6: Storage Management
- **Multi-Provider**: Abstracted storage backend support
- **Cost Optimization**: Automatic lifecycle management (future)
- **Compression**: Optional file compression (future)
- **CDN Integration**: Global distribution for shared files (future)

### NFR-7: Observability
- **Structured Logging**: JSON logs for all operations
- **Metrics**: Storage usage, request latency, error rates
- **Tracing**: Request IDs for debugging
- **Health Monitoring**: Database and MinIO connectivity checks
- **Alerting**: Quota thresholds, error rates, service health

---

## Dependencies

### External Services

1. **MinIO**: Primary object storage backend
   - Endpoint: `isa-minio:9000`
   - Bucket: `isa-storage`
   - Access via presigned URLs only
   - SLA: 99.9% availability

2. **PostgreSQL gRPC Service**: Metadata storage
   - Host: `isa-postgres-grpc:50061`
   - Schema: `storage`
   - Tables: `files`, `file_shares`, `quotas`
   - SLA: 99.9% availability

3. **NATS Event Bus**: Event publishing
   - Host: `isa-nats:4222`
   - Subjects: `storage.file.*`
   - SLA: 99.9% availability

4. **Consul**: Service discovery and health checks
   - Host: `localhost:8500`
   - Service Name: `storage_service`
   - Health Check: HTTP `/health`
   - SLA: 99.9% availability

### Internal Dependencies
- **core.config_manager**: Configuration management
- **core.logger**: Structured logging
- **core.nats_client**: Event bus client
- **isa_common.consul_client**: Service registration
- **isa_common.AsyncPostgresClient**: Database client

### Downstream Services
- **Media Service**: Image/video processing, thumbnails, AI analysis
- **Document Service**: Document indexing for RAG and search
- **Album Service**: Photo album organization
- **Notification Service**: Share notifications and confirmations
- **Audit Service**: Compliance and change tracking
- **Analytics Service**: Usage metrics and reporting
- **Organization Service**: Team management

---

## Success Criteria

### Phase 1: Core Storage (Complete)
- [x] File upload with quota validation working
- [x] File metadata storage and retrieval functional
- [x] MinIO integration stable
- [x] PostgreSQL schema and operations working
- [x] Basic sharing functionality implemented
- [x] Event publishing for core operations

### Phase 2: Advanced Features (Complete)
- [x] Comprehensive sharing with permissions and expiry
- [x] Real-time quota management and statistics
- [x] Organization support implemented
- [x] Presigned URL management with auto-refresh
- [x] File deletion with share validation
- [x] Health checks and monitoring

### Phase 3: Production Hardening (Current)
- [x] Comprehensive test coverage (Component, Integration, API, Smoke)
- [x] Performance benchmarks met (sub-2s uploads)
- [x] Security review completed
- [x] Monitoring and alerting setup
- [x] Load testing completed
- [ ] Production deployment and validation

### Phase 4: Optimization and Scale (Future)
- [ ] Multi-provider storage support (S3, Azure)
- [ ] CDN integration for shared files
- [ ] Advanced search and filtering
- [ ] Auto-cleanup and lifecycle policies
- [ ] Cost optimization features
- [ ] Advanced analytics and reporting

---

## Out of Scope

The following are explicitly NOT included in this release:

1. **Video Streaming**: Real-time video streaming capabilities
2. **File Versioning**: Multiple versions of same file
3. **Real-time Collaboration**: Simultaneous file editing
4. **Advanced Search**: Content-based search within files
5. **File Conversion**: Format conversion between file types
6. **Backup and Recovery**: Self-service file restoration
7. **File Encryption**: Client-side encryption (future)
8. **Batch Operations**: Bulk file operations (future)
9. **WebDAV Support**: WebDAV protocol for file access
10. **File Linking**: Linking between related files

---

## Appendix: Request/Response Examples

### 1. File Upload

**Request**:
```bash
curl -X POST http://localhost:8209/api/v1/storage/files/upload \
  -F "file=@vacation_photo.jpg" \
  -F "user_id=user_123" \
  -F "access_level=private" \
  -F "metadata={\"source\":\"mobile_app\",\"location\":\"beach\"}" \
  -F "tags=photo,vacation,beach" \
  -F "auto_delete_after_days=30" \
  -F "enable_indexing=true"
```

**Response**:
```json
{
  "file_id": "file_abc123def4567890123456789012345678",
  "file_path": "users/user_123/2025/12/15/20251215_143000_a1b2c3d4_vacation_photo.jpg",
  "download_url": "https://minio.example.com/presigned-url-24h",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "uploaded_at": "2025-12-15T14:30:00Z",
  "message": "File uploaded successfully"
}
```

### 2. File Share Creation

**Request**:
```bash
curl -X POST http://localhost:8209/api/v1/storage/shares \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "file_id": "file_abc123def4567890123456789012345678",
    "shared_by": "user_123",
    "shared_with_email": "friend@example.com",
    "permissions": {"view": true, "download": true},
    "password": "secret123",
    "expires_hours": 48
  }'
```

**Response**:
```json
{
  "share_id": "share_a1b2c3d4e5f6",
  "share_url": "http://localhost:8209/api/v1/storage/shares/share_a1b2c3d4e5f6",
  "access_token": null,
  "expires_at": "2025-12-17T14:30:00Z",
  "permissions": {"view": true, "download": true, "delete": false},
  "message": "File shared successfully"
}
```

### 3. Storage Statistics

**Request**:
```bash
curl -X GET "http://localhost:8209/api/v1/storage/stats?user_id=user_123" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "user_id": "user_123",
  "total_quota_bytes": 10737418240,
  "used_bytes": 5368709120,
  "available_bytes": 5368709120,
  "usage_percentage": 50.0,
  "file_count": 42,
  "by_type": {
    "image/jpeg": {"count": 30, "bytes": 4000000000},
    "application/pdf": {"count": 12, "bytes": 1368709120}
  },
  "by_status": {
    "available": 40,
    "deleted": 2
  }
}
```

### 4. Shared File Access

**Request**:
```bash
curl -X GET "http://localhost:8209/api/v1/storage/shares/share_a1b2c3d4e5f6?password=secret123"
```

**Response**:
```json
{
  "file_id": "file_abc123...",
  "user_id": null,
  "file_name": "vacation_photo.jpg",
  "file_path": "users/user_123/2025/12/15/...",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "status": "available",
  "access_level": "private",
  "download_url": "https://minio.example.com/presigned-url-15min",
  "metadata": {"location": "beach"},
  "tags": ["photo"],
  "uploaded_at": "2025-12-15T14:30:00Z",
  "updated_at": "2025-12-15T14:30:00Z"
}
```

---

## Migration Notes

### Initial Setup
**Status**: Complete
**Target**: Day 1

Storage Service initial deployment includes:
- PostgreSQL schema creation (`storage.files`, `storage.file_shares`, `storage.quotas`)
- MinIO bucket creation (`isa-storage`)
- Default quota configuration (10GB per user)
- Event publisher setup for NATS integration

### Data Migration
**Status**: Not Required
**Target**: N/A

Storage Service is net-new, no data migration required from existing systems.

### Configuration Migration
**Status**: Complete
**Target**: Day 1

Configuration managed through environment variables:
- MinIO connection settings
- PostgreSQL gRPC service discovery
- NATS event bus configuration
- Consul service registration
- Default quota limits and file type restrictions

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Storage Service Product Team
**Related Documents**:
- Domain Context: docs/domain/storage_service.md
- Design Doc: docs/design/storage_service.md
- Data Contract: tests/contracts/storage/data_contract.py
- Logic Contract: tests/contracts/storage/logic_contract.md
