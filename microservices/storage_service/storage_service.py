"""
Storage Service

业务逻辑层，处理文件存储的核心业务逻辑
集成MinIO作为S3兼容的对象存储后端
"""

import os
import uuid
import mimetypes
import hashlib
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO, Any
from datetime import datetime, timedelta, timezone
from io import BytesIO

from fastapi import UploadFile, HTTPException

# Use isa-common's MinIOClient for gRPC service discovery
from isa_common.minio_client import MinIOClient
from isa_common.consul_client import ConsulRegistry as IsaCommonConsulRegistry

from .storage_repository import StorageRepository
# Import organization client from organization_service (provider pattern)
from microservices.organization_service.client import OrganizationServiceClient
from core.nats_client import Event, EventType, ServiceSource
from .models import (
    StoredFile, FileShare, StorageQuota,
    FileStatus, StorageProvider, FileAccessLevel,
    FileUploadRequest, FileUploadResponse,
    FileListRequest, FileInfoResponse,
    FileShareRequest, FileShareResponse,
    StorageStatsResponse,
    PhotoVersionType, PhotoVersion, PhotoWithVersions,
    SavePhotoVersionRequest, SavePhotoVersionResponse,
    SwitchPhotoVersionRequest, GetPhotoVersionsRequest,
    # Album models
    CreateAlbumRequest, UpdateAlbumRequest, AddPhotosToAlbumRequest, ShareAlbumRequest,
    AlbumResponse, AlbumListResponse, AlbumPhotosResponse, AlbumSyncResponse
)
from core.consul_registry import ConsulRegistry

logger = logging.getLogger(__name__)


class StorageService:
    """存储服务业务逻辑层"""

    def __init__(self, config, event_bus=None):
        """
        初始化存储服务

        Args:
            config: 配置对象
            event_bus: 事件总线（可选）
        """
        self.repository = StorageRepository()
        self.config = config
        self.event_bus = event_bus

        # Initialize Consul registry for MinIO service discovery
        consul_host = getattr(config, 'consul_host', 'localhost')
        consul_port = getattr(config, 'consul_port', 8500)

        self.consul_registry = IsaCommonConsulRegistry(
            consul_host=consul_host,
            consul_port=consul_port
        )

        # Initialize MinIO client with Consul service discovery
        # This will automatically find the minio-grpc-service endpoint
        self.minio_client = MinIOClient(
            user_id='storage_service',
            consul_registry=self.consul_registry,
            service_name_override='minio-grpc-service'
        )

        self.bucket_name = getattr(config, 'minio_bucket_name', 'isa-storage')
        
        # 文件配置
        self.allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
            'application/pdf',
            'text/plain', 'text/csv', 'text/html', 'text/css', 'text/javascript',
            'application/json', 'application/xml',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
            'video/mp4', 'video/mpeg', 'video/quicktime',
            'audio/mpeg', 'audio/wav', 'audio/ogg'
        ]
        
        # 默认配额设置
        self.default_quota_bytes = 10 * 1024 * 1024 * 1024  # 10GB
        self.max_file_size = 500 * 1024 * 1024  # 500MB

        # 确保bucket存在
        self._ensure_bucket_exists()

    def _get_service_url(self, service_name: str, fallback_port: int) -> str:
        """Get service URL via Consul discovery with fallback"""
        fallback_url = f"http://localhost:{fallback_port}"
        try:
            # Use isa-common Consul registry to get service URL
            url = self.consul_registry.get_service_url(service_name)
            if url:
                return url
        except Exception as e:
            logger.warning(f"Consul lookup failed for {service_name}: {e}")
        return fallback_url
    
    def _ensure_bucket_exists(self):
        """确保MinIO bucket存在"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                result = self.minio_client.create_bucket(
                    self.bucket_name,
                    organization_id='isa-storage-org'
                )
                if result and result.get('success'):
                    logger.info(f"Created MinIO bucket: {self.bucket_name}")
                else:
                    logger.error(f"Failed to create bucket: {self.bucket_name}")
                    raise Exception(f"Failed to create bucket: {self.bucket_name}")
            else:
                logger.info(f"MinIO bucket exists: {self.bucket_name}")
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
        unique_filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
        
        return f"users/{safe_user_id}/{year}/{month}/{day}/{unique_filename}"
    
    def _calculate_checksum(self, file_content: bytes) -> str:
        """计算文件校验和"""
        return hashlib.sha256(file_content).hexdigest()
    
    async def _check_quota(self, user_id: str, file_size: int) -> bool:
        """检查用户配额"""
        quota = await self.repository.get_storage_quota(quota_type="user", entity_id=user_id)
        
        if not quota:
            # 如果没有配额记录，创建默认配额
            quota = StorageQuota(
                user_id=user_id,
                total_quota_bytes=self.default_quota_bytes,
                used_bytes=0,
                file_count=0,
                max_file_size=self.max_file_size
            )
            # 这里应该创建配额记录，但简化处理
            return True
        
        # 检查配额
        if quota.used_bytes + file_size > quota.total_quota_bytes:
            return False
        
        if quota.max_file_size and file_size > quota.max_file_size:
            return False
        
        return True
    
    async def upload_file(
        self,
        file: UploadFile,
        request: FileUploadRequest
    ) -> FileUploadResponse:
        """
        上传文件到MinIO
        
        Args:
            file: 上传的文件对象
            request: 上传请求参数
            
        Returns:
            FileUploadResponse: 上传响应
        """
        try:
            # 读取文件内容
            file_content = await file.read()
            file_size = len(file_content)
            
            # 验证文件类型
            content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
            if content_type not in self.allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type not allowed: {content_type}"
                )
            
            # 验证文件大小
            if file_size > self.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB"
                )
            
            # 检查配额
            if not await self._check_quota(request.user_id, file_size):
                raise HTTPException(
                    status_code=400,
                    detail="Storage quota exceeded"
                )
            
            # 生成文件信息
            file_id = f"file_{uuid.uuid4().hex}"
            object_name = self._generate_object_name(request.user_id, file.filename)
            checksum = self._calculate_checksum(file_content)
            
            # 上传到MinIO (使用isa-common MinIOClient)
            file_stream = BytesIO(file_content)
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

            success = self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_key=object_name,
                data=file_stream,
                size=file_size,
                metadata=upload_metadata
            )

            if not success:
                raise HTTPException(status_code=500, detail="Failed to upload file to storage")

            # 生成预签名下载URL（1小时有效 = 3600秒）
            download_url = self.minio_client.get_presigned_url(
                bucket_name=self.bucket_name,
                object_key=object_name,
                expiry_seconds=3600
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
                download_url_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                uploaded_at=datetime.now(timezone.utc)
            )
            
            await self.repository.create_file_record(stored_file)
            
            # 更新用户配额使用量
            await self.repository.update_storage_usage(
                quota_type="user",
                entity_id=request.user_id,
                bytes_delta=file_size,
                file_count_delta=1
            )
            
            # 如果设置了自动删除
            if request.auto_delete_after_days:
                # 这里应该创建一个定时任务来删除文件
                pass

            # Publish file.uploaded event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.FILE_UPLOADED,
                        source=ServiceSource.STORAGE_SERVICE,
                        data={
                            "file_id": file_id,
                            "file_name": file.filename,
                            "file_size": file_size,
                            "content_type": content_type,
                            "user_id": request.user_id,
                            "organization_id": request.organization_id,
                            "access_level": request.access_level,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published file.uploaded event for file {file_id}")
                except Exception as e:
                    logger.error(f"Failed to publish file.uploaded event: {e}")

            return FileUploadResponse(
                file_id=file_id,
                file_path=object_name,
                download_url=download_url,
                file_size=file_size,
                content_type=content_type,
                uploaded_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_file_info(
        self,
        file_id: str,
        user_id: str
    ) -> FileInfoResponse:
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
        if not file.download_url or file.download_url_expires_at < datetime.now(timezone.utc):
            try:
                download_url = self.minio_client.get_presigned_url(
                    bucket_name=file.bucket_name,
                    object_key=file.object_name,
                    expiry_seconds=3600
                )
                file.download_url = download_url
                file.download_url_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
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
            updated_at=file.updated_at
        )
    
    async def list_files(
        self,
        request: FileListRequest
    ) -> List[FileInfoResponse]:
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
            offset=request.offset
        )
        
        response = []
        for file in files:
            # 检查并更新下载URL
            if not file.download_url or file.download_url_expires_at < datetime.now(timezone.utc):
                try:
                    download_url = self.minio_client.get_presigned_url(
                        bucket_name=file.bucket_name,
                        object_key=file.object_name,
                        expiry_seconds=3600
                    )
                    file.download_url = download_url
                except Exception:
                    file.download_url = None
            
            response.append(FileInfoResponse(
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
                updated_at=file.updated_at
            ))
        
        return response
    
    async def delete_file(
        self,
        file_id: str,
        user_id: str,
        permanent: bool = False
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
            # 从MinIO删除
            try:
                self.minio_client.delete_object(
                    bucket_name=file.bucket_name,
                    object_key=file.object_name
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
                file_count_delta=-1
            )

            # Publish file.deleted event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.FILE_DELETED,
                        source=ServiceSource.STORAGE_SERVICE,
                        data={
                            "file_id": file_id,
                            "file_name": file.file_name,
                            "file_size": file.file_size,
                            "user_id": user_id,
                            "permanent": permanent,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published file.deleted event for file {file_id}")
                except Exception as e:
                    logger.error(f"Failed to publish file.deleted event: {e}")

        return success
    
    async def share_file(
        self,
        request: FileShareRequest
    ) -> FileShareResponse:
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
            expires_at=datetime.now(timezone.utc) + timedelta(hours=request.expires_hours)
        )

        logger.info(f"About to create file share: {share.share_id}")
        created_share = await self.repository.create_file_share(share)
        logger.info(f"Created share result: {created_share}")
        
        # 生成分享URL
        base_url = self._get_service_url('wallet_service', 8209) if hasattr(self, '_get_service_url') else 'http://localhost:8209'
        share_url = f"{base_url}/api/shares/{created_share.share_id}?token={access_token}"

        # Publish file.shared event
        if self.event_bus:
            try:
                event = Event(
                    event_type=EventType.FILE_SHARED,
                    source=ServiceSource.STORAGE_SERVICE,
                    data={
                        "share_id": created_share.share_id,
                        "file_id": request.file_id,
                        "file_name": file.file_name,
                        "shared_by": request.shared_by,
                        "shared_with": request.shared_with,
                        "shared_with_email": request.shared_with_email,
                        "expires_at": created_share.expires_at.isoformat(),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                await self.event_bus.publish_event(event)
                logger.info(f"Published file.shared event for file {request.file_id}")
            except Exception as e:
                logger.error(f"Failed to publish file.shared event: {e}")

        return FileShareResponse(
            share_id=created_share.share_id,
            share_url=share_url,
            access_token=access_token if not request.password else None,
            expires_at=created_share.expires_at,
            permissions=created_share.permissions
        )
    
    async def get_shared_file(
        self,
        share_id: str,
        access_token: Optional[str] = None,
        password: Optional[str] = None
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
        
        # 生成下载URL
        download_url = None
        if share.permissions.get("view") or share.permissions.get("download"):
            try:
                download_url = self.minio_client.get_presigned_url(
                    bucket_name=file.bucket_name,
                    object_key=file.object_name,
                    expiry_seconds=900  # 15 minutes
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
            updated_at=file.updated_at
        )
    
    async def get_storage_stats(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
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
            quota = await self.repository.get_storage_quota(quota_type="organization", entity_id=organization_id)
        else:
            quota = await self.repository.get_storage_quota(quota_type="user", entity_id=user_id)

        if not quota:
            # 使用默认配额
            quota = StorageQuota(
                user_id=user_id,
                organization_id=organization_id,
                total_quota_bytes=self.default_quota_bytes,
                used_bytes=0,
                file_count=0
            )
        
        # 获取统计信息
        stats = await self.repository.get_storage_stats(user_id, organization_id)
        
        # 计算使用百分比
        usage_percentage = (quota.used_bytes / quota.total_quota_bytes * 100) if quota.total_quota_bytes > 0 else 0
        
        return StorageStatsResponse(
            user_id=user_id,
            organization_id=organization_id,
            total_quota_bytes=quota.total_quota_bytes,
            used_bytes=quota.used_bytes,
            available_bytes=quota.total_quota_bytes - quota.used_bytes,
            usage_percentage=usage_percentage,
            file_count=stats.get("file_count", 0),
            by_type=stats.get("by_type", {}),
            by_status=stats.get("by_status", {})
        )
    
    # ==================== Photo Version Management Methods ====================
    
    async def save_photo_version(
        self,
        request: SavePhotoVersionRequest
    ) -> SavePhotoVersionResponse:
        """
        保存照片的AI处理版本
        1. 从AI生成的URL下载图片
        2. 上传到云存储
        3. 如果是相框端，保存到本地
        4. 记录版本信息
        """
        import uuid
        from io import BytesIO
        import os
        
        version_id = f"ver_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc)
        
        try:
            # 1. 下载AI生成的图片 (使用requests库，同步方式)
            import requests
            
            response = requests.get(request.source_url, timeout=30)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to download image from source: {response.status_code}"
                )
            
            image_data = response.content
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            
            # 2. 准备文件名和路径
            file_extension = '.jpg' if 'jpeg' in content_type else '.png'
            file_name = f"{request.photo_id}_{version_id}{file_extension}"
            object_name = f"photo_versions/{request.user_id}/{request.photo_id}/{file_name}"
            
            # 3. 上传到MinIO云存储
            bucket_name = "emoframe-photos"

            # 确保bucket存在
            if not self.minio_client.bucket_exists(bucket_name):
                result = self.minio_client.create_bucket(bucket_name, organization_id='emoframe-org')
                if not result or not result.get('success'):
                    raise HTTPException(status_code=500, detail=f"Failed to create bucket: {bucket_name}")

            # 上传文件 (all metadata values must be strings for MinIO)
            upload_metadata = {
                'photo_id': str(request.photo_id),
                'version_id': str(version_id),
                'version_type': str(request.version_type.value),
                'processing_mode': str(request.processing_mode or ''),
                'created_at': timestamp.isoformat()
            }

            success = self.minio_client.put_object(
                bucket_name=bucket_name,
                object_key=object_name,
                data=BytesIO(image_data),
                size=len(image_data),
                metadata=upload_metadata
            )

            if not success:
                raise HTTPException(status_code=500, detail="Failed to upload photo version to storage")

            # 生成云端访问URL (7天有效期 = 604800秒)
            cloud_url = self.minio_client.get_presigned_url(
                bucket_name=bucket_name,
                object_key=object_name,
                expiry_seconds=604800  # 7 days
            )
            
            # 4. 如果需要保存到本地（相框端）
            local_path = None
            if request.save_local:
                # 创建本地目录
                local_dir = f"/data/emoframe/photos/{request.user_id}/{request.photo_id}"
                os.makedirs(local_dir, exist_ok=True)
                
                # 保存到本地
                local_path = f"{local_dir}/{file_name}"
                with open(local_path, 'wb') as f:
                    f.write(image_data)
            
            # 5. 创建版本记录
            photo_version = PhotoVersion(
                version_id=version_id,
                photo_id=request.photo_id,
                user_id=request.user_id,
                version_name=request.version_name,
                version_type=request.version_type,
                processing_mode=request.processing_mode,
                file_id=f"file_{version_id}",
                cloud_url=cloud_url,
                local_path=local_path,
                file_size=len(image_data),
                processing_params=request.processing_params,
                metadata=request.metadata or {},
                is_current=request.set_as_current,
                created_at=timestamp,
                updated_at=timestamp
            )
            
            # 6. 保存到数据库（这里简化处理，实际需要持久化）
            await self.repository.save_photo_version(photo_version)
            
            # 7. 如果设为当前版本，更新照片的当前版本
            if request.set_as_current:
                await self.repository.update_photo_current_version(
                    photo_id=request.photo_id,
                    version_id=version_id
                )
            
            return SavePhotoVersionResponse(
                version_id=version_id,
                photo_id=request.photo_id,
                cloud_url=cloud_url,
                local_path=local_path,
                version_name=request.version_name,
                created_at=timestamp,
                message="Photo version saved successfully"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save photo version: {str(e)}"
            )
    
    async def get_photo_versions(
        self,
        request: GetPhotoVersionsRequest
    ) -> PhotoWithVersions:
        """获取照片的所有版本"""
        
        # 从数据库获取版本列表
        versions = await self.repository.get_photo_versions(
            photo_id=request.photo_id,
            user_id=request.user_id
        )
        
        # 获取照片基本信息
        photo_info = await self.repository.get_photo_info(request.photo_id)
        
        return PhotoWithVersions(
            photo_id=request.photo_id,
            title=photo_info.get("title", "Untitled"),
            original_file_id=photo_info.get("original_file_id"),
            current_version_id=photo_info.get("current_version_id"),
            versions=versions,
            version_count=len(versions),
            created_at=photo_info.get("created_at"),
            updated_at=photo_info.get("updated_at")
        )
    
    async def switch_photo_version(
        self,
        request: SwitchPhotoVersionRequest
    ) -> Dict[str, Any]:
        """切换照片的当前显示版本"""
        
        # 验证版本存在
        version = await self.repository.get_photo_version(
            version_id=request.version_id,
            user_id=request.user_id
        )
        
        if not version or version.photo_id != request.photo_id:
            raise HTTPException(
                status_code=404,
                detail="Photo version not found"
            )
        
        # 更新当前版本
        await self.repository.update_photo_current_version(
            photo_id=request.photo_id,
            version_id=request.version_id
        )
        
        # 更新所有版本的is_current标志
        await self.repository.update_version_current_flags(
            photo_id=request.photo_id,
            current_version_id=request.version_id
        )
        
        return {
            "success": True,
            "photo_id": request.photo_id,
            "current_version_id": request.version_id,
            "message": "Photo version switched successfully"
        }
    
    async def delete_photo_version(
        self,
        version_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """删除照片版本（不能删除原始版本）"""
        
        # 获取版本信息
        version = await self.repository.get_photo_version(version_id, user_id)
        
        if not version:
            raise HTTPException(
                status_code=404,
                detail="Photo version not found"
            )
        
        if version.version_type == PhotoVersionType.ORIGINAL:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete original version"
            )
        
        # 如果是当前版本，切换回原始版本
        if version.is_current:
            original_version = await self.repository.get_original_version(version.photo_id)
            if original_version:
                await self.repository.update_photo_current_version(
                    photo_id=version.photo_id,
                    version_id=original_version.version_id
                )
        
        # 删除云存储中的文件
        try:
            bucket_name = "emoframe-photos"
            object_name = version.cloud_url.split(bucket_name + "/")[-1].split("?")[0]
            self.minio_client.delete_object(bucket_name, object_name)
        except Exception as e:
            logger.warning(f"Failed to delete cloud file: {e}")
        
        # 删除本地文件（如果存在）
        if version.local_path and os.path.exists(version.local_path):
            try:
                os.remove(version.local_path)
            except Exception as e:
                logger.warning(f"Failed to delete local file: {e}")
        
        # 从数据库删除版本记录
        await self.repository.delete_photo_version(version_id)
        
        return {
            "success": True,
            "version_id": version_id,
            "message": "Photo version deleted successfully"
        }

    # ==================== Album Management Methods ====================

    async def create_album(self, request: 'CreateAlbumRequest') -> 'AlbumResponse':
        """创建相册 - 支持家庭共享集成"""
        import uuid
        from datetime import datetime
        
        album_id = f"album_{uuid.uuid4().hex[:12]}"
        current_time = datetime.now(timezone.utc)
        sharing_resource_id = None
        
        album_data = {
            "album_id": album_id,
            "name": request.name,
            "description": request.description,
            "user_id": request.user_id,
            "organization_id": request.organization_id,
            "cover_photo_id": request.cover_photo_id,
            "photo_count": 0,
            "auto_sync": request.auto_sync,
            "is_family_shared": request.enable_family_sharing,
            "sharing_resource_id": None,
            "sync_frames": [],
            "tags": request.tags,
            "metadata": {},
            "ai_metadata": {},
            "created_at": current_time.isoformat(),
            "updated_at": current_time.isoformat(),
            "last_synced_at": None
        }
        
        try:
            # 1. 创建相册
            created_album = await self.repository.create_album(album_data)
            
            # 2. 如果启用家庭共享，创建共享资源
            if request.enable_family_sharing and request.organization_id:
                async with OrganizationServiceClient() as org_client:
                    sharing_result = await org_client.create_sharing(
                        organization_id=request.organization_id,
                        user_id=request.user_id,
                        resource_type="album",
                        resource_id=album_id,
                        resource_name=request.name,
                        share_with_all_members=True,
                        default_permission="read_write"
                    )
                
                if sharing_result:
                    sharing_resource_id = sharing_result.get("sharing_id")
                    # 更新相册的sharing_resource_id
                    await self.repository.update_album(album_id, request.user_id, {
                        "sharing_resource_id": sharing_resource_id
                    })
                    logger.info(f"Created family sharing for album {album_id}")
                else:
                    logger.warning(f"Failed to create family sharing for album {album_id}")
            
            from .models import AlbumResponse
            return AlbumResponse(
                album_id=album_id,
                name=request.name,
                description=request.description,
                user_id=request.user_id,
                cover_photo_id=request.cover_photo_id,
                photo_count=0,
                auto_sync=request.auto_sync,
                is_family_shared=request.enable_family_sharing,
                sharing_resource_id=sharing_resource_id,
                sync_frames=[],
                tags=request.tags,
                created_at=current_time,
                updated_at=current_time,
                last_synced_at=None
            )
            
        except Exception as e:
            logger.error(f"Error creating album: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create album: {str(e)}")

    async def get_album(self, album_id: str, user_id: str) -> 'AlbumResponse':
        """获取相册详情 - 支持家庭共享权限检查"""
        try:
            # 1. 尝试直接获取用户拥有的相册
            album_data = await self.repository.get_album_by_id(album_id, user_id)
            
            # 2. 如果用户不是相册所有者，检查家庭共享权限
            if not album_data:
                has_shared_access = await self.check_family_album_access(album_id, user_id, "read")
                if has_shared_access:
                    # 通过共享访问，获取相册数据（使用相册所有者查询）
                    album_data = await self.repository.get_album_by_id_any_user(album_id)
                    if not album_data:
                        raise HTTPException(status_code=404, detail="Album not found")
                else:
                    raise HTTPException(status_code=404, detail="Album not found")
            
            # 3. 获取家庭共享信息
            family_sharing_info = None
            if album_data.get("is_family_shared") and album_data.get("sharing_resource_id"):
                async with OrganizationServiceClient() as org_client:
                    family_sharing_info = await org_client.get_sharing(
                        organization_id=album_data.get("organization_id"),
                        sharing_id=album_data.get("sharing_resource_id"),
                        user_id=user_id
                    )
            
            from .models import AlbumResponse
            return AlbumResponse(
                album_id=album_data["album_id"],
                name=album_data["name"],
                description=album_data.get("description"),
                user_id=album_data["user_id"],
                cover_photo_id=album_data.get("cover_photo_id"),
                photo_count=album_data.get("photo_count", 0),
                auto_sync=album_data.get("auto_sync", True),
                is_family_shared=album_data.get("is_family_shared", False),
                sharing_resource_id=album_data.get("sharing_resource_id"),
                sync_frames=album_data.get("sync_frames", []),
                tags=album_data.get("tags", []),
                created_at=datetime.fromisoformat(album_data["created_at"]) if album_data.get("created_at") else None,
                updated_at=datetime.fromisoformat(album_data["updated_at"]) if album_data.get("updated_at") else None,
                last_synced_at=datetime.fromisoformat(album_data["last_synced_at"]) if album_data.get("last_synced_at") else None,
                family_sharing_info=family_sharing_info
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting album {album_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get album: {str(e)}")

    async def check_family_album_access(self, album_id: str, user_id: str, required_permission: str = "read") -> bool:
        """检查家庭共享相册访问权限"""
        try:
            async with OrganizationServiceClient() as org_client:
                return await org_client.check_access(
                    resource_type="album",
                    resource_id=album_id,
                    user_id=user_id,
                    required_permission=required_permission
                )
        except Exception as e:
            logger.error(f"Error checking family album access: {e}")
            return False

    async def list_user_albums(self, user_id: str, limit: int = 100, offset: int = 0) -> 'AlbumListResponse':
        """获取用户相册列表"""
        try:
            albums_data = await self.repository.list_user_albums(user_id, limit, offset)
            
            from .models import AlbumResponse, AlbumListResponse
            albums = []
            
            for album_data in albums_data:
                album = AlbumResponse(
                    album_id=album_data["album_id"],
                    name=album_data["name"],
                    description=album_data.get("description"),
                    user_id=album_data["user_id"],
                    cover_photo_id=album_data.get("cover_photo_id"),
                    photo_count=album_data.get("photo_count", 0),
                    auto_sync=album_data.get("auto_sync", True),
                    is_family_shared=album_data.get("is_family_shared", False),
                    sharing_resource_id=album_data.get("sharing_resource_id"),
                    sync_frames=album_data.get("sync_frames", []),
                    tags=album_data.get("tags", []),
                    created_at=datetime.fromisoformat(album_data["created_at"]) if album_data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(album_data["updated_at"]) if album_data.get("updated_at") else None,
                    last_synced_at=datetime.fromisoformat(album_data["last_synced_at"]) if album_data.get("last_synced_at") else None,
                    family_sharing_info=None
                )
                albums.append(album)
            
            return AlbumListResponse(
                albums=albums,
                count=len(albums),
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            logger.error(f"Error listing albums for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to list albums: {str(e)}")

    async def update_album(self, album_id: str, user_id: str, request: 'UpdateAlbumRequest') -> 'AlbumResponse':
        """更新相册"""
        try:
            # 构建更新数据
            updates = {}
            if request.name is not None:
                updates["name"] = request.name
            if request.description is not None:
                updates["description"] = request.description
            if request.cover_photo_id is not None:
                updates["cover_photo_id"] = request.cover_photo_id
            if request.auto_sync is not None:
                updates["auto_sync"] = request.auto_sync
            if request.enable_family_sharing is not None:
                updates["is_family_shared"] = request.enable_family_sharing
            if request.tags is not None:
                updates["tags"] = request.tags
            
            success = await self.repository.update_album(album_id, user_id, updates)
            if not success:
                raise HTTPException(status_code=404, detail="Album not found")
            
            # 返回更新后的相册
            return await self.get_album(album_id, user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating album {album_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update album: {str(e)}")

    async def delete_album(self, album_id: str, user_id: str) -> Dict[str, Any]:
        """删除相册"""
        try:
            success = await self.repository.delete_album(album_id, user_id)
            if not success:
                raise HTTPException(status_code=404, detail="Album not found")
            
            return {
                "success": True,
                "album_id": album_id,
                "message": "Album deleted successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting album {album_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete album: {str(e)}")

    async def add_photos_to_album(self, album_id: str, request: 'AddPhotosToAlbumRequest') -> Dict[str, Any]:
        """添加照片到相册"""
        try:
            # 验证相册存在
            album = await self.repository.get_album_by_id(album_id, request.added_by)
            if not album:
                raise HTTPException(status_code=404, detail="Album not found")
            
            # 验证照片存在
            for photo_id in request.photo_ids:
                file_info = await self.repository.get_file_by_id(photo_id, request.added_by)
                if not file_info:
                    raise HTTPException(status_code=404, detail=f"Photo {photo_id} not found")
            
            success = await self.repository.add_photos_to_album(
                album_id, request.photo_ids, request.added_by
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to add photos to album")
            
            return {
                "success": True,
                "album_id": album_id,
                "added_photos": len(request.photo_ids),
                "message": f"Successfully added {len(request.photo_ids)} photos to album"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding photos to album {album_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add photos: {str(e)}")

    async def get_album_photos(self, album_id: str, user_id: str, limit: int = 50, offset: int = 0) -> 'AlbumPhotosResponse':
        """获取相册照片列表"""
        try:
            # 验证用户有权限访问该相册
            album = await self.repository.get_album_by_id(album_id, user_id)
            if not album:
                raise HTTPException(status_code=404, detail="Album not found")
            
            photos_data = await self.repository.get_album_photos(album_id, limit, offset)
            
            from .models import AlbumPhotosResponse
            return AlbumPhotosResponse(
                album_id=album_id,
                photos=photos_data,
                count=len(photos_data),
                limit=limit,
                offset=offset
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting photos for album {album_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get album photos: {str(e)}")

    async def add_family_member(self, album_id: str, request: 'AddFamilyMemberRequest', user_id: str) -> Dict[str, Any]:
        """添加家庭成员"""
        import uuid
        from datetime import datetime
        
        try:
            # 验证相册存在且用户有权限
            album = await self.repository.get_album_by_id(album_id, user_id)
            if not album:
                raise HTTPException(status_code=404, detail="Album not found")
            
            member_id = f"member_{uuid.uuid4().hex[:12]}"
            current_time = datetime.now(timezone.utc)
            
            member_data = {
                "member_id": member_id,
                "album_id": album_id,
                "user_id": request.user_id,
                "name": request.name,
                "relationship": request.relationship,
                "avatar_photo_id": request.avatar_photo_id,
                "face_encodings": None,
                "face_photos": [],
                "can_add_photos": request.can_add_photos,
                "can_edit_album": request.can_edit_album,
                "created_at": current_time.isoformat(),
                "updated_at": current_time.isoformat()
            }
            
            created_member = await self.repository.add_family_member(member_data)
            
            return {
                "success": True,
                "member_id": member_id,
                "album_id": album_id,
                "message": "Family member added successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding family member to album {album_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add family member: {str(e)}")

    async def get_album_sync_status(self, album_id: str, frame_id: str, user_id: str) -> 'AlbumSyncResponse':
        """获取相册同步状态"""
        try:
            # 验证相册存在且用户有权限
            album = await self.repository.get_album_by_id(album_id, user_id)
            if not album:
                raise HTTPException(status_code=404, detail="Album not found")
            
            sync_data = await self.repository.get_album_sync_status(album_id, frame_id)
            
            if not sync_data:
                # 如果没有同步记录，创建一个默认的
                sync_data = {
                    "album_id": album_id,
                    "frame_id": frame_id,
                    "sync_status": "pending",
                    "sync_version": 0,
                    "total_photos": album.get("photo_count", 0),
                    "synced_photos": 0,
                    "pending_photos": album.get("photo_count", 0),
                    "failed_photos": 0,
                    "last_sync_timestamp": None
                }
            
            from .models import AlbumSyncResponse
            return AlbumSyncResponse(
                album_id=album_id,
                frame_id=frame_id,
                sync_status=sync_data.get("sync_status", "pending"),
                last_sync_timestamp=datetime.fromisoformat(sync_data["last_sync_timestamp"]) if sync_data.get("last_sync_timestamp") else None,
                sync_version=sync_data.get("sync_version", 0),
                progress={
                    "total": sync_data.get("total_photos", 0),
                    "synced": sync_data.get("synced_photos", 0),
                    "pending": sync_data.get("pending_photos", 0),
                    "failed": sync_data.get("failed_photos", 0)
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting sync status for album {album_id}, frame {frame_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")

    async def share_album_with_family(self, album_id: str, request: 'ShareAlbumRequest', user_id: str) -> Dict[str, Any]:
        """创建或更新相册的家庭共享"""
        try:
            # 1. 验证相册存在且用户有权限
            album = await self.repository.get_album_by_id(album_id, user_id)
            if not album:
                raise HTTPException(status_code=404, detail="Album not found")
            
            if not album.get("organization_id"):
                raise HTTPException(status_code=400, detail="Album must be associated with an organization for family sharing")

            async with OrganizationServiceClient() as org_client:
                # 2. 检查是否已有共享设置
                sharing_resource_id = album.get("sharing_resource_id")

                if sharing_resource_id:
                    # 更新现有共享设置
                    sharing_updates = {}
                    if request.shared_with_members is not None:
                        sharing_updates["shared_with_members"] = request.shared_with_members
                    if request.default_permission:
                        sharing_updates["default_permission"] = request.default_permission
                    if request.custom_permissions:
                        sharing_updates["custom_permissions"] = request.custom_permissions

                    sharing_updates["share_with_all_members"] = request.share_with_all_family

                    updated = await org_client.update_sharing(
                        organization_id=album.get("organization_id"),
                        sharing_id=sharing_resource_id,
                        user_id=user_id,
                        updates=sharing_updates
                    )
                    success = updated is not None

                    if success:
                        # 更新相册的家庭共享状态
                        await self.repository.update_album(album_id, user_id, {
                            "is_family_shared": True
                        })

                        return {
                            "success": True,
                            "album_id": album_id,
                            "sharing_resource_id": sharing_resource_id,
                            "action": "updated",
                            "message": "Album sharing updated successfully"
                        }
                    else:
                        raise HTTPException(status_code=500, detail="Failed to update album sharing")
                else:
                    # 创建新的共享设置
                    sharing_result = await org_client.create_sharing(
                        organization_id=album["organization_id"],
                        user_id=user_id,
                        resource_type="album",
                        resource_id=album_id,
                        resource_name=album["name"],
                        shared_with_members=request.shared_with_members,
                        share_with_all_members=request.share_with_all_family,
                        default_permission=request.default_permission,
                        custom_permissions=request.custom_permissions
                    )

                    if sharing_result:
                        new_sharing_resource_id = sharing_result.get("sharing_id")

                        # 更新相册记录
                        await self.repository.update_album(album_id, user_id, {
                            "is_family_shared": True,
                            "sharing_resource_id": new_sharing_resource_id
                        })

                        return {
                            "success": True,
                            "album_id": album_id,
                            "sharing_resource_id": new_sharing_resource_id,
                            "action": "created",
                            "message": "Album sharing created successfully"
                        }
                    else:
                        raise HTTPException(status_code=500, detail="Failed to create album sharing")
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sharing album {album_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to share album: {str(e)}")

    async def get_user_accessible_albums(self, user_id: str, include_shared: bool = True, limit: int = 100, offset: int = 0) -> 'AlbumListResponse':
        """获取用户可访问的所有相册（包括共享相册）"""
        try:
            # 1. 获取用户拥有的相册
            owned_albums = await self.repository.list_user_albums(user_id, limit, offset)
            
            # 2. 如果包含共享相册，获取通过家庭共享可访问的相册
            shared_albums = []
            if include_shared:
                try:
                    # Get user's organizations and their shared albums
                    async with OrganizationServiceClient() as org_client:
                        # For now, we need the organization_id to query shared resources
                        # This would need to be refactored to get all orgs for user first
                        shared_album_resources = []  # Placeholder - needs organization context
                    
                    # 获取共享相册的详细信息
                    for resource in shared_album_resources:
                        album_id = resource.get("resource_id")
                        if album_id:
                            album_data = await self.repository.get_album_by_id_any_user(album_id)
                            if album_data and album_data["user_id"] != user_id:  # 排除自己的相册
                                shared_albums.append(album_data)
                except Exception as e:
                    logger.warning(f"Failed to get shared albums for user {user_id}: {e}")
            
            # 3. 合并结果
            all_albums_data = owned_albums + shared_albums
            
            from .models import AlbumResponse, AlbumListResponse
            albums = []
            
            for album_data in all_albums_data:
                album = AlbumResponse(
                    album_id=album_data["album_id"],
                    name=album_data["name"],
                    description=album_data.get("description"),
                    user_id=album_data["user_id"],
                    cover_photo_id=album_data.get("cover_photo_id"),
                    photo_count=album_data.get("photo_count", 0),
                    auto_sync=album_data.get("auto_sync", True),
                    is_family_shared=album_data.get("is_family_shared", False),
                    sharing_resource_id=album_data.get("sharing_resource_id"),
                    sync_frames=album_data.get("sync_frames", []),
                    tags=album_data.get("tags", []),
                    created_at=datetime.fromisoformat(album_data["created_at"]) if album_data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(album_data["updated_at"]) if album_data.get("updated_at") else None,
                    last_synced_at=datetime.fromisoformat(album_data["last_synced_at"]) if album_data.get("last_synced_at") else None
                )
                albums.append(album)
            
            return AlbumListResponse(
                albums=albums,
                count=len(albums),
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            logger.error(f"Error getting accessible albums for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get accessible albums: {str(e)}")

    # ==================== Gallery & Slideshow Features ====================
    
    async def create_playlist(self, request: 'CreatePlaylistRequest') -> Dict[str, Any]:
        """创建幻灯片播放列表"""
        try:
            playlist_data = {
                "name": request.name,
                "description": request.description,
                "user_id": request.user_id,
                "playlist_type": request.playlist_type.value,
                "photo_ids": json.dumps(request.photo_ids),
                "album_ids": json.dumps(request.album_ids),
                "smart_criteria": json.dumps(request.smart_criteria.dict()) if request.smart_criteria else None,
                "rotation_type": request.rotation_type.value,
                "transition_duration": request.transition_duration,
                "photo_count": len(request.photo_ids)
            }
            
            result = await self.repository.create_playlist(playlist_data)
            if not result:
                raise HTTPException(status_code=500, detail="Failed to create playlist")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_playlist_photos(self, playlist_id: str, user_id: str) -> Dict[str, Any]:
        """获取播放列表的照片（含预加载URL）"""
        try:
            playlist = await self.repository.get_playlist(playlist_id)
            if not playlist:
                raise HTTPException(status_code=404, detail="Playlist not found")
            
            # Get photos based on playlist type
            photo_ids = json.loads(playlist.get("photo_ids", "[]"))
            
            if playlist["playlist_type"] == "album":
                # Get photos from albums
                album_ids = json.loads(playlist.get("album_ids", "[]"))
                photos = []
                for album_id in album_ids:
                    album_photos = await self.repository.get_album_photos(album_id)
                    photos.extend(album_photos)
            elif playlist["playlist_type"] == "favorites":
                # Get favorite photos
                photos = await self.repository.get_favorite_photos(user_id, limit=100)
            elif playlist["playlist_type"] == "smart":
                # Smart selection based on criteria
                photos = await self._smart_photo_selection(user_id, playlist.get("smart_criteria"))
            else:
                # Manual playlist - get specific photos
                if photo_ids:
                    photos = []
                    for photo_id in photo_ids:
                        file = await self.repository.get_file_by_id(photo_id, user_id)
                        if file:
                            photos.append(file)
                else:
                    photos = []
            
            # Generate download URLs for each photo
            photo_list = []
            for photo in photos:
                download_url = await self.generate_download_url(photo.get("file_id"), user_id, expiry_hours=24)
                photo_data = {
                    **photo,
                    "download_url": download_url
                }
                photo_list.append(photo_data)
            
            return {
                "playlist_id": playlist_id,
                "photos": photo_list,
                "total": len(photo_list)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting playlist photos: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _smart_photo_selection(self, user_id: str, criteria: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """AI智能照片选择"""
        try:
            if not criteria:
                # Default: recent high-quality photos
                files = await self.repository.list_user_files(user_id, limit=50, offset=0)
                return files
            
            # Parse criteria
            criteria_obj = criteria if isinstance(criteria, dict) else json.loads(criteria)
            
            # Build query filters
            query_filters = []
            
            # Get all user photos
            all_photos = await self.repository.list_user_files(user_id, limit=500, offset=0)
            
            # Filter by criteria
            filtered_photos = []
            for photo in all_photos:
                # Check if image type
                if not photo.get("content_type", "").startswith("image/"):
                    continue
                
                # Get metadata
                metadata = await self.repository.get_photo_metadata(photo["file_id"])
                
                # Apply filters
                if criteria_obj.get("favorites_only") and not (metadata and metadata.get("is_favorite")):
                    continue
                
                if criteria_obj.get("min_quality_score") and metadata:
                    if not metadata.get("quality_score") or metadata["quality_score"] < criteria_obj["min_quality_score"]:
                        continue
                
                if criteria_obj.get("has_faces") is not None and metadata:
                    if metadata.get("has_faces") != criteria_obj["has_faces"]:
                        continue
                
                # Date range filter
                if criteria_obj.get("date_range_days"):
                    days_ago = datetime.now(timezone.utc) - timedelta(days=criteria_obj["date_range_days"])
                    photo_date = datetime.fromisoformat(photo.get("uploaded_at", ""))
                    if photo_date < days_ago:
                        continue
                
                filtered_photos.append(photo)
            
            # Apply diversity and quality scoring
            max_photos = criteria_obj.get("max_photos", 50)
            if len(filtered_photos) > max_photos:
                # Simple selection: take most recent
                filtered_photos.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
                filtered_photos = filtered_photos[:max_photos]
            
            return filtered_photos
            
        except Exception as e:
            logger.error(f"Error in smart photo selection: {e}")
            return []
    
    async def get_random_photos(self, user_id: str, count: int = 10, criteria: Optional['SmartSelectionCriteria'] = None) -> Dict[str, Any]:
        """获取随机照片用于幻灯片"""
        try:
            import random
            
            # Get photos based on criteria
            if criteria:
                photos = await self._smart_photo_selection(user_id, criteria.dict() if hasattr(criteria, 'dict') else criteria)
            else:
                # Get all user photos
                photos = await self.repository.list_user_files(user_id, limit=500, offset=0)
                # Filter to images only
                photos = [p for p in photos if p.get("content_type", "").startswith("image/")]
            
            # Randomly select
            if len(photos) > count:
                selected_photos = random.sample(photos, count)
            else:
                selected_photos = photos
            
            # Generate download URLs
            photo_list = []
            for photo in selected_photos:
                download_url = await self.generate_download_url(photo["file_id"], user_id, expiry_hours=24)
                photo_data = {
                    **photo,
                    "download_url": download_url
                }
                photo_list.append(photo_data)
            
            return {
                "photos": photo_list,
                "count": len(photo_list),
                "criteria_applied": criteria.dict() if criteria and hasattr(criteria, 'dict') else None
            }
            
        except Exception as e:
            logger.error(f"Error getting random photos: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def preload_images(self, request: 'PreloadImagesRequest') -> Dict[str, Any]:
        """预加载图片到缓存"""
        try:
            cached_count = 0
            failed_count = 0
            
            for photo_id in request.photo_ids:
                # Get file info
                file = await self.repository.get_file_by_id(photo_id, request.user_id)
                if not file:
                    failed_count += 1
                    continue
                
                # Check if already cached
                cache_entry = await self.repository.get_cache_entry(request.frame_id, photo_id)
                
                if cache_entry and cache_entry["status"] == "cached":
                    # Already cached, increment hit count
                    await self.repository.increment_cache_hit(cache_entry["cache_id"])
                    cached_count += 1
                    continue
                
                # Generate download URL
                download_url = await self.generate_download_url(photo_id, request.user_id, expiry_hours=24)
                
                # Create cache entry
                cache_data = {
                    "photo_id": photo_id,
                    "frame_id": request.frame_id,
                    "user_id": request.user_id,
                    "original_url": download_url,
                    "cache_key": f"{request.frame_id}:{photo_id}",
                    "status": "pending",
                    "priority": request.priority,
                    "file_size": file.get("file_size"),
                    "content_type": file.get("content_type"),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                }
                
                result = await self.repository.create_cache_entry(cache_data)
                if result:
                    cached_count += 1
                else:
                    failed_count += 1
            
            return {
                "frame_id": request.frame_id,
                "requested": len(request.photo_ids),
                "cached": cached_count,
                "failed": failed_count,
                "message": f"Preloaded {cached_count} photos, {failed_count} failed"
            }
            
        except Exception as e:
            logger.error(f"Error preloading images: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_cache_stats(self, frame_id: str) -> Dict[str, Any]:
        """获取设备缓存统计"""
        try:
            stats = await self.repository.get_frame_cache_stats(frame_id)
            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_photo_metadata(self, request: 'UpdatePhotoMetadataRequest', user_id: str) -> Dict[str, Any]:
        """更新照片元数据"""
        try:
            # Verify user owns the photo
            file = await self.repository.get_file_by_id(request.file_id, user_id)
            if not file:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Get existing metadata or create new
            existing = await self.repository.get_photo_metadata(request.file_id)
            
            metadata = {
                "file_id": request.file_id,
                "is_favorite": request.is_favorite if request.is_favorite is not None else (existing.get("is_favorite", False) if existing else False),
                "rating": request.rating if request.rating is not None else (existing.get("rating") if existing else None),
                "tags": request.tags if request.tags is not None else (existing.get("tags", []) if existing else []),
                "location_name": request.location_name if request.location_name is not None else (existing.get("location_name") if existing else None),
                "latitude": request.latitude if request.latitude is not None else (existing.get("latitude") if existing else None),
                "longitude": request.longitude if request.longitude is not None else (existing.get("longitude") if existing else None),
            }
            
            result = await self.repository.upsert_photo_metadata(metadata)
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating photo metadata: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_rotation_schedule(self, request: 'CreateRotationScheduleRequest') -> Dict[str, Any]:
        """创建照片轮播计划"""
        try:
            # Verify playlist exists
            playlist = await self.repository.get_playlist(request.playlist_id)
            if not playlist:
                raise HTTPException(status_code=404, detail="Playlist not found")
            
            schedule_data = {
                "playlist_id": request.playlist_id,
                "frame_id": request.frame_id,
                "user_id": request.user_id,
                "start_time": request.start_time,
                "end_time": request.end_time,
                "days_of_week": json.dumps(request.days_of_week),
                "interval_seconds": request.interval_seconds,
                "shuffle": request.shuffle
            }
            
            result = await self.repository.create_rotation_schedule(schedule_data)
            if not result:
                raise HTTPException(status_code=500, detail="Failed to create rotation schedule")
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating rotation schedule: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_frame_playlists(self, frame_id: str) -> List[Dict[str, Any]]:
        """获取设备的播放列表"""
        try:
            schedules = await self.repository.get_frame_schedules(frame_id)
            
            playlists = []
            for schedule in schedules:
                playlist = await self.repository.get_playlist(schedule["playlist_id"])
                if playlist:
                    playlists.append({
                        **playlist,
                        "schedule": schedule
                    })
            
            return playlists
            
        except Exception as e:
            logger.error(f"Error getting frame playlists: {e}")
            return []