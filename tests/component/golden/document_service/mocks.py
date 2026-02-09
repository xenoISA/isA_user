"""
Document Service - Mock Dependencies

Mock implementations for component testing.
Returns KnowledgeDocument model objects as expected by the service.
Implements protocols defined in document_service/protocols.py
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid

# Import the actual models used by the service
from microservices.document_service.models import (
    KnowledgeDocument,
    DocumentPermissionHistory,
    DocumentType,
    DocumentStatus,
    AccessLevel,
    ChunkingStrategy,
)


class MockDocumentRepository:
    """Mock document repository for component testing

    Implements DocumentRepositoryProtocol interface.
    Returns KnowledgeDocument model objects, not dicts.
    """

    def __init__(self):
        self._documents: Dict[str, KnowledgeDocument] = {}
        self._permission_history: List[DocumentPermissionHistory] = []
        self._stats: Dict[str, Any] = {}
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    def set_document(
        self,
        doc_id: str,
        user_id: str,
        title: str,
        doc_type: DocumentType = DocumentType.PDF,
        file_id: Optional[str] = None,
        status: DocumentStatus = DocumentStatus.DRAFT,
        access_level: AccessLevel = AccessLevel.PRIVATE,
        allowed_users: Optional[List[str]] = None,
        allowed_groups: Optional[List[str]] = None,
        denied_users: Optional[List[str]] = None,
        organization_id: Optional[str] = None,
        description: Optional[str] = None,
        file_size: int = 1024,
        version: int = 1,
        is_latest: bool = True,
        chunk_count: int = 0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        indexed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ):
        """Add a document to the mock repository"""
        doc = KnowledgeDocument(
            doc_id=doc_id,
            user_id=user_id,
            organization_id=organization_id,
            title=title,
            description=description,
            doc_type=doc_type,
            file_id=file_id or f"file_{uuid.uuid4().hex[:8]}",
            file_size=file_size,
            version=version,
            is_latest=is_latest,
            status=status,
            chunk_count=chunk_count,
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            access_level=access_level,
            allowed_users=allowed_users or [],
            allowed_groups=allowed_groups or [],
            denied_users=denied_users or [],
            collection_name=f"user_{user_id}",
            point_ids=[],
            metadata=metadata or {},
            tags=tags or [],
            indexed_at=indexed_at,
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._documents[doc_id] = doc

    def set_stats(
        self,
        total_documents: int = 0,
        indexed_documents: int = 0,
        total_chunks: int = 0,
        total_size_bytes: int = 0,
        by_type: Optional[Dict[str, int]] = None,
        by_status: Optional[Dict[str, int]] = None,
    ):
        """Set document statistics"""
        self._stats = {
            "total_documents": total_documents,
            "indexed_documents": indexed_documents,
            "total_chunks": total_chunks,
            "total_size_bytes": total_size_bytes,
            "by_type": by_type or {},
            "by_status": by_status or {},
        }

    def set_error(self, error: Exception):
        """Set an error to be raised on operations"""
        self._error = error

    def clear_error(self):
        """Clear the error"""
        self._error = None

    def _log_call(self, method: str, **kwargs):
        """Log method calls for assertions"""
        self._call_log.append({"method": method, "kwargs": kwargs})

    def assert_called(self, method: str):
        """Assert that a method was called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method in called_methods, f"Expected {method} to be called, but got {called_methods}"

    def assert_called_with(self, method: str, **kwargs):
        """Assert that a method was called with specific kwargs"""
        for call in self._call_log:
            if call["method"] == method:
                for key, value in kwargs.items():
                    assert key in call["kwargs"], f"Expected kwarg {key} not found"
                    assert call["kwargs"][key] == value, f"Expected {key}={value}, got {call['kwargs'][key]}"
                return
        raise AssertionError(f"Expected {method} to be called with {kwargs}")

    def get_call_count(self, method: str) -> int:
        """Get number of times a method was called"""
        return sum(1 for c in self._call_log if c["method"] == method)

    async def check_connection(self) -> bool:
        """Check database connection"""
        self._log_call("check_connection")
        if self._error:
            return False
        return True

    async def create_document(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Create a new document"""
        self._log_call("create_document", doc_id=document.doc_id, user_id=document.user_id)
        if self._error:
            raise self._error

        self._documents[document.doc_id] = document
        return document

    async def get_document_by_id(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Get document by ID"""
        self._log_call("get_document_by_id", doc_id=doc_id)
        if self._error:
            raise self._error

        return self._documents.get(doc_id)

    async def list_user_documents(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        doc_type: Optional[DocumentType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[KnowledgeDocument]:
        """List user's documents with filters"""
        self._log_call(
            "list_user_documents",
            user_id=user_id,
            organization_id=organization_id,
            status=status,
            doc_type=doc_type,
            limit=limit,
            offset=offset,
        )
        if self._error:
            raise self._error

        results = []
        for doc in self._documents.values():
            # Filter by user
            if doc.user_id != user_id:
                continue
            # Filter by organization
            if organization_id and doc.organization_id != organization_id:
                continue
            # Filter by status
            if status and doc.status != status:
                continue
            # Filter by type
            if doc_type and doc.doc_type != doc_type:
                continue
            # Only latest versions
            if doc.is_latest:
                results.append(doc)

        # Apply pagination
        return results[offset : offset + limit]

    async def update_document(self, doc_id: str, update_data: Dict[str, Any]) -> bool:
        """Update document fields"""
        self._log_call("update_document", doc_id=doc_id, update_data=update_data)
        if self._error:
            raise self._error

        if doc_id not in self._documents:
            return False

        doc = self._documents[doc_id]
        # Create new document with updates
        doc_dict = {
            "doc_id": doc.doc_id,
            "user_id": doc.user_id,
            "organization_id": update_data.get("organization_id", doc.organization_id),
            "title": update_data.get("title", doc.title),
            "description": update_data.get("description", doc.description),
            "doc_type": doc.doc_type,
            "file_id": update_data.get("file_id", doc.file_id),
            "file_size": update_data.get("file_size", doc.file_size),
            "version": doc.version,
            "is_latest": doc.is_latest,
            "status": doc.status,
            "chunk_count": update_data.get("chunk_count", doc.chunk_count),
            "chunking_strategy": doc.chunking_strategy,
            "access_level": update_data.get("access_level", doc.access_level),
            "allowed_users": update_data.get("allowed_users", doc.allowed_users),
            "allowed_groups": update_data.get("allowed_groups", doc.allowed_groups),
            "denied_users": update_data.get("denied_users", doc.denied_users),
            "collection_name": doc.collection_name,
            "point_ids": update_data.get("point_ids", doc.point_ids),
            "metadata": update_data.get("metadata", doc.metadata),
            "tags": update_data.get("tags", doc.tags),
            "indexed_at": doc.indexed_at,
            "created_at": doc.created_at,
            "updated_at": datetime.now(timezone.utc),
        }
        self._documents[doc_id] = KnowledgeDocument(**doc_dict)
        return True

    async def update_document_status(
        self, doc_id: str, status: DocumentStatus, chunk_count: Optional[int] = None
    ) -> bool:
        """Update document status"""
        self._log_call("update_document_status", doc_id=doc_id, status=status, chunk_count=chunk_count)
        if self._error:
            raise self._error

        if doc_id not in self._documents:
            return False

        doc = self._documents[doc_id]
        update_data = {"status": status}
        if chunk_count is not None:
            update_data["chunk_count"] = chunk_count
        if status == DocumentStatus.INDEXED:
            update_data["indexed_at"] = datetime.now(timezone.utc)

        # Recreate document with new status
        doc_dict = doc.model_dump()
        doc_dict.update(update_data)
        doc_dict["updated_at"] = datetime.now(timezone.utc)
        self._documents[doc_id] = KnowledgeDocument(**doc_dict)
        return True

    async def delete_document(self, doc_id: str, user_id: str, soft: bool = True) -> bool:
        """Delete document"""
        self._log_call("delete_document", doc_id=doc_id, user_id=user_id, soft=soft)
        if self._error:
            raise self._error

        if doc_id not in self._documents:
            return False

        if soft:
            # Soft delete - update status
            await self.update_document_status(doc_id, DocumentStatus.DELETED)
        else:
            # Hard delete - remove from storage
            del self._documents[doc_id]
        return True

    async def update_document_permissions(
        self,
        doc_id: str,
        access_level: AccessLevel,
        allowed_users: List[str],
        allowed_groups: List[str],
        denied_users: List[str],
    ) -> bool:
        """Update document permissions"""
        self._log_call(
            "update_document_permissions",
            doc_id=doc_id,
            access_level=access_level,
            allowed_users=allowed_users,
            allowed_groups=allowed_groups,
            denied_users=denied_users,
        )
        if self._error:
            raise self._error

        if doc_id not in self._documents:
            return False

        doc = self._documents[doc_id]
        doc_dict = doc.model_dump()
        doc_dict["access_level"] = access_level
        doc_dict["allowed_users"] = allowed_users
        doc_dict["allowed_groups"] = allowed_groups
        doc_dict["denied_users"] = denied_users
        doc_dict["updated_at"] = datetime.now(timezone.utc)
        self._documents[doc_id] = KnowledgeDocument(**doc_dict)
        return True

    async def record_permission_change(self, history: DocumentPermissionHistory) -> bool:
        """Record permission change in history"""
        self._log_call("record_permission_change", doc_id=history.doc_id, changed_by=history.changed_by)
        if self._error:
            raise self._error

        self._permission_history.append(history)
        return True

    async def create_document_version(
        self,
        base_doc_id: str,
        new_file_id: str,
        new_version: int,
        chunk_count: int,
        point_ids: List[str],
        user_id: str,
    ) -> KnowledgeDocument:
        """Create a new document version"""
        self._log_call(
            "create_document_version",
            base_doc_id=base_doc_id,
            new_file_id=new_file_id,
            new_version=new_version,
        )
        if self._error:
            raise self._error

        base_doc = self._documents.get(base_doc_id)
        if not base_doc:
            raise ValueError(f"Base document {base_doc_id} not found")

        # Create new version
        new_doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        new_doc = KnowledgeDocument(
            doc_id=new_doc_id,
            user_id=base_doc.user_id,
            organization_id=base_doc.organization_id,
            title=base_doc.title,
            description=base_doc.description,
            doc_type=base_doc.doc_type,
            file_id=new_file_id,
            file_size=base_doc.file_size,
            version=new_version,
            parent_version_id=base_doc_id,
            is_latest=True,
            status=DocumentStatus.INDEXED,
            chunk_count=chunk_count,
            chunking_strategy=base_doc.chunking_strategy,
            access_level=base_doc.access_level,
            allowed_users=base_doc.allowed_users,
            allowed_groups=base_doc.allowed_groups,
            denied_users=base_doc.denied_users,
            collection_name=base_doc.collection_name,
            point_ids=point_ids,
            metadata=base_doc.metadata,
            tags=base_doc.tags,
            indexed_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._documents[new_doc_id] = new_doc
        return new_doc

    async def mark_version_as_old(self, doc_id: str) -> bool:
        """Mark document version as old (not latest)"""
        self._log_call("mark_version_as_old", doc_id=doc_id)
        if self._error:
            raise self._error

        if doc_id not in self._documents:
            return False

        doc = self._documents[doc_id]
        doc_dict = doc.model_dump()
        doc_dict["is_latest"] = False
        doc_dict["updated_at"] = datetime.now(timezone.utc)
        self._documents[doc_id] = KnowledgeDocument(**doc_dict)
        return True

    async def get_user_stats(
        self, user_id: str, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user's document statistics"""
        self._log_call("get_user_stats", user_id=user_id, organization_id=organization_id)
        if self._error:
            raise self._error

        if self._stats:
            return self._stats

        # Calculate from data
        user_docs = [d for d in self._documents.values() if d.user_id == user_id and d.is_latest]
        total = len(user_docs)
        indexed = sum(1 for d in user_docs if d.status == DocumentStatus.INDEXED)
        chunks = sum(d.chunk_count for d in user_docs)
        size = sum(d.file_size for d in user_docs)

        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for doc in user_docs:
            by_type[doc.doc_type.value] = by_type.get(doc.doc_type.value, 0) + 1
            by_status[doc.status.value] = by_status.get(doc.status.value, 0) + 1

        return {
            "total_documents": total,
            "indexed_documents": indexed,
            "total_chunks": chunks,
            "total_size_bytes": size,
            "by_type": by_type,
            "by_status": by_status,
        }


class MockEventBus:
    """Mock NATS event bus"""

    def __init__(self):
        self.published_events: List[Any] = []
        self._call_log: List[Dict] = []

    async def publish(self, event: Any):
        """Publish event"""
        self._call_log.append({"method": "publish", "event": event})
        self.published_events.append(event)

    async def publish_event(self, event: Any):
        """Publish event (alias)"""
        await self.publish(event)

    def assert_published(self, event_type: str = None):
        """Assert that an event was published"""
        assert len(self.published_events) > 0, "No events were published"
        if event_type:
            # Event class stores event_type.value as 'type' attribute
            event_types = [str(getattr(e, "type", getattr(e, "event_type", e))) for e in self.published_events]
            assert any(event_type.lower() in et.lower() for et in event_types), f"Expected {event_type} event, got {event_types}"

    def assert_not_published(self):
        """Assert that no events were published"""
        assert len(self.published_events) == 0, f"Expected no events, got {len(self.published_events)}"

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def clear(self):
        """Clear published events"""
        self.published_events = []
        self._call_log = []


class MockStorageClient:
    """Mock storage service client"""

    def __init__(self):
        self._files: Dict[str, Dict] = {}
        self._call_log: List[Dict] = []
        self._error: Optional[Exception] = None

    def set_file(self, file_id: str, file_size: int = 1024, download_url: str = None):
        """Add a file to mock storage"""
        self._files[file_id] = {
            "file_id": file_id,
            "file_size": file_size,
            "download_url": download_url or f"https://storage.example.com/{file_id}",
        }

    def set_error(self, error: Exception):
        """Set error to raise"""
        self._error = error

    async def get_file_info(self, file_id: str, user_id: str) -> Optional[Dict]:
        """Get file info"""
        self._call_log.append({"method": "get_file_info", "file_id": file_id, "user_id": user_id})
        if self._error:
            raise self._error
        return self._files.get(file_id)

    async def get_download_url(self, file_id: str, user_id: str) -> Optional[Dict]:
        """Get download URL for file"""
        self._call_log.append({"method": "get_download_url", "file_id": file_id, "user_id": user_id})
        if self._error:
            raise self._error
        file_info = self._files.get(file_id)
        if file_info:
            return {"download_url": file_info["download_url"]}
        return None


class MockAuthorizationClient:
    """Mock authorization service client"""

    def __init__(self):
        self._permissions: Dict[str, bool] = {}
        self._call_log: List[Dict] = []
        self._error: Optional[Exception] = None

    def set_permission(self, user_id: str, resource_id: str, action: str, allowed: bool = True):
        """Set permission for user on resource"""
        key = f"{user_id}:{resource_id}:{action}"
        self._permissions[key] = allowed

    def set_error(self, error: Exception):
        """Set error to raise"""
        self._error = error

    async def check_permission(
        self, user_id: str, resource_type: str, resource_id: str, action: str
    ) -> bool:
        """Check if user has permission"""
        self._call_log.append({
            "method": "check_permission",
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
        })
        if self._error:
            raise self._error

        key = f"{user_id}:{resource_id}:{action}"
        return self._permissions.get(key, False)


class MockDigitalAnalyticsClient:
    """Mock Digital Analytics client for RAG operations"""

    def __init__(self):
        self._enabled: bool = True
        self._store_results: Dict[str, Dict] = {}
        self._search_results: Dict[str, Dict] = {}
        self._rag_results: Dict[str, Dict] = {}
        self._call_log: List[Dict] = []
        self._error: Optional[Exception] = None

    def set_enabled(self, enabled: bool):
        """Enable/disable the client"""
        self._enabled = enabled

    def is_enabled(self) -> bool:
        """Check if client is enabled"""
        return self._enabled

    def set_store_result(self, content_hash: str, result: Dict):
        """Set result for store_content call"""
        self._store_results[content_hash] = result

    def set_search_result(self, query: str, result: Dict):
        """Set result for search_content call"""
        self._search_results[query.lower()] = result

    def set_rag_result(self, query: str, result: Dict):
        """Set result for generate_response call"""
        self._rag_results[query.lower()] = result

    def set_error(self, error: Exception):
        """Set error to raise"""
        self._error = error

    async def store_content(
        self,
        user_id: str,
        content: str,
        content_type: str,
        collection_name: str,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Store content for RAG"""
        self._call_log.append({
            "method": "store_content",
            "user_id": user_id,
            "content_type": content_type,
            "collection_name": collection_name,
        })
        if self._error:
            raise self._error

        # Return pre-set result or default
        content_hash = hash(content)
        if str(content_hash) in self._store_results:
            return self._store_results[str(content_hash)]

        # Default result
        return {
            "chunks_stored": 10,
            "point_ids": [f"point_{i}" for i in range(10)],
        }

    async def search_content(
        self,
        user_id: str,
        query: str,
        collection_name: str,
        top_k: int = 10,
    ) -> Dict:
        """Search content"""
        self._call_log.append({
            "method": "search_content",
            "user_id": user_id,
            "query": query,
            "collection_name": collection_name,
            "top_k": top_k,
        })
        if self._error:
            raise self._error

        # Return pre-set result or default
        if query.lower() in self._search_results:
            return self._search_results[query.lower()]

        return {"results": []}

    async def generate_response(
        self,
        user_id: str,
        query: str,
        collection_name: str,
        top_k: int = 5,
    ) -> Dict:
        """Generate RAG response"""
        self._call_log.append({
            "method": "generate_response",
            "user_id": user_id,
            "query": query,
            "collection_name": collection_name,
            "top_k": top_k,
        })
        if self._error:
            raise self._error

        # Return pre-set result or default
        if query.lower() in self._rag_results:
            return self._rag_results[query.lower()]

        return {
            "response": "Default mock response",
            "confidence": 0.8,
        }
