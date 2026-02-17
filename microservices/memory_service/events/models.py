"""
Memory Service Event Models

Pydantic models for all events published by Memory Service
"""

from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class MemoryEventType(str, Enum):
    """
    Events published by memory_service.

    Stream: memory-stream
    Subjects: memory.>
    """
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    FACTUAL_MEMORY_STORED = "memory.factual.stored"
    EPISODIC_MEMORY_STORED = "memory.episodic.stored"
    PROCEDURAL_MEMORY_STORED = "memory.procedural.stored"
    SEMANTIC_MEMORY_STORED = "memory.semantic.stored"
    WORKING_MEMORY_ACTIVATED = "memory.working.activated"
    SESSION_MEMORY_DEACTIVATED = "memory.session.deactivated"


class MemorySubscribedEventType(str, Enum):
    """Events that memory_service subscribes to from other services."""
    SESSION_ENDED = "session.ended"
    USER_DELETED = "user.deleted"


class MemoryStreamConfig:
    """Stream configuration for memory_service"""
    STREAM_NAME = "memory-stream"
    SUBJECTS = ["memory.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "memory"

from typing import Optional, Dict, Any, List
from datetime import datetime


class MemoryCreatedEvent(BaseModel):
    """Event published when a memory is created"""

    memory_id: str = Field(..., description="Unique memory ID")
    memory_type: str = Field(..., description="Type of memory (factual/episodic/procedural/semantic/working/session)")
    user_id: str = Field(..., description="User ID who owns the memory")
    content: str = Field(..., description="Memory content")
    importance_score: Optional[float] = Field(None, description="Importance score (0.0-1.0)")
    tags: Optional[List[str]] = Field(None, description="Memory tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    timestamp: str = Field(..., description="Creation timestamp")


class MemoryUpdatedEvent(BaseModel):
    """Event published when a memory is updated"""

    memory_id: str = Field(..., description="Unique memory ID")
    memory_type: str = Field(..., description="Type of memory")
    user_id: str = Field(..., description="User ID who owns the memory")
    updated_fields: List[str] = Field(..., description="List of updated field names")
    timestamp: str = Field(..., description="Update timestamp")


class MemoryDeletedEvent(BaseModel):
    """Event published when a memory is deleted"""

    memory_id: str = Field(..., description="Unique memory ID")
    memory_type: str = Field(..., description="Type of memory")
    user_id: str = Field(..., description="User ID who owns the memory")
    timestamp: str = Field(..., description="Deletion timestamp")


class FactualMemoryStoredEvent(BaseModel):
    """Event published when factual memories are stored from AI extraction"""

    user_id: str = Field(..., description="User ID")
    count: int = Field(..., description="Number of memories extracted")
    importance_score: float = Field(..., description="Average importance score")
    source: str = Field(default="dialog", description="Source of extraction (dialog/manual)")
    timestamp: str = Field(..., description="Storage timestamp")


class EpisodicMemoryStoredEvent(BaseModel):
    """Event published when episodic memories are stored from AI extraction"""

    user_id: str = Field(..., description="User ID")
    count: int = Field(..., description="Number of memories extracted")
    importance_score: float = Field(..., description="Average importance score")
    source: str = Field(default="dialog", description="Source of extraction (dialog/manual)")
    timestamp: str = Field(..., description="Storage timestamp")


class ProceduralMemoryStoredEvent(BaseModel):
    """Event published when procedural memories are stored from AI extraction"""

    user_id: str = Field(..., description="User ID")
    count: int = Field(..., description="Number of memories extracted")
    importance_score: float = Field(..., description="Average importance score")
    source: str = Field(default="dialog", description="Source of extraction (dialog/manual)")
    timestamp: str = Field(..., description="Storage timestamp")


class SemanticMemoryStoredEvent(BaseModel):
    """Event published when semantic memories are stored from AI extraction"""

    user_id: str = Field(..., description="User ID")
    count: int = Field(..., description="Number of memories extracted")
    importance_score: float = Field(..., description="Average importance score")
    source: str = Field(default="dialog", description="Source of extraction (dialog/manual)")
    timestamp: str = Field(..., description="Storage timestamp")


class SessionMemoryDeactivatedEvent(BaseModel):
    """Event published when a session memory is deactivated"""

    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    duration_seconds: Optional[int] = Field(None, description="Session duration in seconds")
    message_count: Optional[int] = Field(None, description="Number of messages in session")
    timestamp: str = Field(..., description="Deactivation timestamp")
