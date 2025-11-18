"""
Invitation Service Event Publishers

邀请服务事件发布函数
"""

import logging
from datetime import datetime
from typing import Optional
from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger(__name__)


async def publish_invitation_sent(
    event_bus,
    invitation_id: str,
    organization_id: str,
    email: str,
    role: str,
    invited_by: str,
    email_sent: bool = False,
    metadata: Optional[dict] = None
):
    """
    发布邀请已发送事件

    Args:
        event_bus: NATS事件总线
        invitation_id: 邀请ID
        organization_id: 组织ID
        email: 受邀邮箱
        role: 角色
        invited_by: 邀请人用户ID
        email_sent: 邮件是否发送成功
        metadata: 额外元数据
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping event publication")
        return

    try:
        event = Event(
            event_type=EventType.INVITATION_SENT,
            source=ServiceSource.INVITATION_SERVICE,
            data={
                "invitation_id": invitation_id,
                "organization_id": organization_id,
                "email": email,
                "role": role,
                "invited_by": invited_by,
                "email_sent": email_sent,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.info(f"Published invitation.sent event for invitation {invitation_id}")

    except Exception as e:
        logger.error(f"Error publishing invitation sent event: {e}")


async def publish_invitation_expired(
    event_bus,
    invitation_id: str,
    organization_id: str,
    email: str,
    expired_at: str,
    metadata: Optional[dict] = None
):
    """
    发布邀请已过期事件

    Args:
        event_bus: NATS事件总线
        invitation_id: 邀请ID
        organization_id: 组织ID
        email: 受邀邮箱
        expired_at: 过期时间
        metadata: 额外元数据
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping event publication")
        return

    try:
        event = Event(
            event_type=EventType.INVITATION_EXPIRED,
            source=ServiceSource.INVITATION_SERVICE,
            data={
                "invitation_id": invitation_id,
                "organization_id": organization_id,
                "email": email,
                "expired_at": expired_at,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.info(f"Published invitation.expired event for invitation {invitation_id}")

    except Exception as e:
        logger.error(f"Error publishing invitation expired event: {e}")


async def publish_invitation_accepted(
    event_bus,
    invitation_id: str,
    organization_id: str,
    user_id: str,
    email: str,
    role: str,
    accepted_at: str,
    metadata: Optional[dict] = None
):
    """
    发布邀请已接受事件

    Args:
        event_bus: NATS事件总线
        invitation_id: 邀请ID
        organization_id: 组织ID
        user_id: 接受邀请的用户ID
        email: 用户邮箱
        role: 分配的角色
        accepted_at: 接受时间
        metadata: 额外元数据
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping event publication")
        return

    try:
        event = Event(
            event_type=EventType.INVITATION_ACCEPTED,
            source=ServiceSource.INVITATION_SERVICE,
            data={
                "invitation_id": invitation_id,
                "organization_id": organization_id,
                "user_id": user_id,
                "email": email,
                "role": role,
                "accepted_at": accepted_at,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.info(f"Published invitation.accepted event for invitation {invitation_id}")

    except Exception as e:
        logger.error(f"Error publishing invitation accepted event: {e}")


async def publish_invitation_cancelled(
    event_bus,
    invitation_id: str,
    organization_id: str,
    email: str,
    cancelled_by: str,
    metadata: Optional[dict] = None
):
    """
    发布邀请已取消事件

    Args:
        event_bus: NATS事件总线
        invitation_id: 邀请ID
        organization_id: 组织ID
        email: 受邀邮箱
        cancelled_by: 取消人用户ID
        metadata: 额外元数据
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping event publication")
        return

    try:
        event = Event(
            event_type=EventType.INVITATION_CANCELLED,
            source=ServiceSource.INVITATION_SERVICE,
            data={
                "invitation_id": invitation_id,
                "organization_id": organization_id,
                "email": email,
                "cancelled_by": cancelled_by,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        await event_bus.publish_event(event)
        logger.info(f"Published invitation.cancelled event for invitation {invitation_id}")

    except Exception as e:
        logger.error(f"Error publishing invitation cancelled event: {e}")
