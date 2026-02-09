"""
Compliance Service Event Models

合规服务事件数据模型定义
"""

from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class ComplianceEventType(str, Enum):
    """
    Events published by compliance_service.

    Stream: compliance-stream
    Subjects: compliance.>
    """
    CHECK_PERFORMED = "compliance.check.performed"
    VIOLATION_DETECTED = "compliance.violation.detected"
    WARNING_ISSUED = "compliance.warning.issued"


class ComplianceSubscribedEventType(str, Enum):
    """Events that compliance_service subscribes to from other services."""
    USER_CREATED = "user.created"
    ORDER_COMPLETED = "order.completed"


class ComplianceStreamConfig:
    """Stream configuration for compliance_service"""
    STREAM_NAME = "compliance-stream"
    SUBJECTS = ["compliance.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "compliance"

from typing import List, Dict, Any, Optional
from datetime import datetime


class ComplianceCheckPerformedEvent(BaseModel):
    """合规检查执行完成事件"""

    check_id: str = Field(..., description="检查ID")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    check_type: str = Field(..., description="检查类型")
    content_type: str = Field(..., description="内容类型")
    status: str = Field(..., description="检查状态")
    risk_level: str = Field(..., description="风险级别")
    violations_count: int = Field(default=0, description="违规数量")
    warnings_count: int = Field(default=0, description="警告数量")
    action_taken: Optional[str] = Field(None, description="采取的措施")
    processing_time_ms: Optional[float] = Field(None, description="处理时间(毫秒)")
    timestamp: str = Field(..., description="事件时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")


class ComplianceViolationDetectedEvent(BaseModel):
    """检测到合规违规事件"""

    check_id: str = Field(..., description="检查ID")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    violations: List[Dict[str, Any]] = Field(default_factory=list, description="违规详情列表")
    risk_level: str = Field(..., description="风险级别")
    action_taken: Optional[str] = Field(None, description="采取的措施")
    requires_review: bool = Field(default=False, description="是否需要人工审核")
    blocked_content: bool = Field(default=False, description="是否阻止了内容")
    timestamp: str = Field(..., description="事件时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")


class ComplianceWarningIssuedEvent(BaseModel):
    """发出合规警告事件"""

    check_id: str = Field(..., description="检查ID")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="警告详情列表")
    warning_types: List[str] = Field(default_factory=list, description="警告类型列表")
    risk_level: str = Field(default="low", description="风险级别")
    allowed_with_warning: bool = Field(default=True, description="是否允许但带警告")
    timestamp: str = Field(..., description="事件时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")
