"""
Document Service Component Golden Tests

These tests document CURRENT DocumentService behavior with mocked deps.
Uses proper dependency injection - no patching needed!

Usage:
    pytest tests/component/golden/document_service -v
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
import uuid

from .mocks import (
    MockDocumentRepository,
    MockEventBus,
    MockStorageClient,
    MockAuthorizationClient,
    MockDigitalAnalyticsClient,
)

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo():
    """Create a fresh MockDocumentRepository"""
    return MockDocumentRepository()


@pytest.fixture
def mock_repo_with_document():
    """Create MockDocumentRepository with existing document"""
    from microservices.document_service.models import DocumentType, DocumentStatus, AccessLevel

    repo = MockDocumentRepository()
    repo.set_document(
        doc_id="doc_test_123",
        user_id="user_test_123",
        title="Test Document",
        doc_type=DocumentType.PDF,
        status=DocumentStatus.INDEXED,
        access_level=AccessLevel.PRIVATE,
        file_size=2048,
        chunk_count=25,
        tags=["test", "golden"],
    )
    return repo


@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


@pytest.fixture
def mock_storage_client():
    """Create a fresh MockStorageClient"""
    client = MockStorageClient()
    client.set_file("file_test_123", file_size=2048)
    return client


@pytest.fixture
def mock_auth_client():
    """Create a fresh MockAuthorizationClient"""
    return MockAuthorizationClient()


@pytest.fixture
def mock_digital_client():
    """Create a fresh MockDigitalAnalyticsClient"""
    return MockDigitalAnalyticsClient()


@pytest.fixture
def document_service(
    mock_repo,
    mock_event_bus,
    mock_storage_client,
    mock_auth_client,
    mock_digital_client,
):
    """Create DocumentService with all mocked dependencies"""
    from microservices.document_service.document_service import DocumentService

    service = DocumentService(
        repository=mock_repo,
        event_bus=mock_event_bus,
        storage_client=mock_storage_client,
        auth_client=mock_auth_client,
        digital_client=mock_digital_client,
    )
    return service


# =============================================================================
# DocumentService.create_document() Tests
# =============================================================================

class TestDocumentServiceCreateGolden:
    """Golden: DocumentService.create_document() current behavior"""

    async def test_create_document_returns_response(
        self, mock_repo, mock_event_bus, mock_storage_client, mock_digital_client
    ):
        """GOLDEN: create_document creates document and returns DocumentResponse"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import (
            DocumentCreateRequest,
            DocumentResponse,
            DocumentType,
            AccessLevel,
        )

        mock_storage_client.set_file("file_new_123", file_size=4096)

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            storage_client=mock_storage_client,
            digital_client=mock_digital_client,
        )

        request = DocumentCreateRequest(
            title="New Document",
            description="Test description",
            doc_type=DocumentType.PDF,
            file_id="file_new_123",
            access_level=AccessLevel.PRIVATE,
            tags=["new", "test"],
        )

        result = await service.create_document(request, user_id="user_new_123")

        assert isinstance(result, DocumentResponse)
        assert result.title == "New Document"
        assert result.user_id == "user_new_123"
        assert result.file_id == "file_new_123"
        assert result.tags == ["new", "test"]

        # Verify repository was called
        mock_repo.assert_called("create_document")

    async def test_create_document_publishes_event(
        self, mock_repo, mock_event_bus, mock_storage_client, mock_digital_client
    ):
        """GOLDEN: create_document publishes DOCUMENT_CREATED event"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import (
            DocumentCreateRequest,
            DocumentType,
        )

        mock_storage_client.set_file("file_event_123", file_size=1024)

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            storage_client=mock_storage_client,
            digital_client=mock_digital_client,
        )

        request = DocumentCreateRequest(
            title="Event Test",
            doc_type=DocumentType.PDF,
            file_id="file_event_123",
        )

        await service.create_document(request, user_id="user_event_123")

        # Verify event was published (event type value is "document.created")
        mock_event_bus.assert_published("document.created")

    async def test_create_document_validates_empty_title(self, mock_repo):
        """GOLDEN: Pydantic model rejects empty title during request creation"""
        from pydantic import ValidationError
        from microservices.document_service.models import (
            DocumentCreateRequest,
            DocumentType,
        )

        # Pydantic validation happens at model creation time
        with pytest.raises(ValidationError) as exc_info:
            DocumentCreateRequest(
                title="",  # Empty title
                doc_type=DocumentType.PDF,
                file_id="file_123",
            )

        assert "title" in str(exc_info.value).lower()

    async def test_create_document_validates_title_too_long(self, mock_repo):
        """GOLDEN: Pydantic model rejects title > 500 chars during request creation"""
        from pydantic import ValidationError
        from microservices.document_service.models import (
            DocumentCreateRequest,
            DocumentType,
        )

        # Pydantic validation happens at model creation time
        with pytest.raises(ValidationError) as exc_info:
            DocumentCreateRequest(
                title="A" * 501,  # 501 characters
                doc_type=DocumentType.PDF,
                file_id="file_123",
            )

        assert "title" in str(exc_info.value).lower()


# =============================================================================
# DocumentService.get_document() Tests
# =============================================================================

class TestDocumentServiceGetGolden:
    """Golden: DocumentService.get_document() current behavior"""

    async def test_get_document_returns_document(self, mock_repo_with_document, mock_event_bus):
        """GOLDEN: get_document returns DocumentResponse for owner"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import DocumentResponse

        service = DocumentService(
            repository=mock_repo_with_document,
            event_bus=mock_event_bus,
        )

        result = await service.get_document("doc_test_123", "user_test_123")

        assert isinstance(result, DocumentResponse)
        assert result.doc_id == "doc_test_123"
        assert result.title == "Test Document"
        assert result.user_id == "user_test_123"

    async def test_get_document_raises_not_found(self, mock_repo, mock_event_bus):
        """GOLDEN: get_document raises DocumentNotFoundError when not found"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.protocols import DocumentNotFoundError

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        with pytest.raises(DocumentNotFoundError):
            await service.get_document("doc_nonexistent", "user_123")

    async def test_get_document_denies_private_access(self, mock_repo_with_document, mock_event_bus):
        """GOLDEN: get_document raises DocumentPermissionError for unauthorized user"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.protocols import DocumentPermissionError

        service = DocumentService(
            repository=mock_repo_with_document,
            event_bus=mock_event_bus,
        )

        # Different user tries to access private document
        with pytest.raises(DocumentPermissionError):
            await service.get_document("doc_test_123", "other_user")


# =============================================================================
# DocumentService.list_user_documents() Tests
# =============================================================================

class TestDocumentServiceListGolden:
    """Golden: DocumentService.list_user_documents() current behavior"""

    async def test_list_returns_user_documents(self, mock_repo, mock_event_bus):
        """GOLDEN: list_user_documents returns list of DocumentResponse"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import DocumentType

        # Add documents
        for i in range(3):
            mock_repo.set_document(
                doc_id=f"doc_list_{i}",
                user_id="user_list_123",
                title=f"Document {i}",
                doc_type=DocumentType.PDF,
            )

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.list_user_documents("user_list_123", limit=10)

        assert len(result) == 3
        assert all(doc.user_id == "user_list_123" for doc in result)

    async def test_list_filters_by_status(self, mock_repo, mock_event_bus):
        """GOLDEN: list_user_documents filters by status"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import DocumentType, DocumentStatus

        mock_repo.set_document(
            doc_id="doc_indexed",
            user_id="user_filter",
            title="Indexed Doc",
            status=DocumentStatus.INDEXED,
        )
        mock_repo.set_document(
            doc_id="doc_draft",
            user_id="user_filter",
            title="Draft Doc",
            status=DocumentStatus.DRAFT,
        )

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.list_user_documents(
            "user_filter",
            status=DocumentStatus.INDEXED,
        )

        assert len(result) == 1
        assert result[0].status == DocumentStatus.INDEXED

    async def test_list_empty_returns_empty(self, mock_repo, mock_event_bus):
        """GOLDEN: list_user_documents returns empty list when no documents"""
        from microservices.document_service.document_service import DocumentService

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.list_user_documents("user_no_docs")

        assert result == []


# =============================================================================
# DocumentService.delete_document() Tests
# =============================================================================

class TestDocumentServiceDeleteGolden:
    """Golden: DocumentService.delete_document() current behavior"""

    async def test_delete_document_soft_delete(self, mock_repo_with_document, mock_event_bus):
        """GOLDEN: delete_document performs soft delete by default"""
        from microservices.document_service.document_service import DocumentService

        service = DocumentService(
            repository=mock_repo_with_document,
            event_bus=mock_event_bus,
        )

        result = await service.delete_document("doc_test_123", "user_test_123", permanent=False)

        assert result is True
        mock_repo_with_document.assert_called("delete_document")
        mock_repo_with_document.assert_called_with("delete_document", soft=True)

    async def test_delete_document_publishes_event(self, mock_repo_with_document, mock_event_bus):
        """GOLDEN: delete_document publishes DOCUMENT_DELETED event"""
        from microservices.document_service.document_service import DocumentService

        service = DocumentService(
            repository=mock_repo_with_document,
            event_bus=mock_event_bus,
        )

        await service.delete_document("doc_test_123", "user_test_123")

        # Verify event was published (event type value is "document.deleted")
        mock_event_bus.assert_published("document.deleted")

    async def test_delete_raises_not_found(self, mock_repo, mock_event_bus):
        """GOLDEN: delete_document raises DocumentNotFoundError for nonexistent doc"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.protocols import DocumentNotFoundError

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        with pytest.raises(DocumentNotFoundError):
            await service.delete_document("doc_nonexistent", "user_123")

    async def test_delete_denies_unauthorized(self, mock_repo_with_document, mock_event_bus):
        """GOLDEN: delete_document raises DocumentPermissionError for unauthorized user"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.protocols import DocumentPermissionError

        service = DocumentService(
            repository=mock_repo_with_document,
            event_bus=mock_event_bus,
        )

        with pytest.raises(DocumentPermissionError):
            await service.delete_document("doc_test_123", "other_user")


# =============================================================================
# DocumentService Permission Checks
# =============================================================================

class TestDocumentServicePermissionsGolden:
    """Golden: DocumentService._check_document_permission() current behavior"""

    async def test_owner_has_permission(self, mock_repo, mock_event_bus):
        """GOLDEN: Owner always has permission"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import KnowledgeDocument, DocumentType, AccessLevel

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        document = KnowledgeDocument(
            doc_id="doc_perm_1",
            user_id="owner_user",
            title="Test",
            doc_type=DocumentType.PDF,
            file_id="file_1",
            access_level=AccessLevel.PRIVATE,
        )

        result = await service._check_document_permission("owner_user", document, "read")

        assert result is True

    async def test_public_allows_anyone(self, mock_repo, mock_event_bus):
        """GOLDEN: Public access allows any user"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import KnowledgeDocument, DocumentType, AccessLevel

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        document = KnowledgeDocument(
            doc_id="doc_public",
            user_id="owner_user",
            title="Public Doc",
            doc_type=DocumentType.PDF,
            file_id="file_1",
            access_level=AccessLevel.PUBLIC,
        )

        result = await service._check_document_permission("any_user", document, "read")

        assert result is True

    async def test_denied_user_blocked(self, mock_repo, mock_event_bus):
        """GOLDEN: Explicitly denied users are blocked"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import KnowledgeDocument, DocumentType, AccessLevel

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        document = KnowledgeDocument(
            doc_id="doc_deny",
            user_id="owner_user",
            title="Deny Test",
            doc_type=DocumentType.PDF,
            file_id="file_1",
            access_level=AccessLevel.PUBLIC,
            denied_users=["blocked_user"],
        )

        result = await service._check_document_permission("blocked_user", document, "read")

        assert result is False

    async def test_private_allows_listed_users(self, mock_repo, mock_event_bus):
        """GOLDEN: Private allows users in allowed_users list"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import KnowledgeDocument, DocumentType, AccessLevel

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        document = KnowledgeDocument(
            doc_id="doc_private",
            user_id="owner_user",
            title="Private Doc",
            doc_type=DocumentType.PDF,
            file_id="file_1",
            access_level=AccessLevel.PRIVATE,
            allowed_users=["allowed_user"],
        )

        # Allowed user has access
        result = await service._check_document_permission("allowed_user", document, "read")
        assert result is True

        # Non-allowed user denied
        result = await service._check_document_permission("other_user", document, "read")
        assert result is False


# =============================================================================
# DocumentService.update_document_permissions() Tests
# =============================================================================

class TestDocumentServicePermissionUpdateGolden:
    """Golden: DocumentService.update_document_permissions() current behavior"""

    async def test_update_permissions_adds_users(self, mock_repo_with_document, mock_event_bus):
        """GOLDEN: update_document_permissions adds users to allowed list"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import (
            DocumentPermissionUpdateRequest,
            DocumentPermissionResponse,
            AccessLevel,
        )

        service = DocumentService(
            repository=mock_repo_with_document,
            event_bus=mock_event_bus,
        )

        request = DocumentPermissionUpdateRequest(
            access_level=AccessLevel.TEAM,
            add_users=["user_new_1", "user_new_2"],
        )

        result = await service.update_document_permissions(
            "doc_test_123", request, "user_test_123"
        )

        assert isinstance(result, DocumentPermissionResponse)
        assert result.access_level == AccessLevel.TEAM
        assert "user_new_1" in result.allowed_users
        assert "user_new_2" in result.allowed_users

        mock_repo_with_document.assert_called("update_document_permissions")
        mock_repo_with_document.assert_called("record_permission_change")

    async def test_update_permissions_removes_users(self, mock_repo, mock_event_bus):
        """GOLDEN: update_document_permissions removes users from allowed list"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import (
            DocumentPermissionUpdateRequest,
            AccessLevel,
            DocumentType,
        )

        mock_repo.set_document(
            doc_id="doc_remove",
            user_id="owner_user",
            title="Remove Test",
            doc_type=DocumentType.PDF,
            access_level=AccessLevel.TEAM,
            allowed_users=["user_a", "user_b", "user_c"],
        )

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        request = DocumentPermissionUpdateRequest(
            remove_users=["user_b"],
        )

        result = await service.update_document_permissions(
            "doc_remove", request, "owner_user"
        )

        assert "user_b" not in result.allowed_users
        assert "user_a" in result.allowed_users
        assert "user_c" in result.allowed_users


# =============================================================================
# DocumentService.rag_query_secure() Tests
# =============================================================================

class TestDocumentServiceRAGGolden:
    """Golden: DocumentService.rag_query_secure() current behavior"""

    async def test_rag_query_returns_response(
        self, mock_repo, mock_event_bus, mock_digital_client
    ):
        """GOLDEN: rag_query_secure returns RAGQueryResponse"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import RAGQueryRequest, RAGQueryResponse

        mock_digital_client.set_rag_result("test query", {
            "response": "Test answer from RAG",
            "confidence": 0.9,
        })

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            digital_client=mock_digital_client,
        )

        request = RAGQueryRequest(query="test query", top_k=5)

        result = await service.rag_query_secure(request, "user_123")

        assert isinstance(result, RAGQueryResponse)
        assert result.query == "test query"
        assert result.answer == "Test answer from RAG"
        assert result.latency_ms >= 0

    async def test_rag_query_unavailable(self, mock_repo, mock_event_bus, mock_digital_client):
        """GOLDEN: rag_query_secure handles unavailable Digital Analytics"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import RAGQueryRequest

        mock_digital_client.set_enabled(False)

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            digital_client=mock_digital_client,
        )

        request = RAGQueryRequest(query="test", top_k=5)

        result = await service.rag_query_secure(request, "user_123")

        assert "not available" in result.answer.lower()
        assert result.confidence == 0.0


# =============================================================================
# DocumentService.semantic_search_secure() Tests
# =============================================================================

class TestDocumentServiceSearchGolden:
    """Golden: DocumentService.semantic_search_secure() current behavior"""

    async def test_semantic_search_returns_results(
        self, mock_repo, mock_event_bus, mock_digital_client
    ):
        """GOLDEN: semantic_search_secure returns SemanticSearchResponse"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import (
            SemanticSearchRequest,
            SemanticSearchResponse,
            DocumentType,
            AccessLevel,
        )

        # Add test document
        mock_repo.set_document(
            doc_id="doc_search_1",
            user_id="user_search",
            title="Machine Learning Guide",
            doc_type=DocumentType.PDF,
            access_level=AccessLevel.PRIVATE,
        )

        mock_digital_client.set_search_result("machine learning", {
            "results": [
                {
                    "id": "chunk_1",
                    "text": "Machine learning is a branch of AI...",
                    "score": 0.92,
                    "metadata": {"doc_id": "doc_search_1"},
                }
            ]
        })

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            digital_client=mock_digital_client,
        )

        request = SemanticSearchRequest(query="machine learning", top_k=10)

        result = await service.semantic_search_secure(request, "user_search")

        assert isinstance(result, SemanticSearchResponse)
        assert result.query == "machine learning"
        assert len(result.results) == 1
        assert result.results[0].doc_id == "doc_search_1"

    async def test_semantic_search_filters_min_score(
        self, mock_repo, mock_event_bus, mock_digital_client
    ):
        """GOLDEN: semantic_search_secure filters results below min_score"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import (
            SemanticSearchRequest,
            DocumentType,
            AccessLevel,
        )

        mock_repo.set_document(
            doc_id="doc_filter",
            user_id="user_filter",
            title="Filter Test",
            doc_type=DocumentType.PDF,
            access_level=AccessLevel.PRIVATE,
        )

        mock_digital_client.set_search_result("filter test", {
            "results": [
                {"id": "chunk_1", "text": "Low score", "score": 0.3, "metadata": {"doc_id": "doc_filter"}},
            ]
        })

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            digital_client=mock_digital_client,
        )

        request = SemanticSearchRequest(query="filter test", top_k=10, min_score=0.5)

        result = await service.semantic_search_secure(request, "user_filter")

        # Low score result should be filtered out
        assert len(result.results) == 0


# =============================================================================
# DocumentService.get_user_stats() Tests
# =============================================================================

class TestDocumentServiceStatsGolden:
    """Golden: DocumentService.get_user_stats() current behavior"""

    async def test_get_stats_returns_response(self, mock_repo, mock_event_bus):
        """GOLDEN: get_user_stats returns DocumentStatsResponse"""
        from microservices.document_service.document_service import DocumentService
        from microservices.document_service.models import DocumentStatsResponse

        mock_repo.set_stats(
            total_documents=50,
            indexed_documents=45,
            total_chunks=1250,
            total_size_bytes=52428800,
            by_type={"pdf": 30, "docx": 15, "txt": 5},
            by_status={"indexed": 45, "draft": 3, "failed": 2},
        )

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.get_user_stats("user_stats")

        assert isinstance(result, DocumentStatsResponse)
        assert result.user_id == "user_stats"
        assert result.total_documents == 50
        assert result.indexed_documents == 45
        assert result.by_type["pdf"] == 30


# =============================================================================
# DocumentService.check_health() Tests
# =============================================================================

class TestDocumentServiceHealthGolden:
    """Golden: DocumentService.check_health() current behavior"""

    async def test_health_check_healthy(self, mock_repo, mock_event_bus):
        """GOLDEN: check_health returns healthy when DB connected"""
        from microservices.document_service.document_service import DocumentService

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.check_health()

        assert result["status"] == "healthy"
        assert result["database"] == "connected"
        assert result["service"] == "document_service"

    async def test_health_check_unhealthy(self, mock_repo, mock_event_bus):
        """GOLDEN: check_health returns unhealthy on DB error"""
        from microservices.document_service.document_service import DocumentService

        mock_repo.set_error(Exception("Database connection failed"))

        service = DocumentService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await service.check_health()

        assert result["status"] == "unhealthy"
        assert result["database"] == "disconnected"
