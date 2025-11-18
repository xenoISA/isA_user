"""
Telemetry Service Event Publishers

Centralized functions for publishing events from Telemetry Service
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from core.nats_client import Event, EventType, ServiceSource
from .models import (
    TelemetryDataReceivedEvent,
    MetricDefinedEvent,
    AlertRuleCreatedEvent,
    AlertTriggeredEvent,
    AlertResolvedEvent
)

logger = logging.getLogger(__name__)


async def publish_telemetry_data_received(
    event_bus,
    device_id: str,
    metrics_count: int,
    points_count: int
) -> bool:
    """
    Publish telemetry.data.received event

    Args:
        event_bus: Event bus instance
        device_id: Device ID
        metrics_count: Number of unique metrics
        points_count: Number of data points ingested

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = TelemetryDataReceivedEvent(
            device_id=device_id,
            metrics_count=metrics_count,
            points_count=points_count,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.TELEMETRY_DATA_RECEIVED,
            source=ServiceSource.TELEMETRY_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published telemetry.data.received event for device {device_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish telemetry.data.received event: {e}")
        return False


async def publish_metric_defined(
    event_bus,
    metric_id: str,
    name: str,
    data_type: str,
    metric_type: str,
    unit: Optional[str],
    created_by: str
) -> bool:
    """
    Publish metric.defined event

    Args:
        event_bus: Event bus instance
        metric_id: Unique metric ID
        name: Metric name
        data_type: Data type
        metric_type: Metric type
        unit: Unit of measurement
        created_by: User ID who created

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = MetricDefinedEvent(
            metric_id=metric_id,
            name=name,
            data_type=data_type,
            metric_type=metric_type,
            unit=unit,
            created_by=created_by,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.METRIC_DEFINED,
            source=ServiceSource.TELEMETRY_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published metric.defined event for metric {name}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish metric.defined event: {e}")
        return False


async def publish_alert_rule_created(
    event_bus,
    rule_id: str,
    name: str,
    metric_name: str,
    condition: str,
    threshold_value: str,
    level: str,
    enabled: bool,
    created_by: str
) -> bool:
    """
    Publish alert.rule.created event

    Args:
        event_bus: Event bus instance
        rule_id: Unique rule ID
        name: Rule name
        metric_name: Metric being monitored
        condition: Alert condition
        threshold_value: Threshold value
        level: Alert level
        enabled: Is rule enabled
        created_by: User ID who created

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = AlertRuleCreatedEvent(
            rule_id=rule_id,
            name=name,
            metric_name=metric_name,
            condition=condition,
            threshold_value=threshold_value,
            level=level,
            enabled=enabled,
            created_by=created_by,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.ALERT_RULE_CREATED,
            source=ServiceSource.TELEMETRY_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published alert.rule.created event for rule {name}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish alert.rule.created event: {e}")
        return False


async def publish_alert_triggered(
    event_bus,
    alert_id: str,
    rule_id: str,
    rule_name: str,
    device_id: str,
    metric_name: str,
    level: str,
    current_value: str,
    threshold_value: str
) -> bool:
    """
    Publish alert.triggered event

    Args:
        event_bus: Event bus instance
        alert_id: Unique alert ID
        rule_id: Alert rule ID
        rule_name: Alert rule name
        device_id: Device ID
        metric_name: Metric name
        level: Alert level
        current_value: Current metric value
        threshold_value: Threshold value

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = AlertTriggeredEvent(
            alert_id=alert_id,
            rule_id=rule_id,
            rule_name=rule_name,
            device_id=device_id,
            metric_name=metric_name,
            level=level,
            current_value=current_value,
            threshold_value=threshold_value,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.ALERT_TRIGGERED,
            source=ServiceSource.TELEMETRY_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published alert.triggered event for alert {alert_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish alert.triggered event: {e}")
        return False


async def publish_alert_resolved(
    event_bus,
    alert_id: str,
    rule_id: str,
    rule_name: str,
    device_id: str,
    metric_name: str,
    level: str,
    resolved_by: str,
    resolution_note: Optional[str] = None
) -> bool:
    """
    Publish alert.resolved event

    Args:
        event_bus: Event bus instance
        alert_id: Unique alert ID
        rule_id: Alert rule ID
        rule_name: Alert rule name
        device_id: Device ID
        metric_name: Metric name
        level: Alert level
        resolved_by: User ID who resolved
        resolution_note: Resolution note

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = AlertResolvedEvent(
            alert_id=alert_id,
            rule_id=rule_id,
            rule_name=rule_name,
            device_id=device_id,
            metric_name=metric_name,
            level=level,
            resolved_by=resolved_by,
            resolution_note=resolution_note,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type=EventType.ALERT_RESOLVED,
            source=ServiceSource.TELEMETRY_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published alert.resolved event for alert {alert_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish alert.resolved event: {e}")
        return False
