"""
Unit Golden Tests: Document Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.document_service.models import (
    DocumentType,
    DocumentStatus,
    AccessLevel,
    ChunkingStrategy,
    UpdateStrategy,
    KnowledgeDocument,
    DocumentPermissionHistory,
    DocumentCreateRequest,
    DocumentUpdateRequest,
    DocumentPermissionUpdateRequest,
    RAGQueryRequest,
    SemanticSearchRequest,
    DocumentResponse,
    DocumentVersionResponse,
    SearchResultItem,
    RAGQueryResponse,
    SemanticSearchResponse,
    DocumentPermissionResponse,
    DocumentStatsResponse,
)


class TestDocumentType:
    """Test DocumentType enum"""

    def test_document_type_values(self):
        """Test all document type values are defined"""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.DOCX.value == "docx"
        assert DocumentType.PPTX.value == "pptx"
        assert DocumentType.XLSX.value == "xlsx"
        assert DocumentType.TXT.value == "txt"
        assert DocumentType.MARKDOWN.value == "markdown"
        assert DocumentType.HTML.value == "html"
        assert DocumentType.JSON.value == "json"

    def test_document_type_comparison(self):
        """Test document type comparison"""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.PDF != DocumentType.DOCX
        assert DocumentType.MARKDOWN.value == "markdown"


class TestDocumentStatus:
    """Test DocumentStatus enum"""

    def test_document_status_values(self):
        """Test all document status values"""
        assert DocumentStatus.DRAFT.value == "draft"
        assert DocumentStatus.INDEXING.value == "indexing"
        assert DocumentStatus.INDEXED.value == "indexed"
        assert DocumentStatus.UPDATE_PENDING.value == "update_pending"
        assert DocumentStatus.UPDATING.value == "updating"
        assert DocumentStatus.ARCHIVED.value == "archived"
        assert DocumentStatus.FAILED.value == "failed"
        assert DocumentStatus.DELETED.value == "deleted"

    def test_document_status_comparison(self):
        """Test document status comparison"""
        assert DocumentStatus.DRAFT != DocumentStatus.INDEXED
        assert DocumentStatus.INDEXING.value == "indexing"


class TestAccessLevel:
    """Test AccessLevel enum"""

    def test_access_level_values(self):
        """Test all access level values"""
        assert AccessLevel.PRIVATE.value == "private"
        assert AccessLevel.TEAM.value == "team"
        assert AccessLevel.ORGANIZATION.value == "organization"
        assert AccessLevel.PUBLIC.value == "public"

    def test_access_level_hierarchy(self):
        """Test access level hierarchy understanding"""
        # Just verify the enum values exist and are different
        levels = [AccessLevel.PRIVATE, AccessLevel.TEAM, AccessLevel.ORGANIZATION, AccessLevel.PUBLIC]
        assert len(set(levels)) == 4


class TestChunkingStrategy:
    """Test ChunkingStrategy enum"""

    def test_chunking_strategy_values(self):
        """Test all chunking strategy values"""
        assert ChunkingStrategy.FIXED_SIZE.value == "fixed_size"
        assert ChunkingStrategy.SEMANTIC.value == "semantic"
        assert ChunkingStrategy.PARAGRAPH.value == "paragraph"
        assert ChunkingStrategy.RECURSIVE.value == "recursive"


class TestUpdateStrategy:
    """Test UpdateStrategy enum"""

    def test_update_strategy_values(self):
        """Test all update strategy values"""
        assert UpdateStrategy.FULL.value == "full"
        assert UpdateStrategy.SMART.value == "smart"
        assert UpdateStrategy.DIFF.value == "diff"


class TestKnowledgeDocument:
    """Test KnowledgeDocument model validation"""

    def test_knowledge_document_creation_with_all_fields(self):
        """Test creating knowledge document with all fields"""
        now = datetime.now(timezone.utc)

        doc = KnowledgeDocument(
            doc_id="doc_123",
            user_id="user_456",
            organization_id="org_789",
            title="System Architecture Document",
            description="Comprehensive architecture documentation",
            doc_type=DocumentType.PDF,
            file_id="file_abc123",
            file_size=1024000,
            file_url="https://storage.example.com/file_abc123",
            version=2,
            parent_version_id="doc_122",
            is_latest=True,
            status=DocumentStatus.INDEXED,
            chunk_count=50,
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            indexed_at=now,
            last_updated_at=now,
            access_level=AccessLevel.TEAM,
            allowed_users=["user_001", "user_002"],
            allowed_groups=["group_eng", "group_pm"],
            denied_users=["user_999"],
            collection_name="engineering_docs",
            point_ids=["point_1", "point_2", "point_3"],
            metadata={"project": "Platform", "category": "Architecture"},
            tags=["architecture", "system-design", "important"],
            created_at=now,
            updated_at=now,
        )

        assert doc.doc_id == "doc_123"
        assert doc.user_id == "user_456"
        assert doc.organization_id == "org_789"
        assert doc.title == "System Architecture Document"
        assert doc.doc_type == DocumentType.PDF
        assert doc.file_size == 1024000
        assert doc.version == 2
        assert doc.is_latest is True
        assert doc.status == DocumentStatus.INDEXED
        assert doc.chunk_count == 50
        assert doc.chunking_strategy == ChunkingStrategy.SEMANTIC
        assert doc.access_level == AccessLevel.TEAM
        assert len(doc.allowed_users) == 2
        assert len(doc.allowed_groups) == 2
        assert len(doc.denied_users) == 1
        assert len(doc.point_ids) == 3
        assert len(doc.tags) == 3

    def test_knowledge_document_with_minimal_fields(self):
        """Test creating knowledge document with only required fields"""
        doc = KnowledgeDocument(
            doc_id="doc_minimal",
            user_id="user_123",
            title="Quick Note",
            doc_type=DocumentType.TXT,
            file_id="file_xyz",
        )

        assert doc.doc_id == "doc_minimal"
        assert doc.organization_id is None
        assert doc.description is None
        assert doc.file_size == 0
        assert doc.version == 1
        assert doc.is_latest is True
        assert doc.status == DocumentStatus.DRAFT
        assert doc.chunk_count == 0
        assert doc.chunking_strategy == ChunkingStrategy.SEMANTIC
        assert doc.access_level == AccessLevel.PRIVATE
        assert doc.allowed_users == []
        assert doc.allowed_groups == []
        assert doc.denied_users == []
        assert doc.collection_name == "default"
        assert doc.point_ids == []
        assert doc.metadata == {}
        assert doc.tags == []

    def test_knowledge_document_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeDocument(
                doc_id="doc_123",
                user_id="user_123",
            )

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "title" in missing_fields
        assert "doc_type" in missing_fields
        assert "file_id" in missing_fields

    def test_knowledge_document_json_metadata_parsing(self):
        """Test metadata JSON string parsing"""
        doc = KnowledgeDocument(
            doc_id="doc_json",
            user_id="user_123",
            title="Test",
            doc_type=DocumentType.TXT,
            file_id="file_123",
            metadata='{"key": "value", "number": 42}',
        )

        assert isinstance(doc.metadata, dict)
        assert doc.metadata["key"] == "value"
        assert doc.metadata["number"] == 42

    def test_knowledge_document_json_array_parsing(self):
        """Test JSON array string parsing for list fields"""
        doc = KnowledgeDocument(
            doc_id="doc_arrays",
            user_id="user_123",
            title="Test",
            doc_type=DocumentType.TXT,
            file_id="file_123",
            allowed_users='["user_1", "user_2"]',
            tags='["tag1", "tag2", "tag3"]',
        )

        assert isinstance(doc.allowed_users, list)
        assert len(doc.allowed_users) == 2
        assert doc.allowed_users == ["user_1", "user_2"]
        assert len(doc.tags) == 3

    def test_knowledge_document_invalid_json_handling(self):
        """Test that invalid JSON strings are handled gracefully"""
        doc = KnowledgeDocument(
            doc_id="doc_invalid",
            user_id="user_123",
            title="Test",
            doc_type=DocumentType.TXT,
            file_id="file_123",
            metadata='{invalid json}',
            tags='[invalid]',
        )

        # Should default to empty dict/list on parse error
        assert doc.metadata == {}
        assert doc.tags == []


class TestDocumentPermissionHistory:
    """Test DocumentPermissionHistory model validation"""

    def test_permission_history_creation_full(self):
        """Test creating permission history with all fields"""
        now = datetime.now(timezone.utc)

        history = DocumentPermissionHistory(
            history_id=1,
            doc_id="doc_123",
            changed_by="user_admin",
            old_access_level=AccessLevel.PRIVATE,
            new_access_level=AccessLevel.TEAM,
            users_added=["user_001", "user_002"],
            users_removed=["user_999"],
            groups_added=["group_eng"],
            groups_removed=["group_sales"],
            changed_at=now,
        )

        assert history.history_id == 1
        assert history.doc_id == "doc_123"
        assert history.changed_by == "user_admin"
        assert history.old_access_level == AccessLevel.PRIVATE
        assert history.new_access_level == AccessLevel.TEAM
        assert len(history.users_added) == 2
        assert len(history.users_removed) == 1
        assert len(history.groups_added) == 1
        assert len(history.groups_removed) == 1

    def test_permission_history_minimal_fields(self):
        """Test creating permission history with minimal fields"""
        now = datetime.now(timezone.utc)

        history = DocumentPermissionHistory(
            history_id=2,
            doc_id="doc_456",
            changed_by="user_123",
            changed_at=now,
        )

        assert history.history_id == 2
        assert history.old_access_level is None
        assert history.new_access_level is None
        assert history.users_added == []
        assert history.users_removed == []
        assert history.groups_added == []
        assert history.groups_removed == []

    def test_permission_history_json_array_parsing(self):
        """Test JSON array string parsing in permission history"""
        now = datetime.now(timezone.utc)

        history = DocumentPermissionHistory(
            history_id=3,
            doc_id="doc_789",
            changed_by="user_admin",
            users_added='["user_1", "user_2"]',
            groups_removed='["group_old"]',
            changed_at=now,
        )

        assert isinstance(history.users_added, list)
        assert len(history.users_added) == 2
        assert isinstance(history.groups_removed, list)
        assert len(history.groups_removed) == 1


class TestDocumentCreateRequest:
    """Test DocumentCreateRequest model validation"""

    def test_document_create_request_valid(self):
        """Test valid document creation request"""
        request = DocumentCreateRequest(
            title="New Document",
            description="A comprehensive document",
            doc_type=DocumentType.PDF,
            file_id="file_new123",
            access_level=AccessLevel.TEAM,
            allowed_users=["user_001"],
            allowed_groups=["group_eng"],
            tags=["important", "review"],
            chunking_strategy=ChunkingStrategy.PARAGRAPH,
            metadata={"project": "Alpha", "priority": "high"},
        )

        assert request.title == "New Document"
        assert request.description == "A comprehensive document"
        assert request.doc_type == DocumentType.PDF
        assert request.file_id == "file_new123"
        assert request.access_level == AccessLevel.TEAM
        assert len(request.allowed_users) == 1
        assert len(request.tags) == 2
        assert request.chunking_strategy == ChunkingStrategy.PARAGRAPH

    def test_document_create_request_defaults(self):
        """Test default values for optional fields"""
        request = DocumentCreateRequest(
            title="Basic Document",
            doc_type=DocumentType.TXT,
            file_id="file_basic",
        )

        assert request.description is None
        assert request.access_level == AccessLevel.PRIVATE
        assert request.allowed_users == []
        assert request.allowed_groups == []
        assert request.tags == []
        assert request.chunking_strategy == ChunkingStrategy.SEMANTIC
        assert request.metadata == {}

    def test_document_create_request_title_validation(self):
        """Test title validation (min/max length)"""
        # Test minimum length
        with pytest.raises(ValidationError):
            DocumentCreateRequest(
                title="",
                doc_type=DocumentType.TXT,
                file_id="file_123",
            )

        # Test maximum length
        with pytest.raises(ValidationError):
            DocumentCreateRequest(
                title="x" * 501,
                doc_type=DocumentType.TXT,
                file_id="file_123",
            )

    def test_document_create_request_description_max_length(self):
        """Test description max length validation"""
        with pytest.raises(ValidationError):
            DocumentCreateRequest(
                title="Test",
                description="x" * 2001,
                doc_type=DocumentType.TXT,
                file_id="file_123",
            )


class TestDocumentUpdateRequest:
    """Test DocumentUpdateRequest model validation"""

    def test_document_update_request_valid(self):
        """Test valid document update request"""
        request = DocumentUpdateRequest(
            new_file_id="file_updated123",
            update_strategy=UpdateStrategy.SMART,
            title="Updated Title",
            description="Updated description",
            tags=["updated", "reviewed"],
        )

        assert request.new_file_id == "file_updated123"
        assert request.update_strategy == UpdateStrategy.SMART
        assert request.title == "Updated Title"
        assert request.description == "Updated description"
        assert len(request.tags) == 2

    def test_document_update_request_minimal(self):
        """Test minimal update request"""
        request = DocumentUpdateRequest(
            new_file_id="file_new456",
        )

        assert request.new_file_id == "file_new456"
        assert request.update_strategy == UpdateStrategy.SMART
        assert request.title is None
        assert request.description is None
        assert request.tags is None

    def test_document_update_request_strategy_options(self):
        """Test different update strategies"""
        request_full = DocumentUpdateRequest(
            new_file_id="file_123",
            update_strategy=UpdateStrategy.FULL,
        )
        assert request_full.update_strategy == UpdateStrategy.FULL

        request_diff = DocumentUpdateRequest(
            new_file_id="file_456",
            update_strategy=UpdateStrategy.DIFF,
        )
        assert request_diff.update_strategy == UpdateStrategy.DIFF


class TestDocumentPermissionUpdateRequest:
    """Test DocumentPermissionUpdateRequest model validation"""

    def test_permission_update_request_access_level(self):
        """Test updating access level"""
        request = DocumentPermissionUpdateRequest(
            access_level=AccessLevel.ORGANIZATION,
        )

        assert request.access_level == AccessLevel.ORGANIZATION
        assert request.add_users == []
        assert request.remove_users == []

    def test_permission_update_request_users(self):
        """Test adding and removing users"""
        request = DocumentPermissionUpdateRequest(
            add_users=["user_001", "user_002"],
            remove_users=["user_999"],
        )

        assert len(request.add_users) == 2
        assert len(request.remove_users) == 1
        assert request.access_level is None

    def test_permission_update_request_groups(self):
        """Test adding and removing groups"""
        request = DocumentPermissionUpdateRequest(
            add_groups=["group_eng", "group_design"],
            remove_groups=["group_old"],
        )

        assert len(request.add_groups) == 2
        assert len(request.remove_groups) == 1

    def test_permission_update_request_full(self):
        """Test full permission update"""
        request = DocumentPermissionUpdateRequest(
            access_level=AccessLevel.TEAM,
            add_users=["user_001"],
            remove_users=["user_999"],
            add_groups=["group_new"],
            remove_groups=["group_old"],
        )

        assert request.access_level == AccessLevel.TEAM
        assert len(request.add_users) == 1
        assert len(request.remove_users) == 1
        assert len(request.add_groups) == 1
        assert len(request.remove_groups) == 1


class TestRAGQueryRequest:
    """Test RAGQueryRequest model validation"""

    def test_rag_query_request_valid(self):
        """Test valid RAG query request"""
        request = RAGQueryRequest(
            query="What is the system architecture?",
            top_k=10,
            doc_types=[DocumentType.PDF, DocumentType.MARKDOWN],
            tags=["architecture", "design"],
            temperature=0.5,
            max_tokens=1000,
        )

        assert request.query == "What is the system architecture?"
        assert request.top_k == 10
        assert len(request.doc_types) == 2
        assert len(request.tags) == 2
        assert request.temperature == 0.5
        assert request.max_tokens == 1000

    def test_rag_query_request_defaults(self):
        """Test default values"""
        request = RAGQueryRequest(
            query="Test query",
        )

        assert request.query == "Test query"
        assert request.top_k == 5
        assert request.doc_types == []
        assert request.tags == []
        assert request.temperature == 0.7
        assert request.max_tokens == 500

    def test_rag_query_request_query_validation(self):
        """Test query minimum length validation"""
        with pytest.raises(ValidationError):
            RAGQueryRequest(query="")

    def test_rag_query_request_top_k_validation(self):
        """Test top_k range validation"""
        # Test minimum
        with pytest.raises(ValidationError):
            RAGQueryRequest(query="test", top_k=0)

        # Test maximum
        with pytest.raises(ValidationError):
            RAGQueryRequest(query="test", top_k=51)

    def test_rag_query_request_temperature_validation(self):
        """Test temperature range validation"""
        # Test minimum
        with pytest.raises(ValidationError):
            RAGQueryRequest(query="test", temperature=-0.1)

        # Test maximum
        with pytest.raises(ValidationError):
            RAGQueryRequest(query="test", temperature=2.1)

    def test_rag_query_request_max_tokens_validation(self):
        """Test max_tokens range validation"""
        # Test minimum
        with pytest.raises(ValidationError):
            RAGQueryRequest(query="test", max_tokens=49)

        # Test maximum
        with pytest.raises(ValidationError):
            RAGQueryRequest(query="test", max_tokens=4001)


class TestSemanticSearchRequest:
    """Test SemanticSearchRequest model validation"""

    def test_semantic_search_request_valid(self):
        """Test valid semantic search request"""
        request = SemanticSearchRequest(
            query="machine learning algorithms",
            top_k=20,
            doc_types=[DocumentType.PDF],
            tags=["ml", "ai"],
            min_score=0.7,
        )

        assert request.query == "machine learning algorithms"
        assert request.top_k == 20
        assert len(request.doc_types) == 1
        assert len(request.tags) == 2
        assert request.min_score == 0.7

    def test_semantic_search_request_defaults(self):
        """Test default values"""
        request = SemanticSearchRequest(
            query="test search",
        )

        assert request.query == "test search"
        assert request.top_k == 10
        assert request.doc_types == []
        assert request.tags == []
        assert request.min_score == 0.0

    def test_semantic_search_request_top_k_validation(self):
        """Test top_k range validation"""
        # Test minimum
        with pytest.raises(ValidationError):
            SemanticSearchRequest(query="test", top_k=0)

        # Test maximum
        with pytest.raises(ValidationError):
            SemanticSearchRequest(query="test", top_k=101)

    def test_semantic_search_request_min_score_validation(self):
        """Test min_score range validation"""
        # Test minimum
        with pytest.raises(ValidationError):
            SemanticSearchRequest(query="test", min_score=-0.1)

        # Test maximum
        with pytest.raises(ValidationError):
            SemanticSearchRequest(query="test", min_score=1.1)


class TestDocumentResponse:
    """Test DocumentResponse model"""

    def test_document_response_creation(self):
        """Test creating document response"""
        now = datetime.now(timezone.utc)

        response = DocumentResponse(
            doc_id="doc_123",
            user_id="user_456",
            organization_id="org_789",
            title="Test Document",
            description="Test description",
            doc_type=DocumentType.PDF,
            file_id="file_abc",
            file_size=2048000,
            version=1,
            is_latest=True,
            status=DocumentStatus.INDEXED,
            chunk_count=25,
            access_level=AccessLevel.TEAM,
            indexed_at=now,
            created_at=now,
            updated_at=now,
            tags=["test", "important"],
        )

        assert response.doc_id == "doc_123"
        assert response.user_id == "user_456"
        assert response.organization_id == "org_789"
        assert response.title == "Test Document"
        assert response.doc_type == DocumentType.PDF
        assert response.file_size == 2048000
        assert response.version == 1
        assert response.status == DocumentStatus.INDEXED
        assert response.chunk_count == 25
        assert len(response.tags) == 2

    def test_document_response_minimal(self):
        """Test document response with minimal fields"""
        now = datetime.now(timezone.utc)

        response = DocumentResponse(
            doc_id="doc_min",
            user_id="user_123",
            organization_id=None,
            title="Minimal",
            description=None,
            doc_type=DocumentType.TXT,
            file_id="file_min",
            file_size=100,
            version=1,
            is_latest=True,
            status=DocumentStatus.DRAFT,
            chunk_count=0,
            access_level=AccessLevel.PRIVATE,
            indexed_at=None,
            created_at=now,
            updated_at=now,
        )

        assert response.organization_id is None
        assert response.description is None
        assert response.indexed_at is None
        assert response.tags == []


class TestDocumentVersionResponse:
    """Test DocumentVersionResponse model"""

    def test_version_response_creation(self):
        """Test creating version response"""
        now = datetime.now(timezone.utc)

        response = DocumentVersionResponse(
            doc_id="doc_123",
            version=3,
            parent_version_id="doc_122",
            is_latest=True,
            status=DocumentStatus.INDEXED,
            chunk_count=30,
            created_at=now,
        )

        assert response.doc_id == "doc_123"
        assert response.version == 3
        assert response.parent_version_id == "doc_122"
        assert response.is_latest is True
        assert response.status == DocumentStatus.INDEXED
        assert response.chunk_count == 30

    def test_version_response_no_parent(self):
        """Test version response without parent"""
        now = datetime.now(timezone.utc)

        response = DocumentVersionResponse(
            doc_id="doc_456",
            version=1,
            parent_version_id=None,
            is_latest=True,
            status=DocumentStatus.DRAFT,
            chunk_count=0,
            created_at=now,
        )

        assert response.version == 1
        assert response.parent_version_id is None


class TestSearchResultItem:
    """Test SearchResultItem model"""

    def test_search_result_item_creation(self):
        """Test creating search result item"""
        result = SearchResultItem(
            doc_id="doc_123",
            title="Relevant Document",
            doc_type=DocumentType.PDF,
            relevance_score=0.95,
            snippet="This is a relevant snippet from the document...",
            file_id="file_abc",
            chunk_id="chunk_5",
            metadata={"page": 10, "section": "Introduction"},
        )

        assert result.doc_id == "doc_123"
        assert result.title == "Relevant Document"
        assert result.doc_type == DocumentType.PDF
        assert result.relevance_score == 0.95
        assert result.snippet == "This is a relevant snippet from the document..."
        assert result.chunk_id == "chunk_5"
        assert result.metadata["page"] == 10

    def test_search_result_item_minimal(self):
        """Test search result item with minimal fields"""
        result = SearchResultItem(
            doc_id="doc_456",
            title="Simple Result",
            doc_type=DocumentType.TXT,
            relevance_score=0.75,
            snippet="Short snippet",
            file_id="file_xyz",
        )

        assert result.chunk_id is None
        assert result.metadata == {}


class TestRAGQueryResponse:
    """Test RAGQueryResponse model"""

    def test_rag_query_response_creation(self):
        """Test creating RAG query response"""
        sources = [
            SearchResultItem(
                doc_id="doc_1",
                title="Source 1",
                doc_type=DocumentType.PDF,
                relevance_score=0.9,
                snippet="Snippet 1",
                file_id="file_1",
            ),
            SearchResultItem(
                doc_id="doc_2",
                title="Source 2",
                doc_type=DocumentType.MARKDOWN,
                relevance_score=0.85,
                snippet="Snippet 2",
                file_id="file_2",
            ),
        ]

        response = RAGQueryResponse(
            query="What is the architecture?",
            answer="The architecture is a microservices-based system...",
            sources=sources,
            confidence=0.92,
            latency_ms=245.5,
        )

        assert response.query == "What is the architecture?"
        assert "microservices" in response.answer
        assert len(response.sources) == 2
        assert response.confidence == 0.92
        assert response.latency_ms == 245.5

    def test_rag_query_response_defaults(self):
        """Test RAG query response default values"""
        response = RAGQueryResponse(
            query="test query",
            answer="test answer",
        )

        assert response.sources == []
        assert response.confidence == 0.0
        assert response.latency_ms == 0.0


class TestSemanticSearchResponse:
    """Test SemanticSearchResponse model"""

    def test_semantic_search_response_creation(self):
        """Test creating semantic search response"""
        results = [
            SearchResultItem(
                doc_id=f"doc_{i}",
                title=f"Result {i}",
                doc_type=DocumentType.PDF,
                relevance_score=0.9 - (i * 0.1),
                snippet=f"Snippet {i}",
                file_id=f"file_{i}",
            )
            for i in range(5)
        ]

        response = SemanticSearchResponse(
            query="machine learning",
            results=results,
            total_count=50,
            latency_ms=150.3,
        )

        assert response.query == "machine learning"
        assert len(response.results) == 5
        assert response.total_count == 50
        assert response.latency_ms == 150.3

    def test_semantic_search_response_defaults(self):
        """Test semantic search response default values"""
        response = SemanticSearchResponse(
            query="test",
        )

        assert response.results == []
        assert response.total_count == 0
        assert response.latency_ms == 0.0


class TestDocumentPermissionResponse:
    """Test DocumentPermissionResponse model"""

    def test_permission_response_creation(self):
        """Test creating permission response"""
        response = DocumentPermissionResponse(
            doc_id="doc_123",
            access_level=AccessLevel.TEAM,
            allowed_users=["user_001", "user_002"],
            allowed_groups=["group_eng"],
            denied_users=["user_999"],
        )

        assert response.doc_id == "doc_123"
        assert response.access_level == AccessLevel.TEAM
        assert len(response.allowed_users) == 2
        assert len(response.allowed_groups) == 1
        assert len(response.denied_users) == 1

    def test_permission_response_defaults(self):
        """Test permission response default values"""
        response = DocumentPermissionResponse(
            doc_id="doc_456",
            access_level=AccessLevel.PRIVATE,
        )

        assert response.allowed_users == []
        assert response.allowed_groups == []
        assert response.denied_users == []


class TestDocumentStatsResponse:
    """Test DocumentStatsResponse model"""

    def test_stats_response_creation(self):
        """Test creating stats response"""
        response = DocumentStatsResponse(
            user_id="user_123",
            total_documents=100,
            indexed_documents=95,
            total_chunks=2500,
            total_size_bytes=52428800,
            by_type={"pdf": 50, "docx": 30, "markdown": 20},
            by_status={"indexed": 95, "indexing": 3, "failed": 2},
        )

        assert response.user_id == "user_123"
        assert response.total_documents == 100
        assert response.indexed_documents == 95
        assert response.total_chunks == 2500
        assert response.total_size_bytes == 52428800
        assert response.by_type["pdf"] == 50
        assert response.by_status["indexed"] == 95

    def test_stats_response_defaults(self):
        """Test stats response default values"""
        response = DocumentStatsResponse(
            user_id="user_456",
        )

        assert response.total_documents == 0
        assert response.indexed_documents == 0
        assert response.total_chunks == 0
        assert response.total_size_bytes == 0
        assert response.by_type == {}
        assert response.by_status == {}


class TestEnumTypes:
    """Test enum type definitions"""

    def test_all_document_types_defined(self):
        """Test all document types are properly defined"""
        types = [
            DocumentType.PDF,
            DocumentType.DOCX,
            DocumentType.PPTX,
            DocumentType.XLSX,
            DocumentType.TXT,
            DocumentType.MARKDOWN,
            DocumentType.HTML,
            DocumentType.JSON,
        ]
        assert len(types) == 8
        assert len(set(types)) == 8

    def test_all_document_statuses_defined(self):
        """Test all document statuses are properly defined"""
        statuses = [
            DocumentStatus.DRAFT,
            DocumentStatus.INDEXING,
            DocumentStatus.INDEXED,
            DocumentStatus.UPDATE_PENDING,
            DocumentStatus.UPDATING,
            DocumentStatus.ARCHIVED,
            DocumentStatus.FAILED,
            DocumentStatus.DELETED,
        ]
        assert len(statuses) == 8
        assert len(set(statuses)) == 8

    def test_all_access_levels_defined(self):
        """Test all access levels are properly defined"""
        levels = [
            AccessLevel.PRIVATE,
            AccessLevel.TEAM,
            AccessLevel.ORGANIZATION,
            AccessLevel.PUBLIC,
        ]
        assert len(levels) == 4
        assert len(set(levels)) == 4

    def test_all_chunking_strategies_defined(self):
        """Test all chunking strategies are properly defined"""
        strategies = [
            ChunkingStrategy.FIXED_SIZE,
            ChunkingStrategy.SEMANTIC,
            ChunkingStrategy.PARAGRAPH,
            ChunkingStrategy.RECURSIVE,
        ]
        assert len(strategies) == 4
        assert len(set(strategies)) == 4

    def test_all_update_strategies_defined(self):
        """Test all update strategies are properly defined"""
        strategies = [
            UpdateStrategy.FULL,
            UpdateStrategy.SMART,
            UpdateStrategy.DIFF,
        ]
        assert len(strategies) == 3
        assert len(set(strategies)) == 3


if __name__ == "__main__":
    pytest.main([__file__])
