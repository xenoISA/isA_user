"""
Storage Service - Event Data Models

定义所有事件相关的数据模型（Pydantic models）
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class StorageEventType(str, Enum):
    """
    Events published by storage_service.

    Stream: storage-stream
    Subjects: storage.>
    """
    FILE_UPLOADED = "file.uploaded"
    FILE_UPLOADED_WITH_AI = "file.uploaded.with_ai"
    FILE_SHARED = "file.shared"
    FILE_DELETED = "file.deleted"
    FILE_INDEXING_REQUESTED = "file.indexing.requested"
    FILE_INDEXED = "file.indexed"
    FILE_INDEXING_FAILED = "file.indexing.failed"


class StorageSubscribedEventType(str, Enum):
    """Events that storage_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class StorageStreamConfig:
    """Stream configuration for storage_service"""
    STREAM_NAME = "storage-stream"
    SUBJECTS = ["storage.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "storage"



# ==================== File Upload Events ====================


class FileUploadedEventData(BaseModel):
    """文件上传事件数据"""

    file_id: str
    file_name: str
    file_size: int
    content_type: str
    user_id: str
    organization_id: Optional[str] = None
    access_level: str = "private"
    download_url: str
    bucket_name: str
    object_name: str
    timestamp: str


class FileUploadedWithAIEventData(FileUploadedEventData):
    """带AI元数据的文件上传事件"""

    has_ai_data: bool = True
    chunk_id: str  # Qdrant chunk ID
    ai_metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== File Indexing Events ====================


class FileIndexingRequestedEventData(BaseModel):
    """文件索引请求事件数据"""

    file_id: str
    user_id: str
    organization_id: Optional[str] = None
    file_name: str
    file_type: str
    file_size: int
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    bucket_name: str
    object_name: str


class FileIndexedEventData(BaseModel):
    """文件索引完成事件数据"""

    file_id: str
    user_id: str
    file_name: str
    file_size: int
    indexed_at: str


class FileIndexingFailedEventData(BaseModel):
    """文件索引失败事件数据"""

    file_id: str
    user_id: str
    error: str


# ==================== File Management Events ====================


class FileDeletedEventData(BaseModel):
    """文件删除事件数据"""

    file_id: str
    file_name: str
    file_size: int
    user_id: str
    permanent: bool
    timestamp: str


class FileSharedEventData(BaseModel):
    """文件分享事件数据"""

    share_id: str
    file_id: str
    file_name: str
    shared_by: str
    shared_with: Optional[str] = None
    shared_with_email: Optional[str] = None
    expires_at: str
    timestamp: str


