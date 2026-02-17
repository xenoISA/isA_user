"""
Document Service Event Models

Event data models for document_service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field



# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class DocumentEventType(str, Enum):
    """
    Events published by document_service.

    Stream: document-stream
    Subjects: document.>
    """
    DOCUMENT_CREATED = "document.created"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_INDEXED = "document.indexed"
    DOCUMENT_INDEXING_FAILED = "document.indexing.failed"


class DocumentSubscribedEventType(str, Enum):
    """Events that document_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class DocumentStreamConfig:
    """Stream configuration for document_service"""
    STREAM_NAME = "document-stream"
    SUBJECTS = ["document.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "document"



# =============================================================================
# Event Data Models
# =============================================================================

class DocumentBaseEventData(BaseModel):
    """Base event data for document_service events."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
