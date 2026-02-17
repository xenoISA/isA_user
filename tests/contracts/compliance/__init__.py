"""
Compliance Service Test Contracts

Provides Pydantic schemas, test data factory, and request builders
for compliance service testing.
"""

from .data_contract import (
    # Enums
    ContentType,
    ComplianceCheckType,
    ComplianceStatus,
    RiskLevel,
    ModerationCategory,
    PIIType,
    # Request Contracts
    ComplianceCheckRequestContract,
    BatchComplianceCheckRequestContract,
    CompliancePolicyRequestContract,
    ComplianceReportRequestContract,
    UserConsentRequestContract,
    CardDataCheckRequestContract,
    ReviewUpdateRequestContract,
    UserChecksQueryParamsContract,
    # Response Contracts
    ContentModerationResultContract,
    PIIDetectionResultContract,
    PromptInjectionResultContract,
    ComplianceCheckResponseContract,
    BatchComplianceCheckResponseContract,
    CompliancePolicyResponseContract,
    ComplianceReportResponseContract,
    ComplianceStatsResponseContract,
    ComplianceServiceStatusContract,
    UserDataExportResponseContract,
    UserDataSummaryResponseContract,
    CardDataCheckResponseContract,
    # Factory
    ComplianceTestDataFactory,
    # Builders
    ComplianceCheckRequestBuilder,
    CompliancePolicyRequestBuilder,
    ComplianceReportRequestBuilder,
)

__all__ = [
    # Enums
    "ContentType",
    "ComplianceCheckType",
    "ComplianceStatus",
    "RiskLevel",
    "ModerationCategory",
    "PIIType",
    # Request Contracts
    "ComplianceCheckRequestContract",
    "BatchComplianceCheckRequestContract",
    "CompliancePolicyRequestContract",
    "ComplianceReportRequestContract",
    "UserConsentRequestContract",
    "CardDataCheckRequestContract",
    "ReviewUpdateRequestContract",
    "UserChecksQueryParamsContract",
    # Response Contracts
    "ContentModerationResultContract",
    "PIIDetectionResultContract",
    "PromptInjectionResultContract",
    "ComplianceCheckResponseContract",
    "BatchComplianceCheckResponseContract",
    "CompliancePolicyResponseContract",
    "ComplianceReportResponseContract",
    "ComplianceStatsResponseContract",
    "ComplianceServiceStatusContract",
    "UserDataExportResponseContract",
    "UserDataSummaryResponseContract",
    "CardDataCheckResponseContract",
    # Factory
    "ComplianceTestDataFactory",
    # Builders
    "ComplianceCheckRequestBuilder",
    "CompliancePolicyRequestBuilder",
    "ComplianceReportRequestBuilder",
]
