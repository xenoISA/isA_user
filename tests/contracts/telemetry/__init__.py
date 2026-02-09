"""
Telemetry Service Contracts Package

Contains data contracts, test data factory, and request builders for telemetry_service.
"""

from tests.contracts.telemetry.data_contract import (
    # Enums
    DataType,
    MetricType,
    AlertLevel,
    AlertStatus,
    AggregationType,
    TimeRange,

    # Request Contracts
    TelemetryDataPointContract,
    TelemetryIngestRequestContract,
    TelemetryBatchRequestContract,
    MetricDefinitionCreateRequestContract,
    MetricDefinitionUpdateRequestContract,
    AlertRuleCreateRequestContract,
    AlertRuleUpdateRequestContract,
    AlertAcknowledgeRequestContract,
    AlertResolveRequestContract,
    TelemetryQueryRequestContract,
    RealTimeSubscriptionRequestContract,

    # Response Contracts
    TelemetryDataPointResponseContract,
    TelemetryDataResponseContract,
    MetricDefinitionResponseContract,
    MetricDefinitionListResponseContract,
    AlertRuleResponseContract,
    AlertRuleListResponseContract,
    AlertResponseContract,
    AlertListResponseContract,
    DeviceTelemetryStatsResponseContract,
    TelemetryServiceStatsResponseContract,
    RealTimeSubscriptionResponseContract,
    IngestResponseContract,
    ErrorResponseContract,

    # Factory
    TelemetryTestDataFactory,

    # Builders
    TelemetryDataPointBuilder,
    AlertRuleCreateRequestBuilder,
    TelemetryQueryRequestBuilder,
)

__all__ = [
    # Enums
    "DataType",
    "MetricType",
    "AlertLevel",
    "AlertStatus",
    "AggregationType",
    "TimeRange",

    # Request Contracts
    "TelemetryDataPointContract",
    "TelemetryIngestRequestContract",
    "TelemetryBatchRequestContract",
    "MetricDefinitionCreateRequestContract",
    "MetricDefinitionUpdateRequestContract",
    "AlertRuleCreateRequestContract",
    "AlertRuleUpdateRequestContract",
    "AlertAcknowledgeRequestContract",
    "AlertResolveRequestContract",
    "TelemetryQueryRequestContract",
    "RealTimeSubscriptionRequestContract",

    # Response Contracts
    "TelemetryDataPointResponseContract",
    "TelemetryDataResponseContract",
    "MetricDefinitionResponseContract",
    "MetricDefinitionListResponseContract",
    "AlertRuleResponseContract",
    "AlertRuleListResponseContract",
    "AlertResponseContract",
    "AlertListResponseContract",
    "DeviceTelemetryStatsResponseContract",
    "TelemetryServiceStatsResponseContract",
    "RealTimeSubscriptionResponseContract",
    "IngestResponseContract",
    "ErrorResponseContract",

    # Factory
    "TelemetryTestDataFactory",

    # Builders
    "TelemetryDataPointBuilder",
    "AlertRuleCreateRequestBuilder",
    "TelemetryQueryRequestBuilder",
]
