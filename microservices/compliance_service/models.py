"""
Compliance Service Models

定义合规检查相关的数据模型，包括内容审核、隐私检查、AI安全等
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


# ====================
# 枚举类型定义
# ====================

class ContentType(str, Enum):
    """内容类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    PROMPT = "prompt"
    RESPONSE = "response"


class ComplianceCheckType(str, Enum):
    """合规检查类型"""
    CONTENT_MODERATION = "content_moderation"  # 内容审核
    PII_DETECTION = "pii_detection"  # 个人信息检测
    PROMPT_INJECTION = "prompt_injection"  # 提示词注入检测
    TOXICITY = "toxicity"  # 毒性检测
    COPYRIGHT = "copyright"  # 版权检测
    AGE_RESTRICTION = "age_restriction"  # 年龄限制
    GDPR_COMPLIANCE = "gdpr_compliance"  # GDPR合规
    HIPAA_COMPLIANCE = "hipaa_compliance"  # HIPAA合规
    CONTENT_SAFETY = "content_safety"  # 内容安全


class ComplianceStatus(str, Enum):
    """合规状态"""
    PASS = "pass"  # 通过
    FAIL = "fail"  # 失败
    WARNING = "warning"  # 警告
    PENDING = "pending"  # 待审核
    FLAGGED = "flagged"  # 标记
    BLOCKED = "blocked"  # 已阻止


class RiskLevel(str, Enum):
    """风险等级"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModerationCategory(str, Enum):
    """内容审核分类"""
    HATE_SPEECH = "hate_speech"
    VIOLENCE = "violence"
    SEXUAL = "sexual"
    HARASSMENT = "harassment"
    SELF_HARM = "self_harm"
    ILLEGAL = "illegal"
    SPAM = "spam"
    MISINFORMATION = "misinformation"
    CHILD_SAFETY = "child_safety"


class PIIType(str, Enum):
    """个人信息类型"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    IP_ADDRESS = "ip_address"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"
    MEDICAL_INFO = "medical_info"


# ====================
# 核心数据模型
# ====================

class ComplianceCheck(BaseModel):
    """合规检查记录"""
    id: Optional[int] = None
    check_id: str = Field(..., description="检查唯一标识符")
    
    # 检查基本信息
    check_type: ComplianceCheckType
    content_type: ContentType
    status: ComplianceStatus
    risk_level: RiskLevel = RiskLevel.NONE
    
    # 关联信息
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # 内容信息
    content_id: Optional[str] = Field(None, description="内容ID（文件ID或消息ID）")
    content_hash: Optional[str] = Field(None, description="内容哈希值")
    content_size: Optional[int] = Field(None, description="内容大小（字节）")
    
    # 检查结果
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="置信度分数")
    violations: List[Dict[str, Any]] = Field(default_factory=list, description="违规项列表")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="警告项列表")
    detected_issues: List[str] = Field(default_factory=list, description="检测到的问题")
    
    # 审核详情
    moderation_categories: Optional[Dict[str, float]] = Field(None, description="审核类别评分")
    detected_pii: Optional[List[Dict[str, Any]]] = Field(None, description="检测到的PII")
    
    # 处理信息
    action_taken: Optional[str] = Field(None, description="采取的行动")
    blocked_reason: Optional[str] = Field(None, description="阻止原因")
    human_review_required: bool = Field(False, description="是否需要人工审核")
    reviewed_by: Optional[str] = Field(None, description="审核人员")
    review_notes: Optional[str] = Field(None, description="审核备注")
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    provider: Optional[str] = Field(None, description="检查提供商（OpenAI, AWS, etc）")
    
    # 时间戳
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CompliancePolicy(BaseModel):
    """合规策略配置"""
    id: Optional[int] = None
    policy_id: str = Field(..., description="策略ID")
    policy_name: str = Field(..., description="策略名称")
    
    # 策略范围
    organization_id: Optional[str] = Field(None, description="组织ID（为空则为全局策略）")
    content_types: List[ContentType] = Field(..., description="适用的内容类型")
    check_types: List[ComplianceCheckType] = Field(..., description="启用的检查类型")
    
    # 策略规则
    rules: Dict[str, Any] = Field(..., description="策略规则配置")
    thresholds: Dict[str, float] = Field(default_factory=dict, description="阈值配置")
    
    # 行为配置
    auto_block: bool = Field(True, description="自动阻止违规内容")
    require_human_review: bool = Field(False, description="需要人工审核")
    notification_enabled: bool = Field(True, description="启用通知")
    
    # 状态
    is_active: bool = Field(True, description="是否激活")
    priority: int = Field(100, description="优先级")
    
    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class ContentModerationResult(BaseModel):
    """内容审核结果"""
    check_id: str
    content_type: ContentType
    status: ComplianceStatus
    risk_level: RiskLevel
    
    # 审核分类评分
    categories: Dict[ModerationCategory, float] = Field(default_factory=dict)
    flagged_categories: List[ModerationCategory] = Field(default_factory=list)
    
    # 详细信息
    confidence: float = 0.0
    details: Optional[Dict[str, Any]] = None
    
    # 建议
    recommendation: str = "allow"  # allow, review, block
    explanation: Optional[str] = None
    
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class PIIDetectionResult(BaseModel):
    """PII检测结果"""
    check_id: str
    status: ComplianceStatus
    
    # 检测到的PII
    detected_pii: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="检测到的PII列表，每项包含: type, value(masked), location, confidence"
    )
    
    # 统计
    pii_count: int = 0
    pii_types: List[PIIType] = Field(default_factory=list)
    
    # 风险评估
    risk_level: RiskLevel
    needs_redaction: bool = False
    
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class PromptInjectionResult(BaseModel):
    """提示词注入检测结果"""
    check_id: str
    status: ComplianceStatus
    risk_level: RiskLevel
    
    # 检测结果
    is_injection_detected: bool = False
    injection_type: Optional[str] = None  # direct, indirect, jailbreak
    confidence: float = 0.0
    
    # 检测到的模式
    detected_patterns: List[str] = Field(default_factory=list)
    suspicious_tokens: List[str] = Field(default_factory=list)
    
    # 建议
    recommendation: str = "allow"
    explanation: Optional[str] = None
    
    checked_at: datetime = Field(default_factory=datetime.utcnow)


# ====================
# 请求/响应模型
# ====================

class ComplianceCheckRequest(BaseModel):
    """合规检查请求"""
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # 内容信息
    content_type: ContentType
    content: Optional[str] = Field(None, description="文本内容")
    content_id: Optional[str] = Field(None, description="文件ID（用于文件/图片/音频）")
    content_url: Optional[str] = Field(None, description="内容URL")
    
    # 检查配置
    check_types: List[ComplianceCheckType] = Field(
        default_factory=lambda: [ComplianceCheckType.CONTENT_MODERATION],
        description="要执行的检查类型"
    )
    policy_id: Optional[str] = Field(None, description="使用的策略ID")
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = None


class ComplianceCheckResponse(BaseModel):
    """合规检查响应"""
    check_id: str
    status: ComplianceStatus
    risk_level: RiskLevel
    
    # 检查结果
    passed: bool = Field(..., description="是否通过合规检查")
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 详细结果
    moderation_result: Optional[ContentModerationResult] = None
    pii_result: Optional[PIIDetectionResult] = None
    injection_result: Optional[PromptInjectionResult] = None
    
    # 建议行动
    action_required: str = "none"  # none, review, block
    action_taken: Optional[str] = None
    message: str
    
    # 元数据
    checked_at: datetime
    processing_time_ms: float


class BatchComplianceCheckRequest(BaseModel):
    """批量合规检查请求"""
    user_id: str
    organization_id: Optional[str] = None
    
    items: List[Dict[str, Any]] = Field(..., description="待检查项列表")
    check_types: List[ComplianceCheckType]


class BatchComplianceCheckResponse(BaseModel):
    """批量合规检查响应"""
    total_items: int
    passed_items: int
    failed_items: int
    flagged_items: int
    
    results: List[ComplianceCheckResponse]
    summary: Dict[str, Any]


class ComplianceReportRequest(BaseModel):
    """合规报告请求"""
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # 时间范围
    start_date: datetime
    end_date: datetime
    
    # 筛选条件
    check_types: Optional[List[ComplianceCheckType]] = None
    risk_levels: Optional[List[RiskLevel]] = None
    statuses: Optional[List[ComplianceStatus]] = None
    
    # 报告类型
    include_violations: bool = True
    include_statistics: bool = True
    include_trends: bool = False


class ComplianceReportResponse(BaseModel):
    """合规报告响应"""
    report_id: str
    period: Dict[str, datetime]
    
    # 统计数据
    total_checks: int
    passed_checks: int
    failed_checks: int
    flagged_checks: int
    
    # 违规统计
    violations_by_type: Dict[str, int]
    violations_by_category: Dict[str, int]
    high_risk_incidents: int
    
    # 用户统计
    unique_users: int
    top_violators: List[Dict[str, Any]]
    
    # 趋势数据
    daily_stats: Optional[List[Dict[str, Any]]] = None
    
    # 详细记录
    violations: Optional[List[ComplianceCheck]] = None
    
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class CompliancePolicyRequest(BaseModel):
    """创建/更新合规策略请求"""
    policy_name: str
    organization_id: Optional[str] = None
    
    content_types: List[ContentType]
    check_types: List[ComplianceCheckType]
    rules: Dict[str, Any]
    thresholds: Optional[Dict[str, float]] = None
    
    auto_block: bool = True
    require_human_review: bool = False
    notification_enabled: bool = True


# ====================
# 系统模型
# ====================

class ComplianceServiceStatus(BaseModel):
    """合规服务状态"""
    service: str = "compliance_service"
    status: str = "operational"
    port: int = 8250
    version: str = "1.0.0"
    
    # 集成状态
    database_connected: bool
    nats_connected: bool
    
    # 提供商状态
    providers: Dict[str, bool] = Field(
        default_factory=lambda: {
            "openai": False,
            "aws_comprehend": False,
            "perspective_api": False
        }
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ComplianceStats(BaseModel):
    """合规统计"""
    total_checks_today: int
    total_checks_7d: int
    total_checks_30d: int
    
    violations_today: int
    violations_7d: int
    violations_30d: int
    
    blocked_content_today: int
    pending_reviews: int
    
    avg_processing_time_ms: float
    checks_by_type: Dict[str, int]
    violations_by_risk: Dict[str, int]


# 导出所有模型
__all__ = [
    # Enums
    'ContentType', 'ComplianceCheckType', 'ComplianceStatus', 'RiskLevel',
    'ModerationCategory', 'PIIType',
    
    # Core Models
    'ComplianceCheck', 'CompliancePolicy', 'ContentModerationResult',
    'PIIDetectionResult', 'PromptInjectionResult',
    
    # Request/Response Models
    'ComplianceCheckRequest', 'ComplianceCheckResponse',
    'BatchComplianceCheckRequest', 'BatchComplianceCheckResponse',
    'ComplianceReportRequest', 'ComplianceReportResponse',
    'CompliancePolicyRequest',
    
    # System Models
    'ComplianceServiceStatus', 'ComplianceStats'
]

