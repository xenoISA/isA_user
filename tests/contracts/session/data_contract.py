"""
Session Service - Data Contract

Pydantic schemas, test data factory, and request builders for session_service.
Zero hardcoded data - all test data generated through factory methods.

This module defines:
1. Request Contracts - Pydantic schemas for API requests
2. Response Contracts - Pydantic schemas for API responses
3. SessionTestDataFactory - Test data generation (35+ methods)
4. Request Builders - Fluent API for building test requests
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta
from enum import Enum
import secrets
import uuid


# ============================================================================
# Enumerations
# ============================================================================


class SessionStatusEnum(str, Enum):
    """Valid session status values"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ENDED = "ended"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class MessageRoleEnum(str, Enum):
    """Valid message role values"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageTypeEnum(str, Enum):
    """Valid message type values"""
    CHAT = "chat"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    NOTIFICATION = "notification"


# ============================================================================
# Request Contracts (10 schemas)
# ============================================================================


class SessionCreateRequestContract(BaseModel):
    """Contract for session creation requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    session_id: Optional[str] = Field(None, max_length=50, description="Optional custom session ID")
    conversation_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Conversation context data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if v is not None and not v.strip():
            raise ValueError("session_id cannot be empty string")
        return v.strip() if v else None


class SessionUpdateRequestContract(BaseModel):
    """Contract for session update requests"""
    status: Optional[str] = Field(None, description="New session status")
    conversation_data: Optional[Dict[str, Any]] = Field(None, description="Updated conversation data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in [e.value for e in SessionStatusEnum]:
            raise ValueError(f"status must be one of: {[e.value for e in SessionStatusEnum]}")
        return v


class MessageCreateRequestContract(BaseModel):
    """Contract for message creation requests"""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., min_length=1, description="Message content")
    message_type: str = Field(default="chat", description="Message type")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Message metadata")
    tokens_used: int = Field(default=0, ge=0, description="Tokens consumed")
    cost_usd: float = Field(default=0.0, ge=0, description="Cost in USD")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in [e.value for e in MessageRoleEnum]:
            raise ValueError(f"role must be one of: {[e.value for e in MessageRoleEnum]}")
        return v

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v

    @field_validator('message_type')
    @classmethod
    def validate_message_type(cls, v):
        if v not in [e.value for e in MessageTypeEnum]:
            raise ValueError(f"message_type must be one of: {[e.value for e in MessageTypeEnum]}")
        return v


class SessionQueryRequestContract(BaseModel):
    """Contract for session list query parameters"""
    user_id: str = Field(..., min_length=1, description="User ID (required)")
    active_only: bool = Field(default=False, description="Only return active sessions")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")


class MessageQueryRequestContract(BaseModel):
    """Contract for message list query parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=100, ge=1, le=200, description="Items per page")


class SessionEndRequestContract(BaseModel):
    """Contract for session end requests (implicit via DELETE)"""
    user_id: Optional[str] = Field(None, description="User ID for authorization")


class SessionSummaryRequestContract(BaseModel):
    """Contract for session summary requests"""
    user_id: Optional[str] = Field(None, description="User ID for authorization")


class HealthCheckRequestContract(BaseModel):
    """Contract for health check requests (no body)"""
    pass


class DetailedHealthCheckRequestContract(BaseModel):
    """Contract for detailed health check requests (no body)"""
    pass


class SessionStatsRequestContract(BaseModel):
    """Contract for session stats requests (no body)"""
    pass


# ============================================================================
# Response Contracts (10 schemas)
# ============================================================================


class SessionResponseContract(BaseModel):
    """Contract for session response"""
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    status: str = Field(..., description="Session status")
    conversation_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_active: bool = Field(..., description="Is session active")
    message_count: int = Field(..., ge=0, description="Total messages")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    total_cost: float = Field(..., ge=0, description="Total cost USD")
    session_summary: str = Field(default="", description="Session summary")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")

    class Config:
        from_attributes = True


class SessionListResponseContract(BaseModel):
    """Contract for session list response"""
    sessions: List[SessionResponseContract] = Field(..., description="Session list")
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, le=100, description="Page size")


class SessionSummaryResponseContract(BaseModel):
    """Contract for session summary response"""
    session_id: str
    user_id: str
    status: str
    message_count: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    total_cost: float = Field(..., ge=0)
    has_memory: bool
    is_active: bool
    created_at: Optional[datetime]
    last_activity: Optional[datetime]


class SessionStatsResponseContract(BaseModel):
    """Contract for session stats response"""
    total_sessions: int = Field(default=0, ge=0)
    active_sessions: int = Field(default=0, ge=0)
    total_messages: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    total_cost: float = Field(default=0.0, ge=0)
    average_messages_per_session: float = Field(default=0.0, ge=0)


class MessageResponseContract(BaseModel):
    """Contract for message response"""
    message_id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    message_type: str = Field(..., description="Message type")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tokens_used: int = Field(..., ge=0)
    cost_usd: float = Field(..., ge=0)
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageListResponseContract(BaseModel):
    """Contract for message list response"""
    messages: List[MessageResponseContract] = Field(..., description="Message list")
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, le=200, description="Page size")


class HealthCheckResponseContract(BaseModel):
    """Contract for health check response"""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    port: int = Field(..., description="Service port")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Timestamp ISO format")


class DetailedHealthCheckResponseContract(BaseModel):
    """Contract for detailed health check response"""
    service: str = Field(default="session_service")
    status: str = Field(default="operational")
    port: int = Field(default=8205)
    version: str = Field(default="1.0.0")
    database_connected: bool
    timestamp: Optional[datetime]


class ErrorResponseContract(BaseModel):
    """Contract for error responses"""
    error: Optional[str] = Field(None, description="Error type")
    detail: str = Field(..., description="Error detail")
    timestamp: Optional[datetime] = Field(None, description="Error timestamp")


class SuccessResponseContract(BaseModel):
    """Contract for success message responses"""
    message: str = Field(..., description="Success message")


# ============================================================================
# SessionTestDataFactory - 35+ methods (20+ valid + 15+ invalid)
# ============================================================================


class SessionTestDataFactory:
    """
    Test data factory for session_service - zero hardcoded data.

    All methods generate unique, valid test data suitable for testing.
    Factory methods are prefixed with make_ for valid data and
    make_invalid_ for invalid data scenarios.
    """

    # ========================================================================
    # Valid Data Generators (20+ methods)
    # ========================================================================

    @staticmethod
    def make_session_id() -> str:
        """Generate valid session ID"""
        return f"sess_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_message_id() -> str:
        """Generate valid message ID"""
        return f"msg_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(hours_ago: int = 1) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(hours=hours_ago)

    @staticmethod
    def make_future_timestamp(hours_ahead: int = 1) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(hours=hours_ahead)

    @staticmethod
    def make_status() -> str:
        """Generate valid session status"""
        return SessionStatusEnum.ACTIVE.value

    @staticmethod
    def make_role() -> str:
        """Generate valid message role"""
        return MessageRoleEnum.USER.value

    @staticmethod
    def make_message_type() -> str:
        """Generate valid message type"""
        return MessageTypeEnum.CHAT.value

    @staticmethod
    def make_content() -> str:
        """Generate valid message content"""
        return f"Test message content {secrets.token_hex(8)}"

    @staticmethod
    def make_user_content() -> str:
        """Generate user-like message content"""
        templates = [
            "How do I implement {}?",
            "Can you explain {}?",
            "What is the best way to {}?",
            "Help me understand {}.",
            "Please write code for {}.",
        ]
        topics = [
            "binary search",
            "async programming",
            "REST APIs",
            "database indexing",
            "error handling",
        ]
        template = secrets.choice(templates)
        topic = secrets.choice(topics)
        return template.format(topic)

    @staticmethod
    def make_assistant_content() -> str:
        """Generate assistant-like message content"""
        return f"I'd be happy to help with that. Here's an explanation... {secrets.token_hex(16)}"

    @staticmethod
    def make_system_content() -> str:
        """Generate system-like message content"""
        return "You are a helpful AI assistant."

    @staticmethod
    def make_tokens_used() -> int:
        """Generate valid token count"""
        return secrets.randbelow(500) + 10  # 10-509 tokens

    @staticmethod
    def make_cost_usd() -> float:
        """Generate valid cost in USD"""
        return round(secrets.randbelow(100) / 10000 + 0.001, 6)  # 0.001 - 0.011 USD

    @staticmethod
    def make_conversation_data() -> Dict[str, Any]:
        """Generate valid conversation data"""
        return {
            "topic": f"topic_{secrets.token_hex(4)}",
            "context": f"context_{secrets.token_hex(8)}",
        }

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate valid session metadata"""
        return {
            "platform": secrets.choice(["web", "mobile", "api"]),
            "client_version": f"1.{secrets.randbelow(10)}.{secrets.randbelow(10)}",
            "session_type": "conversation",
        }

    @staticmethod
    def make_message_metadata() -> Dict[str, Any]:
        """Generate valid message metadata"""
        return {
            "source": secrets.choice(["keyboard", "voice", "paste"]),
            "processing_time_ms": secrets.randbelow(500) + 50,
        }

    @staticmethod
    def make_session_create_request(**overrides) -> SessionCreateRequestContract:
        """Generate valid session creation request"""
        defaults = {
            "user_id": SessionTestDataFactory.make_user_id(),
            "session_id": None,  # Let service generate
            "conversation_data": SessionTestDataFactory.make_conversation_data(),
            "metadata": SessionTestDataFactory.make_metadata(),
        }
        defaults.update(overrides)
        return SessionCreateRequestContract(**defaults)

    @staticmethod
    def make_session_update_request(**overrides) -> SessionUpdateRequestContract:
        """Generate valid session update request"""
        defaults = {
            "status": None,
            "conversation_data": None,
            "metadata": {"updated": True},
        }
        defaults.update(overrides)
        return SessionUpdateRequestContract(**defaults)

    @staticmethod
    def make_message_create_request(**overrides) -> MessageCreateRequestContract:
        """Generate valid message creation request"""
        defaults = {
            "role": SessionTestDataFactory.make_role(),
            "content": SessionTestDataFactory.make_content(),
            "message_type": SessionTestDataFactory.make_message_type(),
            "metadata": SessionTestDataFactory.make_message_metadata(),
            "tokens_used": SessionTestDataFactory.make_tokens_used(),
            "cost_usd": SessionTestDataFactory.make_cost_usd(),
        }
        defaults.update(overrides)
        return MessageCreateRequestContract(**defaults)

    @staticmethod
    def make_user_message_request() -> MessageCreateRequestContract:
        """Generate user message request"""
        return SessionTestDataFactory.make_message_create_request(
            role="user",
            content=SessionTestDataFactory.make_user_content(),
        )

    @staticmethod
    def make_assistant_message_request() -> MessageCreateRequestContract:
        """Generate assistant message request"""
        return SessionTestDataFactory.make_message_create_request(
            role="assistant",
            content=SessionTestDataFactory.make_assistant_content(),
        )

    @staticmethod
    def make_system_message_request() -> MessageCreateRequestContract:
        """Generate system message request"""
        return SessionTestDataFactory.make_message_create_request(
            role="system",
            content=SessionTestDataFactory.make_system_content(),
            tokens_used=50,
            cost_usd=0.001,
        )

    @staticmethod
    def make_session_response(**overrides) -> SessionResponseContract:
        """Generate valid session response"""
        now = SessionTestDataFactory.make_timestamp()
        defaults = {
            "session_id": SessionTestDataFactory.make_session_id(),
            "user_id": SessionTestDataFactory.make_user_id(),
            "status": SessionStatusEnum.ACTIVE.value,
            "conversation_data": {},
            "metadata": {},
            "is_active": True,
            "message_count": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "session_summary": "",
            "created_at": now,
            "updated_at": now,
            "last_activity": now,
        }
        defaults.update(overrides)
        return SessionResponseContract(**defaults)

    @staticmethod
    def make_message_response(**overrides) -> MessageResponseContract:
        """Generate valid message response"""
        defaults = {
            "message_id": SessionTestDataFactory.make_message_id(),
            "session_id": SessionTestDataFactory.make_session_id(),
            "user_id": SessionTestDataFactory.make_user_id(),
            "role": "user",
            "content": SessionTestDataFactory.make_content(),
            "message_type": "chat",
            "metadata": {},
            "tokens_used": SessionTestDataFactory.make_tokens_used(),
            "cost_usd": SessionTestDataFactory.make_cost_usd(),
            "created_at": SessionTestDataFactory.make_timestamp(),
        }
        defaults.update(overrides)
        return MessageResponseContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (15+ methods)
    # ========================================================================

    @staticmethod
    def make_invalid_user_id_empty() -> str:
        """Generate invalid user ID (empty string)"""
        return ""

    @staticmethod
    def make_invalid_user_id_whitespace() -> str:
        """Generate invalid user ID (whitespace only)"""
        return "   "

    @staticmethod
    def make_invalid_user_id_too_long() -> str:
        """Generate invalid user ID (too long)"""
        return "user_" + "x" * 100

    @staticmethod
    def make_invalid_session_id_empty() -> str:
        """Generate invalid session ID (empty string)"""
        return ""

    @staticmethod
    def make_invalid_role() -> str:
        """Generate invalid message role"""
        return "invalid_role"

    @staticmethod
    def make_invalid_content_empty() -> str:
        """Generate invalid message content (empty)"""
        return ""

    @staticmethod
    def make_invalid_content_whitespace() -> str:
        """Generate invalid message content (whitespace only)"""
        return "   "

    @staticmethod
    def make_invalid_message_type() -> str:
        """Generate invalid message type"""
        return "invalid_type"

    @staticmethod
    def make_invalid_status() -> str:
        """Generate invalid session status"""
        return "invalid_status"

    @staticmethod
    def make_invalid_tokens_negative() -> int:
        """Generate invalid token count (negative)"""
        return -10

    @staticmethod
    def make_invalid_cost_negative() -> float:
        """Generate invalid cost (negative)"""
        return -0.5

    @staticmethod
    def make_invalid_page_zero() -> int:
        """Generate invalid page number (zero)"""
        return 0

    @staticmethod
    def make_invalid_page_negative() -> int:
        """Generate invalid page number (negative)"""
        return -1

    @staticmethod
    def make_invalid_page_size_zero() -> int:
        """Generate invalid page size (zero)"""
        return 0

    @staticmethod
    def make_invalid_page_size_too_large() -> int:
        """Generate invalid page size (too large for sessions)"""
        return 500

    @staticmethod
    def make_nonexistent_session_id() -> str:
        """Generate a session ID that doesn't exist"""
        return f"sess_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_user_id() -> str:
        """Generate a user ID that doesn't exist"""
        return f"user_nonexistent_{uuid.uuid4().hex[:8]}"


# ============================================================================
# Request Builders (3 builders)
# ============================================================================


class SessionCreateRequestBuilder:
    """Builder for session creation requests with fluent API"""

    def __init__(self):
        self._user_id = SessionTestDataFactory.make_user_id()
        self._session_id = None
        self._conversation_data = {}
        self._metadata = {}

    def with_user_id(self, value: str) -> 'SessionCreateRequestBuilder':
        """Set custom user ID"""
        self._user_id = value
        return self

    def with_session_id(self, value: str) -> 'SessionCreateRequestBuilder':
        """Set custom session ID"""
        self._session_id = value
        return self

    def with_conversation_data(self, value: Dict[str, Any]) -> 'SessionCreateRequestBuilder':
        """Set conversation data"""
        self._conversation_data = value
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'SessionCreateRequestBuilder':
        """Set metadata"""
        self._metadata = value
        return self

    def with_platform(self, platform: str) -> 'SessionCreateRequestBuilder':
        """Set platform in metadata"""
        self._metadata["platform"] = platform
        return self

    def with_topic(self, topic: str) -> 'SessionCreateRequestBuilder':
        """Set topic in conversation data"""
        self._conversation_data["topic"] = topic
        return self

    def build(self) -> SessionCreateRequestContract:
        """Build the request"""
        return SessionCreateRequestContract(
            user_id=self._user_id,
            session_id=self._session_id,
            conversation_data=self._conversation_data,
            metadata=self._metadata,
        )


class SessionUpdateRequestBuilder:
    """Builder for session update requests with fluent API"""

    def __init__(self):
        self._status = None
        self._conversation_data = None
        self._metadata = None

    def with_status(self, value: str) -> 'SessionUpdateRequestBuilder':
        """Set session status"""
        self._status = value
        return self

    def with_status_ended(self) -> 'SessionUpdateRequestBuilder':
        """Set status to ended"""
        self._status = SessionStatusEnum.ENDED.value
        return self

    def with_status_completed(self) -> 'SessionUpdateRequestBuilder':
        """Set status to completed"""
        self._status = SessionStatusEnum.COMPLETED.value
        return self

    def with_conversation_data(self, value: Dict[str, Any]) -> 'SessionUpdateRequestBuilder':
        """Set conversation data"""
        self._conversation_data = value
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'SessionUpdateRequestBuilder':
        """Set metadata"""
        self._metadata = value
        return self

    def build(self) -> SessionUpdateRequestContract:
        """Build the request"""
        return SessionUpdateRequestContract(
            status=self._status,
            conversation_data=self._conversation_data,
            metadata=self._metadata,
        )


class MessageCreateRequestBuilder:
    """Builder for message creation requests with fluent API"""

    def __init__(self):
        self._role = MessageRoleEnum.USER.value
        self._content = SessionTestDataFactory.make_content()
        self._message_type = MessageTypeEnum.CHAT.value
        self._metadata = {}
        self._tokens_used = 0
        self._cost_usd = 0.0

    def with_role(self, value: str) -> 'MessageCreateRequestBuilder':
        """Set message role"""
        self._role = value
        return self

    def as_user(self) -> 'MessageCreateRequestBuilder':
        """Set role to user"""
        self._role = MessageRoleEnum.USER.value
        return self

    def as_assistant(self) -> 'MessageCreateRequestBuilder':
        """Set role to assistant"""
        self._role = MessageRoleEnum.ASSISTANT.value
        return self

    def as_system(self) -> 'MessageCreateRequestBuilder':
        """Set role to system"""
        self._role = MessageRoleEnum.SYSTEM.value
        return self

    def with_content(self, value: str) -> 'MessageCreateRequestBuilder':
        """Set message content"""
        self._content = value
        return self

    def with_message_type(self, value: str) -> 'MessageCreateRequestBuilder':
        """Set message type"""
        self._message_type = value
        return self

    def as_tool_call(self) -> 'MessageCreateRequestBuilder':
        """Set type to tool_call"""
        self._message_type = MessageTypeEnum.TOOL_CALL.value
        return self

    def as_tool_result(self) -> 'MessageCreateRequestBuilder':
        """Set type to tool_result"""
        self._message_type = MessageTypeEnum.TOOL_RESULT.value
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'MessageCreateRequestBuilder':
        """Set metadata"""
        self._metadata = value
        return self

    def with_tokens_used(self, value: int) -> 'MessageCreateRequestBuilder':
        """Set tokens used"""
        self._tokens_used = value
        return self

    def with_cost_usd(self, value: float) -> 'MessageCreateRequestBuilder':
        """Set cost in USD"""
        self._cost_usd = value
        return self

    def with_metrics(self, tokens: int, cost: float) -> 'MessageCreateRequestBuilder':
        """Set both tokens and cost"""
        self._tokens_used = tokens
        self._cost_usd = cost
        return self

    def build(self) -> MessageCreateRequestContract:
        """Build the request"""
        return MessageCreateRequestContract(
            role=self._role,
            content=self._content,
            message_type=self._message_type,
            metadata=self._metadata,
            tokens_used=self._tokens_used,
            cost_usd=self._cost_usd,
        )
