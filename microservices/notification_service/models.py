"""
Notification Service Data Models

定义通知服务的数据模型，包括通知、模板、发送记录等
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


# ====================
# 枚举类型定义
# ====================

class NotificationType(str, Enum):
    """通知类型"""
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"
    WEBHOOK = "webhook"


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    CANCELLED = "cancelled"


class NotificationPriority(str, Enum):
    """通知优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TemplateStatus(str, Enum):
    """模板状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class RecipientType(str, Enum):
    """接收者类型"""
    USER = "user"
    EMAIL = "email"
    PHONE = "phone"
    GROUP = "group"
    ROLE = "role"


class PushPlatform(str, Enum):
    """推送平台"""
    WEB = "web"
    IOS = "ios"
    ANDROID = "android"


# ====================
# 核心数据模型
# ====================

class NotificationTemplate(BaseModel):
    """通知模板模型"""
    id: Optional[str] = None
    template_id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = None
    type: NotificationType = Field(..., description="通知类型")
    
    # 模板内容
    subject: Optional[str] = Field(None, description="邮件主题（邮件类型使用）")
    content: str = Field(..., description="模板内容（支持变量替换）")
    html_content: Optional[str] = Field(None, description="HTML内容（邮件类型使用）")
    
    # 配置
    variables: List[str] = Field(default_factory=list, description="模板变量列表")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 状态
    status: TemplateStatus = TemplateStatus.ACTIVE
    version: int = Field(default=1, description="模板版本")
    
    # 时间戳
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Notification(BaseModel):
    """通知模型"""
    id: Optional[str] = None
    notification_id: str = Field(..., description="通知ID")
    
    # 基本信息
    type: NotificationType = Field(..., description="通知类型")
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # 接收者
    recipient_type: RecipientType = RecipientType.USER
    recipient_id: Optional[str] = Field(None, description="接收者ID（用户/组ID）")
    recipient_email: Optional[EmailStr] = Field(None, description="接收者邮箱")
    recipient_phone: Optional[str] = Field(None, description="接收者电话")
    
    # 内容
    template_id: Optional[str] = Field(None, description="使用的模板ID")
    subject: Optional[str] = Field(None, description="通知主题")
    content: str = Field(..., description="通知内容")
    html_content: Optional[str] = Field(None, description="HTML内容")
    variables: Dict[str, Any] = Field(default_factory=dict, description="模板变量值")
    
    # 发送配置
    scheduled_at: Optional[datetime] = Field(None, description="计划发送时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    
    # 状态
    status: NotificationStatus = NotificationStatus.PENDING
    error_message: Optional[str] = None
    
    # 追踪
    provider: Optional[str] = Field(None, description="发送提供商")
    provider_message_id: Optional[str] = Field(None, description="提供商消息ID")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    # 时间戳
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None


class InAppNotification(BaseModel):
    """应用内通知模型"""
    id: Optional[str] = None
    notification_id: str = Field(..., description="通知ID")
    user_id: str = Field(..., description="用户ID")
    
    # 内容
    title: str = Field(..., description="通知标题")
    message: str = Field(..., description="通知消息")
    icon: Optional[str] = Field(None, description="图标")
    image_url: Optional[str] = Field(None, description="图片URL")
    action_url: Optional[str] = Field(None, description="点击动作URL")
    
    # 分类
    category: Optional[str] = Field(None, description="通知分类")
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # 状态
    is_read: bool = Field(default=False)
    is_archived: bool = Field(default=False)
    
    # 时间戳
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None


class NotificationBatch(BaseModel):
    """批量通知模型"""
    id: Optional[str] = None
    batch_id: str = Field(..., description="批次ID")
    name: Optional[str] = Field(None, description="批次名称")
    
    # 配置
    template_id: str = Field(..., description="模板ID")
    type: NotificationType = Field(..., description="通知类型")
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # 接收者
    recipients: List[Dict[str, Any]] = Field(..., description="接收者列表")
    total_recipients: int = Field(..., description="总接收者数")
    
    # 状态统计
    sent_count: int = Field(default=0)
    delivered_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    
    # 时间
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class EmailProvider(BaseModel):
    """邮件提供商配置"""
    provider_name: str = Field(..., description="提供商名称")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_endpoint: Optional[str] = Field(None, description="API端点")
    from_email: str = Field(..., description="发件人邮箱")
    from_name: Optional[str] = Field(None, description="发件人名称")
    reply_to: Optional[str] = Field(None, description="回复邮箱")
    is_active: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PushSubscription(BaseModel):
    """推送订阅模型"""
    id: Optional[int] = None
    user_id: str = Field(..., description="用户ID")
    device_token: str = Field(..., description="设备令牌/订阅令牌")
    platform: PushPlatform = Field(..., description="平台类型")
    endpoint: Optional[str] = Field(None, description="Web Push端点")
    auth_key: Optional[str] = Field(None, description="Web Push认证密钥")
    p256dh_key: Optional[str] = Field(None, description="Web Push P256DH密钥")
    device_name: Optional[str] = Field(None, description="设备名称")
    device_model: Optional[str] = Field(None, description="设备型号")
    app_version: Optional[str] = Field(None, description="应用版本")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


# ====================
# 请求/响应模型
# ====================

class SendNotificationRequest(BaseModel):
    """发送通知请求"""
    type: NotificationType
    recipient_id: Optional[str] = None
    recipient_email: Optional[EmailStr] = None
    recipient_phone: Optional[str] = None
    template_id: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    html_content: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    priority: NotificationPriority = NotificationPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class SendBatchRequest(BaseModel):
    """批量发送请求"""
    name: Optional[str] = None
    template_id: str
    type: NotificationType
    recipients: List[Dict[str, Any]]
    priority: NotificationPriority = NotificationPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateTemplateRequest(BaseModel):
    """创建模板请求"""
    name: str
    description: Optional[str] = None
    type: NotificationType
    subject: Optional[str] = None
    content: str
    html_content: Optional[str] = None
    variables: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateTemplateRequest(BaseModel):
    """更新模板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    html_content: Optional[str] = None
    variables: Optional[List[str]] = None
    status: Optional[TemplateStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class RegisterPushSubscriptionRequest(BaseModel):
    """注册推送订阅请求"""
    user_id: str
    device_token: str
    platform: PushPlatform
    endpoint: Optional[str] = None
    auth_key: Optional[str] = None
    p256dh_key: Optional[str] = None
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    app_version: Optional[str] = None


class NotificationResponse(BaseModel):
    """通知响应"""
    notification: Notification
    message: str = Field(default="Notification processed")
    success: bool = Field(default=True)


class TemplateResponse(BaseModel):
    """模板响应"""
    template: NotificationTemplate
    message: str = Field(default="Template processed")


class BatchResponse(BaseModel):
    """批量发送响应"""
    batch: NotificationBatch
    message: str = Field(default="Batch created")


class NotificationStatsResponse(BaseModel):
    """通知统计响应"""
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_pending: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)
    period: str = Field(default="all_time")


# ====================
# 系统模型
# ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    port: int
    version: str


class ServiceInfo(BaseModel):
    """服务信息"""
    service: str
    version: str
    description: str
    capabilities: Dict[str, Any]
    endpoints: Dict[str, str]