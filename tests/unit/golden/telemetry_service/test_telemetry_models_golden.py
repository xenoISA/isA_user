"""
Unit Golden Tests: Telemetry Service Models

Tests model validation and serialization without external dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.telemetry_service.models import (
    # Enums
    DataType,
    MetricType,
    AlertLevel,
    AlertStatus,
    AggregationType,
    TimeRange,
    # Core Models
    TelemetryDataPoint,
    # Request Models
    TelemetryBatchRequest,
    MetricDefinitionRequest,
    AlertRuleRequest,
    QueryRequest,
    RealTimeSubscriptionRequest,
    # Response Models
    MetricDefinitionResponse,
    TelemetryDataResponse,
    AlertRuleResponse,
    AlertResponse,
    DeviceTelemetryStatsResponse,
    TelemetryStatsResponse,
    RealTimeDataResponse,
    AggregatedDataResponse,
    AlertListResponse,
)


# ==================
# Enum Tests
# ==================

class TestDataTypeEnum:
    """Test DataType enum values"""

    def test_data_type_values(self):
        """Test all data type enum values are defined"""
        assert DataType.NUMERIC.value == "numeric"
        assert DataType.STRING.value == "string"
        assert DataType.BOOLEAN.value == "boolean"
        assert DataType.JSON.value == "json"
        assert DataType.BINARY.value == "binary"
        assert DataType.GEOLOCATION.value == "geolocation"
        assert DataType.TIMESTAMP.value == "timestamp"

    def test_data_type_comparison(self):
        """Test data type comparison"""
        assert DataType.NUMERIC != DataType.STRING
        assert DataType.NUMERIC.value == "numeric"


class TestMetricTypeEnum:
    """Test MetricType enum values"""

    def test_metric_type_values(self):
        """Test all metric type enum values are defined"""
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.SUMMARY.value == "summary"

    def test_metric_type_comparison(self):
        """Test metric type comparison"""
        assert MetricType.GAUGE != MetricType.COUNTER
        assert MetricType.GAUGE.value == "gauge"


class TestAlertLevelEnum:
    """Test AlertLevel enum values"""

    def test_alert_level_values(self):
        """Test all alert level enum values are defined"""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"
        assert AlertLevel.EMERGENCY.value == "emergency"

    def test_alert_level_comparison(self):
        """Test alert level comparison"""
        assert AlertLevel.INFO != AlertLevel.CRITICAL
        assert AlertLevel.WARNING.value == "warning"


class TestAlertStatusEnum:
    """Test AlertStatus enum values"""

    def test_alert_status_values(self):
        """Test all alert status enum values are defined"""
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.SUPPRESSED.value == "suppressed"

    def test_alert_status_comparison(self):
        """Test alert status comparison"""
        assert AlertStatus.ACTIVE != AlertStatus.RESOLVED
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"


class TestAggregationTypeEnum:
    """Test AggregationType enum values"""

    def test_aggregation_type_values(self):
        """Test all aggregation type enum values are defined"""
        assert AggregationType.AVG.value == "avg"
        assert AggregationType.MIN.value == "min"
        assert AggregationType.MAX.value == "max"
        assert AggregationType.SUM.value == "sum"
        assert AggregationType.COUNT.value == "count"
        assert AggregationType.MEDIAN.value == "median"
        assert AggregationType.P95.value == "p95"
        assert AggregationType.P99.value == "p99"

    def test_aggregation_type_comparison(self):
        """Test aggregation type comparison"""
        assert AggregationType.AVG != AggregationType.MAX
        assert AggregationType.SUM.value == "sum"


class TestTimeRangeEnum:
    """Test TimeRange enum values"""

    def test_time_range_values(self):
        """Test all time range enum values are defined"""
        assert TimeRange.LAST_HOUR.value == "1h"
        assert TimeRange.LAST_6_HOURS.value == "6h"
        assert TimeRange.LAST_24_HOURS.value == "24h"
        assert TimeRange.LAST_7_DAYS.value == "7d"
        assert TimeRange.LAST_30_DAYS.value == "30d"
        assert TimeRange.LAST_90_DAYS.value == "90d"


# ==================
# Core Model Tests
# ==================

class TestTelemetryDataPoint:
    """Test TelemetryDataPoint model"""

    def test_data_point_creation_with_numeric_value(self):
        """Test creating data point with numeric value"""
        now = datetime.now(timezone.utc)

        data_point = TelemetryDataPoint(
            timestamp=now,
            metric_name="cpu_usage",
            value=75.5,
            unit="percent",
            tags={"device": "sensor_01", "location": "factory"},
            metadata={"sensor_type": "cpu"}
        )

        assert data_point.timestamp == now
        assert data_point.metric_name == "cpu_usage"
        assert data_point.value == 75.5
        assert data_point.unit == "percent"
        assert data_point.tags["device"] == "sensor_01"
        assert data_point.metadata["sensor_type"] == "cpu"

    def test_data_point_creation_with_string_value(self):
        """Test creating data point with string value"""
        now = datetime.now(timezone.utc)

        data_point = TelemetryDataPoint(
            timestamp=now,
            metric_name="system_status",
            value="healthy"
        )

        assert data_point.metric_name == "system_status"
        assert data_point.value == "healthy"
        assert data_point.unit is None
        assert data_point.tags == {}
        assert data_point.metadata == {}

    def test_data_point_creation_with_boolean_value(self):
        """Test creating data point with boolean value"""
        now = datetime.now(timezone.utc)

        data_point = TelemetryDataPoint(
            timestamp=now,
            metric_name="door_open",
            value=True
        )

        assert data_point.metric_name == "door_open"
        assert data_point.value is True

    def test_data_point_creation_with_dict_value(self):
        """Test creating data point with dict value"""
        now = datetime.now(timezone.utc)

        data_point = TelemetryDataPoint(
            timestamp=now,
            metric_name="device_info",
            value={"model": "sensor_v2", "firmware": "1.2.3"}
        )

        assert data_point.metric_name == "device_info"
        assert isinstance(data_point.value, dict)
        assert data_point.value["model"] == "sensor_v2"

    def test_data_point_metric_name_validation(self):
        """Test metric name length validation"""
        now = datetime.now(timezone.utc)

        # Test minimum length (empty string should fail)
        with pytest.raises(ValidationError) as exc_info:
            TelemetryDataPoint(
                timestamp=now,
                metric_name="",
                value=100
            )
        errors = exc_info.value.errors()
        assert any("metric_name" in str(err["loc"]) for err in errors)

        # Test maximum length (>100 characters)
        with pytest.raises(ValidationError):
            TelemetryDataPoint(
                timestamp=now,
                metric_name="a" * 101,
                value=100
            )

    def test_data_point_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            TelemetryDataPoint(metric_name="test")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "timestamp" in missing_fields
        assert "value" in missing_fields


# ==================
# Request Model Tests
# ==================

class TestTelemetryBatchRequest:
    """Test TelemetryBatchRequest model"""

    def test_batch_request_creation(self):
        """Test creating batch request with multiple data points"""
        now = datetime.now(timezone.utc)

        data_points = [
            TelemetryDataPoint(timestamp=now, metric_name="temp", value=25.5),
            TelemetryDataPoint(timestamp=now, metric_name="humidity", value=60.0),
        ]

        request = TelemetryBatchRequest(
            data_points=data_points,
            compression="gzip",
            batch_id="batch_123"
        )

        assert len(request.data_points) == 2
        assert request.compression == "gzip"
        assert request.batch_id == "batch_123"

    def test_batch_request_defaults(self):
        """Test batch request with default values"""
        now = datetime.now(timezone.utc)

        data_points = [
            TelemetryDataPoint(timestamp=now, metric_name="test", value=1),
        ]

        request = TelemetryBatchRequest(data_points=data_points)

        assert request.compression is None
        assert request.batch_id is None

    def test_batch_request_min_items_validation(self):
        """Test batch request requires at least one data point"""
        with pytest.raises(ValidationError) as exc_info:
            TelemetryBatchRequest(data_points=[])

        errors = exc_info.value.errors()
        assert any("data_points" in str(err["loc"]) for err in errors)

    def test_batch_request_max_items_validation(self):
        """Test batch request maximum items validation"""
        now = datetime.now(timezone.utc)

        # Create 1001 data points (exceeds max of 1000)
        data_points = [
            TelemetryDataPoint(timestamp=now, metric_name=f"metric_{i}", value=i)
            for i in range(1001)
        ]

        with pytest.raises(ValidationError) as exc_info:
            TelemetryBatchRequest(data_points=data_points)

        errors = exc_info.value.errors()
        assert any("data_points" in str(err["loc"]) for err in errors)


class TestMetricDefinitionRequest:
    """Test MetricDefinitionRequest model"""

    def test_metric_definition_request_creation(self):
        """Test creating metric definition request with all fields"""
        request = MetricDefinitionRequest(
            name="cpu_temperature",
            description="CPU temperature in celsius",
            data_type=DataType.NUMERIC,
            metric_type=MetricType.GAUGE,
            unit="celsius",
            min_value=0.0,
            max_value=100.0,
            retention_days=90,
            aggregation_interval=60,
            tags=["cpu", "temperature"],
            metadata={"sensor_type": "thermal"}
        )

        assert request.name == "cpu_temperature"
        assert request.description == "CPU temperature in celsius"
        assert request.data_type == DataType.NUMERIC
        assert request.metric_type == MetricType.GAUGE
        assert request.unit == "celsius"
        assert request.min_value == 0.0
        assert request.max_value == 100.0
        assert request.retention_days == 90
        assert request.aggregation_interval == 60
        assert request.tags == ["cpu", "temperature"]

    def test_metric_definition_request_defaults(self):
        """Test metric definition request with default values"""
        request = MetricDefinitionRequest(
            name="test_metric",
            data_type=DataType.NUMERIC
        )

        assert request.metric_type == MetricType.GAUGE
        assert request.retention_days == 90
        assert request.aggregation_interval == 60
        assert request.tags == []
        assert request.metadata == {}

    def test_metric_definition_request_validation(self):
        """Test metric definition request field validations"""
        # Test name length
        with pytest.raises(ValidationError):
            MetricDefinitionRequest(
                name="",
                data_type=DataType.NUMERIC
            )

        with pytest.raises(ValidationError):
            MetricDefinitionRequest(
                name="a" * 101,
                data_type=DataType.NUMERIC
            )

        # Test retention_days range
        with pytest.raises(ValidationError):
            MetricDefinitionRequest(
                name="test",
                data_type=DataType.NUMERIC,
                retention_days=0
            )

        with pytest.raises(ValidationError):
            MetricDefinitionRequest(
                name="test",
                data_type=DataType.NUMERIC,
                retention_days=3651
            )

        # Test aggregation_interval range
        with pytest.raises(ValidationError):
            MetricDefinitionRequest(
                name="test",
                data_type=DataType.NUMERIC,
                aggregation_interval=0
            )

        with pytest.raises(ValidationError):
            MetricDefinitionRequest(
                name="test",
                data_type=DataType.NUMERIC,
                aggregation_interval=86401
            )


class TestAlertRuleRequest:
    """Test AlertRuleRequest model"""

    def test_alert_rule_request_creation_with_all_fields(self):
        """Test creating alert rule request with all fields"""
        request = AlertRuleRequest(
            name="High CPU Usage Alert",
            description="Triggers when CPU usage exceeds 80%",
            metric_name="cpu_usage",
            condition="> 80",
            threshold_value=80.0,
            evaluation_window=300,
            trigger_count=3,
            level=AlertLevel.WARNING,
            device_ids=["device_001", "device_002"],
            device_groups=["production", "critical"],
            device_filters={"location": "datacenter_1"},
            notification_channels=["email", "slack"],
            cooldown_minutes=15,
            auto_resolve=True,
            auto_resolve_timeout=3600,
            enabled=True,
            tags=["cpu", "performance"]
        )

        assert request.name == "High CPU Usage Alert"
        assert request.description == "Triggers when CPU usage exceeds 80%"
        assert request.metric_name == "cpu_usage"
        assert request.condition == "> 80"
        assert request.threshold_value == 80.0
        assert request.evaluation_window == 300
        assert request.trigger_count == 3
        assert request.level == AlertLevel.WARNING
        assert len(request.device_ids) == 2
        assert len(request.device_groups) == 2
        assert request.notification_channels == ["email", "slack"]
        assert request.cooldown_minutes == 15
        assert request.auto_resolve is True
        assert request.enabled is True

    def test_alert_rule_request_defaults(self):
        """Test alert rule request with default values"""
        request = AlertRuleRequest(
            name="Test Alert",
            metric_name="test_metric",
            condition="> 100",
            threshold_value=100
        )

        assert request.evaluation_window == 300
        assert request.trigger_count == 1
        assert request.level == AlertLevel.WARNING
        assert request.device_ids == []
        assert request.device_groups == []
        assert request.device_filters == {}
        assert request.notification_channels == []
        assert request.cooldown_minutes == 15
        assert request.auto_resolve is True
        assert request.auto_resolve_timeout == 3600
        assert request.enabled is True
        assert request.tags == []

    def test_alert_rule_request_validation(self):
        """Test alert rule request field validations"""
        # Test name length
        with pytest.raises(ValidationError):
            AlertRuleRequest(
                name="",
                metric_name="test",
                condition="> 100",
                threshold_value=100
            )

        # Test evaluation_window range
        with pytest.raises(ValidationError):
            AlertRuleRequest(
                name="test",
                metric_name="test",
                condition="> 100",
                threshold_value=100,
                evaluation_window=59
            )

        with pytest.raises(ValidationError):
            AlertRuleRequest(
                name="test",
                metric_name="test",
                condition="> 100",
                threshold_value=100,
                evaluation_window=3601
            )

        # Test trigger_count range
        with pytest.raises(ValidationError):
            AlertRuleRequest(
                name="test",
                metric_name="test",
                condition="> 100",
                threshold_value=100,
                trigger_count=0
            )

        with pytest.raises(ValidationError):
            AlertRuleRequest(
                name="test",
                metric_name="test",
                condition="> 100",
                threshold_value=100,
                trigger_count=101
            )

    def test_alert_rule_request_with_string_threshold(self):
        """Test alert rule request with string threshold value"""
        request = AlertRuleRequest(
            name="Status Alert",
            metric_name="system_status",
            condition="== 'error'",
            threshold_value="error"
        )

        assert request.threshold_value == "error"
        assert isinstance(request.threshold_value, str)


class TestQueryRequest:
    """Test QueryRequest model"""

    def test_query_request_creation_with_all_fields(self):
        """Test creating query request with all fields"""
        start = datetime.now(timezone.utc) - timedelta(hours=1)
        end = datetime.now(timezone.utc)

        request = QueryRequest(
            devices=["device_001", "device_002"],
            metrics=["cpu_usage", "memory_usage"],
            start_time=start,
            end_time=end,
            aggregation=AggregationType.AVG,
            interval=300,
            filters={"location": "datacenter_1"},
            limit=500,
            offset=0
        )

        assert len(request.devices) == 2
        assert len(request.metrics) == 2
        assert request.start_time == start
        assert request.end_time == end
        assert request.aggregation == AggregationType.AVG
        assert request.interval == 300
        assert request.filters == {"location": "datacenter_1"}
        assert request.limit == 500
        assert request.offset == 0

    def test_query_request_defaults(self):
        """Test query request with default values"""
        start = datetime.now(timezone.utc) - timedelta(hours=1)
        end = datetime.now(timezone.utc)

        request = QueryRequest(
            metrics=["cpu_usage"],
            start_time=start,
            end_time=end
        )

        assert request.devices == []
        assert request.aggregation is None
        assert request.interval is None
        assert request.filters == {}
        assert request.limit == 1000
        assert request.offset == 0

    def test_query_request_validation(self):
        """Test query request field validations"""
        start = datetime.now(timezone.utc) - timedelta(hours=1)
        end = datetime.now(timezone.utc)

        # Test metrics min_items
        with pytest.raises(ValidationError):
            QueryRequest(
                metrics=[],
                start_time=start,
                end_time=end
            )

        # Test interval range
        with pytest.raises(ValidationError):
            QueryRequest(
                metrics=["test"],
                start_time=start,
                end_time=end,
                interval=59
            )

        with pytest.raises(ValidationError):
            QueryRequest(
                metrics=["test"],
                start_time=start,
                end_time=end,
                interval=86401
            )

        # Test limit range
        with pytest.raises(ValidationError):
            QueryRequest(
                metrics=["test"],
                start_time=start,
                end_time=end,
                limit=0
            )

        with pytest.raises(ValidationError):
            QueryRequest(
                metrics=["test"],
                start_time=start,
                end_time=end,
                limit=10001
            )

        # Test offset range
        with pytest.raises(ValidationError):
            QueryRequest(
                metrics=["test"],
                start_time=start,
                end_time=end,
                offset=-1
            )


class TestRealTimeSubscriptionRequest:
    """Test RealTimeSubscriptionRequest model"""

    def test_realtime_subscription_request_creation(self):
        """Test creating real-time subscription request"""
        request = RealTimeSubscriptionRequest(
            device_ids=["device_001"],
            metric_names=["cpu_usage", "memory_usage"],
            tags={"location": "datacenter_1"},
            filter_condition="value > 80",
            max_frequency=1000
        )

        assert len(request.device_ids) == 1
        assert len(request.metric_names) == 2
        assert request.tags == {"location": "datacenter_1"}
        assert request.filter_condition == "value > 80"
        assert request.max_frequency == 1000

    def test_realtime_subscription_request_defaults(self):
        """Test real-time subscription request with default values"""
        request = RealTimeSubscriptionRequest()

        assert request.device_ids == []
        assert request.metric_names == []
        assert request.tags == {}
        assert request.filter_condition is None
        assert request.max_frequency == 1000

    def test_realtime_subscription_request_validation(self):
        """Test real-time subscription request field validations"""
        # Test max_frequency range
        with pytest.raises(ValidationError):
            RealTimeSubscriptionRequest(max_frequency=99)

        with pytest.raises(ValidationError):
            RealTimeSubscriptionRequest(max_frequency=10001)


# ==================
# Response Model Tests
# ==================

class TestMetricDefinitionResponse:
    """Test MetricDefinitionResponse model"""

    def test_metric_definition_response_creation(self):
        """Test creating metric definition response"""
        now = datetime.now(timezone.utc)

        response = MetricDefinitionResponse(
            metric_id="metric_123",
            name="cpu_temperature",
            description="CPU temperature in celsius",
            data_type=DataType.NUMERIC,
            metric_type=MetricType.GAUGE,
            unit="celsius",
            min_value=0.0,
            max_value=100.0,
            retention_days=90,
            aggregation_interval=60,
            tags=["cpu", "temperature"],
            metadata={"sensor_type": "thermal"},
            created_at=now,
            updated_at=now,
            created_by="user_123"
        )

        assert response.metric_id == "metric_123"
        assert response.name == "cpu_temperature"
        assert response.data_type == DataType.NUMERIC
        assert response.metric_type == MetricType.GAUGE
        assert response.unit == "celsius"
        assert response.created_by == "user_123"


class TestTelemetryDataResponse:
    """Test TelemetryDataResponse model"""

    def test_telemetry_data_response_creation(self):
        """Test creating telemetry data response"""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)

        data_points = [
            TelemetryDataPoint(timestamp=now, metric_name="cpu_usage", value=75.5),
            TelemetryDataPoint(timestamp=now, metric_name="cpu_usage", value=80.0),
        ]

        response = TelemetryDataResponse(
            device_id="device_001",
            metric_name="cpu_usage",
            data_points=data_points,
            count=2,
            aggregation=AggregationType.AVG,
            interval=300,
            start_time=start,
            end_time=now
        )

        assert response.device_id == "device_001"
        assert response.metric_name == "cpu_usage"
        assert len(response.data_points) == 2
        assert response.count == 2
        assert response.aggregation == AggregationType.AVG
        assert response.interval == 300

    def test_telemetry_data_response_without_aggregation(self):
        """Test telemetry data response without aggregation"""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)

        data_points = [
            TelemetryDataPoint(timestamp=now, metric_name="temp", value=25.5)
        ]

        response = TelemetryDataResponse(
            device_id="device_001",
            metric_name="temp",
            data_points=data_points,
            count=1,
            aggregation=None,
            interval=None,
            start_time=start,
            end_time=now
        )

        assert response.aggregation is None
        assert response.interval is None


class TestAlertRuleResponse:
    """Test AlertRuleResponse model"""

    def test_alert_rule_response_creation_with_all_fields(self):
        """Test creating alert rule response with all fields"""
        now = datetime.now(timezone.utc)

        response = AlertRuleResponse(
            rule_id="rule_123",
            name="High CPU Usage Alert",
            description="Triggers when CPU usage exceeds 80%",
            metric_name="cpu_usage",
            condition="> 80",
            threshold_value=80.0,
            evaluation_window=300,
            trigger_count=3,
            level=AlertLevel.WARNING,
            device_ids=["device_001"],
            device_groups=["production"],
            device_filters={"location": "datacenter_1"},
            notification_channels=["email"],
            cooldown_minutes=15,
            auto_resolve=True,
            auto_resolve_timeout=3600,
            enabled=True,
            tags=["cpu"],
            total_triggers=42,
            last_triggered=now,
            created_at=now,
            updated_at=now,
            created_by="user_123"
        )

        assert response.rule_id == "rule_123"
        assert response.name == "High CPU Usage Alert"
        assert response.metric_name == "cpu_usage"
        assert response.level == AlertLevel.WARNING
        assert response.total_triggers == 42
        assert response.last_triggered == now
        assert response.created_by == "user_123"

    def test_alert_rule_response_defaults(self):
        """Test alert rule response with default values"""
        now = datetime.now(timezone.utc)

        response = AlertRuleResponse(
            rule_id="rule_123",
            name="Test Alert",
            description="Test alert description",
            metric_name="test_metric",
            condition="> 100",
            threshold_value=100,
            evaluation_window=300,
            trigger_count=1,
            level=AlertLevel.WARNING,
            device_ids=[],
            device_groups=[],
            device_filters={},
            notification_channels=[],
            cooldown_minutes=15,
            auto_resolve=True,
            auto_resolve_timeout=3600,
            enabled=True,
            tags=[],
            created_at=now,
            updated_at=now,
            created_by="user_123"
        )

        assert response.total_triggers == 0
        assert response.last_triggered is None


class TestAlertResponse:
    """Test AlertResponse model"""

    def test_alert_response_creation_with_all_fields(self):
        """Test creating alert response with all fields"""
        now = datetime.now(timezone.utc)

        response = AlertResponse(
            alert_id="alert_123",
            rule_id="rule_456",
            rule_name="High CPU Usage",
            device_id="device_001",
            metric_name="cpu_usage",
            level=AlertLevel.WARNING,
            status=AlertStatus.ACTIVE,
            message="CPU usage exceeded threshold",
            current_value=85.5,
            threshold_value=80.0,
            triggered_at=now,
            acknowledged_at=now + timedelta(minutes=5),
            resolved_at=now + timedelta(hours=1),
            auto_resolve_at=now + timedelta(hours=2),
            acknowledged_by="user_123",
            resolved_by="user_123",
            resolution_note="Issue resolved",
            affected_devices_count=1,
            tags=["cpu", "performance"],
            metadata={"datacenter": "dc1"}
        )

        assert response.alert_id == "alert_123"
        assert response.rule_id == "rule_456"
        assert response.rule_name == "High CPU Usage"
        assert response.device_id == "device_001"
        assert response.level == AlertLevel.WARNING
        assert response.status == AlertStatus.ACTIVE
        assert response.current_value == 85.5
        assert response.threshold_value == 80.0
        assert response.acknowledged_by == "user_123"
        assert response.resolved_by == "user_123"
        assert response.resolution_note == "Issue resolved"

    def test_alert_response_defaults(self):
        """Test alert response with default values"""
        now = datetime.now(timezone.utc)

        response = AlertResponse(
            alert_id="alert_123",
            rule_id="rule_456",
            rule_name="Test Alert",
            device_id="device_001",
            metric_name="test_metric",
            level=AlertLevel.INFO,
            status=AlertStatus.ACTIVE,
            message="Test alert message",
            current_value=100,
            threshold_value=90,
            triggered_at=now,
            tags=[],
            metadata={}
        )

        assert response.acknowledged_at is None
        assert response.resolved_at is None
        assert response.auto_resolve_at is None
        assert response.acknowledged_by is None
        assert response.resolved_by is None
        assert response.resolution_note is None
        assert response.affected_devices_count == 1

    def test_alert_response_with_string_values(self):
        """Test alert response with string threshold values"""
        now = datetime.now(timezone.utc)

        response = AlertResponse(
            alert_id="alert_123",
            rule_id="rule_456",
            rule_name="Status Alert",
            device_id="device_001",
            metric_name="system_status",
            level=AlertLevel.ERROR,
            status=AlertStatus.ACTIVE,
            message="System status is error",
            current_value="error",
            threshold_value="error",
            triggered_at=now,
            tags=[],
            metadata={}
        )

        assert response.current_value == "error"
        assert response.threshold_value == "error"
        assert isinstance(response.current_value, str)


class TestDeviceTelemetryStatsResponse:
    """Test DeviceTelemetryStatsResponse model"""

    def test_device_telemetry_stats_response_creation(self):
        """Test creating device telemetry stats response"""
        now = datetime.now(timezone.utc)

        response = DeviceTelemetryStatsResponse(
            device_id="device_001",
            total_metrics=10,
            active_metrics=8,
            data_points_count=1000,
            last_update=now,
            storage_size=1048576,
            avg_frequency=10.5,
            last_24h_points=500,
            last_24h_alerts=3,
            metrics_by_type={"gauge": 5, "counter": 3, "histogram": 2},
            top_metrics=[
                {"name": "cpu_usage", "count": 200},
                {"name": "memory_usage", "count": 180}
            ]
        )

        assert response.device_id == "device_001"
        assert response.total_metrics == 10
        assert response.active_metrics == 8
        assert response.data_points_count == 1000
        assert response.last_update == now
        assert response.storage_size == 1048576
        assert response.avg_frequency == 10.5
        assert response.last_24h_points == 500
        assert response.last_24h_alerts == 3
        assert response.metrics_by_type["gauge"] == 5
        assert len(response.top_metrics) == 2

    def test_device_telemetry_stats_response_without_last_update(self):
        """Test device telemetry stats response without last update"""
        response = DeviceTelemetryStatsResponse(
            device_id="device_001",
            total_metrics=0,
            active_metrics=0,
            data_points_count=0,
            last_update=None,
            storage_size=0,
            avg_frequency=0.0,
            last_24h_points=0,
            last_24h_alerts=0,
            metrics_by_type={},
            top_metrics=[]
        )

        assert response.last_update is None
        assert response.total_metrics == 0


class TestTelemetryStatsResponse:
    """Test TelemetryStatsResponse model"""

    def test_telemetry_stats_response_creation(self):
        """Test creating telemetry stats response"""
        response = TelemetryStatsResponse(
            total_devices=100,
            active_devices=85,
            total_metrics=500,
            total_data_points=100000,
            storage_size=104857600,
            points_per_second=150.5,
            avg_latency=25.3,
            error_rate=0.02,
            last_24h_points=50000,
            last_24h_devices=80,
            last_24h_alerts=15,
            devices_by_type={"sensor": 60, "gateway": 40},
            metrics_by_type={"gauge": 300, "counter": 200},
            data_by_hour=[
                {"hour": 0, "points": 4000},
                {"hour": 1, "points": 3800}
            ]
        )

        assert response.total_devices == 100
        assert response.active_devices == 85
        assert response.total_metrics == 500
        assert response.total_data_points == 100000
        assert response.storage_size == 104857600
        assert response.points_per_second == 150.5
        assert response.avg_latency == 25.3
        assert response.error_rate == 0.02
        assert response.last_24h_points == 50000
        assert response.last_24h_devices == 80
        assert response.last_24h_alerts == 15
        assert len(response.devices_by_type) == 2
        assert len(response.metrics_by_type) == 2
        assert len(response.data_by_hour) == 2


class TestRealTimeDataResponse:
    """Test RealTimeDataResponse model"""

    def test_realtime_data_response_creation(self):
        """Test creating real-time data response"""
        now = datetime.now(timezone.utc)

        data_points = [
            TelemetryDataPoint(timestamp=now, metric_name="cpu_usage", value=75.5),
            TelemetryDataPoint(timestamp=now, metric_name="memory_usage", value=60.0)
        ]

        response = RealTimeDataResponse(
            subscription_id="sub_123",
            device_id="device_001",
            data_points=data_points,
            timestamp=now,
            sequence_number=42
        )

        assert response.subscription_id == "sub_123"
        assert response.device_id == "device_001"
        assert len(response.data_points) == 2
        assert response.timestamp == now
        assert response.sequence_number == 42


class TestAggregatedDataResponse:
    """Test AggregatedDataResponse model"""

    def test_aggregated_data_response_with_device(self):
        """Test creating aggregated data response with device"""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)

        data_points = [
            {"timestamp": start, "value": 75.0},
            {"timestamp": start + timedelta(minutes=5), "value": 78.0}
        ]

        response = AggregatedDataResponse(
            device_id="device_001",
            metric_name="cpu_usage",
            aggregation_type=AggregationType.AVG,
            interval=300,
            data_points=data_points,
            start_time=start,
            end_time=now,
            count=2
        )

        assert response.device_id == "device_001"
        assert response.metric_name == "cpu_usage"
        assert response.aggregation_type == AggregationType.AVG
        assert response.interval == 300
        assert len(response.data_points) == 2
        assert response.count == 2

    def test_aggregated_data_response_multi_device(self):
        """Test creating aggregated data response for multiple devices"""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)

        data_points = [
            {"timestamp": start, "value": 75.0}
        ]

        response = AggregatedDataResponse(
            device_id=None,
            metric_name="cpu_usage",
            aggregation_type=AggregationType.AVG,
            interval=300,
            data_points=data_points,
            start_time=start,
            end_time=now,
            count=1
        )

        assert response.device_id is None
        assert response.metric_name == "cpu_usage"


class TestAlertListResponse:
    """Test AlertListResponse model"""

    def test_alert_list_response_creation(self):
        """Test creating alert list response"""
        now = datetime.now(timezone.utc)

        alerts = [
            AlertResponse(
                alert_id=f"alert_{i}",
                rule_id="rule_123",
                rule_name="Test Alert",
                device_id=f"device_{i}",
                metric_name="cpu_usage",
                level=AlertLevel.WARNING,
                status=AlertStatus.ACTIVE if i < 2 else AlertStatus.RESOLVED,
                message="Test message",
                current_value=80 + i,
                threshold_value=80,
                triggered_at=now,
                tags=[],
                metadata={}
            )
            for i in range(3)
        ]

        response = AlertListResponse(
            alerts=alerts,
            count=3,
            active_count=2,
            critical_count=0,
            filters={"level": "warning"},
            limit=100,
            offset=0
        )

        assert len(response.alerts) == 3
        assert response.count == 3
        assert response.active_count == 2
        assert response.critical_count == 0
        assert response.filters == {"level": "warning"}
        assert response.limit == 100
        assert response.offset == 0

    def test_alert_list_response_empty(self):
        """Test creating empty alert list response"""
        response = AlertListResponse(
            alerts=[],
            count=0,
            active_count=0,
            critical_count=0,
            filters={},
            limit=100,
            offset=0
        )

        assert len(response.alerts) == 0
        assert response.count == 0
        assert response.active_count == 0
        assert response.critical_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
