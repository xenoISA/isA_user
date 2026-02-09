"""
Storage Microservice

MinIO-based file storage service with S3 compatibility
Provides file upload, download, sharing, and quota management

重构说明：
- 只保留核心存储功能：文件上传、下载、删除、分享、配额
- 移除了照片版本、相册、播放列表等功能（由 Media/Album Service 负责）
- 移除了 AI 智能分析功能（由 Media Service 负责）

Port: 8209
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import Event, get_event_bus

from isa_common.consul_client import ConsulRegistry

from .events import StorageEventPublisher
from .models import (
    FileInfoResponse,
    FileListRequest,
    FileShareRequest,
    FileShareResponse,
    FileStatus,
    FileUploadRequest,
    FileUploadResponse,
    StorageStatsResponse,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .storage_repository import StorageRepository
from .storage_service import StorageService

# Initialize configuration
config_manager = ConfigManager("storage_service")
service_config = config_manager.get_service_config()

# Setup loggers
app_logger = setup_service_logger("storage_service")
logger = app_logger

# 全局变量
storage_service = None
event_bus = None
consul_registry = None
event_publisher = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global storage_service, event_bus, consul_registry, event_publisher

    logger.info("Starting Storage Service...")

    # Initialize event bus
    try:
        event_bus = await get_event_bus("storage_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")
        event_bus = None

    # 初始化 event publisher
    if event_bus:
        event_publisher = StorageEventPublisher(event_bus)
        logger.info("Event publisher initialized")

    # 初始化服务 (need it before subscribing to events)
    storage_service = StorageService(
        service_config,
        event_bus=event_bus,
        config_manager=config_manager,
        event_publisher=event_publisher,
    )

    # 检查数据库连接
    if not await storage_service.repository.check_connection():
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")

    # Subscribe to events
    if event_bus:
        try:
            from .events.handlers import get_event_handlers

            # Get intelligence service if available
            intelligence_service = getattr(storage_service, 'intelligence_service', None)

            handler_map = get_event_handlers(storage_service, intelligence_service, event_bus)

            for pattern, handler_func in handler_map.items():
                await event_bus.subscribe_to_events(
                    pattern=pattern,
                    handler=handler_func,
                    durable=f"storage-{pattern.replace('.', '-')}-consumer"
                )
                logger.info(f"✅ Subscribed to {pattern}")

            logger.info(f"✅ Storage event subscriber started ({len(handler_map)} event patterns)")

        except Exception as e:
            logger.warning(f"⚠️  Failed to set up event subscriptions: {e}")

    # Consul 服务注册
    if service_config.consul_enabled:
        try:
            route_meta = get_routes_for_consul()
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
                health_check_type="ttl"  # Use TTL for reliable health checks,
            )
            consul_registry.register()
            consul_registry.start_maintenance()  # Start TTL heartbeat
            # Start TTL heartbeat - added for consistency with isA_Model
            logger.info(
                f"Service registered with Consul: {route_meta.get('route_count', 0)} routes"
            )
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            consul_registry = None

    logger.info("Storage Service started successfully on port 8209")

    yield

    # 清理
    logger.info("Shutting down Storage Service...")

    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("Service deregistered from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister from Consul: {e}")

    if event_bus:
        await event_bus.close()


# ==================== FastAPI 应用初始化 ====================

app = FastAPI(
    title="Storage Service",
    description="MinIO-based file storage service with S3 compatibility",
    version="1.0.0",
    lifespan=lifespan,
)


# ==================== 异常处理器 ====================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ==================== 健康检查路由 ====================


@app.get("/api/v1/storage/health")
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "storage_service",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/info")
async def service_info():
    """服务信息端点"""
    return {
        "service": "storage_service",
        "version": "1.0.0",
        "description": "File storage service with MinIO backend",
        "capabilities": [
            "file_upload",
            "file_download",
            "file_sharing",
            "quota_management",
        ],
        "port": service_config.service_port,
    }


# ==================== 核心文件操作路由 ====================


@app.post("/api/v1/storage/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    organization_id: Optional[str] = Form(None),
    access_level: str = Form("private"),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    enable_indexing: bool = Form(True),
):
    """
    上传文件到存储服务

    - **file**: 要上传的文件
    - **user_id**: 用户ID
    - **organization_id**: 组织ID（可选）
    - **access_level**: 访问级别 (public/private/restricted/shared)
    - **tags**: 标签列表（JSON字符串）
    - **metadata**: 元数据（JSON字符串）
    - **enable_indexing**: 是否启用索引（触发 AI 处理事件）
    """
    import json

    # 解析标签 - 支持 JSON 数组或逗号分隔字符串
    tags_list = []
    if tags:
        try:
            # 尝试作为 JSON 解析
            tags_list = json.loads(tags)
        except json.JSONDecodeError:
            # 如果不是 JSON，按逗号分割
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    # 解析元数据
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            logger.warning(f"Invalid metadata JSON: {metadata}")
            metadata_dict = {}

    request = FileUploadRequest(
        user_id=user_id,
        organization_id=organization_id,
        access_level=access_level,
        tags=tags_list,
        metadata=metadata_dict,
        enable_indexing=enable_indexing,
    )

    return await storage_service.upload_file(file, request)


@app.get("/api/v1/storage/files", response_model=List[FileInfoResponse])
async def list_files(
    user_id: str = Query(..., description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID"),
    prefix: Optional[str] = Query(None, description="路径前缀"),
    status: Optional[FileStatus] = Query(None, description="文件状态"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    列出用户文件

    - **user_id**: 用户ID
    - **organization_id**: 组织ID（可选）
    - **prefix**: 路径前缀过滤
    - **status**: 文件状态过滤
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    request = FileListRequest(
        user_id=user_id,
        organization_id=organization_id,
        prefix=prefix,
        status=status,
        limit=limit,
        offset=offset,
    )

    return await storage_service.list_files(request)


@app.get("/api/v1/storage/files/stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    user_id: Optional[str] = Query(None, description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID"),
):
    """
    获取存储统计信息

    - **user_id**: 用户ID
    - **organization_id**: 组织ID
    """
    return await storage_service.get_storage_stats(user_id, organization_id)


@app.get("/api/v1/storage/files/quota")
async def get_storage_quota(
    user_id: Optional[str] = Query(None, description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID"),
):
    """
    获取存储配额信息

    - **user_id**: 用户ID
    - **organization_id**: 组织ID
    """
    stats = await storage_service.get_storage_stats(user_id, organization_id)
    return {
        "user_id": user_id,
        "organization_id": organization_id,
        "total_quota_bytes": stats.total_quota_bytes,
        "used_bytes": stats.used_bytes,
        "available_bytes": stats.available_bytes,
        "usage_percentage": stats.usage_percentage,
        "file_count": stats.file_count,
    }


@app.get("/api/v1/storage/files/{file_id}", response_model=FileInfoResponse)
async def get_file_info(file_id: str, user_id: str = Query(..., description="用户ID")):
    """
    获取文件信息

    - **file_id**: 文件ID
    - **user_id**: 用户ID
    """
    return await storage_service.get_file_info(file_id, user_id)


@app.get("/api/v1/storage/files/{file_id}/download")
async def download_file(file_id: str, user_id: str = Query(..., description="用户ID")):
    """
    获取文件下载URL

    - **file_id**: 文件ID
    - **user_id**: 用户ID
    """
    file_info = await storage_service.get_file_info(file_id, user_id)
    return {
        "file_id": file_id,
        "file_name": file_info.file_name,
        "download_url": file_info.download_url,
        "content_type": file_info.content_type,
        "file_size": file_info.file_size,
    }


@app.delete("/api/v1/storage/files/{file_id}")
async def delete_file(
    file_id: str,
    user_id: str = Query(..., description="用户ID"),
    permanent: bool = Query(False, description="是否永久删除"),
):
    """
    删除文件

    - **file_id**: 文件ID
    - **user_id**: 用户ID
    - **permanent**: 是否永久删除（默认软删除）
    """
    success = await storage_service.delete_file(file_id, user_id, permanent)
    if success:
        return {
            "success": True,
            "file_id": file_id,
            "message": "File deleted successfully",
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to delete file")


# ==================== 文件分享路由 ====================


@app.post("/api/v1/storage/files/{file_id}/share", response_model=FileShareResponse)
async def share_file(
    file_id: str,
    shared_by: str = Form(...),
    shared_with: Optional[str] = Form(None),
    shared_with_email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    expires_hours: int = Form(24),
    max_downloads: Optional[int] = Form(None),
    view: bool = Form(True),
    download: bool = Form(False),
    delete: bool = Form(False),
):
    """
    创建文件分享链接

    - **file_id**: 文件ID
    - **shared_by**: 分享者用户ID
    - **shared_with**: 被分享者用户ID（可选）
    - **shared_with_email**: 被分享者邮箱（可选）
    - **password**: 访问密码（可选）
    - **expires_hours**: 过期时间（小时）
    - **max_downloads**: 最大下载次数（可选）
    - **view**: 允许查看
    - **download**: 允许下载
    - **delete**: 允许删除
    """
    permissions = {"view": view, "download": download, "delete": delete}

    request = FileShareRequest(
        file_id=file_id,
        shared_by=shared_by,
        shared_with=shared_with,
        shared_with_email=shared_with_email,
        password=password,
        expires_hours=expires_hours,
        max_downloads=max_downloads,
        permissions=permissions,
    )

    return await storage_service.share_file(request)


@app.get("/api/v1/storage/shares/{share_id}", response_model=FileInfoResponse)
async def get_shared_file(
    share_id: str,
    token: Optional[str] = Query(None, description="访问令牌"),
    password: Optional[str] = Query(None, description="访问密码"),
):
    """
    访问分享的文件

    - **share_id**: 分享ID
    - **token**: 访问令牌（可选）
    - **password**: 访问密码（可选）
    """
    return await storage_service.get_shared_file(share_id, token, password)


# ==================== 测试端点 ====================


@app.post("/api/v1/storage/test/upload")
async def test_upload(user_id: str = "test_user"):
    """测试文件上传（用于开发调试）"""
    from io import BytesIO

    # 创建测试文件
    test_content = b"This is a test file for storage service"
    test_file = UploadFile(filename="test.txt", file=BytesIO(test_content))

    request = FileUploadRequest(
        user_id=user_id, access_level="private", enable_indexing=False
    )

    return await storage_service.upload_file(test_file, request)


@app.get("/api/v1/storage/test/minio-status")
async def check_minio_status():
    """检查 MinIO 连接状态"""
    try:
        bucket_exists = storage_service.minio_client.bucket_exists(
            storage_service.bucket_name
        )
        return {
            "status": "connected",
            "bucket": storage_service.bucket_name,
            "bucket_exists": bucket_exists,
        }
    except Exception as e:
        logger.error(f"MinIO connection error: {e}")
        return {"status": "error", "error": str(e)}


# ==================== 运行服务 ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host="0.0.0.0", port=service_config.service_port, reload=True
    )
