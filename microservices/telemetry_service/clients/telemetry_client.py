"""
Telemetry Service Client

Client library for other microservices to interact with telemetry service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TelemetryServiceClient:
    """Telemetry Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Telemetry Service client

        Args:
            base_url: Telemetry service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("telemetry_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8218"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Telemetry Data Ingestion
    # =============================================================================

    async def send_telemetry(
        self,
        device_id: str,
        metric_name: str,
        value: float,
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send single telemetry data point

        Args:
            device_id: Device ID
            metric_name: Metric name
            value: Metric value
            unit: Unit of measurement (optional)
            tags: Additional tags (optional)
            timestamp: Timestamp (optional, defaults to now)

        Returns:
            Ingestion result

        Example:
            >>> client = TelemetryServiceClient()
            >>> result = await client.send_telemetry(
            ...     device_id="device_001",
            ...     metric_name="temperature",
            ...     value=25.5,
            ...     unit="celsius",
            ...     tags={"location": "living_room"}
            ... )
        """
        try:
            payload = {
                "metric_name": metric_name,
                "value": value
            }

            if unit:
                payload["unit"] = unit
            if tags:
                payload["tags"] = tags
            if timestamp:
                payload["timestamp"] = timestamp.isoformat()

            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/telemetry",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send telemetry: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")
            return None

    async def send_batch_telemetry(
        self,
        device_id: str,
        data_points: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Send batch telemetry data points

        Args:
            device_id: Device ID
            data_points: List of telemetry data point dictionaries

        Returns:
            Batch ingestion result

        Example:
            >>> data_points = [
            ...     {"metric_name": "temperature", "value": 25.5, "unit": "celsius"},
            ...     {"metric_name": "humidity", "value": 60.0, "unit": "percent"}
            ... ]
            >>> result = await client.send_batch_telemetry("device_001", data_points)
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/telemetry/batch",
                json={"data_points": data_points}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send batch telemetry: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sending batch telemetry: {e}")
            return None

    async def send_bulk_telemetry(
        self,
        telemetry_data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Send bulk telemetry from multiple devices

        Args:
            telemetry_data: List of telemetry records with device_id

        Returns:
            Bulk ingestion result

        Example:
            >>> data = [
            ...     {
            ...         "device_id": "device_001",
            ...         "metric_name": "temperature",
            ...         "value": 25.5
            ...     },
            ...     {
            ...         "device_id": "device_002",
            ...         "metric_name": "temperature",
            ...         "value": 26.0
            ...     }
            ... ]
            >>> result = await client.send_bulk_telemetry(data)
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/telemetry/bulk",
                json={"telemetry_data": telemetry_data}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send bulk telemetry: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sending bulk telemetry: {e}")
            return None

    # =============================================================================
    # Metric Definitions
    # =============================================================================

    async def define_metric(
        self,
        metric_name: str,
        description: str,
        unit: str,
        metric_type: str = "gauge",
        aggregations: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Define new metric

        Args:
            metric_name: Metric name
            description: Metric description
            unit: Unit of measurement
            metric_type: Type (gauge, counter, histogram)
            aggregations: Supported aggregations (optional)
            tags: Allowed tag keys (optional)

        Returns:
            Created metric definition

        Example:
            >>> metric = await client.define_metric(
            ...     metric_name="cpu_usage",
            ...     description="CPU usage percentage",
            ...     unit="percent",
            ...     metric_type="gauge",
            ...     aggregations=["avg", "max", "min"]
            ... )
        """
        try:
            payload = {
                "metric_name": metric_name,
                "description": description,
                "unit": unit,
                "metric_type": metric_type
            }

            if aggregations:
                payload["aggregations"] = aggregations
            if tags:
                payload["tags"] = tags

            response = await self.client.post(
                f"{self.base_url}/api/v1/metrics",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to define metric: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error defining metric: {e}")
            return None

    async def list_metrics(self) -> Optional[List[Dict[str, Any]]]:
        """
        List all metric definitions

        Returns:
            List of metric definitions

        Example:
            >>> metrics = await client.list_metrics()
            >>> for metric in metrics:
            ...     print(f"{metric['metric_name']}: {metric['description']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/metrics"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list metrics: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing metrics: {e}")
            return None

    async def get_metric(
        self,
        metric_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get metric definition

        Args:
            metric_name: Metric name

        Returns:
            Metric definition

        Example:
            >>> metric = await client.get_metric("temperature")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/metrics/{metric_name}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get metric: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting metric: {e}")
            return None

    async def delete_metric(
        self,
        metric_name: str
    ) -> bool:
        """
        Delete metric definition

        Args:
            metric_name: Metric name

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_metric("old_metric")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/metrics/{metric_name}"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete metric: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting metric: {e}")
            return False

    # =============================================================================
    # Telemetry Queries
    # =============================================================================

    async def query_telemetry(
        self,
        device_id: Optional[str] = None,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None,
        aggregation: Optional[str] = None,
        interval: Optional[str] = None,
        limit: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        Query telemetry data

        Args:
            device_id: Filter by device (optional)
            metric_name: Filter by metric (optional)
            start_time: Start time (optional)
            end_time: End time (optional)
            tags: Filter by tags (optional)
            aggregation: Aggregation function (optional)
            interval: Aggregation interval (optional)
            limit: Maximum results

        Returns:
            Telemetry query results

        Example:
            >>> result = await client.query_telemetry(
            ...     device_id="device_001",
            ...     metric_name="temperature",
            ...     start_time=datetime(2024, 1, 1),
            ...     end_time=datetime(2024, 1, 2),
            ...     aggregation="avg",
            ...     interval="1h"
            ... )
        """
        try:
            payload = {"limit": limit}

            if device_id:
                payload["device_id"] = device_id
            if metric_name:
                payload["metric_name"] = metric_name
            if start_time:
                payload["start_time"] = start_time.isoformat()
            if end_time:
                payload["end_time"] = end_time.isoformat()
            if tags:
                payload["tags"] = tags
            if aggregation:
                payload["aggregation"] = aggregation
            if interval:
                payload["interval"] = interval

            response = await self.client.post(
                f"{self.base_url}/api/v1/query",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to query telemetry: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error querying telemetry: {e}")
            return None

    async def get_latest_value(
        self,
        device_id: str,
        metric_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest value for device metric

        Args:
            device_id: Device ID
            metric_name: Metric name

        Returns:
            Latest value data

        Example:
            >>> latest = await client.get_latest_value("device_001", "temperature")
            >>> print(f"Latest temperature: {latest['value']} {latest['unit']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/{device_id}/metrics/{metric_name}/latest"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get latest value: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting latest value: {e}")
            return None

    async def get_device_metrics(
        self,
        device_id: str
    ) -> Optional[List[str]]:
        """
        Get all metrics for device

        Args:
            device_id: Device ID

        Returns:
            List of metric names

        Example:
            >>> metrics = await client.get_device_metrics("device_001")
            >>> print(f"Available metrics: {', '.join(metrics)}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/{device_id}/metrics"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get device metrics: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting device metrics: {e}")
            return None

    async def get_metric_range(
        self,
        device_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        aggregation: Optional[str] = None,
        interval: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get metric values for time range

        Args:
            device_id: Device ID
            metric_name: Metric name
            start_time: Start time
            end_time: End time
            aggregation: Aggregation function (optional)
            interval: Aggregation interval (optional)

        Returns:
            Time series data

        Example:
            >>> data = await client.get_metric_range(
            ...     device_id="device_001",
            ...     metric_name="temperature",
            ...     start_time=datetime(2024, 1, 1),
            ...     end_time=datetime(2024, 1, 2),
            ...     aggregation="avg",
            ...     interval="15m"
            ... )
        """
        try:
            params = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

            if aggregation:
                params["aggregation"] = aggregation
            if interval:
                params["interval"] = interval

            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/{device_id}/metrics/{metric_name}/range",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get metric range: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting metric range: {e}")
            return None

    async def get_aggregated_data(
        self,
        metric_name: str,
        aggregation: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        device_ids: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get aggregated data across devices

        Args:
            metric_name: Metric name
            aggregation: Aggregation function
            start_time: Start time
            end_time: End time
            interval: Aggregation interval
            device_ids: Filter by devices (optional)
            tags: Filter by tags (optional)

        Returns:
            Aggregated data

        Example:
            >>> data = await client.get_aggregated_data(
            ...     metric_name="temperature",
            ...     aggregation="avg",
            ...     start_time=datetime(2024, 1, 1),
            ...     end_time=datetime(2024, 1, 2),
            ...     interval="1h",
            ...     device_ids=["device_001", "device_002"]
            ... )
        """
        try:
            params = {
                "metric_name": metric_name,
                "aggregation": aggregation,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "interval": interval
            }

            if device_ids:
                params["device_ids"] = ",".join(device_ids)
            if tags:
                for key, value in tags.items():
                    params[f"tag_{key}"] = value

            response = await self.client.get(
                f"{self.base_url}/api/v1/aggregated",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get aggregated data: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}")
            return None

    # =============================================================================
    # Alerts
    # =============================================================================

    async def create_alert_rule(
        self,
        rule_name: str,
        metric_name: str,
        condition: str,
        threshold: float,
        severity: str = "warning",
        device_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create alert rule

        Args:
            rule_name: Rule name
            metric_name: Metric to monitor
            condition: Condition (gt, lt, gte, lte, eq)
            threshold: Threshold value
            severity: Alert severity
            device_id: Specific device (optional)
            tags: Tag filters (optional)

        Returns:
            Created alert rule

        Example:
            >>> rule = await client.create_alert_rule(
            ...     rule_name="high_temp",
            ...     metric_name="temperature",
            ...     condition="gt",
            ...     threshold=30.0,
            ...     severity="critical"
            ... )
        """
        try:
            payload = {
                "rule_name": rule_name,
                "metric_name": metric_name,
                "condition": condition,
                "threshold": threshold,
                "severity": severity
            }

            if device_id:
                payload["device_id"] = device_id
            if tags:
                payload["tags"] = tags

            response = await self.client.post(
                f"{self.base_url}/api/v1/alerts/rules",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create alert rule: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
            return None

    async def list_alert_rules(self) -> Optional[List[Dict[str, Any]]]:
        """
        List all alert rules

        Returns:
            List of alert rules

        Example:
            >>> rules = await client.list_alert_rules()
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/alerts/rules"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list alert rules: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing alert rules: {e}")
            return None

    async def list_alerts(
        self,
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        List alerts

        Args:
            device_id: Filter by device (optional)
            severity: Filter by severity (optional)
            status: Filter by status (optional)
            limit: Maximum results

        Returns:
            List of alerts

        Example:
            >>> alerts = await client.list_alerts(severity="critical", status="active")
        """
        try:
            params = {"limit": limit}

            if device_id:
                params["device_id"] = device_id
            if severity:
                params["severity"] = severity
            if status:
                params["status"] = status

            response = await self.client.get(
                f"{self.base_url}/api/v1/alerts",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list alerts: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing alerts: {e}")
            return None

    async def acknowledge_alert(
        self,
        alert_id: str
    ) -> bool:
        """
        Acknowledge alert

        Args:
            alert_id: Alert ID

        Returns:
            True if successful

        Example:
            >>> success = await client.acknowledge_alert("alert_123")
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/alerts/{alert_id}/acknowledge"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to acknowledge alert: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False

    async def resolve_alert(
        self,
        alert_id: str
    ) -> bool:
        """
        Resolve alert

        Args:
            alert_id: Alert ID

        Returns:
            True if successful

        Example:
            >>> success = await client.resolve_alert("alert_123")
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/alerts/{alert_id}/resolve"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to resolve alert: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False

    # =============================================================================
    # Statistics
    # =============================================================================

    async def get_device_stats(
        self,
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get device telemetry statistics

        Args:
            device_id: Device ID

        Returns:
            Device statistics

        Example:
            >>> stats = await client.get_device_stats("device_001")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/devices/{device_id}/stats"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get device stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting device stats: {e}")
            return None

    async def get_telemetry_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get telemetry service statistics

        Returns:
            Service statistics

        Example:
            >>> stats = await client.get_telemetry_stats()
            >>> print(f"Total data points: {stats['total_data_points']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/stats"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get telemetry stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting telemetry stats: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["TelemetryServiceClient"]
