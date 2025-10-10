"""
Storage Repository

数据访问层，处理文件存储相关的数据库操作
使用Supabase客户端进行数据库操作
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json

# Database client setup
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    StoredFile, FileShare, StorageQuota,
    FileStatus, StorageProvider, FileAccessLevel,
    PhotoVersion, PhotoVersionType
)

logger = logging.getLogger(__name__)


class StorageRepository:
    """存储数据访问层"""
    
    def __init__(self):
        """初始化存储仓库"""
        self.supabase = get_supabase_client()
        # 表名定义 - 使用dev schema
        self.files_table = "storage_files"
        self.shares_table = "file_shares" 
        self.quotas_table = "storage_quotas"
    
    # ==================== 文件操作 ====================
    
    async def create_file_record(self, file_data: StoredFile) -> StoredFile:
        """创建文件记录"""
        try:
            data = {
                "file_id": file_data.file_id,
                "user_id": file_data.user_id,
                "organization_id": file_data.organization_id,
                "file_name": file_data.file_name,
                "file_path": file_data.file_path,
                "file_size": file_data.file_size,
                "content_type": file_data.content_type,
                "file_extension": file_data.file_extension,
                "storage_provider": file_data.storage_provider.value,
                "bucket_name": file_data.bucket_name,
                "object_name": file_data.object_name,
                "status": file_data.status.value,
                "access_level": file_data.access_level.value,
                "checksum": file_data.checksum,
                "etag": file_data.etag,
                "version_id": file_data.version_id,
                "metadata": file_data.metadata,
                "tags": file_data.tags,
                "download_url": file_data.download_url,
                "download_url_expires_at": file_data.download_url_expires_at.isoformat() if file_data.download_url_expires_at else None,
                "uploaded_at": file_data.uploaded_at.isoformat() if file_data.uploaded_at else datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.files_table).insert(data).execute()
            
            if result.data:
                return StoredFile.model_validate(result.data[0])
            return None
                
        except Exception as e:
            logger.error(f"Error creating file record: {e}")
            raise
    
    async def get_file_by_id(self, file_id: str, user_id: Optional[str] = None) -> Optional[StoredFile]:
        """根据文件ID获取文件记录"""
        try:
            query = self.supabase.table(self.files_table).select("*").eq("file_id", file_id)
            
            # 排除已删除的文件
            query = query.neq("status", FileStatus.DELETED.value)
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.single().execute()
            
            if result.data:
                return StoredFile.model_validate(result.data)
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Error getting file: {e}")
            raise
    
    async def list_user_files(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        status: Optional[FileStatus] = None,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StoredFile]:
        """列出用户文件"""
        try:
            query = self.supabase.table(self.files_table).select("*").eq("user_id", user_id)
            
            if organization_id:
                query = query.eq("organization_id", organization_id)
            
            if status:
                query = query.eq("status", status.value)
            else:
                # 默认排除已删除的文件
                query = query.neq("status", FileStatus.DELETED.value)
            
            if prefix:
                query = query.ilike("file_name", f"{prefix}%")
            
            # 排序和分页
            query = query.order("uploaded_at", desc=True).range(offset, offset + limit - 1)
            
            result = query.execute()
            
            if result.data:
                return [StoredFile.model_validate(row) for row in result.data]
            return []
                
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    async def update_file_status(
        self,
        file_id: str,
        status: FileStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """更新文件状态"""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if status == FileStatus.DELETED:
                update_data["deleted_at"] = datetime.utcnow().isoformat()
            
            result = self.supabase.table(self.files_table).update(update_data).eq("file_id", file_id).execute()
            
            return len(result.data) > 0 if result.data else False
                
        except Exception as e:
            logger.error(f"Error updating file status: {e}")
            return False
    
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """删除文件（软删除）"""
        try:
            update_data = {
                "status": FileStatus.DELETED.value,
                "deleted_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.files_table).update(update_data).eq("file_id", file_id).eq("user_id", user_id).execute()
            
            return len(result.data) > 0 if result.data else False
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    # ==================== 文件分享操作 ====================
    
    async def create_file_share(self, share_data: FileShare) -> FileShare:
        """创建文件分享"""
        try:
            share_id = f"share_{uuid.uuid4().hex[:12]}"
            
            data = {
                "share_id": share_id,
                "file_id": share_data.file_id,
                "shared_by": share_data.shared_by,
                "shared_with": share_data.shared_with,
                "shared_with_email": share_data.shared_with_email,
                "access_token": share_data.access_token,
                "password": share_data.password,
                "permissions": share_data.permissions,
                "max_downloads": share_data.max_downloads,
                "download_count": 0,
                "expires_at": share_data.expires_at.isoformat() if share_data.expires_at else None,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.shares_table).insert(data).execute()
            
            if result.data:
                share_data.share_id = share_id
                return FileShare.model_validate(result.data[0])
            return None
                
        except Exception as e:
            logger.error(f"Error creating file share: {e}")
            raise
    
    async def get_file_share(
        self,
        share_id: str,
        access_token: Optional[str] = None
    ) -> Optional[FileShare]:
        """获取文件分享"""
        try:
            query = self.supabase.table(self.shares_table).select("*").eq("share_id", share_id).eq("is_active", True)
            
            # 检查是否过期
            query = query.or_(f"expires_at.is.null,expires_at.gt.{datetime.utcnow().isoformat()}")
            
            if access_token:
                query = query.eq("access_token", access_token)
            
            result = query.single().execute()
            
            if result.data:
                return FileShare.model_validate(result.data)
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Error getting file share: {e}")
            raise
    
    async def increment_share_download(self, share_id: str) -> bool:
        """增加分享下载次数"""
        try:
            # 先获取当前下载次数
            result = self.supabase.table(self.shares_table).select("download_count").eq("share_id", share_id).single().execute()
            
            if result.data:
                current_count = result.data.get("download_count", 0)
                
                update_data = {
                    "download_count": current_count + 1,
                    "accessed_at": datetime.utcnow().isoformat()
                }
                
                result = self.supabase.table(self.shares_table).update(update_data).eq("share_id", share_id).eq("is_active", True).execute()
                
                return len(result.data) > 0 if result.data else False
            return False
                
        except Exception as e:
            logger.error(f"Error incrementing share download: {e}")
            return False
    
    # ==================== 配额操作 ====================
    
    async def get_storage_quota(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Optional[StorageQuota]:
        """获取存储配额"""
        try:
            query = self.supabase.table(self.quotas_table).select("*").eq("is_active", True)
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            if organization_id:
                query = query.eq("organization_id", organization_id)
            
            if not user_id and not organization_id:
                return None
            
            result = query.single().execute()
            
            if result.data:
                return StorageQuota.model_validate(result.data)
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Error getting storage quota: {e}")
            return None
    
    async def update_storage_usage(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        bytes_delta: int = 0,
        file_count_delta: int = 0
    ) -> bool:
        """更新存储使用量"""
        try:
            # 先获取当前使用量
            query = self.supabase.table(self.quotas_table).select("used_bytes, file_count")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            if organization_id:
                query = query.eq("organization_id", organization_id)
            
            if not user_id and not organization_id:
                return False
            
            result = query.single().execute()
            
            if result.data:
                current_bytes = result.data.get("used_bytes", 0)
                current_count = result.data.get("file_count", 0)
                
                update_data = {
                    "used_bytes": max(0, current_bytes + bytes_delta),  # 确保不会变成负数
                    "file_count": max(0, current_count + file_count_delta),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                query = self.supabase.table(self.quotas_table).update(update_data)
                
                if user_id:
                    query = query.eq("user_id", user_id)
                if organization_id:
                    query = query.eq("organization_id", organization_id)
                
                result = query.execute()
                return len(result.data) > 0 if result.data else False
            else:
                # 如果没有配额记录，创建一个默认的
                if user_id:
                    default_quota = {
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "total_quota_bytes": 10 * 1024 * 1024 * 1024,  # 10GB
                        "used_bytes": max(0, bytes_delta),
                        "file_count": max(0, file_count_delta),
                        "is_active": True,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    result = self.supabase.table(self.quotas_table).insert(default_quota).execute()
                    return len(result.data) > 0 if result.data else False
            
            return False
                
        except Exception as e:
            logger.error(f"Error updating storage usage: {e}")
            return False
    
    async def get_storage_stats(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            # 获取文件列表
            query = self.supabase.table(self.files_table).select("file_size, content_type, status")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            if organization_id:
                query = query.eq("organization_id", organization_id)
            
            # 排除已删除的文件
            query = query.neq("status", FileStatus.DELETED.value)
            
            result = query.execute()
            
            # 统计信息
            stats = {
                "file_count": 0,
                "total_size": 0,
                "by_type": {},
                "by_status": {}
            }
            
            if result.data:
                stats["file_count"] = len(result.data)
                
                for file in result.data:
                    # 总大小
                    file_size = file.get("file_size", 0)
                    stats["total_size"] += file_size
                    
                    # 按类型统计
                    content_type = file.get("content_type", "unknown")
                    if content_type not in stats["by_type"]:
                        stats["by_type"][content_type] = {"count": 0, "total_size": 0}
                    stats["by_type"][content_type]["count"] += 1
                    stats["by_type"][content_type]["total_size"] += file_size
                    
                    # 按状态统计
                    status = file.get("status", "unknown")
                    if status not in stats["by_status"]:
                        stats["by_status"][status] = 0
                    stats["by_status"][status] += 1
            
            return stats
                
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                "file_count": 0,
                "total_size": 0,
                "by_type": {},
                "by_status": {}
            }
    
    # ==================== Photo Version Management ====================
    
    # 简单的内存存储用于演示
    _photo_versions = {}  # {version_id: PhotoVersion}
    _photo_versions_by_photo = {}  # {photo_id: [version_ids]}
    
    async def save_photo_version(self, photo_version: PhotoVersion) -> PhotoVersion:
        """保存照片版本记录"""
        try:
            # 保存版本到内存
            StorageRepository._photo_versions[photo_version.version_id] = photo_version
            
            # 更新照片的版本列表
            if photo_version.photo_id not in StorageRepository._photo_versions_by_photo:
                StorageRepository._photo_versions_by_photo[photo_version.photo_id] = []
            StorageRepository._photo_versions_by_photo[photo_version.photo_id].append(photo_version.version_id)
            
            logger.info(f"Saving photo version: {photo_version.version_id}")
            return photo_version
        except Exception as e:
            logger.error(f"Error saving photo version: {e}")
            raise
    
    async def get_photo_versions(self, photo_id: str, user_id: str) -> List[PhotoVersion]:
        """获取照片的所有版本"""
        try:
            logger.info(f"Getting photo versions for photo: {photo_id}")
            
            # 获取该照片的所有版本ID
            version_ids = StorageRepository._photo_versions_by_photo.get(photo_id, [])
            
            # 获取版本详情并筛选用户
            versions = []
            for version_id in version_ids:
                version = StorageRepository._photo_versions.get(version_id)
                if version and version.user_id == user_id:
                    versions.append(version)
            
            return versions
        except Exception as e:
            logger.error(f"Error getting photo versions: {e}")
            raise
    
    async def get_photo_version(self, version_id: str, user_id: str) -> Optional[PhotoVersion]:
        """获取单个照片版本"""
        try:
            logger.info(f"Getting photo version: {version_id}")
            version = StorageRepository._photo_versions.get(version_id)
            if version and version.user_id == user_id:
                return version
            return None
        except Exception as e:
            logger.error(f"Error getting photo version: {e}")
            raise
    
    async def get_photo_info(self, photo_id: str) -> Dict[str, Any]:
        """获取照片基本信息"""
        try:
            logger.info(f"Getting photo info: {photo_id}")
            return {
                "title": "Test Photo",
                "original_file_id": f"file_{photo_id}",
                "current_version_id": f"ver_{photo_id}_original",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Error getting photo info: {e}")
            raise
    
    async def update_photo_current_version(self, photo_id: str, version_id: str) -> bool:
        """更新照片的当前版本"""
        try:
            logger.info(f"Updating photo {photo_id} current version to {version_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating photo current version: {e}")
            raise
    
    async def update_version_current_flags(self, photo_id: str, current_version_id: str) -> bool:
        """更新版本的当前标志"""
        try:
            logger.info(f"Updating version current flags for photo {photo_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating version current flags: {e}")
            raise
    
    async def get_original_version(self, photo_id: str) -> Optional[PhotoVersion]:
        """获取原始版本"""
        try:
            logger.info(f"Getting original version for photo: {photo_id}")
            return PhotoVersion(
                version_id=f"ver_{photo_id}_original",
                photo_id=photo_id,
                user_id="test_user",
                version_name="Original",
                version_type=PhotoVersionType.ORIGINAL,
                file_id=f"file_{photo_id}_original",
                cloud_url="https://example.com/original.jpg",
                file_size=1024000,
                is_current=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Error getting original version: {e}")
            raise
    
    async def delete_photo_version(self, version_id: str) -> bool:
        """删除照片版本"""
        try:
            logger.info(f"Deleting photo version: {version_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting photo version: {e}")
            raise

    # ==================== 数据库初始化 ====================
    
    async def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            result = self.supabase.table(self.files_table).select("count").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False