"""
Document Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import (
    KnowledgeDocument,
    DocumentPermissionHistory,
    DocumentStatus,
    DocumentType,
    AccessLevel,
)


# ==================== Custom Exceptions ====================

class DocumentNotFoundError(Exception):
    """Document not found error - defined here to avoid importing service"""
    pass


class DocumentValidationError(Exception):
    """Document validation error - defined here to avoid importing service"""
    pass


class DocumentPermissionError(Exception):
    """Document permission error - defined here to avoid importing service"""
    pass


class DocumentServiceError(Exception):
    """General document service error - defined here to avoid importing service"""
    pass


# ==================== Repository Protocol ====================

@runtime_checkable
class DocumentRepositoryProtocol(Protocol):
    """
    Interface for Document Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create_document(
        self, document_data: KnowledgeDocument
    ) -> Optional[KnowledgeDocument]:
        """Create a new knowledge document"""
        ...

    async def get_document_by_id(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Get document by ID"""
        ...

    async def get_document_by_file_id(
        self, file_id: str, user_id: str
    ) -> Optional[KnowledgeDocument]:
        """Get document by file ID and user ID"""
        ...

    async def list_user_documents(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        doc_type: Optional[DocumentType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[KnowledgeDocument]:
        """List user's documents with pagination and filters"""
        ...

    async def update_document(
        self, doc_id: str, update_data: Dict[str, Any]
    ) -> Optional[KnowledgeDocument]:
        """Update document fields"""
        ...

    async def update_document_status(
        self, doc_id: str, status: DocumentStatus, chunk_count: Optional[int] = None
    ) -> bool:
        """Update document status and optionally chunk count"""
        ...

    async def delete_document(
        self, doc_id: str, user_id: str, soft: bool = True
    ) -> bool:
        """Delete document (soft or hard)"""
        ...

    async def mark_version_as_old(self, doc_id: str) -> bool:
        """Mark a document version as not latest"""
        ...

    async def list_document_versions(
        self, file_id: str, user_id: str
    ) -> List[KnowledgeDocument]:
        """List all versions of a document"""
        ...

    async def create_document_version(
        self,
        base_doc_id: str,
        new_file_id: str,
        new_version: int,
        chunk_count: int,
        point_ids: List[str],
        user_id: str,
    ) -> Optional[KnowledgeDocument]:
        """Create a new version of an existing document"""
        ...

    async def update_document_permissions(
        self,
        doc_id: str,
        access_level: Optional[AccessLevel] = None,
        allowed_users: Optional[List[str]] = None,
        allowed_groups: Optional[List[str]] = None,
        denied_users: Optional[List[str]] = None,
    ) -> bool:
        """Update document permissions"""
        ...

    async def record_permission_change(
        self, history_data: DocumentPermissionHistory
    ) -> bool:
        """Record permission change history"""
        ...

    async def get_permission_history(
        self, doc_id: str, limit: int = 50
    ) -> List[DocumentPermissionHistory]:
        """Get permission change history for a document"""
        ...

    async def get_user_stats(
        self, user_id: str, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user's document statistics"""
        ...

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...


# ==================== Event Bus Protocol ====================

@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


# ==================== Service Client Protocols ====================

@runtime_checkable
class StorageClientProtocol(Protocol):
    """Interface for Storage Service Client"""

    async def get_file_info(
        self, file_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get file information from storage service"""
        ...

    async def get_download_url(
        self, file_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get download URL for a file"""
        ...


@runtime_checkable
class AuthorizationClientProtocol(Protocol):
    """Interface for Authorization Service Client"""

    async def check_permission(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
    ) -> bool:
        """Check if user has permission for action on resource"""
        ...


@runtime_checkable
class DigitalAnalyticsClientProtocol(Protocol):
    """Interface for Digital Analytics Client"""

    def is_enabled(self) -> bool:
        """Check if Digital Analytics is enabled"""
        ...

    async def store_content(
        self,
        user_id: str,
        content: str,
        content_type: str,
        collection_name: str,
        metadata: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Store content for RAG indexing"""
        ...

    async def generate_response(
        self,
        user_id: str,
        query: str,
        collection_name: str,
        top_k: int,
    ) -> Optional[Dict[str, Any]]:
        """Generate RAG response"""
        ...

    async def search_content(
        self,
        user_id: str,
        query: str,
        collection_name: str,
        top_k: int,
    ) -> Optional[Dict[str, Any]]:
        """Semantic search in content"""
        ...
