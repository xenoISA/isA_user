"""
Telemetry Repository

Data access layer for telemetry service with time-series data storage.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import uuid
import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from core.config_manager import ConfigManager
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import ListValue, Struct

from .models import (
    DataType, MetricType, AlertLevel, AlertStatus, AggregationType,
    TelemetryDataPoint, MetricDefinitionResponse, TelemetryDataResponse,
    AlertRuleResponse, AlertResponse
)

logger = logging.getLogger(__name__)


class TelemetryRepository:
    """Repository for telemetry operations using PostgresClient"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("telemetry_service")

        # Discover PostgreSQL service
        # Priority: environment variables → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(
            host=host,
            port=port,
            user_id="telemetry_service"
        )
        self.schema = "telemetry"
        self.data_table = "telemetry_data"
        self.metric_definitions_table = "metric_definitions"
        self.alert_rules_table = "alert_rules"
        self.alerts_table = "alerts"
        self.aggregated_table = "aggregated_data"
        self.stats_table = "telemetry_stats"

        # Ensure schema and tables exist
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure telemetry schema and tables exist"""
        try:
            # Create schema
            with self.db:
                self.db.execute("CREATE SCHEMA IF NOT EXISTS telemetry", schema='public')
                logger.info("Telemetry schema ensured")

            # Create metric_definitions table
            create_metric_definitions = '''
                CREATE TABLE IF NOT EXISTS telemetry.metric_definitions (
                    id SERIAL PRIMARY KEY,
                    metric_id VARCHAR(64) NOT NULL UNIQUE,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description VARCHAR(500),
                    data_type VARCHAR(20) NOT NULL,
                    metric_type VARCHAR(20) NOT NULL DEFAULT 'gauge',
                    unit VARCHAR(20),
                    min_value DOUBLE PRECISION,
                    max_value DOUBLE PRECISION,
                    retention_days INTEGER DEFAULT 90,
                    aggregation_interval INTEGER DEFAULT 60,
                    tags TEXT[],
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    created_by VARCHAR(100) NOT NULL,
                    CONSTRAINT check_data_type CHECK (data_type IN ('numeric', 'string', 'boolean', 'json', 'binary', 'geolocation', 'timestamp')),
                    CONSTRAINT check_metric_type CHECK (metric_type IN ('gauge', 'counter', 'histogram', 'summary')),
                    CONSTRAINT check_retention_days CHECK (retention_days BETWEEN 1 AND 3650)
                )
            '''

            # Create alert_rules table
            create_alert_rules = '''
                CREATE TABLE IF NOT EXISTS telemetry.alert_rules (
                    id SERIAL PRIMARY KEY,
                    rule_id VARCHAR(64) NOT NULL UNIQUE,
                    name VARCHAR(200) NOT NULL,
                    description VARCHAR(1000),
                    metric_name VARCHAR(100) NOT NULL,
                    condition VARCHAR(500) NOT NULL,
                    threshold_value TEXT NOT NULL,
                    evaluation_window INTEGER DEFAULT 300,
                    trigger_count INTEGER DEFAULT 1,
                    level VARCHAR(20) NOT NULL DEFAULT 'warning',
                    device_ids TEXT[],
                    device_groups TEXT[],
                    device_filters JSONB DEFAULT '{}',
                    notification_channels TEXT[],
                    cooldown_minutes INTEGER DEFAULT 15,
                    auto_resolve BOOLEAN DEFAULT TRUE,
                    auto_resolve_timeout INTEGER DEFAULT 3600,
                    enabled BOOLEAN DEFAULT TRUE,
                    tags TEXT[],
                    total_triggers INTEGER DEFAULT 0,
                    last_triggered TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    created_by VARCHAR(100) NOT NULL,
                    CONSTRAINT check_alert_level CHECK (level IN ('info', 'warning', 'error', 'critical', 'emergency'))
                )
            '''

            with self.db:
                self.db.execute(create_metric_definitions, schema=self.schema)
                self.db.execute(create_alert_rules, schema=self.schema)
                logger.info("Telemetry tables ensured")

        except Exception as e:
            logger.warning(f"Could not ensure schema/tables (may already exist): {e}")

    def _convert_protobuf_to_native(self, value: Any) -> Any:
        """Convert Protobuf types to native Python types"""
        if isinstance(value, (ListValue, Struct)):
            return MessageToDict(value)
        return value

    # ============ Telemetry Data Operations ============

    async def ingest_data_points(self, device_id: str, data_points: List[TelemetryDataPoint]) -> Dict[str, Any]:
        """Ingest multiple telemetry data points"""
        try:
            ingested_count = 0
            failed_count = 0

            for data_point in data_points:
                success = await self.ingest_single_point(device_id, data_point)
                if success:
                    ingested_count += 1
                else:
                    failed_count += 1

            return {
                "success": True,
                "ingested_count": ingested_count,
                "failed_count": failed_count
            }

        except Exception as e:
            logger.error(f"Error ingesting data points: {e}")
            return {
                "success": False,
                "ingested_count": 0,
                "failed_count": len(data_points)
            }

    async def ingest_single_point(self, device_id: str, data_point: TelemetryDataPoint) -> bool:
        """Ingest a single telemetry data point"""
        try:
            # Determine which value field to use based on data type
            value_numeric = None
            value_string = None
            value_boolean = None
            value_json = None

            if isinstance(data_point.value, (int, float)):
                value_numeric = float(data_point.value)
            elif isinstance(data_point.value, str):
                value_string = data_point.value
            elif isinstance(data_point.value, bool):
                value_boolean = data_point.value
            elif isinstance(data_point.value, dict):
                value_json = data_point.value

            query = f'''
                INSERT INTO {self.schema}.{self.data_table} (
                    time, device_id, metric_name, value_numeric, value_string,
                    value_boolean, value_json, unit, tags, metadata, quality
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (time, device_id, metric_name) DO UPDATE
                SET value_numeric = EXCLUDED.value_numeric,
                    value_string = EXCLUDED.value_string,
                    value_boolean = EXCLUDED.value_boolean,
                    value_json = EXCLUDED.value_json,
                    unit = EXCLUDED.unit,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    quality = EXCLUDED.quality
            '''

            params = [
                data_point.timestamp,
                device_id,
                data_point.metric_name,
                value_numeric,
                value_string,
                value_boolean,
                value_json,
                data_point.unit,
                data_point.tags or {},
                data_point.metadata or {},
                100  # Default quality
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count >= 0

        except Exception as e:
            logger.error(f"Error ingesting single data point: {e}")
            return False

    async def query_telemetry_data(
        self,
        device_id: Optional[str] = None,
        metric_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query telemetry data with filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if device_id:
                param_count += 1
                conditions.append(f"device_id = ${param_count}")
                params.append(device_id)

            if metric_names:
                param_count += 1
                conditions.append(f"metric_name = ANY(${param_count})")
                params.append(metric_names)

            if start_time:
                param_count += 1
                conditions.append(f"time >= ${param_count}")
                params.append(start_time)

            if end_time:
                param_count += 1
                conditions.append(f"time <= ${param_count}")
                params.append(end_time)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            param_count += 1
            limit_param = f"${param_count}"
            params.append(limit)

            query = f'''
                SELECT * FROM {self.schema}.{self.data_table}
                {where_clause}
                ORDER BY time DESC
                LIMIT {limit_param}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                data_points = []
                for row in results:
                    # Determine the value based on which field is set
                    value = None
                    if row.get('value_numeric') is not None:
                        value = row['value_numeric']
                    elif row.get('value_string') is not None:
                        value = row['value_string']
                    elif row.get('value_boolean') is not None:
                        value = row['value_boolean']
                    elif row.get('value_json') is not None:
                        value = self._convert_protobuf_to_native(row['value_json'])

                    data_points.append({
                        "time": row["time"],
                        "timestamp": row["time"],  # Keep both for compatibility
                        "device_id": row["device_id"],
                        "metric_name": row["metric_name"],
                        "value": value,
                        "unit": row.get("unit"),
                        "tags": self._convert_protobuf_to_native(row.get("tags", {})),
                        "metadata": self._convert_protobuf_to_native(row.get("metadata", {})),
                        "value_numeric": row.get("value_numeric"),
                        "value_string": row.get("value_string"),
                        "value_boolean": row.get("value_boolean"),
                        "value_json": row.get("value_json")
                    })
                return data_points

            return []

        except Exception as e:
            logger.error(f"Error querying telemetry data: {e}")
            return []

    # ============ Metric Definition Operations ============

    async def create_metric_definition(self, metric_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a metric definition"""
        try:
            # First check if metric with this name already exists
            existing = await self.get_metric_definition(metric_def["name"])
            if existing:
                logger.info(f"Metric definition '{metric_def['name']}' already exists, returning existing")
                return existing

            metric_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.metric_definitions_table} (
                    metric_id, name, description, data_type, metric_type,
                    unit, min_value, max_value, retention_days, aggregation_interval,
                    tags, metadata, created_by, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING *
            '''

            params = [
                metric_id,
                metric_def["name"],
                metric_def.get("description"),
                metric_def["data_type"],
                metric_def.get("metric_type", "gauge"),
                metric_def.get("unit"),
                metric_def.get("min_value"),
                metric_def.get("max_value"),
                metric_def.get("retention_days", 90),
                metric_def.get("aggregation_interval", 60),
                metric_def.get("tags", []),
                metric_def.get("metadata", {}),
                metric_def.get("created_by", "system"),
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                result = results[0]
                # Ensure metadata and tags are never None
                if result.get("metadata") is None:
                    result["metadata"] = {}
                if result.get("tags") is None:
                    result["tags"] = []
                return result

            return None

        except Exception as e:
            logger.error(f"Error creating metric definition: {e}")
            # If it's a duplicate key error, try to return the existing metric
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                existing = await self.get_metric_definition(metric_def["name"])
                if existing:
                    return existing
            return None

    async def get_metric_definition(self, name: str) -> Optional[Dict[str, Any]]:
        """Get metric definition by name"""
        try:
            query = f'SELECT * FROM {self.schema}.{self.metric_definitions_table} WHERE name = $1'

            with self.db:
                results = self.db.query(query, [name], schema=self.schema)

            if results and len(results) > 0:
                result = results[0]
                # Ensure metadata is never None
                if result.get("metadata") is None:
                    result["metadata"] = {}
                if result.get("tags") is None:
                    result["tags"] = []
                return result

            return None

        except Exception as e:
            logger.error(f"Error getting metric definition: {e}")
            return None

    # ============ Alert Rule Operations ============

    async def create_alert_rule(self, rule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create an alert rule"""
        try:
            rule_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.alert_rules_table} (
                    rule_id, name, description, metric_name, condition,
                    threshold_value, evaluation_window, trigger_count, level,
                    device_ids, device_groups, device_filters, notification_channels,
                    cooldown_minutes, auto_resolve, auto_resolve_timeout, enabled,
                    tags, total_triggers, last_triggered, created_by, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
                RETURNING *
            '''

            params = [
                rule_id,
                rule_data["name"],
                rule_data.get("description"),
                rule_data["metric_name"],
                rule_data["condition"],
                rule_data["threshold_value"],
                rule_data.get("evaluation_window", 300),
                rule_data.get("trigger_count", 1),
                rule_data.get("level", "warning"),
                rule_data.get("device_ids", []),
                rule_data.get("device_groups", []),
                rule_data.get("device_filters", {}),
                rule_data.get("notification_channels", []),
                rule_data.get("cooldown_minutes", 15),
                rule_data.get("auto_resolve", True),
                rule_data.get("auto_resolve_timeout", 3600),
                rule_data.get("enabled", True),
                rule_data.get("tags", []),
                0,  # total_triggers
                None,  # last_triggered
                rule_data.get("created_by", "system"),
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                result = results[0]
                # Ensure arrays and JSONB fields are never None
                if result.get("device_ids") is None:
                    result["device_ids"] = []
                if result.get("device_groups") is None:
                    result["device_groups"] = []
                if result.get("device_filters") is None:
                    result["device_filters"] = {}
                if result.get("notification_channels") is None:
                    result["notification_channels"] = []
                if result.get("tags") is None:
                    result["tags"] = []
                return result

            return None

        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
            return None

    async def list_alert_rules(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """List alert rules"""
        try:
            where_clause = "WHERE enabled = $1" if enabled_only else ""
            params = [True] if enabled_only else []

            query = f'''
                SELECT * FROM {self.schema}.{self.alert_rules_table}
                {where_clause}
                ORDER BY created_at DESC
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error listing alert rules: {e}")
            return []

    # ============ Alert Operations ============

    async def create_alert(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create an alert"""
        try:
            alert_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.alerts_table} (
                    alert_id, rule_id, rule_name, device_id, metric_name,
                    level, status, message, current_value, threshold_value,
                    triggered_at, auto_resolve_at, affected_devices_count,
                    tags, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING *
            '''

            auto_resolve_at = None
            if alert_data.get("auto_resolve_timeout"):
                auto_resolve_at = now + timedelta(seconds=alert_data["auto_resolve_timeout"])

            params = [
                alert_id,
                alert_data["rule_id"],
                alert_data["rule_name"],
                alert_data["device_id"],
                alert_data["metric_name"],
                alert_data["level"],
                alert_data.get("status", "active"),
                alert_data["message"],
                str(alert_data["current_value"]),
                str(alert_data["threshold_value"]),
                now,
                auto_resolve_at,
                alert_data.get("affected_devices_count", 1),
                alert_data.get("tags", []),
                alert_data.get("metadata", {})
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return results[0]

            return None

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None

    async def list_alerts(
        self,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List alerts with filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if device_id:
                param_count += 1
                conditions.append(f"device_id = ${param_count}")
                params.append(device_id)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status)

            if level:
                param_count += 1
                conditions.append(f"level = ${param_count}")
                params.append(level)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            param_count += 1
            limit_param = f"${param_count}"
            params.append(limit)

            query = f'''
                SELECT * FROM {self.schema}.{self.alerts_table}
                {where_clause}
                ORDER BY triggered_at DESC
                LIMIT {limit_param}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error listing alerts: {e}")
            return []

    # ============ Statistics Operations ============

    async def get_device_stats(self, device_id: str) -> Dict[str, Any]:
        """Get statistics for a specific device"""
        try:
            # Count total data points
            count_query = f'''
                SELECT COUNT(*) as total_points
                FROM {self.schema}.{self.data_table}
                WHERE device_id = $1
            '''

            # Get active metrics
            metrics_query = f'''
                SELECT DISTINCT metric_name
                FROM {self.schema}.{self.data_table}
                WHERE device_id = $1
            '''

            # Get latest data point
            latest_query = f'''
                SELECT time as last_data_received
                FROM {self.schema}.{self.data_table}
                WHERE device_id = $1
                ORDER BY time DESC
                LIMIT 1
            '''

            with self.db:
                count_results = self.db.query(count_query, [device_id], schema=self.schema)
                metrics_results = self.db.query(metrics_query, [device_id], schema=self.schema)
                latest_results = self.db.query(latest_query, [device_id], schema=self.schema)

            total_points = count_results[0]['total_points'] if count_results else 0
            active_metrics = len(metrics_results) if metrics_results else 0
            last_data_received = latest_results[0]['last_data_received'] if latest_results else None

            return {
                "device_id": device_id,
                "total_points": total_points,
                "active_metrics": active_metrics,
                "last_data_received": last_data_received,
                "metrics": [m["metric_name"] for m in metrics_results] if metrics_results else []
            }

        except Exception as e:
            logger.error(f"Error getting device stats: {e}")
            return {}

    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global telemetry statistics"""
        try:
            # Total devices
            devices_query = f'''
                SELECT COUNT(DISTINCT device_id) as total_devices
                FROM {self.schema}.{self.data_table}
            '''

            # Total data points
            points_query = f'''
                SELECT COUNT(*) as total_points
                FROM {self.schema}.{self.data_table}
            '''

            # Total metrics
            metrics_query = f'''
                SELECT COUNT(DISTINCT metric_name) as total_metrics
                FROM {self.schema}.{self.data_table}
            '''

            # Active alerts
            alerts_query = f'''
                SELECT COUNT(*) as active_alerts
                FROM {self.schema}.{self.alerts_table}
                WHERE status = $1
            '''

            with self.db:
                devices_results = self.db.query(devices_query, [], schema=self.schema)
                points_results = self.db.query(points_query, [], schema=self.schema)
                metrics_results = self.db.query(metrics_query, [], schema=self.schema)
                alerts_results = self.db.query(alerts_query, ["active"], schema=self.schema)

            return {
                "total_devices": devices_results[0]['total_devices'] if devices_results else 0,
                "total_points": points_results[0]['total_points'] if points_results else 0,
                "total_metrics": metrics_results[0]['total_metrics'] if metrics_results else 0,
                "active_alerts": alerts_results[0]['active_alerts'] if alerts_results else 0
            }

        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return {}

    # ============ Additional Missing Methods ============

    async def get_metric_definition_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Alias for get_metric_definition"""
        return await self.get_metric_definition(name)

    async def list_metric_definitions(
        self,
        data_type: Optional[str] = None,
        metric_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List metric definitions with optional filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if data_type:
                param_count += 1
                conditions.append(f"data_type = ${param_count}")
                params.append(data_type)

            if metric_type:
                param_count += 1
                conditions.append(f"metric_type = ${param_count}")
                params.append(metric_type)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.metric_definitions_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error listing metric definitions: {e}")
            return []

    async def delete_metric_definition(self, metric_id: str) -> bool:
        """Delete a metric definition"""
        try:
            query = f'DELETE FROM {self.schema}.{self.metric_definitions_table} WHERE metric_id = $1'

            with self.db:
                count = self.db.execute(query, [metric_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting metric definition: {e}")
            return False

    async def get_alert_rules(
        self,
        metric_name: Optional[str] = None,
        enabled_only: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get alert rules with optional filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if metric_name:
                param_count += 1
                conditions.append(f"metric_name = ${param_count}")
                params.append(metric_name)

            if enabled_only is not None:
                param_count += 1
                conditions.append(f"enabled = ${param_count}")
                params.append(enabled_only)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.alert_rules_table}
                {where_clause}
                ORDER BY created_at DESC
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results:
                # Ensure arrays and JSONB fields are never None for all results
                for result in results:
                    if result.get("device_ids") is None:
                        result["device_ids"] = []
                    else:
                        result["device_ids"] = self._convert_protobuf_to_native(result["device_ids"])
                    if result.get("device_groups") is None:
                        result["device_groups"] = []
                    else:
                        result["device_groups"] = self._convert_protobuf_to_native(result["device_groups"])
                    if result.get("device_filters") is None:
                        result["device_filters"] = {}
                    else:
                        result["device_filters"] = self._convert_protobuf_to_native(result["device_filters"])
                    if result.get("notification_channels") is None:
                        result["notification_channels"] = []
                    else:
                        result["notification_channels"] = self._convert_protobuf_to_native(result["notification_channels"])
                    if result.get("tags") is None:
                        result["tags"] = []
                    else:
                        result["tags"] = self._convert_protobuf_to_native(result["tags"])
                return results

            return []

        except Exception as e:
            logger.error(f"Error getting alert rules: {e}")
            return []

    async def get_alert_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a single alert rule by ID"""
        try:
            query = f'SELECT * FROM {self.schema}.{self.alert_rules_table} WHERE rule_id = $1'

            with self.db:
                results = self.db.query(query, [rule_id], schema=self.schema)

            if results and len(results) > 0:
                result = results[0]
                # Ensure arrays and JSONB fields are never None
                if result.get("device_ids") is None:
                    result["device_ids"] = []
                if result.get("device_groups") is None:
                    result["device_groups"] = []
                if result.get("device_filters") is None:
                    result["device_filters"] = {}
                if result.get("notification_channels") is None:
                    result["notification_channels"] = []
                if result.get("tags") is None:
                    result["tags"] = []
                return result

            return None

        except Exception as e:
            logger.error(f"Error getting alert rule: {e}")
            return None

    async def update_alert_rule(self, rule_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an alert rule"""
        try:
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            if not set_clauses:
                return False

            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            # Add rule_id for WHERE clause
            param_count += 1
            params.append(rule_id)

            query = f'''
                UPDATE {self.schema}.{self.alert_rules_table}
                SET {', '.join(set_clauses)}
                WHERE rule_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating alert rule: {e}")
            return False

    async def update_alert_rule_stats(self, rule_id: str) -> bool:
        """Update alert rule statistics (increment trigger count)"""
        try:
            now = datetime.now(timezone.utc)
            query = f'''
                UPDATE {self.schema}.{self.alert_rules_table}
                SET total_triggers = total_triggers + 1,
                    last_triggered = $1,
                    updated_at = $2
                WHERE rule_id = $3
            '''

            with self.db:
                count = self.db.execute(query, [now, now, rule_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating alert rule stats: {e}")
            return False

    async def get_alerts(
        self,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get alerts with optional filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if device_id:
                param_count += 1
                conditions.append(f"device_id = ${param_count}")
                params.append(device_id)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status)

            if level:
                param_count += 1
                conditions.append(f"level = ${param_count}")
                params.append(level)

            if start_time:
                param_count += 1
                conditions.append(f"triggered_at >= ${param_count}")
                params.append(start_time)

            if end_time:
                param_count += 1
                conditions.append(f"triggered_at <= ${param_count}")
                params.append(end_time)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.alerts_table}
                {where_clause}
                ORDER BY triggered_at DESC
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

    async def get_alerts_by_device(
        self,
        device_id: str,
        start_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get alerts for a specific device"""
        return await self.get_alerts(
            device_id=device_id,
            start_time=start_time
        )

    async def update_alert(self, alert_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an alert"""
        try:
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            if not set_clauses:
                return False

            # Add alert_id for WHERE clause
            param_count += 1
            params.append(alert_id)

            query = f'''
                UPDATE {self.schema}.{self.alerts_table}
                SET {', '.join(set_clauses)}
                WHERE alert_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating alert: {e}")
            return False

    async def disable_device_alert_rules(self, device_id: str) -> int:
        """
        Disable all alert rules for a specific device

        Args:
            device_id: The device ID

        Returns:
            int: Number of alert rules disabled
        """
        try:
            query = f'''
                UPDATE {self.schema}.{self.alert_rules_table}
                SET enabled = $1, updated_at = CURRENT_TIMESTAMP
                WHERE $2 = ANY(device_ids)
                AND enabled = true
            '''

            with self.db:
                count = self.db.execute(
                    query,
                    [False, device_id],
                    schema=self.schema
                )

            return count if count else 0

        except Exception as e:
            logger.error(f"Error disabling device alert rules: {e}")
            return 0
