# Storage Service Logic Contract

**Business Rules and Specifications for Storage Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for storage service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Authorization Matrix](#authorization-matrix)
4. [API Contracts](#api-contracts)
5. [Event Contracts](#event-contracts)
6. [Performance SLAs](#performance-slas)
7. [Edge Cases](#edge-cases)

---

## Business Rules

### BR-001: File Upload
**Given**: Valid file upload request with multipart/form-data
**When**: User uploads a file
**Then**:
- File ID generated (format: `file_[0-9a-f]{32}`)
- File persisted to MinIO bucket (`isa-storage`)
- Database record created in `storage.files` table
- Event `file.uploaded` published to NATS
- User quota updated (+file_size, +1 file_count)
- Presigned download URL generated (24h expiry)
- Object name: `users/{user_id}/{YYYY}/{MM}/{DD}/{timestamp}_{uuid}_{ext}`

**Validation Rules**:
- `user_id`: Required
- `file`: Required, size ≤ 500MB
- `content_type`: Must be in allowed_types list
- Quota: `used_bytes + file_size ≤ total_quota_bytes`

**Edge Cases**:
- Quota exceeded → **400 Bad Request** `{"detail": "Storage quota exceeded"}`
- Invalid file type → **400 Bad Request** `{"detail": "File type not allowed: ..."}`
- File size > 500MB → **400 Bad Request** `{"detail": "File too large. Maximum size: 500.0MB"}`
- MinIO failure → **500 Internal Server Error**

---

### BR-002: File Download (Get File Info)
**Given**: Valid file_id and user_id
**When**: User requests file information
**Then**:
- File metadata returned from database
- If download_url expired → regenerate presigned URL (24h expiry)
- User must have permission to access file (see Authorization Matrix)

**Validation Rules**:
- `file_id`: Required
- `user_id`: Required
- File must exist
- User must have read permission

**Edge Cases**:
- File not found → **404 Not Found**
- No permission → **403 Forbidden**
- Deleted file → **404 Not Found**

---

### BR-003: File Listing
**Given**: Valid user_id
**When**: User lists files
**Then**:
- Returns files owned by user or shared with user
- Supports filtering by: status, prefix, organization_id
- Supports pagination: limit (1-1000), offset (≥0)
- Expired download URLs regenerated in batch
- Results sorted by uploaded_at DESC

**Default Values**:
- `limit`: 100
- `offset`: 0
- `status`: None (all statuses)

---

### BR-004: File Deletion
**Given**: Valid file_id and user_id
**When**: User deletes a file
**Then**:
- If `permanent=false` (soft delete):
  - File status updated to `deleted` in database
  - File remains in MinIO
  - User quota updated (-file_size, -1 file_count)
- If `permanent=true` (hard delete):
  - File deleted from MinIO
  - File record deleted from database
  - User quota updated
- Event `file.deleted` published

**Validation Rules**:
- User must be file owner OR org admin
- Cannot delete if file is referenced by active shares

**Edge Cases**:
- File not found → **404 Not Found**
- No permission → **403 Forbidden**
- MinIO delete fails → Continue with DB update (log error)

---

### BR-005: File Sharing
**Given**: Valid file_id and share request
**When**: File owner creates a share
**Then**:
- Share ID generated (format: `share_[0-9a-f]{12}`)
- Access token generated (UUID hex) if no password
- Share record created in `storage.file_shares` table
- Share URL: `http://{host}:{port}/api/v1/storage/shares/{share_id}?token={token}`
- Expiration: `now + expires_hours` (1-720 hours)
- Event `file.shared` published

**Permission Model**:
```json
{
  "view": true,       // Can view file metadata
  "download": false,  // Can download file
  "delete": false     // Can delete file (dangerous!)
}
```

**Validation Rules**:
- `file_id`: Must exist
- `shared_by`: Must be file owner
- `expires_hours`: 1-720 (max 30 days)
- `password`: Min 4 characters if provided
- Either `shared_with` or `shared_with_email` should be provided

**Edge Cases**:
- File not found → **404 Not Found**
- Not file owner → **403 Forbidden**
- Invalid expires_hours → **422 Validation Error**

---

### BR-006: Accessing Shared Files
**Given**: Valid share_id and access_token/password
**When**: User accesses shared file
**Then**:
- Share must be active (`is_active=true`)
- Share must not be expired (`expires_at > now`)
- If password protected → password must match
- If max_downloads set → download_count < max_downloads
- Download count incremented if `permissions.download=true`
- Presigned URL generated (15min expiry for shares)

**Validation Rules**:
- Share must exist
- Share must be active and not expired
- Password must match (if protected)
- Download limit not exceeded

**Edge Cases**:
- Share not found → **404 Not Found**
- Share expired → **404 Not Found** (treat as not found)
- Invalid password → **401 Unauthorized**
- Download limit exceeded → **403 Forbidden**

---

### BR-007: Storage Quota Management
**Given**: user_id or organization_id
**When**: User/org quota is checked
**Then**:
- If no quota record exists → create default (10GB)
- Used bytes tracked accurately
- File count tracked accurately
- Usage percentage calculated: `(used_bytes / total_quota_bytes) * 100`

**Default Quotas**:
- User: 10GB (10,737,418,240 bytes)
- Max file size: 500MB (524,288,000 bytes)

**Quota Update Rules**:
- Upload: `+file_size`, `+1 file_count`
- Delete: `-file_size`, `-1 file_count`
- Updates must be atomic

---

## State Machines

### File Status State Machine

```
┌─────────┐
│UPLOADING│ Initial state during upload
└────┬────┘
     │
     ▼
┌─────────┐
│AVAILABLE│ File successfully uploaded
└────┬────┘
     │
     ├────► DELETED   (soft delete, can restore)
     │
     ├────► ARCHIVED  (moved to cold storage)
     │
     └────► FAILED    (upload/processing failed)
```

**Valid Transitions**:
- `UPLOADING` → `AVAILABLE` (upload success)
- `UPLOADING` → `FAILED` (upload failure)
- `AVAILABLE` → `DELETED` (soft delete)
- `AVAILABLE` → `ARCHIVED` (archive)
- `DELETED` → `AVAILABLE` (restore, not implemented yet)
- `ARCHIVED` → `AVAILABLE` (restore from archive)

**Invalid Transitions** (should reject):
- `FAILED` → `AVAILABLE`
- `DELETED` → `ARCHIVED`

---

### File Share Status

```
┌────────┐
│ ACTIVE │ Share is active and accessible
└───┬────┘
    │
    ├────► EXPIRED   (expires_at < now)
    │
    └────► INACTIVE  (manually deactivated)
```

---

## Authorization Matrix

### File Operations

| Action              | Owner | Org Admin | Org Member | Shared User (view) | Shared User (download) | Public |
|---------------------|-------|-----------|------------|-------------------|----------------------|--------|
| **Upload**          | ✅     | ✅         | ✅          | ❌                 | ❌                    | ❌      |
| **Get Info**        | ✅     | ✅         | ✅*         | ✅                 | ✅                    | ❌      |
| **Download**        | ✅     | ✅         | ✅*         | ❌                 | ✅                    | ❌      |
| **Update Metadata** | ✅     | ✅         | ❌          | ❌                 | ❌                    | ❌      |
| **Delete**          | ✅     | ✅         | ❌          | ❌                 | ❌                    | ❌      |
| **Share**           | ✅     | ❌         | ❌          | ❌                 | ❌                    | ❌      |

*Only if file access_level is `shared` or `public`

### Access Level Permissions

| Access Level | Owner | Org Admin | Org Member | Authenticated | Anonymous |
|--------------|-------|-----------|------------|---------------|-----------|
| `private`    | ✅     | ✅         | ❌          | ❌             | ❌         |
| `restricted` | ✅     | ✅         | ✅          | ❌             | ❌         |
| `shared`     | ✅     | ✅         | ✅          | ✅*            | ❌         |
| `public`     | ✅     | ✅         | ✅          | ✅             | ✅         |

*Authenticated users can access if explicitly shared

---

## API Contracts

### POST /api/v1/storage/files/upload

**Request**: `multipart/form-data`
- `file`: Binary file data (required)
- `user_id`: String (required)
- `organization_id`: String (optional)
- `access_level`: Enum (optional, default: `private`)
- `metadata`: JSON string (optional)
- `tags`: JSON array string (optional)
- `auto_delete_after_days`: Integer (optional)
- `enable_indexing`: Boolean (optional, default: `true`)

**Success Response**: `200 OK`
```json
{
  "file_id": "file_abc123...",
  "file_path": "users/user_123/2025/12/10/...",
  "download_url": "https://...",
  "file_size": 1048576,
  "content_type": "image/jpeg",
  "uploaded_at": "2025-12-10T12:00:00Z",
  "message": "File uploaded successfully"
}
```

**Error Responses**:
- `400 Bad Request`: Quota exceeded, invalid file type, file too large
- `422 Validation Error`: Missing required fields
- `500 Internal Server Error`: MinIO failure, database error

---

### GET /api/v1/storage/files/{file_id}

**Request Parameters**:
- `file_id`: String (path)
- `user_id`: String (query, required)

**Success Response**: `200 OK`
```json
{
  "file_id": "file_abc123",
  "file_name": "photo.jpg",
  "file_path": "users/.../photo.jpg",
  "file_size": 1048576,
  "content_type": "image/jpeg",
  "status": "available",
  "access_level": "private",
  "download_url": "https://...",
  "metadata": {},
  "tags": ["photo"],
  "uploaded_at": "2025-12-10T12:00:00Z",
  "updated_at": "2025-12-10T12:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Missing user_id
- `403 Forbidden`: No permission
- `404 Not Found`: File not found

---

### GET /api/v1/storage/files

**Request Parameters**:
- `user_id`: String (query, required)
- `organization_id`: String (query, optional)
- `prefix`: String (query, optional)
- `status`: Enum (query, optional)
- `limit`: Integer (query, optional, default: 100, max: 1000)
- `offset`: Integer (query, optional, default: 0)

**Success Response**: `200 OK`
```json
[
  {
    "file_id": "file_abc123",
    "file_name": "photo.jpg",
    ...
  }
]
```

---

### DELETE /api/v1/storage/files/{file_id}

**Request Parameters**:
- `file_id`: String (path)
- `user_id`: String (query, required)
- `permanent`: Boolean (query, optional, default: false)

**Success Response**: `200 OK`
```json
{
  "success": true,
  "message": "File deleted successfully"
}
```

**Error Responses**:
- `403 Forbidden`: Not file owner
- `404 Not Found`: File not found

---

### POST /api/v1/storage/shares

**Request**: `application/json`
```json
{
  "file_id": "file_abc123",
  "shared_by": "user_123",
  "shared_with_email": "friend@example.com",
  "permissions": {"view": true, "download": true},
  "password": "secret",
  "expires_hours": 48,
  "max_downloads": 5
}
```

**Success Response**: `200 OK`
```json
{
  "share_id": "share_abc123",
  "share_url": "http://localhost:8209/api/v1/storage/shares/share_abc123?token=...",
  "access_token": "...",
  "expires_at": "2025-12-12T12:00:00Z",
  "permissions": {"view": true, "download": true, "delete": false},
  "message": "File shared successfully"
}
```

---

### GET /api/v1/storage/shares/{share_id}

**Request Parameters**:
- `share_id`: String (path)
- `token`: String (query, required if no password)
- `password`: String (query, required if password protected)

**Success Response**: `200 OK`
Returns `FileInfoResponse` with presigned URL (15min expiry)

**Error Responses**:
- `401 Unauthorized`: Invalid password
- `403 Forbidden`: Download limit exceeded
- `404 Not Found`: Share not found or expired

---

### GET /api/v1/storage/stats

**Request Parameters**:
- `user_id`: String (query, optional)
- `organization_id`: String (query, optional)

**Success Response**: `200 OK`
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

## Event Contracts

### Event: file.uploaded

**Published**: After successful file upload
**Subject**: `storage.file.uploaded`
**Payload**:
```json
{
  "event_type": "FILE_UPLOADED",
  "source": "storage_service",
  "timestamp": "2025-12-10T12:00:00Z",
  "data": {
    "file_id": "file_abc123",
    "file_name": "photo.jpg",
    "file_size": 1048576,
    "content_type": "image/jpeg",
    "user_id": "user_123",
    "organization_id": "org_456",
    "access_level": "private",
    "download_url": "https://...",
    "bucket_name": "user-storage_service-isa-storage",
    "object_name": "users/user_123/2025/12/10/..."
  }
}
```

**Subscribers**:
- `media_service`: Processes images/videos (AI analysis, thumbnails)
- `document_service`: Indexes documents for RAG
- `audit_service`: Records file upload audit log

---

### Event: file.deleted

**Published**: After successful file deletion
**Subject**: `storage.file.deleted`
**Payload**:
```json
{
  "event_type": "FILE_DELETED",
  "source": "storage_service",
  "timestamp": "2025-12-10T12:00:00Z",
  "data": {
    "file_id": "file_abc123",
    "file_name": "photo.jpg",
    "file_size": 1048576,
    "user_id": "user_123",
    "permanent": false
  }
}
```

**Subscribers**:
- `media_service`: Cleans up related media records
- `album_service`: Removes file from albums
- `audit_service`: Records deletion audit log

---

### Event: file.shared

**Published**: After successful file share creation
**Subject**: `storage.file.shared`
**Payload**:
```json
{
  "event_type": "FILE_SHARED",
  "source": "storage_service",
  "timestamp": "2025-12-10T12:00:00Z",
  "data": {
    "share_id": "share_abc123",
    "file_id": "file_abc123",
    "file_name": "photo.jpg",
    "shared_by": "user_123",
    "shared_with": "user_456",
    "shared_with_email": "friend@example.com",
    "expires_at": "2025-12-12T12:00:00Z"
  }
}
```

**Subscribers**:
- `notification_service`: Sends email notification to recipient

---

## Performance SLAs

### Response Time Targets (p95)

| Operation        | Target  | Max Acceptable |
|------------------|---------|----------------|
| File Upload      | < 2s    | < 5s           |
| File Info (GET)  | < 100ms | < 500ms        |
| File List        | < 200ms | < 1s           |
| File Delete      | < 500ms | < 2s           |
| Create Share     | < 200ms | < 1s           |
| Access Share     | < 300ms | < 1s           |
| Get Stats        | < 500ms | < 2s           |

### Throughput Targets

- Concurrent uploads: 100 req/s
- Read operations: 1000 req/s
- MinIO presigned URL generation: 500 req/s

### Resource Limits

- Max file size: 500MB
- Max concurrent uploads per user: 10
- Max files per user: 100,000
- Max shares per file: 100

---

## Edge Cases

### EC-001: Concurrent Uploads
**Scenario**: User uploads multiple files simultaneously
**Expected**: All uploads succeed independently
**Edge Case**: Quota check race condition
**Solution**: Use atomic quota updates with database locks

---

### EC-002: Upload During Quota Update
**Scenario**: User uploads file while quota is being recalculated
**Expected**: Quota check uses current accurate value
**Solution**: Read-modify-write with transaction isolation

---

### EC-003: MinIO Unavailable
**Scenario**: MinIO service is down during upload
**Expected**: Return 500 error, don't create DB record
**Solution**: Upload to MinIO first, then create DB record

---

### EC-004: Database Unavailable
**Scenario**: PostgreSQL is down during upload
**Expected**: Return 500 error, file may remain in MinIO (orphaned)
**Solution**: Background cleanup job removes orphaned files

---

### EC-005: Expired Presigned URL
**Scenario**: User tries to download with expired URL
**Expected**: API regenerates URL automatically
**Solution**: Check expiry in `get_file_info()`, regenerate if needed

---

### EC-006: File Deleted While Shared
**Scenario**: File owner deletes file that has active shares
**Expected**: Shares become inaccessible (404)
**Solution**: Allow deletion, shares reference missing file

---

### EC-007: Share Accessed After Expiry
**Scenario**: User has share URL, tries after expiration
**Expected**: 404 Not Found (treat as non-existent)
**Solution**: Check `expires_at < now` in query

---

### EC-008: Large File Upload Timeout
**Scenario**: User uploads 500MB file, connection slow
**Expected**: Upload succeeds with extended timeout
**Solution**: HTTP client timeout set to 300s

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-XXX success scenarios)
- ✅ Validation errors (400, 422)
- ✅ Authorization failures (401, 403)
- ✅ Not found errors (404)
- ✅ State transitions (valid and invalid)
- ✅ Event publishing (verify published)
- ✅ Edge cases (EC-XXX scenarios)
- ✅ Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-10
**Owner**: Storage Service Team
