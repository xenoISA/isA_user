"""
OTA Service - Data Models

OTA更新服务数据模型，包含固件管理、更新任务、部署策略等
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class UpdateType(str, Enum):
    """更新类型"""
    FIRMWARE = "firmware"  # 固件更新 (FOTA)
    SOFTWARE = "software"  # 软件更新 (SOTA) 
    APPLICATION = "application"  # 应用更新 (AOTA)
    CONFIG = "config"  # 配置更新 (COTA)
    BOOTLOADER = "bootloader"  # 引导程序更新
    SECURITY_PATCH = "security_patch"  # 安全补丁


class UpdateStatus(str, Enum):
    """更新状态"""
    CREATED = "created"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    REBOOTING = "rebooting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


class DeploymentStrategy(str, Enum):
    """部署策略"""
    IMMEDIATE = "immediate"  # 立即部署
    SCHEDULED = "scheduled"  # 定时部署
    STAGED = "staged"  # 分阶段部署
    CANARY = "canary"  # 金丝雀部署
    BLUE_GREEN = "blue_green"  # 蓝绿部署


class Priority(str, Enum):
    """优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class RollbackTrigger(str, Enum):
    """回滚触发条件"""
    MANUAL = "manual"
    FAILURE_RATE = "failure_rate"
    HEALTH_CHECK = "health_check"
    TIMEOUT = "timeout"
    ERROR_THRESHOLD = "error_threshold"


# ==================
# Request Models
# ==================

class FirmwareUploadRequest(BaseModel):
    """固件上传请求"""
    name: str = Field(..., min_length=1, max_length=200)
    version: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    device_model: str = Field(..., min_length=1, max_length=100)
    manufacturer: str = Field(..., min_length=1, max_length=100)
    min_hardware_version: Optional[str] = Field(None, max_length=50)
    max_hardware_version: Optional[str] = Field(None, max_length=50)
    file_size: int = Field(..., gt=0)
    checksum_md5: str = Field(..., min_length=32, max_length=32)
    checksum_sha256: str = Field(..., min_length=64, max_length=64)
    tags: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}
    is_beta: bool = False
    is_security_update: bool = False
    changelog: Optional[str] = Field(None, max_length=5000)


class UpdateCampaignRequest(BaseModel):
    """更新活动请求"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    firmware_id: str
    target_devices: Optional[List[str]] = []  # 目标设备ID列表
    target_groups: Optional[List[str]] = []  # 目标设备组ID列表
    target_filters: Optional[Dict[str, Any]] = {}  # 设备筛选条件
    deployment_strategy: DeploymentStrategy = DeploymentStrategy.STAGED
    priority: Priority = Priority.NORMAL
    
    # 部署配置
    rollout_percentage: int = Field(100, ge=1, le=100)  # 部署百分比
    max_concurrent_updates: int = Field(10, ge=1, le=1000)  # 最大并发更新数
    batch_size: int = Field(50, ge=1, le=500)  # 批次大小
    
    # 时间配置
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    timeout_minutes: int = Field(60, ge=5, le=1440)  # 超时时间（分钟）
    
    # 回滚配置
    auto_rollback: bool = True
    failure_threshold_percent: int = Field(20, ge=1, le=100)  # 失败率阈值
    rollback_triggers: List[RollbackTrigger] = [RollbackTrigger.FAILURE_RATE]
    
    # 通知配置
    notify_on_start: bool = True
    notify_on_complete: bool = True
    notify_on_failure: bool = True
    notification_channels: Optional[List[str]] = []


class DeviceUpdateRequest(BaseModel):
    """设备更新请求

    Note: device_id is in the URL path, not required in request body
    """
    firmware_id: str
    priority: Priority = Priority.NORMAL
    force_update: bool = False  # 强制更新，跳过版本检查
    pre_update_commands: Optional[List[str]] = []  # 更新前命令
    post_update_commands: Optional[List[str]] = []  # 更新后命令
    maintenance_window: Optional[Dict[str, Any]] = None  # 维护窗口
    max_retries: int = Field(3, ge=0, le=10)
    timeout_minutes: int = Field(60, ge=5, le=1440)


class UpdateApprovalRequest(BaseModel):
    """更新审批请求"""
    campaign_id: str
    approved: bool
    approval_comment: Optional[str] = Field(None, max_length=500)
    conditions: Optional[Dict[str, Any]] = {}  # 审批条件


# ==================
# Response Models
# ==================

class FirmwareResponse(BaseModel):
    """固件响应"""
    firmware_id: str
    name: str
    version: str
    description: Optional[str]
    device_model: str
    manufacturer: str
    min_hardware_version: Optional[str]
    max_hardware_version: Optional[str]
    file_size: int
    file_url: str
    checksum_md5: str
    checksum_sha256: str
    tags: List[str]
    metadata: Dict[str, Any]
    is_beta: bool
    is_security_update: bool
    changelog: Optional[str]
    download_count: int = 0
    success_rate: float = 0.0
    created_at: datetime
    updated_at: datetime
    created_by: str


class UpdateCampaignResponse(BaseModel):
    """更新活动响应"""
    campaign_id: str
    name: str
    description: Optional[str]
    firmware: FirmwareResponse
    status: UpdateStatus
    deployment_strategy: DeploymentStrategy
    priority: Priority
    
    # 目标设备
    target_device_count: int
    targeted_devices: List[str]
    targeted_groups: List[str]
    
    # 部署配置
    rollout_percentage: int
    max_concurrent_updates: int
    batch_size: int
    
    # 进度统计
    total_devices: int
    pending_devices: int
    in_progress_devices: int
    completed_devices: int
    failed_devices: int
    cancelled_devices: int
    
    # 时间信息
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    timeout_minutes: int
    
    # 回滚配置
    auto_rollback: bool
    failure_threshold_percent: int
    rollback_triggers: List[RollbackTrigger]
    
    # 审批状态
    requires_approval: bool = False
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approval_comment: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    created_by: str


class DeviceUpdateResponse(BaseModel):
    """设备更新响应"""
    update_id: str
    device_id: str
    campaign_id: Optional[str]
    firmware: FirmwareResponse
    status: UpdateStatus
    priority: Priority
    
    # 进度信息
    progress_percentage: float = Field(0.0, ge=0, le=100)
    current_phase: Optional[str] = None
    
    # 版本信息
    from_version: Optional[str] = None
    to_version: str
    
    # 时间信息
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    timeout_at: Optional[datetime]
    
    # 错误信息
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # 网络信息
    download_size: Optional[int] = None
    download_progress: float = Field(0.0, ge=0, le=100)
    download_speed: Optional[float] = None  # bytes/second
    
    # 验证信息
    signature_verified: Optional[bool] = None
    checksum_verified: Optional[bool] = None
    
    created_at: datetime
    updated_at: datetime


class UpdateStatsResponse(BaseModel):
    """更新统计响应"""
    total_campaigns: int
    active_campaigns: int
    completed_campaigns: int
    failed_campaigns: int
    
    total_updates: int
    pending_updates: int
    in_progress_updates: int
    completed_updates: int
    failed_updates: int
    
    success_rate: float
    avg_update_time: float  # minutes
    total_data_transferred: int  # bytes
    
    # 最近24小时统计
    last_24h_updates: int
    last_24h_failures: int
    last_24h_data_transferred: int
    
    # 设备类型分布
    updates_by_device_type: Dict[str, int]
    updates_by_firmware_version: Dict[str, int]


class UpdateHistoryResponse(BaseModel):
    """更新历史响应"""
    device_id: str
    updates: List[DeviceUpdateResponse]
    total_updates: int
    successful_updates: int
    failed_updates: int
    avg_success_rate: float
    last_update: Optional[datetime]


class RollbackResponse(BaseModel):
    """回滚响应"""
    rollback_id: str
    campaign_id: str
    device_id: Optional[str]  # None表示整个活动回滚
    trigger: RollbackTrigger
    reason: str
    from_version: str
    to_version: str
    status: UpdateStatus
    started_at: datetime
    completed_at: Optional[datetime]
    success: bool
    error_message: Optional[str] = None


class UpdateHealthResponse(BaseModel):
    """更新健康检查响应"""
    service_status: str
    active_campaigns: int
    active_updates: int
    storage_usage: Dict[str, Any]  # 存储使用情况
    network_status: Dict[str, Any]  # 网络状态
    last_successful_update: Optional[datetime]
    error_rate: float
    avg_response_time: float