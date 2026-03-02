"""
Telemetry Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

from .models import TelemetryDataPoint


class TelemetryServiceError(Exception):
    """Base exception for telemetry service errors"""
    pass


class MetricNotFoundError(Exception):
    """Metric definition not found"""
    pass


class AlertRuleNotFoundError(Exception):
    """Alert rule not found"""
    pass


@runtime_checkable
class TelemetryRepositoryProtocol(Protocol):
    """Interface for Telemetry Repository"""

    async def ingest_data_points(
        self, device_id: str, data_points: List[TelemetryDataPoint],
    ) -> Dict[str, Any]: ...

    async def ingest_single_point(
        self, device_id: str, data_point: TelemetryDataPoint,
    ) -> bool: ...

    async def query_telemetry_data(
        self, device_id: Optional[str] = None,
        metric_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]: ...

    async def create_metric_definition(
        self, metric_def: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]: ...

    async def get_metric_definition(self, name: str) -> Optional[Dict[str, Any]]: ...

    async def list_metric_definitions(
        self, data_type: Optional[str] = None, metric_type: Optional[str] = None,
        limit: int = 100, offset: int = 0,
    ) -> List[Dict[str, Any]]: ...

    async def delete_metric_definition(self, metric_id: str) -> bool: ...

    async def create_alert_rule(self, rule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def list_alert_rules(self, enabled_only: bool = True) -> List[Dict[str, Any]]: ...

    async def get_alert_rule(self, rule_id: str) -> Optional[Dict[str, Any]]: ...

    async def update_alert_rule(self, rule_id: str, update_data: Dict[str, Any]) -> bool: ...

    async def delete_alert_rule(self, rule_id: str) -> bool: ...

    async def create_alert(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def list_alerts(
        self, device_id: Optional[str] = None, status: Optional[str] = None,
        level: Optional[str] = None, limit: int = 100,
    ) -> List[Dict[str, Any]]: ...

    async def update_alert(self, alert_id: str, update_data: Dict[str, Any]) -> bool: ...

    async def get_device_stats(self, device_id: str) -> Dict[str, Any]: ...

    async def get_global_stats(self) -> Dict[str, Any]: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
