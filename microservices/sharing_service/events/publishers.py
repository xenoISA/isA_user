"""
Sharing Service Event Publishers

Publish events for share lifecycle.
"""

import logging
from typing import Any, Dict, Optional

from core.nats_client import Event

logger = logging.getLogger(__name__)


async def publish_share_created(
    event_bus,
    share_id: str,
    session_id: str,
    owner_id: str,
    share_token: str,
    permissions: str,
    expires_at: Optional[str] = None,
):
    """Publish share.created event"""
    try:
        from datetime import datetime, timezone

        event = Event(
            event_type="share.created",
            source="sharing_service",
            data={
                "share_id": share_id,
                "session_id": session_id,
                "owner_id": owner_id,
                "share_token": share_token,
                "permissions": permissions,
                "expires_at": expires_at,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await event_bus.publish_event(event)
        logger.info(f"Published share.created for share {share_id}")
    except Exception as e:
        logger.error(f"Failed to publish share.created: {e}")


async def publish_share_accessed(
    event_bus,
    share_id: str,
    session_id: str,
    share_token: str,
    access_count: int,
):
    """Publish share.accessed event"""
    try:
        from datetime import datetime, timezone

        event = Event(
            event_type="share.accessed",
            source="sharing_service",
            data={
                "share_id": share_id,
                "session_id": session_id,
                "share_token": share_token,
                "access_count": access_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await event_bus.publish_event(event)
        logger.info(f"Published share.accessed for share {share_id}")
    except Exception as e:
        logger.error(f"Failed to publish share.accessed: {e}")


async def publish_share_revoked(
    event_bus,
    share_id: str,
    session_id: str,
    owner_id: str,
    share_token: str,
):
    """Publish share.revoked event"""
    try:
        from datetime import datetime, timezone

        event = Event(
            event_type="share.revoked",
            source="sharing_service",
            data={
                "share_id": share_id,
                "session_id": session_id,
                "owner_id": owner_id,
                "share_token": share_token,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await event_bus.publish_event(event)
        logger.info(f"Published share.revoked for share {share_id}")
    except Exception as e:
        logger.error(f"Failed to publish share.revoked: {e}")
