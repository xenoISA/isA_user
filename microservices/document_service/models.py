"""
Document Service Models

Models for knowledge base document management with RAG and authorization
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import json


# ==================== Enumerations ====================

class DocumentType(str, Enum):
    """Document type"""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class DocumentStatus(str, Enum):
    """Document indexing status"""
    DRAFT = "draft"                      # Draft, not yet indexed
    INDEXING = "indexing"                # Currently being indexed
    INDEXED = "indexed"                  # Successfully indexed
    UPDATE_PENDING = "update_pending"    # Pending incremental update
    UPDATING = "updating"                # Currently updating
    ARCHIVED = "archived"                # Archived
    FAILED = "failed"                    # Indexing failed
    DELETED = "deleted"                  # Soft deleted


class AccessLevel(str, Enum):
    """Document access level"""
    PRIVATE = "private"                  # Only creator
    TEAM = "team"                        # Team members
    ORGANIZATION = "organization"        # Organization members
    PUBLIC = "public"                    # Public access


class ChunkingStrategy(str, Enum):
    """Chunking strategy for document processing"""
    FIXED_SIZE = "fixed_size"            # Fixed size chunks
    SEMANTIC = "semantic"                # Semantic chunking
    PARAGRAPH = "paragraph"              # Paragraph-based
    RECURSIVE = "recursive"              # Recursive character splitting


class UpdateStrategy(str, Enum):
    """RAG update strategy"""
    FULL = "full"                        # Delete old, full reindex
    SMART = "smart"                      # Smart incremental (similarity-based)
    DIFF = "diff"                        # Diff-based precise update


# ==================== Core Models ====================

class KnowledgeDocument(BaseModel):
    """Knowledge base document core model"""
    doc_id: str
    user_id: str
    organization_id: Optional[str] = None

    # Document basic info
    title: str
    description: Optional[str] = None
    doc_type: DocumentType
    file_id: str  # Storage Service file ID
    file_size: int = 0
    file_url: Optional[str] = None

    # Version control
    version: int = 1
    parent_version_id: Optional[str] = None  # Parent version ID
    is_latest: bool = True

    # RAG indexing info
    status: DocumentStatus = DocumentStatus.DRAFT
    chunk_count: int = 0
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    indexed_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None

    # Authorization
    access_level: AccessLevel = AccessLevel.PRIVATE
    allowed_users: List[str] = Field(default_factory=list)      # Authorized users
    allowed_groups: List[str] = Field(default_factory=list)     # Authorized groups
    denied_users: List[str] = Field(default_factory=list)       # Explicitly denied users

    # Qdrant collection info
    collection_name: str = "default"  # Qdrant collection name
    point_ids: List[str] = Field(default_factory=list)  # Qdrant point IDs

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('metadata', mode='before')
    @classmethod
    def parse_json_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else {}
            except json.JSONDecodeError:
                return {}
        return v if v is not None else {}

    @field_validator('allowed_users', 'allowed_groups', 'denied_users', 'point_ids', 'tags', mode='before')
    @classmethod
    def parse_json_array(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        return v if v is not None else []

    class Config:
        from_attributes = True


class DocumentPermissionHistory(BaseModel):
    """Document permission change history"""
    history_id: int
    doc_id: str
    changed_by: str
    old_access_level: Optional[AccessLevel] = None
    new_access_level: Optional[AccessLevel] = None
    users_added: List[str] = Field(default_factory=list)
    users_removed: List[str] = Field(default_factory=list)
    groups_added: List[str] = Field(default_factory=list)
    groups_removed: List[str] = Field(default_factory=list)
    changed_at: datetime

    @field_validator('users_added', 'users_removed', 'groups_added', 'groups_removed', mode='before')
    @classmethod
    def parse_json_array(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        return v if v is not None else []

    class Config:
        from_attributes = True


# ==================== Request Models ====================

class DocumentCreateRequest(BaseModel):
    """Document creation request"""
    title: str = Field(..., description="Document title", min_length=1, max_length=500)
    description: Optional[str] = Field(None, description="Document description", max_length=2000)
    doc_type: DocumentType = Field(..., description="Document type")
    file_id: str = Field(..., description="Storage service file ID")
    access_level: AccessLevel = Field(AccessLevel.PRIVATE, description="Access level")
    allowed_users: List[str] = Field(default_factory=list, description="Authorized user IDs")
    allowed_groups: List[str] = Field(default_factory=list, description="Authorized group IDs")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    chunking_strategy: ChunkingStrategy = Field(ChunkingStrategy.SEMANTIC, description="Chunking strategy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DocumentUpdateRequest(BaseModel):
    """Document update request (incremental RAG update)"""
    new_file_id: str = Field(..., description="New file ID")
    update_strategy: UpdateStrategy = Field(UpdateStrategy.SMART, description="Update strategy")
    title: Optional[str] = Field(None, description="New title")
    description: Optional[str] = Field(None, description="New description")
    tags: Optional[List[str]] = Field(None, description="Updated tags")


class DocumentPermissionUpdateRequest(BaseModel):
    """Document permission update request"""
    access_level: Optional[AccessLevel] = Field(None, description="New access level")
    add_users: List[str] = Field(default_factory=list, description="Users to add")
    remove_users: List[str] = Field(default_factory=list, description="Users to remove")
    add_groups: List[str] = Field(default_factory=list, description="Groups to add")
    remove_groups: List[str] = Field(default_factory=list, description="Groups to remove")


class RAGQueryRequest(BaseModel):
    """RAG query request with permission filtering"""
    query: str = Field(..., description="Query text", min_length=1)
    top_k: int = Field(5, ge=1, le=50, description="Number of results")
    doc_types: List[DocumentType] = Field(default_factory=list, description="Filter by document types")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int = Field(500, ge=50, le=4000, description="Max response tokens")


class SemanticSearchRequest(BaseModel):
    """Semantic search request"""
    query: str = Field(..., description="Search query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results")
    doc_types: List[DocumentType] = Field(default_factory=list, description="Filter by document types")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum relevance score")


# ==================== Response Models ====================

class DocumentResponse(BaseModel):
    """Document response"""
    doc_id: str
    user_id: str
    organization_id: Optional[str]
    title: str
    description: Optional[str]
    doc_type: DocumentType
    file_id: str
    file_size: int
    version: int
    is_latest: bool
    status: DocumentStatus
    chunk_count: int
    access_level: AccessLevel
    indexed_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    tags: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class DocumentVersionResponse(BaseModel):
    """Document version response"""
    doc_id: str
    version: int
    parent_version_id: Optional[str]
    is_latest: bool
    status: DocumentStatus
    chunk_count: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class SearchResultItem(BaseModel):
    """Search result item"""
    doc_id: str
    title: str
    doc_type: DocumentType
    relevance_score: float
    snippet: str
    file_id: str
    chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class RAGQueryResponse(BaseModel):
    """RAG query response"""
    query: str
    answer: str
    sources: List[SearchResultItem] = Field(default_factory=list)
    confidence: float = 0.0
    latency_ms: float = 0.0

    class Config:
        from_attributes = True


class SemanticSearchResponse(BaseModel):
    """Semantic search response"""
    query: str
    results: List[SearchResultItem] = Field(default_factory=list)
    total_count: int = 0
    latency_ms: float = 0.0

    class Config:
        from_attributes = True


class DocumentPermissionResponse(BaseModel):
    """Document permission response"""
    doc_id: str
    access_level: AccessLevel
    allowed_users: List[str] = Field(default_factory=list)
    allowed_groups: List[str] = Field(default_factory=list)
    denied_users: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class DocumentStatsResponse(BaseModel):
    """Document statistics response"""
    user_id: str
    total_documents: int = 0
    indexed_documents: int = 0
    total_chunks: int = 0
    total_size_bytes: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)

    class Config:
        from_attributes = True


# ==================== Service Status Models ====================

class DocumentServiceStatus(BaseModel):
    """Document service status response"""
    service: str = "document_service"
    status: str = "operational"
    port: int = 8227
    version: str = "1.0.0"
    database_connected: bool
    timestamp: datetime


# ==================== Export Models ====================

__all__ = [
    # Enums
    'DocumentType', 'DocumentStatus', 'AccessLevel', 'ChunkingStrategy', 'UpdateStrategy',
    # Core Models
    'KnowledgeDocument', 'DocumentPermissionHistory',
    # Request Models
    'DocumentCreateRequest', 'DocumentUpdateRequest', 'DocumentPermissionUpdateRequest',
    'RAGQueryRequest', 'SemanticSearchRequest',
    # Response Models
    'DocumentResponse', 'DocumentVersionResponse', 'SearchResultItem',
    'RAGQueryResponse', 'SemanticSearchResponse', 'DocumentPermissionResponse',
    'DocumentStatsResponse', 'DocumentServiceStatus'
]
