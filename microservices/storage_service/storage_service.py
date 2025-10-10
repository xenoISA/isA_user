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
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO, Any
from datetime import datetime, timedelta
from io import BytesIO

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException

from .storage_repository import StorageRepository
from .models import (
    StoredFile, FileShare, StorageQuota,
    FileStatus, StorageProvider, FileAccessLevel,
    FileUploadRequest, FileUploadResponse,
    FileListRequest, FileInfoResponse,
    FileShareRequest, FileShareResponse,
    StorageStatsResponse,
    PhotoVersionType, PhotoVersion, PhotoWithVersions,
    SavePhotoVersionRequest, SavePhotoVersionResponse,
    SwitchPhotoVersionRequest, GetPhotoVersionsRequest
)
from core.consul_registry import ConsulRegistry

logger = logging.getLogger(__name__)


class StorageService:
    """存储服务业务逻辑层"""

    def __init__(self, config):
        """
        初始化存储服务

        Args:
            config: 配置对象
        """
        self.repository = StorageRepository()
        self.config = config
        self.consul = None
        self._init_consul()

        # MinIO配置
        self.minio_client = Minio(
            endpoint=getattr(config, 'minio_endpoint', 'localhost:9000'),
            access_key=getattr(config, 'minio_access_key', 'minioadmin'),
            secret_key=getattr(config, 'minio_secret_key', 'minioadmin'),
            secure=getattr(config, 'minio_secure', False)
        )
        
        self.bucket_name = getattr(config, 'minio_bucket_name', 'isA-storage')
        
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

    def _init_consul(self):
        """Initialize Consul registry for service discovery"""
        try:
            from core.config_manager import ConfigManager
            config_manager = ConfigManager("storage_service")
            config = config_manager.get_service_config()

            if config.consul_enabled:
                self.consul = ConsulRegistry(
                    service_name=config.service_name,
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port
                )
                logger.info("Consul service discovery initialized for storage service")
        except Exception as e:
            logger.warning(f"Failed to initialize Consul: {e}, will use fallback URLs")

    def _get_service_url(self, service_name: str, fallback_port: int) -> str:
        """Get service URL via Consul discovery with fallback"""
        fallback_url = f"http://localhost:{fallback_port}"
        if self.consul:
            return self.consul.get_service_address(service_name, fallback_url=fallback_url)
        return fallback_url
    
    def _ensure_bucket_exists(self):
        """确保MinIO bucket存在"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
                
                # 设置bucket策略允许公共读取（可选）
                # self._set_bucket_policy()
            else:
                logger.info(f"MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise
    
    def _generate_object_name(self, user_id: str, filename: str) -> str:
        """生成对象存储路径"""
        now = datetime.utcnow()
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
        quota = await self.repository.get_storage_quota(user_id=user_id)
        
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
            
            # 上传到MinIO
            file_stream = BytesIO(file_content)
            result = self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_stream,
                length=file_size,
                content_type=content_type,
                metadata={
                    "file-id": file_id,
                    "user-id": request.user_id,
                    "original-name": file.filename,
                    "checksum": checksum,
                    **(request.metadata or {})
                }
            )
            
            # 生成预签名下载URL（1小时有效）
            download_url = self.minio_client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(hours=1)
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
                etag=result.etag,
                version_id=result.version_id,
                metadata=request.metadata,
                tags=request.tags,
                download_url=download_url,
                download_url_expires_at=datetime.utcnow() + timedelta(hours=1),
                uploaded_at=datetime.utcnow()
            )
            
            await self.repository.create_file_record(stored_file)
            
            # 更新用户配额使用量
            await self.repository.update_storage_usage(
                user_id=request.user_id,
                bytes_delta=file_size,
                file_count_delta=1
            )
            
            # 如果设置了自动删除
            if request.auto_delete_after_days:
                # 这里应该创建一个定时任务来删除文件
                pass
            
            return FileUploadResponse(
                file_id=file_id,
                file_path=object_name,
                download_url=download_url,
                file_size=file_size,
                content_type=content_type,
                uploaded_at=datetime.utcnow()
            )
            
        except S3Error as e:
            logger.error(f"MinIO error uploading file: {e}")
            raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
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
        if not file.download_url or file.download_url_expires_at < datetime.utcnow():
            try:
                download_url = self.minio_client.presigned_get_object(
                    bucket_name=file.bucket_name,
                    object_name=file.object_name,
                    expires=timedelta(hours=1)
                )
                file.download_url = download_url
                file.download_url_expires_at = datetime.utcnow() + timedelta(hours=1)
            except S3Error:
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
            if not file.download_url or file.download_url_expires_at < datetime.utcnow():
                try:
                    download_url = self.minio_client.presigned_get_object(
                        bucket_name=file.bucket_name,
                        object_name=file.object_name,
                        expires=timedelta(hours=1)
                    )
                    file.download_url = download_url
                except S3Error:
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
                self.minio_client.remove_object(
                    bucket_name=file.bucket_name,
                    object_name=file.object_name
                )
            except S3Error as e:
                logger.error(f"Error deleting file from MinIO: {e}")
                # 继续处理，即使MinIO删除失败
        
        # 更新数据库状态
        success = await self.repository.delete_file(file_id, user_id)
        
        if success:
            # 更新配额使用量
            await self.repository.update_storage_usage(
                user_id=user_id,
                bytes_delta=-file.file_size,
                file_count_delta=-1
            )
        
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
            expires_at=datetime.utcnow() + timedelta(hours=request.expires_hours)
        )
        
        created_share = await self.repository.create_file_share(share)
        
        # 生成分享URL
        base_url = self._get_service_url('wallet_service', 8209) if hasattr(self, '_get_service_url') else 'http://localhost:8209'
        share_url = f"{base_url}/api/shares/{created_share.share_id}?token={access_token}"
        
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
                download_url = self.minio_client.presigned_get_object(
                    bucket_name=file.bucket_name,
                    object_name=file.object_name,
                    expires=timedelta(minutes=15)  # 分享的URL有效期短一些
                )
            except S3Error:
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
        quota = await self.repository.get_storage_quota(user_id, organization_id)
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
        timestamp = datetime.utcnow()
        
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
                self.minio_client.make_bucket(bucket_name)
            
            # 上传文件
            self.minio_client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=BytesIO(image_data),
                length=len(image_data),
                content_type=content_type,
                metadata={
                    'photo_id': request.photo_id,
                    'version_id': version_id,
                    'version_type': request.version_type.value,
                    'processing_mode': request.processing_mode or '',
                    'created_at': timestamp.isoformat()
                }
            )
            
            # 生成云端访问URL
            cloud_url = self.minio_client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(days=7)  # 7天有效期（最大允许值）
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
            self.minio_client.remove_object(bucket_name, object_name)
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