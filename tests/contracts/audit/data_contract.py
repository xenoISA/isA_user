"""
Audit Service Data Contract

Defines canonical data structures for audit service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for audit service test data.
Zero hardcoded data - all values generated through factory methods.
"""

import uuid
import random
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums (matching production models)
# ============================================================================

class EventType(str, Enum):
    """Audit event types"""
    # User events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"

    # Permission events
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    PERMISSION_UPDATE = "permission_update"

    # Resource events
    RESOURCE_CREATE = "resource_create"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"
    RESOURCE_ACCESS = "resource_access"

    # Organization events
    ORGANIZATION_CREATE = "organization_create"
    ORGANIZATION_UPDATE = "organization_update"
    ORGANIZATION_DELETE = "organization_delete"
    ORGANIZATION_JOIN = "organization_join"
    ORGANIZATION_LEAVE = "organization_leave"

    # System events
    SYSTEM_ERROR = "system_error"
    SYSTEM_CONFIG_CHANGE = "system_config_change"

    # Security events
    SECURITY_ALERT = "security_alert"
    SECURITY_VIOLATION = "security_violation"

    # Compliance events
    COMPLIANCE_CHECK = "compliance_check"


class AuditCategory(str, Enum):
    """Audit event categories"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    SYSTEM = "system"


class EventSeverity(str, Enum):
    """Event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(str, Enum):
    """Event status"""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    ERROR = "error"


class InvestigationStatus(str, Enum):
    """Security event investigation status"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class ComplianceStandard(str, Enum):
    """Supported compliance standards"""
    GDPR = "GDPR"
    SOX = "SOX"
    HIPAA = "HIPAA"


class ReportType(str, Enum):
    """Compliance report types"""
    PERIODIC = "periodic"
    AD_HOC = "ad_hoc"
    INVESTIGATION = "investigation"
    QUARTERLY_AUDIT = "quarterly_audit"


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class AuditEventCreateRequestContract(BaseModel):
    """
    Contract: Audit event creation request schema

    Used for logging new audit events via API.
    """
    event_type: EventType = Field(..., description="Type of audit event")
    category: AuditCategory = Field(..., description="Event category")
    severity: EventSeverity = Field(default=EventSeverity.LOW, description="Event severity")
    action: str = Field(..., min_length=1, max_length=255, description="Action performed")
    description: Optional[str] = Field(None, max_length=1000, description="Event description")
    user_id: Optional[str] = Field(None, description="User who performed the action")
    organization_id: Optional[str] = Field(None, description="Organization context")
    session_id: Optional[str] = Field(None, description="Session identifier")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, max_length=500, description="Client user agent")
    resource_type: Optional[str] = Field(None, max_length=100, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    resource_name: Optional[str] = Field(None, max_length=255, description="Resource name")
    success: bool = Field(default=True, description="Whether action succeeded")
    error_message: Optional[str] = Field(None, max_length=1000, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    tags: Optional[List[str]] = Field(default_factory=list, description="Event tags")

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Action must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("action cannot be empty or whitespace")
        return v.strip()

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Basic IP address validation"""
        if v is not None:
            v = v.strip()
            # Allow IPv4, IPv6, and localhost
            if not v:
                return None
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "user_login",
                "category": "authentication",
                "severity": "low",
                "action": "User logged in via OAuth",
                "user_id": "user_001",
                "ip_address": "192.168.1.100",
                "success": True,
            }
        }


class AuditEventBatchRequestContract(BaseModel):
    """
    Contract: Batch audit event logging request schema

    Used for logging multiple events at once.
    """
    events: List[AuditEventCreateRequestContract] = Field(
        ..., min_length=1, max_length=100,
        description="List of events to log (max 100)"
    )

    @field_validator('events')
    @classmethod
    def validate_events(cls, v: List) -> List:
        """Validate batch size"""
        if len(v) > 100:
            raise ValueError("Maximum 100 events per batch")
        if len(v) == 0:
            raise ValueError("At least one event required")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "event_type": "user_login",
                        "category": "authentication",
                        "action": "User logged in",
                        "user_id": "user_001",
                    }
                ]
            }
        }


class AuditQueryRequestContract(BaseModel):
    """
    Contract: Audit event query request schema

    Used for querying audit events with filters.
    """
    event_types: Optional[List[EventType]] = Field(None, description="Filter by event types")
    categories: Optional[List[AuditCategory]] = Field(None, description="Filter by categories")
    severities: Optional[List[EventSeverity]] = Field(None, description="Filter by severities")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    organization_id: Optional[str] = Field(None, description="Filter by organization ID")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    success: Optional[bool] = Field(None, description="Filter by success status")
    start_time: Optional[datetime] = Field(None, description="Start of time range")
    end_time: Optional[datetime] = Field(None, description="End of time range")
    limit: int = Field(default=100, ge=1, le=1000, description="Max results (1-1000)")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")

    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Limit cannot exceed 1000"""
        if v > 1000:
            raise ValueError("Query limit cannot exceed 1000")
        return v

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate time range is within 365 days"""
        if v is not None and info.data.get('start_time') is not None:
            start = info.data['start_time']
            if v < start:
                raise ValueError("end_time must be after start_time")
            if (v - start).days > 365:
                raise ValueError("Time range cannot exceed 365 days")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "event_types": ["user_login", "user_logout"],
                "categories": ["authentication"],
                "user_id": "user_001",
                "start_time": "2025-12-01T00:00:00Z",
                "end_time": "2025-12-22T23:59:59Z",
                "limit": 100,
                "offset": 0,
            }
        }


class UserActivityQueryRequestContract(BaseModel):
    """
    Contract: User activity query request schema

    Used for retrieving user activity history.
    """
    days: int = Field(default=30, ge=1, le=365, description="Number of days to query")
    limit: int = Field(default=100, ge=1, le=1000, description="Max results")

    class Config:
        json_schema_extra = {
            "example": {
                "days": 30,
                "limit": 100,
            }
        }


class SecurityAlertRequestContract(BaseModel):
    """
    Contract: Security alert creation request schema

    Used for creating security alerts.
    """
    threat_type: str = Field(..., min_length=1, max_length=100, description="Type of threat")
    severity: EventSeverity = Field(..., description="Alert severity")
    source_ip: Optional[str] = Field(None, description="Source IP of threat")
    target_resource: Optional[str] = Field(None, max_length=255, description="Target resource")
    description: str = Field(..., min_length=1, max_length=1000, description="Alert description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional data")

    @field_validator('threat_type')
    @classmethod
    def validate_threat_type(cls, v: str) -> str:
        """Threat type must not be empty"""
        if not v or not v.strip():
            raise ValueError("threat_type cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "threat_type": "brute_force_attempt",
                "severity": "high",
                "source_ip": "10.0.0.15",
                "target_resource": "auth_endpoint",
                "description": "Multiple failed login attempts detected",
            }
        }


class SecurityEventQueryRequestContract(BaseModel):
    """
    Contract: Security event query request schema

    Used for querying security events.
    """
    days: int = Field(default=7, ge=1, le=90, description="Number of days to query")
    severity: Optional[EventSeverity] = Field(None, description="Filter by severity")
    investigation_status: Optional[InvestigationStatus] = Field(None, description="Filter by status")
    limit: int = Field(default=100, ge=1, le=1000, description="Max results")

    class Config:
        json_schema_extra = {
            "example": {
                "days": 7,
                "severity": "high",
                "limit": 100,
            }
        }


class ComplianceReportRequestContract(BaseModel):
    """
    Contract: Compliance report generation request schema

    Used for generating compliance reports.
    """
    report_type: ReportType = Field(..., description="Type of report")
    compliance_standard: ComplianceStandard = Field(..., description="Compliance standard")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    include_details: bool = Field(default=True, description="Include detailed findings")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")

    @field_validator('period_end')
    @classmethod
    def validate_period(cls, v: datetime, info) -> datetime:
        """Validate period end is after start"""
        if info.data.get('period_start') is not None:
            if v < info.data['period_start']:
                raise ValueError("period_end must be after period_start")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "report_type": "quarterly_audit",
                "compliance_standard": "GDPR",
                "period_start": "2025-10-01T00:00:00Z",
                "period_end": "2025-12-31T23:59:59Z",
                "include_details": True,
            }
        }


class DataCleanupRequestContract(BaseModel):
    """
    Contract: Data cleanup request schema

    Used for cleaning up old audit data.
    """
    retention_days: int = Field(default=365, ge=30, le=2555, description="Retention period in days")
    dry_run: bool = Field(default=False, description="Preview without deleting")

    class Config:
        json_schema_extra = {
            "example": {
                "retention_days": 365,
                "dry_run": False,
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class AuditEventResponseContract(BaseModel):
    """
    Contract: Audit event response schema

    Validates API response structure for audit events.
    """
    id: str = Field(..., description="Unique event ID")
    event_type: str = Field(..., description="Event type")
    category: str = Field(..., description="Event category")
    severity: str = Field(..., description="Event severity")
    status: str = Field(..., description="Event status")
    action: str = Field(..., description="Action performed")
    description: Optional[str] = Field(None, description="Event description")
    user_id: Optional[str] = Field(None, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    ip_address: Optional[str] = Field(None, description="Client IP")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    resource_name: Optional[str] = Field(None, description="Resource name")
    success: bool = Field(..., description="Success status")
    error_message: Optional[str] = Field(None, description="Error message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    tags: List[str] = Field(default_factory=list, description="Tags")
    compliance_flags: List[str] = Field(default_factory=list, description="Compliance flags")
    retention_policy: Optional[str] = Field(None, description="Retention policy")
    timestamp: datetime = Field(..., description="Event timestamp")
    created_at: datetime = Field(..., description="Record creation time")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "audit_abc123",
                "event_type": "user_login",
                "category": "authentication",
                "severity": "low",
                "status": "success",
                "action": "User logged in",
                "user_id": "user_001",
                "success": True,
                "timestamp": "2025-12-22T10:00:00Z",
                "created_at": "2025-12-22T10:00:00Z",
            }
        }


class AuditQueryResponseContract(BaseModel):
    """
    Contract: Audit query response schema

    Validates API response for audit event queries.
    """
    events: List[AuditEventResponseContract] = Field(..., description="List of events")
    total_count: int = Field(..., ge=0, description="Total matching events")
    page_info: Dict[str, Any] = Field(..., description="Pagination info")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")

    class Config:
        json_schema_extra = {
            "example": {
                "events": [],
                "total_count": 0,
                "page_info": {"limit": 100, "offset": 0, "has_more": False},
                "filters_applied": {},
            }
        }


class AuditBatchResponseContract(BaseModel):
    """
    Contract: Batch audit event response schema

    Validates API response for batch event logging.
    """
    successful_count: int = Field(..., ge=0, description="Successfully logged events")
    failed_count: int = Field(..., ge=0, description="Failed events")
    results: List[Dict[str, Any]] = Field(..., description="Individual results")

    class Config:
        json_schema_extra = {
            "example": {
                "successful_count": 5,
                "failed_count": 0,
                "results": [{"id": "audit_001", "success": True}],
            }
        }


class UserActivityResponseContract(BaseModel):
    """
    Contract: User activity response schema

    Validates API response for user activity queries.
    """
    user_id: str = Field(..., description="User ID")
    activities: List[Dict[str, Any]] = Field(..., description="Activity list")
    total_count: int = Field(..., ge=0, description="Total activities")
    period_days: int = Field(..., ge=0, description="Query period in days")
    query_timestamp: datetime = Field(..., description="Query execution time")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_001",
                "activities": [],
                "total_count": 0,
                "period_days": 30,
                "query_timestamp": "2025-12-22T12:00:00Z",
            }
        }


class UserActivitySummaryResponseContract(BaseModel):
    """
    Contract: User activity summary response schema

    Validates API response for user activity summaries.
    """
    user_id: str = Field(..., description="User ID")
    total_activities: int = Field(..., ge=0, description="Total activities")
    success_count: int = Field(..., ge=0, description="Successful activities")
    failure_count: int = Field(..., ge=0, description="Failed activities")
    last_activity: Optional[datetime] = Field(None, description="Last activity time")
    most_common_activities: List[Dict[str, Any]] = Field(default_factory=list, description="Common activities")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score 0-100")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_001",
                "total_activities": 150,
                "success_count": 145,
                "failure_count": 5,
                "last_activity": "2025-12-22T11:30:00Z",
                "most_common_activities": [{"action": "resource_access", "count": 100}],
                "risk_score": 12.5,
                "metadata": {},
            }
        }


class SecurityEventResponseContract(BaseModel):
    """
    Contract: Security event response schema

    Validates API response for security events.
    """
    id: str = Field(..., description="Security event ID")
    event_type: str = Field(..., description="Event type")
    severity: str = Field(..., description="Severity level")
    threat_level: str = Field(..., description="Threat level")
    source_ip: Optional[str] = Field(None, description="Source IP")
    target_resource: Optional[str] = Field(None, description="Target resource")
    description: Optional[str] = Field(None, description="Event description")
    detection_method: Optional[str] = Field(None, description="Detection method")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence 0-1")
    response_action: Optional[str] = Field(None, description="Response taken")
    investigation_status: str = Field(..., description="Investigation status")
    detected_at: datetime = Field(..., description="Detection time")
    resolved_at: Optional[datetime] = Field(None, description="Resolution time")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "sec_001",
                "event_type": "security_alert",
                "severity": "high",
                "threat_level": "high",
                "investigation_status": "open",
                "detected_at": "2025-12-22T10:05:00Z",
            }
        }


class SecurityEventListResponseContract(BaseModel):
    """
    Contract: Security event list response schema

    Validates API response for security event queries.
    """
    security_events: List[SecurityEventResponseContract] = Field(..., description="Security events")
    total_count: int = Field(..., ge=0, description="Total events")
    period_days: int = Field(..., ge=0, description="Query period")
    severity_filter: Optional[str] = Field(None, description="Applied severity filter")
    query_timestamp: datetime = Field(..., description="Query time")

    class Config:
        json_schema_extra = {
            "example": {
                "security_events": [],
                "total_count": 0,
                "period_days": 7,
                "severity_filter": None,
                "query_timestamp": "2025-12-22T12:00:00Z",
            }
        }


class ComplianceReportResponseContract(BaseModel):
    """
    Contract: Compliance report response schema

    Validates API response for compliance reports.
    """
    report_type: str = Field(..., description="Report type")
    compliance_standard: str = Field(..., description="Compliance standard")
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")
    total_events: int = Field(..., ge=0, description="Total events analyzed")
    compliant_events: int = Field(..., ge=0, description="Compliant events")
    non_compliant_events: int = Field(..., ge=0, description="Non-compliant events")
    compliance_score: float = Field(..., ge=0, le=100, description="Compliance score 0-100")
    findings: List[Dict[str, Any]] = Field(default_factory=list, description="Findings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    risk_assessment: Dict[str, Any] = Field(default_factory=dict, description="Risk assessment")
    generated_at: datetime = Field(..., description="Generation time")
    generated_by: str = Field(..., description="Generator")
    status: str = Field(default="final", description="Report status")

    class Config:
        json_schema_extra = {
            "example": {
                "report_type": "quarterly_audit",
                "compliance_standard": "GDPR",
                "period_start": "2025-10-01T00:00:00Z",
                "period_end": "2025-12-31T23:59:59Z",
                "total_events": 5420,
                "compliant_events": 5350,
                "non_compliant_events": 70,
                "compliance_score": 98.7,
                "findings": [],
                "recommendations": [],
                "risk_assessment": {"risk_level": "low"},
                "generated_at": "2025-12-22T12:00:00Z",
                "generated_by": "audit_service",
                "status": "final",
            }
        }


class ComplianceStandardResponseContract(BaseModel):
    """
    Contract: Compliance standard info response schema

    Validates API response for compliance standards list.
    """
    name: str = Field(..., description="Standard name")
    description: str = Field(..., description="Standard description")
    retention_days: int = Field(..., ge=0, description="Required retention days")
    regions: List[str] = Field(default_factory=list, description="Applicable regions")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "GDPR",
                "description": "General Data Protection Regulation",
                "retention_days": 2555,
                "regions": ["EU"],
            }
        }


class AuditServiceStatsResponseContract(BaseModel):
    """
    Contract: Audit service statistics response schema

    Validates API response for service statistics.
    """
    total_events: int = Field(..., ge=0, description="Total audit events")
    events_today: int = Field(..., ge=0, description="Events logged today")
    active_users: int = Field(..., ge=0, description="Active users (30d)")
    security_alerts: int = Field(..., ge=0, description="Open security alerts")
    compliance_score: float = Field(..., ge=0, le=100, description="Overall compliance score")

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 1250000,
                "events_today": 4500,
                "active_users": 850,
                "security_alerts": 12,
                "compliance_score": 97.5,
            }
        }


class AuditServiceHealthResponseContract(BaseModel):
    """
    Contract: Audit service health response schema

    Validates API response for health checks.
    """
    service: str = Field(default="audit_service", description="Service name")
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$", description="Health status")
    port: int = Field(..., ge=1024, le=65535, description="Service port")
    version: str = Field(..., description="Service version")
    database_connected: bool = Field(..., description="Database connection status")
    timestamp: datetime = Field(..., description="Check timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "service": "audit_service",
                "status": "healthy",
                "port": 8204,
                "version": "1.0.0",
                "database_connected": True,
                "timestamp": "2025-12-22T12:00:00Z",
            }
        }


class DataCleanupResponseContract(BaseModel):
    """
    Contract: Data cleanup response schema

    Validates API response for cleanup operations.
    """
    message: str = Field(..., description="Status message")
    cleaned_events: int = Field(..., ge=0, description="Number of events cleaned")
    retention_days: int = Field(..., ge=0, description="Retention period used")
    cleanup_timestamp: datetime = Field(..., description="Cleanup execution time")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Data cleanup completed",
                "cleaned_events": 15420,
                "retention_days": 365,
                "cleanup_timestamp": "2025-12-22T02:00:00Z",
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class AuditTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Zero hardcoded data - all values generated dynamically.
    Methods prefixed with 'make_' generate valid data.
    Methods prefixed with 'make_invalid_' generate invalid data.
    """

    # ========================================================================
    # ID Generators
    # ========================================================================

    @staticmethod
    def make_audit_event_id() -> str:
        """Generate unique audit event ID"""
        return f"audit_{uuid.uuid4().hex}"

    @staticmethod
    def make_security_event_id() -> str:
        """Generate unique security event ID"""
        return f"sec_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate unique user ID"""
        return f"user_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate unique organization ID"""
        return f"org_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_session_id() -> str:
        """Generate unique session ID"""
        return f"sess_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_resource_id() -> str:
        """Generate unique resource ID"""
        return f"res_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_uuid() -> str:
        """Generate standard UUID"""
        return str(uuid.uuid4())

    @staticmethod
    def make_correlation_id() -> str:
        """Generate correlation ID for tracing"""
        return f"corr_{uuid.uuid4().hex[:16]}"

    # ========================================================================
    # String Generators
    # ========================================================================

    @staticmethod
    def make_action() -> str:
        """Generate random action description"""
        actions = [
            "User logged in", "File uploaded", "Permission granted",
            "Resource created", "Configuration changed", "Record updated",
            "Session started", "Data accessed", "Report generated",
        ]
        return f"{random.choice(actions)} - {secrets.token_hex(4)}"

    @staticmethod
    def make_description(length: int = 50) -> str:
        """Generate random description"""
        words = ["audit", "event", "security", "compliance", "access", "user", "system"]
        return " ".join(random.choices(words, k=min(length // 7, 20)))

    @staticmethod
    def make_resource_type() -> str:
        """Generate random resource type"""
        types = ["file", "folder", "document", "user", "organization", "device", "album", "photo"]
        return random.choice(types)

    @staticmethod
    def make_resource_name() -> str:
        """Generate random resource name"""
        return f"Resource_{secrets.token_hex(4)}"

    @staticmethod
    def make_threat_type() -> str:
        """Generate random threat type"""
        threats = [
            "brute_force_attempt", "unauthorized_access", "suspicious_activity",
            "data_exfiltration", "privilege_escalation", "anomalous_behavior",
        ]
        return random.choice(threats)

    @staticmethod
    def make_alphanumeric(length: int = 16) -> str:
        """Generate alphanumeric string"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))

    @staticmethod
    def make_user_agent() -> str:
        """Generate random user agent string"""
        browsers = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Mobile/15E148",
        ]
        return random.choice(browsers)

    # ========================================================================
    # IP Address Generators
    # ========================================================================

    @staticmethod
    def make_ip_address() -> str:
        """Generate random IPv4 address"""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    @staticmethod
    def make_ipv6_address() -> str:
        """Generate random IPv6 address"""
        return "::1"  # Localhost for simplicity

    @staticmethod
    def make_private_ip() -> str:
        """Generate private IP address"""
        return f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"

    # ========================================================================
    # Enum Generators
    # ========================================================================

    @staticmethod
    def make_event_type() -> EventType:
        """Generate random event type"""
        return random.choice(list(EventType))

    @staticmethod
    def make_category() -> AuditCategory:
        """Generate random audit category"""
        return random.choice(list(AuditCategory))

    @staticmethod
    def make_severity() -> EventSeverity:
        """Generate random severity"""
        return random.choice(list(EventSeverity))

    @staticmethod
    def make_status() -> EventStatus:
        """Generate random event status"""
        return random.choice(list(EventStatus))

    @staticmethod
    def make_investigation_status() -> InvestigationStatus:
        """Generate random investigation status"""
        return random.choice(list(InvestigationStatus))

    @staticmethod
    def make_compliance_standard() -> ComplianceStandard:
        """Generate random compliance standard"""
        return random.choice(list(ComplianceStandard))

    @staticmethod
    def make_report_type() -> ReportType:
        """Generate random report type"""
        return random.choice(list(ReportType))

    # ========================================================================
    # Timestamp Generators
    # ========================================================================

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current UTC timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(days=random.randint(1, days))

    @staticmethod
    def make_future_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(days=random.randint(1, days))

    @staticmethod
    def make_timestamp_iso() -> str:
        """Generate ISO format timestamp string"""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def make_time_range(days: int = 30) -> Tuple[datetime, datetime]:
        """Generate start and end time range"""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return (start, end)

    # ========================================================================
    # Numeric Generators
    # ========================================================================

    @staticmethod
    def make_positive_int(max_val: int = 1000) -> int:
        """Generate positive integer"""
        return random.randint(1, max_val)

    @staticmethod
    def make_percentage() -> float:
        """Generate percentage (0-100)"""
        return round(random.uniform(0, 100), 2)

    @staticmethod
    def make_risk_score() -> float:
        """Generate risk score (0-100)"""
        return round(random.uniform(0, 100), 2)

    @staticmethod
    def make_confidence_score() -> float:
        """Generate confidence score (0-1)"""
        return round(random.uniform(0, 1), 2)

    @staticmethod
    def make_compliance_score() -> float:
        """Generate compliance score (typically 80-100)"""
        return round(random.uniform(80, 100), 2)

    # ========================================================================
    # Metadata Generators
    # ========================================================================

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate random metadata dictionary"""
        return {
            "source": random.choice(["api", "nats", "internal"]),
            "version": f"1.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "trace_id": AuditTestDataFactory.make_correlation_id(),
        }

    @staticmethod
    def make_tags(count: int = 3) -> List[str]:
        """Generate random tags"""
        all_tags = ["security", "compliance", "audit", "user", "system", "critical", "high", "internal"]
        return random.sample(all_tags, min(count, len(all_tags)))

    @staticmethod
    def make_compliance_flags() -> List[str]:
        """Generate compliance flags"""
        flags = ["GDPR", "SOX", "HIPAA"]
        return random.sample(flags, random.randint(0, len(flags)))

    # ========================================================================
    # Request Generators (Valid Data)
    # ========================================================================

    @staticmethod
    def make_audit_event_create_request(**overrides) -> AuditEventCreateRequestContract:
        """Generate valid audit event creation request"""
        defaults = {
            "event_type": AuditTestDataFactory.make_event_type(),
            "category": AuditTestDataFactory.make_category(),
            "severity": AuditTestDataFactory.make_severity(),
            "action": AuditTestDataFactory.make_action(),
            "description": AuditTestDataFactory.make_description(),
            "user_id": AuditTestDataFactory.make_user_id(),
            "organization_id": AuditTestDataFactory.make_organization_id(),
            "session_id": AuditTestDataFactory.make_session_id(),
            "ip_address": AuditTestDataFactory.make_ip_address(),
            "user_agent": AuditTestDataFactory.make_user_agent(),
            "resource_type": AuditTestDataFactory.make_resource_type(),
            "resource_id": AuditTestDataFactory.make_resource_id(),
            "resource_name": AuditTestDataFactory.make_resource_name(),
            "success": random.choice([True, True, True, False]),  # 75% success
            "metadata": AuditTestDataFactory.make_metadata(),
            "tags": AuditTestDataFactory.make_tags(),
        }
        defaults.update(overrides)
        return AuditEventCreateRequestContract(**defaults)

    @staticmethod
    def make_audit_batch_request(count: int = 5) -> AuditEventBatchRequestContract:
        """Generate valid batch audit event request"""
        events = [
            AuditTestDataFactory.make_audit_event_create_request()
            for _ in range(count)
        ]
        return AuditEventBatchRequestContract(events=events)

    @staticmethod
    def make_audit_query_request(**overrides) -> AuditQueryRequestContract:
        """Generate valid audit query request"""
        start, end = AuditTestDataFactory.make_time_range(30)
        defaults = {
            "event_types": [AuditTestDataFactory.make_event_type()],
            "categories": [AuditTestDataFactory.make_category()],
            "start_time": start,
            "end_time": end,
            "limit": 100,
            "offset": 0,
        }
        defaults.update(overrides)
        return AuditQueryRequestContract(**defaults)

    @staticmethod
    def make_user_activity_query_request(**overrides) -> UserActivityQueryRequestContract:
        """Generate valid user activity query request"""
        defaults = {
            "days": 30,
            "limit": 100,
        }
        defaults.update(overrides)
        return UserActivityQueryRequestContract(**defaults)

    @staticmethod
    def make_security_alert_request(**overrides) -> SecurityAlertRequestContract:
        """Generate valid security alert request"""
        defaults = {
            "threat_type": AuditTestDataFactory.make_threat_type(),
            "severity": random.choice([EventSeverity.HIGH, EventSeverity.CRITICAL]),
            "source_ip": AuditTestDataFactory.make_ip_address(),
            "target_resource": AuditTestDataFactory.make_resource_name(),
            "description": f"Security alert: {AuditTestDataFactory.make_description()}",
            "metadata": AuditTestDataFactory.make_metadata(),
        }
        defaults.update(overrides)
        return SecurityAlertRequestContract(**defaults)

    @staticmethod
    def make_security_event_query_request(**overrides) -> SecurityEventQueryRequestContract:
        """Generate valid security event query request"""
        defaults = {
            "days": 7,
            "severity": EventSeverity.HIGH,
            "limit": 100,
        }
        defaults.update(overrides)
        return SecurityEventQueryRequestContract(**defaults)

    @staticmethod
    def make_compliance_report_request(**overrides) -> ComplianceReportRequestContract:
        """Generate valid compliance report request"""
        start, end = AuditTestDataFactory.make_time_range(90)
        defaults = {
            "report_type": ReportType.QUARTERLY_AUDIT,
            "compliance_standard": AuditTestDataFactory.make_compliance_standard(),
            "period_start": start,
            "period_end": end,
            "include_details": True,
            "filters": {},
        }
        defaults.update(overrides)
        return ComplianceReportRequestContract(**defaults)

    @staticmethod
    def make_data_cleanup_request(**overrides) -> DataCleanupRequestContract:
        """Generate valid data cleanup request"""
        defaults = {
            "retention_days": 365,
            "dry_run": False,
        }
        defaults.update(overrides)
        return DataCleanupRequestContract(**defaults)

    # ========================================================================
    # Response Generators
    # ========================================================================

    @staticmethod
    def make_audit_event_response(**overrides) -> Dict[str, Any]:
        """Generate audit event response data"""
        now = AuditTestDataFactory.make_timestamp()
        defaults = {
            "id": AuditTestDataFactory.make_audit_event_id(),
            "event_type": AuditTestDataFactory.make_event_type().value,
            "category": AuditTestDataFactory.make_category().value,
            "severity": AuditTestDataFactory.make_severity().value,
            "status": EventStatus.SUCCESS.value,
            "action": AuditTestDataFactory.make_action(),
            "description": AuditTestDataFactory.make_description(),
            "user_id": AuditTestDataFactory.make_user_id(),
            "organization_id": AuditTestDataFactory.make_organization_id(),
            "ip_address": AuditTestDataFactory.make_ip_address(),
            "resource_type": AuditTestDataFactory.make_resource_type(),
            "resource_id": AuditTestDataFactory.make_resource_id(),
            "resource_name": AuditTestDataFactory.make_resource_name(),
            "success": True,
            "metadata": AuditTestDataFactory.make_metadata(),
            "tags": AuditTestDataFactory.make_tags(),
            "compliance_flags": AuditTestDataFactory.make_compliance_flags(),
            "retention_policy": "1_year",
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_audit_query_response(count: int = 5) -> Dict[str, Any]:
        """Generate audit query response data"""
        events = [
            AuditTestDataFactory.make_audit_event_response()
            for _ in range(count)
        ]
        return {
            "events": events,
            "total_count": count,
            "page_info": {"limit": 100, "offset": 0, "has_more": False},
            "filters_applied": {},
        }

    @staticmethod
    def make_audit_batch_response(total: int = 5, failed: int = 0) -> Dict[str, Any]:
        """Generate batch audit response data"""
        return {
            "successful_count": total - failed,
            "failed_count": failed,
            "results": [
                {"id": AuditTestDataFactory.make_audit_event_id(), "success": True}
                for _ in range(total - failed)
            ],
        }

    @staticmethod
    def make_user_activity_response(**overrides) -> Dict[str, Any]:
        """Generate user activity response data"""
        defaults = {
            "user_id": AuditTestDataFactory.make_user_id(),
            "activities": [
                {
                    "event_id": AuditTestDataFactory.make_audit_event_id(),
                    "event_type": AuditTestDataFactory.make_event_type().value,
                    "action": AuditTestDataFactory.make_action(),
                    "timestamp": AuditTestDataFactory.make_past_timestamp().isoformat(),
                    "success": True,
                }
                for _ in range(5)
            ],
            "total_count": 5,
            "period_days": 30,
            "query_timestamp": AuditTestDataFactory.make_timestamp().isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_user_activity_summary_response(**overrides) -> Dict[str, Any]:
        """Generate user activity summary response data"""
        total = random.randint(100, 500)
        failures = random.randint(0, 20)
        defaults = {
            "user_id": AuditTestDataFactory.make_user_id(),
            "total_activities": total,
            "success_count": total - failures,
            "failure_count": failures,
            "last_activity": AuditTestDataFactory.make_timestamp().isoformat(),
            "most_common_activities": [
                {"action": "resource_access", "count": random.randint(50, 200)},
                {"action": "user_login", "count": random.randint(10, 50)},
            ],
            "risk_score": AuditTestDataFactory.make_risk_score(),
            "metadata": {"period_days": 30},
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_security_event_response(**overrides) -> Dict[str, Any]:
        """Generate security event response data"""
        defaults = {
            "id": AuditTestDataFactory.make_security_event_id(),
            "event_type": "audit.security.alert",
            "severity": EventSeverity.HIGH.value,
            "threat_level": "high",
            "source_ip": AuditTestDataFactory.make_ip_address(),
            "target_resource": AuditTestDataFactory.make_resource_name(),
            "description": AuditTestDataFactory.make_description(),
            "detection_method": "automated",
            "confidence_score": AuditTestDataFactory.make_confidence_score(),
            "response_action": "investigation_required",
            "investigation_status": InvestigationStatus.OPEN.value,
            "detected_at": AuditTestDataFactory.make_timestamp().isoformat(),
            "resolved_at": None,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_security_event_list_response(count: int = 3) -> Dict[str, Any]:
        """Generate security event list response data"""
        events = [
            AuditTestDataFactory.make_security_event_response()
            for _ in range(count)
        ]
        return {
            "security_events": events,
            "total_count": count,
            "period_days": 7,
            "severity_filter": None,
            "query_timestamp": AuditTestDataFactory.make_timestamp().isoformat(),
        }

    @staticmethod
    def make_compliance_report_response(**overrides) -> Dict[str, Any]:
        """Generate compliance report response data"""
        total = random.randint(1000, 10000)
        compliant = int(total * random.uniform(0.9, 0.99))
        start, end = AuditTestDataFactory.make_time_range(90)
        defaults = {
            "report_type": ReportType.QUARTERLY_AUDIT.value,
            "compliance_standard": AuditTestDataFactory.make_compliance_standard().value,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_events": total,
            "compliant_events": compliant,
            "non_compliant_events": total - compliant,
            "compliance_score": round((compliant / total) * 100, 2),
            "findings": [],
            "recommendations": ["Review access controls", "Update retention policies"],
            "risk_assessment": {
                "risk_level": "low",
                "compliance_score": round((compliant / total) * 100, 2),
            },
            "generated_at": AuditTestDataFactory.make_timestamp().isoformat(),
            "generated_by": "audit_service",
            "status": "final",
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_compliance_standard_response(**overrides) -> Dict[str, Any]:
        """Generate compliance standard response data"""
        standard = AuditTestDataFactory.make_compliance_standard()
        standards_info = {
            ComplianceStandard.GDPR: ("General Data Protection Regulation", 2555, ["EU"]),
            ComplianceStandard.SOX: ("Sarbanes-Oxley Act", 2555, ["US"]),
            ComplianceStandard.HIPAA: ("Health Insurance Portability and Accountability Act", 2190, ["US"]),
        }
        info = standards_info.get(standard, ("Unknown", 365, []))
        defaults = {
            "name": standard.value,
            "description": info[0],
            "retention_days": info[1],
            "regions": info[2],
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_service_stats_response(**overrides) -> Dict[str, Any]:
        """Generate service statistics response data"""
        defaults = {
            "total_events": random.randint(100000, 5000000),
            "events_today": random.randint(1000, 10000),
            "active_users": random.randint(100, 2000),
            "security_alerts": random.randint(0, 50),
            "compliance_score": AuditTestDataFactory.make_compliance_score(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_service_health_response(**overrides) -> Dict[str, Any]:
        """Generate service health response data"""
        defaults = {
            "service": "audit_service",
            "status": "healthy",
            "port": 8204,
            "version": "1.0.0",
            "database_connected": True,
            "timestamp": AuditTestDataFactory.make_timestamp().isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_data_cleanup_response(**overrides) -> Dict[str, Any]:
        """Generate data cleanup response data"""
        defaults = {
            "message": "Data cleanup completed",
            "cleaned_events": random.randint(1000, 50000),
            "retention_days": 365,
            "cleanup_timestamp": AuditTestDataFactory.make_timestamp().isoformat(),
        }
        defaults.update(overrides)
        return defaults

    # ========================================================================
    # Invalid Data Generators
    # ========================================================================

    @staticmethod
    def make_invalid_audit_event_missing_action() -> dict:
        """Generate audit event missing required action"""
        return {
            "event_type": "user.logged_in",
            "category": AuditCategory.AUTHENTICATION.value,
            # Missing action
        }

    @staticmethod
    def make_invalid_audit_event_empty_action() -> dict:
        """Generate audit event with empty action"""
        return {
            "event_type": "user.logged_in",
            "category": AuditCategory.AUTHENTICATION.value,
            "action": "",
        }

    @staticmethod
    def make_invalid_audit_event_whitespace_action() -> dict:
        """Generate audit event with whitespace-only action"""
        return {
            "event_type": "user.logged_in",
            "category": AuditCategory.AUTHENTICATION.value,
            "action": "   ",
        }

    @staticmethod
    def make_invalid_audit_event_invalid_type() -> dict:
        """Generate audit event with invalid event type"""
        return {
            "event_type": "invalid_event_type",
            "category": AuditCategory.AUTHENTICATION.value,
            "action": AuditTestDataFactory.make_action(),
        }

    @staticmethod
    def make_invalid_audit_event_invalid_category() -> dict:
        """Generate audit event with invalid category"""
        return {
            "event_type": "user.logged_in",
            "category": "invalid_category",
            "action": AuditTestDataFactory.make_action(),
        }

    @staticmethod
    def make_invalid_audit_event_invalid_severity() -> dict:
        """Generate audit event with invalid severity"""
        return {
            "event_type": "user.logged_in",
            "category": AuditCategory.AUTHENTICATION.value,
            "severity": "invalid_severity",
            "action": AuditTestDataFactory.make_action(),
        }

    @staticmethod
    def make_invalid_batch_empty() -> dict:
        """Generate empty batch request"""
        return {"events": []}

    @staticmethod
    def make_invalid_batch_too_large() -> dict:
        """Generate batch request exceeding limit"""
        return {
            "events": [
                {
                    "event_type": "user.logged_in",
                    "category": AuditCategory.AUTHENTICATION.value,
                    "action": f"Action {i}",
                }
                for i in range(101)  # Exceeds 100 limit
            ]
        }

    @staticmethod
    def make_invalid_query_limit_zero() -> dict:
        """Generate query with zero limit"""
        return {"limit": 0, "offset": 0}

    @staticmethod
    def make_invalid_query_limit_negative() -> dict:
        """Generate query with negative limit"""
        return {"limit": -1, "offset": 0}

    @staticmethod
    def make_invalid_query_limit_too_large() -> dict:
        """Generate query with limit exceeding max"""
        return {"limit": 1001, "offset": 0}

    @staticmethod
    def make_invalid_query_offset_negative() -> dict:
        """Generate query with negative offset"""
        return {"limit": 100, "offset": -1}

    @staticmethod
    def make_invalid_query_time_range_reversed() -> dict:
        """Generate query with reversed time range"""
        now = datetime.now(timezone.utc)
        return {
            "start_time": now.isoformat(),
            "end_time": (now - timedelta(days=30)).isoformat(),
        }

    @staticmethod
    def make_invalid_query_time_range_too_long() -> dict:
        """Generate query with time range exceeding 365 days"""
        now = datetime.now(timezone.utc)
        return {
            "start_time": (now - timedelta(days=400)).isoformat(),
            "end_time": now.isoformat(),
        }

    @staticmethod
    def make_invalid_security_alert_empty_threat_type() -> dict:
        """Generate security alert with empty threat type"""
        return {
            "threat_type": "",
            "severity": EventSeverity.HIGH.value,
            "description": "Test alert",
        }

    @staticmethod
    def make_invalid_security_alert_missing_severity() -> dict:
        """Generate security alert missing severity"""
        return {
            "threat_type": "brute_force",
            "description": "Test alert",
        }

    @staticmethod
    def make_invalid_compliance_report_reversed_period() -> dict:
        """Generate compliance report with reversed period"""
        now = datetime.now(timezone.utc)
        return {
            "report_type": ReportType.QUARTERLY_AUDIT.value,
            "compliance_standard": ComplianceStandard.GDPR.value,
            "period_start": now.isoformat(),
            "period_end": (now - timedelta(days=30)).isoformat(),
        }

    @staticmethod
    def make_invalid_compliance_report_invalid_standard() -> dict:
        """Generate compliance report with invalid standard"""
        start, end = AuditTestDataFactory.make_time_range(30)
        return {
            "report_type": ReportType.QUARTERLY_AUDIT.value,
            "compliance_standard": "INVALID_STANDARD",
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }

    @staticmethod
    def make_invalid_cleanup_retention_too_short() -> dict:
        """Generate cleanup request with retention too short"""
        return {"retention_days": 10}  # Min is 30

    @staticmethod
    def make_invalid_cleanup_retention_too_long() -> dict:
        """Generate cleanup request with retention too long"""
        return {"retention_days": 3000}  # Max is 2555

    # ========================================================================
    # Edge Case Generators
    # ========================================================================

    @staticmethod
    def make_unicode_action() -> str:
        """Generate action with unicode characters"""
        return f"User action \u4e2d\u6587 {secrets.token_hex(4)}"

    @staticmethod
    def make_special_chars_action() -> str:
        """Generate action with special characters"""
        return f"Action!@#$%^&*() {secrets.token_hex(4)}"

    @staticmethod
    def make_max_length_action() -> str:
        """Generate action at max length (255 chars)"""
        return "x" * 255

    @staticmethod
    def make_min_length_action() -> str:
        """Generate action at min length (1 char)"""
        return "x"

    @staticmethod
    def make_max_length_description() -> str:
        """Generate description at max length (1000 chars)"""
        return "x" * 1000

    @staticmethod
    def make_localhost_ip() -> str:
        """Generate localhost IP"""
        return "127.0.0.1"

    # ========================================================================
    # Batch Generators
    # ========================================================================

    @staticmethod
    def make_batch_audit_event_ids(count: int = 5) -> List[str]:
        """Generate multiple audit event IDs"""
        return [AuditTestDataFactory.make_audit_event_id() for _ in range(count)]

    @staticmethod
    def make_batch_user_ids(count: int = 5) -> List[str]:
        """Generate multiple user IDs"""
        return [AuditTestDataFactory.make_user_id() for _ in range(count)]

    @staticmethod
    def make_batch_create_requests(count: int = 5) -> List[AuditEventCreateRequestContract]:
        """Generate multiple audit event create requests"""
        return [AuditTestDataFactory.make_audit_event_create_request() for _ in range(count)]

    @staticmethod
    def make_batch_security_alerts(count: int = 3) -> List[SecurityAlertRequestContract]:
        """Generate multiple security alert requests"""
        return [AuditTestDataFactory.make_security_alert_request() for _ in range(count)]


# ============================================================================
# Request Builders
# ============================================================================

class AuditEventCreateRequestBuilder:
    """Builder pattern for creating audit event requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._data = {
            "event_type": AuditTestDataFactory.make_event_type(),
            "category": AuditTestDataFactory.make_category(),
            "severity": EventSeverity.LOW,
            "action": AuditTestDataFactory.make_action(),
            "success": True,
            "metadata": {},
            "tags": [],
        }

    def with_event_type(self, event_type: EventType) -> "AuditEventCreateRequestBuilder":
        """Set event type"""
        self._data["event_type"] = event_type
        return self

    def with_category(self, category: AuditCategory) -> "AuditEventCreateRequestBuilder":
        """Set category"""
        self._data["category"] = category
        return self

    def with_severity(self, severity: EventSeverity) -> "AuditEventCreateRequestBuilder":
        """Set severity"""
        self._data["severity"] = severity
        return self

    def with_action(self, action: str) -> "AuditEventCreateRequestBuilder":
        """Set action"""
        self._data["action"] = action
        return self

    def with_description(self, description: str) -> "AuditEventCreateRequestBuilder":
        """Set description"""
        self._data["description"] = description
        return self

    def with_user_id(self, user_id: str) -> "AuditEventCreateRequestBuilder":
        """Set user ID"""
        self._data["user_id"] = user_id
        return self

    def with_organization_id(self, org_id: str) -> "AuditEventCreateRequestBuilder":
        """Set organization ID"""
        self._data["organization_id"] = org_id
        return self

    def with_resource(self, resource_type: str, resource_id: str, resource_name: Optional[str] = None) -> "AuditEventCreateRequestBuilder":
        """Set resource information"""
        self._data["resource_type"] = resource_type
        self._data["resource_id"] = resource_id
        if resource_name:
            self._data["resource_name"] = resource_name
        return self

    def with_ip_address(self, ip_address: str) -> "AuditEventCreateRequestBuilder":
        """Set IP address"""
        self._data["ip_address"] = ip_address
        return self

    def with_success(self, success: bool) -> "AuditEventCreateRequestBuilder":
        """Set success status"""
        self._data["success"] = success
        return self

    def with_failure(self, error_message: str) -> "AuditEventCreateRequestBuilder":
        """Set as failed with error message"""
        self._data["success"] = False
        self._data["error_message"] = error_message
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "AuditEventCreateRequestBuilder":
        """Set metadata"""
        self._data["metadata"] = metadata
        return self

    def with_tags(self, tags: List[str]) -> "AuditEventCreateRequestBuilder":
        """Set tags"""
        self._data["tags"] = tags
        return self

    def with_invalid_action(self) -> "AuditEventCreateRequestBuilder":
        """Set invalid empty action for negative testing"""
        self._data["action"] = ""
        return self

    def build(self) -> AuditEventCreateRequestContract:
        """Build the request contract"""
        return AuditEventCreateRequestContract(**self._data)

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


class AuditQueryRequestBuilder:
    """Builder pattern for creating audit query requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._data = {
            "limit": 100,
            "offset": 0,
        }

    def with_event_types(self, event_types: List[EventType]) -> "AuditQueryRequestBuilder":
        """Set event types filter"""
        self._data["event_types"] = event_types
        return self

    def with_categories(self, categories: List[AuditCategory]) -> "AuditQueryRequestBuilder":
        """Set categories filter"""
        self._data["categories"] = categories
        return self

    def with_severities(self, severities: List[EventSeverity]) -> "AuditQueryRequestBuilder":
        """Set severities filter"""
        self._data["severities"] = severities
        return self

    def with_user_id(self, user_id: str) -> "AuditQueryRequestBuilder":
        """Set user ID filter"""
        self._data["user_id"] = user_id
        return self

    def with_organization_id(self, org_id: str) -> "AuditQueryRequestBuilder":
        """Set organization ID filter"""
        self._data["organization_id"] = org_id
        return self

    def with_time_range(self, start: datetime, end: datetime) -> "AuditQueryRequestBuilder":
        """Set time range filter"""
        self._data["start_time"] = start
        self._data["end_time"] = end
        return self

    def with_time_range_days(self, days: int) -> "AuditQueryRequestBuilder":
        """Set time range by days from now"""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        self._data["start_time"] = start
        self._data["end_time"] = end
        return self

    def with_pagination(self, limit: int, offset: int) -> "AuditQueryRequestBuilder":
        """Set pagination"""
        self._data["limit"] = limit
        self._data["offset"] = offset
        return self

    def with_success_filter(self, success: bool) -> "AuditQueryRequestBuilder":
        """Set success filter"""
        self._data["success"] = success
        return self

    def with_invalid_limit(self) -> "AuditQueryRequestBuilder":
        """Set invalid limit for negative testing"""
        self._data["limit"] = 10000
        return self

    def build(self) -> AuditQueryRequestContract:
        """Build the request contract"""
        return AuditQueryRequestContract(**self._data)

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


class SecurityAlertRequestBuilder:
    """Builder pattern for creating security alert requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._data = {
            "threat_type": AuditTestDataFactory.make_threat_type(),
            "severity": EventSeverity.HIGH,
            "description": AuditTestDataFactory.make_description(),
            "metadata": {},
        }

    def with_threat_type(self, threat_type: str) -> "SecurityAlertRequestBuilder":
        """Set threat type"""
        self._data["threat_type"] = threat_type
        return self

    def with_severity(self, severity: EventSeverity) -> "SecurityAlertRequestBuilder":
        """Set severity"""
        self._data["severity"] = severity
        return self

    def with_source_ip(self, source_ip: str) -> "SecurityAlertRequestBuilder":
        """Set source IP"""
        self._data["source_ip"] = source_ip
        return self

    def with_target_resource(self, target_resource: str) -> "SecurityAlertRequestBuilder":
        """Set target resource"""
        self._data["target_resource"] = target_resource
        return self

    def with_description(self, description: str) -> "SecurityAlertRequestBuilder":
        """Set description"""
        self._data["description"] = description
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "SecurityAlertRequestBuilder":
        """Set metadata"""
        self._data["metadata"] = metadata
        return self

    def with_brute_force(self, attempt_count: int = 50) -> "SecurityAlertRequestBuilder":
        """Configure as brute force alert"""
        self._data["threat_type"] = "brute_force_attempt"
        self._data["severity"] = EventSeverity.HIGH
        self._data["metadata"] = {"attempt_count": attempt_count}
        return self

    def with_invalid_threat_type(self) -> "SecurityAlertRequestBuilder":
        """Set invalid empty threat type for negative testing"""
        self._data["threat_type"] = ""
        return self

    def build(self) -> SecurityAlertRequestContract:
        """Build the request contract"""
        return SecurityAlertRequestContract(**self._data)

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "EventType",
    "AuditCategory",
    "EventSeverity",
    "EventStatus",
    "InvestigationStatus",
    "ComplianceStandard",
    "ReportType",

    # Request Contracts
    "AuditEventCreateRequestContract",
    "AuditEventBatchRequestContract",
    "AuditQueryRequestContract",
    "UserActivityQueryRequestContract",
    "SecurityAlertRequestContract",
    "SecurityEventQueryRequestContract",
    "ComplianceReportRequestContract",
    "DataCleanupRequestContract",

    # Response Contracts
    "AuditEventResponseContract",
    "AuditQueryResponseContract",
    "AuditBatchResponseContract",
    "UserActivityResponseContract",
    "UserActivitySummaryResponseContract",
    "SecurityEventResponseContract",
    "SecurityEventListResponseContract",
    "ComplianceReportResponseContract",
    "ComplianceStandardResponseContract",
    "AuditServiceStatsResponseContract",
    "AuditServiceHealthResponseContract",
    "DataCleanupResponseContract",

    # Factory
    "AuditTestDataFactory",

    # Builders
    "AuditEventCreateRequestBuilder",
    "AuditQueryRequestBuilder",
    "SecurityAlertRequestBuilder",
]
