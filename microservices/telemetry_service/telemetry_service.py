"""
Telemetry Service - Business Logic

遥测服务业务逻辑，处理设备数据采集、存储、查询和警报
"""

import secrets
import asyncio
import json
from datetime import datetime, timedelta
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

logger = logging.getLogger("telemetry_service")


class TelemetryService:
    """遥测服务"""
    
    def __init__(self):
        # 在生产环境中，这些应该使用专业的时序数据库如InfluxDB、TimescaleDB等
        self.data_store = defaultdict(list)  # 简化的数据存储
        self.metric_definitions = {}  # 指标定义
        self.alert_rules = {}  # 警报规则
        self.active_alerts = {}  # 活跃警报
        self.real_time_subscribers = {}  # 实时订阅
        
        # 配置
        self.max_batch_size = 1000
        self.max_query_points = 10000
        self.default_retention_days = 90
        
    async def ingest_telemetry_data(self, device_id: str, data_points: List[TelemetryDataPoint]) -> Dict[str, Any]:
        """摄取遥测数据"""
        try:
            ingested_count = 0
            failed_count = 0
            errors = []
            
            for data_point in data_points:
                try:
                    # 验证数据点
                    await self._validate_data_point(device_id, data_point)
                    
                    # 存储数据
                    key = f"{device_id}:{data_point.metric_name}"
                    self.data_store[key].append({
                        "timestamp": data_point.timestamp,
                        "value": data_point.value,
                        "unit": data_point.unit,
                        "tags": data_point.tags or {},
                        "metadata": data_point.metadata or {}
                    })
                    
                    # 检查警报规则
                    await self._check_alert_rules(device_id, data_point)
                    
                    # 发送实时数据到订阅者
                    await self._notify_real_time_subscribers(device_id, data_point)
                    
                    ingested_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    errors.append(str(e))
                    logger.error(f"Error ingesting data point for {device_id}: {e}")
            
            result = {
                "success": True,
                "ingested_count": ingested_count,
                "failed_count": failed_count,
                "total_count": len(data_points),
                "errors": errors[:10]  # 最多返回10个错误
            }
            
            logger.info(f"Ingested {ingested_count}/{len(data_points)} data points for device {device_id}")
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
            metric_id = secrets.token_hex(16)
            
            metric_definition = MetricDefinitionResponse(
                metric_id=metric_id,
                name=metric_data["name"],
                description=metric_data.get("description"),
                data_type=metric_data["data_type"],
                metric_type=metric_data.get("metric_type", MetricType.GAUGE),
                unit=metric_data.get("unit"),
                min_value=metric_data.get("min_value"),
                max_value=metric_data.get("max_value"),
                retention_days=metric_data.get("retention_days", self.default_retention_days),
                aggregation_interval=metric_data.get("aggregation_interval", 60),
                tags=metric_data.get("tags", []),
                metadata=metric_data.get("metadata", {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=user_id
            )
            
            self.metric_definitions[metric_definition.name] = metric_definition
            
            logger.info(f"Metric definition created: {metric_definition.name}")
            return metric_definition
            
        except Exception as e:
            logger.error(f"Error creating metric definition: {e}")
            return None
    
    async def create_alert_rule(self, user_id: str, rule_data: Dict[str, Any]) -> Optional[AlertRuleResponse]:
        """创建警报规则"""
        try:
            rule_id = secrets.token_hex(16)
            
            alert_rule = AlertRuleResponse(
                rule_id=rule_id,
                name=rule_data["name"],
                description=rule_data.get("description"),
                metric_name=rule_data["metric_name"],
                condition=rule_data["condition"],
                threshold_value=rule_data["threshold_value"],
                evaluation_window=rule_data.get("evaluation_window", 300),
                trigger_count=rule_data.get("trigger_count", 1),
                level=rule_data.get("level", AlertLevel.WARNING),
                device_ids=rule_data.get("device_ids", []),
                device_groups=rule_data.get("device_groups", []),
                device_filters=rule_data.get("device_filters", {}),
                notification_channels=rule_data.get("notification_channels", []),
                cooldown_minutes=rule_data.get("cooldown_minutes", 15),
                auto_resolve=rule_data.get("auto_resolve", True),
                auto_resolve_timeout=rule_data.get("auto_resolve_timeout", 3600),
                enabled=rule_data.get("enabled", True),
                tags=rule_data.get("tags", []),
                total_triggers=0,
                last_triggered=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=user_id
            )
            
            self.alert_rules[rule_id] = alert_rule
            
            logger.info(f"Alert rule created: {rule_data['name']}")
            return alert_rule
            
        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
            return None
    
    async def query_telemetry_data(self, query_params: Dict[str, Any]) -> Optional[TelemetryDataResponse]:
        """查询遥测数据"""
        try:
            device_ids = query_params.get("device_ids", [])
            metric_names = query_params["metric_names"]
            start_time = query_params["start_time"]
            end_time = query_params["end_time"]
            aggregation = query_params.get("aggregation")
            interval = query_params.get("interval")
            limit = query_params.get("limit", 1000)
            
            all_data_points = []
            
            # 查询每个设备的数据
            for device_id in device_ids or ["all"]:
                for metric_name in metric_names:
                    key = f"{device_id}:{metric_name}"
                    raw_data = self.data_store.get(key, [])
                    
                    # 时间过滤
                    filtered_data = [
                        point for point in raw_data
                        if start_time <= point["timestamp"] <= end_time
                    ]
                    
                    # 限制返回数量
                    filtered_data = filtered_data[:limit]
                    
                    # 转换为数据点格式
                    for point in filtered_data:
                        data_point = TelemetryDataPoint(
                            timestamp=point["timestamp"],
                            metric_name=metric_name,
                            value=point["value"],
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
                device_id=device_ids[0] if len(device_ids) == 1 else "multiple",
                metric_name=metric_names[0] if len(metric_names) == 1 else "multiple",
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
            device_keys = [key for key in self.data_store.keys() if key.startswith(f"{device_id}:")]
            
            total_points = sum(len(self.data_store[key]) for key in device_keys)
            
            # 计算最近更新时间
            last_update = None
            all_timestamps = []
            for key in device_keys:
                for point in self.data_store[key]:
                    all_timestamps.append(point["timestamp"])
            
            if all_timestamps:
                last_update = max(all_timestamps)
            
            # 计算24小时统计
            last_24h = datetime.utcnow() - timedelta(hours=24)
            last_24h_points = 0
            for key in device_keys:
                last_24h_points += len([
                    point for point in self.data_store[key]
                    if point["timestamp"] >= last_24h
                ])
            
            stats = DeviceTelemetryStatsResponse(
                device_id=device_id,
                total_metrics=len(device_keys),
                active_metrics=len([key for key in device_keys if self.data_store[key]]),
                data_points_count=total_points,
                last_update=last_update,
                storage_size=total_points * 100,  # 估算存储大小
                avg_frequency=total_points / max(1, len(device_keys)) / 60,  # points per minute
                last_24h_points=last_24h_points,
                last_24h_alerts=0,  # TODO: 计算24小时内的警报数
                metrics_by_type={
                    "gauge": len(device_keys),
                    "counter": 0,
                    "histogram": 0
                },
                top_metrics=[
                    {
                        "name": key.split(":", 1)[1],
                        "points": len(self.data_store[key])
                    }
                    for key in device_keys[:5]  # 前5个指标
                ]
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting device stats: {e}")
            return None
    
    async def get_service_stats(self) -> Optional[TelemetryStatsResponse]:
        """获取服务统计"""
        try:
            total_devices = len(set(key.split(":", 1)[0] for key in self.data_store.keys()))
            total_points = sum(len(points) for points in self.data_store.values())
            
            # 计算24小时统计
            last_24h = datetime.utcnow() - timedelta(hours=24)
            last_24h_points = 0
            for points in self.data_store.values():
                last_24h_points += len([
                    point for point in points
                    if point["timestamp"] >= last_24h
                ])
            
            stats = TelemetryStatsResponse(
                total_devices=total_devices,
                active_devices=total_devices,  # 简化假设所有设备都活跃
                total_metrics=len(self.data_store.keys()),
                total_data_points=total_points,
                storage_size=total_points * 100,  # 估算存储大小
                points_per_second=last_24h_points / 86400,
                avg_latency=50.0,  # 模拟延迟
                error_rate=1.5,
                last_24h_points=last_24h_points,
                last_24h_devices=total_devices,
                last_24h_alerts=len(self.active_alerts),
                devices_by_type={
                    "sensor": total_devices // 2,
                    "gateway": total_devices // 4,
                    "camera": total_devices // 4
                },
                metrics_by_type={
                    "gauge": len(self.data_store.keys()) // 2,
                    "counter": len(self.data_store.keys()) // 3,
                    "histogram": len(self.data_store.keys()) // 6
                },
                data_by_hour=[
                    {"hour": i, "points": last_24h_points // 24}
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
                "created_at": datetime.utcnow(),
                "last_sent": datetime.utcnow()
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
            
            # 获取原始数据
            if device_id:
                key = f"{device_id}:{metric_name}"
                raw_data = self.data_store.get(key, [])
            else:
                # 多设备聚合
                raw_data = []
                for key in self.data_store.keys():
                    if key.endswith(f":{metric_name}"):
                        raw_data.extend(self.data_store[key])
            
            # 时间过滤
            filtered_data = [
                point for point in raw_data
                if start_time <= point["timestamp"] <= end_time
            ]
            
            # 按时间间隔分组聚合
            aggregated_points = await self._aggregate_by_interval(
                filtered_data, aggregation_type, interval, start_time, end_time
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
        # 检查指标定义
        if data_point.metric_name in self.metric_definitions:
            metric_def = self.metric_definitions[data_point.metric_name]
            
            # 检查数据类型
            if metric_def.data_type == DataType.NUMERIC:
                if not isinstance(data_point.value, (int, float)):
                    raise ValueError(f"Invalid data type for metric {data_point.metric_name}")
            
            # 检查范围
            if metric_def.min_value is not None and isinstance(data_point.value, (int, float)):
                if data_point.value < metric_def.min_value:
                    raise ValueError(f"Value below minimum for metric {data_point.metric_name}")
            
            if metric_def.max_value is not None and isinstance(data_point.value, (int, float)):
                if data_point.value > metric_def.max_value:
                    raise ValueError(f"Value above maximum for metric {data_point.metric_name}")
    
    async def _check_alert_rules(self, device_id: str, data_point: TelemetryDataPoint):
        """检查警报规则"""
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # 检查是否匹配设备
            if rule.device_ids and device_id not in rule.device_ids:
                continue
            
            # 检查是否匹配指标
            if rule.metric_name != data_point.metric_name:
                continue
            
            # 评估条件
            if await self._evaluate_alert_condition(rule, data_point):
                await self._trigger_alert(rule, device_id, data_point)
    
    async def _evaluate_alert_condition(self, rule: AlertRuleResponse, data_point: TelemetryDataPoint) -> bool:
        """评估警报条件"""
        try:
            condition = rule.condition
            threshold = rule.threshold_value
            value = data_point.value
            
            if condition.startswith(">"):
                return isinstance(value, (int, float)) and value > threshold
            elif condition.startswith("<"):
                return isinstance(value, (int, float)) and value < threshold
            elif condition.startswith("=="):
                return value == threshold
            elif condition.startswith("!="):
                return value != threshold
            
            return False
        except Exception as e:
            logger.error(f"Error evaluating alert condition: {e}")
            return False
    
    async def _trigger_alert(self, rule: AlertRuleResponse, device_id: str, data_point: TelemetryDataPoint):
        """触发警报"""
        try:
            alert_id = secrets.token_hex(16)
            
            alert = AlertResponse(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                device_id=device_id,
                metric_name=rule.metric_name,
                level=rule.level,
                status=AlertStatus.ACTIVE,
                message=f"Alert triggered: {rule.name}",
                current_value=data_point.value,
                threshold_value=rule.threshold_value,
                triggered_at=datetime.utcnow(),
                acknowledged_at=None,
                resolved_at=None,
                auto_resolve_at=datetime.utcnow() + timedelta(seconds=rule.auto_resolve_timeout) if rule.auto_resolve else None,
                acknowledged_by=None,
                resolved_by=None,
                resolution_note=None,
                affected_devices_count=1,
                tags=rule.tags,
                metadata={"trigger_value": data_point.value}
            )
            
            self.active_alerts[alert_id] = alert
            
            # 更新规则统计
            rule.total_triggers += 1
            rule.last_triggered = datetime.utcnow()
            
            logger.warning(f"Alert triggered: {rule.name} for device {device_id}")
            
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
                now = datetime.utcnow()
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