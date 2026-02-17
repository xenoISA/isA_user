"""
Telemetry Service Event Models

Pydantic models for all events published by Telemetry Service
"""

from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class TelemetryEventType(str, Enum):
    """
    Events published by telemetry_service.

    Stream: telemetry-stream
    Subjects: telemetry.>
    """
    DATA_RECEIVED = "telemetry.data.received"
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    METRIC_DEFINED = "metric.defined"
    ALERT_RULE_CREATED = "alert.rule.created"


class TelemetrySubscribedEventType(str, Enum):
    """Events that telemetry_service subscribes to from other services."""
    DEVICE_REGISTERED = "device.registered"


class TelemetryStreamConfig:
    """Stream configuration for telemetry_service"""
    STREAM_NAME = "telemetry-stream"
    SUBJECTS = ["telemetry.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "telemetry"

from typing import Optional, Dict, Any
from datetime import datetime


class TelemetryDataReceivedEvent(BaseModel):
    """Event published when telemetry data is received"""

    device_id: str = Field(..., description="Device ID")
    metrics_count: int = Field(..., description="Number of unique metrics")
    points_count: int = Field(..., description="Number of data points ingested")
    timestamp: str = Field(..., description="Ingestion timestamp")


class MetricDefinedEvent(BaseModel):
    """Event published when a metric definition is created"""

    metric_id: str = Field(..., description="Unique metric ID")
    name: str = Field(..., description="Metric name")
    data_type: str = Field(..., description="Data type (numeric/string/boolean/json)")
    metric_type: str = Field(..., description="Metric type (gauge/counter/histogram)")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    created_by: str = Field(..., description="User ID who created")
    timestamp: str = Field(..., description="Creation timestamp")


class AlertRuleCreatedEvent(BaseModel):
    """Event published when an alert rule is created"""

    rule_id: str = Field(..., description="Unique rule ID")
    name: str = Field(..., description="Rule name")
    metric_name: str = Field(..., description="Metric being monitored")
    condition: str = Field(..., description="Alert condition (e.g., >100, <0)")
    threshold_value: str = Field(..., description="Threshold value")
    level: str = Field(..., description="Alert level (info/warning/critical)")
    enabled: bool = Field(..., description="Is rule enabled")
    created_by: str = Field(..., description="User ID who created")
    timestamp: str = Field(..., description="Creation timestamp")


class AlertTriggeredEvent(BaseModel):
    """Event published when an alert is triggered"""

    alert_id: str = Field(..., description="Unique alert ID")
    rule_id: str = Field(..., description="Alert rule ID")
    rule_name: str = Field(..., description="Alert rule name")
    device_id: str = Field(..., description="Device ID")
    metric_name: str = Field(..., description="Metric name")
    level: str = Field(..., description="Alert level")
    current_value: str = Field(..., description="Current metric value")
    threshold_value: str = Field(..., description="Threshold value")
    timestamp: str = Field(..., description="Trigger timestamp")


class AlertResolvedEvent(BaseModel):
    """Event published when an alert is resolved"""

    alert_id: str = Field(..., description="Unique alert ID")
    rule_id: str = Field(..., description="Alert rule ID")
    rule_name: str = Field(..., description="Alert rule name")
    device_id: str = Field(..., description="Device ID")
    metric_name: str = Field(..., description="Metric name")
    level: str = Field(..., description="Alert level")
    resolved_by: str = Field(..., description="User ID who resolved")
    resolution_note: Optional[str] = Field(None, description="Resolution note")
    timestamp: str = Field(..., description="Resolution timestamp")
