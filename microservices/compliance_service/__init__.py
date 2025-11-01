"""
Compliance Service

AI平台内容合规检查服务
提供内容审核、PII检测、提示词注入检测等功能
"""

from .models import (
    ComplianceCheck,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceCheckType,
    ComplianceStatus,
    RiskLevel,
    ContentType
)

from .compliance_service import ComplianceService
from .compliance_repository import ComplianceRepository
from .middleware import ComplianceMiddleware, ComplianceClient
from .client import ComplianceServiceClient, get_compliance_client
from .service_clients import (
    AuditServiceClient,
    AccountServiceClient,
    StorageServiceClient,
    ServiceClients,
    get_service_clients
)

__version__ = "1.0.0"

__all__ = [
    # Core Service
    "ComplianceService",
    "ComplianceRepository",
    
    # Client for other services to use
    "ComplianceServiceClient",
    "get_compliance_client",
    
    # Middleware integration
    "ComplianceMiddleware",
    "ComplianceClient",  # Legacy name, same as ComplianceServiceClient
    
    # Service clients (for compliance to talk to other services)
    "AuditServiceClient",
    "AccountServiceClient",
    "StorageServiceClient",
    "ServiceClients",
    "get_service_clients",
    
    # Models
    "ComplianceCheck",
    "ComplianceCheckRequest",
    "ComplianceCheckResponse",
    "ComplianceCheckType",
    "ComplianceStatus",
    "RiskLevel",
    "ContentType"
]

