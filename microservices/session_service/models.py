"""
Session Service Models

Independent models for session management microservice.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived" 
    ENDED = "ended"


class MessageType(str, Enum):
    """Message type enumeration"""
    CHAT = "chat"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    NOTIFICATION = "notification"


class Session(BaseModel):
    """Session model for session service"""
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    conversation_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Conversation data")
    status: str = Field(default="active", description="Session status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")
    is_active: bool = Field(default=True, description="Is session active")
    message_count: int = Field(default=0, description="Message count")
    total_tokens: int = Field(default=0, description="Total tokens")
    total_cost: float = Field(default=0.0, description="Total cost")
    session_summary: str = Field(default="", description="Session summary")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionMessage(BaseModel):
    """Session message model"""
    message_id: Optional[str] = None
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    message_type: str = Field(default="chat", description="Message type")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Message metadata")
    tokens_used: int = Field(default=0, description="Tokens used")
    cost_usd: float = Field(default=0.0, description="Cost in USD")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionMemory(BaseModel):
    """Session memory model"""
    memory_id: Optional[str] = None
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    memory_type: str = Field(..., description="Memory type")
    content: str = Field(..., description="Memory content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Memory metadata")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Session Service Specific Request Models

class SessionCreateRequest(BaseModel):
    """Session create request"""
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Optional session ID (auto-generated if not provided)")
    conversation_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Initial conversation data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")


class SessionUpdateRequest(BaseModel):
    """Session update request"""
    status: Optional[str] = Field(None, description="Session status")
    conversation_data: Optional[Dict[str, Any]] = Field(None, description="Updated conversation data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class MessageCreateRequest(BaseModel):
    """Message create request"""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    message_type: str = Field(default="chat", description="Message type")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Message metadata")
    tokens_used: int = Field(default=0, description="Tokens used")
    cost_usd: float = Field(default=0.0, description="Cost in USD")


class MemoryCreateRequest(BaseModel):
    """Memory create request"""
    memory_type: str = Field(..., description="Memory type")
    content: str = Field(..., description="Memory content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Memory metadata")


class MemoryUpdateRequest(BaseModel):
    """Memory update request"""
    content: Optional[str] = Field(None, description="Updated memory content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated memory metadata")


# Session Service Specific Response Models

class SessionResponse(BaseModel):
    """Session response"""
    session_id: str
    user_id: str
    status: str
    conversation_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_active: bool
    message_count: int
    total_tokens: int
    total_cost: float
    session_summary: str = ""
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_activity: Optional[datetime]

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Session list response"""
    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    """Message response"""
    message_id: str
    session_id: str
    user_id: str
    role: str
    content: str
    message_type: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tokens_used: int
    cost_usd: float
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Message list response"""
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int


class MemoryResponse(BaseModel):
    """Memory response"""
    memory_id: str
    session_id: str
    user_id: str
    memory_type: str
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class SessionSummaryResponse(BaseModel):
    """Session summary response"""
    session_id: str
    user_id: str
    status: str
    message_count: int
    total_tokens: int
    total_cost: float
    has_memory: bool
    is_active: bool
    created_at: Optional[datetime]
    last_activity: Optional[datetime]


class SessionStatsResponse(BaseModel):
    """Session service statistics"""
    total_sessions: int = 0
    active_sessions: int = 0
    total_messages: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    average_messages_per_session: float = 0.0


# Service Status Models

class SessionServiceStatus(BaseModel):
    """Session service status response"""
    service: str = "session_service"
    status: str = "operational"
    port: int = 8205
    version: str = "1.0.0"
    database_connected: bool
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


# Export all models
__all__ = [
    'SessionStatus', 'MessageType',
    'Session', 'SessionMessage', 'SessionMemory',
    'SessionCreateRequest', 'SessionUpdateRequest', 'MessageCreateRequest',
    'MemoryCreateRequest', 'MemoryUpdateRequest',
    'SessionResponse', 'SessionListResponse', 'MessageResponse',
    'MessageListResponse', 'MemoryResponse', 'SessionSummaryResponse',
    'SessionStatsResponse', 'SessionServiceStatus', 'ErrorResponse'
]