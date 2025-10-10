"""
Audit Service Data Models

定义审计服务的数据模型，包括事件类型、审计日志、合规报告等
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


# ====================
# 枚举类型定义
# ====================

class EventType(str, Enum):
    """事件类型枚举"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    PERMISSION_UPDATE = "permission_update"
    PERMISSION_CHECK = "permission_check"
    
    RESOURCE_CREATE = "resource_create"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"
    RESOURCE_ACCESS = "resource_access"
    
    ORGANIZATION_CREATE = "organization_create"
    ORGANIZATION_UPDATE = "organization_update"
    ORGANIZATION_DELETE = "organization_delete"
    ORGANIZATION_JOIN = "organization_join"
    ORGANIZATION_LEAVE = "organization_leave"
    
    SYSTEM_ERROR = "system_error"
    SECURITY_ALERT = "security_alert"
    COMPLIANCE_CHECK = "compliance_check"


class EventSeverity(str, Enum):
    """事件严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(str, Enum):
    """事件状态"""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    ERROR = "error"


class AuditCategory(str, Enum):
    """审计分类"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    SYSTEM = "system"


# ====================
# 核心数据模型
# ====================

class AuditEvent(BaseModel):
    """审计事件核心模型"""
    id: Optional[str] = None
    event_type: EventType
    category: AuditCategory
    severity: EventSeverity = EventSeverity.LOW
    status: EventStatus = EventStatus.SUCCESS
    
    # 事件主体信息
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    organization_id: Optional[str] = None
    
    # 资源相关信息
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    
    # 事件描述
    action: str = Field(..., description="执行的操作")
    description: Optional[str] = None
    
    # 技术信息
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    api_endpoint: Optional[str] = None
    http_method: Optional[str] = None
    
    # 结果信息
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    
    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: Optional[datetime] = None
    
    # 合规相关
    retention_policy: Optional[str] = None
    compliance_flags: Optional[List[str]] = None


class UserActivity(BaseModel):
    """用户活动记录"""
    user_id: str
    session_id: Optional[str] = None
    activity_type: EventType
    activity_description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    success: bool = True
    metadata: Optional[Dict[str, Any]] = None


class SecurityEvent(BaseModel):
    """安全事件模型"""
    id: Optional[str] = None
    event_type: EventType
    severity: EventSeverity
    threat_level: str = "low"  # low, medium, high, critical
    
    # 事件详情
    source_ip: Optional[str] = None
    target_resource: Optional[str] = None
    attack_vector: Optional[str] = None
    
    # 检测信息
    detection_method: Optional[str] = None
    confidence_score: Optional[float] = None
    
    # 响应信息
    response_action: Optional[str] = None
    investigation_status: str = "open"  # open, investigating, resolved, false_positive
    
    # 时间戳
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    # 关联信息
    related_events: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceReport(BaseModel):
    """合规报告模型"""
    id: Optional[str] = None
    report_type: str
    compliance_standard: str  # GDPR, SOX, HIPAA, etc.
    
    # 报告期间
    period_start: datetime
    period_end: datetime
    
    # 统计信息
    total_events: int = 0
    compliant_events: int = 0
    non_compliant_events: int = 0
    compliance_score: float = 0.0
    
    # 详细信息
    findings: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    
    # 时间戳
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: Optional[str] = None
    
    # 状态
    status: str = "draft"  # draft, final, published
    metadata: Optional[Dict[str, Any]] = None


# ====================
# 请求/响应模型
# ====================

class AuditEventCreateRequest(BaseModel):
    """创建审计事件请求"""
    event_type: EventType
    category: AuditCategory
    severity: EventSeverity = EventSeverity.LOW
    action: str
    description: Optional[str] = None
    
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    organization_id: Optional[str] = None
    
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    api_endpoint: Optional[str] = None
    http_method: Optional[str] = None
    
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class AuditEventResponse(BaseModel):
    """审计事件响应"""
    id: str
    event_type: EventType
    category: AuditCategory
    severity: EventSeverity
    status: EventStatus
    action: str
    description: Optional[str] = None
    
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    
    success: bool
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class AuditQueryRequest(BaseModel):
    """审计查询请求"""
    event_types: Optional[List[EventType]] = None
    categories: Optional[List[AuditCategory]] = None
    severities: Optional[List[EventSeverity]] = None
    
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    resource_type: Optional[str] = None
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    success_only: Optional[bool] = None
    failure_only: Optional[bool] = None
    
    ip_address: Optional[str] = None
    tags: Optional[List[str]] = None
    
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)
    
    sort_by: str = "timestamp"
    sort_order: str = "desc"  # asc, desc


class AuditQueryResponse(BaseModel):
    """审计查询响应"""
    events: List[AuditEventResponse]
    total_count: int
    page_info: Dict[str, Any]
    filters_applied: Dict[str, Any]
    query_metadata: Optional[Dict[str, Any]] = None


class UserActivitySummary(BaseModel):
    """用户活动摘要"""
    user_id: str
    total_activities: int
    success_count: int
    failure_count: int
    last_activity: Optional[datetime] = None
    most_common_activities: List[Dict[str, Any]]
    risk_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class SecurityAlertRequest(BaseModel):
    """安全告警请求"""
    threat_type: str
    severity: EventSeverity
    source_ip: Optional[str] = None
    target_resource: Optional[str] = None
    description: str
    metadata: Optional[Dict[str, Any]] = None


class ComplianceReportRequest(BaseModel):
    """合规报告请求"""
    report_type: str
    compliance_standard: str
    period_start: datetime
    period_end: datetime
    include_details: bool = True
    filters: Optional[Dict[str, Any]] = None


# ====================
# 系统和服务模型
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


class ServiceStats(BaseModel):
    """服务统计"""
    total_events: int
    events_today: int
    active_users: int
    security_alerts: int
    compliance_score: float