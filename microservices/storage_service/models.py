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


# ==================== Album Management Models ====================

class Album(BaseModel):
    """相册模型 - 专注存储和媒体管理"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    album_id: str = Field(..., description="相册唯一标识符")
    name: str = Field(..., description="相册名称")
    description: Optional[str] = Field(None, description="相册描述")
    user_id: str = Field(..., description="创建者用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    
    cover_photo_id: Optional[str] = Field(None, description="封面照片ID")
    photo_count: int = Field(0, description="照片数量")
    
    # 智能相框特性
    auto_sync: bool = Field(True, description="自动同步到相框")
    sync_frames: List[str] = Field(default_factory=list, description="同步到的相框ID列表")
    
    # 共享状态 (实际权限管理由organization_service处理)
    is_family_shared: bool = Field(False, description="是否启用家庭共享")
    sharing_resource_id: Optional[str] = Field(None, description="organization_service中的共享资源ID")
    
    # 元数据和AI标记
    tags: List[str] = Field(default_factory=list, description="标签")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    ai_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="AI生成的元数据")
    
    # 时间戳
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_synced_at: Optional[datetime] = Field(None, description="最后同步时间")


# FamilyMember model removed - handled by organization_service family_sharing


class AlbumPhoto(BaseModel):
    """相册照片关联模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    album_id: str = Field(..., description="相册ID")
    photo_id: str = Field(..., description="照片ID（关联StoredFile的file_id）")
    
    added_by: str = Field(..., description="添加者用户ID")
    added_at: Optional[datetime] = Field(None, description="添加时间")
    
    # 相册内属性
    is_featured: bool = Field(False, description="是否精选照片")
    display_order: int = Field(0, description="显示顺序")
    
    # AI智能标记
    ai_tags: List[str] = Field(default_factory=list, description="AI生成的标签")
    ai_objects: List[str] = Field(default_factory=list, description="AI识别的物体")
    ai_scenes: List[str] = Field(default_factory=list, description="AI识别的场景")
    face_detection_results: Optional[Dict[str, Any]] = Field(None, description="人脸检测结果")
    
    # 同步状态
    sync_status: Dict[str, Any] = Field(default_factory=dict, description="各设备的同步状态")


class AlbumSyncStatus(BaseModel):
    """相册同步状态模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    album_id: str = Field(..., description="相册ID")
    frame_id: str = Field(..., description="相框设备ID")
    
    last_sync_timestamp: Optional[datetime] = Field(None, description="最后同步时间")
    sync_version: int = Field(0, description="同步版本号")
    
    # 同步统计
    total_photos: int = Field(0, description="总照片数")
    synced_photos: int = Field(0, description="已同步照片数")
    pending_photos: int = Field(0, description="待同步照片数")
    failed_photos: int = Field(0, description="同步失败照片数")
    
    # 状态
    sync_status: str = Field("pending", description="同步状态: pending/syncing/completed/failed")
    last_error: Optional[str] = Field(None, description="最后错误信息")
    
    created_at: Optional[datetime] = Field(None, description="创建时间")
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


# ==================== Album Request/Response Models ====================

class CreateAlbumRequest(BaseModel):
    """创建相册请求"""
    name: str = Field(..., description="相册名称")
    description: Optional[str] = Field(None, description="相册描述")
    user_id: str = Field(..., description="创建者用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    cover_photo_id: Optional[str] = Field(None, description="封面照片ID")
    auto_sync: bool = Field(True, description="自动同步到相框")
    enable_family_sharing: bool = Field(False, description="是否启用家庭共享")
    tags: List[str] = Field(default_factory=list, description="标签")


class UpdateAlbumRequest(BaseModel):
    """更新相册请求"""
    name: Optional[str] = Field(None, description="相册名称")
    description: Optional[str] = Field(None, description="相册描述")
    cover_photo_id: Optional[str] = Field(None, description="封面照片ID")
    auto_sync: Optional[bool] = Field(None, description="自动同步到相框")
    enable_family_sharing: Optional[bool] = Field(None, description="是否启用家庭共享")
    tags: Optional[List[str]] = Field(None, description="标签")


class AddPhotosToAlbumRequest(BaseModel):
    """添加照片到相册请求"""
    photo_ids: List[str] = Field(..., description="照片ID列表")
    added_by: str = Field(..., description="添加者用户ID")
    is_featured: bool = Field(False, description="是否设为精选")


# AddFamilyMemberRequest removed - family sharing handled by organization_service

class ShareAlbumRequest(BaseModel):
    """相册家庭共享请求"""
    album_id: str = Field(..., description="相册ID")
    shared_with_members: Optional[List[str]] = Field(None, description="共享给特定成员")
    share_with_all_family: bool = Field(True, description="共享给所有家庭成员")
    default_permission: str = Field("read_write", description="默认权限级别")
    custom_permissions: Optional[Dict[str, str]] = Field(None, description="自定义权限")


class AlbumResponse(BaseModel):
    """相册响应"""
    album_id: str
    name: str
    description: Optional[str] = None
    user_id: str
    cover_photo_id: Optional[str] = None
    photo_count: int
    auto_sync: bool
    is_family_shared: bool
    sharing_resource_id: Optional[str] = None
    sync_frames: List[str]
    tags: List[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    
    # Family sharing info (populated from organization_service if needed)
    family_sharing_info: Optional[Dict[str, Any]] = None


class AlbumListResponse(BaseModel):
    """相册列表响应"""
    albums: List[AlbumResponse]
    count: int
    limit: int
    offset: int


class AlbumPhotosResponse(BaseModel):
    """相册照片列表响应"""
    album_id: str
    photos: List[Dict[str, Any]]  # 包含照片信息和相册内属性
    count: int
    limit: int
    offset: int


class AlbumSyncResponse(BaseModel):
    """相册同步响应"""
    album_id: str
    frame_id: str
    sync_status: str
    last_sync_timestamp: Optional[datetime]
    sync_version: int
    progress: Dict[str, int]  # total, synced, pending, failed
    message: str = "Sync status retrieved successfully"


# ==================== Gallery & Slideshow Features ====================

class PlaylistType(str, Enum):
    """播放列表类型"""
    MANUAL = "manual"  # Manually curated photos
    SMART = "smart"  # AI-powered smart selection
    ALBUM = "album"  # Based on existing album
    RECENT = "recent"  # Recent uploads
    FAVORITES = "favorites"  # Favorited photos
    RANDOM = "random"  # Random selection


class RotationScheduleType(str, Enum):
    """轮播计划类型"""
    SEQUENTIAL = "sequential"  # Show photos in order
    RANDOM = "random"  # Random order
    SMART = "smart"  # AI-powered smart selection
    SHUFFLE = "shuffle"  # Shuffle once, then repeat


class SlideshowPlaylist(BaseModel):
    """幻灯片播放列表模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    playlist_id: str = Field(..., description="播放列表唯一标识符")
    name: str = Field(..., description="播放列表名称")
    description: Optional[str] = Field(None, description="描述")
    user_id: str = Field(..., description="创建者用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    
    # Playlist configuration
    playlist_type: PlaylistType = Field(PlaylistType.MANUAL, description="播放列表类型")
    photo_ids: List[str] = Field(default_factory=list, description="照片ID列表")
    album_ids: List[str] = Field(default_factory=list, description="关联的相册ID")
    
    # Smart selection criteria (for SMART type)
    smart_criteria: Optional[Dict[str, Any]] = Field(None, description="智能选择条件")
    
    # Display settings
    rotation_type: RotationScheduleType = Field(RotationScheduleType.SEQUENTIAL, description="轮播类型")
    transition_duration: int = Field(5, description="每张照片显示时长(秒)")
    transition_effect: str = Field("fade", description="过渡效果")
    
    # Active frames
    active_frames: List[str] = Field(default_factory=list, description="激活的设备ID列表")
    
    # Metadata
    photo_count: int = Field(0, description="照片数量")
    is_active: bool = Field(True, description="是否激活")
    last_played_at: Optional[datetime] = Field(None, description="最后播放时间")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class PhotoRotationSchedule(BaseModel):
    """照片轮播计划模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    schedule_id: str = Field(..., description="计划唯一标识符")
    playlist_id: str = Field(..., description="播放列表ID")
    frame_id: str = Field(..., description="设备ID")
    user_id: str = Field(..., description="用户ID")
    
    # Schedule settings
    is_active: bool = Field(True, description="是否激活")
    start_time: Optional[str] = Field(None, description="每日开始时间 (HH:MM)")
    end_time: Optional[str] = Field(None, description="每日结束时间 (HH:MM)")
    days_of_week: List[int] = Field(default_factory=lambda: list(range(7)), description="星期几 (0-6)")
    
    # Rotation settings
    interval_seconds: int = Field(5, description="轮播间隔(秒)")
    shuffle: bool = Field(False, description="是否随机播放")
    loop: bool = Field(True, description="是否循环播放")
    
    # Current state
    current_photo_index: int = Field(0, description="当前照片索引")
    last_rotation_at: Optional[datetime] = Field(None, description="最后轮播时间")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class PhotoMetadata(BaseModel):
    """照片元数据模型 - 增强版"""
    model_config = ConfigDict(from_attributes=True)
    
    file_id: str = Field(..., description="文件ID")
    
    # Basic metadata
    is_favorite: bool = Field(False, description="是否收藏")
    rating: Optional[int] = Field(None, ge=0, le=5, description="评分 (0-5)")
    tags: List[str] = Field(default_factory=list, description="标签")
    
    # Date information
    taken_at: Optional[datetime] = Field(None, description="拍摄时间")
    location_name: Optional[str] = Field(None, description="地点名称")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")
    
    # AI-generated metadata
    ai_tags: List[str] = Field(default_factory=list, description="AI标签")
    ai_objects: List[str] = Field(default_factory=list, description="AI识别物体")
    ai_scenes: List[str] = Field(default_factory=list, description="AI识别场景")
    ai_emotions: List[str] = Field(default_factory=list, description="AI识别情感")
    ai_colors: List[str] = Field(default_factory=list, description="主色调")
    has_faces: bool = Field(False, description="是否包含人脸")
    face_count: int = Field(0, description="人脸数量")
    
    # Quality metrics
    quality_score: Optional[float] = Field(None, description="照片质量分数")
    sharpness_score: Optional[float] = Field(None, description="清晰度分数")
    exposure_score: Optional[float] = Field(None, description="曝光度分数")
    
    # Usage statistics
    view_count: int = Field(0, description="查看次数")
    display_count: int = Field(0, description="展示次数")
    last_displayed_at: Optional[datetime] = Field(None, description="最后展示时间")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class CacheStatus(str, Enum):
    """缓存状态"""
    PENDING = "pending"  # Waiting to be cached
    CACHING = "caching"  # Currently downloading/caching
    CACHED = "cached"  # Successfully cached
    FAILED = "failed"  # Cache failed
    EXPIRED = "expired"  # Cache expired


class PhotoCache(BaseModel):
    """照片缓存模型 - For preloading and offline access"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = None
    cache_id: str = Field(..., description="缓存唯一标识符")
    photo_id: str = Field(..., description="照片ID (file_id)")
    frame_id: str = Field(..., description="设备ID")
    user_id: str = Field(..., description="用户ID")
    
    # Cache info
    original_url: str = Field(..., description="原始URL")
    cached_url: Optional[str] = Field(None, description="缓存URL/本地路径")
    cache_key: str = Field(..., description="缓存键")
    
    # Cache status
    status: CacheStatus = Field(CacheStatus.PENDING, description="缓存状态")
    priority: str = Field("normal", description="优先级: high, normal, low")
    
    # File info
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    content_type: Optional[str] = Field(None, description="内容类型")
    
    # Cache metrics
    hit_count: int = Field(0, description="缓存命中次数")
    last_accessed_at: Optional[datetime] = Field(None, description="最后访问时间")
    
    # Expiry
    cached_at: Optional[datetime] = Field(None, description="缓存时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    # Error info
    error_message: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(0, description="重试次数")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class SmartSelectionCriteria(BaseModel):
    """智能照片选择条件"""
    
    # Date filters
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    date_range_days: Optional[int] = Field(None, description="最近N天")
    
    # Album filters
    album_ids: Optional[List[str]] = Field(None, description="限定相册")
    exclude_album_ids: Optional[List[str]] = Field(None, description="排除相册")
    
    # Quality filters
    min_quality_score: Optional[float] = Field(None, description="最低质量分数")
    favorites_only: bool = Field(False, description="仅收藏")
    min_rating: Optional[int] = Field(None, description="最低评分")
    
    # AI filters
    include_tags: Optional[List[str]] = Field(None, description="包含标签")
    exclude_tags: Optional[List[str]] = Field(None, description="排除标签")
    has_faces: Optional[bool] = Field(None, description="是否包含人脸")
    include_emotions: Optional[List[str]] = Field(None, description="包含情感")
    
    # Display diversity
    max_photos: int = Field(50, description="最大照片数")
    diversity_weight: float = Field(0.5, description="多样性权重 0-1")
    recency_weight: float = Field(0.3, description="新鲜度权重 0-1")
    quality_weight: float = Field(0.2, description="质量权重 0-1")


# ==================== Request/Response Models for Gallery ====================

class CreatePlaylistRequest(BaseModel):
    """创建播放列表请求"""
    name: str = Field(..., description="播放列表名称")
    description: Optional[str] = None
    user_id: str
    playlist_type: PlaylistType = PlaylistType.MANUAL
    photo_ids: List[str] = Field(default_factory=list)
    album_ids: List[str] = Field(default_factory=list)
    smart_criteria: Optional[SmartSelectionCriteria] = None
    rotation_type: RotationScheduleType = RotationScheduleType.SEQUENTIAL
    transition_duration: int = 5


class UpdatePlaylistRequest(BaseModel):
    """更新播放列表请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    photo_ids: Optional[List[str]] = None
    album_ids: Optional[List[str]] = None
    smart_criteria: Optional[SmartSelectionCriteria] = None
    rotation_type: Optional[RotationScheduleType] = None
    transition_duration: Optional[int] = None
    is_active: Optional[bool] = None


class CreateRotationScheduleRequest(BaseModel):
    """创建轮播计划请求"""
    playlist_id: str
    frame_id: str
    user_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    days_of_week: List[int] = Field(default_factory=lambda: list(range(7)))
    interval_seconds: int = 5
    shuffle: bool = False


class UpdatePhotoMetadataRequest(BaseModel):
    """更新照片元数据请求"""
    file_id: str
    is_favorite: Optional[bool] = None
    rating: Optional[int] = Field(None, ge=0, le=5)
    tags: Optional[List[str]] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PreloadImagesRequest(BaseModel):
    """预加载图片请求"""
    frame_id: str
    user_id: str
    photo_ids: List[str] = Field(..., description="要预加载的照片ID列表")
    priority: str = Field("normal", description="优先级")


class RandomPhotosRequest(BaseModel):
    """随机照片请求"""
    user_id: str
    count: int = Field(10, ge=1, le=100, description="照片数量")
    criteria: Optional[SmartSelectionCriteria] = None


# ==================== Response Models ====================

class PlaylistResponse(BaseModel):
    """播放列表响应"""
    playlist_id: str
    name: str
    description: Optional[str]
    playlist_type: PlaylistType
    photo_count: int
    rotation_type: RotationScheduleType
    transition_duration: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class PlaylistListResponse(BaseModel):
    """播放列表列表响应"""
    playlists: List[PlaylistResponse]
    total: int


class PlaylistPhotosResponse(BaseModel):
    """播放列表照片响应"""
    playlist_id: str
    photos: List[Dict[str, Any]]  # Full photo info including URLs
    total: int


class PhotoCacheStatsResponse(BaseModel):
    """照片缓存统计响应"""
    frame_id: str
    total_cached: int
    total_size_bytes: int
    cache_hit_rate: float
    pending_count: int
    failed_count: int
    oldest_cache: Optional[datetime]
    newest_cache: Optional[datetime]


class RandomPhotosResponse(BaseModel):
    """随机照片响应"""
    photos: List[Dict[str, Any]]
    count: int
    criteria_applied: Optional[SmartSelectionCriteria]