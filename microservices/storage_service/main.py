"""
Storage Microservice

MinIO-based file storage service with S3 compatibility
Provides file upload, download, sharing, and quota management

Port: 8209
"""

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from isa_common.consul_client import ConsulRegistry

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import Event, EventType, ServiceSource, get_event_bus

from .intelligence_models import (
    ChunkingStrategy,
    ImageRAGRequest,
    ImageRAGResponse,
    ImageSearchRequest,
    ImageSearchResponse,
    IntelligenceStats,
    RAGQueryRequest,
    RAGQueryResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    StoreImageRequest,
    StoreImageResponse,
)
from .intelligence_service import IntelligenceService
from .models import (
    AddPhotosToAlbumRequest,
    AlbumListResponse,
    AlbumPhotosResponse,
    AlbumResponse,
    AlbumSyncResponse,
    # Album models
    CreateAlbumRequest,
    # Gallery & Slideshow models
    CreatePlaylistRequest,
    CreateRotationScheduleRequest,
    FileInfoResponse,
    FileListRequest,
    FileShareRequest,
    FileShareResponse,
    FileStatus,
    FileUploadRequest,
    FileUploadResponse,
    GetPhotoVersionsRequest,
    PhotoWithVersions,
    PreloadImagesRequest,
    SavePhotoVersionRequest,
    SavePhotoVersionResponse,
    ShareAlbumRequest,
    SmartSelectionCriteria,
    StorageStatsResponse,
    SwitchPhotoVersionRequest,
    UpdateAlbumRequest,
    UpdatePhotoMetadataRequest,
    UpdatePlaylistRequest,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .storage_repository import StorageRepository
from .storage_service import StorageService

# Initialize configuration
config_manager = ConfigManager("storage_service")
service_config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("storage_service")
logger = app_logger  # for backward compatibility

# 全局变量
storage_service = None
intelligence_service = None
event_bus = None
consul_registry = None


# ==================== Event Handlers ====================


async def handle_file_indexing_request(event: Event):
    """
    Event handler for FILE_INDEXING_REQUESTED events

    Processes file indexing asynchronously when a file is uploaded
    """
    try:
        logger.info(f"Received file indexing request: {event.id}")

        # Extract event data
        data = event.data
        file_id = data.get("file_id")
        user_id = data.get("user_id")
        organization_id = data.get("organization_id")
        file_name = data.get("file_name")
        file_type = data.get("file_type")
        file_size = data.get("file_size")
        metadata = data.get("metadata", {})
        tags = data.get("tags", [])
        bucket_name = data.get("bucket_name")
        object_name = data.get("object_name")

        if not all([file_id, user_id, file_name, bucket_name, object_name]):
            logger.error(f"Missing required fields in indexing request: {data}")
            return

        # Prepare file content/URL based on file type
        try:
            # For images and PDFs, pass the presigned URL instead of downloading
            if file_type.startswith("image/") or file_type == "application/pdf":
                # Generate presigned URL for MCP to download
                file_content = storage_service.minio_client.get_presigned_url(
                    bucket_name=bucket_name,
                    object_key=object_name,
                    expiry_seconds=3600,  # 1 hour
                )
                if not file_content:
                    raise Exception("Failed to generate presigned URL")
                logger.info(
                    f"Generated presigned URL for {file_type}: {file_content[:100]}..."
                )
            else:
                # For text files, download and decode content
                file_bytes = storage_service.minio_client.get_object(
                    bucket_name, object_name
                )
                # isa_common MinIOClient returns bytes directly, not a response object
                if file_bytes is None:
                    raise Exception("File not found in MinIO")
                file_content = file_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Failed to download file {file_id} from MinIO: {e}")
            # Publish indexing failed event
            if event_bus:
                failed_event = Event(
                    event_type=EventType.FILE_INDEXING_FAILED,
                    source=ServiceSource.STORAGE_SERVICE,
                    data={
                        "file_id": file_id,
                        "user_id": user_id,
                        "error": f"Failed to download file: {str(e)}",
                    },
                )
                await event_bus.publish_event(failed_event)
            return

        # Index the file via intelligence service
        try:
            logger.info(f"Starting async indexing for file {file_id}")
            await intelligence_service.index_file(
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id,
                file_name=file_name,
                file_content=file_content,
                file_type=file_type,
                file_size=file_size,
                metadata=metadata,
                tags=tags,
            )

            logger.info(f"Successfully indexed file {file_id}")

            # Publish success event
            if event_bus:
                success_event = Event(
                    event_type=EventType.FILE_INDEXED,
                    source=ServiceSource.STORAGE_SERVICE,
                    data={
                        "file_id": file_id,
                        "user_id": user_id,
                        "file_name": file_name,
                        "file_size": file_size,
                        "indexed_at": datetime.utcnow().isoformat(),
                    },
                )
                await event_bus.publish_event(success_event)

        except Exception as e:
            logger.error(f"Failed to index file {file_id}: {e}")
            # Publish indexing failed event
            if event_bus:
                failed_event = Event(
                    event_type=EventType.FILE_INDEXING_FAILED,
                    source=ServiceSource.STORAGE_SERVICE,
                    data={"file_id": file_id, "user_id": user_id, "error": str(e)},
                )
                await event_bus.publish_event(failed_event)

    except Exception as e:
        logger.error(f"Error handling file indexing request: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global storage_service, intelligence_service, event_bus, consul_registry

    logger.info("Starting Storage Service with Intelligence capabilities...")

    # Consul 服务注册
    if service_config.consul_enabled:
        try:
            # 获取路由元数据
            route_meta = get_routes_for_consul()

            # 合并服务元数据
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }

            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=service_config.service_port,
                consul_host=service_config.consul_host,
                consul_port=service_config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="http",
            )
            consul_registry.register()
            logger.info(
                f"Service registered with Consul: {route_meta.get('route_count', 0)} routes"
            )
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            consul_registry = None

    # Initialize event bus
    try:
        event_bus = await get_event_bus("storage_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(
            f"Failed to initialize event bus: {e}. Continuing without event publishing."
        )
        event_bus = None

    # 初始化服务 (使用 ConfigManager 的 service_config)
    storage_service = StorageService(
        service_config, event_bus=event_bus, config_manager=config_manager
    )
    intelligence_service = IntelligenceService(config=config_manager)

    # Subscribe to file indexing events
    if event_bus:
        try:
            await event_bus.subscribe_to_events(
                pattern="storage_service.file.indexing.requested",
                handler=handle_file_indexing_request,
                durable="storage-indexing-consumer",
            )
            logger.info("Subscribed to file indexing events")
        except Exception as e:
            logger.warning(f"Failed to subscribe to indexing events: {e}")

    # 检查数据库连接
    if not await storage_service.repository.check_connection():
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")

    # Register with Consul
    if service_config.consul_enabled:
        # 优先从环境变量读取端口，如果环境变量不存在则使用配置中的端口
        # 这样可以支持通过 uvicorn --port 命令行参数启动的情况
        # 注意：如果通过 uvicorn --port 启动，需要设置环境变量 STORAGE_SERVICE_PORT 或 PORT
        actual_port = int(
            os.getenv(
                "STORAGE_SERVICE_PORT",
                os.getenv("PORT", str(service_config.service_port)),
            )
        )

        # 记录端口信息用于调试
        logger.info(
            f"Service port: config_port={service_config.service_port}, "
            f"env_port={os.getenv('STORAGE_SERVICE_PORT', os.getenv('PORT', 'not set'))}, "
            f"actual_port={actual_port}"
        )

        # Service discovery via Consul agent sidecar
        logger.info("Service discovery via Consul agent sidecar")

    logger.info("Storage Service started successfully on port 8209")

    yield

    # 清理
    logger.info("Shutting down Storage Service...")

    # Consul 注销
    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("Service deregistered from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister from Consul: {e}")

    # Close event bus
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")


# 创建FastAPI应用
app = FastAPI(
    title="Smart Storage Service",
    description="Intelligent file storage with semantic search & RAG (powered by isA_MCP)",
    version="1.0.0",
    lifespan=lifespan,
)


# Add exception handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler to log full stack traces"""
    import traceback

    error_trace = traceback.format_exc()
    logger.error("=" * 80)
    logger.error(f"EXCEPTION CAUGHT: {type(exc).__name__}: {exc}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request method: {request.method}")
    logger.error("Full Traceback:")
    logger.error(error_trace)
    logger.error("=" * 80)

    # Also print to stderr for immediate visibility
    print(
        f"\n\n{'=' * 80}\nEXCEPTION: {exc}\n{error_trace}\n{'=' * 80}\n\n",
        file=sys.stderr,
    )

    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ==================== 健康检查 ====================


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": service_config.service_name,
        "port": service_config.service_port,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/info")
async def service_info():
    """服务信息"""
    return {
        "service": "smart-storage-service",
        "version": "1.0.0",
        "description": "Intelligent file storage with semantic search & RAG (powered by isA_MCP)",
        "capabilities": {
            "upload": True,
            "download": True,
            "share": True,
            "quota_management": True,
            "versioning": True,
            "metadata": True,
            "tagging": True,
            # NEW: Intelligent capabilities
            "semantic_search": True,
            "rag_qa": True,
            "auto_indexing": True,
            "multi_mode_rag": True,
            "citation_support": True,
        },
        "storage_backend": "MinIO",
        "intelligence_backend": "isA_MCP (digital_analytics_tools)",
        "rag_modes": ["simple", "raptor", "self_rag", "crag", "plan_rag", "hm_rag"],
        "endpoints": {
            "upload": "/api/v1/files/upload",
            "download": "/api/v1/files/{file_id}/download",
            "list": "/api/v1/files",
            "share": "/api/v1/files/{file_id}/share",
            "quota": "/api/v1/files/quota",
            "stats": "/api/v1/files/stats",
            # NEW: Intelligent endpoints
            "semantic_search": "/api/v1/files/search",
            "rag_query": "/api/v1/files/ask",
            "intelligence_stats": "/api/v1/storage/intelligence/stats",
        },
    }


# ==================== 文件上传 ====================


@app.post("/api/v1/storage/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    organization_id: Optional[str] = Form(None),
    access_level: str = Form("private"),
    metadata: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    auto_delete_after_days: Optional[int] = Form(None),
    enable_indexing: bool = Form(True),
):
    """
    上传文件

    - **file**: 要上传的文件
    - **user_id**: 用户ID
    - **organization_id**: 组织ID（可选）
    - **access_level**: 访问级别 (public/private/restricted/shared)
    - **metadata**: JSON格式的元数据（可选）
    - **tags**: 逗号分隔的标签（可选）
    - **auto_delete_after_days**: 自动删除天数（可选）
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # 解析元数据和标签
    import json

    parsed_metadata = json.loads(metadata) if metadata else None
    parsed_tags = tags.split(",") if tags else None

    request = FileUploadRequest(
        user_id=user_id,
        organization_id=organization_id,
        access_level=access_level,
        metadata=parsed_metadata,
        tags=parsed_tags,
        auto_delete_after_days=auto_delete_after_days,
        enable_indexing=enable_indexing,
    )

    result = await storage_service.upload_file(file, request)

    # Publish event for async indexing if enabled
    # Async event-driven indexing for ALL file types (images, PDFs, text, etc.)
    # Intelligence service will handle each type appropriately in background
    if event_bus and request.enable_indexing:
        try:
            # Get file record to retrieve MinIO details
            file_record = await storage_service.repository.get_file_by_id(
                result.file_id, user_id
            )
            if file_record:
                # Publish FILE_INDEXING_REQUESTED event for async background processing
                indexing_event = Event(
                    event_type=EventType.FILE_INDEXING_REQUESTED,
                    source=ServiceSource.STORAGE_SERVICE,
                    data={
                        "file_id": result.file_id,
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "file_name": file.filename,
                        "file_type": file.content_type,
                        "file_size": result.file_size,
                        "metadata": parsed_metadata,
                        "tags": parsed_tags,
                        "bucket_name": file_record.bucket_name,
                        "object_name": file_record.object_name,
                    },
                )
                await event_bus.publish_event(indexing_event)
                logger.info(
                    f"📤 Published async indexing request for {file.content_type} file {result.file_id}"
                )
        except Exception as e:
            # Don't fail upload if event publishing fails
            logger.error(
                f"Failed to publish indexing event for file {result.file_id}: {e}"
            )

    return result


# ==================== 文件列表 ====================


@app.get("/api/v1/storage/files", response_model=List[FileInfoResponse])
async def list_files(
    user_id: str,
    organization_id: Optional[str] = None,
    prefix: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    列出用户文件

    - **user_id**: 用户ID
    - **organization_id**: 组织ID（可选）
    - **prefix**: 文件名前缀过滤（可选）
    - **status**: 文件状态过滤（可选）
    - **limit**: 返回数量限制
    - **offset**: 分页偏移
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    request = FileListRequest(
        user_id=user_id,
        organization_id=organization_id,
        prefix=prefix,
        status=FileStatus(status) if status else None,
        limit=limit,
        offset=offset,
    )

    return await storage_service.list_files(request)


# ==================== 存储统计 & 配额 (must be before {file_id}) ====================


@app.get("/api/v1/storage/files/stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    user_id: Optional[str] = None, organization_id: Optional[str] = None
):
    """
    获取存储统计信息

    - **user_id**: 用户ID（可选）
    - **organization_id**: 组织ID（可选）
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if not user_id and not organization_id:
        raise HTTPException(
            status_code=400, detail="Either user_id or organization_id required"
        )

    return await storage_service.get_storage_stats(user_id, organization_id)


@app.get("/api/v1/storage/files/quota")
async def get_storage_quota(
    user_id: Optional[str] = None, organization_id: Optional[str] = None
):
    """
    获取存储配额信息

    - **user_id**: 用户ID（可选）
    - **organization_id**: 组织ID（可选）
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if not user_id and not organization_id:
        raise HTTPException(
            status_code=400, detail="Either user_id or organization_id required"
        )

    # Determine quota type and entity_id based on what was provided
    if user_id:
        quota = await storage_service.repository.get_storage_quota("user", user_id)
    else:
        quota = await storage_service.repository.get_storage_quota(
            "organization", organization_id
        )

    if not quota:
        # 返回默认配额
        return {
            "total_quota_bytes": storage_service.default_quota_bytes,
            "used_bytes": 0,
            "available_bytes": storage_service.default_quota_bytes,
            "file_count": 0,
            "max_file_size": storage_service.max_file_size,
            "is_active": True,
        }

    return {
        "total_quota_bytes": quota.total_quota_bytes,
        "used_bytes": quota.used_bytes,
        "available_bytes": quota.total_quota_bytes - quota.used_bytes,
        "file_count": quota.file_count,
        "max_file_size": quota.max_file_size,
        "max_file_count": quota.max_file_count,
        "allowed_extensions": quota.allowed_extensions,
        "blocked_extensions": quota.blocked_extensions,
        "is_active": quota.is_active,
        "updated_at": quota.updated_at,
    }


# ==================== 文件信息 ====================


@app.get("/api/v1/storage/files/{file_id}", response_model=FileInfoResponse)
async def get_file_info(file_id: str, user_id: str):
    """
    获取文件信息

    - **file_id**: 文件ID
    - **user_id**: 用户ID
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.get_file_info(file_id, user_id)


# ==================== 文件下载 ====================


@app.get("/api/v1/storage/files/{file_id}/download")
async def download_file(
    file_id: str, user_id: str, expires_minutes: int = Query(60, ge=1, le=1440)
):
    """
    获取文件下载URL

    - **file_id**: 文件ID
    - **user_id**: 用户ID
    - **expires_minutes**: URL过期时间（分钟）
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    file_info = await storage_service.get_file_info(file_id, user_id)

    if not file_info.download_url:
        raise HTTPException(status_code=404, detail="Download URL not available")

    return {
        "file_id": file_id,
        "download_url": file_info.download_url,
        "expires_in": expires_minutes * 60,
        "file_name": file_info.file_name,
        "content_type": file_info.content_type,
    }


# ==================== 文件删除 ====================


@app.delete("/api/v1/storage/files/{file_id}")
async def delete_file(file_id: str, user_id: str, permanent: bool = Query(False)):
    """
    删除文件

    - **file_id**: 文件ID
    - **user_id**: 用户ID
    - **permanent**: 是否永久删除
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    success = await storage_service.delete_file(file_id, user_id, permanent)

    if success:
        return {"message": "File deleted successfully", "file_id": file_id}
    else:
        raise HTTPException(status_code=404, detail="File not found or deletion failed")


# ==================== 文件分享 ====================


@app.post("/api/v1/storage/files/{file_id}/share", response_model=FileShareResponse)
async def share_file(
    file_id: str,
    shared_by: str = Form(...),
    shared_with: Optional[str] = Form(None),
    shared_with_email: Optional[str] = Form(None),
    view: bool = Form(True),
    download: bool = Form(False),
    delete: bool = Form(False),
    password: Optional[str] = Form(None),
    expires_hours: int = Form(24),
    max_downloads: Optional[int] = Form(None),
):
    """
    分享文件

    - **file_id**: 文件ID
    - **shared_by**: 分享者用户ID
    - **shared_with**: 被分享者用户ID（可选）
    - **shared_with_email**: 被分享者邮箱（可选）
    - **view/download/delete**: 权限设置
    - **password**: 访问密码（可选）
    - **expires_hours**: 过期时间（小时）
    - **max_downloads**: 最大下载次数（可选）
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    request = FileShareRequest(
        file_id=file_id,
        shared_by=shared_by,
        shared_with=shared_with,
        shared_with_email=shared_with_email,
        permissions={"view": view, "download": download, "delete": delete},
        password=password,
        expires_hours=expires_hours,
        max_downloads=max_downloads,
    )

    return await storage_service.share_file(request)


# ==================== 访问分享 ====================


@app.get("/api/v1/storage/shares/{share_id}", response_model=FileInfoResponse)
async def get_shared_file(
    share_id: str,
    token: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
):
    """
    访问分享的文件

    - **share_id**: 分享ID
    - **token**: 访问令牌（可选）
    - **password**: 访问密码（可选）
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.get_shared_file(share_id, token, password)


# ==================== 测试端点 ====================


@app.post("/api/v1/storage/test/upload")
async def test_upload(user_id: str = "test_user"):
    """测试文件上传（创建测试文件）"""
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # 创建一个测试文件
    from io import BytesIO
    from tempfile import SpooledTemporaryFile

    test_content = b"This is a test file content for storage service."
    file = SpooledTemporaryFile()
    file.write(test_content)
    file.seek(0)

    test_file = UploadFile(
        filename="test_file.txt", file=file, headers={"content-type": "text/plain"}
    )

    request = FileUploadRequest(
        user_id=user_id,
        metadata={"test": True, "created_at": datetime.utcnow().isoformat()},
        tags=["test", "demo"],
    )

    result = await storage_service.upload_file(test_file, request)

    return {"message": "Test file uploaded successfully", "result": result}


@app.get("/api/v1/storage/test/minio-status")
async def check_minio_status():
    """检查MinIO连接状态"""
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # 列出所有buckets
        buckets = storage_service.minio_client.list_buckets()

        return {
            "status": "connected",
            "bucket_name": storage_service.bucket_name,
            "bucket_exists": storage_service.minio_client.bucket_exists(
                storage_service.bucket_name
            ),
            "all_buckets": [b.name for b in buckets],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==================== Photo Version Management ====================


@app.post(
    "/api/v1/storage/photos/versions/save", response_model=SavePhotoVersionResponse
)
async def save_photo_version(request: SavePhotoVersionRequest):
    """
    保存照片的AI处理版本

    - 从AI生成的URL下载图片
    - 上传到云存储
    - 记录版本信息
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.save_photo_version(request)


@app.post(
    "/api/v1/storage/photos/{photo_id}/versions", response_model=PhotoWithVersions
)
async def get_photo_versions(
    photo_id: str, user_id: str = Query(..., description="User ID")
):
    """
    获取照片的所有版本

    - **photo_id**: 照片ID
    - **user_id**: 用户ID
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    request = GetPhotoVersionsRequest(photo_id=photo_id, user_id=user_id)

    return await storage_service.get_photo_versions(request)


@app.put("/api/v1/storage/photos/{photo_id}/versions/{version_id}/switch")
async def switch_photo_version(
    photo_id: str, version_id: str, user_id: str = Query(..., description="User ID")
):
    """
    切换照片的当前显示版本

    - **photo_id**: 照片ID
    - **version_id**: 版本ID
    - **user_id**: 用户ID
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    request = SwitchPhotoVersionRequest(
        photo_id=photo_id, version_id=version_id, user_id=user_id
    )

    return await storage_service.switch_photo_version(request)


@app.delete("/api/v1/storage/photos/versions/{version_id}")
async def delete_photo_version(
    version_id: str, user_id: str = Query(..., description="User ID")
):
    """
    删除照片版本（不能删除原始版本）

    - **version_id**: 版本ID
    - **user_id**: 用户ID
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.delete_photo_version(version_id, user_id)


# ==================== 智能文档分析端点 (Intelligent Features) ====================


@app.post("/api/v1/storage/files/search", response_model=SemanticSearchResponse)
async def semantic_search_files(request: SemanticSearchRequest):
    """
    语义搜索文件 - 使用自然语言查询用户的文件库

    Powered by isA_MCP digital_analytics_tools

    - **user_id**: 用户ID
    - **query**: 自然语言搜索查询
    - **top_k**: 返回结果数量 (default: 5)
    - **enable_rerank**: 启用重排序 (default: false)
    - **min_score**: 最低相关性分数 (default: 0.0)
    - **file_types**: 文件类型过滤 (optional)
    - **tags**: 标签过滤 (optional)
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    if not storage_service:
        raise HTTPException(status_code=503, detail="Storage service not initialized")

    return await intelligence_service.semantic_search(
        request, storage_service.repository
    )


@app.post("/api/v1/storage/files/ask", response_model=RAGQueryResponse)
async def rag_query_files(request: RAGQueryRequest):
    """
    RAG问答 - 基于用户文件回答问题

    Powered by isA_MCP digital_analytics_tools with 6 RAG modes:
    - simple: 标准RAG
    - raptor: 递归摘要RAG
    - self_rag: 自我反思RAG
    - crag: 校正RAG
    - plan_rag: 计划式RAG
    - hm_rag: 混合模式RAG

    - **user_id**: 用户ID
    - **query**: 用户问题
    - **rag_mode**: RAG模式 (default: simple)
    - **session_id**: 会话ID (用于多轮对话, optional)
    - **top_k**: 检索文档数量 (default: 3)
    - **enable_citations**: 启用引用 (default: true)
    - **max_tokens**: 最大生成长度 (default: 500)
    - **temperature**: 生成温度 (default: 0.7)
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    if not storage_service:
        raise HTTPException(status_code=503, detail="Storage service not initialized")

    return await intelligence_service.rag_query(request, storage_service.repository)


@app.get("/api/v1/storage/intelligence/stats", response_model=IntelligenceStats)
async def get_intelligence_stats(user_id: str):
    """
    获取用户的智能服务统计信息

    - **user_id**: 用户ID

    Returns:
    - total_files: 总文件数
    - indexed_files: 已索引文件数
    - total_chunks: 总分块数
    - total_searches: 总搜索次数
    - storage_size_bytes: 存储大小
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    if not storage_service:
        raise HTTPException(status_code=503, detail="Storage service not initialized")

    return await intelligence_service.get_stats(user_id, storage_service.repository)


# ==================== 错误处理 ====================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ==================== 智能索引与搜索 ====================


@app.post("/api/v1/storage/intelligence/search", response_model=SemanticSearchResponse)
async def semantic_search(request: SemanticSearchRequest):
    """
    语义搜索已索引的文档

    通过MCP digital_analytics_tools进行语义搜索
    返回相关文档列表及相关性分数
    """
    if not intelligence_service or not storage_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    try:
        result = await intelligence_service.semantic_search(
            request=request, storage_repository=storage_service.repository
        )
        return result
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/storage/intelligence/rag", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """
    RAG问答查询

    支持7种RAG模式：
    - Simple: 基础RAG
    - RAPTOR: 递归摘要树
    - Self-RAG: 自我反思RAG
    - CRAG: 校正式RAG
    - Plan-RAG: 计划式RAG
    - HM-RAG: 混合记忆RAG
    - Graph: 知识图谱RAG
    """
    if not intelligence_service or not storage_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    try:
        result = await intelligence_service.rag_query(
            request=request, storage_repository=storage_service.repository
        )
        return result
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/v1/storage/intelligence/stats")
async def get_intelligence_stats(user_id: str = Query(..., description="用户ID")):
    """
    获取用户的智能索引统计信息

    包括：
    - 已索引文件数量
    - 文档块总数
    - 搜索次数
    - 平均搜索延迟
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    try:
        stats = await intelligence_service.get_stats(user_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get intelligence stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ==================== 图片智能处理 ====================


@app.post("/api/v1/storage/intelligence/image/store", response_model=StoreImageResponse)
async def store_image(request: StoreImageRequest):
    """
    存储图片并提取智能描述

    通过VLM（gpt-4o-mini）自动提取图片描述
    生成向量索引用于后续语义搜索
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    try:
        start_time = time.time()

        result = await intelligence_service._store_image_via_mcp(
            user_id=request.user_id,
            image_path=request.image_path,
            metadata=request.metadata,
            description_prompt=request.description_prompt,
            model=request.model,
        )

        processing_time = (time.time() - start_time) * 1000

        return StoreImageResponse(
            success=result.get("success", False),
            image_path=result.get("image_path", request.image_path),
            description=result.get("description", ""),
            description_length=result.get("description_length", 0),
            storage_id=result.get("storage_id", ""),
            vlm_model=result.get("vlm_model", request.model),
            processing_time=processing_time / 1000,  # 转换为秒
            metadata=result.get("metadata", {}),
        )
    except Exception as e:
        logger.error(f"Store image failed: {e}")
        raise HTTPException(status_code=500, detail=f"Store image failed: {str(e)}")


@app.post(
    "/api/v1/storage/intelligence/image/search", response_model=ImageSearchResponse
)
async def search_images(request: ImageSearchRequest):
    """
    图片语义搜索

    用自然语言描述搜索图片内容
    返回相关度排序的图片列表
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    try:
        result = await intelligence_service._search_images_via_mcp(
            user_id=request.user_id,
            query=request.query,
            top_k=request.top_k,
            enable_rerank=request.enable_rerank,
            search_mode=request.search_mode,
        )

        # 构建图片搜索结果
        from .intelligence_models import ImageSearchResult

        image_results = []
        for item in result.get("image_results", []):
            image_results.append(
                ImageSearchResult(
                    knowledge_id=item.get("knowledge_id", ""),
                    image_path=item.get("image_path", ""),
                    description=item.get("description", ""),
                    relevance_score=item.get("relevance_score", 0.0),
                    metadata=item.get("metadata", {}),
                    search_method=item.get("search_method", "traditional_isa"),
                )
            )

        return ImageSearchResponse(
            success=result.get("success", False),
            user_id=request.user_id,
            query=request.query,
            image_results=image_results,
            total_images_found=result.get("total_images_found", 0),
            search_method=result.get("search_method", "traditional_isa"),
        )
    except Exception as e:
        logger.error(f"Image search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image search failed: {str(e)}")


@app.post("/api/v1/storage/intelligence/image/rag", response_model=ImageRAGResponse)
async def image_rag_query(request: ImageRAGRequest):
    """
    多模态RAG问答

    结合图片和文本内容生成智能答案
    支持同时检索图片和文档
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=503, detail="Intelligence service not initialized"
        )

    try:
        result = await intelligence_service._generate_image_rag_via_mcp(
            user_id=request.user_id,
            query=request.query,
            context_limit=request.context_limit,
            include_images=request.include_images,
            rag_mode=request.rag_mode,
        )

        # 构建图片来源列表
        from .intelligence_models import ImageSource

        image_sources = []
        for source in result.get("image_sources", []):
            image_sources.append(
                ImageSource(
                    image_path=source.get("image_path", ""),
                    description=source.get("description", ""),
                    relevance=source.get("relevance", 0.0),
                )
            )

        # 文本来源（如果有的话，使用现有的SearchResult模型）
        text_sources = []
        # TODO: 如果需要支持混合搜索，可以在这里添加文本来源

        return ImageRAGResponse(
            success=result.get("success", False),
            response=result.get("response", ""),
            context_items=result.get("context_items", 0),
            image_sources=image_sources,
            text_sources=text_sources,
            metadata=result.get("metadata", {}),
        )
    except Exception as e:
        logger.error(f"Image RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image RAG query failed: {str(e)}")


# ==================== Album Management API ====================


@app.post("/api/v1/storage/albums", response_model=AlbumResponse)
async def create_album(request: CreateAlbumRequest):
    """
    创建相册

    - **name**: 相册名称
    - **description**: 相册描述（可选）
    - **user_id**: 创建者用户ID
    - **cover_photo_id**: 封面照片ID（可选）
    - **auto_sync**: 是否自动同步到相框
    - **is_shared**: 是否为共享相册
    - **tags**: 标签列表
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.create_album(request)


@app.get("/api/v1/storage/albums/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: str, user_id: str = Query(..., description="用户ID")):
    """
    获取相册详情

    - **album_id**: 相册ID
    - **user_id**: 用户ID
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.get_album(album_id, user_id)


@app.get("/api/v1/storage/albums", response_model=AlbumListResponse)
async def list_user_albums(
    user_id: str = Query(..., description="用户ID"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
):
    """
    获取用户相册列表

    - **user_id**: 用户ID
    - **limit**: 返回数量限制
    - **offset**: 分页偏移
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.list_user_albums(user_id, limit, offset)


@app.put("/api/v1/storage/albums/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: str,
    request: UpdateAlbumRequest,
    user_id: str = Query(..., description="用户ID"),
):
    """
    更新相册信息

    - **album_id**: 相册ID
    - **user_id**: 用户ID
    - **request**: 更新内容
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.update_album(album_id, user_id, request)


@app.delete("/api/v1/storage/albums/{album_id}")
async def delete_album(album_id: str, user_id: str = Query(..., description="用户ID")):
    """
    删除相册

    - **album_id**: 相册ID
    - **user_id**: 用户ID
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.delete_album(album_id, user_id)


@app.post("/api/v1/storage/albums/{album_id}/photos")
async def add_photos_to_album(album_id: str, request: AddPhotosToAlbumRequest):
    """
    添加照片到相册

    - **album_id**: 相册ID
    - **photo_ids**: 照片ID列表
    - **added_by**: 添加者用户ID
    - **is_featured**: 是否设为精选
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.add_photos_to_album(album_id, request)


@app.get("/api/v1/storage/albums/{album_id}/photos", response_model=AlbumPhotosResponse)
async def get_album_photos(
    album_id: str,
    user_id: str = Query(..., description="用户ID"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
):
    """
    获取相册照片列表

    - **album_id**: 相册ID
    - **user_id**: 用户ID
    - **limit**: 返回数量限制
    - **offset**: 分页偏移
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.get_album_photos(album_id, user_id, limit, offset)


@app.post("/api/v1/storage/albums/{album_id}/share")
async def share_album_with_family(
    album_id: str,
    request: ShareAlbumRequest,
    user_id: str = Query(..., description="用户ID"),
):
    """
    创建或更新相册的家庭共享

    - **album_id**: 相册ID
    - **shared_with_members**: 共享给特定成员
    - **share_with_all_family**: 是否共享给所有家庭成员
    - **default_permission**: 默认权限级别
    - **custom_permissions**: 自定义权限设置
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.share_album_with_family(album_id, request, user_id)


@app.get(
    "/api/v1/storage/albums/{album_id}/sync-status/{frame_id}",
    response_model=AlbumSyncResponse,
)
async def get_album_sync_status(
    album_id: str, frame_id: str, user_id: str = Query(..., description="用户ID")
):
    """
    获取相册同步状态

    - **album_id**: 相册ID
    - **frame_id**: 相框设备ID
    - **user_id**: 用户ID
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.get_album_sync_status(album_id, frame_id, user_id)


@app.post("/api/v1/storage/albums/{album_id}/sync/{frame_id}")
async def trigger_album_sync(
    album_id: str,
    frame_id: str,
    user_id: str = Query(..., description="用户ID"),
    force: bool = Query(False, description="是否强制全量同步"),
):
    """
    触发相册同步到相框

    - **album_id**: 相册ID
    - **frame_id**: 相框设备ID
    - **user_id**: 用户ID
    - **force**: 是否强制全量同步
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # TODO: 这里应该调用notification_service来触发同步
    # 目前先返回一个简单的响应
    return {
        "success": True,
        "album_id": album_id,
        "frame_id": frame_id,
        "sync_type": "full" if force else "incremental",
        "message": "Sync triggered successfully",
    }


# ==================== Gallery & Slideshow Endpoints ====================


@app.get("/api/v1/storage/gallery/albums")
async def list_gallery_albums(
    user_id: str = Query(..., description="用户ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    获取相册列表（用于相册库）

    返回用户的所有相册
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.list_user_albums(user_id, limit, offset)


@app.get("/api/v1/storage/gallery/playlists")
async def list_playlists(user_id: str = Query(..., description="用户ID")):
    """
    获取幻灯片播放列表

    返回用户创建的所有播放列表
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    playlists = await storage_service.repository.list_user_playlists(user_id)
    return {"playlists": playlists, "total": len(playlists)}


@app.post("/api/v1/storage/gallery/playlists", status_code=201)
async def create_playlist(request: CreatePlaylistRequest):
    """
    创建播放列表

    支持多种类型：
    - manual: 手动选择照片
    - smart: AI智能选择
    - album: 基于相册
    - favorites: 收藏照片
    - recent: 最近上传
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.create_playlist(request)


@app.get("/api/v1/storage/gallery/playlists/{playlist_id}")
async def get_playlist_details(
    playlist_id: str, user_id: str = Query(..., description="用户ID")
):
    """
    获取播放列表详情
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    playlist = await storage_service.repository.get_playlist(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return playlist


@app.get("/api/v1/storage/gallery/playlists/{playlist_id}/photos")
async def get_playlist_photos(
    playlist_id: str, user_id: str = Query(..., description="用户ID")
):
    """
    获取播放列表的照片

    返回带下载URL的照片列表，用于幻灯片播放
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.get_playlist_photos(playlist_id, user_id)


@app.put("/api/v1/storage/gallery/playlists/{playlist_id}")
async def update_playlist(playlist_id: str, request: UpdatePlaylistRequest):
    """
    更新播放列表
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    updates = request.dict(exclude_unset=True)
    result = await storage_service.repository.update_playlist(playlist_id, updates)

    if not result:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return result


@app.delete("/api/v1/storage/gallery/playlists/{playlist_id}", status_code=204)
async def delete_playlist(playlist_id: str):
    """
    删除播放列表
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    success = await storage_service.repository.delete_playlist(playlist_id)
    if not success:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return None


@app.get("/api/v1/storage/gallery/photos/random")
async def get_random_photos(
    user_id: str = Query(..., description="用户ID"),
    count: int = Query(10, ge=1, le=100, description="照片数量"),
    favorites_only: bool = Query(False, description="仅收藏"),
    min_quality: Optional[float] = Query(None, description="最低质量分数"),
):
    """
    获取随机照片用于幻灯片

    支持智能选择条件：
    - favorites_only: 仅返回收藏照片
    - min_quality: 最低质量分数
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    from .models import SmartSelectionCriteria

    criteria = (
        SmartSelectionCriteria(
            favorites_only=favorites_only,
            min_quality_score=min_quality,
            max_photos=count,
        )
        if (favorites_only or min_quality)
        else None
    )

    return await storage_service.get_random_photos(user_id, count, criteria)


@app.post("/api/v1/storage/gallery/photos/metadata")
async def update_photo_metadata(
    request: UpdatePhotoMetadataRequest, user_id: str = Query(..., description="用户ID")
):
    """
    更新照片元数据

    支持更新：
    - is_favorite: 收藏状态
    - rating: 评分 (0-5)
    - tags: 标签
    - location_name: 地点名称
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.update_photo_metadata(request, user_id)


@app.get("/api/v1/storage/gallery/photos/{file_id}/metadata")
async def get_photo_metadata(
    file_id: str, user_id: str = Query(..., description="用户ID")
):
    """
    获取照片元数据
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Verify user owns the photo
    file = await storage_service.repository.get_file_by_id(file_id, user_id)
    if not file:
        raise HTTPException(status_code=404, detail="Photo not found")

    metadata = await storage_service.repository.get_photo_metadata(file_id)
    return (
        metadata if metadata else {"file_id": file_id, "message": "No metadata found"}
    )


# ==================== Photo Cache & Preloading Endpoints ====================


@app.post("/api/v1/storage/gallery/cache/preload")
async def preload_images(request: PreloadImagesRequest):
    """
    预加载图片到设备缓存

    用于在幻灯片播放前预加载照片，实现无缝过渡

    Example:
    ```json
    {
      "frame_id": "frame_123",
      "user_id": "user_456",
      "photo_ids": ["photo1", "photo2", "photo3"],
      "priority": "high"
    }
    ```
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.preload_images(request)


@app.get("/api/v1/storage/gallery/cache/{frame_id}/stats")
async def get_cache_stats(frame_id: str):
    """
    获取设备缓存统计

    返回：
    - total_cached: 已缓存照片数
    - total_size_bytes: 缓存总大小
    - cache_hit_rate: 缓存命中率
    - pending_count: 待缓存数量
    - failed_count: 失败数量
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.get_cache_stats(frame_id)


@app.post("/api/v1/storage/gallery/cache/{frame_id}/clear")
async def clear_cache(
    frame_id: str,
    days_old: int = Query(30, ge=1, le=365, description="清理N天前的缓存"),
):
    """
    清理过期缓存
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    deleted_count = await storage_service.repository.clean_expired_cache(
        frame_id, days_old
    )
    return {
        "frame_id": frame_id,
        "deleted_count": deleted_count,
        "message": f"Cleared {deleted_count} expired cache entries",
    }


# ==================== Photo Rotation Schedule Endpoints ====================


@app.post("/api/v1/storage/gallery/schedules", status_code=201)
async def create_rotation_schedule(request: CreateRotationScheduleRequest):
    """
    创建照片轮播计划

    为指定设备和播放列表创建轮播计划

    Example:
    ```json
    {
      "playlist_id": "playlist_123",
      "frame_id": "frame_456",
      "user_id": "user_789",
      "start_time": "08:00",
      "end_time": "22:00",
      "days_of_week": [0,1,2,3,4,5,6],
      "interval_seconds": 5,
      "shuffle": false
    }
    ```
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await storage_service.create_rotation_schedule(request)


@app.get("/api/v1/storage/gallery/schedules/{frame_id}")
async def get_frame_schedules(frame_id: str):
    """
    获取设备的轮播计划

    返回指定设备的所有活跃轮播计划
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    schedules = await storage_service.repository.get_frame_schedules(frame_id)
    return {"frame_id": frame_id, "schedules": schedules, "total": len(schedules)}


@app.get("/api/v1/storage/gallery/frames/{frame_id}/playlists")
async def get_frame_playlists(frame_id: str):
    """
    获取设备关联的播放列表

    返回设备配置的所有播放列表及其轮播计划
    """
    if not storage_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    playlists = await storage_service.get_frame_playlists(frame_id)
    return {"frame_id": frame_id, "playlists": playlists, "total": len(playlists)}


# ==================== 主入口 ====================

if __name__ == "__main__":
    import uvicorn

    # Print configuration summary for debugging
    config_manager.print_config_summary()

    uvicorn.run(
        "microservices.storage_service.main:app",
        host=service_config.service_host,
        port=service_config.service_port,
        reload=service_config.debug,
        log_level=service_config.log_level.lower(),
    )
