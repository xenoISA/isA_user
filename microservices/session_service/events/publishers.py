"""
Session Service Event Publishers

Publish events for session lifecycle.
Following the standard event-driven architecture pattern.
"""

import logging
from typing import Any, Dict, Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    create_session_ended_event_data,
    create_session_message_sent_event_data,
    create_session_started_event_data,
    create_session_tokens_used_event_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Session Event Publishers
# ============================================================================


async def publish_session_started(
    event_bus,
    session_id: str,
    user_id: str,
    session_type: str = "conversation",
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Publish session.started event

    Args:
        event_bus: NATS event bus instance
        session_id: Session ID
        user_id: User ID
        session_type: Type of session (conversation, task, etc.)
        metadata: Additional session metadata
    """
    try:
        event_data = create_session_started_event_data(
            session_id=session_id,
            user_id=user_id,
            session_type=session_type,
            metadata=metadata,
        )

        event = Event(
            event_type=EventType.SESSION_STARTED,
            source=ServiceSource.SESSION_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(f"Published session.started for session {session_id}")

    except Exception as e:
        logger.error(f"Failed to publish session.started: {e}")
        # Don't raise - event publishing failures shouldn't break the main flow


async def publish_session_ended(
    event_bus,
    session_id: str,
    user_id: str,
    total_messages: int,
    total_tokens: int,
    total_cost: float,
    duration_seconds: Optional[int] = None,
):
    """
    Publish session.ended event

    Args:
        event_bus: NATS event bus instance
        session_id: Session ID
        user_id: User ID
        total_messages: Total number of messages in session
        total_tokens: Total tokens used
        total_cost: Total cost in USD
        duration_seconds: Session duration in seconds
    """
    try:
        event_data = create_session_ended_event_data(
            session_id=session_id,
            user_id=user_id,
            total_messages=total_messages,
            total_tokens=total_tokens,
            total_cost=total_cost,
            duration_seconds=duration_seconds,
        )

        event = Event(
            event_type=EventType.SESSION_ENDED,
            source=ServiceSource.SESSION_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published session.ended for session {session_id} "
            f"({total_messages} messages, {total_tokens} tokens)"
        )

    except Exception as e:
        logger.error(f"Failed to publish session.ended: {e}")


async def publish_session_message_sent(
    event_bus,
    session_id: str,
    message_id: str,
    user_id: str,
    role: str,
    message_type: str = "text",
    tokens_used: int = 0,
    cost_usd: float = 0.0,
):
    """
    Publish session.message_sent event

    Args:
        event_bus: NATS event bus instance
        session_id: Session ID
        message_id: Message ID
        user_id: User ID
        role: Message role (user/assistant/system)
        message_type: Type of message
        tokens_used: Tokens used in this message
        cost_usd: Cost of this message in USD
    """
    try:
        event_data = create_session_message_sent_event_data(
            session_id=session_id,
            message_id=message_id,
            user_id=user_id,
            role=role,
            message_type=message_type,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

        event = Event(
            event_type=EventType.SESSION_MESSAGE_SENT,
            source=ServiceSource.SESSION_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published session.message_sent for session {session_id}, role: {role}"
        )

    except Exception as e:
        logger.error(f"Failed to publish session.message_sent: {e}")


async def publish_session_tokens_used(
    event_bus,
    session_id: str,
    user_id: str,
    tokens_used: int,
    cost_usd: float,
    message_id: Optional[str] = None,
):
    """
    Publish session.tokens_used event

    Args:
        event_bus: NATS event bus instance
        session_id: Session ID
        user_id: User ID
        tokens_used: Number of tokens used
        cost_usd: Cost in USD
        message_id: Related message ID (optional)
    """
    try:
        event_data = create_session_tokens_used_event_data(
            session_id=session_id,
            user_id=user_id,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            message_id=message_id,
        )

        event = Event(
            event_type=EventType.SESSION_TOKENS_USED,
            source=ServiceSource.SESSION_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published session.tokens_used for session {session_id}: "
            f"{tokens_used} tokens, ${cost_usd}"
        )

    except Exception as e:
        logger.error(f"Failed to publish session.tokens_used: {e}")
