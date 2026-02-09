"""
Document Service Data Contract

Defines canonical data structures for document service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for document service test data.
"""

import uuid
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enumerations (Mirror production models)
# ============================================================================

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
    DRAFT = "draft"
    INDEXING = "indexing"
    INDEXED = "indexed"
    UPDATE_PENDING = "update_pending"
    UPDATING = "updating"
    ARCHIVED = "archived"
    FAILED = "failed"
    DELETED = "deleted"


class AccessLevel(str, Enum):
    """Document access level"""
    PRIVATE = "private"
    TEAM = "team"
    ORGANIZATION = "organization"
    PUBLIC = "public"


class ChunkingStrategy(str, Enum):
    """Chunking strategy for document processing"""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    PARAGRAPH = "paragraph"
    RECURSIVE = "recursive"


class UpdateStrategy(str, Enum):
    """RAG update strategy"""
    FULL = "full"
    SMART = "smart"
    DIFF = "diff"


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class DocumentCreateRequestContract(BaseModel):
    """
    Contract: Document creation request schema

    Used for creating knowledge documents in tests.
    Maps to POST /api/v1/documents endpoint.
    """
    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    description: Optional[str] = Field(None, max_length=2000, description="Document description")
    doc_type: DocumentType = Field(..., description="Document type")
    file_id: str = Field(..., min_length=1, description="Storage service file ID")
    access_level: AccessLevel = Field(AccessLevel.PRIVATE, description="Access level")
    allowed_users: List[str] = Field(default_factory=list, description="Authorized user IDs")
    allowed_groups: List[str] = Field(default_factory=list, description="Authorized group IDs")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    chunking_strategy: ChunkingStrategy = Field(ChunkingStrategy.SEMANTIC, description="Chunking strategy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Machine Learning Guide",
                "description": "Comprehensive ML guide for beginners",
                "doc_type": "pdf",
                "file_id": "file_abc123def456",
                "access_level": "private",
                "allowed_users": [],
                "allowed_groups": [],
                "tags": ["ml", "guide"],
                "chunking_strategy": "semantic",
                "metadata": {"author": "John Doe"}
            }
        }


class DocumentUpdateRequestContract(BaseModel):
    """
    Contract: Document update request schema (incremental RAG update)

    Used for updating document content in tests.
    Maps to PUT /api/v1/documents/{doc_id}/update endpoint.
    """
    new_file_id: str = Field(..., min_length=1, description="New file ID")
    update_strategy: UpdateStrategy = Field(UpdateStrategy.SMART, description="Update strategy")
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="New title")
    description: Optional[str] = Field(None, max_length=2000, description="New description")
    tags: Optional[List[str]] = Field(None, description="Updated tags")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "new_file_id": "file_xyz789",
                "update_strategy": "smart",
                "title": "Updated ML Guide",
                "description": "Updated comprehensive ML guide",
                "tags": ["ml", "guide", "updated"]
            }
        }


class DocumentPermissionUpdateRequestContract(BaseModel):
    """
    Contract: Document permission update request schema

    Used for updating document permissions in tests.
    Maps to PUT /api/v1/documents/{doc_id}/permissions endpoint.
    """
    access_level: Optional[AccessLevel] = Field(None, description="New access level")
    add_users: List[str] = Field(default_factory=list, description="Users to add")
    remove_users: List[str] = Field(default_factory=list, description="Users to remove")
    add_groups: List[str] = Field(default_factory=list, description="Groups to add")
    remove_groups: List[str] = Field(default_factory=list, description="Groups to remove")

    class Config:
        json_schema_extra = {
            "example": {
                "access_level": "team",
                "add_users": ["user_456", "user_789"],
                "remove_users": ["user_old"],
                "add_groups": ["group_new"],
                "remove_groups": []
            }
        }


class RAGQueryRequestContract(BaseModel):
    """
    Contract: RAG query request schema

    Used for RAG queries with permission filtering in tests.
    Maps to POST /api/v1/documents/rag/query endpoint.
    """
    query: str = Field(..., min_length=1, description="Query text")
    top_k: int = Field(5, ge=1, le=50, description="Number of results")
    doc_types: List[DocumentType] = Field(default_factory=list, description="Filter by document types")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int = Field(500, ge=50, le=4000, description="Max response tokens")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is machine learning?",
                "top_k": 5,
                "doc_types": ["pdf"],
                "tags": ["ml"],
                "temperature": 0.7,
                "max_tokens": 500
            }
        }


class SemanticSearchRequestContract(BaseModel):
    """
    Contract: Semantic search request schema

    Used for semantic search with permission filtering in tests.
    Maps to POST /api/v1/documents/search endpoint.
    """
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results")
    doc_types: List[DocumentType] = Field(default_factory=list, description="Filter by document types")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum relevance score")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "query": "neural networks",
                "top_k": 10,
                "doc_types": ["pdf", "docx"],
                "tags": [],
                "min_score": 0.5
            }
        }


class DocumentListParamsContract(BaseModel):
    """
    Contract: Document list query parameters schema

    Used for listing documents with pagination and filtering in tests.
    """
    user_id: str = Field(..., min_length=1, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID filter")
    status: Optional[DocumentStatus] = Field(None, description="Status filter")
    doc_type: Optional[DocumentType] = Field(None, description="Document type filter")
    limit: int = Field(50, ge=1, le=100, description="Max results")
    offset: int = Field(0, ge=0, description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "organization_id": None,
                "status": "indexed",
                "doc_type": "pdf",
                "limit": 50,
                "offset": 0
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class DocumentResponseContract(BaseModel):
    """
    Contract: Document response schema

    Validates API response structure for document operations.
    """
    doc_id: str = Field(..., description="Document ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    title: str = Field(..., description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    doc_type: DocumentType = Field(..., description="Document type")
    file_id: str = Field(..., description="File ID")
    file_size: int = Field(0, ge=0, description="File size in bytes")
    version: int = Field(1, ge=1, description="Version number")
    is_latest: bool = Field(True, description="Is latest version")
    status: DocumentStatus = Field(..., description="Document status")
    chunk_count: int = Field(0, ge=0, description="Number of chunks")
    access_level: AccessLevel = Field(..., description="Access level")
    indexed_at: Optional[datetime] = Field(None, description="Indexed timestamp")
    created_at: Optional[datetime] = Field(None, description="Created timestamp")
    updated_at: Optional[datetime] = Field(None, description="Updated timestamp")
    tags: List[str] = Field(default_factory=list, description="Document tags")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "doc_abc123def456",
                "user_id": "user_123",
                "organization_id": None,
                "title": "ML Guide",
                "description": "ML guide",
                "doc_type": "pdf",
                "file_id": "file_123",
                "file_size": 1024000,
                "version": 1,
                "is_latest": True,
                "status": "indexed",
                "chunk_count": 25,
                "access_level": "private",
                "indexed_at": "2025-12-17T10:30:00Z",
                "created_at": "2025-12-17T10:00:00Z",
                "updated_at": "2025-12-17T10:30:00Z",
                "tags": ["ml"]
            }
        }


class DocumentPermissionResponseContract(BaseModel):
    """
    Contract: Document permission response schema

    Validates API response structure for permission operations.
    """
    doc_id: str = Field(..., description="Document ID")
    access_level: AccessLevel = Field(..., description="Access level")
    allowed_users: List[str] = Field(default_factory=list, description="Allowed users")
    allowed_groups: List[str] = Field(default_factory=list, description="Allowed groups")
    denied_users: List[str] = Field(default_factory=list, description="Denied users")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "doc_abc123",
                "access_level": "team",
                "allowed_users": ["user_456"],
                "allowed_groups": ["group_123"],
                "denied_users": []
            }
        }


class SearchResultItemContract(BaseModel):
    """
    Contract: Search result item schema

    Represents a single search result.
    """
    doc_id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    doc_type: DocumentType = Field(..., description="Document type")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    snippet: str = Field(..., description="Content snippet")
    file_id: str = Field(..., description="File ID")
    chunk_id: Optional[str] = Field(None, description="Chunk ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "doc_abc123",
                "title": "ML Guide",
                "doc_type": "pdf",
                "relevance_score": 0.95,
                "snippet": "Machine learning is...",
                "file_id": "file_123",
                "chunk_id": "chunk_456",
                "metadata": {}
            }
        }


class RAGQueryResponseContract(BaseModel):
    """
    Contract: RAG query response schema

    Validates API response structure for RAG queries.
    """
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    sources: List[SearchResultItemContract] = Field(default_factory=list, description="Source documents")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    latency_ms: float = Field(0.0, ge=0.0, description="Query latency in ms")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is ML?",
                "answer": "Machine learning is...",
                "sources": [],
                "confidence": 0.85,
                "latency_ms": 234.5
            }
        }


class SemanticSearchResponseContract(BaseModel):
    """
    Contract: Semantic search response schema

    Validates API response structure for semantic search.
    """
    query: str = Field(..., description="Original query")
    results: List[SearchResultItemContract] = Field(default_factory=list, description="Search results")
    total_count: int = Field(0, ge=0, description="Total result count")
    latency_ms: float = Field(0.0, ge=0.0, description="Search latency in ms")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "neural networks",
                "results": [],
                "total_count": 0,
                "latency_ms": 123.4
            }
        }


class DocumentStatsResponseContract(BaseModel):
    """
    Contract: Document statistics response schema

    Validates API response structure for user statistics.
    """
    user_id: str = Field(..., description="User ID")
    total_documents: int = Field(0, ge=0, description="Total documents")
    indexed_documents: int = Field(0, ge=0, description="Indexed documents")
    total_chunks: int = Field(0, ge=0, description="Total chunks")
    total_size_bytes: int = Field(0, ge=0, description="Total size in bytes")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count by type")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Count by status")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "total_documents": 42,
                "indexed_documents": 40,
                "total_chunks": 1250,
                "total_size_bytes": 52428800,
                "by_type": {"pdf": 20, "docx": 15, "txt": 7},
                "by_status": {"indexed": 40, "draft": 2}
            }
        }


class DocumentServiceStatusContract(BaseModel):
    """
    Contract: Document service status response schema

    Validates API response structure for service health check.
    """
    service: str = Field(default="document_service", description="Service name")
    status: str = Field(..., pattern="^(operational|degraded|down)$", description="Service status")
    port: int = Field(8227, ge=1024, le=65535, description="Service port")
    version: str = Field(..., description="Service version")
    database_connected: bool = Field(..., description="Database connection status")
    timestamp: datetime = Field(..., description="Status check timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "service": "document_service",
                "status": "operational",
                "port": 8227,
                "version": "1.0.0",
                "database_connected": True,
                "timestamp": "2025-12-17T10:30:00Z"
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class DocumentTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    Zero hardcoded data - all values generated dynamically.
    """

    # ========================================================================
    # Valid Data Generators (20+ methods)
    # ========================================================================

    @staticmethod
    def make_doc_id() -> str:
        """Generate unique test document ID"""
        return f"doc_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate unique test user ID"""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate unique test organization ID"""
        return f"org_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_file_id() -> str:
        """Generate unique test file ID"""
        return f"file_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_title() -> str:
        """Generate random document title"""
        subjects = ["Machine Learning", "Data Science", "AI", "Python", "Cloud", "DevOps", "Security"]
        types = ["Guide", "Manual", "Reference", "Handbook", "Tutorial", "Overview"]
        return f"{random.choice(subjects)} {random.choice(types)} {secrets.token_hex(4)}"

    @staticmethod
    def make_description() -> str:
        """Generate random document description"""
        return f"Test document description {secrets.token_hex(8)}"

    @staticmethod
    def make_doc_type() -> DocumentType:
        """Generate random document type"""
        return random.choice(list(DocumentType))

    @staticmethod
    def make_access_level() -> AccessLevel:
        """Generate random access level"""
        return random.choice(list(AccessLevel))

    @staticmethod
    def make_chunking_strategy() -> ChunkingStrategy:
        """Generate random chunking strategy"""
        return random.choice(list(ChunkingStrategy))

    @staticmethod
    def make_update_strategy() -> UpdateStrategy:
        """Generate random update strategy"""
        return random.choice(list(UpdateStrategy))

    @staticmethod
    def make_status() -> DocumentStatus:
        """Generate random document status"""
        return random.choice(list(DocumentStatus))

    @staticmethod
    def make_tags() -> List[str]:
        """Generate random tags"""
        all_tags = ["ml", "ai", "data", "python", "cloud", "security", "devops", "guide", "tutorial"]
        return random.sample(all_tags, k=random.randint(1, 3))

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate random metadata"""
        return {
            "source": f"test_source_{secrets.token_hex(4)}",
            "version": f"1.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "author": f"author_{secrets.token_hex(4)}",
        }

    @staticmethod
    def make_query() -> str:
        """Generate random query text"""
        queries = [
            "What is machine learning?",
            "How does deep learning work?",
            "Explain neural networks",
            "What are the best practices for data science?",
            "How to implement AI in production?",
        ]
        return random.choice(queries) + f" {secrets.token_hex(4)}"

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days_ago: int = 30) -> datetime:
        """Generate past timestamp"""
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    @staticmethod
    def make_file_size() -> int:
        """Generate random file size (1KB - 100MB)"""
        return random.randint(1024, 100 * 1024 * 1024)

    @staticmethod
    def make_chunk_count() -> int:
        """Generate random chunk count"""
        return random.randint(1, 500)

    @staticmethod
    def make_relevance_score() -> float:
        """Generate random relevance score"""
        return round(random.uniform(0.5, 1.0), 3)

    @staticmethod
    def make_snippet() -> str:
        """Generate random content snippet"""
        return f"This is a sample snippet from the document... {secrets.token_hex(16)}"

    @staticmethod
    def make_create_request(**overrides) -> DocumentCreateRequestContract:
        """
        Create valid document creation request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            DocumentCreateRequestContract with valid data
        """
        defaults = {
            "title": DocumentTestDataFactory.make_title(),
            "description": DocumentTestDataFactory.make_description(),
            "doc_type": DocumentTestDataFactory.make_doc_type(),
            "file_id": DocumentTestDataFactory.make_file_id(),
            "access_level": AccessLevel.PRIVATE,
            "allowed_users": [],
            "allowed_groups": [],
            "tags": DocumentTestDataFactory.make_tags(),
            "chunking_strategy": ChunkingStrategy.SEMANTIC,
            "metadata": DocumentTestDataFactory.make_metadata(),
        }
        defaults.update(overrides)
        return DocumentCreateRequestContract(**defaults)

    @staticmethod
    def make_update_request(**overrides) -> DocumentUpdateRequestContract:
        """
        Create valid document update request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            DocumentUpdateRequestContract with valid data
        """
        defaults = {
            "new_file_id": DocumentTestDataFactory.make_file_id(),
            "update_strategy": UpdateStrategy.SMART,
            "title": DocumentTestDataFactory.make_title(),
            "description": DocumentTestDataFactory.make_description(),
            "tags": DocumentTestDataFactory.make_tags(),
        }
        defaults.update(overrides)
        return DocumentUpdateRequestContract(**defaults)

    @staticmethod
    def make_permission_request(**overrides) -> DocumentPermissionUpdateRequestContract:
        """
        Create valid permission update request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            DocumentPermissionUpdateRequestContract with valid data
        """
        defaults = {
            "access_level": AccessLevel.TEAM,
            "add_users": [DocumentTestDataFactory.make_user_id()],
            "remove_users": [],
            "add_groups": [],
            "remove_groups": [],
        }
        defaults.update(overrides)
        return DocumentPermissionUpdateRequestContract(**defaults)

    @staticmethod
    def make_rag_query_request(**overrides) -> RAGQueryRequestContract:
        """
        Create valid RAG query request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            RAGQueryRequestContract with valid data
        """
        defaults = {
            "query": DocumentTestDataFactory.make_query(),
            "top_k": 5,
            "doc_types": [],
            "tags": [],
            "temperature": 0.7,
            "max_tokens": 500,
        }
        defaults.update(overrides)
        return RAGQueryRequestContract(**defaults)

    @staticmethod
    def make_search_request(**overrides) -> SemanticSearchRequestContract:
        """
        Create valid semantic search request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            SemanticSearchRequestContract with valid data
        """
        defaults = {
            "query": DocumentTestDataFactory.make_query(),
            "top_k": 10,
            "doc_types": [],
            "tags": [],
            "min_score": 0.5,
        }
        defaults.update(overrides)
        return SemanticSearchRequestContract(**defaults)

    @staticmethod
    def make_list_params(**overrides) -> DocumentListParamsContract:
        """
        Create valid list parameters with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            DocumentListParamsContract with valid data
        """
        defaults = {
            "user_id": DocumentTestDataFactory.make_user_id(),
            "organization_id": None,
            "status": None,
            "doc_type": None,
            "limit": 50,
            "offset": 0,
        }
        defaults.update(overrides)
        return DocumentListParamsContract(**defaults)

    @staticmethod
    def make_document_response(**overrides) -> DocumentResponseContract:
        """
        Create expected document response for assertions.

        Used in tests to validate API responses match contract.
        """
        now = datetime.now(timezone.utc)
        defaults = {
            "doc_id": DocumentTestDataFactory.make_doc_id(),
            "user_id": DocumentTestDataFactory.make_user_id(),
            "organization_id": None,
            "title": DocumentTestDataFactory.make_title(),
            "description": DocumentTestDataFactory.make_description(),
            "doc_type": DocumentTestDataFactory.make_doc_type(),
            "file_id": DocumentTestDataFactory.make_file_id(),
            "file_size": DocumentTestDataFactory.make_file_size(),
            "version": 1,
            "is_latest": True,
            "status": DocumentStatus.INDEXED,
            "chunk_count": DocumentTestDataFactory.make_chunk_count(),
            "access_level": AccessLevel.PRIVATE,
            "indexed_at": now,
            "created_at": now - timedelta(hours=1),
            "updated_at": now,
            "tags": DocumentTestDataFactory.make_tags(),
        }
        defaults.update(overrides)
        return DocumentResponseContract(**defaults)

    @staticmethod
    def make_permission_response(**overrides) -> DocumentPermissionResponseContract:
        """
        Create expected permission response for assertions.
        """
        defaults = {
            "doc_id": DocumentTestDataFactory.make_doc_id(),
            "access_level": AccessLevel.PRIVATE,
            "allowed_users": [],
            "allowed_groups": [],
            "denied_users": [],
        }
        defaults.update(overrides)
        return DocumentPermissionResponseContract(**defaults)

    @staticmethod
    def make_search_result_item(**overrides) -> SearchResultItemContract:
        """
        Create search result item for assertions.
        """
        defaults = {
            "doc_id": DocumentTestDataFactory.make_doc_id(),
            "title": DocumentTestDataFactory.make_title(),
            "doc_type": DocumentTestDataFactory.make_doc_type(),
            "relevance_score": DocumentTestDataFactory.make_relevance_score(),
            "snippet": DocumentTestDataFactory.make_snippet(),
            "file_id": DocumentTestDataFactory.make_file_id(),
            "chunk_id": f"chunk_{secrets.token_hex(8)}",
            "metadata": {},
        }
        defaults.update(overrides)
        return SearchResultItemContract(**defaults)

    @staticmethod
    def make_rag_response(**overrides) -> RAGQueryResponseContract:
        """
        Create expected RAG response for assertions.
        """
        defaults = {
            "query": DocumentTestDataFactory.make_query(),
            "answer": f"This is a generated answer based on the documents... {secrets.token_hex(16)}",
            "sources": [],
            "confidence": 0.85,
            "latency_ms": random.uniform(100, 500),
        }
        defaults.update(overrides)
        return RAGQueryResponseContract(**defaults)

    @staticmethod
    def make_search_response(**overrides) -> SemanticSearchResponseContract:
        """
        Create expected search response for assertions.
        """
        defaults = {
            "query": DocumentTestDataFactory.make_query(),
            "results": [],
            "total_count": 0,
            "latency_ms": random.uniform(50, 200),
        }
        defaults.update(overrides)
        return SemanticSearchResponseContract(**defaults)

    @staticmethod
    def make_stats_response(**overrides) -> DocumentStatsResponseContract:
        """
        Create expected stats response for assertions.
        """
        total = random.randint(10, 100)
        indexed = int(total * 0.9)
        defaults = {
            "user_id": DocumentTestDataFactory.make_user_id(),
            "total_documents": total,
            "indexed_documents": indexed,
            "total_chunks": total * random.randint(10, 50),
            "total_size_bytes": total * random.randint(100000, 1000000),
            "by_type": {"pdf": int(total * 0.5), "docx": int(total * 0.3), "txt": int(total * 0.2)},
            "by_status": {"indexed": indexed, "draft": total - indexed},
        }
        defaults.update(overrides)
        return DocumentStatsResponseContract(**defaults)

    @staticmethod
    def make_service_status(**overrides) -> DocumentServiceStatusContract:
        """
        Create expected service status response for assertions.
        """
        defaults = {
            "service": "document_service",
            "status": "operational",
            "port": 8227,
            "version": "1.0.0",
            "database_connected": True,
            "timestamp": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return DocumentServiceStatusContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (15+ methods)
    # ========================================================================

    @staticmethod
    def make_invalid_create_request_empty_title() -> dict:
        """Generate create request with empty title"""
        return {
            "title": "",
            "doc_type": "pdf",
            "file_id": DocumentTestDataFactory.make_file_id(),
        }

    @staticmethod
    def make_invalid_create_request_whitespace_title() -> dict:
        """Generate create request with whitespace-only title"""
        return {
            "title": "   ",
            "doc_type": "pdf",
            "file_id": DocumentTestDataFactory.make_file_id(),
        }

    @staticmethod
    def make_invalid_create_request_missing_title() -> dict:
        """Generate create request missing title"""
        return {
            "doc_type": "pdf",
            "file_id": DocumentTestDataFactory.make_file_id(),
        }

    @staticmethod
    def make_invalid_create_request_missing_file_id() -> dict:
        """Generate create request missing file_id"""
        return {
            "title": DocumentTestDataFactory.make_title(),
            "doc_type": "pdf",
        }

    @staticmethod
    def make_invalid_create_request_invalid_doc_type() -> dict:
        """Generate create request with invalid doc_type"""
        return {
            "title": DocumentTestDataFactory.make_title(),
            "doc_type": "invalid_type",
            "file_id": DocumentTestDataFactory.make_file_id(),
        }

    @staticmethod
    def make_invalid_create_request_title_too_long() -> dict:
        """Generate create request with title exceeding max length"""
        return {
            "title": "A" * 501,  # Max is 500
            "doc_type": "pdf",
            "file_id": DocumentTestDataFactory.make_file_id(),
        }

    @staticmethod
    def make_invalid_update_request_missing_file_id() -> dict:
        """Generate update request missing new_file_id"""
        return {
            "update_strategy": "smart",
            "title": DocumentTestDataFactory.make_title(),
        }

    @staticmethod
    def make_invalid_update_request_empty_file_id() -> dict:
        """Generate update request with empty new_file_id"""
        return {
            "new_file_id": "",
            "update_strategy": "smart",
        }

    @staticmethod
    def make_invalid_update_request_invalid_strategy() -> dict:
        """Generate update request with invalid update_strategy"""
        return {
            "new_file_id": DocumentTestDataFactory.make_file_id(),
            "update_strategy": "invalid_strategy",
        }

    @staticmethod
    def make_invalid_rag_query_empty_query() -> dict:
        """Generate RAG query with empty query"""
        return {
            "query": "",
            "top_k": 5,
        }

    @staticmethod
    def make_invalid_rag_query_whitespace_query() -> dict:
        """Generate RAG query with whitespace-only query"""
        return {
            "query": "   ",
            "top_k": 5,
        }

    @staticmethod
    def make_invalid_rag_query_invalid_top_k() -> dict:
        """Generate RAG query with invalid top_k"""
        return {
            "query": DocumentTestDataFactory.make_query(),
            "top_k": 100,  # Max is 50
        }

    @staticmethod
    def make_invalid_rag_query_invalid_temperature() -> dict:
        """Generate RAG query with invalid temperature"""
        return {
            "query": DocumentTestDataFactory.make_query(),
            "top_k": 5,
            "temperature": 3.0,  # Max is 2.0
        }

    @staticmethod
    def make_invalid_search_request_empty_query() -> dict:
        """Generate search request with empty query"""
        return {
            "query": "",
            "top_k": 10,
        }

    @staticmethod
    def make_invalid_search_request_invalid_min_score() -> dict:
        """Generate search request with invalid min_score"""
        return {
            "query": DocumentTestDataFactory.make_query(),
            "top_k": 10,
            "min_score": 1.5,  # Max is 1.0
        }

    @staticmethod
    def make_invalid_list_params_invalid_limit() -> dict:
        """Generate list params with invalid limit"""
        return {
            "user_id": DocumentTestDataFactory.make_user_id(),
            "limit": 200,  # Max is 100
            "offset": 0,
        }

    @staticmethod
    def make_invalid_doc_id() -> str:
        """Generate invalid document ID format"""
        return "invalid_format"

    @staticmethod
    def make_nonexistent_doc_id() -> str:
        """Generate valid format but non-existent document ID"""
        return f"doc_nonexistent_{secrets.token_hex(6)}"


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class DocumentCreateRequestBuilder:
    """
    Builder pattern for creating complex document creation requests.

    Example:
        request = (
            DocumentCreateRequestBuilder()
            .with_title("My Document")
            .with_doc_type(DocumentType.PDF)
            .with_file_id("file_123")
            .with_access_level(AccessLevel.TEAM)
            .with_allowed_users(["user_456"])
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "title": DocumentTestDataFactory.make_title(),
            "description": None,
            "doc_type": DocumentType.PDF,
            "file_id": DocumentTestDataFactory.make_file_id(),
            "access_level": AccessLevel.PRIVATE,
            "allowed_users": [],
            "allowed_groups": [],
            "tags": [],
            "chunking_strategy": ChunkingStrategy.SEMANTIC,
            "metadata": {},
        }

    def with_title(self, title: str) -> "DocumentCreateRequestBuilder":
        """Set document title"""
        self._data["title"] = title
        return self

    def with_description(self, description: str) -> "DocumentCreateRequestBuilder":
        """Set document description"""
        self._data["description"] = description
        return self

    def with_doc_type(self, doc_type: DocumentType) -> "DocumentCreateRequestBuilder":
        """Set document type"""
        self._data["doc_type"] = doc_type
        return self

    def with_file_id(self, file_id: str) -> "DocumentCreateRequestBuilder":
        """Set file ID"""
        self._data["file_id"] = file_id
        return self

    def with_access_level(self, access_level: AccessLevel) -> "DocumentCreateRequestBuilder":
        """Set access level"""
        self._data["access_level"] = access_level
        return self

    def with_allowed_users(self, users: List[str]) -> "DocumentCreateRequestBuilder":
        """Set allowed users"""
        self._data["allowed_users"] = users
        return self

    def with_allowed_groups(self, groups: List[str]) -> "DocumentCreateRequestBuilder":
        """Set allowed groups"""
        self._data["allowed_groups"] = groups
        return self

    def with_tags(self, tags: List[str]) -> "DocumentCreateRequestBuilder":
        """Set tags"""
        self._data["tags"] = tags
        return self

    def with_chunking_strategy(self, strategy: ChunkingStrategy) -> "DocumentCreateRequestBuilder":
        """Set chunking strategy"""
        self._data["chunking_strategy"] = strategy
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "DocumentCreateRequestBuilder":
        """Set metadata"""
        self._data["metadata"] = metadata
        return self

    def build(self) -> DocumentCreateRequestContract:
        """Build the final request"""
        data = {k: v for k, v in self._data.items() if v is not None}
        return DocumentCreateRequestContract(**data)


class DocumentUpdateRequestBuilder:
    """
    Builder pattern for creating complex document update requests.

    Example:
        request = (
            DocumentUpdateRequestBuilder()
            .with_new_file_id("file_xyz")
            .with_update_strategy(UpdateStrategy.FULL)
            .with_title("Updated Title")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "new_file_id": DocumentTestDataFactory.make_file_id(),
            "update_strategy": UpdateStrategy.SMART,
            "title": None,
            "description": None,
            "tags": None,
        }

    def with_new_file_id(self, file_id: str) -> "DocumentUpdateRequestBuilder":
        """Set new file ID"""
        self._data["new_file_id"] = file_id
        return self

    def with_update_strategy(self, strategy: UpdateStrategy) -> "DocumentUpdateRequestBuilder":
        """Set update strategy"""
        self._data["update_strategy"] = strategy
        return self

    def with_title(self, title: str) -> "DocumentUpdateRequestBuilder":
        """Set new title"""
        self._data["title"] = title
        return self

    def with_description(self, description: str) -> "DocumentUpdateRequestBuilder":
        """Set new description"""
        self._data["description"] = description
        return self

    def with_tags(self, tags: List[str]) -> "DocumentUpdateRequestBuilder":
        """Set new tags"""
        self._data["tags"] = tags
        return self

    def build(self) -> DocumentUpdateRequestContract:
        """Build the final request"""
        data = {k: v for k, v in self._data.items() if v is not None}
        return DocumentUpdateRequestContract(**data)


class DocumentPermissionUpdateRequestBuilder:
    """
    Builder pattern for creating complex permission update requests.

    Example:
        request = (
            DocumentPermissionUpdateRequestBuilder()
            .with_access_level(AccessLevel.ORGANIZATION)
            .add_user("user_456")
            .add_group("group_789")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "access_level": None,
            "add_users": [],
            "remove_users": [],
            "add_groups": [],
            "remove_groups": [],
        }

    def with_access_level(self, access_level: AccessLevel) -> "DocumentPermissionUpdateRequestBuilder":
        """Set access level"""
        self._data["access_level"] = access_level
        return self

    def add_user(self, user_id: str) -> "DocumentPermissionUpdateRequestBuilder":
        """Add a user to allowed list"""
        self._data["add_users"].append(user_id)
        return self

    def remove_user(self, user_id: str) -> "DocumentPermissionUpdateRequestBuilder":
        """Remove a user from allowed list"""
        self._data["remove_users"].append(user_id)
        return self

    def add_group(self, group_id: str) -> "DocumentPermissionUpdateRequestBuilder":
        """Add a group to allowed list"""
        self._data["add_groups"].append(group_id)
        return self

    def remove_group(self, group_id: str) -> "DocumentPermissionUpdateRequestBuilder":
        """Remove a group from allowed list"""
        self._data["remove_groups"].append(group_id)
        return self

    def build(self) -> DocumentPermissionUpdateRequestContract:
        """Build the final request"""
        return DocumentPermissionUpdateRequestContract(**self._data)


class RAGQueryRequestBuilder:
    """
    Builder pattern for creating complex RAG query requests.

    Example:
        request = (
            RAGQueryRequestBuilder()
            .with_query("What is machine learning?")
            .with_top_k(10)
            .with_doc_types([DocumentType.PDF])
            .with_temperature(0.5)
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "query": DocumentTestDataFactory.make_query(),
            "top_k": 5,
            "doc_types": [],
            "tags": [],
            "temperature": 0.7,
            "max_tokens": 500,
        }

    def with_query(self, query: str) -> "RAGQueryRequestBuilder":
        """Set query text"""
        self._data["query"] = query
        return self

    def with_top_k(self, top_k: int) -> "RAGQueryRequestBuilder":
        """Set top_k"""
        self._data["top_k"] = top_k
        return self

    def with_doc_types(self, doc_types: List[DocumentType]) -> "RAGQueryRequestBuilder":
        """Set document type filter"""
        self._data["doc_types"] = doc_types
        return self

    def with_tags(self, tags: List[str]) -> "RAGQueryRequestBuilder":
        """Set tag filter"""
        self._data["tags"] = tags
        return self

    def with_temperature(self, temperature: float) -> "RAGQueryRequestBuilder":
        """Set temperature"""
        self._data["temperature"] = temperature
        return self

    def with_max_tokens(self, max_tokens: int) -> "RAGQueryRequestBuilder":
        """Set max tokens"""
        self._data["max_tokens"] = max_tokens
        return self

    def build(self) -> RAGQueryRequestContract:
        """Build the final request"""
        return RAGQueryRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "DocumentType",
    "DocumentStatus",
    "AccessLevel",
    "ChunkingStrategy",
    "UpdateStrategy",
    # Request Contracts
    "DocumentCreateRequestContract",
    "DocumentUpdateRequestContract",
    "DocumentPermissionUpdateRequestContract",
    "RAGQueryRequestContract",
    "SemanticSearchRequestContract",
    "DocumentListParamsContract",
    # Response Contracts
    "DocumentResponseContract",
    "DocumentPermissionResponseContract",
    "RAGQueryResponseContract",
    "SemanticSearchResponseContract",
    "SearchResultItemContract",
    "DocumentStatsResponseContract",
    "DocumentServiceStatusContract",
    # Factory
    "DocumentTestDataFactory",
    # Builders
    "DocumentCreateRequestBuilder",
    "DocumentUpdateRequestBuilder",
    "DocumentPermissionUpdateRequestBuilder",
    "RAGQueryRequestBuilder",
]
