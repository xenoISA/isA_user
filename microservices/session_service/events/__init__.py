"""
Session Service Events Module

Event-driven architecture for session lifecycle management.
Follows the standard event-driven architecture pattern.
"""

from .handlers import SessionEventHandlers
from .models import (
    SessionEndedEventData,
    SessionMessageSentEventData,
    SessionStartedEventData,
    SessionTokensUsedEventData,
    create_session_ended_event_data,
    create_session_message_sent_event_data,
    create_session_started_event_data,
    create_session_tokens_used_event_data,
)
from .publishers import (
    publish_session_ended,
    publish_session_message_sent,
    publish_session_started,
    publish_session_tokens_used,
)

__all__ = [
    # Handlers
    "SessionEventHandlers",
    # Models
    "SessionStartedEventData",
    "SessionEndedEventData",
    "SessionMessageSentEventData",
    "SessionTokensUsedEventData",
    "create_session_started_event_data",
    "create_session_ended_event_data",
    "create_session_message_sent_event_data",
    "create_session_tokens_used_event_data",
    # Publishers
    "publish_session_started",
    "publish_session_ended",
    "publish_session_message_sent",
    "publish_session_tokens_used",
]
