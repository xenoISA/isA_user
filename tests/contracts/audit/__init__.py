"""
Audit Service Contracts Package

Provides data contracts, test data factory, and request builders for audit service testing.
"""

from tests.contracts.audit.data_contract import (
    # Enums
    EventType,
    AuditCategory,
    EventSeverity,
    EventStatus,
    InvestigationStatus,
    ComplianceStandard,
    ReportType,

    # Request Contracts
    AuditEventCreateRequestContract,
    AuditEventBatchRequestContract,
    AuditQueryRequestContract,
    UserActivityQueryRequestContract,
    SecurityAlertRequestContract,
    SecurityEventQueryRequestContract,
    ComplianceReportRequestContract,
    DataCleanupRequestContract,

    # Response Contracts
    AuditEventResponseContract,
    AuditQueryResponseContract,
    AuditBatchResponseContract,
    UserActivityResponseContract,
    UserActivitySummaryResponseContract,
    SecurityEventResponseContract,
    SecurityEventListResponseContract,
    ComplianceReportResponseContract,
    ComplianceStandardResponseContract,
    AuditServiceStatsResponseContract,
    AuditServiceHealthResponseContract,
    DataCleanupResponseContract,

    # Factory
    AuditTestDataFactory,

    # Builders
    AuditEventCreateRequestBuilder,
    AuditQueryRequestBuilder,
    SecurityAlertRequestBuilder,
)

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
