"""
Telemetry Service - Mock Dependencies

Mock implementations for component testing.
All test data uses TelemetryTestDataFactory - zero hardcoded data.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import uuid

from tests.contracts.telemetry.data_contract import (
    TelemetryTestDataFactory,
    DataType,
    MetricType,
    AlertLevel,
    AlertStatus,
    AggregationType,
)


class MockTelemetryRepository:
    """Mock telemetry repository for component testing

    Implements TelemetryRepositoryProtocol interface.
    Uses TelemetryTestDataFactory for all test data.
    """

    def __init__(self):
        self._data_points: Dict[str, List[Dict]] = {}  # device_id -> list of points
        self._metric_definitions: Dict[str, Dict] = {}  # metric_id -> definition
        self._metric_by_name: Dict[str, str] = {}  # name -> metric_id
        self._alert_rules: Dict[str, Dict] = {}  # rule_id -> rule
        self._alerts: Dict[str, Dict] = {}  # alert_id -> alert
        self._stats: Dict[str, Any] = {}
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    def set_data_points(self, device_id: str, points: List[Dict]):
        """Add data points for a device"""
        self._data_points[device_id] = points

    def add_data_point(self, device_id: str, point: Dict):
        """Add a single data point for a device"""
        if device_id not in self._data_points:
            self._data_points[device_id] = []
        self._data_points[device_id].append(point)

    def set_metric_definition(
        self,
        metric_id: str = None,
        name: str = None,
        data_type: str = "numeric",
        metric_type: str = "gauge",
        **kwargs
    ):
        """Add a metric definition"""
        metric_id = metric_id or TelemetryTestDataFactory.make_metric_id()
        name = name or TelemetryTestDataFactory.make_metric_name()
        now = datetime.now(timezone.utc)

        metric_def = {
            "metric_id": metric_id,
            "name": name,
            "description": kwargs.get("description", TelemetryTestDataFactory.make_description()),
            "data_type": data_type,
            "metric_type": metric_type,
            "unit": kwargs.get("unit", TelemetryTestDataFactory.make_unit()),
            "min_value": kwargs.get("min_value"),
            "max_value": kwargs.get("max_value"),
            "retention_days": kwargs.get("retention_days", 90),
            "aggregation_interval": kwargs.get("aggregation_interval", 60),
            "tags": kwargs.get("tags", []),
            "metadata": kwargs.get("metadata", {}),
            "created_at": kwargs.get("created_at", now),
            "updated_at": kwargs.get("updated_at", now),
            "created_by": kwargs.get("created_by", TelemetryTestDataFactory.make_user_id()),
        }

        self._metric_definitions[metric_id] = metric_def
        self._metric_by_name[name] = metric_id

    def set_alert_rule(
        self,
        rule_id: str = None,
        name: str = None,
        metric_name: str = None,
        condition: str = ">",
        threshold_value: str = "90",
        level: str = "warning",
        enabled: bool = True,
        **kwargs
    ):
        """Add an alert rule"""
        rule_id = rule_id or TelemetryTestDataFactory.make_rule_id()
        name = name or TelemetryTestDataFactory.make_rule_name()
        metric_name = metric_name or TelemetryTestDataFactory.make_metric_name()
        now = datetime.now(timezone.utc)

        alert_rule = {
            "rule_id": rule_id,
            "name": name,
            "description": kwargs.get("description"),
            "metric_name": metric_name,
            "condition": condition,
            "threshold_value": threshold_value,
            "evaluation_window": kwargs.get("evaluation_window", 300),
            "trigger_count": kwargs.get("trigger_count", 1),
            "level": level,
            "device_ids": kwargs.get("device_ids", []),
            "device_groups": kwargs.get("device_groups", []),
            "device_filters": kwargs.get("device_filters", {}),
            "notification_channels": kwargs.get("notification_channels", []),
            "cooldown_minutes": kwargs.get("cooldown_minutes", 15),
            "auto_resolve": kwargs.get("auto_resolve", True),
            "auto_resolve_timeout": kwargs.get("auto_resolve_timeout", 3600),
            "enabled": enabled,
            "tags": kwargs.get("tags", []),
            "total_triggers": kwargs.get("total_triggers", 0),
            "last_triggered": kwargs.get("last_triggered"),
            "created_at": kwargs.get("created_at", now),
            "updated_at": kwargs.get("updated_at", now),
            "created_by": kwargs.get("created_by", TelemetryTestDataFactory.make_user_id()),
        }

        self._alert_rules[rule_id] = alert_rule
        return alert_rule

    def set_alert(
        self,
        alert_id: str = None,
        rule_id: str = None,
        device_id: str = None,
        metric_name: str = None,
        status: str = "active",
        level: str = "warning",
        **kwargs
    ):
        """Add an alert"""
        alert_id = alert_id or TelemetryTestDataFactory.make_alert_id()
        rule_id = rule_id or TelemetryTestDataFactory.make_rule_id()
        device_id = device_id or TelemetryTestDataFactory.make_device_id()
        metric_name = metric_name or TelemetryTestDataFactory.make_metric_name()
        now = datetime.now(timezone.utc)

        alert = {
            "alert_id": alert_id,
            "rule_id": rule_id,
            "rule_name": kwargs.get("rule_name", TelemetryTestDataFactory.make_rule_name()),
            "device_id": device_id,
            "metric_name": metric_name,
            "level": level,
            "status": status,
            "message": kwargs.get("message", "Alert triggered"),
            "current_value": kwargs.get("current_value", "95"),
            "threshold_value": kwargs.get("threshold_value", "90"),
            "triggered_at": kwargs.get("triggered_at", now),
            "acknowledged_at": kwargs.get("acknowledged_at"),
            "acknowledged_by": kwargs.get("acknowledged_by"),
            "resolved_at": kwargs.get("resolved_at"),
            "resolved_by": kwargs.get("resolved_by"),
            "resolution_note": kwargs.get("resolution_note"),
            "auto_resolve_at": kwargs.get("auto_resolve_at"),
            "affected_devices_count": kwargs.get("affected_devices_count", 1),
            "tags": kwargs.get("tags", []),
            "metadata": kwargs.get("metadata", {}),
            "created_at": kwargs.get("created_at", now),
            "updated_at": kwargs.get("updated_at", now),
        }

        self._alerts[alert_id] = alert
        return alert

    def set_stats(
        self,
        total_devices: int = 0,
        total_metrics: int = 0,
        total_points: int = 0,
        last_24h_points: int = 0,
        **kwargs
    ):
        """Set service statistics"""
        self._stats = {
            "total_devices": total_devices,
            "total_metrics": total_metrics,
            "total_points": total_points,
            "last_24h_points": last_24h_points,
            **kwargs
        }

    def set_error(self, error: Exception):
        """Set an error to be raised on operations"""
        self._error = error

    def clear_error(self):
        """Clear any set error"""
        self._error = None

    def _log_call(self, method: str, **kwargs):
        """Log method calls for assertions"""
        self._call_log.append({"method": method, "kwargs": kwargs})

    def assert_called(self, method: str):
        """Assert that a method was called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method in called_methods, f"Expected {method} to be called, but got {called_methods}"

    def assert_called_with(self, method: str, **kwargs):
        """Assert that a method was called with specific kwargs"""
        for call in self._call_log:
            if call["method"] == method:
                for key, value in kwargs.items():
                    assert key in call["kwargs"], f"Expected kwarg {key} not found"
                    assert call["kwargs"][key] == value, f"Expected {key}={value}, got {call['kwargs'][key]}"
                return
        raise AssertionError(f"Expected {method} to be called with {kwargs}")

    def assert_not_called(self, method: str):
        """Assert that a method was not called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method not in called_methods, f"Expected {method} not to be called, but it was"

    def get_call_count(self, method: str) -> int:
        """Get the number of times a method was called"""
        return sum(1 for c in self._call_log if c["method"] == method)

    def reset(self):
        """Reset all data and call log"""
        self._data_points.clear()
        self._metric_definitions.clear()
        self._metric_by_name.clear()
        self._alert_rules.clear()
        self._alerts.clear()
        self._stats.clear()
        self._error = None
        self._call_log.clear()

    # Repository interface methods

    async def ingest_data_points(self, device_id: str, data_points: List) -> Dict[str, Any]:
        """Ingest telemetry data points"""
        self._log_call("ingest_data_points", device_id=device_id, data_points=data_points)

        if self._error:
            raise self._error

        if device_id not in self._data_points:
            self._data_points[device_id] = []

        ingested_count = 0
        for point in data_points:
            point_dict = {
                "time": point.timestamp,
                "device_id": device_id,
                "metric_name": point.metric_name,
                "value_numeric": point.value if isinstance(point.value, (int, float)) else None,
                "value_string": point.value if isinstance(point.value, str) else None,
                "value_boolean": point.value if isinstance(point.value, bool) else None,
                "unit": point.unit,
                "tags": point.tags or {},
                "metadata": point.metadata or {},
            }
            self._data_points[device_id].append(point_dict)
            ingested_count += 1

        return {
            "success": True,
            "ingested_count": ingested_count,
            "failed_count": 0,
        }

    async def query_telemetry_data(
        self,
        device_id: Optional[str],
        metric_names: List[str],
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000
    ) -> List[Dict]:
        """Query telemetry data"""
        self._log_call(
            "query_telemetry_data",
            device_id=device_id,
            metric_names=metric_names,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        if self._error:
            raise self._error

        results = []

        devices_to_query = [device_id] if device_id else list(self._data_points.keys())

        for dev_id in devices_to_query:
            points = self._data_points.get(dev_id, [])
            for point in points:
                # Filter by time
                point_time = point.get("time")
                if point_time and start_time <= point_time <= end_time:
                    # Filter by metric name
                    if not metric_names or point.get("metric_name") in metric_names:
                        results.append(point)

        return results[:limit]

    async def create_metric_definition(self, metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create metric definition"""
        self._log_call("create_metric_definition", metric_data=metric_data)

        if self._error:
            raise self._error

        metric_id = TelemetryTestDataFactory.make_metric_id()
        now = datetime.now(timezone.utc)

        metric_def = {
            "metric_id": metric_id,
            **metric_data,
            "created_at": now,
            "updated_at": now,
        }

        self._metric_definitions[metric_id] = metric_def
        self._metric_by_name[metric_data["name"]] = metric_id

        return metric_def

    async def get_metric_definition_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get metric definition by name"""
        self._log_call("get_metric_definition_by_name", name=name)

        if self._error:
            raise self._error

        metric_id = self._metric_by_name.get(name)
        if metric_id:
            return self._metric_definitions.get(metric_id)
        return None

    async def get_metric_definition(self, metric_id: str) -> Optional[Dict[str, Any]]:
        """Get metric definition by ID"""
        self._log_call("get_metric_definition", metric_id=metric_id)

        if self._error:
            raise self._error

        return self._metric_definitions.get(metric_id)

    async def list_metric_definitions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List metric definitions"""
        self._log_call("list_metric_definitions", limit=limit, offset=offset)

        if self._error:
            raise self._error

        definitions = list(self._metric_definitions.values())
        return definitions[offset:offset + limit]

    async def create_alert_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert rule"""
        self._log_call("create_alert_rule", rule_data=rule_data)

        if self._error:
            raise self._error

        rule_id = TelemetryTestDataFactory.make_rule_id()
        now = datetime.now(timezone.utc)

        alert_rule = {
            "rule_id": rule_id,
            **rule_data,
            "total_triggers": 0,
            "last_triggered": None,
            "created_at": now,
            "updated_at": now,
        }

        self._alert_rules[rule_id] = alert_rule
        return alert_rule

    async def get_alert_rules(
        self,
        metric_name: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get alert rules"""
        self._log_call("get_alert_rules", metric_name=metric_name, enabled_only=enabled_only)

        if self._error:
            raise self._error

        rules = list(self._alert_rules.values())

        if metric_name:
            rules = [r for r in rules if r.get("metric_name") == metric_name]

        if enabled_only:
            rules = [r for r in rules if r.get("enabled", True)]

        return rules

    async def get_alert_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get alert rule by ID"""
        self._log_call("get_alert_rule", rule_id=rule_id)

        if self._error:
            raise self._error

        return self._alert_rules.get(rule_id)

    async def update_alert_rule(self, rule_id: str, update_data: Dict[str, Any]) -> bool:
        """Update alert rule"""
        self._log_call("update_alert_rule", rule_id=rule_id, update_data=update_data)

        if self._error:
            raise self._error

        if rule_id not in self._alert_rules:
            return False

        self._alert_rules[rule_id].update(update_data)
        self._alert_rules[rule_id]["updated_at"] = datetime.now(timezone.utc)
        return True

    async def update_alert_rule_stats(self, rule_id: str) -> bool:
        """Update alert rule statistics"""
        self._log_call("update_alert_rule_stats", rule_id=rule_id)

        if self._error:
            raise self._error

        if rule_id not in self._alert_rules:
            return False

        self._alert_rules[rule_id]["total_triggers"] = self._alert_rules[rule_id].get("total_triggers", 0) + 1
        self._alert_rules[rule_id]["last_triggered"] = datetime.now(timezone.utc)
        return True

    async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert"""
        self._log_call("create_alert", alert_data=alert_data)

        if self._error:
            raise self._error

        alert_id = TelemetryTestDataFactory.make_alert_id()
        now = datetime.now(timezone.utc)

        alert = {
            "alert_id": alert_id,
            **alert_data,
            "created_at": now,
            "updated_at": now,
        }

        self._alerts[alert_id] = alert
        return alert

    async def get_alerts(
        self,
        status: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get alerts"""
        self._log_call(
            "get_alerts",
            status=status,
            level=level,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )

        if self._error:
            raise self._error

        alerts = list(self._alerts.values())

        if status:
            alerts = [a for a in alerts if a.get("status") == status]

        if level:
            alerts = [a for a in alerts if a.get("level") == level]

        if start_time:
            alerts = [a for a in alerts if a.get("triggered_at", datetime.min.replace(tzinfo=timezone.utc)) >= start_time]

        if end_time:
            alerts = [a for a in alerts if a.get("triggered_at", datetime.max.replace(tzinfo=timezone.utc)) <= end_time]

        return alerts[offset:offset + limit]

    async def get_alerts_by_device(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get alerts by device"""
        self._log_call("get_alerts_by_device", device_id=device_id, start_time=start_time, end_time=end_time)

        if self._error:
            raise self._error

        alerts = [a for a in self._alerts.values() if a.get("device_id") == device_id]

        if start_time:
            alerts = [a for a in alerts if a.get("triggered_at", datetime.min.replace(tzinfo=timezone.utc)) >= start_time]

        if end_time:
            alerts = [a for a in alerts if a.get("triggered_at", datetime.max.replace(tzinfo=timezone.utc)) <= end_time]

        return alerts

    async def update_alert(self, alert_id: str, update_data: Dict[str, Any]) -> bool:
        """Update alert"""
        self._log_call("update_alert", alert_id=alert_id, update_data=update_data)

        if self._error:
            raise self._error

        if alert_id not in self._alerts:
            return False

        self._alerts[alert_id].update(update_data)
        self._alerts[alert_id]["updated_at"] = datetime.now(timezone.utc)
        return True

    async def get_device_stats(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device telemetry stats"""
        self._log_call("get_device_stats", device_id=device_id)

        if self._error:
            raise self._error

        points = self._data_points.get(device_id, [])

        if not points:
            return None

        metrics = list(set(p.get("metric_name") for p in points if p.get("metric_name")))
        last_update = max((p.get("time") for p in points if p.get("time")), default=None)

        # Calculate 24h points
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_24h_points = sum(
            1 for p in points
            if p.get("time") and p["time"] >= last_24h
        )

        return {
            "device_id": device_id,
            "total_points": len(points),
            "metrics": metrics,
            "last_update": last_update,
            "last_24h_points": last_24h_points,
        }

    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global telemetry stats"""
        self._log_call("get_global_stats")

        if self._error:
            raise self._error

        if self._stats:
            return self._stats

        # Calculate from data
        total_devices = len(self._data_points)
        total_points = sum(len(points) for points in self._data_points.values())

        # Get unique metrics
        all_metrics = set()
        for points in self._data_points.values():
            for point in points:
                if point.get("metric_name"):
                    all_metrics.add(point["metric_name"])

        # Calculate 24h points
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_24h_points = sum(
            1 for points in self._data_points.values()
            for p in points
            if p.get("time") and p["time"] >= last_24h
        )

        return {
            "total_devices": total_devices,
            "total_metrics": len(all_metrics),
            "total_points": total_points,
            "last_24h_points": last_24h_points,
        }


class MockEventBus:
    """Mock NATS event bus for telemetry service"""

    def __init__(self):
        self.published_events: List[Any] = []
        self._call_log: List[Dict] = []
        self._error: Optional[Exception] = None

    def set_error(self, error: Exception):
        """Set an error to be raised on publish"""
        self._error = error

    def clear_error(self):
        """Clear any set error"""
        self._error = None

    async def publish(self, event: Any):
        """Publish event"""
        self._call_log.append({"method": "publish", "event": event})

        if self._error:
            raise self._error

        self.published_events.append(event)

    async def publish_event(self, event: Any):
        """Publish event (alias)"""
        await self.publish(event)

    def assert_published(self, event_type: str = None):
        """Assert that an event was published"""
        assert len(self.published_events) > 0, "No events were published"
        if event_type:
            event_types = [getattr(e, "event_type", str(e)) for e in self.published_events]
            assert event_type in str(event_types), f"Expected {event_type} event, got {event_types}"

    def assert_not_published(self):
        """Assert that no events were published"""
        assert len(self.published_events) == 0, f"Expected no events, but {len(self.published_events)} were published"

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def get_published_count(self) -> int:
        """Get count of published events"""
        return len(self.published_events)

    def reset(self):
        """Reset all published events"""
        self.published_events.clear()
        self._call_log.clear()
        self._error = None
