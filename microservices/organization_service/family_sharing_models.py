"""
Family Sharing Models

家庭共享功能数据模型
支持订阅、设备、存储、钱包等资源的家庭共享
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============ Enums ============

class SharingResourceType(str, Enum):
    """共享资源类型"""
    SUBSCRIPTION = "subscription"  # 订阅共享（如家庭订阅套餐）
    DEVICE = "device"  # 设备共享（智能家居设备）
    STORAGE = "storage"  # 存储共享（云存储空间）
    WALLET = "wallet"  # 钱包共享（家庭钱包、零花钱）
    MEDIA_LIBRARY = "media_library"  # 媒体库共享（照片、视频）
    CALENDAR = "calendar"  # 家庭日历
    SHOPPING_LIST = "shopping_list"  # 购物清单
    LOCATION = "location"  # 位置共享


class SharingPermissionLevel(str, Enum):
    """共享权限级别"""
    OWNER = "owner"  # 所有者（完全控制）
    ADMIN = "admin"  # 管理员（可以管理和使用）
    FULL_ACCESS = "full_access"  # 完全访问（可以使用和修改）
    READ_WRITE = "read_write"  # 读写访问
    READ_ONLY = "read_only"  # 只读访问
    LIMITED = "limited"  # 受限访问（有配额/时间限制）
    VIEW_ONLY = "view_only"  # 仅查看


class SharingStatus(str, Enum):
    """共享状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class QuotaType(str, Enum):
    """配额类型"""
    UNLIMITED = "unlimited"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    TOTAL = "total"


# ============ Request Models ============

class CreateSharingRequest(BaseModel):
    """创建共享请求"""
    resource_type: SharingResourceType = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID（如订阅ID、设备ID等）")
    resource_name: Optional[str] = Field(None, description="资源名称")
    shared_with_members: Optional[List[str]] = Field(default_factory=list, description="共享给哪些成员（user_id列表）")
    share_with_all_members: bool = Field(False, description="是否共享给所有家庭成员")
    default_permission: SharingPermissionLevel = Field(
        SharingPermissionLevel.READ_WRITE,
        description="默认权限级别"
    )
    custom_permissions: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="自定义成员权限 {user_id: permission_level}"
    )
    quota_settings: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="配额设置"
    )
    restrictions: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="限制条件（如时间限制、使用限制等）"
    )
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")


class UpdateSharingRequest(BaseModel):
    """更新共享请求"""
    shared_with_members: Optional[List[str]] = None
    share_with_all_members: Optional[bool] = None
    default_permission: Optional[SharingPermissionLevel] = None
    custom_permissions: Optional[Dict[str, str]] = None
    quota_settings: Optional[Dict[str, Any]] = None
    restrictions: Optional[Dict[str, Any]] = None
    status: Optional[SharingStatus] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateMemberSharingPermissionRequest(BaseModel):
    """更新成员共享权限请求"""
    user_id: str = Field(..., description="用户ID")
    permission_level: SharingPermissionLevel = Field(..., description="权限级别")
    quota_override: Optional[Dict[str, Any]] = Field(None, description="个人配额覆盖")
    restrictions_override: Optional[Dict[str, Any]] = Field(None, description="个人限制覆盖")


class GetMemberSharedResourcesRequest(BaseModel):
    """获取成员共享资源请求"""
    user_id: str = Field(..., description="用户ID")
    resource_type: Optional[SharingResourceType] = Field(None, description="资源类型过滤")
    status: Optional[SharingStatus] = Field(None, description="状态过滤")
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


# ============ Response Models ============

class SharingResourceResponse(BaseModel):
    """共享资源响应"""
    sharing_id: str
    organization_id: str
    resource_type: SharingResourceType
    resource_id: str
    resource_name: Optional[str] = None
    created_by: str
    share_with_all_members: bool
    default_permission: SharingPermissionLevel
    status: SharingStatus
    total_members_shared: int = 0
    quota_settings: Dict[str, Any] = Field(default_factory=dict)
    restrictions: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MemberSharingPermissionResponse(BaseModel):
    """成员共享权限响应"""
    user_id: str
    sharing_id: str
    resource_type: SharingResourceType
    resource_id: str
    resource_name: Optional[str] = None
    permission_level: SharingPermissionLevel
    quota_allocated: Optional[Dict[str, Any]] = None
    quota_used: Optional[Dict[str, Any]] = None
    restrictions: Optional[Dict[str, Any]] = None
    is_active: bool = True
    granted_at: datetime
    last_accessed_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SharedResourceDetailResponse(BaseModel):
    """共享资源详情响应（包含成员列表）"""
    sharing: SharingResourceResponse
    member_permissions: List[MemberSharingPermissionResponse] = Field(default_factory=list)
    usage_stats: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MemberSharedResourcesResponse(BaseModel):
    """成员共享资源列表响应"""
    user_id: str
    organization_id: str
    shared_resources: List[MemberSharingPermissionResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class SharingUsageStatsResponse(BaseModel):
    """共享使用统计响应"""
    sharing_id: str
    resource_type: SharingResourceType
    resource_id: str
    total_members: int
    active_members: int
    total_usage: Dict[str, Any] = Field(default_factory=dict)  # 总使用量
    member_usage: List[Dict[str, Any]] = Field(default_factory=list)  # 每个成员的使用量
    quota_utilization: Optional[float] = None  # 配额利用率（0-100）
    period_start: datetime
    period_end: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============ Specific Sharing Types ============

class SubscriptionSharingSettings(BaseModel):
    """订阅共享设置"""
    subscription_id: str
    plan_name: str
    max_seats: int = Field(..., description="最大席位数")
    current_seats_used: int = 0
    features_included: List[str] = Field(default_factory=list)
    per_user_quota: Optional[Dict[str, Any]] = None


class DeviceSharingSettings(BaseModel):
    """设备共享设置"""
    device_id: str
    device_name: str
    device_type: str  # smart_speaker, camera, thermostat, etc.
    location: Optional[str] = None
    allow_remote_control: bool = True
    time_restrictions: Optional[List[Dict[str, str]]] = None  # [{day: "monday", start: "18:00", end: "22:00"}]


class StorageSharingSettings(BaseModel):
    """存储共享设置"""
    storage_id: str
    total_quota_gb: float
    allocated_quotas: Dict[str, float] = Field(default_factory=dict)  # {user_id: quota_gb}
    shared_folders: List[str] = Field(default_factory=list)
    allow_upload: bool = True
    allow_delete: bool = False
    file_type_restrictions: Optional[List[str]] = None


class WalletSharingSettings(BaseModel):
    """钱包共享设置"""
    wallet_id: str
    wallet_name: str
    total_balance: Decimal
    spending_limits: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="消费限额 {user_id: {daily: 100, monthly: 500}}"
    )
    require_approval_above: Optional[Decimal] = None
    allowed_categories: Optional[List[str]] = None

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class MediaLibrarySharingSettings(BaseModel):
    """媒体库共享设置"""
    library_id: str
    library_name: str
    library_type: str  # photos, videos, music
    total_items: int = 0
    allow_add: bool = True
    allow_edit: bool = False
    allow_delete: bool = False
    shared_albums: List[str] = Field(default_factory=list)


# ============ Composite Models for Different Resource Types ============

class CreateSubscriptionSharingRequest(CreateSharingRequest):
    """创建订阅共享请求"""
    subscription_settings: SubscriptionSharingSettings

    def __init__(self, **data):
        data['resource_type'] = SharingResourceType.SUBSCRIPTION
        super().__init__(**data)


class CreateDeviceSharingRequest(CreateSharingRequest):
    """创建设备共享请求"""
    device_settings: DeviceSharingSettings

    def __init__(self, **data):
        data['resource_type'] = SharingResourceType.DEVICE
        super().__init__(**data)


class CreateStorageSharingRequest(CreateSharingRequest):
    """创建存储共享请求"""
    storage_settings: StorageSharingSettings

    def __init__(self, **data):
        data['resource_type'] = SharingResourceType.STORAGE
        super().__init__(**data)


class CreateWalletSharingRequest(CreateSharingRequest):
    """创建钱包共享请求"""
    wallet_settings: WalletSharingSettings

    def __init__(self, **data):
        data['resource_type'] = SharingResourceType.WALLET
        super().__init__(**data)


class CreateMediaLibrarySharingRequest(CreateSharingRequest):
    """创建媒体库共享请求"""
    media_library_settings: MediaLibrarySharingSettings

    def __init__(self, **data):
        data['resource_type'] = SharingResourceType.MEDIA_LIBRARY
        super().__init__(**data)
