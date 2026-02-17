# Storage Service - Design Document

## Design Overview

**Service Name**: storage_service
**Port**: 8209
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-15

### Design Principles
1. **File-First Architecture**: Files are primary citizens, metadata is secondary
2. **Idempotent Operations**: All file operations safe for retry
3. **Event-Driven Sync**: Loose coupling via NATS for file lifecycle events
4. **Multi-Provider Support**: Abstracted storage backend (MinIO primary)
5. **Security by Default**: All operations authenticated and authorized
6. **Graceful Degradation**: Storage failures don't corrupt metadata

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Mobile Apps, Web Apps, Admin Dashboard, Other Services) │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                 Storage Service (Port 8209)               │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)             │ │
│  │  - Request validation (Pydantic models)               │ │
│  │  - Multipart file upload handling                     │ │
│  │  - Response formatting                                │ │
│  │  - Error handling & exception handlers                │ │
│  │  - Health checks (/health, /health/detailed)          │ │
│  │  - Lifecycle management (startup/shutdown)            │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Service Layer (storage_service.py)              │ │
│  │  - Business logic (validation, quota checks)         │ │
│  │  - File upload orchestration                          │ │
│  │  - Presigned URL management                           │ │
│  │  - File sharing logic                                 │ │
│  │  - Quota management                                   │ │
│  │  - Event publishing orchestration                     │ │
│  │  - Statistics aggregation                             │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Repository Layer (storage_repository.py)        │ │
│  │  - Database CRUD operations                           │ │
│  │  - PostgreSQL gRPC communication                      │ │
│  │  - Query construction (parameterized)                 │ │
│  │  - Result parsing (proto to Pydantic)                 │ │
│  │  - No business logic                                  │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Storage Backend (storage_backend.py)            │ │
│  │  - MinIO S3-compatible operations                     │ │
│  │  - Presigned URL generation                          │ │
│  │  - File existence checks                              │ │
│  │  - Object deletion                                    │ │
│  │  - Multi-provider abstraction                         │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Event Publishing (events/publishers.py)          │ │
│  │  - NATS event bus integration                         │ │
│  │  - Event model construction                           │ │
│  │  - Async non-blocking publishing                      │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐
│  PostgreSQL  │ │    NATS     │ │   MinIO    │
│   (gRPC)     │ │  (Events)   │ │   (S3)     │
│              │ │             │ │            │
│  Schema:     │ │  Subjects:  │ │  Buckets:  │
│  storage     │ │  storage.*  │ │  isa-storage│
│  Tables:     │ │             │ │            │
│  files       │ │  Publishers:│ │  Objects:  │
│  file_shares │ │  - uploaded │ │  users/{   │
│  quotas      │ │  - deleted  │ │  user_id}/ │
│              │ │  - shared   │ │  ...       │
│  Indexes:    │ │             │ │            │
│  - file_id   │ │             │ │            │
│  - user_id   │ │             │ │            │
│  - status    │ │             │ │            │
└──────────────┘ └─────────────┘ └────────────┘

Optional:
┌──────────────────┐
│ media_service    │ ← Event subscriber for image processing
│ (Port 8211)     │   (thumbnails, AI analysis)
└──────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Storage Service                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Service   │───→│ Repository   │   │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │   │
│  │             │    │             │    │              │   │
│  │ - File      │    │ - Storage   │    │ - Storage    │   │
│  │   Upload    │    │   Service   │    │   Repository │   │
│  │ - Share     │    │             │    │              │   │
│  │   Request   │    │             │    │              │   │
│  │ - File Info │    │             │    │              │   │
│  │   Response  │    │             │    │              │   │
│  │ - Storage   │    │             │    │              │   │
│  │   Stats     │    │             │    │              │   │
│  └─────────────┘    └─────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑           │
│         │                  │                    │           │
│  ┌──────┴──────────────────┴────────────────────┴───────┐  │
│  │              FastAPI Main (main.py)                   │  │
│  │  - Dependency Injection (get_storage_service)        │  │
│  │  - Route Handlers (8 endpoints)                      │  │
│  │  - Exception Handlers (custom errors)                │  │
│  │  - Multipart upload handling                          │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Storage Backend                          │  │
│  │  (storage_backend.py)                                │  │
│  │  - MinIO S3 client                                   │  │
│  │  - Presigned URL generation                          │  │
│  │  - File operations (put, get, delete)                │  │
│  │  - Bucket management                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Event Publishers                         │  │
│  │  (events/publishers.py, events/models.py)            │  │
│  │  - publish_file_uploaded                              │  │
│  │  - publish_file_deleted                               │  │
│  │  - publish_file_shared                                │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Factory Pattern                       │  │
│  │              (factory.py, protocols.py)               │  │
│  │  - create_storage_service (production)                │  │
│  │  - StorageRepositoryProtocol (interface)             │  │
│  │  - StorageBackendProtocol (interface)                │  │
│  │  - Enables dependency injection for tests             │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Multipart file upload processing
- Request validation via Pydantic models
- Route definitions (8 endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                  # Basic health check
GET /health/detailed                         # Database & MinIO connectivity

# File Management
POST /api/v1/storage/files/upload            # Multipart file upload
GET  /api/v1/storage/files/{file_id}         # Get file info + download URL
GET  /api/v1/storage/files                   # List files with pagination
DELETE /api/v1/storage/files/{file_id}       # Delete file (soft/hard)

# File Sharing
POST /api/v1/storage/shares                  # Create file share
GET  /api/v1/storage/shares/{share_id}       # Access shared file

# Statistics
GET /api/v1/storage/stats                   # Storage statistics
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus("storage_service")
    await storage_microservice.initialize(event_bus=event_bus)

    # Subscribe to events (handlers from events/handlers.py)
    event_handlers = get_event_handlers()
    for event_type, handler in event_handlers.items():
        await event_bus.subscribe_to_events(event_type, handler)

    # Consul registration (metadata includes routes)
    if config.consul_enabled:
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    await storage_microservice.shutdown()
    if event_bus:
        await event_bus.close()
```

### 2. Service Layer (storage_service.py)

**Class**: `StorageService`

**Responsibilities**:
- Business logic execution
- File upload orchestration
- Quota validation and management
- Presigned URL generation
- File sharing logic
- Event publishing coordination
- Input validation
- Error handling and custom exceptions

**Key Methods**:
```python
class StorageService:
    def __init__(
        self,
        repository: StorageRepositoryProtocol,
        backend: StorageBackendProtocol,
        event_bus: Optional[EventBusProtocol] = None
    ):
        self.repository = repository
        self.backend = backend
        self.event_bus = event_bus

    async def upload_file(
        self,
        file_data: bytes,
        content_type: str,
        file_name: str,
        request: FileUploadRequestContract
    ) -> FileUploadResponseContract:
        """
        Handle file upload with quota validation and metadata storage.
        """
        # 1. Validate user quota
        quota = await self.repository.get_user_quota(request.user_id)
        if quota.used_bytes + len(file_data) > quota.total_quota_bytes:
            raise StorageQuotaExceededError(f"Storage quota exceeded: {quota.used_bytes}/{quota.total_quota_bytes}")

        # 2. Validate file type
        allowed_types = await self.repository.get_allowed_content_types()
        if content_type not in allowed_types:
            raise UnsupportedFileTypeError(f"File type not allowed: {content_type}")

        # 3. Validate file size
        max_size = await self.repository.get_max_file_size()
        if len(file_data) > max_size:
            raise FileTooLargeError(f"File too large. Maximum size: {max_size/1024/1024:.1f}MB")

        # 4. Generate file metadata
        file_id = StorageTestDataFactory.make_file_id()
        timestamp = datetime.now(timezone.utc)
        object_name = f"users/{request.user_id}/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{timestamp.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{file_name}"

        # 5. Upload to MinIO
        try:
            await self.backend.put_object(
                bucket_name="isa-storage",
                object_name=object_name,
                data=file_data,
                content_type=content_type
            )
        except Exception as e:
            raise StorageBackendError(f"Failed to upload file to storage backend: {str(e)}")

        # 6. Create database record
        file_record = await self.repository.create_file_record(
            file_id=file_id,
            user_id=request.user_id,
            organization_id=request.organization_id,
            file_name=file_name,
            file_path=object_name,
            file_size=len(file_data),
            content_type=content_type,
            access_level=request.access_level,
            metadata=request.metadata,
            tags=request.tags,
            auto_delete_after_days=request.auto_delete_after_days,
            enable_indexing=request.enable_indexing
        )

        # 7. Update user quota
        await self.repository.update_user_quota(
            user_id=request.user_id,
            used_bytes_delta=len(file_data),
            file_count_delta=1
        )

        # 8. Generate presigned download URL
        download_url = await self.backend.generate_presigned_url(
            bucket_name="isa-storage",
            object_name=object_name,
            expires_in=86400  # 24 hours
        )

        # 9. Publish event (non-blocking)
        if self.event_bus:
            await publish_file_uploaded(
                self.event_bus,
                file_id=file_id,
                file_name=file_name,
                file_size=len(file_data),
                content_type=content_type,
                user_id=request.user_id,
                organization_id=request.organization_id,
                access_level=request.access_level,
                download_url=download_url,
                bucket_name="isa-storage",
                object_name=object_name
            )

        return FileUploadResponseContract(
            file_id=file_id,
            file_path=object_name,
            download_url=download_url,
            file_size=len(file_data),
            content_type=content_type,
            uploaded_at=file_record.created_at,
            message="File uploaded successfully"
        )

    async def get_file_info(
        self,
        file_id: str,
        user_id: str
    ) -> FileInfoResponseContract:
        """Get file information with access validation and URL regeneration"""
        # 1. Get file record with permission check
        file_record = await self.repository.get_file_by_id(file_id, user_id)
        if not file_record:
            raise FileNotFoundError(f"File not found: {file_id}")

        # 2. Check download URL expiry
        download_url = file_record.download_url
        if not download_url or self._is_url_expired(file_record.download_url_expires_at):
            # Regenerate presigned URL
            download_url = await self.backend.generate_presigned_url(
                bucket_name="isa-storage",
                object_name=file_record.file_path,
                expires_in=86400  # 24 hours
            )
            # Update database with new URL and expiry
            await self.repository.update_download_url(file_id, download_url)

        return FileInfoResponseContract(
            file_id=file_record.file_id,
            user_id=file_record.user_id,
            file_name=file_record.file_name,
            file_path=file_record.file_path,
            file_size=file_record.file_size,
            content_type=file_record.content_type,
            status=file_record.status,
            access_level=file_record.access_level,
            download_url=download_url,
            metadata=file_record.metadata,
            tags=file_record.tags,
            uploaded_at=file_record.created_at,
            updated_at=file_record.updated_at
        )

    async def list_files(
        self,
        request: FileListRequestContract
    ) -> List[FileInfoResponseContract]:
        """List files with filtering and pagination"""
        files = await self.repository.list_files(
            user_id=request.user_id,
            organization_id=request.organization_id,
            prefix=request.prefix,
            status=request.status,
            limit=request.limit,
            offset=request.offset
        )

        # Batch regenerate expired URLs
        for file_record in files:
            if not file_record.download_url or self._is_url_expired(file_record.download_url_expires_at):
                download_url = await self.backend.generate_presigned_url(
                    bucket_name="isa-storage",
                    object_name=file_record.file_path,
                    expires_in=86400
                )
                await self.repository.update_download_url(file_record.file_id, download_url)
                file_record.download_url = download_url

        return [FileInfoResponseContract(
            file_id=f.file_id,
            user_id=f.user_id,
            file_name=f.file_name,
            file_path=f.file_path,
            file_size=f.file_size,
            content_type=f.content_type,
            status=f.status,
            access_level=f.access_level,
            download_url=f.download_url,
            metadata=f.metadata,
            tags=f.tags,
            uploaded_at=f.created_at,
            updated_at=f.updated_at
        ) for f in files]

    async def delete_file(
        self,
        file_id: str,
        user_id: str,
        permanent: bool = False
    ) -> Dict[str, Any]:
        """Delete file (soft or hard)"""
        # 1. Get file record with permission check
        file_record = await self.repository.get_file_by_id(file_id, user_id)
        if not file_record:
            raise FileNotFoundError(f"File not found: {file_id}")

        # 2. Check for active shares
        active_shares = await self.repository.count_active_shares(file_id)
        if active_shares > 0:
            raise FileHasActiveSharesError(f"Cannot delete file with {active_shares} active shares")

        # 3. Perform deletion
        if permanent:
            # Hard delete: remove from MinIO and database
            try:
                await self.backend.delete_object(
                    bucket_name="isa-storage",
                    object_name=file_record.file_path
                )
            except Exception as e:
                # Log error but continue with DB deletion
                logger.warning(f"Failed to delete object from MinIO: {str(e)}")
            
            await self.repository.hard_delete_file(file_id)
        else:
            # Soft delete: mark as deleted in database
            await self.repository.soft_delete_file(file_id)

        # 4. Update user quota
        await self.repository.update_user_quota(
            user_id=user_id,
            used_bytes_delta=-file_record.file_size,
            file_count_delta=-1
        )

        # 5. Publish event
        if self.event_bus:
            await publish_file_deleted(
                self.event_bus,
                file_id=file_id,
                file_name=file_record.file_name,
                file_size=file_record.file_size,
                user_id=user_id,
                permanent=permanent
            )

        return {
            "success": True,
            "message": "File deleted successfully",
            "permanent": permanent
        }

    async def create_file_share(
        self,
        request: FileShareRequestContract
    ) -> FileShareResponseContract:
        """Create file share with permissions and expiry"""
        # 1. Validate file exists and user owns it
        file_record = await self.repository.get_file_by_id(request.file_id, request.shared_by)
        if not file_record:
            raise FileNotFoundError(f"File not found: {request.file_id}")

        # 2. Validate expiry
        if not (1 <= request.expires_hours <= 720):
            raise ValidationError("expires_hours must be between 1 and 720")

        # 3. Create share record
        share_id = StorageTestDataFactory.make_share_id()
        access_token = None
        if not request.password:
            access_token = uuid.uuid4().hex

        expires_at = datetime.now(timezone.utc) + timedelta(hours=request.expires_hours)

        share_record = await self.repository.create_file_share(
            share_id=share_id,
            file_id=request.file_id,
            shared_by=request.shared_by,
            shared_with=request.shared_with,
            shared_with_email=request.shared_with_email,
            permissions=request.permissions,
            password=request.password,
            access_token=access_token,
            expires_at=expires_at,
            max_downloads=request.max_downloads
        )

        # 4. Generate share URL
        share_url = f"http://{config.host}:{config.port}/api/v1/storage/shares/{share_id}"
        if access_token:
            share_url += f"?token={access_token}"

        # 5. Publish event
        if self.event_bus:
            await publish_file_shared(
                self.event_bus,
                share_id=share_id,
                file_id=request.file_id,
                file_name=file_record.file_name,
                shared_by=request.shared_by,
                shared_with=request.shared_with,
                shared_with_email=request.shared_with_email,
                expires_at=expires_at
            )

        return FileShareResponseContract(
            share_id=share_id,
            share_url=share_url,
            access_token=access_token,
            expires_at=expires_at,
            permissions=request.permissions,
            message="File shared successfully"
        )

    async def access_shared_file(
        self,
        share_id: str,
        token: Optional[str] = None,
        password: Optional[str] = None
    ) -> FileInfoResponseContract:
        """Access file via share link"""
        # 1. Get share record
        share_record = await self.repository.get_share_by_id(share_id)
        if not share_record:
            raise FileNotFoundError(f"Share not found: {share_id}")

        # 2. Validate share is active and not expired
        if not share_record.is_active or share_record.expires_at < datetime.now(timezone.utc):
            raise FileNotFoundError(f"Share not found or expired: {share_id}")

        # 3. Validate access method
        if share_record.password:
            if password != share_record.password:
                raise UnauthorizedError("Invalid password")
        elif share_record.access_token:
            if token != share_record.access_token:
                raise UnauthorizedError("Invalid access token")
        else:
            raise UnauthorizedError("No valid access method")

        # 4. Check download limit
        if share_record.max_downloads and share_record.download_count >= share_record.max_downloads:
            raise ForbiddenError("Download limit exceeded")

        # 5. Get file record
        file_record = await self.repository.get_file_by_id_no_user_check(share_record.file_id)
        if not file_record or file_record.status != FileStatus.AVAILABLE:
            raise FileNotFoundError(f"File not available: {share_record.file_id}")

        # 6. Generate short-lived presigned URL (15 minutes)
        download_url = await self.backend.generate_presigned_url(
            bucket_name="isa-storage",
            object_name=file_record.file_path,
            expires_in=900  # 15 minutes
        )

        # 7. Increment download count if download permission
        if share_record.permissions.get("download", False):
            await self.repository.increment_share_downloads(share_id)

        return FileInfoResponseContract(
            file_id=file_record.file_id,
            user_id=None,  # Don't expose owner for shared files
            file_name=file_record.file_name,
            file_path=file_record.file_path,
            file_size=file_record.file_size,
            content_type=file_record.content_type,
            status=file_record.status,
            access_level=file_record.access_level,
            download_url=download_url,
            metadata=file_record.metadata,
            tags=file_record.tags,
            uploaded_at=file_record.created_at,
            updated_at=file_record.updated_at
        )

    async def get_storage_stats(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> StorageStatsResponseContract:
        """Get storage statistics"""
        stats = await self.repository.get_storage_stats(user_id, organization_id)
        
        # Calculate usage percentage
        usage_percentage = 0.0
        if stats.get("total_quota_bytes", 0) > 0:
            usage_percentage = (stats["used_bytes"] / stats["total_quota_bytes"]) * 100

        return StorageStatsResponseContract(
            user_id=user_id,
            organization_id=organization_id,
            total_quota_bytes=stats["total_quota_bytes"],
            used_bytes=stats["used_bytes"],
            available_bytes=stats["total_quota_bytes"] - stats["used_bytes"],
            usage_percentage=usage_percentage,
            file_count=stats["file_count"],
            by_type=stats.get("by_type", {}),
            by_status=stats.get("by_status", {})
        )

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        db_connected = await self.repository.check_connection()
        storage_connected = await self.backend.check_connection()
        
        return {
            "status": "healthy" if db_connected and storage_connected else "unhealthy",
            "database_connected": db_connected,
            "storage_connected": storage_connected,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _is_url_expired(self, expires_at: Optional[datetime]) -> bool:
        """Check if presigned URL has expired"""
        if not expires_at:
            return True
        return expires_at < datetime.now(timezone.utc)
```

**Custom Exceptions**:
```python
class StorageServiceError(Exception):
    """Base exception for storage service"""
    pass

class FileNotFoundError(StorageServiceError):
    """File not found"""
    pass

class StorageQuotaExceededError(StorageServiceError):
    """Storage quota exceeded"""
    pass

class UnsupportedFileTypeError(StorageServiceError):
    """File type not allowed"""
    pass

class FileTooLargeError(StorageServiceError):
    """File exceeds maximum size"""
    pass

class StorageBackendError(StorageServiceError):
    """Storage backend operation failed"""
    pass

class FileHasActiveSharesError(StorageServiceError):
    """Cannot delete file with active shares"""
    pass

class UnauthorizedError(StorageServiceError):
    """Unauthorized access"""
    pass

class ForbiddenError(StorageServiceError):
    """Access forbidden"""
    pass

class ValidationError(StorageServiceError):
    """Validation error"""
    pass
```

### 3. Repository Layer (storage_repository.py)

**Class**: `StorageRepository`

**Responsibilities**:
- PostgreSQL CRUD operations
- gRPC communication with postgres_grpc_service
- Query construction (parameterized)
- Result parsing (proto JSONB to Python dict)
- No business logic

**Key Methods**:
```python
class StorageRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        # Discover PostgreSQL gRPC service via Consul
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id='storage_service')
        self.schema = "storage"
        self.files_table = "files"
        self.file_shares_table = "file_shares"
        self.quotas_table = "quotas"

    # File Operations
    async def create_file_record(
        self,
        file_id: str,
        user_id: str,
        organization_id: Optional[str],
        file_name: str,
        file_path: str,
        file_size: int,
        content_type: str,
        access_level: FileAccessLevel,
        metadata: Dict[str, Any],
        tags: List[str],
        auto_delete_after_days: Optional[int],
        enable_indexing: bool
    ) -> File:
        """Create file record in database"""
        async with self.db:
            await self.db.execute(
                f"""INSERT INTO {self.schema}.{self.files_table}
                    (file_id, user_id, organization_id, file_name, file_path, 
                     file_size, content_type, status, access_level, 
                     metadata, tags, auto_delete_after_days, enable_indexing)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)""",
                params=[
                    file_id, user_id, organization_id, file_name, file_path,
                    file_size, content_type, FileStatus.AVAILABLE.value, access_level.value,
                    metadata, tags, auto_delete_after_days, enable_indexing
                ]
            )

        return await self.get_file_by_id_no_user_check(file_id)

    async def get_file_by_id(
        self,
        file_id: str,
        user_id: str
    ) -> Optional[File]:
        """Get file by ID with user permission check"""
        async with self.db:
            result = await self.db.query_row(
                f"""SELECT * FROM {self.schema}.{self.files_table}
                    WHERE file_id = $1 AND user_id = $2 AND status = 'available'""",
                params=[file_id, user_id]
            )
        if result:
            return self._row_to_file(result)
        return None

    async def get_file_by_id_no_user_check(
        self,
        file_id: str
    ) -> Optional[File]:
        """Get file by ID without user permission check"""
        async with self.db:
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.files_table} WHERE file_id = $1",
                params=[file_id]
            )
        if result:
            return self._row_to_file(result)
        return None

    async def list_files(
        self,
        user_id: str,
        organization_id: Optional[str],
        prefix: Optional[str],
        status: Optional[FileStatus],
        limit: int,
        offset: int
    ) -> List[File]:
        """List files with filters"""
        conditions = ["user_id = $1"]
        params = [user_id]
        param_count = 2

        if organization_id:
            conditions.append(f"organization_id = ${param_count}")
            params.append(organization_id)
            param_count += 1

        if prefix:
            conditions.append(f"file_path LIKE ${param_count}")
            params.append(f"%{prefix}%")
            param_count += 1

        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status.value)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions)
        params.extend([limit, offset])

        query = f"""
            SELECT * FROM {self.schema}.{self.files_table}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """

        async with self.db:
            rows = await self.db.query(query, params=params)

        return [self._row_to_file(row) for row in rows] if rows else []

    async def soft_delete_file(self, file_id: str) -> bool:
        """Soft delete file (mark as deleted)"""
        async with self.db:
            await self.db.execute(
                f"UPDATE {self.schema}.{self.files_table} SET status = 'deleted', updated_at = $1 WHERE file_id = $2",
                params=[datetime.now(tz=timezone.utc), file_id]
            )
        return True

    async def hard_delete_file(self, file_id: str) -> bool:
        """Hard delete file (remove from database)"""
        async with self.db:
            await self.db.execute(
                f"DELETE FROM {self.schema}.{self.files_table} WHERE file_id = $1",
                params=[file_id]
            )
        return True

    async def update_download_url(self, file_id: str, download_url: str) -> bool:
        """Update download URL and expiry"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        async with self.db:
            await self.db.execute(
                f"""UPDATE {self.schema}.{self.files_table}
                    SET download_url = $1, download_url_expires_at = $2, updated_at = $3
                    WHERE file_id = $4""",
                params=[download_url, expires_at, datetime.now(tz=timezone.utc), file_id]
            )
        return True

    # File Share Operations
    async def create_file_share(
        self,
        share_id: str,
        file_id: str,
        shared_by: str,
        shared_with: Optional[str],
        shared_with_email: Optional[str],
        permissions: Dict[str, bool],
        password: Optional[str],
        access_token: Optional[str],
        expires_at: datetime,
        max_downloads: Optional[int]
    ) -> FileShare:
        """Create file share record"""
        async with self.db:
            await self.db.execute(
                f"""INSERT INTO {self.schema}.{self.file_shares_table}
                    (share_id, file_id, shared_by, shared_with, shared_with_email,
                     permissions, password, access_token, expires_at, max_downloads)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                params=[
                    share_id, file_id, shared_by, shared_with, shared_with_email,
                    permissions, password, access_token, expires_at, max_downloads
                ]
            )

        return await self.get_share_by_id(share_id)

    async def get_share_by_id(self, share_id: str) -> Optional[FileShare]:
        """Get share by ID"""
        async with self.db:
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.file_shares_table} WHERE share_id = $1",
                params=[share_id]
            )
        if result:
            return self._row_to_file_share(result)
        return None

    async def count_active_shares(self, file_id: str) -> int:
        """Count active shares for a file"""
        async with self.db:
            result = await self.db.query_row(
                f"""SELECT COUNT(*) as count FROM {self.schema}.{self.file_shares_table}
                    WHERE file_id = $1 AND is_active = TRUE AND expires_at > NOW()""",
                params=[file_id]
            )
        return result['count'] if result else 0

    async def increment_share_downloads(self, share_id: str) -> bool:
        """Increment share download count"""
        async with self.db:
            await self.db.execute(
                f"""UPDATE {self.schema}.{self.file_shares_table}
                    SET download_count = download_count + 1, last_downloaded_at = $1
                    WHERE share_id = $2""",
                params=[datetime.now(tz=timezone.utc), share_id]
            )
        return True

    # Quota Operations
    async def get_user_quota(self, user_id: str) -> UserQuota:
        """Get user quota (create default if not exists)"""
        async with self.db:
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.quotas_table} WHERE user_id = $1",
                params=[user_id]
            )

        if not result:
            # Create default quota
            await self.create_default_quota(user_id)
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.quotas_table} WHERE user_id = $1",
                params=[user_id]
            )

        return self._row_to_user_quota(result)

    async def create_default_quota(self, user_id: str) -> UserQuota:
        """Create default user quota (10GB)"""
        default_quota = 10 * 1024 * 1024 * 1024  # 10GB
        async with self.db:
            await self.db.execute(
                f"""INSERT INTO {self.schema}.{self.quotas_table}
                    (user_id, total_quota_bytes, used_bytes, file_count)
                    VALUES ($1, $2, $3, $4)""",
                params=[user_id, default_quota, 0, 0]
            )

        return await self.get_user_quota(user_id)

    async def update_user_quota(
        self,
        user_id: str,
        used_bytes_delta: int,
        file_count_delta: int
    ) -> bool:
        """Update user quota usage"""
        async with self.db:
            await self.db.execute(
                f"""UPDATE {self.schema}.{self.quotas_table}
                    SET used_bytes = used_bytes + $1,
                        file_count = file_count + $2,
                        updated_at = $3
                    WHERE user_id = $4""",
                params=[used_bytes_delta, file_count_delta, datetime.now(tz=timezone.utc), user_id]
            )
        return True

    # Statistics
    async def get_storage_stats(
        self,
        user_id: Optional[str],
        organization_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get storage statistics"""
        conditions = []
        params = []

        if user_id:
            conditions.append(f"user_id = ${len(params) + 1}")
            params.append(user_id)

        if organization_id:
            conditions.append(f"organization_id = ${len(params) + 1}")
            params.append(organization_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with self.db:
            # Get quota and usage stats
            quota_result = await self.db.query_row(
                f"""SELECT COALESCE(SUM(total_quota_bytes), 0) as total_quota,
                           COALESCE(SUM(used_bytes), 0) as used_bytes,
                           COALESCE(SUM(file_count), 0) as file_count
                    FROM {self.schema}.{self.quotas_table}
                    {where_clause.replace('user_id', 'q.user_id') if 'user_id' in where_clause else where_clause}""",
                params=params
            )

            # Get stats by file type
            type_stats = await self.db.query(
                f"""SELECT content_type, COUNT(*) as count, SUM(file_size) as bytes
                    FROM {self.schema}.{self.files_table}
                    {where_clause}
                    GROUP BY content_type""",
                params=params
            )

            # Get stats by status
            status_stats = await self.db.query(
                f"""SELECT status, COUNT(*) as count
                    FROM {self.schema}.{self.files_table}
                    {where_clause}
                    GROUP BY status""",
                params=params
            )

        by_type = {}
        for row in type_stats:
            by_type[row['content_type']] = {
                "count": row['count'],
                "bytes": row['bytes']
            }

        by_status = {}
        for row in status_stats:
            by_status[row['status']] = row['count']

        total_quota = quota_result['total_quota'] if quota_result else 0
        used_bytes = quota_result['used_bytes'] if quota_result else 0
        file_count = quota_result['file_count'] if quota_result else 0

        return {
            "total_quota_bytes": total_quota,
            "used_bytes": used_bytes,
            "file_count": file_count,
            "by_type": by_type,
            "by_status": by_status
        }

    # Configuration
    async def get_allowed_content_types(self) -> List[str]:
        """Get allowed file content types"""
        # This could be stored in a config table
        return [
            "image/jpeg", "image/png", "image/gif", "image/webp",
            "application/pdf", "text/plain", "text/csv",
            "application/json", "application/xml",
            "video/mp4", "video/quicktime", "video/x-msvideo",
            "audio/mpeg", "audio/wav", "audio/ogg"
        ]

    async def get_max_file_size(self) -> int:
        """Get maximum allowed file size"""
        # 500MB default
        return 500 * 1024 * 1024

    # Health Check
    async def check_connection(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.db:
                await self.db.query_row("SELECT 1")
            return True
        except Exception:
            return False

    # Row converters
    def _row_to_file(self, row: Dict[str, Any]) -> File:
        """Convert database row to File model"""
        return File(
            file_id=row["file_id"],
            user_id=row["user_id"],
            organization_id=row.get("organization_id"),
            file_name=row["file_name"],
            file_path=row["file_path"],
            file_size=row["file_size"],
            content_type=row["content_type"],
            status=FileStatus(row["status"]),
            access_level=FileAccessLevel(row["access_level"]),
            download_url=row.get("download_url"),
            download_url_expires_at=row.get("download_url_expires_at"),
            metadata=row.get("metadata", {}),
            tags=row.get("tags", []),
            auto_delete_after_days=row.get("auto_delete_after_days"),
            enable_indexing=row.get("enable_indexing", True),
            created_at=row["created_at"],
            updated_at=row.get("updated_at")
        )

    def _row_to_file_share(self, row: Dict[str, Any]) -> FileShare:
        """Convert database row to FileShare model"""
        return FileShare(
            share_id=row["share_id"],
            file_id=row["file_id"],
            shared_by=row["shared_by"],
            shared_with=row.get("shared_with"),
            shared_with_email=row.get("shared_with_email"),
            permissions=row["permissions"],
            password=row.get("password"),
            access_token=row.get("access_token"),
            expires_at=row["expires_at"],
            max_downloads=row.get("max_downloads"),
            download_count=row.get("download_count", 0),
            is_active=row.get("is_active", True),
            created_at=row["created_at"],
            last_downloaded_at=row.get("last_downloaded_at")
        )

    def _row_to_user_quota(self, row: Dict[str, Any]) -> UserQuota:
        """Convert database row to UserQuota model"""
        return UserQuota(
            user_id=row["user_id"],
            total_quota_bytes=row["total_quota_bytes"],
            used_bytes=row["used_bytes"],
            file_count=row["file_count"],
            created_at=row["created_at"],
            updated_at=row.get("updated_at")
        )
```

### 4. Storage Backend Layer (storage_backend.py)

**Class**: `MinIOStorageBackend`

**Responsibilities**:
- MinIO S3-compatible operations
- Presigned URL generation
- File existence checks
- Object deletion
- Bucket management
- Multi-provider abstraction

**Key Methods**:
```python
class MinIOStorageBackend:
    def __init__(self, config: ConfigManager):
        self.endpoint = config.minio_endpoint
        self.access_key = config.minio_access_key
        self.secret_key = config.minio_secret_key
        self.secure = config.minio_secure
        
        # Initialize MinIO client
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

    async def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str
    ) -> bool:
        """Upload object to MinIO"""
        try:
            # Create bucket if not exists
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
            
            # Upload object
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upload object to MinIO: {str(e)}")
            raise

    async def generate_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires_in: int = 3600
    ) -> str:
        """Generate presigned URL for object access"""
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires_in)
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise

    async def delete_object(
        self,
        bucket_name: str,
        object_name: str
    ) -> bool:
        """Delete object from MinIO"""
        try:
            self.client.remove_object(bucket_name, object_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete object from MinIO: {str(e)}")
            raise

    async def check_connection(self) -> bool:
        """Check MinIO connectivity"""
        try:
            # List buckets to check connection
            buckets = self.client.list_buckets()
            return True
        except Exception:
            return False

    async def object_exists(
        self,
        bucket_name: str,
        object_name: str
    ) -> bool:
        """Check if object exists"""
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except Exception:
            return False
```

---

## Database Schema Design

### PostgreSQL Schema: `storage`

#### Table: storage.files

```sql
-- Create storage schema
CREATE SCHEMA IF NOT EXISTS storage;

-- Create files table
CREATE TABLE IF NOT EXISTS storage.files (
    -- Primary Key
    file_id VARCHAR(255) PRIMARY KEY,

    -- Ownership
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- File Information
    file_name VARCHAR(512) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_size BIGINT NOT NULL,
    content_type VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'available' CHECK (status IN ('uploading', 'available', 'deleted', 'failed', 'archived')),
    access_level VARCHAR(50) DEFAULT 'private' CHECK (access_level IN ('private', 'restricted', 'shared', 'public')),

    -- URLs
    download_url TEXT,
    download_url_expires_at TIMESTAMPTZ,

    -- Metadata (flexible JSONB)
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT '{}',

    -- Lifecycle
    auto_delete_after_days INTEGER,
    enable_indexing BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_files_user_id ON storage.files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_organization_id ON storage.files(organization_id);
CREATE INDEX IF NOT EXISTS idx_files_status ON storage.files(status);
CREATE INDEX IF NOT EXISTS idx_files_access_level ON storage.files(access_level);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON storage.files(created_at);
CREATE INDEX IF NOT EXISTS idx_files_content_type ON storage.files(content_type);
CREATE INDEX IF NOT EXISTS idx_files_metadata ON storage.files USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_files_tags ON storage.files USING GIN(tags);

-- Comments
COMMENT ON TABLE storage.files IS 'File metadata and ownership records';
COMMENT ON COLUMN storage.files.file_id IS 'Unique file identifier';
COMMENT ON COLUMN storage.files.user_id IS 'File owner user ID';
COMMENT ON COLUMN storage.files.organization_id IS 'Optional organization ID';
COMMENT ON COLUMN storage.files.file_name IS 'Original filename';
COMMENT ON COLUMN storage.files.file_path IS 'Storage object path';
COMMENT ON COLUMN storage.files.file_size IS 'File size in bytes';
COMMENT ON COLUMN storage.files.content_type IS 'MIME type';
COMMENT ON COLUMN storage.files.status IS 'File status (uploading, available, deleted, failed, archived)';
COMMENT ON COLUMN storage.files.access_level IS 'Access level (private, restricted, shared, public)';
COMMENT ON COLUMN storage.files.download_url IS 'Presigned download URL';
COMMENT ON COLUMN storage.files.download_url_expires_at IS 'URL expiry timestamp';
COMMENT ON COLUMN storage.files.metadata IS 'File metadata (JSONB)';
COMMENT ON COLUMN storage.files.tags IS 'File tags array';
COMMENT ON COLUMN storage.files.auto_delete_after_days IS 'Auto-delete after N days (optional)';
COMMENT ON COLUMN storage.files.enable_indexing IS 'Enable RAG indexing';
```

#### Table: storage.file_shares

```sql
-- Create file_shares table
CREATE TABLE IF NOT EXISTS storage.file_shares (
    -- Primary Key
    share_id VARCHAR(255) PRIMARY KEY,

    -- File Reference
    file_id VARCHAR(255) NOT NULL REFERENCES storage.files(file_id) ON DELETE CASCADE,

    -- Sharing Information
    shared_by VARCHAR(255) NOT NULL,
    shared_with VARCHAR(255),
    shared_with_email VARCHAR(255),

    -- Permissions (JSONB)
    permissions JSONB NOT NULL DEFAULT '{"view": true, "download": false, "delete": false}'::jsonb,

    -- Access Control
    password VARCHAR(255),
    access_token VARCHAR(255),

    -- Expiration and Limits
    expires_at TIMESTAMPTZ NOT NULL,
    max_downloads INTEGER,

    -- Usage Tracking
    download_count INTEGER DEFAULT 0,
    last_downloaded_at TIMESTAMPTZ,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_file_shares_file_id ON storage.file_shares(file_id);
CREATE INDEX IF NOT EXISTS idx_file_shares_shared_by ON storage.file_shares(shared_by);
CREATE INDEX IF NOT EXISTS idx_file_shares_shared_with ON storage.file_shares(shared_with);
CREATE INDEX IF NOT EXISTS idx_file_shares_email ON storage.file_shares(shared_with_email);
CREATE INDEX IF NOT EXISTS idx_file_shares_expires_at ON storage.file_shares(expires_at);
CREATE INDEX IF NOT EXISTS idx_file_shares_is_active ON storage.file_shares(is_active);
CREATE INDEX IF NOT EXISTS idx_file_shares_access_token ON storage.file_shares(access_token);

-- Comments
COMMENT ON TABLE storage.file_shares IS 'File sharing records with permissions';
COMMENT ON COLUMN storage.file_shares.share_id IS 'Unique share identifier';
COMMENT ON COLUMN storage.file_shares.file_id IS 'Referenced file ID';
COMMENT ON COLUMN storage.file_shares.shared_by IS 'User who shared the file';
COMMENT ON COLUMN storage.file_shares.shared_with IS 'User ID shared with (optional)';
COMMENT ON COLUMN storage.file_shares.shared_with_email IS 'Email shared with (optional)';
COMMENT ON COLUMN storage.file_shares.permissions IS 'Share permissions (view, download, delete)';
COMMENT ON COLUMN storage.file_shares.password IS 'Optional password protection';
COMMENT ON COLUMN storage.file_shares.access_token IS 'Access token for password-less shares';
COMMENT ON COLUMN storage.file_shares.expires_at IS 'Share expiration time';
COMMENT ON COLUMN storage.file_shares.max_downloads IS 'Maximum download limit (optional)';
COMMENT ON COLUMN storage.file_shares.download_count IS 'Current download count';
COMMENT ON COLUMN storage.file_shares.last_downloaded_at IS 'Last download timestamp';
COMMENT ON COLUMN storage.file_shares.is_active IS 'Share active status';
```

#### Table: storage.quotas

```sql
-- Create quotas table
CREATE TABLE IF NOT EXISTS storage.quotas (
    -- Primary Key
    user_id VARCHAR(255) PRIMARY KEY,

    -- Quota Limits
    total_quota_bytes BIGINT NOT NULL DEFAULT 10737418240, -- 10GB default
    used_bytes BIGINT NOT NULL DEFAULT 0,
    file_count INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_quotas_used_bytes ON storage.quotas(used_bytes);
CREATE INDEX IF NOT EXISTS idx_quotas_file_count ON storage.quotas(file_count);

-- Comments
COMMENT ON TABLE storage.quotas IS 'User storage quota tracking';
COMMENT ON COLUMN storage.quotas.user_id IS 'User ID';
COMMENT ON COLUMN storage.quotas.total_quota_bytes IS 'Total storage quota in bytes';
COMMENT ON COLUMN storage.quotas.used_bytes IS 'Used storage in bytes';
COMMENT ON COLUMN storage.quotas.file_count IS 'Number of files owned';
```

### Index Strategy

1. **Primary Keys** (`file_id`, `share_id`, `user_id`): Clustered indexes for fast lookups
2. **User ID Index** (`idx_files_user_id`): Filter files by owner
3. **Status Index** (`idx_files_status`): Filter by file status
4. **Access Level Index** (`idx_files_access_level`): Filter by access permissions
5. **Created At Index** (`idx_files_created_at`): Sort by upload time
6. **JSONB Indexes** (`idx_files_metadata`, `idx_files_tags`): GIN indexes for metadata and tags queries
7. **Share Expiry Index** (`idx_file_shares_expires_at`): Cleanup expired shares

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
storage.file.uploaded         # File successfully uploaded
storage.file.deleted          # File deleted (soft or hard)
storage.file.shared           # File share created
```

### Event Models (events/models.py)

```python
class FileUploadedEventData(BaseModel):
    """Event: storage.file.uploaded"""
    event_type: str = "FILE_UPLOADED"
    source: str = "storage_service"
    timestamp: datetime
    data: Dict[str, Any]

class FileDeletedEventData(BaseModel):
    """Event: storage.file.deleted"""
    event_type: str = "FILE_DELETED"
    source: str = "storage_service"
    timestamp: datetime
    data: Dict[str, Any]

class FileSharedEventData(BaseModel):
    """Event: storage.file.shared"""
    event_type: str = "FILE_SHARED"
    source: str = "storage_service"
    timestamp: datetime
    data: Dict[str, Any]
```

### Event Flow Diagram

```
┌─────────────┐
│   Client    │ (Mobile App, Web App)
└──────┬──────┘
       │ POST /files/upload
       ↓
┌──────────────────┐
│  Storage Service │
│                  │
│  1. Validate     │
│  2. Check Quota  │
│  3. Upload to    │───→ MinIO (isa-storage bucket)
│     MinIO       │         │
│  4. Store Metadata├────→ PostgreSQL (storage.files)
│  5. Update Quota │         │
│  6. Publish      │         │ Success
└──────────────────┘         │
       │                     ↓
       │              ┌──────────────┐
       │              │ Return File  │
       │              │ Info Response│
       │              └──────────────┘
       │ Event: storage.file.uploaded
       ↓
┌─────────────────┐
│   NATS Bus      │
│ Subject:        │
│ storage.file.   │
│ uploaded        │
└────────┬────────┘
         │
         ├──→ Media Service (process images/videos)
         ├──→ Document Service (index for RAG)
         ├──→ Audit Service (log upload)
         ├──→ Analytics Service (track usage)
         └──→ Notification Service (upload confirmation)
```

---

## Data Flow Diagrams

### 1. File Upload Flow

```
Client uploads file: photo.jpg (2MB)
    │
    ↓
POST /api/v1/storage/files/upload
Content-Type: multipart/form-data
Form Data:
- file: [binary data]
- user_id: "user_123"
- access_level: "private"
- tags: ["photo", "vacation"]
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│           StorageService.upload_file()                     │
│                                                             │
│  Step 1: Validate quota                                    │
│    repository.get_user_quota(user_123) ──────────────────→ PostgreSQL:
│                                                      ←─────────┤ SELECT * FROM storage.quotas WHERE user_id = $1
│    Result: 10GB total, 5GB used (OK)                       │         │
│                                                             │         │
│  Step 2: Validate file type                                │         │
│    repository.get_allowed_content_types() ─────────────────→ [cached]
│                                                      ←─────────┤ Result: ["image/jpeg", ...]
│    Content-Type: image/jpeg ✓                               │         │
│                                                             │         │
│  Step 3: Validate file size                                │         │
│    repository.get_max_file_size() ────────────────────────→ [cached]
│                                                      ←─────────┤ Result: 500MB
│    File size: 2MB ✓                                        │         │
│                                                             │         │
│  Step 4: Generate metadata                                  │         │
│    file_id = "file_abc123..."                               │         │
│    object_name = "users/user_123/2025/12/15/..."          │         │
│                                                             │         │
│  Step 5: Upload to MinIO                                   │         │
│    backend.put_object() ───────────────────────────────────→ MinIO:
│                                                      ←─────────┤ PUT /isa-storage/users/user_123/...
│    Success                                                 │         │
│                                                             │         │
│  Step 6: Store metadata                                    │         │
│    repository.create_file_record()──────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ INSERT INTO storage.files...
│    Success                                                 │         │
│                                                             │         │
│  Step 7: Update quota                                      │         │
│    repository.update_user_quota()──────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ UPDATE storage.quotas...
│    Success (used_bytes += 2MB, file_count += 1)            │         │
│                                                             │         │
│  Step 8: Generate presigned URL                             │         │
│    backend.generate_presigned_url()────────────────────────→ MinIO:
│                                                      ←─────────┤ GET presigned URL (24h)
│    URL: https://minio.example.com/...                      │         │
│                                                             │         │
│  Step 9: Publish event                                     │         │
│    publish_file_uploaded()──────────────────────────────────→ NATS:
│                                                             │   storage.file.uploaded
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
Return FileUploadResponseContract:
{
  "file_id": "file_abc123...",
  "file_path": "users/user_123/...",
  "download_url": "https://minio.example.com/...",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "uploaded_at": "2025-12-15T10:00:00Z",
  "message": "File uploaded successfully"
}
    │
    ↓
                                                               Event Subscribers Process:
┌─────────────────────────────────────────────────────────────┐
│                  Event Subscribers                         │
│ - Media Service: Create thumbnails, AI analysis            │
│ - Document Service: Index for RAG (if enable_indexing)     │
│ - Audit Service: Log file upload for compliance           │
│ - Analytics Service: Track storage usage metrics          │
│ - Notification Service: Send upload confirmation           │
└─────────────────────────────────────────────────────────────┘
```

### 2. File Download Flow

```
Client requests file info: file_abc123
    │
    ↓
GET /api/v1/storage/files/file_abc123?user_id=user_123
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│           StorageService.get_file_info()                   │
│                                                             │
│  Step 1: Get file record with permission check             │
│    repository.get_file_by_id()────────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ SELECT * FROM storage.files 
│    Result: File record (user_123 matches) ✓                │         WHERE file_id = $1 AND user_id = $2
│                                                             │         │
│  Step 2: Check download URL expiry                         │         │
│    download_url_expires_at = 2025-12-14T10:00:00Z            │         │
│    Current time = 2025-12-15T10:00:00Z                     │         │
│    URL expired ✓                                            │         │
│                                                             │         │
│  Step 3: Regenerate presigned URL                          │         │
│    backend.generate_presigned_url()────────────────────────→ MinIO:
│                                                      ←─────────┤ GET presigned URL (24h)
│    New URL expires: 2025-12-16T10:00:00Z                   │         │
│                                                             │         │
│  Step 4: Update database with new URL                      │         │
│    repository.update_download_url()────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ UPDATE storage.files SET download_url = $1...
│    Success                                                  │         │
│                                                             │         │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
Return FileInfoResponseContract:
{
  "file_id": "file_abc123",
  "user_id": "user_123",
  "file_name": "photo.jpg",
  "file_path": "users/user_123/...",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "status": "available",
  "access_level": "private",
  "download_url": "https://minio.example.com/presigned-url",
  "metadata": {},
  "tags": ["photo", "vacation"],
  "uploaded_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-15T10:00:00Z"
}
    │
    ↓
Client downloads file via presigned URL (direct to MinIO)
```

### 3. File Sharing Flow

```
User shares file: file_abc123 with friend@example.com
    │
    ↓
POST /api/v1/storage/shares
{
  "file_id": "file_abc123",
  "shared_by": "user_123",
  "shared_with_email": "friend@example.com",
  "permissions": {"view": true, "download": true},
  "expires_hours": 48
}
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│           StorageService.create_file_share()               │
│                                                             │
│  Step 1: Validate file exists and user owns it             │
│    repository.get_file_by_id()────────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ SELECT * FROM storage.files 
│    Result: File owned by user_123 ✓                        │         WHERE file_id = $1 AND user_id = $2
│                                                             │         │
│  Step 2: Validate expiry (48h = within 1-720h range) ✓      │         │
│                                                             │         │
│  Step 3: Create share record                               │         │
│    share_id = "share_xyz789"                               │         │
│    access_token = "abc123def456"                           │         │
│    expires_at = 2025-12-17T10:00:00Z                       │         │
│    repository.create_file_share()──────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ INSERT INTO storage.file_shares...
│    Success                                                  │         │
│                                                             │         │
│  Step 4: Generate share URL                                │         │
│    share_url = "http://localhost:8209/api/v1/storage/      │         │
│               shares/share_xyz789?token=abc123def456"      │         │
│                                                             │         │
│  Step 5: Publish event                                     │         │
│    publish_file_shared()──────────────────────────────────→ NATS:
│                                                             │   storage.file.shared
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
Return FileShareResponseContract:
{
  "share_id": "share_xyz789",
  "share_url": "http://localhost:8209/api/v1/storage/shares/share_xyz789?token=abc123def456",
  "access_token": "abc123def456",
  "expires_at": "2025-12-17T10:00:00Z",
  "permissions": {"view": true, "download": true, "delete": false},
  "message": "File shared successfully"
}
    │
    ↓
                                                               Event Subscriber:
┌─────────────────────────────────────────────────────────────┐
│                Notification Service                        │
│ - Send email to friend@example.com with share link         │
│ - Include file details and expiry information              │
└─────────────────────────────────────────────────────────────┘
```

### 4. Shared File Access Flow

```
Recipient clicks share link
    │
    ↓
GET /api/v1/storage/shares/share_xyz789?token=abc123def456
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│           StorageService.access_shared_file()               │
│                                                             │
│  Step 1: Get share record                                  │
│    repository.get_share_by_id()───────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ SELECT * FROM storage.file_shares 
│    Result: Share record found ✓                            │         WHERE share_id = $1
│                                                             │         │
│  Step 2: Validate share is active and not expired           │         │
│    is_active = true ✓                                       │         │
│    expires_at = 2025-12-17T10:00:00Z                       │         │
│    Current time = 2025-12-15T12:00:00Z ✓                   │         │
│                                                             │         │
│  Step 3: Validate access method                             │         │
│    access_token = "abc123def456" (matches) ✓               │         │
│                                                             │         │
│  Step 4: Check download limit                               │         │
│    max_downloads = null (no limit) ✓                        │         │
│    download_count = 0                                        │         │
│                                                             │         │
│  Step 5: Get file record                                    │         │
│    repository.get_file_by_id_no_user_check() ─────────────→ PostgreSQL:
│                                                      ←─────────┤ SELECT * FROM storage.files 
│    Result: File status = available ✓                        │         WHERE file_id = $1
│                                                             │         │
│  Step 6: Generate short-lived presigned URL (15min)         │         │
│    backend.generate_presigned_url()────────────────────────→ MinIO:
│                                                      ←─────────┤ GET presigned URL (15min)
│    URL expires: 2025-12-15T12:15:00Z                        │         │
│                                                             │         │
│  Step 7: Increment download count (download permission)    │         │
│    repository.increment_share_downloads()──────────────────→ PostgreSQL:
│                                                      ←─────────┤ UPDATE storage.file_shares...
│    download_count = 1                                        │         │
│                                                             │         │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
Return FileInfoResponseContract:
{
  "file_id": "file_abc123",
  "user_id": null,  // Hidden for shared access
  "file_name": "photo.jpg",
  "file_path": "users/user_123/...",
  "file_size": 2097152,
  "content_type": "image/jpeg",
  "status": "available",
  "access_level": "private",  // Original access level
  "download_url": "https://minio.example.com/presigned-url",
  "metadata": {},
  "tags": ["photo", "vacation"],
  "uploaded_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-15T10:00:00Z"
}
    │
    ↓
Recipient downloads file via short-lived URL (direct to MinIO)
```

### 5. File Deletion Flow

```
User deletes file: file_abc123 (soft delete)
    │
    ↓
DELETE /api/v1/storage/files/file_abc123?user_id=user_123&permanent=false
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│           StorageService.delete_file()                     │
│                                                             │
│  Step 1: Get file record with permission check             │
│    repository.get_file_by_id()────────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ SELECT * FROM storage.files 
│    Result: File owned by user_123 ✓                        │         WHERE file_id = $1 AND user_id = $2
│                                                             │         │
│  Step 2: Check for active shares                           │         │
│    repository.count_active_shares()────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ SELECT COUNT(*) FROM storage.file_shares
│    Result: 0 active shares ✓                               │         WHERE file_id = $1 AND is_active = TRUE...
│                                                             │         │
│  Step 3: Perform soft delete                               │         │
│    repository.soft_delete_file()──────────────────────────→ PostgreSQL:
│                                                      ←─────────┤ UPDATE storage.files SET status = 'deleted'...
│    Success                                                  │         │
│                                                             │         │
│  Step 4: Update user quota                                  │         │
│    repository.update_user_quota()──────────────────────────→ PostgreSQL:
│    used_bytes_delta = -2097152 (2MB)                       │         │ UPDATE storage.quotas SET used_bytes = used_bytes - 2097152...
│    file_count_delta = -1                                    │         │
│    Success                                                  │         │
│                                                             │         │
│  Step 5: Publish event                                     │         │
│    publish_file_deleted()──────────────────────────────────→ NATS:
│    permanent = false                                        │         storage.file.deleted
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
Return {"success": true, "message": "File deleted successfully", "permanent": false}
    │
    ↓
                                                               Event Subscribers:
┌─────────────────────────────────────────────────────────────┐
│                  Event Subscribers                         │
│ - Media Service: Clean up related media records           │
│ - Document Service: Remove from RAG index                  │
│ - Album Service: Remove from albums                        │
│ - Audit Service: Log deletion for compliance               │
│ - Analytics Service: Update storage metrics               │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server
- **minio**: MinIO Python client

### Data Storage
- **PostgreSQL 15+**: Primary database for metadata
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `storage`
- **Tables**: `files`, `file_shares`, `quotas`
- **MinIO**: S3-compatible object storage

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `storage.file.*`
- **Publishers**: Storage Service
- **Subscribers**: 5+ services

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration

### Dependency Injection
- **Protocols (typing.Protocol)**: Interface definitions
- **Factory Pattern**: Production vs test instances
- **ConfigManager**: Environment-based configuration

### Observability
- **Structured Logging**: JSON format
- **core.logger**: Service logger
- **Health Endpoints**: `/health`, `/health/detailed`

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **File Type Validation**: Allowed MIME types list
- **File Size Limits**: Maximum 500MB per file
- **SQL Injection**: Parameterized queries via gRPC

### Access Control
- **User Isolation**: All queries filtered by user_id
- **JWT Authentication**: Handled by API Gateway
- **Share Access**: Token/password-based with expiry
- **Permission Model**: Granular share permissions

### Data Privacy
- **Soft Delete**: File metadata preserved for audit
- **Secure URLs**: Presigned URLs with expiry
- **Access Levels**: private, restricted, shared, public
- **Share Limits**: Download limits and expiry

### Storage Security
- **Encryption in Transit**: TLS for all communication
- **MinIO Security**: Access key rotation, bucket policies
- **File Isolation**: User-based object paths
- **URL Expiry**: Automatic URL expiration

---

## Performance Optimization

### Database Optimization
- **Indexes**: Strategic indexes on user_id, status, access_level, created_at
- **Connection Pooling**: gRPC client pools connections
- **Concurrent Queries**: `asyncio.gather` for statistics
- **Pagination**: LIMIT/OFFSET with reasonable limits

### Storage Optimization
- **Presigned URLs**: Direct access to MinIO, bypassing service
- **URL Caching**: Database caching of presigned URLs
- **Batch Operations**: Bulk URL regeneration for file lists
- **Object Path Structure**: Hierarchical paths for MinIO efficiency

### API Optimization
- **Async Operations**: All I/O is async
- **Multipart Upload**: Efficient file upload handling
- **Stream Processing**: Large files streamed to MinIO
- **Response Caching**: File metadata cached in database

### Event Publishing
- **Non-Blocking**: Event failures don't block operations
- **Async Publishing**: Fire-and-forget pattern
- **Error Logging**: Failed publishes logged for retry

---

## Error Handling

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

### Error Response Format
```json
{
  "detail": "Storage quota exceeded: 10GB/10GB"
}
```

### Exception Handling
```python
@app.exception_handler(StorageQuotaExceededError)
async def quota_exceeded_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(FileNotFoundError)
async def not_found_handler(request, exc):
    return HTTPException(status_code=404, detail=str(exc))

@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request, exc):
    return HTTPException(status_code=401, detail=str(exc))

@app.exception_handler(ForbiddenError)
async def forbidden_handler(request, exc):
    return HTTPException(status_code=403, detail=str(exc))
```

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation
- **Logic Contract**: Business rule documentation
- **Component Tests**: Factory, builder, validation tests

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **HTTP + MinIO**: File upload/download flows
- **Event Publishing**: Verify events published correctly
- **Share Flows**: Complete sharing lifecycle

### API Testing
- **Endpoint Contracts**: All 8 endpoints tested
- **File Upload**: Multipart upload handling
- **Error Handling**: Validation, not found, server errors
- **Quota Management**: Quota enforcement and updates

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Connectivity**: Database and MinIO availability

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Storage Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/storage_service.md
- PRD: docs/prd/storage_service.md
- Data Contract: tests/contracts/storage/data_contract.py
- Logic Contract: tests/contracts/storage/logic_contract.md
