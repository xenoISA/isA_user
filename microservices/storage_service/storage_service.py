"""
Storage Service

业务逻辑层，处理文件存储的核心业务逻辑
职责：文件上传、下载、删除、分享、配额管理
集成MinIO作为S3兼容的对象存储后端

重构说明：
- 移除了照片版本管理（现由 Media Service 负责）
- 移除了相册管理（现由 Album Service 负责）
- 移除了播放列表和轮播计划（现由 Media Service 负责）
- 移除了智能照片选择和缓存（现由 Media Service 负责）
- 移除了AI分析功能（现由 Media Service 负责）
- 专注于核心存储功能：文件CRUD、分享、配额
"""

import hashlib
import logging
import mimetypes
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config_manager import ConfigManager
from core.nats_client import Event
from fastapi import HTTPException, UploadFile

# Use isa-common's AsyncMinIOClient for async gRPC
from isa_common import AsyncMinIOClient

from .clients import StorageOrganizationClient
from .models import (
    FileAccessLevel,
    FileInfoResponse,
    FileListRequest,
    FileShare,
    FileShareRequest,
    FileShareResponse,
    FileStatus,
    FileUploadRequest,
    FileUploadResponse,
    StorageProvider,
    StorageQuota,
    StorageStatsResponse,
    StoredFile,
)
from .storage_repository import StorageRepository

logger = logging.getLogger(__name__)


class StorageService:
    """存储服务业务逻辑层 - 专注于文件存储核心功能"""

    def __init__(
        self,
        config,
        event_bus=None,
        config_manager: Optional[ConfigManager] = None,
        event_publisher=None,
    ):
        """
        初始化存储服务

        Args:
            config: 配置对象
            event_bus: 事件总线（可选，保留向后兼容）
            config_manager: ConfigManager 实例（可选）
            event_publisher: Event publisher from events/ (可选)
        """
        self.repository = StorageRepository(config=config_manager)
        self.config = config
        self.config_manager = config_manager
        self.event_bus = event_bus  # 保留向后兼容
        self.event_publisher = event_publisher  # 使用新的 publisher
        self.org_client = StorageOrganizationClient()  # 初始化 org client

        # Discover MinIO S3 service using config_manager
        # Priority: Environment variables (MINIO_HOST/PORT) → Consul → fallback
        # Note: Now using native S3 protocol via aioboto3 (not gRPC gateway)
        minio_host, minio_port = config_manager.discover_service(
            service_name="minio",
            default_host="minio",
            default_port=9000,  # S3 API port (not gRPC 50051)
            env_host_key="MINIO_HOST",
            env_port_key="MINIO_PORT",
        )

        # Get MinIO credentials from environment
        import os
        minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")

        logger.info(f"Connecting to MinIO S3 API at {minio_host}:{minio_port}")
        # Initialize AsyncMinIOClient with native S3 protocol (aioboto3)
        self.minio_client = AsyncMinIOClient(
            user_id="storage_service",
            host=minio_host,
            port=minio_port,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
        )
        self._bucket_initialized = False  # Lazy init flag

        self.bucket_name = getattr(config, "minio_bucket_name", "isa-storage")

        # 文件配置
        self.allowed_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/svg+xml",
            "application/pdf",
            "text/plain",
            "text/csv",
            "text/html",
            "text/css",
            "text/javascript",
            "application/json",
            "application/xml",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "application/x-rar-compressed",
            "application/x-7z-compressed",
            "video/mp4",
            "video/mpeg",
            "video/quicktime",
            "audio/mpeg",
            "audio/wav",
            "audio/ogg",
        ]

        # 默认配额设置
        self.default_quota_bytes = 10 * 1024 * 1024 * 1024  # 10GB
        self.max_file_size = 500 * 1024 * 1024  # 500MB
        # Note: Bucket init is now lazy - called in async methods

    async def _ensure_bucket_exists(self):
        """确保MinIO bucket存在 - ASYNC version with lazy init"""
        if self._bucket_initialized:
            return

        try:
            async with self.minio_client:
                exists = await self.minio_client.bucket_exists(self.bucket_name)
                if not exists:
                    result = await self.minio_client.create_bucket(self.bucket_name)
                    if result and result.get("success"):
                        logger.info(f"Created MinIO bucket: {self.bucket_name}")
                    else:
                        logger.error(f"Failed to create bucket: {self.bucket_name}")
                        raise Exception(f"Failed to create bucket: {self.bucket_name}")
                else:
                    logger.info(f"MinIO bucket exists: {self.bucket_name}")

            self._bucket_initialized = True

        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise

    def _generate_object_name(self, user_id: str, filename: str) -> str:
        """生成对象存储路径"""
        now = datetime.now(timezone.utc)
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")

        # 清理用户ID中的特殊字符
        safe_user_id = user_id.replace("|", "_").replace("/", "_")

        # 生成唯一文件名
        file_ext = Path(filename).suffix
        unique_filename = (
            f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
        )

        return f"users/{safe_user_id}/{year}/{month}/{day}/{unique_filename}"

    def _calculate_checksum(self, file_content: bytes) -> str:
        """计算文件校验和"""
        return hashlib.sha256(file_content).hexdigest()

    async def _check_quota(self, user_id: str, file_size: int) -> bool:
        """检查用户配额"""
        logger.info(f"_check_quota called: user_id={user_id}, file_size={file_size}")
        quota = await self.repository.get_storage_quota(
            quota_type="user", entity_id=user_id
        )
        logger.info(f"Retrieved quota: {quota}")

        if not quota:
            # 如果没有配额记录，创建默认配额
            logger.debug("No quota found, using defaults")
            quota = StorageQuota(
                user_id=user_id,
                total_quota_bytes=self.default_quota_bytes,
                used_bytes=0,
                file_count=0,
                max_file_size=self.max_file_size,
            )
            # 这里应该创建配额记录，但简化处理
            return True

        # 检查配额（处理 None 值）
        used_bytes = quota.used_bytes if quota.used_bytes is not None else 0
        logger.info(
            f"Quota check: used_bytes={used_bytes}, total_quota={quota.total_quota_bytes}, max_file_size={quota.max_file_size}"
        )

        if used_bytes + file_size > quota.total_quota_bytes:
            logger.debug(
                f"Quota exceeded: {used_bytes + file_size} > {quota.total_quota_bytes}"
            )
            return False

        if quota.max_file_size and file_size > quota.max_file_size:
            logger.debug(f"File too large: {file_size} > {quota.max_file_size}")
            return False

        logger.debug("Quota check passed")
        return True

    # ==================== 核心文件操作 ====================

    async def upload_file(
        self, file: UploadFile, request: FileUploadRequest
    ) -> FileUploadResponse:
        """
        上传文件到MinIO - ASYNC version

        Args:
            file: 上传的文件对象
            request: 上传请求参数

        Returns:
            FileUploadResponse: 上传响应
        """
        try:
            # Ensure bucket exists (lazy init)
            await self._ensure_bucket_exists()

            # 读取文件内容
            file_content = await file.read()
            file_size = len(file_content)

            # 验证文件类型
            content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
            if content_type not in self.allowed_types:
                raise HTTPException(
                    status_code=400, detail=f"File type not allowed: {content_type}"
                )

            # 验证文件大小
            logger.info(f"Checking file size: {file_size} vs max {self.max_file_size}")
            if file_size > self.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size: {self.max_file_size / (1024 * 1024):.1f}MB",
                )

            # 检查配额
            logger.info(
                f"Checking quota for user {request.user_id}, file_size={file_size}"
            )
            try:
                quota_ok = await self._check_quota(request.user_id, file_size)
                logger.debug(f"Quota check result: {quota_ok}")
                if not quota_ok:
                    raise HTTPException(
                        status_code=400, detail="Storage quota exceeded"
                    )
            except Exception as e:
                logger.error(f"Error in quota check: {e}", exc_info=True)
                raise

            # 生成文件信息
            file_id = f"file_{uuid.uuid4().hex}"
            object_name = self._generate_object_name(request.user_id, file.filename)
            checksum = self._calculate_checksum(file_content)

            # 上传到MinIO (使用isa-common AsyncMinIOClient)
            upload_metadata = {
                "file-id": file_id,
                "user-id": request.user_id,
                "original-name": file.filename,
                "checksum": checksum,
            }

            # Add request metadata (convert all values to strings for MinIO)
            if request.metadata:
                for key, value in request.metadata.items():
                    upload_metadata[key] = str(value) if value is not None else ""

            # ASYNC upload to MinIO (positional args: bucket, key, data)
            async with self.minio_client:
                result = await self.minio_client.upload_object(
                    self.bucket_name,
                    object_name,
                    file_content,
                    content_type=content_type,
                    metadata=upload_metadata,
                )

                if not result or not result.get("success"):
                    raise HTTPException(
                        status_code=500, detail="Failed to upload file to storage"
                    )

                # ASYNC generate presigned URL (24小时有效 = 86400秒，用于AI处理和异步事件)
                download_url = await self.minio_client.get_presigned_url(
                    self.bucket_name,
                    object_name,
                    expiry_seconds=86400,  # 24 hours for AI processing
                )

            # 保存文件记录到数据库
            stored_file = StoredFile(
                file_id=file_id,
                user_id=request.user_id,
                organization_id=request.organization_id,
                file_name=file.filename,
                file_path=object_name,
                file_size=file_size,
                content_type=content_type,
                file_extension=Path(file.filename).suffix,
                storage_provider=StorageProvider.MINIO,
                bucket_name=self.bucket_name,
                object_name=object_name,
                status=FileStatus.AVAILABLE,
                access_level=request.access_level,
                checksum=checksum,
                etag=None,  # isa-common MinIOClient handles etag internally
                version_id=None,  # Version ID not needed for basic uploads
                metadata=request.metadata,
                tags=request.tags,
                download_url=download_url,
                download_url_expires_at=datetime.now(timezone.utc)
                + timedelta(hours=24),
                uploaded_at=datetime.now(timezone.utc),
            )

            await self.repository.create_file_record(stored_file)

            # 更新用户配额使用量
            await self.repository.update_storage_usage(
                quota_type="user",
                entity_id=request.user_id,
                bytes_delta=file_size,
                file_count_delta=1,
            )

            # 如果设置了自动删除
            if request.auto_delete_after_days:
                # 这里应该创建一个定时任务来删除文件
                pass

            # 发布文件上传事件
            # Note: AI处理现在由Media Service订阅file.uploaded事件后处理
            if self.event_publisher:
                try:
                    # Construct full MinIO bucket name (with user prefix)
                    # MinIO gRPC client adds prefix: user-{user_id}-{bucket_name}
                    full_bucket_name = f"user-storage_service-{self.bucket_name}"

                    await self.event_publisher.publish_file_uploaded(
                        file_id=file_id,
                        file_name=file.filename,
                        file_size=file_size,
                        content_type=content_type,
                        user_id=request.user_id,
                        organization_id=request.organization_id,
                        access_level=request.access_level,
                        download_url=download_url,
                        bucket_name=full_bucket_name,
                        object_name=object_name,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to publish file upload event: {e}", exc_info=True
                    )

            return FileUploadResponse(
                file_id=file_id,
                file_path=object_name,
                download_url=download_url,
                file_size=file_size,
                content_type=content_type,
                uploaded_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_file_info(self, file_id: str, user_id: str) -> FileInfoResponse:
        """
        获取文件信息

        Args:
            file_id: 文件ID
            user_id: 用户ID

        Returns:
            FileInfoResponse: 文件信息
        """
        file = await self.repository.get_file_by_id(file_id, user_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        # 检查下载URL是否过期，如果过期则重新生成
        if not file.download_url or file.download_url_expires_at < datetime.now(
            timezone.utc
        ):
            try:
                # ASYNC presigned URL generation (positional: bucket, key)
                async with self.minio_client:
                    download_url = await self.minio_client.get_presigned_url(
                        file.bucket_name,
                        file.object_name,
                        expiry_seconds=86400,  # 24 hours
                    )
                file.download_url = download_url
                file.download_url_expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=24
                )
            except Exception:
                file.download_url = None

        return FileInfoResponse(
            file_id=file.file_id,
            file_name=file.file_name,
            file_path=file.file_path,
            file_size=file.file_size,
            content_type=file.content_type,
            status=file.status,
            access_level=file.access_level,
            download_url=file.download_url,
            metadata=file.metadata,
            tags=file.tags,
            uploaded_at=file.uploaded_at,
            updated_at=file.updated_at,
        )

    async def list_files(self, request: FileListRequest) -> List[FileInfoResponse]:
        """
        列出用户文件

        Args:
            request: 列表请求参数

        Returns:
            List[FileInfoResponse]: 文件列表
        """
        files = await self.repository.list_user_files(
            user_id=request.user_id,
            organization_id=request.organization_id,
            status=request.status,
            prefix=request.prefix,
            limit=request.limit,
            offset=request.offset,
        )

        response = []

        # Batch generate presigned URLs for expired ones
        files_needing_urls = [
            f for f in files
            if not f.download_url or f.download_url_expires_at < datetime.now(timezone.utc)
        ]

        if files_needing_urls:
            async with self.minio_client:
                for file in files_needing_urls:
                    try:
                        file.download_url = await self.minio_client.get_presigned_url(
                            file.bucket_name,
                            file.object_name,
                            expiry_seconds=86400,  # 24 hours
                        )
                    except Exception:
                        file.download_url = None

        for file in files:
            response.append(
                FileInfoResponse(
                    file_id=file.file_id,
                    file_name=file.file_name,
                    file_path=file.file_path,
                    file_size=file.file_size,
                    content_type=file.content_type,
                    status=file.status,
                    access_level=file.access_level,
                    download_url=file.download_url,
                    metadata=file.metadata,
                    tags=file.tags,
                    uploaded_at=file.uploaded_at,
                    updated_at=file.updated_at,
                )
            )

        return response

    async def delete_file(
        self, file_id: str, user_id: str, permanent: bool = False
    ) -> bool:
        """
        删除文件

        Args:
            file_id: 文件ID
            user_id: 用户ID
            permanent: 是否永久删除

        Returns:
            bool: 删除成功
        """
        # 获取文件信息
        file = await self.repository.get_file_by_id(file_id, user_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if permanent:
            # ASYNC delete from MinIO (positional: bucket, key)
            try:
                async with self.minio_client:
                    await self.minio_client.delete_object(
                        file.bucket_name,
                        file.object_name
                    )
            except Exception as e:
                logger.error(f"Error deleting file from MinIO: {e}")
                # 继续处理，即使MinIO删除失败

        # 更新数据库状态
        success = await self.repository.delete_file(file_id, user_id)

        if success:
            # 更新配额使用量
            await self.repository.update_storage_usage(
                quota_type="user",
                entity_id=user_id,
                bytes_delta=-file.file_size,
                file_count_delta=-1,
            )

            # 发布文件删除事件
            # Note: Media Service和Album Service会订阅此事件，清理相关数据
            if self.event_publisher:
                try:
                    await self.event_publisher.publish_file_deleted(
                        file_id=file_id,
                        file_name=file.file_name,
                        file_size=file.file_size,
                        user_id=user_id,
                        permanent=permanent,
                    )
                except Exception as e:
                    logger.error(f"Failed to publish file.deleted event: {e}")

        return success

    # ==================== 文件分享功能 ====================

    async def share_file(self, request: FileShareRequest) -> FileShareResponse:
        """
        分享文件

        Args:
            request: 分享请求参数

        Returns:
            FileShareResponse: 分享响应
        """
        # 验证文件存在且属于用户
        file = await self.repository.get_file_by_id(request.file_id, request.shared_by)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        # 生成访问令牌
        access_token = uuid.uuid4().hex

        # 创建分享记录
        share = FileShare(
            share_id=f"share_{uuid.uuid4().hex[:12]}",
            file_id=request.file_id,
            shared_by=request.shared_by,
            shared_with=request.shared_with,
            shared_with_email=request.shared_with_email,
            access_token=access_token,
            password=request.password,
            permissions=request.permissions,
            max_downloads=request.max_downloads,
            download_count=0,
            is_active=True,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=request.expires_hours),
        )

        logger.info(f"About to create file share: {share.share_id}")
        created_share = await self.repository.create_file_share(share)
        logger.info(f"Created share result: {created_share}")

        # 生成分享URL - 使用服务发现获取 storage_service 的地址
        storage_host, storage_port = self.config_manager.discover_service(
            service_name="storage_service",
            default_host="localhost",
            default_port=8209,
            env_host_key="STORAGE_SERVICE_HOST",
            env_port_key="STORAGE_SERVICE_PORT",
        )
        base_url = f"http://{storage_host}:{storage_port}"
        share_url = f"{base_url}/api/v1/storage/shares/{created_share.share_id}?token={access_token}"

        # 发布文件分享事件
        if self.event_publisher:
            try:
                await self.event_publisher.publish_file_shared(
                    share_id=created_share.share_id,
                    file_id=request.file_id,
                    file_name=file.file_name,
                    shared_by=request.shared_by,
                    shared_with=request.shared_with,
                    shared_with_email=request.shared_with_email,
                    expires_at=created_share.expires_at.isoformat(),
                )
            except Exception as e:
                logger.error(f"Failed to publish file.shared event: {e}")

        return FileShareResponse(
            share_id=created_share.share_id,
            share_url=share_url,
            access_token=access_token if not request.password else None,
            expires_at=created_share.expires_at,
            permissions=created_share.permissions,
        )

    async def get_shared_file(
        self,
        share_id: str,
        access_token: Optional[str] = None,
        password: Optional[str] = None,
    ) -> FileInfoResponse:
        """
        获取分享的文件

        Args:
            share_id: 分享ID
            access_token: 访问令牌
            password: 访问密码

        Returns:
            FileInfoResponse: 文件信息
        """
        # 获取分享信息
        share = await self.repository.get_file_share(share_id, access_token)
        if not share:
            raise HTTPException(status_code=404, detail="Share not found or expired")

        # 验证密码
        if share.password and share.password != password:
            raise HTTPException(status_code=401, detail="Invalid password")

        # 检查下载次数限制
        if share.max_downloads and share.download_count >= share.max_downloads:
            raise HTTPException(status_code=403, detail="Download limit exceeded")

        # 获取文件信息
        file = await self.repository.get_file_by_id(share.file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        # 更新访问记录
        if share.permissions.get("download"):
            await self.repository.increment_share_download(share_id)

        # ASYNC generate download URL (positional: bucket, key)
        download_url = None
        if share.permissions.get("view") or share.permissions.get("download"):
            try:
                async with self.minio_client:
                    download_url = await self.minio_client.get_presigned_url(
                        file.bucket_name,
                        file.object_name,
                        expiry_seconds=900,  # 15 minutes
                    )
            except Exception:
                pass

        return FileInfoResponse(
            file_id=file.file_id,
            file_name=file.file_name,
            file_path=file.file_path,
            file_size=file.file_size,
            content_type=file.content_type,
            status=file.status,
            access_level=file.access_level,
            download_url=download_url,
            metadata=file.metadata,
            tags=file.tags,
            uploaded_at=file.uploaded_at,
            updated_at=file.updated_at,
        )

    # ==================== 存储配额与统计 ====================

    async def get_storage_stats(
        self, user_id: Optional[str] = None, organization_id: Optional[str] = None
    ) -> StorageStatsResponse:
        """
        获取存储统计信息

        Args:
            user_id: 用户ID
            organization_id: 组织ID

        Returns:
            StorageStatsResponse: 存储统计
        """
        # 获取配额信息
        if organization_id:
            quota = await self.repository.get_storage_quota(
                quota_type="organization", entity_id=organization_id
            )
        else:
            quota = await self.repository.get_storage_quota(
                quota_type="user", entity_id=user_id
            )

        if not quota:
            # 使用默认配额
            quota = StorageQuota(
                user_id=user_id,
                organization_id=organization_id,
                total_quota_bytes=self.default_quota_bytes,
                used_bytes=0,
                file_count=0,
            )

        # 获取统计信息
        stats = await self.repository.get_storage_stats(user_id, organization_id)

        # 处理 None 值
        used_bytes = quota.used_bytes if quota.used_bytes is not None else 0
        total_quota_bytes = (
            quota.total_quota_bytes
            if quota.total_quota_bytes is not None
            else self.default_quota_bytes
        )

        # 计算使用百分比
        usage_percentage = (
            (used_bytes / total_quota_bytes * 100) if total_quota_bytes > 0 else 0
        )

        return StorageStatsResponse(
            user_id=user_id,
            organization_id=organization_id,
            total_quota_bytes=total_quota_bytes,
            used_bytes=used_bytes,
            available_bytes=total_quota_bytes - used_bytes,
            usage_percentage=usage_percentage,
            file_count=stats.get("file_count", 0),
            by_type=stats.get("by_type", {}),
            by_status=stats.get("by_status", {}),
        )
