"""
Memory Service Contract Proof Tests

Validates that the memory service data contracts and logic contracts work correctly.

Test Categories:
1. Data Contract Factory Tests - Verify factory generates valid data
2. Request Builder Tests - Verify builders create valid requests
3. Contract Validation Tests - Verify validation catches errors
4. Business Rule Tests - Verify logic rules are enforced
5. Response Validation Tests - Verify responses match schemas

Related Documents:
- Data Contract: tests/contracts/memory/data_contract.py
- Logic Contract: tests/contracts/memory/logic_contract.md

Test Execution:
    pytest tests/component/golden/test_memory_contracts_proof.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from tests.contracts.memory import (
    # Factories
    MemoryTestDataFactory,
    # Builders
    FactualMemoryRequestBuilder,
    SessionMemoryRequestBuilder,
    # Schemas
    CreateMemoryRequest,
    ExtractFactualMemoryRequest,
    ExtractEpisodicMemoryRequest,
    MemoryOperationResult,
    MemoryResponse,
    MemoryListResponse,
)


# ===================================================================================
# TEST CLASS 1: DATA CONTRACT FACTORY TESTS
# ===================================================================================

class TestMemoryDataContractFactory:
    """Test that MemoryTestDataFactory generates valid, consistent test data"""

    @pytest.fixture
    def factory(self):
        """Create test data factory"""
        return MemoryTestDataFactory(seed=42)

    # ==================== Factual Memory ====================

    def test_factory_generates_valid_factual_extract_request(self, factory):
        """Test factory creates valid factual extraction request"""
        request = factory.factual_extract_request()

        # Validate schema
        assert isinstance(request, ExtractFactualMemoryRequest)
        assert request.user_id.startswith("usr_")
        assert len(request.dialog_content) > 0
        assert 0.0 <= request.importance_score <= 1.0

    def test_factory_generates_valid_factual_memory_request(self, factory):
        """Test factory creates valid factual memory creation request"""
        request = factory.create_factual_memory_request()

        assert isinstance(request, CreateMemoryRequest)
        assert request.memory_type == "factual"
        assert request.subject is not None
        assert request.predicate is not None
        assert request.object_value is not None
        assert len(request.content) > 0

    def test_factory_generates_valid_factual_memory_response(self, factory):
        """Test factory creates valid factual memory response"""
        response = factory.factual_memory_response()

        assert isinstance(response, MemoryResponse)
        assert response.memory_type == "factual"
        assert response.id.startswith("fact_")
        assert response.subject is not None
        assert response.predicate is not None
        assert response.object_value is not None

    # ==================== Episodic Memory ====================

    def test_factory_generates_valid_episodic_extract_request(self, factory):
        """Test factory creates valid episodic extraction request"""
        request = factory.episodic_extract_request()

        assert isinstance(request, ExtractEpisodicMemoryRequest)
        assert request.user_id.startswith("usr_")
        assert len(request.dialog_content) > 0
        assert 0.0 <= request.importance_score <= 1.0

    def test_factory_generates_valid_episodic_memory_response(self, factory):
        """Test factory creates valid episodic memory response"""
        response = factory.episodic_memory_response()

        assert isinstance(response, MemoryResponse)
        assert response.memory_type == "episodic"
        assert response.id.startswith("epis_")
        assert response.event_type is not None
        assert -1.0 <= response.emotional_valence <= 1.0
        assert 0.0 <= response.vividness <= 1.0

    # ==================== Procedural Memory ====================

    def test_factory_generates_valid_procedural_memory_response(self, factory):
        """Test factory creates valid procedural memory response"""
        response = factory.procedural_memory_response()

        assert isinstance(response, MemoryResponse)
        assert response.memory_type == "procedural"
        assert response.id.startswith("proc_")
        assert response.skill_type is not None
        assert response.steps is not None
        assert len(response.steps) > 0
        assert response.domain is not None

    # ==================== Semantic Memory ====================

    def test_factory_generates_valid_semantic_memory_response(self, factory):
        """Test factory creates valid semantic memory response"""
        response = factory.semantic_memory_response()

        assert isinstance(response, MemoryResponse)
        assert response.memory_type == "semantic"
        assert response.id.startswith("sem_")
        assert response.concept_type is not None
        assert response.definition is not None
        assert response.category is not None

    # ==================== Working Memory ====================

    def test_factory_generates_valid_working_memory_response(self, factory):
        """Test factory creates valid working memory response"""
        response = factory.working_memory_response()

        assert isinstance(response, MemoryResponse)
        assert response.memory_type == "working"
        assert response.id.startswith("work_")
        assert response.task_id is not None
        assert response.ttl_seconds > 0
        assert response.expires_at is not None

        # Validate expiry calculation
        created = datetime.fromisoformat(response.created_at)
        expires = datetime.fromisoformat(response.expires_at)
        diff_seconds = (expires - created).total_seconds()
        assert abs(diff_seconds - response.ttl_seconds) < 1  # Allow 1s tolerance

    # ==================== Session Memory ====================

    def test_factory_generates_valid_session_memory_response(self, factory):
        """Test factory creates valid session memory response"""
        response = factory.session_memory_response()

        assert isinstance(response, MemoryResponse)
        assert response.memory_type == "session"
        assert response.id.startswith("sess_")
        assert response.session_id is not None
        assert response.interaction_sequence >= 1
        assert response.conversation_state is not None

    # ==================== Lists and Statistics ====================

    def test_factory_generates_valid_memory_list(self, factory):
        """Test factory creates valid memory list response"""
        response = factory.memory_list_response(memory_type="factual", count=3)

        assert isinstance(response, MemoryListResponse)
        assert response.count == 3
        assert len(response.memories) == 3
        assert all(m.memory_type == "factual" for m in response.memories)

    def test_factory_generates_valid_statistics(self, factory):
        """Test factory creates valid statistics response"""
        response = factory.memory_statistics_response()

        assert response.user_id.startswith("usr_")
        assert response.total_memories > 0
        assert "factual" in response.by_type
        assert "episodic" in response.by_type
        assert "procedural" in response.by_type
        assert "semantic" in response.by_type
        assert "working" in response.by_type
        assert "session" in response.by_type

    # ==================== Consistency Tests ====================

    def test_factory_with_seed_generates_consistent_data(self):
        """Test that factory with same seed generates consistent data"""
        factory1 = MemoryTestDataFactory(seed=100)
        factory2 = MemoryTestDataFactory(seed=100)

        req1 = factory1.factual_extract_request()
        req2 = factory2.factual_extract_request()

        # Should generate same user_id with same seed
        assert req1.user_id == req2.user_id

    def test_factory_generates_unique_ids_per_instance(self, factory):
        """Test that factory generates unique IDs within single instance"""
        response1 = factory.factual_memory_response()
        response2 = factory.factual_memory_response()
        response3 = factory.episodic_memory_response()

        # All IDs should be unique
        ids = {response1.id, response2.id, response3.id}
        assert len(ids) == 3


# ===================================================================================
# TEST CLASS 2: REQUEST BUILDER TESTS
# ===================================================================================

class TestMemoryRequestBuilders:
    """Test that request builders create valid, customizable requests"""

    def test_factual_memory_builder_creates_valid_request(self):
        """Test FactualMemoryRequestBuilder creates valid request"""
        request = (
            FactualMemoryRequestBuilder()
            .for_user("usr_test_123")
            .with_fact("Sarah", "works at", "Microsoft")
            .with_importance(0.8)
            .with_fact_type("employment")
            .with_tags(["work", "career"])
            .build()
        )

        assert isinstance(request, CreateMemoryRequest)
        assert request.user_id == "usr_test_123"
        assert request.memory_type == "factual"
        assert request.subject == "Sarah"
        assert request.predicate == "works at"
        assert request.object_value == "Microsoft"
        assert request.importance_score == 0.8
        assert request.fact_type == "employment"
        assert "work" in request.tags

    def test_session_memory_builder_creates_valid_multi_message_session(self):
        """Test SessionMemoryRequestBuilder creates valid multi-message session"""
        requests = (
            SessionMemoryRequestBuilder()
            .for_user("usr_test_456")
            .with_session("session_test_789")
            .add_message("Hello, how are you?", message_type="human", role="user")
            .add_message("I'm doing great! How can I help?", message_type="ai", role="assistant")
            .add_message("I need help with deployment", message_type="human", role="user")
            .build_messages()
        )

        assert len(requests) == 3

        # Validate first message
        assert requests[0].user_id == "usr_test_456"
        assert requests[0].session_id == "session_test_789"
        assert requests[0].interaction_sequence == 1
        assert requests[0].content == "Hello, how are you?"

        # Validate second message
        assert requests[1].interaction_sequence == 2
        assert requests[1].content == "I'm doing great! How can I help?"

        # Validate third message
        assert requests[2].interaction_sequence == 3

    def test_builder_with_defaults_creates_valid_request(self):
        """Test builder with minimal input uses sensible defaults"""
        request = FactualMemoryRequestBuilder().build()

        assert isinstance(request, CreateMemoryRequest)
        assert request.user_id.startswith("usr_")  # Auto-generated
        assert request.memory_type == "factual"
        assert request.confidence == 0.9  # Default
        assert len(request.content) > 0  # Auto-generated


# ===================================================================================
# TEST CLASS 3: CONTRACT VALIDATION TESTS (NEGATIVE TESTS)
# ===================================================================================

class TestMemoryContractValidation:
    """Test that Pydantic validation catches invalid data"""

    # ==================== General Memory Validation ====================

    @pytest.mark.logic_rule("BR-MEM-002")
    def test_empty_user_id_raises_validation_error(self):
        """Test BR-MEM-002: Empty user_id is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ExtractFactualMemoryRequest(
                user_id="",  # Empty - should fail
                dialog_content="Test content",
                importance_score=0.5
            )
        assert "user_id" in str(exc_info.value)

    @pytest.mark.logic_rule("BR-MEM-004")
    def test_empty_content_raises_validation_error(self):
        """Test BR-MEM-004: Empty content is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ExtractFactualMemoryRequest(
                user_id="usr_123",
                dialog_content="",  # Empty - should fail
                importance_score=0.5
            )
        assert "dialog_content" in str(exc_info.value)

    @pytest.mark.logic_rule("BR-MEM-005")
    def test_importance_score_out_of_range_raises_validation_error(self):
        """Test BR-MEM-005: importance_score outside [0, 1] is rejected"""
        with pytest.raises(ValidationError):
            ExtractFactualMemoryRequest(
                user_id="usr_123",
                dialog_content="Test",
                importance_score=1.5  # Out of range - should fail
            )

    @pytest.mark.logic_rule("BR-MEM-005")
    def test_negative_importance_score_raises_validation_error(self):
        """Test BR-MEM-005: Negative importance_score is rejected"""
        with pytest.raises(ValidationError):
            ExtractFactualMemoryRequest(
                user_id="usr_123",
                dialog_content="Test",
                importance_score=-0.1  # Negative - should fail
            )

    @pytest.mark.logic_rule("BR-MEM-006")
    def test_confidence_out_of_range_raises_validation_error(self):
        """Test BR-MEM-006: confidence outside [0, 1] is rejected"""
        with pytest.raises(ValidationError):
            CreateMemoryRequest(
                user_id="usr_123",
                memory_type="factual",
                content="Test",
                confidence=2.0  # Out of range - should fail
            )

    # ==================== Episodic Memory Validation ====================

    @pytest.mark.logic_rule("BR-EPIS-001")
    def test_emotional_valence_out_of_range_raises_validation_error(self):
        """Test BR-EPIS-001: emotional_valence outside [-1, 1] is rejected"""
        with pytest.raises(ValidationError):
            CreateMemoryRequest(
                user_id="usr_123",
                memory_type="episodic",
                content="Test",
                emotional_valence=1.5  # Out of range - should fail
            )

    @pytest.mark.logic_rule("BR-EPIS-002")
    def test_vividness_out_of_range_raises_validation_error(self):
        """Test BR-EPIS-002: vividness outside [0, 1] is rejected"""
        with pytest.raises(ValidationError):
            CreateMemoryRequest(
                user_id="usr_123",
                memory_type="episodic",
                content="Test",
                vividness=-0.5  # Negative - should fail
            )

    # ==================== Working Memory Validation ====================

    @pytest.mark.logic_rule("BR-WORK-001")
    def test_zero_ttl_raises_validation_error(self):
        """Test BR-WORK-001: Zero TTL is rejected"""
        with pytest.raises(ValidationError):
            CreateMemoryRequest(
                user_id="usr_123",
                memory_type="working",
                content="Test",
                task_id="task_1",
                task_context={"key": "value"},
                ttl_seconds=0  # Zero - should fail
            )

    @pytest.mark.logic_rule("BR-WORK-001")
    def test_negative_ttl_raises_validation_error(self):
        """Test BR-WORK-001: Negative TTL is rejected"""
        with pytest.raises(ValidationError):
            CreateMemoryRequest(
                user_id="usr_123",
                memory_type="working",
                content="Test",
                task_id="task_1",
                task_context={"key": "value"},
                ttl_seconds=-100  # Negative - should fail
            )

    # ==================== Session Memory Validation ====================

    @pytest.mark.logic_rule("BR-SESS-002")
    def test_zero_interaction_sequence_raises_validation_error(self):
        """Test BR-SESS-002: interaction_sequence must be positive"""
        with pytest.raises(ValidationError):
            CreateMemoryRequest(
                user_id="usr_123",
                memory_type="session",
                content="Test",
                session_id="sess_1",
                interaction_sequence=0  # Zero - should fail (must be >= 1)
            )


# ===================================================================================
# TEST CLASS 4: BUSINESS RULE TESTS
# ===================================================================================

class TestMemoryBusinessRules:
    """Test that business rules from logic contract are enforced"""

    @pytest.fixture
    def factory(self):
        return MemoryTestDataFactory()

    @pytest.mark.logic_rule("BR-MEM-001")
    def test_memory_ids_are_unique(self, factory):
        """Test BR-MEM-001: All memories have unique IDs"""
        memory1 = factory.factual_memory_response()
        memory2 = factory.factual_memory_response()
        memory3 = factory.episodic_memory_response()

        # All IDs must be unique
        ids = [memory1.id, memory2.id, memory3.id]
        assert len(ids) == len(set(ids)), "Memory IDs are not unique"

    @pytest.mark.logic_rule("BR-MEM-003")
    def test_memory_type_is_valid(self, factory):
        """Test BR-MEM-003: memory_type is one of six valid types"""
        valid_types = ["factual", "episodic", "procedural", "semantic", "working", "session"]

        # Test each valid type
        for memory_type in valid_types:
            request = CreateMemoryRequest(
                user_id="usr_123",
                memory_type=memory_type,
                content="Test content"
            )
            assert request.memory_type in valid_types

    @pytest.mark.logic_rule("BR-MEM-007")
    def test_access_count_defaults_to_zero(self, factory):
        """Test BR-MEM-007: access_count starts at 0"""
        response = factory.factual_memory_response()
        assert response.access_count == 0

    @pytest.mark.logic_rule("BR-FACT-003")
    def test_factual_content_auto_generated_from_spo(self, factory):
        """Test BR-FACT-003: Content auto-generated from subject-predicate-object"""
        request = factory.create_factual_memory_request(
            subject="Alice",
            predicate="lives in",
            object_value="London"
        )
        # Content should be auto-generated or match SPO
        assert "Alice" in request.content
        assert "lives in" in request.content
        assert "London" in request.content

    @pytest.mark.logic_rule("BR-WORK-002")
    def test_working_memory_expiry_calculation(self, factory):
        """Test BR-WORK-002: expires_at calculated from created_at + TTL"""
        response = factory.working_memory_response(ttl_seconds=3600)

        created_at = datetime.fromisoformat(response.created_at)
        expires_at = datetime.fromisoformat(response.expires_at)
        ttl_seconds = response.ttl_seconds

        # Calculate expected expiry
        expected_expires = created_at + timedelta(seconds=ttl_seconds)

        # Allow 1 second tolerance
        diff = abs((expires_at - expected_expires).total_seconds())
        assert diff < 1, f"Expiry calculation incorrect: diff={diff}s"

    @pytest.mark.logic_rule("BR-SESS-003")
    def test_session_sequence_auto_increments(self):
        """Test BR-SESS-003: interaction_sequence auto-increments"""
        builder = SessionMemoryRequestBuilder()
        requests = (
            builder
            .with_session("sess_test")
            .add_message("Message 1")
            .add_message("Message 2")
            .add_message("Message 3")
            .build_messages()
        )

        # Verify sequences increment correctly
        assert requests[0].interaction_sequence == 1
        assert requests[1].interaction_sequence == 2
        assert requests[2].interaction_sequence == 3


# ===================================================================================
# TEST CLASS 5: RESPONSE VALIDATION TESTS
# ===================================================================================

class TestMemoryResponseValidation:
    """Test that response schemas validate correctly"""

    @pytest.fixture
    def factory(self):
        return MemoryTestDataFactory()

    def test_memory_operation_result_validation(self, factory):
        """Test MemoryOperationResult schema validation"""
        result = factory.memory_operation_result(
            success=True,
            operation="create",
            message="Memory created successfully",
            affected_count=1
        )

        assert isinstance(result, MemoryOperationResult)
        assert result.success is True
        assert result.operation == "create"
        assert result.affected_count == 1

    def test_memory_response_has_required_fields(self, factory):
        """Test MemoryResponse includes all required fields"""
        response = factory.factual_memory_response()

        # Required fields
        assert response.id is not None
        assert response.user_id is not None
        assert response.memory_type is not None
        assert response.content is not None
        assert response.importance_score is not None
        assert response.confidence is not None
        assert response.access_count is not None
        assert response.tags is not None
        assert response.context is not None
        assert response.created_at is not None
        assert response.updated_at is not None

    def test_memory_list_response_validation(self, factory):
        """Test MemoryListResponse schema validation"""
        response = factory.memory_list_response(memory_type="factual", count=5)

        assert isinstance(response, MemoryListResponse)
        assert response.count == 5
        assert len(response.memories) == 5
        assert all(isinstance(m, MemoryResponse) for m in response.memories)

    def test_timestamp_fields_are_iso8601_format(self, factory):
        """Test that timestamp fields are ISO 8601 formatted"""
        response = factory.episodic_memory_response()

        # Validate ISO 8601 format by parsing
        datetime.fromisoformat(response.created_at)
        datetime.fromisoformat(response.updated_at)
        if response.episode_date:
            datetime.fromisoformat(response.episode_date)


# ===================================================================================
# TEST CLASS 6: EDGE CASE TESTS
# ===================================================================================

class TestMemoryEdgeCases:
    """Test edge cases documented in logic contract"""

    @pytest.fixture
    def factory(self):
        return MemoryTestDataFactory()

    def test_unicode_content_handling(self, factory):
        """Test Edge Case 7: Unicode content with emojis and CJK characters"""
        content = "今天天气很好 🌞 Très bien! 日本語テスト"
        request = CreateMemoryRequest(
            user_id="usr_123",
            memory_type="factual",
            content=content,
            subject="Test",
            predicate="is",
            object_value="unicode"
        )

        # Validate content preserved
        assert request.content == content

    def test_working_memory_with_short_ttl(self, factory):
        """Test Edge Case 2: Working memory with very short TTL"""
        response = factory.working_memory_response(ttl_seconds=1)

        assert response.ttl_seconds == 1
        # Expiry should be ~1 second from creation
        created = datetime.fromisoformat(response.created_at)
        expires = datetime.fromisoformat(response.expires_at)
        diff = (expires - created).total_seconds()
        assert 0.5 <= diff <= 1.5, f"TTL calculation off: {diff}s"

    def test_session_with_single_message(self, factory):
        """Test Edge Case 3: Session with only one message"""
        response = factory.session_memory_response(interaction_sequence=1)

        assert response.session_id is not None
        assert response.interaction_sequence == 1
        # Single message session is valid

    def test_factual_memory_with_same_subject_different_predicate(self, factory):
        """Test Edge Case 4: Multiple facts with same subject, different predicates"""
        fact1 = factory.create_factual_memory_request(
            subject="John",
            predicate="lives in",
            object_value="Tokyo"
        )
        fact2 = factory.create_factual_memory_request(
            subject="John",
            predicate="works at",
            object_value="Apple"
        )

        # Both should be valid (different predicates)
        assert fact1.subject == fact2.subject
        assert fact1.predicate != fact2.predicate

    def test_bulk_memory_creation(self, factory):
        """Test Edge Case 8: Bulk creation of many memories"""
        memories = []
        for i in range(100):
            memory = factory.factual_memory_response()
            memories.append(memory)

        # All IDs should be unique
        ids = [m.id for m in memories]
        assert len(ids) == len(set(ids)), "Duplicate IDs in bulk creation"


# ===================================================================================
# SUMMARY TEST (META)
# ===================================================================================

def test_all_memory_types_covered():
    """Meta-test: Verify all 6 memory types are covered by tests"""
    factory = MemoryTestDataFactory()

    # Ensure factory can generate all memory types
    factual = factory.factual_memory_response()
    episodic = factory.episodic_memory_response()
    procedural = factory.procedural_memory_response()
    semantic = factory.semantic_memory_response()
    working = factory.working_memory_response()
    session = factory.session_memory_response()

    memory_types = {factual.memory_type, episodic.memory_type, procedural.memory_type,
                    semantic.memory_type, working.memory_type, session.memory_type}

    assert memory_types == {"factual", "episodic", "procedural", "semantic", "working", "session"}


# ===================================================================================
# RUN TESTS
# ===================================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
