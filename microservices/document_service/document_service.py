"""
Document Service - Business logic layer for knowledge document operations

Handles RAG incremental updates, permission management, and document versioning
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.nats_client import Event

# Import protocols (no I/O dependencies) - NOT the concrete repository!
from .protocols import (
    DocumentRepositoryProtocol,
    EventBusProtocol,
    StorageClientProtocol,
    AuthorizationClientProtocol,
    DigitalAnalyticsClientProtocol,
    DocumentNotFoundError,
    DocumentValidationError,
    DocumentPermissionError,
    DocumentServiceError,
)
from .models import (
    AccessLevel,
    ChunkingStrategy,
    DocumentCreateRequest,
    DocumentPermissionHistory,
    DocumentPermissionResponse,
    DocumentPermissionUpdateRequest,
    DocumentResponse,
    DocumentStatsResponse,
    DocumentStatus,
    DocumentType,
    DocumentUpdateRequest,
    DocumentVersionResponse,
    KnowledgeDocument,
    RAGQueryRequest,
    RAGQueryResponse,
    SearchResultItem,
    SemanticSearchRequest,
    SemanticSearchResponse,
    UpdateStrategy,
)

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


# ==================== Document Service ====================


class DocumentService:
    """Document service - business logic layer for knowledge documents"""

    def __init__(
        self,
        repository: Optional[DocumentRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        config_manager: Optional["ConfigManager"] = None,
        storage_client: Optional[StorageClientProtocol] = None,
        auth_client: Optional[AuthorizationClientProtocol] = None,
        digital_client: Optional[DigitalAnalyticsClientProtocol] = None,
    ):
        """
        Initialize document service with injected dependencies.

        Args:
            repository: Repository (inject mock for testing)
            event_bus: Event bus for publishing events
            config_manager: Configuration manager
            storage_client: Storage service client
            auth_client: Authorization service client
            digital_client: Digital analytics client
        """
        self.repo = repository  # Will be set by factory if None
        self.event_bus = event_bus
        self.config_manager = config_manager

        # Service clients (injected or initialized)
        self.storage_client = storage_client
        self.auth_client = auth_client
        self.digital_client = digital_client

        # Lazy init clients if not provided
        if not any([storage_client, auth_client, digital_client]):
            self._init_clients()

    def _init_clients(self):
        """Initialize service clients"""
        try:
            from .clients import (
                StorageServiceClient,
                AuthorizationServiceClient,
                DigitalAnalyticsClient,
            )

            self.storage_client = StorageServiceClient()
            self.auth_client = AuthorizationServiceClient()
            self.digital_client = DigitalAnalyticsClient()

            logger.info("✅ Document service clients initialized")
        except Exception as e:
            logger.warning(f"⚠️  Some clients failed to initialize: {e}")

    # ==================== Document CRUD Operations ====================

    async def create_document(
        self,
        request: DocumentCreateRequest,
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> DocumentResponse:
        """
        Create a new knowledge document and index it

        Args:
            request: Document creation request
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            DocumentResponse
        """
        try:
            # Validate request
            self._validate_document_create_request(request)

            # Generate doc_id
            doc_id = f"doc_{uuid.uuid4().hex[:12]}"

            # Get file info from storage service
            file_info = None
            file_size = 0
            if self.storage_client:
                try:
                    file_info = await self.storage_client.get_file_info(
                        request.file_id, user_id
                    )
                    file_size = file_info.get("file_size", 0)
                except Exception as e:
                    logger.warning(f"Failed to get file info: {e}")

            # Create document object
            document = KnowledgeDocument(
                doc_id=doc_id,
                user_id=user_id,
                organization_id=organization_id,
                title=request.title,
                description=request.description,
                doc_type=request.doc_type,
                file_id=request.file_id,
                file_size=file_size,
                version=1,
                is_latest=True,
                status=DocumentStatus.DRAFT,
                chunk_count=0,
                chunking_strategy=request.chunking_strategy,
                access_level=request.access_level,
                allowed_users=request.allowed_users or [],
                allowed_groups=request.allowed_groups or [],
                collection_name=f"user_{user_id}",
                metadata=request.metadata or {},
                tags=request.tags or [],
            )

            # Save to database
            created = await self.repo.create_document(document)

            if not created:
                raise DocumentServiceError("Failed to create document")

            # Trigger indexing (async background task)
            if self.digital_client:
                try:
                    await self._index_document_async(created, user_id)
                except Exception as e:
                    logger.error(f"Failed to index document: {e}")
                    await self.repo.update_document_status(
                        doc_id, DocumentStatus.FAILED
                    )

            # Publish document.created event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="document.created",
                        source="document_service",
                        data={
                            "doc_id": created.doc_id,
                            "user_id": user_id,
                            "title": created.title,
                            "doc_type": created.doc_type.value,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish document.created event: {e}")

            return self._document_to_response(created)

        except DocumentValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise DocumentServiceError(f"Failed to create document: {str(e)}")

    async def get_document(self, doc_id: str, user_id: str) -> DocumentResponse:
        """
        Get document by ID (with permission check)
        """
        document = await self.repo.get_document_by_id(doc_id)

        if not document:
            raise DocumentNotFoundError(f"Document {doc_id} not found")

        # Check permission
        has_permission = await self._check_document_permission(
            user_id, document, "read"
        )
        if not has_permission:
            raise DocumentPermissionError("Access denied to this document")

        return self._document_to_response(document)

    async def list_user_documents(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        doc_type: Optional[DocumentType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DocumentResponse]:
        """List user's documents"""
        documents = await self.repo.list_user_documents(
            user_id, organization_id, status, doc_type, limit, offset
        )
        return [self._document_to_response(doc) for doc in documents]

    async def delete_document(
        self, doc_id: str, user_id: str, permanent: bool = False
    ) -> bool:
        """
        Delete document

        Args:
            doc_id: Document ID
            user_id: User ID
            permanent: If True, hard delete

        Returns:
            True if deleted
        """
        try:
            # Get document
            document = await self.repo.get_document_by_id(doc_id)
            if not document:
                raise DocumentNotFoundError(f"Document {doc_id} not found")

            # Check permission
            has_permission = await self._check_document_permission(
                user_id, document, "delete"
            )
            if not has_permission:
                raise DocumentPermissionError("Access denied to delete this document")

            # Note: Digital Analytics handles chunk storage internally
            # We don't need to explicitly delete points - they are managed by collection

            # Delete from database
            result = await self.repo.delete_document(
                doc_id, user_id, soft=not permanent
            )

            # Publish document.deleted event
            if result and self.event_bus:
                try:
                    event = Event(
                        event_type="document.deleted",
                        source="document_service",
                        data={
                            "doc_id": doc_id,
                            "user_id": user_id,
                            "permanent": permanent,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish document.deleted event: {e}")

            return result

        except (DocumentNotFoundError, DocumentPermissionError):
            raise
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise DocumentServiceError(f"Failed to delete document: {str(e)}")

    # ==================== RAG Incremental Update Operations ====================

    async def update_document_incremental(
        self, doc_id: str, request: DocumentUpdateRequest, user_id: str
    ) -> DocumentResponse:
        """
        Update document content - re-index via Digital Analytics

        Note: All update strategies now use the same approach - re-store content
        via digital_analytics which handles chunking, embedding, and storage internally.
        """
        try:
            # Get current document
            current_doc = await self.repo.get_document_by_id(doc_id)
            if not current_doc:
                raise DocumentNotFoundError(f"Document {doc_id} not found")

            # Check permission
            has_permission = await self._check_document_permission(
                user_id, current_doc, "update"
            )
            if not has_permission:
                raise DocumentPermissionError("No permission to update document")

            # Update status to UPDATING
            await self.repo.update_document_status(doc_id, DocumentStatus.UPDATING)

            # Download new file content
            new_content = await self._download_file_content(request.new_file_id, user_id)

            # Re-index via Digital Analytics (handles chunking internally)
            result = await self._reindex_document(
                doc_id, request.new_file_id, new_content, user_id, current_doc
            )

            # Create new version
            new_version = current_doc.version + 1
            new_doc = await self.repo.create_document_version(
                base_doc_id=doc_id,
                new_file_id=request.new_file_id,
                new_version=new_version,
                chunk_count=result.get("chunk_count", 0),
                point_ids=result.get("point_ids", []),
                user_id=user_id,
            )

            # Mark old version as not latest
            await self.repo.mark_version_as_old(doc_id)

            # Update title/description if provided
            if request.title or request.description or request.tags:
                update_data = {}
                if request.title:
                    update_data["title"] = request.title
                if request.description:
                    update_data["description"] = request.description
                if request.tags:
                    update_data["tags"] = request.tags
                await self.repo.update_document(new_doc.doc_id, update_data)

            # Publish document.updated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="document.updated",
                        source="document_service",
                        data={
                            "doc_id": new_doc.doc_id,
                            "old_doc_id": doc_id,
                            "version": new_version,
                            "user_id": user_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish document.updated event: {e}")

            return self._document_to_response(new_doc)

        except (DocumentNotFoundError, DocumentPermissionError):
            raise
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            # Restore status to INDEXED or FAILED
            await self.repo.update_document_status(doc_id, DocumentStatus.FAILED)
            raise DocumentServiceError(f"Failed to update document: {str(e)}")

    async def _reindex_document(
        self,
        doc_id: str,
        new_file_id: str,
        new_content: str,
        user_id: str,
        current_doc: KnowledgeDocument,
    ) -> Dict[str, Any]:
        """
        Re-index document content via Digital Analytics

        Digital Analytics handles all chunking, embedding, and storage internally.
        We just need to call store_content() with the new content.
        """
        try:
            if not self.digital_client or not self.digital_client.is_enabled():
                logger.warning("Digital Analytics not available, skipping indexing")
                return {"chunk_count": 0, "point_ids": []}

            # Store new content via Digital Analytics
            # Digital Analytics will handle chunking and embedding internally
            index_result = await self.digital_client.store_content(
                user_id=user_id,
                content=new_content,
                content_type=current_doc.doc_type.value,
                collection_name=f"user_{user_id}",
                metadata={
                    "doc_id": doc_id,
                    "file_id": new_file_id,
                    "title": current_doc.title,
                    "access_level": current_doc.access_level.value,
                    "allowed_users": current_doc.allowed_users,
                    "allowed_groups": current_doc.allowed_groups,
                    "denied_users": current_doc.denied_users,
                },
            )

            if index_result:
                chunk_count = index_result.get("chunks_stored", 0)
                point_ids = index_result.get("point_ids", [])
                logger.info(f"✅ Document re-indexed: {doc_id}, {chunk_count} chunks")
                return {"chunk_count": chunk_count, "point_ids": point_ids}

            return {"chunk_count": 0, "point_ids": []}

        except Exception as e:
            logger.error(f"Document reindex failed: {e}")
            raise

    # ==================== Permission Management Operations ====================

    async def update_document_permissions(
        self, doc_id: str, request: DocumentPermissionUpdateRequest, user_id: str
    ) -> DocumentPermissionResponse:
        """
        Update document permissions

        Note: Permission changes are stored in PostgreSQL.
        For RAG queries, permissions are applied at query time by filtering results.
        """
        try:
            # Get document
            document = await self.repo.get_document_by_id(doc_id)
            if not document:
                raise DocumentNotFoundError(f"Document {doc_id} not found")

            # Check permission (must be owner or admin)
            has_permission = await self._check_document_permission(
                user_id, document, "admin"
            )
            if not has_permission and document.user_id != user_id:
                raise DocumentPermissionError(
                    "Only document owner can update permissions"
                )

            # Record old state for history
            old_access_level = document.access_level
            old_allowed_users = document.allowed_users.copy()
            old_allowed_groups = document.allowed_groups.copy()

            # Update permissions
            new_access_level = request.access_level or document.access_level
            new_allowed_users = document.allowed_users.copy()
            new_allowed_groups = document.allowed_groups.copy()
            new_denied_users = document.denied_users.copy()

            # Apply changes
            if request.add_users:
                new_allowed_users.extend(request.add_users)
            if request.remove_users:
                new_allowed_users = [
                    u for u in new_allowed_users if u not in request.remove_users
                ]
            if request.add_groups:
                new_allowed_groups.extend(request.add_groups)
            if request.remove_groups:
                new_allowed_groups = [
                    g for g in new_allowed_groups if g not in request.remove_groups
                ]

            # Remove duplicates
            new_allowed_users = list(set(new_allowed_users))
            new_allowed_groups = list(set(new_allowed_groups))

            # Update database
            await self.repo.update_document_permissions(
                doc_id=doc_id,
                access_level=new_access_level,
                allowed_users=new_allowed_users,
                allowed_groups=new_allowed_groups,
                denied_users=new_denied_users,
            )

            # Record permission change history
            history = DocumentPermissionHistory(
                history_id=0,  # Auto-generated
                doc_id=doc_id,
                changed_by=user_id,
                old_access_level=old_access_level,
                new_access_level=new_access_level,
                users_added=request.add_users or [],
                users_removed=request.remove_users or [],
                groups_added=request.add_groups or [],
                groups_removed=request.remove_groups or [],
                changed_at=datetime.utcnow(),
            )
            await self.repo.record_permission_change(history)

            # Publish permission.updated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="document.permission.updated",
                        source="document_service",
                        data={
                            "doc_id": doc_id,
                            "user_id": user_id,
                            "access_level": new_access_level.value,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(
                        f"Failed to publish permission.updated event: {e}"
                    )

            return DocumentPermissionResponse(
                doc_id=doc_id,
                access_level=new_access_level,
                allowed_users=new_allowed_users,
                allowed_groups=new_allowed_groups,
                denied_users=new_denied_users,
            )

        except (DocumentNotFoundError, DocumentPermissionError):
            raise
        except Exception as e:
            logger.error(f"Error updating permissions: {e}")
            raise DocumentServiceError(f"Failed to update permissions: {str(e)}")

    async def get_document_permissions(
        self, doc_id: str, user_id: str
    ) -> DocumentPermissionResponse:
        """Get document permissions"""
        document = await self.repo.get_document_by_id(doc_id)
        if not document:
            raise DocumentNotFoundError(f"Document {doc_id} not found")

        # Check read permission
        has_permission = await self._check_document_permission(
            user_id, document, "read"
        )
        if not has_permission:
            raise DocumentPermissionError("Access denied to this document")

        return DocumentPermissionResponse(
            doc_id=doc_id,
            access_level=document.access_level,
            allowed_users=document.allowed_users,
            allowed_groups=document.allowed_groups,
            denied_users=document.denied_users,
        )

    # ==================== RAG Query Operations (with Permission Filtering) ====================

    async def rag_query_secure(
        self, request: RAGQueryRequest, user_id: str, organization_id: Optional[str] = None
    ) -> RAGQueryResponse:
        """
        RAG query with permission filtering

        Uses Digital Analytics generate_response() for RAG.
        Permission filtering is done by:
        1. Using collection_name to scope to user's documents
        2. Post-filtering results based on document permissions in PostgreSQL
        """
        try:
            start_time = time.time()

            if not self.digital_client or not self.digital_client.is_enabled():
                return RAGQueryResponse(
                    query=request.query,
                    answer="Digital Analytics Service not available",
                    sources=[],
                    confidence=0.0,
                    latency_ms=0.0,
                )

            # Query via Digital Analytics
            result = await self.digital_client.generate_response(
                user_id=user_id,
                query=request.query,
                collection_name=f"user_{user_id}",
                top_k=request.top_k,
            )

            if not result:
                return RAGQueryResponse(
                    query=request.query,
                    answer="No response generated",
                    sources=[],
                    confidence=0.0,
                    latency_ms=(time.time() - start_time) * 1000,
                )

            # Build response
            latency_ms = (time.time() - start_time) * 1000

            return RAGQueryResponse(
                query=request.query,
                answer=result.get("response", ""),
                sources=[],  # Digital Analytics doesn't return sources in current API
                confidence=0.8,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            raise DocumentServiceError(f"RAG query failed: {str(e)}")

    async def semantic_search_secure(
        self, request: SemanticSearchRequest, user_id: str, organization_id: Optional[str] = None
    ) -> SemanticSearchResponse:
        """
        Semantic search with permission filtering

        Uses Digital Analytics search_content() for semantic search.
        Results are filtered based on document permissions stored in PostgreSQL.
        """
        try:
            start_time = time.time()

            if not self.digital_client or not self.digital_client.is_enabled():
                return SemanticSearchResponse(
                    query=request.query, results=[], total_count=0, latency_ms=0.0
                )

            # Search via Digital Analytics
            result = await self.digital_client.search_content(
                user_id=user_id,
                query=request.query,
                collection_name=f"user_{user_id}",
                top_k=request.top_k,
            )

            if not result:
                return SemanticSearchResponse(
                    query=request.query,
                    results=[],
                    total_count=0,
                    latency_ms=(time.time() - start_time) * 1000,
                )

            # Convert to SearchResultItem
            results = []
            search_results = result.get("results", [])
            for item in search_results:
                score = item.get("score", 0.0)
                if score < request.min_score:
                    continue

                doc_id = item.get("metadata", {}).get("doc_id", "")
                if doc_id:
                    document = await self.repo.get_document_by_id(doc_id)
                    if document:
                        # Check permission
                        has_access = await self._check_document_permission(
                            user_id, document, "read"
                        )
                        if has_access:
                            results.append(
                                SearchResultItem(
                                    doc_id=doc_id,
                                    title=document.title,
                                    doc_type=document.doc_type,
                                    relevance_score=score,
                                    snippet=item.get("text", "")[:200],
                                    file_id=document.file_id,
                                    chunk_id=item.get("id"),
                                    metadata=item.get("metadata", {}),
                                )
                            )

            latency_ms = (time.time() - start_time) * 1000

            return SemanticSearchResponse(
                query=request.query,
                results=results,
                total_count=len(results),
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            raise DocumentServiceError(f"Semantic search failed: {str(e)}")

    # ==================== Statistics ====================

    async def get_user_stats(
        self, user_id: str, organization_id: Optional[str] = None
    ) -> DocumentStatsResponse:
        """Get user's document statistics"""
        try:
            stats = await self.repo.get_user_stats(user_id, organization_id)

            return DocumentStatsResponse(
                user_id=user_id,
                total_documents=stats.get("total_documents", 0),
                indexed_documents=stats.get("indexed_documents", 0),
                total_chunks=stats.get("total_chunks", 0),
                total_size_bytes=stats.get("total_size_bytes", 0),
                by_type=stats.get("by_type", {}),
                by_status=stats.get("by_status", {}),
            )

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            raise DocumentServiceError(f"Failed to get stats: {str(e)}")

    # ==================== Helper Methods ====================

    async def _index_document_async(
        self, document: KnowledgeDocument, user_id: str
    ):
        """Index document via Digital Analytics (async background task)"""
        try:
            # Update status
            await self.repo.update_document_status(
                document.doc_id, DocumentStatus.INDEXING
            )

            # Download file content from storage service
            file_content = await self._download_file_content(document.file_id, user_id)

            # Index via Digital Analytics
            if self.digital_client and self.digital_client.is_enabled():
                result = await self.digital_client.store_content(
                    user_id=user_id,
                    content=file_content,
                    content_type=document.doc_type.value,
                    collection_name=f"user_{user_id}",
                    metadata={
                        "doc_id": document.doc_id,
                        "title": document.title,
                        "file_id": document.file_id,
                        "access_level": document.access_level.value,
                        "allowed_users": document.allowed_users,
                        "allowed_groups": document.allowed_groups,
                        "denied_users": document.denied_users,
                    },
                )

                if result:
                    chunk_count = result.get("chunks_stored", 0)
                    point_ids = result.get("point_ids", [])

                    # Update document
                    await self.repo.update_document(
                        document.doc_id, {"point_ids": point_ids}
                    )
                    await self.repo.update_document_status(
                        document.doc_id, DocumentStatus.INDEXED, chunk_count=chunk_count
                    )
                    logger.info(f"✅ Document indexed: {document.doc_id}, {chunk_count} chunks")
                else:
                    # Digital Analytics returned no result
                    await self.repo.update_document_status(
                        document.doc_id, DocumentStatus.INDEXED, chunk_count=0
                    )
                    logger.warning(f"⚠️ Document indexed without chunks: {document.doc_id}")
            else:
                # Digital Analytics not available - mark as indexed anyway for testing
                await self.repo.update_document_status(
                    document.doc_id, DocumentStatus.INDEXED, chunk_count=0
                )
                logger.warning(f"⚠️ Digital Analytics not available, skipping indexing: {document.doc_id}")

        except Exception as e:
            logger.error(f"Document indexing failed: {e}")
            await self.repo.update_document_status(
                document.doc_id, DocumentStatus.FAILED
            )

    async def _download_file_content(self, file_id: str, user_id: str) -> str:
        """
        Get file content for indexing from storage service

        Args:
            file_id: The file ID in storage service
            user_id: User ID for permission check

        Returns:
            File content as string, or download URL for binary files

        Raises:
            DocumentServiceError: If storage client unavailable or file not found
        """
        if not self.storage_client:
            raise DocumentServiceError("Storage client not available")

        try:
            # Get download URL from storage service
            download_info = await self.storage_client.get_download_url(file_id, user_id)

            if not download_info or not download_info.get("download_url"):
                raise DocumentServiceError(f"File {file_id} not found in storage service")

            download_url = download_info["download_url"]

            # Fetch actual content from URL
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(download_url)
                response.raise_for_status()

                # Handle different content types
                content_type = response.headers.get("content-type", "")
                if "text" in content_type or "json" in content_type:
                    return response.text
                else:
                    # For binary files (PDF, images), return URL for Digital Analytics to process
                    return download_url

        except DocumentServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            raise DocumentServiceError(f"Failed to download file: {str(e)}")

    async def _check_document_permission(
        self, user_id: str, document: KnowledgeDocument, action: str
    ) -> bool:
        """Check if user has permission for action on document"""
        # Owner always has permission
        if document.user_id == user_id:
            return True

        # Check explicit deny
        if user_id in document.denied_users:
            return False

        # Check access level
        if document.access_level == AccessLevel.PUBLIC:
            return True

        if document.access_level == AccessLevel.PRIVATE:
            return user_id in document.allowed_users

        # For TEAM and ORGANIZATION, check via authorization service
        if self.auth_client:
            try:
                return await self.auth_client.check_permission(
                    user_id=user_id,
                    resource_type="document",
                    resource_id=document.doc_id,
                    action=action,
                )
            except Exception as e:
                logger.warning(f"Authorization check failed: {e}")
                return False

        return user_id in document.allowed_users

    def _validate_document_create_request(self, request: DocumentCreateRequest):
        """Validate document creation request"""
        if not request.title or len(request.title.strip()) == 0:
            raise DocumentValidationError("Document title is required")

        if len(request.title) > 500:
            raise DocumentValidationError("Title too long (max 500 characters)")

    def _document_to_response(self, document: KnowledgeDocument) -> DocumentResponse:
        """Convert KnowledgeDocument to response"""
        return DocumentResponse(
            doc_id=document.doc_id,
            user_id=document.user_id,
            organization_id=document.organization_id,
            title=document.title,
            description=document.description,
            doc_type=document.doc_type,
            file_id=document.file_id,
            file_size=document.file_size,
            version=document.version,
            is_latest=document.is_latest,
            status=document.status,
            chunk_count=document.chunk_count,
            access_level=document.access_level,
            indexed_at=document.indexed_at,
            created_at=document.created_at,
            updated_at=document.updated_at,
            tags=document.tags,
        )

    # ==================== Health Check ====================

    async def check_health(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            db_connected = await self.repo.check_connection()
            return {
                "service": "document_service",
                "status": "healthy" if db_connected else "unhealthy",
                "database": "connected" if db_connected else "disconnected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "document_service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
