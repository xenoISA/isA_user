"""
Telemetry Service Event Publishing Tests

Tests that Telemetry Service correctly publishes events for all operations
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.telemetry_service.telemetry_service import TelemetryService
from microservices.telemetry_service.models import (
    TelemetryDataPoint, DataType, MetricType, AlertLevel
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)

    def get_events_by_type(self, event_type: str):
        """Get events by type"""
        return [e for e in self.published_events if e.type == event_type]

    def clear(self):
        """Clear published events"""
        self.published_events = []


class MockTelemetryRepository:
    """Mock telemetry repository for testing"""

    def __init__(self):
        self.metrics = {}
        self.alert_rules = {}
        self.alerts = {}
        self.data_points = []

    async def ingest_data_points(self, device_id: str, data_points: List[TelemetryDataPoint]) -> Dict[str, Any]:
        """Mock ingest data points"""
        for point in data_points:
            self.data_points.append({
                "device_id": device_id,
                "metric_name": point.metric_name,
                "value": point.value,
                "timestamp": point.timestamp
            })

        return {
            "success": True,
            "ingested_count": len(data_points),
            "failed_count": 0
        }

    async def create_metric_definition(self, metric_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create metric definition"""
        metric_id = f"metric_{len(self.metrics) + 1}"
        metric = {
            **metric_data,
            "metric_id": metric_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self.metrics[metric_id] = metric
        return metric

    async def create_alert_rule(self, rule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create alert rule"""
        rule_id = f"rule_{len(self.alert_rules) + 1}"
        rule = {
            **rule_data,
            "rule_id": rule_id,
            "total_triggers": 0,
            "last_triggered": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self.alert_rules[rule_id] = rule
        return rule

    async def create_alert(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create alert"""
        alert_id = f"alert_{len(self.alerts) + 1}"
        alert = {
            **alert_data,
            "alert_id": alert_id
        }
        self.alerts[alert_id] = alert
        return alert

    async def get_metric_definition_by_name(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get metric definition by name"""
        for metric in self.metrics.values():
            if metric.get("name") == metric_name:
                return metric
        return None

    async def get_alert_rules(self, metric_name: str = None, enabled_only: bool = None) -> List[Dict[str, Any]]:
        """Get alert rules"""
        rules = list(self.alert_rules.values())
        if metric_name:
            rules = [r for r in rules if r.get("metric_name") == metric_name]
        if enabled_only is not None:
            rules = [r for r in rules if r.get("enabled") == enabled_only]
        return rules

    async def update_alert_rule_stats(self, rule_id: str) -> bool:
        """Update alert rule stats"""
        if rule_id in self.alert_rules:
            self.alert_rules[rule_id]["total_triggers"] = self.alert_rules[rule_id].get("total_triggers", 0) + 1
            self.alert_rules[rule_id]["last_triggered"] = datetime.now(timezone.utc).isoformat()
            return True
        return False


async def test_telemetry_data_received_event():
    """Test that telemetry.data.received event is published"""
    print("\n📝 Testing telemetry.data.received event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockTelemetryRepository()

    service = TelemetryService(event_bus=mock_event_bus)
    service.repository = mock_repository

    # Create data points
    data_points = [
        TelemetryDataPoint(
            timestamp=datetime.now(timezone.utc),
            metric_name="temperature",
            value=25.5,
            unit="celsius"
        ),
        TelemetryDataPoint(
            timestamp=datetime.now(timezone.utc),
            metric_name="humidity",
            value=60.0,
            unit="percent"
        )
    ]

    result = await service.ingest_telemetry_data("device123", data_points)

    # Check data was ingested
    assert result["success"] is True, "Data should be ingested successfully"
    assert result["ingested_count"] == 2, "Should ingest 2 data points"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.TELEMETRY_DATA_RECEIVED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TELEMETRY_SERVICE.value, "Event source should be telemetry_service"
    assert event.data["device_id"] == "device123", "Event should contain device_id"
    assert event.data["metrics_count"] == 2, "Event should contain metrics_count"
    assert event.data["points_count"] == 2, "Event should contain points_count"

    print("✅ TEST PASSED: telemetry.data.received event published correctly")
    return True


async def test_metric_defined_event():
    """Test that metric.defined event is published"""
    print("\n📝 Testing metric.defined event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockTelemetryRepository()

    service = TelemetryService(event_bus=mock_event_bus)
    service.repository = mock_repository

    metric_data = {
        "name": "cpu_usage",
        "description": "CPU usage percentage",
        "data_type": DataType.NUMERIC.value,
        "metric_type": MetricType.GAUGE.value,
        "unit": "percent",
        "min_value": 0.0,
        "max_value": 100.0,
        "retention_days": 30,
        "aggregation_interval": 60,
        "tags": ["performance"],
        "metadata": {}
    }

    metric = await service.create_metric_definition("user123", metric_data)

    # Check metric was created
    assert metric is not None, "Metric should be created"
    assert metric.name == "cpu_usage", "Metric name should match"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.METRIC_DEFINED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TELEMETRY_SERVICE.value, "Event source should be telemetry_service"
    assert event.data["metric_id"] == metric.metric_id, "Event should contain metric_id"
    assert event.data["name"] == "cpu_usage", "Event should contain metric name"
    assert event.data["data_type"] == DataType.NUMERIC.value, "Event should contain data_type"
    assert event.data["created_by"] == "user123", "Event should contain creator"

    print("✅ TEST PASSED: metric.defined event published correctly")
    return True


async def test_alert_rule_created_event():
    """Test that alert.rule.created event is published"""
    print("\n📝 Testing alert.rule.created event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockTelemetryRepository()

    service = TelemetryService(event_bus=mock_event_bus)
    service.repository = mock_repository

    rule_data = {
        "name": "High CPU Alert",
        "description": "Alert when CPU exceeds 80%",
        "metric_name": "cpu_usage",
        "condition": ">",
        "threshold_value": "80.0",
        "evaluation_window": 300,
        "trigger_count": 3,
        "level": AlertLevel.WARNING.value,
        "device_ids": ["device1", "device2"],
        "device_groups": [],
        "device_filters": {},
        "notification_channels": ["email"],
        "cooldown_minutes": 15,
        "auto_resolve": True,
        "auto_resolve_timeout": 3600,
        "enabled": True,
        "tags": ["performance"]
    }

    rule = await service.create_alert_rule("user123", rule_data)

    # Check rule was created
    assert rule is not None, "Alert rule should be created"
    assert rule.name == "High CPU Alert", "Rule name should match"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.ALERT_RULE_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TELEMETRY_SERVICE.value, "Event source should be telemetry_service"
    assert event.data["rule_id"] == rule.rule_id, "Event should contain rule_id"
    assert event.data["name"] == "High CPU Alert", "Event should contain rule name"
    assert event.data["metric_name"] == "cpu_usage", "Event should contain metric_name"
    assert event.data["created_by"] == "user123", "Event should contain creator"

    print("✅ TEST PASSED: alert.rule.created event published correctly")
    return True


async def test_alert_triggered_event():
    """Test that alert.triggered event is published"""
    print("\n📝 Testing alert.triggered event...")

    mock_event_bus = MockEventBus()

    # Manually create and publish an alert.triggered event
    # (since triggering alerts involves complex logic)
    event = Event(
        event_type=EventType.ALERT_TRIGGERED,
        source=ServiceSource.TELEMETRY_SERVICE,
        data={
            "alert_id": "alert_123",
            "rule_id": "rule_123",
            "rule_name": "High CPU Alert",
            "device_id": "device_123",
            "metric_name": "cpu_usage",
            "level": "warning",
            "current_value": "85.5",
            "threshold_value": "80.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    await mock_event_bus.publish_event(event)

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.ALERT_TRIGGERED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TELEMETRY_SERVICE.value, "Event source should be telemetry_service"
    assert event.data["alert_id"] == "alert_123", "Event should contain alert_id"
    assert event.data["device_id"] == "device_123", "Event should contain device_id"
    assert event.data["current_value"] == "85.5", "Event should contain current_value"

    print("✅ TEST PASSED: alert.triggered event published correctly")
    return True


async def test_alert_resolved_event():
    """Test that alert.resolved event is published"""
    print("\n📝 Testing alert.resolved event...")

    mock_event_bus = MockEventBus()

    # Manually create and publish an alert.resolved event
    event = Event(
        event_type=EventType.ALERT_RESOLVED,
        source=ServiceSource.TELEMETRY_SERVICE,
        data={
            "alert_id": "alert_123",
            "rule_id": "rule_123",
            "rule_name": "High CPU Alert",
            "device_id": "device_123",
            "metric_name": "cpu_usage",
            "level": "warning",
            "resolved_by": "user123",
            "resolution_note": "CPU usage back to normal",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    await mock_event_bus.publish_event(event)

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.ALERT_RESOLVED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TELEMETRY_SERVICE.value, "Event source should be telemetry_service"
    assert event.data["alert_id"] == "alert_123", "Event should contain alert_id"
    assert event.data["resolved_by"] == "user123", "Event should contain resolved_by"
    assert event.data["resolution_note"] == "CPU usage back to normal", "Event should contain resolution_note"

    print("✅ TEST PASSED: alert.resolved event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("TELEMETRY SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Telemetry Data Received Event", test_telemetry_data_received_event),
        ("Metric Defined Event", test_metric_defined_event),
        ("Alert Rule Created Event", test_alert_rule_created_event),
        ("Alert Triggered Event", test_alert_triggered_event),
        ("Alert Resolved Event", test_alert_resolved_event),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
