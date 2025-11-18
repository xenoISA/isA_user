"""
Compliance Service Event Publishers

合规服务事件发布函数
"""

import logging
from datetime import datetime
from typing import Optional
from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger(__name__)


async def publish_compliance_check_performed(
    event_bus,
    check_id: str,
    user_id: str,
    check_type: str,
    content_type: str,
    status: str,
    risk_level: str,
    violations_count: int,
    warnings_count: int,
    action_taken: Optional[str] = None,
    organization_id: Optional[str] = None,
    processing_time_ms: Optional[float] = None,
    metadata: Optional[dict] = None
):
    """
    发布合规检查执行完成事件

    Args:
        event_bus: NATS事件总线
        check_id: 检查ID
        user_id: 用户ID
        check_type: 检查类型
        content_type: 内容类型
        status: 检查状态
        risk_level: 风险级别
        violations_count: 违规数量
        warnings_count: 警告数量
        action_taken: 采取的措施
        organization_id: 组织ID
        processing_time_ms: 处理时间(毫秒)
        metadata: 额外元数据
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping event publication")
        return

    try:
        event = Event(
            event_type=EventType.COMPLIANCE_CHECK_PERFORMED,
            source=ServiceSource.COMPLIANCE_SERVICE,
            data={
                "check_id": check_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "check_type": check_type,
                "content_type": content_type,
                "status": status,
                "risk_level": risk_level,
                "violations_count": violations_count,
                "warnings_count": warnings_count,
                "action_taken": action_taken,
                "processing_time_ms": processing_time_ms,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.info(f"Published compliance.check.performed event for check {check_id}")

    except Exception as e:
        logger.error(f"Error publishing compliance check performed event: {e}")


async def publish_compliance_violation_detected(
    event_bus,
    check_id: str,
    user_id: str,
    violations: list,
    risk_level: str,
    action_taken: Optional[str] = None,
    organization_id: Optional[str] = None,
    requires_review: bool = False,
    blocked_content: bool = False,
    metadata: Optional[dict] = None
):
    """
    发布检测到合规违规事件

    Args:
        event_bus: NATS事件总线
        check_id: 检查ID
        user_id: 用户ID
        violations: 违规详情列表
        risk_level: 风险级别
        action_taken: 采取的措施
        organization_id: 组织ID
        requires_review: 是否需要人工审核
        blocked_content: 是否阻止了内容
        metadata: 额外元数据
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping event publication")
        return

    try:
        event = Event(
            event_type=EventType.COMPLIANCE_VIOLATION_DETECTED,
            source=ServiceSource.COMPLIANCE_SERVICE,
            data={
                "check_id": check_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "violations": violations,
                "violations_count": len(violations),
                "risk_level": risk_level,
                "action_taken": action_taken,
                "requires_review": requires_review,
                "blocked_content": blocked_content,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.warning(f"Published compliance.violation.detected event for check {check_id}")

    except Exception as e:
        logger.error(f"Error publishing compliance violation detected event: {e}")


async def publish_compliance_warning_issued(
    event_bus,
    check_id: str,
    user_id: str,
    warnings: list,
    risk_level: str = "low",
    organization_id: Optional[str] = None,
    allowed_with_warning: bool = True,
    metadata: Optional[dict] = None
):
    """
    发布发出合规警告事件

    Args:
        event_bus: NATS事件总线
        check_id: 检查ID
        user_id: 用户ID
        warnings: 警告详情列表
        risk_level: 风险级别
        organization_id: 组织ID
        allowed_with_warning: 是否允许但带警告
        metadata: 额外元数据
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping event publication")
        return

    try:
        # Extract warning types
        warning_types = [w.get("check_type", "unknown") for w in warnings]

        event = Event(
            event_type=EventType.COMPLIANCE_WARNING_ISSUED,
            source=ServiceSource.COMPLIANCE_SERVICE,
            data={
                "check_id": check_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "warnings": warnings,
                "warnings_count": len(warnings),
                "warning_types": warning_types,
                "risk_level": risk_level,
                "allowed_with_warning": allowed_with_warning,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.info(f"Published compliance.warning.issued event for check {check_id}")

    except Exception as e:
        logger.error(f"Error publishing compliance warning issued event: {e}")
