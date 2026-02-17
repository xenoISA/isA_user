"""
Session Service Event Models

Event data models for session lifecycle events.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class SessionEventType(str, Enum):
    """
    Events published by session_service.

    Stream: session-stream
    Subjects: session.>
    """
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    SESSION_MESSAGE_SENT = "session.message_sent"
    SESSION_TOKENS_USED = "session.tokens_used"


class SessionSubscribedEventType(str, Enum):
    """Events that session_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class SessionStreamConfig:
    """Stream configuration for session_service"""
    STREAM_NAME = "session-stream"
    SUBJECTS = ["session.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "session"


# ============================================================================
# Session Event Models
# ============================================================================


class SessionStartedEventData(BaseModel):
    """
    Event: session.started
    Triggered when a new session is created
    """

    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    session_type: str = Field(default="conversation", description="Session type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_12345",
                "user_id": "user_67890",
                "session_type": "conversation",
                "metadata": {"platform": "web"},
                "timestamp": "2025-11-16T10:00:00Z",
            }
        }


class SessionEndedEventData(BaseModel):
    """
    Event: session.ended
    Triggered when a session is ended or completed
    """

    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    total_messages: int = Field(..., description="Total number of messages in session")
    total_tokens: int = Field(..., description="Total tokens used in session")
    total_cost: float = Field(..., description="Total cost in USD")
    duration_seconds: Optional[int] = Field(
        None, description="Session duration in seconds"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_12345",
                "user_id": "user_67890",
                "total_messages": 10,
                "total_tokens": 1500,
                "total_cost": 0.15,
                "duration_seconds": 300,
                "timestamp": "2025-11-16T10:05:00Z",
            }
        }


class SessionMessageSentEventData(BaseModel):
    """
    Event: session.message_sent
    Triggered when a message is added to a session
    """

    session_id: str = Field(..., description="Session ID")
    message_id: str = Field(..., description="Message ID")
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., description="Message role (user/assistant/system)")
    message_type: str = Field(default="text", description="Message type")
    tokens_used: int = Field(default=0, description="Tokens used in this message")
    cost_usd: float = Field(default=0.0, description="Cost of this message in USD")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_12345",
                "message_id": "msg_98765",
                "user_id": "user_67890",
                "role": "user",
                "message_type": "text",
                "tokens_used": 50,
                "cost_usd": 0.005,
                "timestamp": "2025-11-16T10:02:00Z",
            }
        }


class SessionTokensUsedEventData(BaseModel):
    """
    Event: session.tokens_used
    Triggered when tokens are consumed in a session
    """

    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    tokens_used: int = Field(..., description="Tokens used")
    cost_usd: float = Field(..., description="Cost in USD")
    message_id: Optional[str] = Field(None, description="Related message ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_12345",
                "user_id": "user_67890",
                "tokens_used": 150,
                "cost_usd": 0.015,
                "message_id": "msg_98765",
                "timestamp": "2025-11-16T10:02:30Z",
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================


def create_session_started_event_data(
    session_id: str,
    user_id: str,
    session_type: str = "conversation",
    metadata: Optional[Dict[str, Any]] = None,
) -> SessionStartedEventData:
    """Create session started event data"""
    return SessionStartedEventData(
        session_id=session_id,
        user_id=user_id,
        session_type=session_type,
        metadata=metadata,
    )


def create_session_ended_event_data(
    session_id: str,
    user_id: str,
    total_messages: int,
    total_tokens: int,
    total_cost: float,
    duration_seconds: Optional[int] = None,
) -> SessionEndedEventData:
    """Create session ended event data"""
    return SessionEndedEventData(
        session_id=session_id,
        user_id=user_id,
        total_messages=total_messages,
        total_tokens=total_tokens,
        total_cost=total_cost,
        duration_seconds=duration_seconds,
    )


def create_session_message_sent_event_data(
    session_id: str,
    message_id: str,
    user_id: str,
    role: str,
    message_type: str = "text",
    tokens_used: int = 0,
    cost_usd: float = 0.0,
) -> SessionMessageSentEventData:
    """Create session message sent event data"""
    return SessionMessageSentEventData(
        session_id=session_id,
        message_id=message_id,
        user_id=user_id,
        role=role,
        message_type=message_type,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
    )


def create_session_tokens_used_event_data(
    session_id: str,
    user_id: str,
    tokens_used: int,
    cost_usd: float,
    message_id: Optional[str] = None,
) -> SessionTokensUsedEventData:
    """Create session tokens used event data"""
    return SessionTokensUsedEventData(
        session_id=session_id,
        user_id=user_id,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        message_id=message_id,
    )
