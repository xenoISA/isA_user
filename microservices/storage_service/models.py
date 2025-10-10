"""
Storage Service Models

定义文件存储相关的数据模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class FileStatus(str, Enum):
    """文件状态枚举"""
    UPLOADING = "uploading"
    AVAILABLE = "available"
    DELETED = "deleted"
    FAILED = "failed"
    ARCHIVED = "archived"


class StorageProvider(str, Enum):
    """存储提供商枚举"""
    MINIO = "minio"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"
    LOCAL = "local"


class FileAccessLevel(str, Enum):
    """文件访问级别"""
    PUBLIC = "public"
    PRIVATE = "private"
    RESTRICTED = "restricted"
    SHARED = "shared"


# ==================== Database Models ====================

class StoredFile(BaseModel):
    """存储文件模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    file_id: str = Field(..., description="文件唯一标识符")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    
    file_name: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="存储路径")
    file_size: int = Field(..., description="文件大小(字节)")
    content_type: str = Field(..., description="MIME类型")
    file_extension: Optional[str] = Field(None, description="文件扩展名")
    
    storage_provider: StorageProvider = Field(StorageProvider.MINIO, description="存储提供商")
    bucket_name: str = Field(..., description="存储桶名称")
    object_name: str = Field(..., description="对象名称")
    
    status: FileStatus = Field(FileStatus.AVAILABLE, description="文件状态")
    access_level: FileAccessLevel = Field(FileAccessLevel.PRIVATE, description="访问级别")
    
    checksum: Optional[str] = Field(None, description="文件校验和")
    etag: Optional[str] = Field(None, description="ETag")
    version_id: Optional[str] = Field(None, description="版本ID")
    
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")
    
    download_url: Optional[str] = Field(None, description="下载URL")
    download_url_expires_at: Optional[datetime] = Field(None, description="下载URL过期时间")
    
    uploaded_at: Optional[datetime] = Field(None, description="上传时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")


class FileShare(BaseModel):
    """文件分享模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    share_id: str = Field(..., description="分享ID")
    file_id: str = Field(..., description="文件ID")
    
    shared_by: str = Field(..., description="分享者用户ID")
    shared_with: Optional[str] = Field(None, description="被分享者用户ID")
    shared_with_email: Optional[str] = Field(None, description="被分享者邮箱")
    
    access_token: Optional[str] = Field(None, description="访问令牌")
    password: Optional[str] = Field(None, description="访问密码")
    
    permissions: Dict[str, bool] = Field(
        default_factory=lambda: {"view": True, "download": False, "delete": False},
        description="权限设置"
    )
    
    max_downloads: Optional[int] = Field(None, description="最大下载次数")
    download_count: int = Field(0, description="已下载次数")
    
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    is_active: bool = Field(True, description="是否激活")
    
    created_at: Optional[datetime] = Field(None, description="创建时间")
    accessed_at: Optional[datetime] = Field(None, description="最后访问时间")


class StorageQuota(BaseModel):
    """存储配额模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    user_id: Optional[str] = Field(None, description="用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    
    total_quota_bytes: int = Field(..., description="总配额(字节)")
    used_bytes: int = Field(0, description="已使用(字节)")
    file_count: int = Field(0, description="文件数量")
    
    max_file_size: Optional[int] = Field(None, description="最大单文件大小")
    max_file_count: Optional[int] = Field(None, description="最大文件数量")
    
    allowed_extensions: Optional[List[str]] = Field(None, description="允许的文件扩展名")
    blocked_extensions: Optional[List[str]] = Field(None, description="禁止的文件扩展名")
    
    is_active: bool = Field(True, description="是否激活")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


# ==================== Request/Response Models ====================

class FileUploadRequest(BaseModel):
    """文件上传请求"""
    user_id: str
    organization_id: Optional[str] = None
    access_level: FileAccessLevel = FileAccessLevel.PRIVATE
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    auto_delete_after_days: Optional[int] = None
    enable_indexing: bool = Field(True, description="Enable auto-indexing for RAG/vectorization")


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    file_id: str
    file_path: str
    download_url: str
    file_size: int
    content_type: str
    uploaded_at: datetime
    message: str = "File uploaded successfully"


class FileListRequest(BaseModel):
    """文件列表请求"""
    user_id: str
    organization_id: Optional[str] = None
    prefix: Optional[str] = None
    status: Optional[FileStatus] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class FileInfoResponse(BaseModel):
    """文件信息响应"""
    file_id: str
    file_name: str
    file_path: str
    file_size: int
    content_type: str
    status: FileStatus
    access_level: FileAccessLevel
    download_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    uploaded_at: datetime
    updated_at: Optional[datetime] = None


class FileShareRequest(BaseModel):
    """文件分享请求"""
    file_id: str
    shared_by: str
    shared_with: Optional[str] = None
    shared_with_email: Optional[str] = None
    permissions: Dict[str, bool] = Field(
        default_factory=lambda: {"view": True, "download": False, "delete": False}
    )
    password: Optional[str] = None
    expires_hours: int = Field(24, ge=1, le=720)  # 最长30天
    max_downloads: Optional[int] = None


class FileShareResponse(BaseModel):
    """文件分享响应"""
    share_id: str
    share_url: str
    access_token: Optional[str] = None
    expires_at: datetime
    permissions: Dict[str, bool]
    message: str = "File shared successfully"


class StorageStatsResponse(BaseModel):
    """存储统计响应"""
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    total_quota_bytes: int
    used_bytes: int
    available_bytes: int
    usage_percentage: float
    file_count: int
    by_type: Dict[str, Dict[str, Any]]
    by_status: Dict[str, int]


# ==================== Photo Version Models ====================

class PhotoVersionType(str, Enum):
    """照片版本类型"""
    ORIGINAL = "original"
    AI_ENHANCED = "ai_enhanced"
    AI_STYLED = "ai_styled"
    USER_EDITED = "user_edited"
    RESTORED = "restored"


class PhotoVersion(BaseModel):
    """照片版本模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    version_id: str = Field(..., description="版本唯一标识符")
    photo_id: str = Field(..., description="照片ID（关联原始照片）")
    user_id: str = Field(..., description="用户ID")
    
    version_name: str = Field(..., description="版本名称")
    version_type: PhotoVersionType = Field(..., description="版本类型")
    processing_mode: Optional[str] = Field(None, description="AI处理模式")
    
    file_id: str = Field(..., description="关联的文件ID")
    cloud_url: str = Field(..., description="云端URL")
    local_path: Optional[str] = Field(None, description="本地路径（仅相框端）")
    
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    file_size: int = Field(..., description="文件大小")
    
    processing_params: Optional[Dict[str, Any]] = Field(None, description="处理参数")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    is_current: bool = Field(False, description="是否为当前显示版本")
    is_favorite: bool = Field(False, description="是否收藏")
    
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class PhotoWithVersions(BaseModel):
    """带版本的照片模型"""
    model_config = ConfigDict(from_attributes=True)
    
    photo_id: str = Field(..., description="照片ID")
    title: str = Field(..., description="照片标题")
    original_file_id: str = Field(..., description="原始文件ID")
    current_version_id: str = Field(..., description="当前显示版本ID")
    
    versions: List[PhotoVersion] = Field(default_factory=list, description="所有版本")
    version_count: int = Field(0, description="版本数量")
    
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class SavePhotoVersionRequest(BaseModel):
    """保存照片版本请求"""
    photo_id: str = Field(..., description="原始照片ID")
    user_id: str = Field(..., description="用户ID")
    version_name: str = Field(..., description="版本名称")
    version_type: PhotoVersionType = Field(PhotoVersionType.AI_ENHANCED, description="版本类型")
    processing_mode: Optional[str] = Field(None, description="处理模式")
    
    source_url: str = Field(..., description="AI生成的图片URL")
    save_local: bool = Field(False, description="是否保存到本地（相框端）")
    
    processing_params: Optional[Dict[str, Any]] = Field(None, description="处理参数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    set_as_current: bool = Field(False, description="是否设为当前版本")


class SavePhotoVersionResponse(BaseModel):
    """保存照片版本响应"""
    version_id: str
    photo_id: str
    cloud_url: str
    local_path: Optional[str] = None
    version_name: str
    created_at: datetime
    message: str = "Photo version saved successfully"


class SwitchPhotoVersionRequest(BaseModel):
    """切换照片版本请求"""
    photo_id: str
    version_id: str
    user_id: str


class GetPhotoVersionsRequest(BaseModel):
    """获取照片版本列表请求"""
    photo_id: str
    user_id: str
    include_metadata: bool = Field(False, description="是否包含元数据")