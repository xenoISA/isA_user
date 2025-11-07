"""
Telemetry Service - Business Logic

遥测服务业务逻辑，处理设备数据采集、存储、查询和警报
"""

import secrets
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union
import logging
from collections import defaultdict
import statistics

from .models import (
    DataType, MetricType, AlertLevel, AlertStatus, AggregationType,
    TelemetryDataPoint, MetricDefinitionResponse, TelemetryDataResponse,
    AlertRuleResponse, AlertResponse, DeviceTelemetryStatsResponse,
    TelemetryStatsResponse, RealTimeDataResponse, AggregatedDataResponse
)
from .telemetry_repository import TelemetryRepository
from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger("telemetry_service")


class TelemetryService:
    """遥测服务"""

    def __init__(self, event_bus=None, config=None):
        # Initialize repository for PostgreSQL storage
        self.repository = TelemetryRepository(config=config)

        # Event bus for publishing events
        self.event_bus = event_bus

        # Keep in-memory structures for features not yet in repository
        self.real_time_subscribers = {}  # 实时订阅

        # 配置
        self.max_batch_size = 1000
        self.max_query_points = 10000
        self.default_retention_days = 90
        
    async def ingest_telemetry_data(self, device_id: str, data_points: List[TelemetryDataPoint]) -> Dict[str, Any]:
        """摄取遥测数据"""
        try:
            # Use repository to ingest data
            result = await self.repository.ingest_data_points(device_id, data_points)

            # Process each point for alerts and real-time notifications
            for data_point in data_points:
                try:
                    # 验证数据点
                    await self._validate_data_point(device_id, data_point)

                    # 检查警报规则
                    await self._check_alert_rules(device_id, data_point)

                    # 发送实时数据到订阅者
                    await self._notify_real_time_subscribers(device_id, data_point)

                except Exception as e:
                    logger.error(f"Error processing data point for {device_id}: {e}")

            result["total_count"] = len(data_points)
            result["errors"] = []

            logger.info(f"Ingested {result['ingested_count']}/{len(data_points)} data points for device {device_id}")

            # Publish telemetry.data.received event
            if self.event_bus and result.get('ingested_count', 0) > 0:
                try:
                    event = Event(
                        event_type=EventType.TELEMETRY_DATA_RECEIVED,
                        source=ServiceSource.TELEMETRY_SERVICE,
                        data={
                            "device_id": device_id,
                            "metrics_count": len(set(dp.metric_name for dp in data_points)),
                            "points_count": result['ingested_count'],
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish telemetry.data.received event: {e}")

            return result

        except Exception as e:
            logger.error(f"Error in data ingestion: {e}")
            return {
                "success": False,
                "error": str(e),
                "ingested_count": 0,
                "failed_count": len(data_points),
                "total_count": len(data_points)
            }
    
    async def create_metric_definition(self, user_id: str, metric_data: Dict[str, Any]) -> Optional[MetricDefinitionResponse]:
        """创建指标定义"""
        try:
            # Prepare data for repository
            metric_def_data = {
                "name": metric_data["name"],
                "description": metric_data.get("description"),
                "data_type": metric_data["data_type"],
                "metric_type": metric_data.get("metric_type", MetricType.GAUGE.value),
                "unit": metric_data.get("unit"),
                "min_value": metric_data.get("min_value"),
                "max_value": metric_data.get("max_value"),
                "retention_days": metric_data.get("retention_days", self.default_retention_days),
                "aggregation_interval": metric_data.get("aggregation_interval", 60),
                "tags": metric_data.get("tags", []),
                "metadata": metric_data.get("metadata", {}),
                "created_by": user_id
            }

            # Create in repository
            result = await self.repository.create_metric_definition(metric_def_data)

            if result:
                metric_definition = MetricDefinitionResponse(
                    metric_id=result["metric_id"],
                    name=result["name"],
                    description=result.get("description"),
                    data_type=DataType(result["data_type"]),
                    metric_type=MetricType(result["metric_type"]),
                    unit=result.get("unit"),
                    min_value=result.get("min_value"),
                    max_value=result.get("max_value"),
                    retention_days=result["retention_days"],
                    aggregation_interval=result["aggregation_interval"],
                    tags=result.get("tags", []),
                    metadata=result.get("metadata", {}),
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                    created_by=result["created_by"]
                )

                logger.info(f"Metric definition created: {metric_definition.name}")

                # Publish metric.defined event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.METRIC_DEFINED,
                            source=ServiceSource.TELEMETRY_SERVICE,
                            data={
                                "metric_id": metric_definition.metric_id,
                                "name": metric_definition.name,
                                "data_type": metric_definition.data_type.value,
                                "metric_type": metric_definition.metric_type.value,
                                "unit": metric_definition.unit,
                                "created_by": user_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish metric.defined event: {e}")

                return metric_definition

            return None

        except Exception as e:
            logger.error(f"Error creating metric definition: {e}")
            return None
    
    async def create_alert_rule(self, user_id: str, rule_data: Dict[str, Any]) -> Optional[AlertRuleResponse]:
        """创建警报规则"""
        try:
            # Prepare data for repository
            alert_rule_data = {
                "name": rule_data["name"],
                "description": rule_data.get("description"),
                "metric_name": rule_data["metric_name"],
                "condition": rule_data["condition"],
                "threshold_value": str(rule_data["threshold_value"]),
                "evaluation_window": rule_data.get("evaluation_window", 300),
                "trigger_count": rule_data.get("trigger_count", 1),
                "level": rule_data.get("level", AlertLevel.WARNING.value if hasattr(AlertLevel.WARNING, 'value') else "warning"),
                "device_ids": rule_data.get("device_ids", []),
                "device_groups": rule_data.get("device_groups", []),
                "device_filters": rule_data.get("device_filters", {}),
                "notification_channels": rule_data.get("notification_channels", []),
                "cooldown_minutes": rule_data.get("cooldown_minutes", 15),
                "auto_resolve": rule_data.get("auto_resolve", True),
                "auto_resolve_timeout": rule_data.get("auto_resolve_timeout", 3600),
                "enabled": rule_data.get("enabled", True),
                "tags": rule_data.get("tags", []),
                "created_by": user_id
            }

            # Create in repository
            result = await self.repository.create_alert_rule(alert_rule_data)

            if result:
                alert_rule = AlertRuleResponse(
                    rule_id=result["rule_id"],
                    name=result["name"],
                    description=result.get("description"),
                    metric_name=result["metric_name"],
                    condition=result["condition"],
                    threshold_value=result["threshold_value"],
                    evaluation_window=result["evaluation_window"],
                    trigger_count=result["trigger_count"],
                    level=AlertLevel(result["level"]),
                    device_ids=result.get("device_ids", []),
                    device_groups=result.get("device_groups", []),
                    device_filters=result.get("device_filters", {}),
                    notification_channels=result.get("notification_channels", []),
                    cooldown_minutes=result["cooldown_minutes"],
                    auto_resolve=result["auto_resolve"],
                    auto_resolve_timeout=result["auto_resolve_timeout"],
                    enabled=result["enabled"],
                    tags=result.get("tags", []),
                    total_triggers=result["total_triggers"],
                    last_triggered=result.get("last_triggered"),
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                    created_by=result["created_by"]
                )

                logger.info(f"Alert rule created: {rule_data['name']}")

                # Publish alert.rule.created event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.ALERT_RULE_CREATED,
                            source=ServiceSource.TELEMETRY_SERVICE,
                            data={
                                "rule_id": alert_rule.rule_id,
                                "name": alert_rule.name,
                                "metric_name": alert_rule.metric_name,
                                "condition": alert_rule.condition,
                                "threshold_value": alert_rule.threshold_value,
                                "level": alert_rule.level.value,
                                "enabled": alert_rule.enabled,
                                "created_by": user_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish alert.rule.created event: {e}")

                return alert_rule

            return None

        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
            return None
    
    async def query_telemetry_data(self, query_params: Dict[str, Any]) -> Optional[TelemetryDataResponse]:
        """查询遥测数据"""
        try:
            # Support both old and new field names for backwards compatibility
            device_ids = query_params.get("devices") or query_params.get("device_ids", [])
            metric_names = query_params.get("metrics") or query_params.get("metric_names", [])
            start_time = query_params["start_time"]
            end_time = query_params["end_time"]
            aggregation = query_params.get("aggregation")
            interval = query_params.get("interval")
            limit = query_params.get("limit", 1000)

            all_data_points = []

            # Query from repository for each device
            if device_ids:
                for device_id in device_ids:
                    raw_data = await self.repository.query_telemetry_data(
                        device_id=device_id,
                        metric_names=metric_names,
                        start_time=start_time,
                        end_time=end_time,
                        limit=limit
                    )

                    # Convert to TelemetryDataPoint objects
                    for point in raw_data:
                        # Determine which value field is populated
                        value = None
                        if point.get("value_numeric") is not None:
                            value = point["value_numeric"]
                        elif point.get("value_string") is not None:
                            value = point["value_string"]
                        elif point.get("value_boolean") is not None:
                            value = point["value_boolean"]
                        elif point.get("value_json") is not None:
                            value = point["value_json"]

                        data_point = TelemetryDataPoint(
                            timestamp=point["time"],
                            metric_name=point["metric_name"],
                            value=value,
                            unit=point.get("unit"),
                            tags=point.get("tags", {}),
                            metadata=point.get("metadata", {})
                        )
                        all_data_points.append(data_point)
            else:
                # Query all devices if no device_ids specified
                raw_data = await self.repository.query_telemetry_data(
                    device_id=None,
                    metric_names=metric_names,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit
                )

                for point in raw_data:
                    value = None
                    if point.get("value_numeric") is not None:
                        value = point["value_numeric"]
                    elif point.get("value_string") is not None:
                        value = point["value_string"]
                    elif point.get("value_boolean") is not None:
                        value = point["value_boolean"]
                    elif point.get("value_json") is not None:
                        value = point["value_json"]

                    data_point = TelemetryDataPoint(
                        timestamp=point["time"],
                        metric_name=point["metric_name"],
                        value=value,
                        unit=point.get("unit"),
                        tags=point.get("tags", {}),
                        metadata=point.get("metadata", {})
                    )
                    all_data_points.append(data_point)

            # 聚合处理
            if aggregation and interval:
                all_data_points = await self._aggregate_data_points(
                    all_data_points, aggregation, interval
                )

            response = TelemetryDataResponse(
                device_id=device_ids[0] if device_ids and len(device_ids) == 1 else "multiple",
                metric_name=metric_names[0] if metric_names and len(metric_names) == 1 else "multiple",
                data_points=all_data_points,
                count=len(all_data_points),
                aggregation=aggregation,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )

            logger.info(f"Queried {len(all_data_points)} data points")
            return response

        except Exception as e:
            logger.error(f"Error querying telemetry data: {e}")
            return None
    
    async def get_device_stats(self, device_id: str) -> Optional[DeviceTelemetryStatsResponse]:
        """获取设备遥测统计"""
        try:
            # Get device stats from repository
            stats_data = await self.repository.get_device_stats(device_id)

            # Return stats with zeros if no data (better UX than 404)
            if not stats_data or stats_data.get("total_points", 0) == 0:
                logger.info(f"No telemetry data found for device {device_id}, returning zero stats")
                return DeviceTelemetryStatsResponse(
                    device_id=device_id,
                    total_metrics=0,
                    active_metrics=0,
                    data_points_count=0,
                    last_update=None,
                    storage_size=0,
                    avg_frequency=0.0,
                    last_24h_points=0,
                    last_24h_alerts=0,
                    metrics_by_type={"gauge": 0, "counter": 0, "histogram": 0},
                    top_metrics=[]
                )

            # Calculate avg frequency (points per minute)
            total_metrics = len(stats_data.get("metrics", []))
            total_points = stats_data.get("total_points", 0)
            avg_frequency = total_points / max(1, total_metrics) / 60 if total_metrics > 0 else 0.0

            # Get 24h alerts count
            last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            last_24h_alerts_data = await self.repository.get_alerts_by_device(
                device_id=device_id,
                start_time=last_24h
            )
            last_24h_alerts = len(last_24h_alerts_data) if last_24h_alerts_data else 0

            # Create response
            stats = DeviceTelemetryStatsResponse(
                device_id=device_id,
                total_metrics=total_metrics,
                active_metrics=total_metrics,  # All metrics with data are active
                data_points_count=total_points,
                last_update=stats_data.get("last_update"),
                storage_size=total_points * 100,  # 估算存储大小
                avg_frequency=avg_frequency,
                last_24h_points=stats_data.get("last_24h_points", 0),
                last_24h_alerts=last_24h_alerts,
                metrics_by_type={
                    "gauge": total_metrics,  # Simplified - treat all as gauge
                    "counter": 0,
                    "histogram": 0
                },
                top_metrics=[
                    {"name": metric, "points": total_points // max(1, total_metrics)}
                    for metric in stats_data.get("metrics", [])[:5]
                ]
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting device stats: {e}")
            return None
    
    async def get_service_stats(self) -> Optional[TelemetryStatsResponse]:
        """获取服务统计"""
        try:
            # Get global stats from repository
            global_stats = await self.repository.get_global_stats()

            # Return stats with zeros if no data (better UX than 404)
            if not global_stats or global_stats.get("total_points", 0) == 0:
                logger.info("No telemetry data available in the service, returning zero stats")
                return TelemetryStatsResponse(
                    total_devices=0,
                    active_devices=0,
                    total_metrics=0,
                    total_data_points=0,
                    storage_size=0,
                    points_per_second=0.0,
                    avg_latency=0.0,
                    error_rate=0.0,
                    last_24h_points=0,
                    last_24h_devices=0,
                    last_24h_alerts=0,
                    devices_by_type={},
                    metrics_by_type={},
                    data_by_hour=[]
                )

            total_devices = global_stats.get("total_devices", 0)
            total_metrics = global_stats.get("total_metrics", 0)
            total_points = global_stats.get("total_points", 0)
            last_24h_points = global_stats.get("last_24h_points", 0)

            # Get 24h alerts count
            last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            last_24h_alerts_data = await self.repository.get_alerts(
                start_time=last_24h
            )
            last_24h_alerts = len(last_24h_alerts_data) if last_24h_alerts_data else 0

            # Calculate points per second
            points_per_second = last_24h_points / 86400 if last_24h_points > 0 else 0.0

            stats = TelemetryStatsResponse(
                total_devices=total_devices,
                active_devices=total_devices,  # Simplified - assume all devices are active
                total_metrics=total_metrics,
                total_data_points=total_points,
                storage_size=total_points * 100,  # 估算存储大小
                points_per_second=points_per_second,
                avg_latency=50.0,  # 模拟延迟 - can be enhanced with real metrics
                error_rate=1.5,  # 模拟错误率 - can be enhanced with real metrics
                last_24h_points=last_24h_points,
                last_24h_devices=total_devices,
                last_24h_alerts=last_24h_alerts,
                devices_by_type={
                    "sensor": total_devices // 2 if total_devices > 0 else 0,
                    "gateway": total_devices // 4 if total_devices > 0 else 0,
                    "camera": total_devices // 4 if total_devices > 0 else 0
                },
                metrics_by_type={
                    "gauge": total_metrics // 2 if total_metrics > 0 else 0,
                    "counter": total_metrics // 3 if total_metrics > 0 else 0,
                    "histogram": total_metrics // 6 if total_metrics > 0 else 0
                },
                data_by_hour=[
                    {"hour": i, "points": last_24h_points // 24 if last_24h_points > 0 else 0}
                    for i in range(24)
                ]
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return None
    
    async def subscribe_real_time(self, subscription_data: Dict[str, Any]) -> str:
        """创建实时数据订阅"""
        try:
            subscription_id = secrets.token_hex(16)
            self.real_time_subscribers[subscription_id] = {
                "device_ids": subscription_data.get("device_ids", []),
                "metric_names": subscription_data.get("metric_names", []),
                "tags": subscription_data.get("tags", {}),
                "filter_condition": subscription_data.get("filter_condition"),
                "max_frequency": subscription_data.get("max_frequency", 1000),
                "created_at": datetime.now(timezone.utc),
                "last_sent": datetime.now(timezone.utc)
            }
            
            logger.info(f"Real-time subscription created: {subscription_id}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None
    
    async def unsubscribe_real_time(self, subscription_id: str) -> bool:
        """取消实时数据订阅"""
        try:
            if subscription_id in self.real_time_subscribers:
                del self.real_time_subscribers[subscription_id]
                logger.info(f"Real-time subscription cancelled: {subscription_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False
    
    async def get_aggregated_data(self, query_params: Dict[str, Any]) -> Optional[AggregatedDataResponse]:
        """获取聚合数据"""
        try:
            device_id = query_params.get("device_id")
            metric_name = query_params["metric_name"]
            aggregation_type = query_params["aggregation_type"]
            interval = query_params["interval"]
            start_time = query_params["start_time"]
            end_time = query_params["end_time"]

            # Get raw data from repository
            raw_data_results = await self.repository.query_telemetry_data(
                device_id=device_id,
                metric_names=[metric_name],
                start_time=start_time,
                end_time=end_time,
                limit=10000  # Higher limit for aggregation
            )

            # Convert to the format expected by _aggregate_by_interval
            raw_data = []
            for point in raw_data_results:
                # Determine which value field is populated
                value = None
                if point.get("value_numeric") is not None:
                    value = point["value_numeric"]
                elif point.get("value_string") is not None:
                    value = point["value_string"]
                elif point.get("value_boolean") is not None:
                    value = point["value_boolean"]
                elif point.get("value_json") is not None:
                    value = point["value_json"]

                raw_data.append({
                    "timestamp": point["time"],
                    "value": value
                })

            # 按时间间隔分组聚合
            aggregated_points = await self._aggregate_by_interval(
                raw_data, aggregation_type, interval, start_time, end_time
            )

            response = AggregatedDataResponse(
                device_id=device_id,
                metric_name=metric_name,
                aggregation_type=aggregation_type,
                interval=interval,
                data_points=aggregated_points,
                start_time=start_time,
                end_time=end_time,
                count=len(aggregated_points)
            )

            return response

        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}")
            return None
    
    # Private helper methods
    
    async def _validate_data_point(self, device_id: str, data_point: TelemetryDataPoint):
        """验证数据点"""
        try:
            # Check if metric definition exists in repository
            metric_def_data = await self.repository.get_metric_definition_by_name(data_point.metric_name)

            if metric_def_data:
                # 检查数据类型
                data_type = metric_def_data.get("data_type")
                if data_type == DataType.NUMERIC.value or data_type == "numeric":
                    if not isinstance(data_point.value, (int, float)):
                        raise ValueError(f"Invalid data type for metric {data_point.metric_name}")

                # 检查范围
                min_value = metric_def_data.get("min_value")
                if min_value is not None and isinstance(data_point.value, (int, float)):
                    if data_point.value < min_value:
                        raise ValueError(f"Value below minimum for metric {data_point.metric_name}")

                max_value = metric_def_data.get("max_value")
                if max_value is not None and isinstance(data_point.value, (int, float)):
                    if data_point.value > max_value:
                        raise ValueError(f"Value above maximum for metric {data_point.metric_name}")
        except Exception as e:
            # Log validation errors but don't fail the ingestion
            logger.warning(f"Validation warning for {device_id}:{data_point.metric_name}: {e}")
    
    async def _check_alert_rules(self, device_id: str, data_point: TelemetryDataPoint):
        """检查警报规则"""
        try:
            # Get alert rules from repository
            alert_rules = await self.repository.get_alert_rules(
                metric_name=data_point.metric_name,
                enabled_only=True
            )

            if not alert_rules:
                return

            for rule_data in alert_rules:
                # 检查是否匹配设备
                device_ids = rule_data.get("device_ids", [])
                if device_ids and device_id not in device_ids:
                    continue

                # 评估条件
                condition = rule_data.get("condition")
                threshold_value = rule_data.get("threshold_value")

                if await self._evaluate_alert_condition_simple(condition, threshold_value, data_point):
                    await self._trigger_alert_from_rule(rule_data, device_id, data_point)

        except Exception as e:
            logger.error(f"Error checking alert rules: {e}")
    
    async def _evaluate_alert_condition_simple(self, condition: str, threshold_value: str, data_point: TelemetryDataPoint) -> bool:
        """评估警报条件 (simplified version for rule dict)"""
        try:
            value = data_point.value

            # Try to convert threshold to numeric if possible
            try:
                threshold = float(threshold_value)
            except (ValueError, TypeError):
                threshold = threshold_value

            if condition.startswith(">"):
                return isinstance(value, (int, float)) and isinstance(threshold, (int, float)) and value > threshold
            elif condition.startswith("<"):
                return isinstance(value, (int, float)) and isinstance(threshold, (int, float)) and value < threshold
            elif condition.startswith("=="):
                return value == threshold
            elif condition.startswith("!="):
                return value != threshold

            return False
        except Exception as e:
            logger.error(f"Error evaluating alert condition: {e}")
            return False

    async def _evaluate_alert_condition(self, rule: AlertRuleResponse, data_point: TelemetryDataPoint) -> bool:
        """评估警报条件"""
        return await self._evaluate_alert_condition_simple(rule.condition, rule.threshold_value, data_point)

    async def _trigger_alert_from_rule(self, rule_data: Dict[str, Any], device_id: str, data_point: TelemetryDataPoint):
        """触发警报 (from rule dict)"""
        try:
            now = datetime.now(timezone.utc)

            # Prepare alert data for repository
            alert_data = {
                "rule_id": rule_data["rule_id"],
                "rule_name": rule_data["name"],
                "device_id": device_id,
                "metric_name": rule_data["metric_name"],
                "level": rule_data["level"],
                "status": AlertStatus.ACTIVE.value,
                "message": f"Alert triggered: {rule_data['name']}",
                "current_value": str(data_point.value),
                "threshold_value": rule_data["threshold_value"],
                "triggered_at": now,
                "auto_resolve_at": now + timedelta(seconds=rule_data.get("auto_resolve_timeout", 3600)) if rule_data.get("auto_resolve", True) else None,
                "affected_devices_count": 1,
                "tags": rule_data.get("tags", []),
                "metadata": {"trigger_value": data_point.value}
            }

            # Create alert in repository
            alert_result = await self.repository.create_alert(alert_data)

            if alert_result:
                # Update rule statistics
                await self.repository.update_alert_rule_stats(rule_data["rule_id"])
                logger.warning(f"Alert triggered: {rule_data['name']} for device {device_id}")

                # Publish alert.triggered event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.ALERT_TRIGGERED,
                            source=ServiceSource.TELEMETRY_SERVICE,
                            data={
                                "alert_id": alert_result.get("alert_id"),
                                "rule_id": rule_data["rule_id"],
                                "rule_name": rule_data["name"],
                                "device_id": device_id,
                                "metric_name": rule_data["metric_name"],
                                "level": rule_data["level"],
                                "current_value": str(data_point.value),
                                "threshold_value": rule_data["threshold_value"],
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish alert.triggered event: {e}")

        except Exception as e:
            logger.error(f"Error triggering alert: {e}")

    async def _trigger_alert(self, rule: AlertRuleResponse, device_id: str, data_point: TelemetryDataPoint):
        """触发警报 (from AlertRuleResponse object)"""
        try:
            now = datetime.now(timezone.utc)

            # Prepare alert data for repository
            alert_data = {
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "device_id": device_id,
                "metric_name": rule.metric_name,
                "level": rule.level.value if hasattr(rule.level, 'value') else str(rule.level),
                "status": AlertStatus.ACTIVE.value,
                "message": f"Alert triggered: {rule.name}",
                "current_value": str(data_point.value),
                "threshold_value": rule.threshold_value,
                "triggered_at": now,
                "auto_resolve_at": now + timedelta(seconds=rule.auto_resolve_timeout) if rule.auto_resolve else None,
                "affected_devices_count": 1,
                "tags": rule.tags,
                "metadata": {"trigger_value": data_point.value}
            }

            # Create alert in repository
            alert_result = await self.repository.create_alert(alert_data)

            if alert_result:
                # Update rule statistics
                await self.repository.update_alert_rule_stats(rule.rule_id)
                logger.warning(f"Alert triggered: {rule.name} for device {device_id}")

                # Publish alert.triggered event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.ALERT_TRIGGERED,
                            source=ServiceSource.TELEMETRY_SERVICE,
                            data={
                                "alert_id": alert_result.get("alert_id"),
                                "rule_id": rule.rule_id,
                                "rule_name": rule.name,
                                "device_id": device_id,
                                "metric_name": rule.metric_name,
                                "level": rule.level.value if hasattr(rule.level, 'value') else str(rule.level),
                                "current_value": str(data_point.value),
                                "threshold_value": rule.threshold_value,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish alert.triggered event: {e}")

        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
    
    async def _notify_real_time_subscribers(self, device_id: str, data_point: TelemetryDataPoint):
        """通知实时订阅者"""
        try:
            for sub_id, subscription in self.real_time_subscribers.items():
                # 检查设备过滤
                if subscription["device_ids"] and device_id not in subscription["device_ids"]:
                    continue
                
                # 检查指标过滤
                if subscription["metric_names"] and data_point.metric_name not in subscription["metric_names"]:
                    continue
                
                # 检查频率限制
                now = datetime.now(timezone.utc)
                if (now - subscription["last_sent"]).total_seconds() * 1000 < subscription["max_frequency"]:
                    continue
                
                # 发送实时数据（这里只是模拟，实际应该通过WebSocket等推送）
                real_time_data = RealTimeDataResponse(
                    subscription_id=sub_id,
                    device_id=device_id,
                    data_points=[data_point],
                    timestamp=now,
                    sequence_number=1
                )
                
                subscription["last_sent"] = now
                logger.debug(f"Real-time data sent to subscription {sub_id}")
                
        except Exception as e:
            logger.error(f"Error notifying real-time subscribers: {e}")
    
    async def _aggregate_data_points(self, data_points: List[TelemetryDataPoint], aggregation: AggregationType, interval: int) -> List[TelemetryDataPoint]:
        """聚合数据点"""
        # 简化的聚合实现
        if not data_points:
            return []
        
        # 按时间间隔分组
        grouped = defaultdict(list)
        for point in data_points:
            # 将时间戳对齐到间隔边界
            aligned_time = datetime.fromtimestamp(
                (point.timestamp.timestamp() // interval) * interval
            )
            grouped[aligned_time].append(point)
        
        aggregated = []
        for time_bucket, points in grouped.items():
            if not points:
                continue
                
            values = [p.value for p in points if isinstance(p.value, (int, float))]
            if not values:
                continue
            
            if aggregation == AggregationType.AVG:
                agg_value = statistics.mean(values)
            elif aggregation == AggregationType.MIN:
                agg_value = min(values)
            elif aggregation == AggregationType.MAX:
                agg_value = max(values)
            elif aggregation == AggregationType.SUM:
                agg_value = sum(values)
            elif aggregation == AggregationType.COUNT:
                agg_value = len(values)
            else:
                agg_value = statistics.mean(values)
            
            aggregated.append(TelemetryDataPoint(
                timestamp=time_bucket,
                metric_name=points[0].metric_name,
                value=agg_value,
                unit=points[0].unit,
                tags={"aggregation": aggregation.value}
            ))
        
        return aggregated
    
    async def _aggregate_by_interval(self, raw_data: List[Dict], aggregation_type: AggregationType, 
                                   interval: int, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """按时间间隔聚合数据"""
        if not raw_data:
            return []
        
        # 生成时间桶
        time_buckets = []
        current_time = start_time
        while current_time < end_time:
            time_buckets.append(current_time)
            current_time += timedelta(seconds=interval)
        
        aggregated_points = []
        
        for bucket_start in time_buckets:
            bucket_end = bucket_start + timedelta(seconds=interval)
            
            # 获取时间桶内的数据
            bucket_data = [
                point for point in raw_data
                if bucket_start <= point["timestamp"] < bucket_end
            ]
            
            if not bucket_data:
                continue
            
            values = [point["value"] for point in bucket_data if isinstance(point["value"], (int, float))]
            if not values:
                continue
            
            if aggregation_type == AggregationType.AVG:
                agg_value = statistics.mean(values)
            elif aggregation_type == AggregationType.MIN:
                agg_value = min(values)
            elif aggregation_type == AggregationType.MAX:
                agg_value = max(values)
            elif aggregation_type == AggregationType.SUM:
                agg_value = sum(values)
            elif aggregation_type == AggregationType.COUNT:
                agg_value = len(values)
            else:
                agg_value = statistics.mean(values)
            
            aggregated_points.append({
                "timestamp": bucket_start,
                "value": agg_value
            })
        
        return aggregated_points