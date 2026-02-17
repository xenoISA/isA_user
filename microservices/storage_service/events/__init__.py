"""
Storage Service - Events Module

集中导出所有 event 相关内容
"""

from .handlers import handle_file_indexing_request
from .models import (
    FileDeletedEventData,
    FileIndexedEventData,
    FileIndexingFailedEventData,
    FileIndexingRequestedEventData,
    FileSharedEventData,
    FileUploadedEventData,
    FileUploadedWithAIEventData,
)
from .publishers import StorageEventPublisher

__all__ = [
    # Publishers
    "StorageEventPublisher",
    # Handlers
    "handle_file_indexing_request",
    # Models
    "FileUploadedEventData",
    "FileUploadedWithAIEventData",
    "FileIndexingRequestedEventData",
    "FileIndexedEventData",
    "FileIndexingFailedEventData",
    "FileDeletedEventData",
    "FileSharedEventData",
]
