"""
Telemetry Service Data Contract

Defines canonical data structures for telemetry service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for telemetry service test data.
Zero hardcoded data - all values generated through factory methods.
"""

import uuid
import secrets
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class DataType(str, Enum):
    """Telemetry data value types"""
    NUMERIC = "numeric"
    STRING = "string"
    BOOLEAN = "boolean"
    JSON = "json"
    BINARY = "binary"
    GEOLOCATION = "geolocation"
    TIMESTAMP = "timestamp"


class MetricType(str, Enum):
    """Metric aggregation types"""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    """Alert lifecycle states"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AggregationType(str, Enum):
    """Time-series aggregation functions"""
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    MEDIAN = "median"
    P95 = "p95"
    P99 = "p99"


class TimeRange(str, Enum):
    """Predefined time range options"""
    LAST_1H = "1h"
    LAST_6H = "6h"
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    LAST_90D = "90d"


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class TelemetryDataPointContract(BaseModel):
    """
    Contract: Single telemetry data point schema

    Represents one measurement from a device at a specific timestamp.
    """
    timestamp: datetime = Field(..., description="Measurement timestamp (ISO8601)")
    metric_name: str = Field(..., min_length=1, max_length=100, description="Metric identifier")
    value: Union[int, float, str, bool, Dict[str, Any]] = Field(..., description="Measured value")
    unit: Optional[str] = Field(None, max_length=20, description="Measurement unit")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Key-value tags")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    quality: Optional[int] = Field(100, ge=0, le=100, description="Data quality score")

    @field_validator('metric_name')
    @classmethod
    def validate_metric_name(cls, v: str) -> str:
        """Metric name must be non-empty and trimmed"""
        if not v or not v.strip():
            raise ValueError("metric_name cannot be empty or whitespace")
        return v.strip()

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Ensure tags is a dict"""
        return v or {}

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-12-18T10:00:00Z",
                "metric_name": "temperature",
                "value": 25.5,
                "unit": "celsius",
                "tags": {"location": "room_1", "sensor": "dht22"},
                "quality": 100
            }
        }


class TelemetryIngestRequestContract(BaseModel):
    """
    Contract: Single data point ingestion request

    Used for POST /api/v1/telemetry/devices/{device_id}/telemetry
    """
    timestamp: datetime = Field(..., description="Measurement timestamp")
    metric_name: str = Field(..., min_length=1, max_length=100)
    value: Union[int, float, str, bool, Dict[str, Any]] = Field(...)
    unit: Optional[str] = Field(None, max_length=20)
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    quality: Optional[int] = Field(100, ge=0, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-12-18T10:00:00Z",
                "metric_name": "cpu_usage",
                "value": 45.2,
                "unit": "percent"
            }
        }


class TelemetryBatchRequestContract(BaseModel):
    """
    Contract: Batch data point ingestion request

    Used for POST /api/v1/telemetry/devices/{device_id}/telemetry/batch
    """
    data_points: List[TelemetryDataPointContract] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of data points to ingest"
    )
    batch_id: Optional[str] = Field(None, description="Optional batch identifier for deduplication")
    compression: Optional[str] = Field(None, pattern="^(gzip|lz4)$", description="Compression type")

    @field_validator('data_points')
    @classmethod
    def validate_batch_size(cls, v: List[TelemetryDataPointContract]) -> List[TelemetryDataPointContract]:
        """Validate batch size limits"""
        if len(v) > 1000:
            raise ValueError("Maximum batch size is 1000 data points")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "data_points": [
                    {"timestamp": "2025-12-18T10:00:00Z", "metric_name": "temp", "value": 25.5},
                    {"timestamp": "2025-12-18T10:00:00Z", "metric_name": "humidity", "value": 60}
                ],
                "batch_id": "batch_001"
            }
        }


class MetricDefinitionCreateRequestContract(BaseModel):
    """
    Contract: Metric definition creation request

    Used for POST /api/v1/telemetry/metrics
    """
    name: str = Field(..., min_length=1, max_length=100, description="Unique metric name")
    description: Optional[str] = Field(None, max_length=500, description="Metric description")
    data_type: DataType = Field(..., description="Value data type")
    metric_type: MetricType = Field(default=MetricType.GAUGE, description="Metric aggregation type")
    unit: Optional[str] = Field(None, max_length=20, description="Measurement unit")
    min_value: Optional[float] = Field(None, description="Minimum valid value")
    max_value: Optional[float] = Field(None, description="Maximum valid value")
    retention_days: int = Field(default=90, ge=1, le=3650, description="Data retention period")
    aggregation_interval: int = Field(default=60, ge=1, le=86400, description="Aggregation interval seconds")
    tags: Optional[List[str]] = Field(default_factory=list, description="Categorization tags")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Metric name must be non-empty"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator('max_value')
    @classmethod
    def validate_max_greater_than_min(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure max_value > min_value if both specified"""
        min_val = info.data.get('min_value')
        if v is not None and min_val is not None and v <= min_val:
            raise ValueError("max_value must be greater than min_value")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "battery_level",
                "description": "Device battery percentage",
                "data_type": "numeric",
                "metric_type": "gauge",
                "unit": "percent",
                "min_value": 0,
                "max_value": 100,
                "retention_days": 90
            }
        }


class MetricDefinitionUpdateRequestContract(BaseModel):
    """
    Contract: Metric definition update request

    Partial update - only non-None fields are updated.
    """
    description: Optional[str] = Field(None, max_length=500)
    unit: Optional[str] = Field(None, max_length=20)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    retention_days: Optional[int] = Field(None, ge=1, le=3650)
    aggregation_interval: Optional[int] = Field(None, ge=1, le=86400)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertRuleCreateRequestContract(BaseModel):
    """
    Contract: Alert rule creation request

    Used for POST /api/v1/telemetry/alerts/rules
    """
    name: str = Field(..., min_length=1, max_length=200, description="Alert rule name")
    description: Optional[str] = Field(None, max_length=1000, description="Rule description")
    metric_name: str = Field(..., min_length=1, max_length=100, description="Metric to monitor")
    condition: str = Field(..., pattern="^(>|<|>=|<=|==|!=)$", description="Comparison operator")
    threshold_value: Union[int, float, str] = Field(..., description="Threshold value")
    evaluation_window: int = Field(default=300, ge=60, le=3600, description="Evaluation window seconds")
    trigger_count: int = Field(default=1, ge=1, le=100, description="Consecutive violations to trigger")
    level: AlertLevel = Field(default=AlertLevel.WARNING, description="Alert severity level")
    device_ids: Optional[List[str]] = Field(default_factory=list, description="Target device IDs")
    device_groups: Optional[List[str]] = Field(default_factory=list, description="Target device groups")
    device_filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Dynamic device filters")
    notification_channels: Optional[List[str]] = Field(default_factory=list, description="Notification channels")
    cooldown_minutes: int = Field(default=15, ge=1, le=1440, description="Cooldown between alerts")
    auto_resolve: bool = Field(default=True, description="Auto-resolve when condition clears")
    auto_resolve_timeout: int = Field(default=3600, ge=300, le=86400, description="Auto-resolve timeout seconds")
    enabled: bool = Field(default=True, description="Rule enabled status")
    tags: Optional[List[str]] = Field(default_factory=list, description="Rule tags")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Rule name must be non-empty"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "High CPU Usage",
                "description": "Alert when CPU exceeds 90%",
                "metric_name": "cpu_percent",
                "condition": ">",
                "threshold_value": 90,
                "level": "warning",
                "cooldown_minutes": 15,
                "auto_resolve": True
            }
        }


class AlertRuleUpdateRequestContract(BaseModel):
    """
    Contract: Alert rule update request

    Partial update - only non-None fields are updated.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    condition: Optional[str] = Field(None, pattern="^(>|<|>=|<=|==|!=)$")
    threshold_value: Optional[Union[int, float, str]] = None
    evaluation_window: Optional[int] = Field(None, ge=60, le=3600)
    trigger_count: Optional[int] = Field(None, ge=1, le=100)
    level: Optional[AlertLevel] = None
    device_ids: Optional[List[str]] = None
    notification_channels: Optional[List[str]] = None
    cooldown_minutes: Optional[int] = Field(None, ge=1, le=1440)
    auto_resolve: Optional[bool] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class AlertAcknowledgeRequestContract(BaseModel):
    """
    Contract: Alert acknowledgement request

    Used for PUT /api/v1/telemetry/alerts/{alert_id}/acknowledge
    """
    note: Optional[str] = Field(None, max_length=500, description="Acknowledgement note")

    class Config:
        json_schema_extra = {
            "example": {
                "note": "Investigating high CPU usage on production server"
            }
        }


class AlertResolveRequestContract(BaseModel):
    """
    Contract: Alert resolution request

    Used for PUT /api/v1/telemetry/alerts/{alert_id}/resolve
    """
    resolution_note: Optional[str] = Field(None, max_length=1000, description="Resolution notes")

    class Config:
        json_schema_extra = {
            "example": {
                "resolution_note": "Fixed memory leak in v2.3.1, CPU now normal"
            }
        }


class TelemetryQueryRequestContract(BaseModel):
    """
    Contract: Telemetry data query request

    Used for POST /api/v1/telemetry/query
    """
    devices: List[str] = Field(default_factory=list, description="Device IDs to query")
    metrics: List[str] = Field(..., min_length=1, description="Metric names to query")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")
    aggregation: Optional[AggregationType] = Field(None, description="Aggregation function")
    interval: Optional[int] = Field(None, ge=60, le=86400, description="Aggregation interval seconds")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tag filters")
    limit: int = Field(default=1000, ge=1, le=10000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Result offset")

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v: datetime, info) -> datetime:
        """Ensure end_time > start_time"""
        start = info.data.get('start_time')
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator('interval')
    @classmethod
    def validate_aggregation_interval(cls, v: Optional[int], info) -> Optional[int]:
        """Interval required if aggregation specified"""
        aggregation = info.data.get('aggregation')
        if aggregation and not v:
            raise ValueError("interval required when aggregation is specified")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "devices": ["device_001"],
                "metrics": ["temperature", "humidity"],
                "start_time": "2025-12-17T00:00:00Z",
                "end_time": "2025-12-18T00:00:00Z",
                "aggregation": "avg",
                "interval": 3600,
                "limit": 1000
            }
        }


class RealTimeSubscriptionRequestContract(BaseModel):
    """
    Contract: Real-time subscription request

    Used for POST /api/v1/telemetry/subscribe
    """
    device_ids: Optional[List[str]] = Field(default_factory=list, description="Devices to subscribe")
    metric_names: Optional[List[str]] = Field(default_factory=list, description="Metrics to subscribe")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Tag filters")
    filter_condition: Optional[str] = Field(None, description="Custom filter expression")
    max_frequency: int = Field(default=1000, ge=100, le=10000, description="Min ms between pushes")

    @field_validator('device_ids', 'metric_names')
    @classmethod
    def validate_at_least_one_filter(cls, v, info):
        """At least one filter required"""
        device_ids = info.data.get('device_ids', [])
        metric_names = info.data.get('metric_names', [])
        if info.field_name == 'metric_names' and not v and not device_ids:
            raise ValueError("At least one of device_ids or metric_names required")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "device_ids": ["device_001", "device_002"],
                "metric_names": ["temperature", "humidity"],
                "max_frequency": 1000
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class TelemetryDataPointResponseContract(BaseModel):
    """Contract: Single data point in query response"""
    timestamp: datetime = Field(..., description="Measurement timestamp")
    device_id: Optional[str] = Field(None, description="Source device ID")
    metric_name: str = Field(..., description="Metric name")
    value: Union[int, float, str, bool, Dict[str, Any]] = Field(..., description="Value")
    unit: Optional[str] = Field(None, description="Unit")
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    quality: int = Field(default=100, description="Quality score")


class TelemetryDataResponseContract(BaseModel):
    """
    Contract: Telemetry query response

    Returned by POST /api/v1/telemetry/query
    """
    device_id: str = Field(..., description="Device ID (or 'multiple')")
    metric_name: str = Field(..., description="Metric name (or 'multiple')")
    data_points: List[TelemetryDataPointResponseContract] = Field(..., description="Query results")
    count: int = Field(..., ge=0, description="Number of results")
    aggregation: Optional[str] = Field(None, description="Aggregation applied")
    interval: Optional[int] = Field(None, description="Aggregation interval")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")


class MetricDefinitionResponseContract(BaseModel):
    """
    Contract: Metric definition response

    Returned by metric definition endpoints.
    """
    metric_id: str = Field(..., description="Unique metric identifier")
    name: str = Field(..., description="Metric name")
    description: Optional[str] = Field(None, description="Description")
    data_type: str = Field(..., description="Value data type")
    metric_type: str = Field(..., description="Metric aggregation type")
    unit: Optional[str] = Field(None, description="Unit")
    min_value: Optional[float] = Field(None, description="Minimum value")
    max_value: Optional[float] = Field(None, description="Maximum value")
    retention_days: int = Field(..., description="Retention period")
    aggregation_interval: int = Field(..., description="Aggregation interval")
    tags: List[str] = Field(default_factory=list, description="Tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator user ID")


class MetricDefinitionListResponseContract(BaseModel):
    """
    Contract: Metric definitions list response
    """
    items: List[MetricDefinitionResponseContract] = Field(..., description="Metric definitions")
    count: int = Field(..., ge=0, description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class AlertRuleResponseContract(BaseModel):
    """
    Contract: Alert rule response
    """
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Description")
    metric_name: str = Field(..., description="Monitored metric")
    condition: str = Field(..., description="Comparison operator")
    threshold_value: str = Field(..., description="Threshold value")
    evaluation_window: int = Field(..., description="Evaluation window seconds")
    trigger_count: int = Field(..., description="Trigger count")
    level: str = Field(..., description="Alert level")
    device_ids: List[str] = Field(default_factory=list, description="Target devices")
    device_groups: List[str] = Field(default_factory=list, description="Target groups")
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")
    cooldown_minutes: int = Field(..., description="Cooldown minutes")
    auto_resolve: bool = Field(..., description="Auto-resolve enabled")
    auto_resolve_timeout: int = Field(..., description="Auto-resolve timeout")
    enabled: bool = Field(..., description="Rule enabled")
    tags: List[str] = Field(default_factory=list, description="Tags")
    total_triggers: int = Field(default=0, description="Total trigger count")
    last_triggered: Optional[datetime] = Field(None, description="Last trigger time")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator user ID")


class AlertRuleListResponseContract(BaseModel):
    """
    Contract: Alert rules list response
    """
    items: List[AlertRuleResponseContract] = Field(..., description="Alert rules")
    count: int = Field(..., ge=0, description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class AlertResponseContract(BaseModel):
    """
    Contract: Alert response
    """
    alert_id: str = Field(..., description="Unique alert identifier")
    rule_id: str = Field(..., description="Source rule ID")
    rule_name: str = Field(..., description="Rule name")
    device_id: str = Field(..., description="Affected device")
    metric_name: str = Field(..., description="Triggering metric")
    level: str = Field(..., description="Alert level")
    status: str = Field(..., description="Alert status")
    message: Optional[str] = Field(None, description="Alert message")
    current_value: str = Field(..., description="Triggering value")
    threshold_value: str = Field(..., description="Threshold value")
    triggered_at: datetime = Field(..., description="Trigger timestamp")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgement timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    acknowledged_by: Optional[str] = Field(None, description="Acknowledger user ID")
    resolved_by: Optional[str] = Field(None, description="Resolver user ID")
    resolution_note: Optional[str] = Field(None, description="Resolution notes")
    affected_devices_count: int = Field(default=1, description="Affected device count")
    tags: List[str] = Field(default_factory=list, description="Tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class AlertListResponseContract(BaseModel):
    """
    Contract: Alerts list response
    """
    alerts: List[AlertResponseContract] = Field(..., description="Alerts")
    count: int = Field(..., ge=0, description="Total count")
    active_count: int = Field(..., ge=0, description="Active alerts count")
    critical_count: int = Field(..., ge=0, description="Critical alerts count")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class DeviceTelemetryStatsResponseContract(BaseModel):
    """
    Contract: Device telemetry statistics response
    """
    device_id: str = Field(..., description="Device ID")
    total_metrics: int = Field(..., ge=0, description="Total distinct metrics")
    active_metrics: int = Field(..., ge=0, description="Active metrics")
    data_points_count: int = Field(..., ge=0, description="Total data points")
    last_update: Optional[datetime] = Field(None, description="Last data received")
    storage_size: int = Field(..., ge=0, description="Estimated storage bytes")
    avg_frequency: float = Field(..., ge=0, description="Avg points per minute")
    last_24h_points: int = Field(..., ge=0, description="Points in last 24h")
    last_24h_alerts: int = Field(..., ge=0, description="Alerts in last 24h")
    metrics_by_type: Dict[str, int] = Field(default_factory=dict, description="Metrics by type")
    top_metrics: List[Dict[str, Any]] = Field(default_factory=list, description="Top metrics by volume")


class TelemetryServiceStatsResponseContract(BaseModel):
    """
    Contract: Global telemetry service statistics response
    """
    total_devices: int = Field(..., ge=0, description="Total devices with telemetry")
    active_devices: int = Field(..., ge=0, description="Devices active in last 24h")
    total_metrics: int = Field(..., ge=0, description="Total distinct metrics")
    total_data_points: int = Field(..., ge=0, description="Total data points stored")
    points_per_second: float = Field(..., ge=0, description="Current ingestion rate")
    avg_latency: float = Field(..., ge=0, description="Average query latency ms")
    error_rate: float = Field(..., ge=0, le=100, description="Error rate percentage")
    last_24h_points: int = Field(..., ge=0, description="Points in last 24h")
    last_24h_alerts: int = Field(..., ge=0, description="Alerts in last 24h")
    devices_by_type: Dict[str, int] = Field(default_factory=dict, description="Devices by type")
    metrics_by_type: Dict[str, int] = Field(default_factory=dict, description="Metrics by type")
    data_by_hour: List[Dict[str, Any]] = Field(default_factory=list, description="Hourly data volumes")


class RealTimeSubscriptionResponseContract(BaseModel):
    """
    Contract: Real-time subscription response
    """
    subscription_id: str = Field(..., description="Subscription identifier")
    message: str = Field(default="Subscription created successfully", description="Status message")
    websocket_url: str = Field(..., description="WebSocket connection URL")
    device_ids: List[str] = Field(default_factory=list, description="Subscribed devices")
    metric_names: List[str] = Field(default_factory=list, description="Subscribed metrics")
    max_frequency: int = Field(..., description="Rate limit ms")


class IngestResponseContract(BaseModel):
    """
    Contract: Data ingestion response
    """
    success: bool = Field(default=True, description="Operation success")
    message: str = Field(default="Data point ingested successfully", description="Status message")
    device_id: str = Field(..., description="Target device ID")
    metric_name: Optional[str] = Field(None, description="Ingested metric")
    ingested_count: int = Field(default=1, ge=0, description="Points ingested")
    failed_count: int = Field(default=0, ge=0, description="Points failed")


class ErrorResponseContract(BaseModel):
    """
    Contract: Standard error response
    """
    success: bool = Field(default=False)
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    status_code: int = Field(..., description="HTTP status code")


# ============================================================================
# Test Data Factory
# ============================================================================

class TelemetryTestDataFactory:
    """
    Test data factory for telemetry_service.

    Zero hardcoded data - all values generated dynamically.
    Methods prefixed with 'make_' generate valid data.
    Methods prefixed with 'make_invalid_' generate invalid data.
    """

    # ==========================================================================
    # ID Generators
    # ==========================================================================

    @staticmethod
    def make_device_id() -> str:
        """Generate valid device ID"""
        return f"device_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_metric_id() -> str:
        """Generate valid metric definition ID"""
        return f"met_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_rule_id() -> str:
        """Generate valid alert rule ID"""
        return f"rule_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_alert_id() -> str:
        """Generate valid alert ID"""
        return f"alert_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_subscription_id() -> str:
        """Generate valid subscription ID"""
        return secrets.token_hex(16)

    @staticmethod
    def make_uuid() -> str:
        """Generate UUID string"""
        return str(uuid.uuid4())

    @staticmethod
    def make_correlation_id() -> str:
        """Generate correlation ID for tracing"""
        return f"corr_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:12]}"

    # ==========================================================================
    # String Generators
    # ==========================================================================

    @staticmethod
    def make_metric_name(prefix: str = "") -> str:
        """Generate unique metric name"""
        names = ["temperature", "humidity", "cpu_usage", "memory_usage", "battery_level",
                 "disk_usage", "network_in", "network_out", "error_count", "request_rate"]
        base = random.choice(names) if not prefix else prefix
        return f"{base}_{secrets.token_hex(4)}"

    @staticmethod
    def make_rule_name() -> str:
        """Generate unique alert rule name"""
        prefixes = ["High", "Low", "Critical", "Warning", "Abnormal"]
        metrics = ["CPU", "Memory", "Temperature", "Disk", "Network", "Battery"]
        return f"{random.choice(prefixes)} {random.choice(metrics)} Alert {secrets.token_hex(2)}"

    @staticmethod
    def make_description(length: int = 50) -> str:
        """Generate random description"""
        words = ["monitors", "tracks", "measures", "alerts", "reports", "analyzes"]
        return f"This metric {random.choice(words)} device performance {secrets.token_hex(4)}"

    @staticmethod
    def make_resolution_note() -> str:
        """Generate resolution note"""
        actions = ["Fixed memory leak", "Restarted service", "Scaled up resources",
                   "Applied hotfix", "Cleared cache", "Replaced sensor"]
        return f"{random.choice(actions)} - issue resolved {secrets.token_hex(2)}"

    @staticmethod
    def make_unit() -> str:
        """Generate random unit"""
        units = ["celsius", "fahrenheit", "percent", "bytes", "ms", "rpm", "volts", "amps"]
        return random.choice(units)

    @staticmethod
    def make_alphanumeric(length: int = 16) -> str:
        """Generate alphanumeric string"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))

    # ==========================================================================
    # Timestamp Generators
    # ==========================================================================

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
    def make_time_range(hours: int = 24) -> tuple:
        """Generate start_time and end_time tuple"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        return start_time, end_time

    # ==========================================================================
    # Numeric Generators
    # ==========================================================================

    @staticmethod
    def make_temperature() -> float:
        """Generate realistic temperature value (celsius)"""
        return round(random.uniform(-20.0, 50.0), 2)

    @staticmethod
    def make_humidity() -> float:
        """Generate realistic humidity value (percent)"""
        return round(random.uniform(0.0, 100.0), 2)

    @staticmethod
    def make_cpu_percent() -> float:
        """Generate CPU usage percentage"""
        return round(random.uniform(0.0, 100.0), 2)

    @staticmethod
    def make_memory_percent() -> float:
        """Generate memory usage percentage"""
        return round(random.uniform(0.0, 100.0), 2)

    @staticmethod
    def make_battery_level() -> int:
        """Generate battery level (0-100)"""
        return random.randint(0, 100)

    @staticmethod
    def make_positive_int(max_val: int = 1000) -> int:
        """Generate positive integer"""
        return random.randint(1, max_val)

    @staticmethod
    def make_threshold_value(metric_type: str = "cpu") -> float:
        """Generate realistic threshold value for alerts"""
        thresholds = {
            "cpu": random.uniform(70.0, 95.0),
            "memory": random.uniform(70.0, 90.0),
            "temperature": random.uniform(30.0, 80.0),
            "battery": random.uniform(10.0, 30.0),
            "disk": random.uniform(80.0, 95.0),
        }
        return round(thresholds.get(metric_type, random.uniform(50.0, 90.0)), 1)

    @staticmethod
    def make_quality_score() -> int:
        """Generate data quality score (0-100)"""
        return random.randint(80, 100)

    # ==========================================================================
    # Enum Generators
    # ==========================================================================

    @staticmethod
    def make_data_type() -> DataType:
        """Generate random data type"""
        return random.choice(list(DataType))

    @staticmethod
    def make_metric_type() -> MetricType:
        """Generate random metric type"""
        return random.choice(list(MetricType))

    @staticmethod
    def make_alert_level() -> AlertLevel:
        """Generate random alert level"""
        return random.choice(list(AlertLevel))

    @staticmethod
    def make_alert_status() -> AlertStatus:
        """Generate random alert status"""
        return random.choice(list(AlertStatus))

    @staticmethod
    def make_aggregation_type() -> AggregationType:
        """Generate random aggregation type"""
        return random.choice(list(AggregationType))

    @staticmethod
    def make_condition() -> str:
        """Generate random comparison condition"""
        return random.choice([">", "<", ">=", "<=", "==", "!="])

    # ==========================================================================
    # Tags and Metadata Generators
    # ==========================================================================

    @staticmethod
    def make_tags() -> Dict[str, str]:
        """Generate random tags dict"""
        tag_keys = ["location", "environment", "region", "type", "owner"]
        tag_values = ["prod", "staging", "dev", "us-east", "eu-west", "sensor", "gateway"]
        return {
            random.choice(tag_keys): random.choice(tag_values),
            "source": f"test_{secrets.token_hex(2)}"
        }

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate random metadata dict"""
        return {
            "version": f"1.{random.randint(0, 9)}.{random.randint(0, 99)}",
            "firmware": f"fw_{secrets.token_hex(4)}",
            "calibrated": random.choice([True, False]),
            "last_maintenance": TelemetryTestDataFactory.make_past_timestamp().isoformat()
        }

    @staticmethod
    def make_notification_channels() -> List[str]:
        """Generate notification channels list"""
        channels = ["email", "slack", "pagerduty", "webhook", "sms"]
        return random.sample(channels, k=random.randint(1, 3))

    @staticmethod
    def make_device_ids(count: int = 3) -> List[str]:
        """Generate list of device IDs"""
        return [TelemetryTestDataFactory.make_device_id() for _ in range(count)]

    @staticmethod
    def make_metric_tags() -> List[str]:
        """Generate metric categorization tags"""
        tags = ["system", "network", "storage", "sensor", "iot", "performance", "health"]
        return random.sample(tags, k=random.randint(1, 3))

    # ==========================================================================
    # Data Point Generators
    # ==========================================================================

    @staticmethod
    def make_data_point(**overrides) -> TelemetryDataPointContract:
        """Generate valid telemetry data point"""
        defaults = {
            "timestamp": TelemetryTestDataFactory.make_timestamp(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "value": TelemetryTestDataFactory.make_temperature(),
            "unit": "celsius",
            "tags": TelemetryTestDataFactory.make_tags(),
            "metadata": {},
            "quality": 100,
        }
        defaults.update(overrides)
        return TelemetryDataPointContract(**defaults)

    @staticmethod
    def make_data_point_numeric(**overrides) -> TelemetryDataPointContract:
        """Generate data point with numeric value"""
        return TelemetryTestDataFactory.make_data_point(
            value=TelemetryTestDataFactory.make_cpu_percent(),
            unit="percent",
            **overrides
        )

    @staticmethod
    def make_data_point_string(**overrides) -> TelemetryDataPointContract:
        """Generate data point with string value"""
        statuses = ["running", "idle", "stopped", "error", "maintenance"]
        return TelemetryTestDataFactory.make_data_point(
            metric_name="device_status",
            value=random.choice(statuses),
            unit=None,
            **overrides
        )

    @staticmethod
    def make_data_point_boolean(**overrides) -> TelemetryDataPointContract:
        """Generate data point with boolean value"""
        return TelemetryTestDataFactory.make_data_point(
            metric_name="is_online",
            value=random.choice([True, False]),
            unit=None,
            **overrides
        )

    @staticmethod
    def make_data_point_json(**overrides) -> TelemetryDataPointContract:
        """Generate data point with JSON value"""
        return TelemetryTestDataFactory.make_data_point(
            metric_name="location",
            value={
                "lat": round(random.uniform(-90, 90), 6),
                "lng": round(random.uniform(-180, 180), 6),
                "accuracy": random.randint(1, 50)
            },
            unit=None,
            **overrides
        )

    @staticmethod
    def make_batch_data_points(count: int = 10, **overrides) -> List[TelemetryDataPointContract]:
        """Generate batch of data points"""
        base_time = TelemetryTestDataFactory.make_timestamp()
        metric_name = overrides.pop("metric_name", TelemetryTestDataFactory.make_metric_name())
        return [
            TelemetryTestDataFactory.make_data_point(
                timestamp=base_time - timedelta(minutes=i),
                metric_name=metric_name,
                **overrides
            )
            for i in range(count)
        ]

    # ==========================================================================
    # Request Generators (Valid Data)
    # ==========================================================================

    @staticmethod
    def make_ingest_request(**overrides) -> TelemetryIngestRequestContract:
        """Generate valid ingestion request"""
        defaults = {
            "timestamp": TelemetryTestDataFactory.make_timestamp(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "value": TelemetryTestDataFactory.make_temperature(),
            "unit": "celsius",
            "tags": TelemetryTestDataFactory.make_tags(),
            "metadata": {},
            "quality": 100,
        }
        defaults.update(overrides)
        return TelemetryIngestRequestContract(**defaults)

    @staticmethod
    def make_batch_request(count: int = 10, **overrides) -> TelemetryBatchRequestContract:
        """Generate valid batch ingestion request"""
        data_points = TelemetryTestDataFactory.make_batch_data_points(count)
        defaults = {
            "data_points": data_points,
            "batch_id": f"batch_{secrets.token_hex(8)}",
            "compression": None,
        }
        defaults.update(overrides)
        return TelemetryBatchRequestContract(**defaults)

    @staticmethod
    def make_metric_definition_request(**overrides) -> MetricDefinitionCreateRequestContract:
        """Generate valid metric definition request"""
        defaults = {
            "name": TelemetryTestDataFactory.make_metric_name(),
            "description": TelemetryTestDataFactory.make_description(),
            "data_type": DataType.NUMERIC,
            "metric_type": MetricType.GAUGE,
            "unit": TelemetryTestDataFactory.make_unit(),
            "min_value": 0.0,
            "max_value": 100.0,
            "retention_days": 90,
            "aggregation_interval": 60,
            "tags": TelemetryTestDataFactory.make_metric_tags(),
            "metadata": {},
        }
        defaults.update(overrides)
        return MetricDefinitionCreateRequestContract(**defaults)

    @staticmethod
    def make_alert_rule_request(**overrides) -> AlertRuleCreateRequestContract:
        """Generate valid alert rule request"""
        defaults = {
            "name": TelemetryTestDataFactory.make_rule_name(),
            "description": TelemetryTestDataFactory.make_description(),
            "metric_name": "cpu_usage",
            "condition": ">",
            "threshold_value": TelemetryTestDataFactory.make_threshold_value("cpu"),
            "evaluation_window": 300,
            "trigger_count": 3,
            "level": AlertLevel.WARNING,
            "device_ids": [],
            "device_groups": [],
            "notification_channels": TelemetryTestDataFactory.make_notification_channels(),
            "cooldown_minutes": 15,
            "auto_resolve": True,
            "auto_resolve_timeout": 3600,
            "enabled": True,
            "tags": TelemetryTestDataFactory.make_metric_tags(),
        }
        defaults.update(overrides)
        return AlertRuleCreateRequestContract(**defaults)

    @staticmethod
    def make_query_request(**overrides) -> TelemetryQueryRequestContract:
        """Generate valid query request"""
        start_time, end_time = TelemetryTestDataFactory.make_time_range(24)
        defaults = {
            "devices": [TelemetryTestDataFactory.make_device_id()],
            "metrics": [TelemetryTestDataFactory.make_metric_name()],
            "start_time": start_time,
            "end_time": end_time,
            "aggregation": None,
            "interval": None,
            "filters": {},
            "limit": 1000,
            "offset": 0,
        }
        defaults.update(overrides)
        return TelemetryQueryRequestContract(**defaults)

    @staticmethod
    def make_query_request_with_aggregation(**overrides) -> TelemetryQueryRequestContract:
        """Generate query request with aggregation"""
        return TelemetryTestDataFactory.make_query_request(
            aggregation=AggregationType.AVG,
            interval=3600,
            **overrides
        )

    @staticmethod
    def make_subscription_request(**overrides) -> RealTimeSubscriptionRequestContract:
        """Generate valid subscription request"""
        defaults = {
            "device_ids": TelemetryTestDataFactory.make_device_ids(2),
            "metric_names": ["temperature", "humidity"],
            "tags": {},
            "filter_condition": None,
            "max_frequency": 1000,
        }
        defaults.update(overrides)
        return RealTimeSubscriptionRequestContract(**defaults)

    @staticmethod
    def make_acknowledge_request(**overrides) -> AlertAcknowledgeRequestContract:
        """Generate valid acknowledgement request"""
        defaults = {
            "note": f"Investigating issue {secrets.token_hex(4)}",
        }
        defaults.update(overrides)
        return AlertAcknowledgeRequestContract(**defaults)

    @staticmethod
    def make_resolve_request(**overrides) -> AlertResolveRequestContract:
        """Generate valid resolution request"""
        defaults = {
            "resolution_note": TelemetryTestDataFactory.make_resolution_note(),
        }
        defaults.update(overrides)
        return AlertResolveRequestContract(**defaults)

    # ==========================================================================
    # Response Generators
    # ==========================================================================

    @staticmethod
    def make_data_point_response(**overrides) -> Dict[str, Any]:
        """Generate data point response dict"""
        now = TelemetryTestDataFactory.make_timestamp()
        defaults = {
            "timestamp": now.isoformat(),
            "device_id": TelemetryTestDataFactory.make_device_id(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "value": TelemetryTestDataFactory.make_temperature(),
            "unit": "celsius",
            "tags": TelemetryTestDataFactory.make_tags(),
            "metadata": {},
            "quality": 100,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_telemetry_data_response(count: int = 10, **overrides) -> Dict[str, Any]:
        """Generate telemetry query response"""
        start_time, end_time = TelemetryTestDataFactory.make_time_range(24)
        device_id = TelemetryTestDataFactory.make_device_id()
        metric_name = TelemetryTestDataFactory.make_metric_name()
        data_points = [
            TelemetryTestDataFactory.make_data_point_response(
                device_id=device_id,
                metric_name=metric_name
            )
            for _ in range(count)
        ]
        defaults = {
            "device_id": device_id,
            "metric_name": metric_name,
            "data_points": data_points,
            "count": count,
            "aggregation": None,
            "interval": None,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_metric_definition_response(**overrides) -> Dict[str, Any]:
        """Generate metric definition response"""
        now = TelemetryTestDataFactory.make_timestamp()
        defaults = {
            "metric_id": TelemetryTestDataFactory.make_metric_id(),
            "name": TelemetryTestDataFactory.make_metric_name(),
            "description": TelemetryTestDataFactory.make_description(),
            "data_type": DataType.NUMERIC.value,
            "metric_type": MetricType.GAUGE.value,
            "unit": "celsius",
            "min_value": 0.0,
            "max_value": 100.0,
            "retention_days": 90,
            "aggregation_interval": 60,
            "tags": TelemetryTestDataFactory.make_metric_tags(),
            "metadata": {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": TelemetryTestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_alert_rule_response(**overrides) -> Dict[str, Any]:
        """Generate alert rule response"""
        now = TelemetryTestDataFactory.make_timestamp()
        defaults = {
            "rule_id": TelemetryTestDataFactory.make_rule_id(),
            "name": TelemetryTestDataFactory.make_rule_name(),
            "description": TelemetryTestDataFactory.make_description(),
            "metric_name": "cpu_usage",
            "condition": ">",
            "threshold_value": "90",
            "evaluation_window": 300,
            "trigger_count": 3,
            "level": AlertLevel.WARNING.value,
            "device_ids": [],
            "device_groups": [],
            "notification_channels": TelemetryTestDataFactory.make_notification_channels(),
            "cooldown_minutes": 15,
            "auto_resolve": True,
            "auto_resolve_timeout": 3600,
            "enabled": True,
            "tags": TelemetryTestDataFactory.make_metric_tags(),
            "total_triggers": 0,
            "last_triggered": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": TelemetryTestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_alert_response(**overrides) -> Dict[str, Any]:
        """Generate alert response"""
        now = TelemetryTestDataFactory.make_timestamp()
        defaults = {
            "alert_id": TelemetryTestDataFactory.make_alert_id(),
            "rule_id": TelemetryTestDataFactory.make_rule_id(),
            "rule_name": TelemetryTestDataFactory.make_rule_name(),
            "device_id": TelemetryTestDataFactory.make_device_id(),
            "metric_name": "cpu_usage",
            "level": AlertLevel.WARNING.value,
            "status": AlertStatus.ACTIVE.value,
            "message": "CPU usage exceeded threshold",
            "current_value": "95.5",
            "threshold_value": "90",
            "triggered_at": now.isoformat(),
            "acknowledged_at": None,
            "resolved_at": None,
            "acknowledged_by": None,
            "resolved_by": None,
            "resolution_note": None,
            "affected_devices_count": 1,
            "tags": TelemetryTestDataFactory.make_metric_tags(),
            "metadata": {},
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_device_stats_response(**overrides) -> Dict[str, Any]:
        """Generate device statistics response"""
        defaults = {
            "device_id": TelemetryTestDataFactory.make_device_id(),
            "total_metrics": random.randint(5, 20),
            "active_metrics": random.randint(3, 15),
            "data_points_count": random.randint(1000, 100000),
            "last_update": TelemetryTestDataFactory.make_timestamp().isoformat(),
            "storage_size": random.randint(100000, 10000000),
            "avg_frequency": round(random.uniform(0.1, 10.0), 2),
            "last_24h_points": random.randint(100, 10000),
            "last_24h_alerts": random.randint(0, 10),
            "metrics_by_type": {"gauge": 8, "counter": 4, "histogram": 2},
            "top_metrics": [
                {"name": "temperature", "points": 5000},
                {"name": "cpu_usage", "points": 3000},
            ],
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_service_stats_response(**overrides) -> Dict[str, Any]:
        """Generate service statistics response"""
        defaults = {
            "total_devices": random.randint(100, 10000),
            "active_devices": random.randint(50, 8000),
            "total_metrics": random.randint(20, 100),
            "total_data_points": random.randint(1000000, 100000000),
            "points_per_second": round(random.uniform(100, 10000), 2),
            "avg_latency": round(random.uniform(10, 100), 2),
            "error_rate": round(random.uniform(0, 5), 2),
            "last_24h_points": random.randint(100000, 10000000),
            "last_24h_alerts": random.randint(0, 100),
            "devices_by_type": {"sensor": 500, "gateway": 50, "controller": 20},
            "metrics_by_type": {"gauge": 40, "counter": 30, "histogram": 15},
            "data_by_hour": [{"hour": i, "points": random.randint(1000, 10000)} for i in range(24)],
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_subscription_response(**overrides) -> Dict[str, Any]:
        """Generate subscription response"""
        sub_id = TelemetryTestDataFactory.make_subscription_id()
        defaults = {
            "subscription_id": sub_id,
            "message": "Subscription created successfully",
            "websocket_url": f"/ws/telemetry/{sub_id}",
            "device_ids": TelemetryTestDataFactory.make_device_ids(2),
            "metric_names": ["temperature", "humidity"],
            "max_frequency": 1000,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_ingest_response(**overrides) -> Dict[str, Any]:
        """Generate ingestion response"""
        defaults = {
            "success": True,
            "message": "Data point ingested successfully",
            "device_id": TelemetryTestDataFactory.make_device_id(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "ingested_count": 1,
            "failed_count": 0,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_batch_ingest_response(total: int = 10, failed: int = 0, **overrides) -> Dict[str, Any]:
        """Generate batch ingestion response"""
        defaults = {
            "success": True,
            "message": "Batch ingested successfully",
            "device_id": TelemetryTestDataFactory.make_device_id(),
            "metric_name": None,
            "ingested_count": total - failed,
            "failed_count": failed,
        }
        defaults.update(overrides)
        return defaults

    # ==========================================================================
    # Invalid Data Generators (for negative testing)
    # ==========================================================================

    @staticmethod
    def make_invalid_device_id() -> str:
        """Generate invalid device ID (wrong format)"""
        return "invalid_device"

    @staticmethod
    def make_invalid_metric_name_empty() -> str:
        """Generate empty metric name"""
        return ""

    @staticmethod
    def make_invalid_metric_name_whitespace() -> str:
        """Generate whitespace-only metric name"""
        return "   "

    @staticmethod
    def make_invalid_metric_name_too_long() -> str:
        """Generate metric name exceeding max length"""
        return "x" * 101

    @staticmethod
    def make_invalid_timestamp_future() -> datetime:
        """Generate timestamp too far in future"""
        return datetime.now(timezone.utc) + timedelta(days=1)

    @staticmethod
    def make_invalid_timestamp_past() -> datetime:
        """Generate timestamp too far in past"""
        return datetime.now(timezone.utc) - timedelta(days=100)

    @staticmethod
    def make_invalid_quality_score_negative() -> int:
        """Generate negative quality score"""
        return -1

    @staticmethod
    def make_invalid_quality_score_over() -> int:
        """Generate quality score over 100"""
        return 101

    @staticmethod
    def make_invalid_condition() -> str:
        """Generate invalid condition operator"""
        return "invalid"

    @staticmethod
    def make_invalid_alert_level() -> str:
        """Generate invalid alert level"""
        return "invalid_level"

    @staticmethod
    def make_invalid_data_type() -> str:
        """Generate invalid data type"""
        return "invalid_type"

    @staticmethod
    def make_invalid_aggregation_type() -> str:
        """Generate invalid aggregation type"""
        return "invalid_agg"

    @staticmethod
    def make_invalid_batch_size_zero() -> int:
        """Generate zero batch size"""
        return 0

    @staticmethod
    def make_invalid_batch_size_exceeded() -> int:
        """Generate batch size exceeding limit"""
        return 1001

    @staticmethod
    def make_invalid_limit_zero() -> int:
        """Generate zero limit"""
        return 0

    @staticmethod
    def make_invalid_limit_negative() -> int:
        """Generate negative limit"""
        return -1

    @staticmethod
    def make_invalid_limit_exceeded() -> int:
        """Generate limit exceeding max"""
        return 10001

    @staticmethod
    def make_invalid_offset_negative() -> int:
        """Generate negative offset"""
        return -1

    @staticmethod
    def make_invalid_retention_days_zero() -> int:
        """Generate zero retention days"""
        return 0

    @staticmethod
    def make_invalid_retention_days_exceeded() -> int:
        """Generate retention days exceeding max"""
        return 3651

    @staticmethod
    def make_invalid_evaluation_window_too_small() -> int:
        """Generate evaluation window below minimum"""
        return 30

    @staticmethod
    def make_invalid_evaluation_window_too_large() -> int:
        """Generate evaluation window above maximum"""
        return 3601

    @staticmethod
    def make_invalid_cooldown_zero() -> int:
        """Generate zero cooldown"""
        return 0

    @staticmethod
    def make_invalid_cooldown_exceeded() -> int:
        """Generate cooldown exceeding max"""
        return 1441

    @staticmethod
    def make_invalid_frequency_too_low() -> int:
        """Generate frequency below minimum"""
        return 50

    @staticmethod
    def make_invalid_frequency_too_high() -> int:
        """Generate frequency above maximum"""
        return 10001

    @staticmethod
    def make_invalid_min_max_values() -> tuple:
        """Generate min > max (invalid)"""
        return 100.0, 50.0

    # ==========================================================================
    # Edge Case Generators
    # ==========================================================================

    @staticmethod
    def make_unicode_metric_name() -> str:
        """Generate metric name with unicode characters"""
        return f"temp_\u6e29\u5ea6_{secrets.token_hex(2)}"

    @staticmethod
    def make_special_chars_metric_name() -> str:
        """Generate metric name with special characters"""
        return f"metric.with-special_chars.{secrets.token_hex(2)}"

    @staticmethod
    def make_max_length_metric_name() -> str:
        """Generate metric name at max length (100 chars)"""
        return "x" * 100

    @staticmethod
    def make_min_length_metric_name() -> str:
        """Generate metric name at min length (1 char)"""
        return "x"

    @staticmethod
    def make_boundary_temperature_min() -> float:
        """Generate minimum boundary temperature"""
        return -273.15  # Absolute zero

    @staticmethod
    def make_boundary_temperature_max() -> float:
        """Generate maximum boundary temperature"""
        return 1000.0

    @staticmethod
    def make_boundary_percentage_min() -> float:
        """Generate minimum percentage"""
        return 0.0

    @staticmethod
    def make_boundary_percentage_max() -> float:
        """Generate maximum percentage"""
        return 100.0

    @staticmethod
    def make_large_batch_data_points(count: int = 1000) -> List[TelemetryDataPointContract]:
        """Generate maximum batch size data points"""
        return TelemetryTestDataFactory.make_batch_data_points(count)

    @staticmethod
    def make_empty_tags() -> Dict[str, str]:
        """Generate empty tags dict"""
        return {}

    @staticmethod
    def make_large_metadata() -> Dict[str, Any]:
        """Generate large metadata dict (near 10KB limit)"""
        return {"data": "x" * 9000, "timestamp": TelemetryTestDataFactory.make_timestamp_iso()}

    # ==========================================================================
    # Batch Generators
    # ==========================================================================

    # ==========================================================================
    # Dict Generators (for HTTP request bodies in integration tests)
    # ==========================================================================

    @staticmethod
    def make_data_point_dict(**overrides) -> Dict[str, Any]:
        """Generate data point as dict for API requests"""
        data_point = TelemetryTestDataFactory.make_data_point(**overrides)
        result = data_point.model_dump()
        # Convert datetime to ISO string for JSON serialization
        if isinstance(result.get("timestamp"), datetime):
            result["timestamp"] = result["timestamp"].isoformat()
        return result

    @staticmethod
    def make_batch_request_dict(**overrides) -> Dict[str, Any]:
        """Generate batch request as dict for API requests"""
        batch = TelemetryTestDataFactory.make_batch_request(**overrides)
        result = batch.model_dump()
        # Convert timestamps to ISO strings
        for dp in result.get("data_points", []):
            if isinstance(dp.get("timestamp"), datetime):
                dp["timestamp"] = dp["timestamp"].isoformat()
        return result

    @staticmethod
    def make_metric_definition_create_dict(**overrides) -> Dict[str, Any]:
        """Generate metric definition create request as dict"""
        metric_def = TelemetryTestDataFactory.make_metric_definition_request(**overrides)
        result = metric_def.model_dump()
        # Convert enums to values
        if hasattr(result.get("data_type"), "value"):
            result["data_type"] = result["data_type"].value
        if hasattr(result.get("metric_type"), "value"):
            result["metric_type"] = result["metric_type"].value
        return result

    @staticmethod
    def make_alert_rule_create_dict(**overrides) -> Dict[str, Any]:
        """Generate alert rule create request as dict"""
        rule = TelemetryTestDataFactory.make_alert_rule_request(**overrides)
        result = rule.model_dump()
        # Convert enums to values
        if hasattr(result.get("level"), "value"):
            result["level"] = result["level"].value
        return result

    @staticmethod
    def make_numeric_value() -> float:
        """Generate numeric value for data points"""
        return round(random.uniform(0.0, 100.0), 2)

    @staticmethod
    def make_string_value() -> str:
        """Generate string value for data points"""
        return f"status_{secrets.token_hex(4)}"

    @staticmethod
    def make_boolean_value() -> bool:
        """Generate boolean value for data points"""
        return random.choice([True, False])

    @staticmethod
    def make_device_id_list(count: int = 3) -> List[str]:
        """Generate list of device IDs"""
        return [TelemetryTestDataFactory.make_device_id() for _ in range(count)]

    @staticmethod
    def make_batch_device_ids(count: int = 5) -> List[str]:
        """Generate multiple device IDs"""
        return [TelemetryTestDataFactory.make_device_id() for _ in range(count)]

    @staticmethod
    def make_batch_metric_names(count: int = 5) -> List[str]:
        """Generate multiple metric names"""
        return [TelemetryTestDataFactory.make_metric_name() for _ in range(count)]

    @staticmethod
    def make_batch_alert_rules(count: int = 3) -> List[AlertRuleCreateRequestContract]:
        """Generate multiple alert rule requests"""
        return [TelemetryTestDataFactory.make_alert_rule_request() for _ in range(count)]

    @staticmethod
    def make_batch_metric_definitions(count: int = 3) -> List[MetricDefinitionCreateRequestContract]:
        """Generate multiple metric definition requests"""
        return [TelemetryTestDataFactory.make_metric_definition_request() for _ in range(count)]

    @staticmethod
    def make_multi_device_bulk_data(device_count: int = 3, points_per_device: int = 10) -> Dict[str, List[Dict]]:
        """Generate bulk data for multiple devices"""
        result = {}
        for _ in range(device_count):
            device_id = TelemetryTestDataFactory.make_device_id()
            result[device_id] = [
                TelemetryTestDataFactory.make_data_point().model_dump()
                for _ in range(points_per_device)
            ]
        return result


# ============================================================================
# Request Builders (Fluent API)
# ============================================================================

class TelemetryDataPointBuilder:
    """Builder for telemetry data points with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._timestamp = TelemetryTestDataFactory.make_timestamp()
        self._metric_name = TelemetryTestDataFactory.make_metric_name()
        self._value: Union[int, float, str, bool, Dict] = TelemetryTestDataFactory.make_temperature()
        self._unit: Optional[str] = "celsius"
        self._tags: Dict[str, str] = {}
        self._metadata: Dict[str, Any] = {}
        self._quality: int = 100

    def with_timestamp(self, timestamp: datetime) -> 'TelemetryDataPointBuilder':
        """Set custom timestamp"""
        self._timestamp = timestamp
        return self

    def with_metric_name(self, metric_name: str) -> 'TelemetryDataPointBuilder':
        """Set custom metric name"""
        self._metric_name = metric_name
        return self

    def with_value(self, value: Union[int, float, str, bool, Dict]) -> 'TelemetryDataPointBuilder':
        """Set custom value"""
        self._value = value
        return self

    def with_numeric_value(self, value: float) -> 'TelemetryDataPointBuilder':
        """Set numeric value"""
        self._value = value
        return self

    def with_string_value(self, value: str) -> 'TelemetryDataPointBuilder':
        """Set string value"""
        self._value = value
        return self

    def with_boolean_value(self, value: bool) -> 'TelemetryDataPointBuilder':
        """Set boolean value"""
        self._value = value
        return self

    def with_json_value(self, value: Dict[str, Any]) -> 'TelemetryDataPointBuilder':
        """Set JSON value"""
        self._value = value
        return self

    def with_unit(self, unit: str) -> 'TelemetryDataPointBuilder':
        """Set custom unit"""
        self._unit = unit
        return self

    def with_tags(self, tags: Dict[str, str]) -> 'TelemetryDataPointBuilder':
        """Set custom tags"""
        self._tags = tags
        return self

    def with_tag(self, key: str, value: str) -> 'TelemetryDataPointBuilder':
        """Add a single tag"""
        self._tags[key] = value
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'TelemetryDataPointBuilder':
        """Set custom metadata"""
        self._metadata = metadata
        return self

    def with_quality(self, quality: int) -> 'TelemetryDataPointBuilder':
        """Set custom quality score"""
        self._quality = quality
        return self

    def with_invalid_metric_name(self) -> 'TelemetryDataPointBuilder':
        """Set invalid metric name for negative testing"""
        self._metric_name = TelemetryTestDataFactory.make_invalid_metric_name_empty()
        return self

    def with_invalid_quality(self) -> 'TelemetryDataPointBuilder':
        """Set invalid quality for negative testing"""
        self._quality = TelemetryTestDataFactory.make_invalid_quality_score_negative()
        return self

    def build(self) -> TelemetryDataPointContract:
        """Build the data point contract"""
        return TelemetryDataPointContract(
            timestamp=self._timestamp,
            metric_name=self._metric_name,
            value=self._value,
            unit=self._unit,
            tags=self._tags,
            metadata=self._metadata,
            quality=self._quality,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(mode='json')


class AlertRuleCreateRequestBuilder:
    """Builder for alert rule creation requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._name = TelemetryTestDataFactory.make_rule_name()
        self._description: Optional[str] = None
        self._metric_name = "cpu_usage"
        self._condition = ">"
        self._threshold_value: Union[int, float, str] = 90
        self._evaluation_window = 300
        self._trigger_count = 3
        self._level = AlertLevel.WARNING
        self._device_ids: List[str] = []
        self._device_groups: List[str] = []
        self._notification_channels: List[str] = []
        self._cooldown_minutes = 15
        self._auto_resolve = True
        self._auto_resolve_timeout = 3600
        self._enabled = True
        self._tags: List[str] = []

    def with_name(self, name: str) -> 'AlertRuleCreateRequestBuilder':
        """Set custom name"""
        self._name = name
        return self

    def with_description(self, description: str) -> 'AlertRuleCreateRequestBuilder':
        """Set custom description"""
        self._description = description
        return self

    def with_metric_name(self, metric_name: str) -> 'AlertRuleCreateRequestBuilder':
        """Set custom metric name"""
        self._metric_name = metric_name
        return self

    def with_condition(self, condition: str) -> 'AlertRuleCreateRequestBuilder':
        """Set custom condition"""
        self._condition = condition
        return self

    def with_threshold(self, threshold: Union[int, float, str]) -> 'AlertRuleCreateRequestBuilder':
        """Set custom threshold"""
        self._threshold_value = threshold
        return self

    def with_level(self, level: AlertLevel) -> 'AlertRuleCreateRequestBuilder':
        """Set custom level"""
        self._level = level
        return self

    def with_critical_level(self) -> 'AlertRuleCreateRequestBuilder':
        """Set critical level"""
        self._level = AlertLevel.CRITICAL
        return self

    def with_warning_level(self) -> 'AlertRuleCreateRequestBuilder':
        """Set warning level"""
        self._level = AlertLevel.WARNING
        return self

    def with_device_ids(self, device_ids: List[str]) -> 'AlertRuleCreateRequestBuilder':
        """Set target device IDs"""
        self._device_ids = device_ids
        return self

    def with_notification_channels(self, channels: List[str]) -> 'AlertRuleCreateRequestBuilder':
        """Set notification channels"""
        self._notification_channels = channels
        return self

    def with_cooldown(self, minutes: int) -> 'AlertRuleCreateRequestBuilder':
        """Set cooldown minutes"""
        self._cooldown_minutes = minutes
        return self

    def with_auto_resolve(self, enabled: bool, timeout: int = 3600) -> 'AlertRuleCreateRequestBuilder':
        """Configure auto-resolve"""
        self._auto_resolve = enabled
        self._auto_resolve_timeout = timeout
        return self

    def disabled(self) -> 'AlertRuleCreateRequestBuilder':
        """Create disabled rule"""
        self._enabled = False
        return self

    def with_tags(self, tags: List[str]) -> 'AlertRuleCreateRequestBuilder':
        """Set tags"""
        self._tags = tags
        return self

    def with_invalid_condition(self) -> 'AlertRuleCreateRequestBuilder':
        """Set invalid condition for negative testing"""
        self._condition = TelemetryTestDataFactory.make_invalid_condition()
        return self

    def build(self) -> AlertRuleCreateRequestContract:
        """Build the alert rule request"""
        return AlertRuleCreateRequestContract(
            name=self._name,
            description=self._description,
            metric_name=self._metric_name,
            condition=self._condition,
            threshold_value=self._threshold_value,
            evaluation_window=self._evaluation_window,
            trigger_count=self._trigger_count,
            level=self._level,
            device_ids=self._device_ids,
            device_groups=self._device_groups,
            notification_channels=self._notification_channels,
            cooldown_minutes=self._cooldown_minutes,
            auto_resolve=self._auto_resolve,
            auto_resolve_timeout=self._auto_resolve_timeout,
            enabled=self._enabled,
            tags=self._tags,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(mode='json')


class TelemetryQueryRequestBuilder:
    """Builder for telemetry query requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        start, end = TelemetryTestDataFactory.make_time_range(24)
        self._devices: List[str] = []
        self._metrics: List[str] = [TelemetryTestDataFactory.make_metric_name()]
        self._start_time = start
        self._end_time = end
        self._aggregation: Optional[AggregationType] = None
        self._interval: Optional[int] = None
        self._filters: Dict[str, Any] = {}
        self._limit = 1000
        self._offset = 0

    def with_devices(self, device_ids: List[str]) -> 'TelemetryQueryRequestBuilder':
        """Set device IDs"""
        self._devices = device_ids
        return self

    def with_device(self, device_id: str) -> 'TelemetryQueryRequestBuilder':
        """Add single device ID"""
        self._devices.append(device_id)
        return self

    def with_metrics(self, metric_names: List[str]) -> 'TelemetryQueryRequestBuilder':
        """Set metric names"""
        self._metrics = metric_names
        return self

    def with_metric(self, metric_name: str) -> 'TelemetryQueryRequestBuilder':
        """Add single metric name"""
        self._metrics.append(metric_name)
        return self

    def with_time_range(self, start: datetime, end: datetime) -> 'TelemetryQueryRequestBuilder':
        """Set time range"""
        self._start_time = start
        self._end_time = end
        return self

    def with_last_hours(self, hours: int) -> 'TelemetryQueryRequestBuilder':
        """Set time range to last N hours"""
        self._end_time = datetime.now(timezone.utc)
        self._start_time = self._end_time - timedelta(hours=hours)
        return self

    def with_last_days(self, days: int) -> 'TelemetryQueryRequestBuilder':
        """Set time range to last N days"""
        self._end_time = datetime.now(timezone.utc)
        self._start_time = self._end_time - timedelta(days=days)
        return self

    def with_aggregation(self, agg_type: AggregationType, interval: int) -> 'TelemetryQueryRequestBuilder':
        """Set aggregation"""
        self._aggregation = agg_type
        self._interval = interval
        return self

    def with_avg_aggregation(self, interval: int = 3600) -> 'TelemetryQueryRequestBuilder':
        """Set AVG aggregation"""
        return self.with_aggregation(AggregationType.AVG, interval)

    def with_sum_aggregation(self, interval: int = 3600) -> 'TelemetryQueryRequestBuilder':
        """Set SUM aggregation"""
        return self.with_aggregation(AggregationType.SUM, interval)

    def with_filters(self, filters: Dict[str, Any]) -> 'TelemetryQueryRequestBuilder':
        """Set filters"""
        self._filters = filters
        return self

    def with_pagination(self, limit: int, offset: int) -> 'TelemetryQueryRequestBuilder':
        """Set pagination"""
        self._limit = limit
        self._offset = offset
        return self

    def build(self) -> TelemetryQueryRequestContract:
        """Build the query request"""
        return TelemetryQueryRequestContract(
            devices=self._devices,
            metrics=self._metrics,
            start_time=self._start_time,
            end_time=self._end_time,
            aggregation=self._aggregation,
            interval=self._interval,
            filters=self._filters,
            limit=self._limit,
            offset=self._offset,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(mode='json')


# ============================================================================
# Exports
# ============================================================================

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
