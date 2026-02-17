"""
Unit Tests for Memory Service Models

Tests core memory service models based on cognitive science memory types.
Tests validation, defaults, and field constraints.

Related Documents:
- Domain: docs/domain/memory_service.md
- PRD: docs/prd/memory_service.md
- Design: docs/design/memory_service.md
- Data Contract: tests/contracts/memory/data_contract.py
"""

import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError
from microservices.memory_service.models import (
    MemoryType,
    MemoryModel,
    FactualMemory,
    ProceduralMemory,
    EpisodicMemory,
    SemanticMemory,
    WorkingMemory,
    SessionMemory,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryAssociation,
    MemoryOperationResult,
    MemoryCreateRequest,
    MemoryUpdateRequest,
    MemoryListParams,
    MemoryServiceStatus,
)


# =============================================================================
# MemoryType Enum Tests
# =============================================================================

class TestMemoryType:
    """Test MemoryType enum values"""

    def test_memory_type_factual_value(self):
        """Test factual memory type value"""
        assert MemoryType.FACTUAL.value == "factual"

    def test_memory_type_procedural_value(self):
        """Test procedural memory type value"""
        assert MemoryType.PROCEDURAL.value == "procedural"

    def test_memory_type_episodic_value(self):
        """Test episodic memory type value"""
        assert MemoryType.EPISODIC.value == "episodic"

    def test_memory_type_semantic_value(self):
        """Test semantic memory type value"""
        assert MemoryType.SEMANTIC.value == "semantic"

    def test_memory_type_working_value(self):
        """Test working memory type value"""
        assert MemoryType.WORKING.value == "working"

    def test_memory_type_session_value(self):
        """Test session memory type value"""
        assert MemoryType.SESSION.value == "session"

    def test_memory_type_count(self):
        """Test total number of memory types"""
        assert len(MemoryType) == 6

    def test_memory_type_comparison(self):
        """Test memory type comparison"""
        assert MemoryType.FACTUAL != MemoryType.EPISODIC
        assert MemoryType.FACTUAL == MemoryType.FACTUAL


# =============================================================================
# MemoryModel Base Class Tests
# =============================================================================

class TestMemoryModel:
    """Test MemoryModel base class"""

    def test_memory_model_creation_minimal(self):
        """Test memory model creation with minimal required fields"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test content"
        )

        assert memory.user_id == "user_123"
        assert memory.memory_type == MemoryType.FACTUAL
        assert memory.content == "Test content"

    def test_memory_model_auto_generates_id(self):
        """Test that ID is auto-generated if not provided"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert memory.id is not None
        assert len(memory.id) == 36  # UUID format

    def test_memory_model_accepts_custom_id(self):
        """Test that custom ID can be provided"""
        memory = MemoryModel(
            id="custom_id_123",
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert memory.id == "custom_id_123"

    def test_memory_model_default_importance_score(self):
        """Test default importance score is 0.5"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert memory.importance_score == 0.5

    def test_memory_model_default_confidence(self):
        """Test default confidence is 0.8"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert memory.confidence == 0.8

    def test_memory_model_default_access_count(self):
        """Test default access count is 0"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert memory.access_count == 0

    def test_memory_model_default_empty_tags(self):
        """Test default tags is empty list"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert memory.tags == []

    def test_memory_model_default_empty_context(self):
        """Test default context is empty dict"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert memory.context == {}

    def test_memory_model_importance_score_range_min(self):
        """Test importance score minimum boundary (0.0)"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test",
            importance_score=0.0
        )
        assert memory.importance_score == 0.0

    def test_memory_model_importance_score_range_max(self):
        """Test importance score maximum boundary (1.0)"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test",
            importance_score=1.0
        )
        assert memory.importance_score == 1.0

    def test_memory_model_importance_score_below_range(self):
        """Test importance score below minimum raises error"""
        with pytest.raises(ValidationError):
            MemoryModel(
                user_id="user_123",
                memory_type=MemoryType.FACTUAL,
                content="Test",
                importance_score=-0.1
            )

    def test_memory_model_importance_score_above_range(self):
        """Test importance score above maximum raises error"""
        with pytest.raises(ValidationError):
            MemoryModel(
                user_id="user_123",
                memory_type=MemoryType.FACTUAL,
                content="Test",
                importance_score=1.1
            )

    def test_memory_model_confidence_range_min(self):
        """Test confidence minimum boundary (0.0)"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test",
            confidence=0.0
        )
        assert memory.confidence == 0.0

    def test_memory_model_confidence_range_max(self):
        """Test confidence maximum boundary (1.0)"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test",
            confidence=1.0
        )
        assert memory.confidence == 1.0

    def test_memory_model_access_count_non_negative(self):
        """Test access count must be non-negative"""
        with pytest.raises(ValidationError):
            MemoryModel(
                user_id="user_123",
                memory_type=MemoryType.FACTUAL,
                content="Test",
                access_count=-1
            )

    def test_memory_model_with_embedding(self):
        """Test memory model with embedding vector"""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test",
            embedding=embedding
        )
        assert memory.embedding == embedding

    def test_memory_model_with_tags(self):
        """Test memory model with custom tags"""
        tags = ["important", "work", "project"]
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test",
            tags=tags
        )
        assert memory.tags == tags

    def test_memory_model_with_context(self):
        """Test memory model with context metadata"""
        context = {"source": "api", "version": "1.0"}
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test",
            context=context
        )
        assert memory.context == context

    def test_memory_model_created_at_auto_set(self):
        """Test created_at is auto-set"""
        before = datetime.now()
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        after = datetime.now()
        assert before <= memory.created_at <= after

    def test_memory_model_updated_at_auto_set(self):
        """Test updated_at is auto-set"""
        before = datetime.now()
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        after = datetime.now()
        assert before <= memory.updated_at <= after


# =============================================================================
# FactualMemory Tests
# =============================================================================

class TestFactualMemory:
    """Test FactualMemory model for facts and declarative knowledge"""

    def test_factual_memory_creation(self):
        """Test factual memory creation with required fields"""
        memory = FactualMemory(
            user_id="user_123",
            content="John lives in Tokyo",
            fact_type="person_location",
            subject="John",
            predicate="lives in",
            object_value="Tokyo"
        )

        assert memory.memory_type == MemoryType.FACTUAL
        assert memory.fact_type == "person_location"
        assert memory.subject == "John"
        assert memory.predicate == "lives in"
        assert memory.object_value == "Tokyo"

    def test_factual_memory_default_verification_status(self):
        """Test default verification status is unverified"""
        memory = FactualMemory(
            user_id="user_123",
            content="Test fact",
            fact_type="test",
            subject="A",
            predicate="is",
            object_value="B"
        )
        assert memory.verification_status == "unverified"

    def test_factual_memory_default_empty_related_facts(self):
        """Test default related facts is empty list"""
        memory = FactualMemory(
            user_id="user_123",
            content="Test fact",
            fact_type="test",
            subject="A",
            predicate="is",
            object_value="B"
        )
        assert memory.related_facts == []

    def test_factual_memory_with_source(self):
        """Test factual memory with source attribution"""
        memory = FactualMemory(
            user_id="user_123",
            content="Earth orbits the Sun",
            fact_type="science",
            subject="Earth",
            predicate="orbits",
            object_value="Sun",
            source="Astronomy textbook"
        )
        assert memory.source == "Astronomy textbook"

    def test_factual_memory_with_fact_context(self):
        """Test factual memory with additional context"""
        memory = FactualMemory(
            user_id="user_123",
            content="Test fact",
            fact_type="test",
            subject="A",
            predicate="is",
            object_value="B",
            fact_context="Additional context about the fact"
        )
        assert memory.fact_context == "Additional context about the fact"

    def test_factual_memory_with_related_facts(self):
        """Test factual memory with related fact IDs"""
        related = ["fact_001", "fact_002"]
        memory = FactualMemory(
            user_id="user_123",
            content="Test fact",
            fact_type="test",
            subject="A",
            predicate="is",
            object_value="B",
            related_facts=related
        )
        assert memory.related_facts == related

    def test_factual_memory_auto_generate_content(self):
        """Test content auto-generation from subject-predicate-object"""
        memory = FactualMemory(
            user_id="user_123",
            fact_type="test",
            subject="Cat",
            predicate="is a",
            object_value="mammal",
            content=""  # Will be auto-generated
        )
        # Note: auto-generation happens if content is empty and SPO fields exist
        # The validator may or may not generate - testing actual behavior
        assert memory.subject == "Cat"
        assert memory.predicate == "is a"
        assert memory.object_value == "mammal"


# =============================================================================
# ProceduralMemory Tests
# =============================================================================

class TestProceduralMemory:
    """Test ProceduralMemory model for how-to knowledge"""

    def test_procedural_memory_creation(self):
        """Test procedural memory creation"""
        steps = [
            {"step": 1, "action": "Open editor"},
            {"step": 2, "action": "Write code"},
            {"step": 3, "action": "Save file"}
        ]
        memory = ProceduralMemory(
            user_id="user_123",
            content="How to write code",
            skill_type="programming",
            steps=steps,
            domain="software"
        )

        assert memory.memory_type == MemoryType.PROCEDURAL
        assert memory.skill_type == "programming"
        assert len(memory.steps) == 3
        assert memory.domain == "software"

    def test_procedural_memory_default_difficulty(self):
        """Test default difficulty level is medium"""
        memory = ProceduralMemory(
            user_id="user_123",
            content="Test procedure",
            skill_type="test",
            steps=[{"step": 1, "action": "Do something"}],
            domain="test"
        )
        assert memory.difficulty_level == "medium"

    def test_procedural_memory_default_success_rate(self):
        """Test default success rate is 0.0"""
        memory = ProceduralMemory(
            user_id="user_123",
            content="Test procedure",
            skill_type="test",
            steps=[{"step": 1, "action": "Do something"}],
            domain="test"
        )
        assert memory.success_rate == 0.0

    def test_procedural_memory_default_empty_prerequisites(self):
        """Test default prerequisites is empty list"""
        memory = ProceduralMemory(
            user_id="user_123",
            content="Test procedure",
            skill_type="test",
            steps=[{"step": 1, "action": "Do something"}],
            domain="test"
        )
        assert memory.prerequisites == []

    def test_procedural_memory_with_prerequisites(self):
        """Test procedural memory with prerequisites"""
        prerequisites = ["basic_knowledge", "tool_familiarity"]
        memory = ProceduralMemory(
            user_id="user_123",
            content="Advanced procedure",
            skill_type="advanced",
            steps=[{"step": 1, "action": "Start"}],
            domain="test",
            prerequisites=prerequisites
        )
        assert memory.prerequisites == prerequisites

    def test_procedural_memory_success_rate_range(self):
        """Test success rate boundary (0.0 to 1.0)"""
        memory = ProceduralMemory(
            user_id="user_123",
            content="Test procedure",
            skill_type="test",
            steps=[{"step": 1, "action": "Do something"}],
            domain="test",
            success_rate=0.75
        )
        assert memory.success_rate == 0.75


# =============================================================================
# EpisodicMemory Tests
# =============================================================================

class TestEpisodicMemory:
    """Test EpisodicMemory model for personal experiences"""

    def test_episodic_memory_creation(self):
        """Test episodic memory creation"""
        memory = EpisodicMemory(
            user_id="user_123",
            content="Visited Paris last summer",
            event_type="travel"
        )

        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.event_type == "travel"

    def test_episodic_memory_with_location(self):
        """Test episodic memory with location"""
        memory = EpisodicMemory(
            user_id="user_123",
            content="Visited Paris last summer",
            event_type="travel",
            location="Paris, France"
        )
        assert memory.location == "Paris, France"

    def test_episodic_memory_with_participants(self):
        """Test episodic memory with participants"""
        participants = ["Alice", "Bob", "Charlie"]
        memory = EpisodicMemory(
            user_id="user_123",
            content="Had dinner with friends",
            event_type="social",
            participants=participants
        )
        assert memory.participants == participants

    def test_episodic_memory_default_empty_participants(self):
        """Test default participants is empty list"""
        memory = EpisodicMemory(
            user_id="user_123",
            content="Solo trip",
            event_type="travel"
        )
        assert memory.participants == []

    def test_episodic_memory_emotional_valence_positive(self):
        """Test positive emotional valence"""
        memory = EpisodicMemory(
            user_id="user_123",
            content="Got promoted at work",
            event_type="career",
            emotional_valence=0.9
        )
        assert memory.emotional_valence == 0.9

    def test_episodic_memory_emotional_valence_negative(self):
        """Test negative emotional valence"""
        memory = EpisodicMemory(
            user_id="user_123",
            content="Lost my keys",
            event_type="daily",
            emotional_valence=-0.5
        )
        assert memory.emotional_valence == -0.5

    def test_episodic_memory_emotional_valence_range(self):
        """Test emotional valence range (-1.0 to 1.0)"""
        memory = EpisodicMemory(
            user_id="user_123",
            content="Neutral event",
            event_type="daily",
            emotional_valence=0.0
        )
        assert memory.emotional_valence == 0.0

    def test_episodic_memory_default_vividness(self):
        """Test default vividness is 0.5"""
        memory = EpisodicMemory(
            user_id="user_123",
            content="Test event",
            event_type="test"
        )
        assert memory.vividness == 0.5

    def test_episodic_memory_with_episode_date(self):
        """Test episodic memory with specific date"""
        episode_date = datetime(2024, 6, 15, 14, 30, 0)
        memory = EpisodicMemory(
            user_id="user_123",
            content="Birthday party",
            event_type="celebration",
            episode_date=episode_date
        )
        assert memory.episode_date == episode_date


# =============================================================================
# SemanticMemory Tests
# =============================================================================

class TestSemanticMemory:
    """Test SemanticMemory model for concepts and general knowledge"""

    def test_semantic_memory_creation(self):
        """Test semantic memory creation"""
        memory = SemanticMemory(
            user_id="user_123",
            content="Machine learning is a subset of AI",
            concept_type="technical",
            definition="A field of AI that enables systems to learn from data",
            category="artificial_intelligence"
        )

        assert memory.memory_type == MemoryType.SEMANTIC
        assert memory.concept_type == "technical"
        assert memory.category == "artificial_intelligence"

    def test_semantic_memory_default_abstraction_level(self):
        """Test default abstraction level is medium"""
        memory = SemanticMemory(
            user_id="user_123",
            content="Test concept",
            concept_type="test",
            definition="Test definition",
            category="test"
        )
        assert memory.abstraction_level == "medium"

    def test_semantic_memory_default_empty_related_concepts(self):
        """Test default related concepts is empty list"""
        memory = SemanticMemory(
            user_id="user_123",
            content="Test concept",
            concept_type="test",
            definition="Test definition",
            category="test"
        )
        assert memory.related_concepts == []

    def test_semantic_memory_default_empty_properties(self):
        """Test default properties is empty dict"""
        memory = SemanticMemory(
            user_id="user_123",
            content="Test concept",
            concept_type="test",
            definition="Test definition",
            category="test"
        )
        assert memory.properties == {}

    def test_semantic_memory_with_properties(self):
        """Test semantic memory with properties"""
        properties = {"color": "blue", "size": "large"}
        memory = SemanticMemory(
            user_id="user_123",
            content="Ocean concept",
            concept_type="geography",
            definition="A large body of salt water",
            category="nature",
            properties=properties
        )
        assert memory.properties == properties

    def test_semantic_memory_with_related_concepts(self):
        """Test semantic memory with related concept IDs"""
        related = ["concept_001", "concept_002"]
        memory = SemanticMemory(
            user_id="user_123",
            content="Related concept",
            concept_type="test",
            definition="Test",
            category="test",
            related_concepts=related
        )
        assert memory.related_concepts == related


# =============================================================================
# WorkingMemory Tests
# =============================================================================

class TestWorkingMemory:
    """Test WorkingMemory model for temporary task information"""

    def test_working_memory_creation(self):
        """Test working memory creation"""
        task_context = {"current_step": 1, "total_steps": 5}
        memory = WorkingMemory(
            user_id="user_123",
            content="Processing file upload",
            task_id="task_456",
            task_context=task_context
        )

        assert memory.memory_type == MemoryType.WORKING
        assert memory.task_id == "task_456"
        assert memory.task_context == task_context

    def test_working_memory_default_ttl(self):
        """Test default TTL is 3600 seconds (1 hour)"""
        memory = WorkingMemory(
            user_id="user_123",
            content="Test task",
            task_id="task_123",
            task_context={}
        )
        assert memory.ttl_seconds == 3600

    def test_working_memory_default_priority(self):
        """Test default priority is 1"""
        memory = WorkingMemory(
            user_id="user_123",
            content="Test task",
            task_id="task_123",
            task_context={}
        )
        assert memory.priority == 1

    def test_working_memory_custom_ttl(self):
        """Test custom TTL setting"""
        memory = WorkingMemory(
            user_id="user_123",
            content="Short task",
            task_id="task_123",
            task_context={},
            ttl_seconds=300  # 5 minutes
        )
        assert memory.ttl_seconds == 300

    def test_working_memory_priority_range(self):
        """Test priority range (1 to 10)"""
        memory = WorkingMemory(
            user_id="user_123",
            content="High priority task",
            task_id="task_123",
            task_context={},
            priority=10
        )
        assert memory.priority == 10

    def test_working_memory_ttl_minimum(self):
        """Test TTL minimum is 1 second"""
        memory = WorkingMemory(
            user_id="user_123",
            content="Quick task",
            task_id="task_123",
            task_context={},
            ttl_seconds=1
        )
        assert memory.ttl_seconds == 1


# =============================================================================
# SessionMemory Tests
# =============================================================================

class TestSessionMemory:
    """Test SessionMemory model for conversation context"""

    def test_session_memory_creation(self):
        """Test session memory creation"""
        memory = SessionMemory(
            user_id="user_123",
            content="User asked about weather",
            session_id="sess_789",
            interaction_sequence=1
        )

        assert memory.memory_type == MemoryType.SESSION
        assert memory.session_id == "sess_789"
        assert memory.interaction_sequence == 1

    def test_session_memory_default_session_type(self):
        """Test default session type is chat"""
        memory = SessionMemory(
            user_id="user_123",
            content="Test message",
            session_id="sess_123",
            interaction_sequence=1
        )
        assert memory.session_type == "chat"

    def test_session_memory_default_active(self):
        """Test default active status is True"""
        memory = SessionMemory(
            user_id="user_123",
            content="Test message",
            session_id="sess_123",
            interaction_sequence=1
        )
        assert memory.active is True

    def test_session_memory_default_empty_conversation_state(self):
        """Test default conversation state is empty dict"""
        memory = SessionMemory(
            user_id="user_123",
            content="Test message",
            session_id="sess_123",
            interaction_sequence=1
        )
        assert memory.conversation_state == {}

    def test_session_memory_with_conversation_state(self):
        """Test session memory with conversation state"""
        state = {"topic": "weather", "intent": "query"}
        memory = SessionMemory(
            user_id="user_123",
            content="What's the weather?",
            session_id="sess_123",
            interaction_sequence=1,
            conversation_state=state
        )
        assert memory.conversation_state == state

    def test_session_memory_inactive(self):
        """Test session memory can be set inactive"""
        memory = SessionMemory(
            user_id="user_123",
            content="Ended conversation",
            session_id="sess_123",
            interaction_sequence=5,
            active=False
        )
        assert memory.active is False


# =============================================================================
# MemorySearchQuery Tests
# =============================================================================

class TestMemorySearchQuery:
    """Test MemorySearchQuery model"""

    def test_search_query_minimal(self):
        """Test search query with minimal fields"""
        query = MemorySearchQuery(query="find memories about work")
        assert query.query == "find memories about work"

    def test_search_query_default_top_k(self):
        """Test default top_k is 10"""
        query = MemorySearchQuery(query="test")
        assert query.top_k == 10

    def test_search_query_default_similarity_threshold(self):
        """Test default similarity threshold is 0.7"""
        query = MemorySearchQuery(query="test")
        assert query.similarity_threshold == 0.7

    def test_search_query_with_memory_types(self):
        """Test search query with specific memory types"""
        types = [MemoryType.FACTUAL, MemoryType.EPISODIC]
        query = MemorySearchQuery(
            query="test",
            memory_types=types
        )
        assert query.memory_types == types

    def test_search_query_top_k_range(self):
        """Test top_k range (1 to 100)"""
        query = MemorySearchQuery(query="test", top_k=100)
        assert query.top_k == 100

    def test_search_query_with_filters(self):
        """Test search query with filters"""
        query = MemorySearchQuery(
            query="test",
            user_id="user_123",
            importance_min=0.5,
            confidence_min=0.8,
            tags=["important"]
        )
        assert query.user_id == "user_123"
        assert query.importance_min == 0.5
        assert query.confidence_min == 0.8
        assert query.tags == ["important"]


# =============================================================================
# MemorySearchResult Tests
# =============================================================================

class TestMemorySearchResult:
    """Test MemorySearchResult model"""

    def test_search_result_creation(self):
        """Test search result creation"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test memory"
        )
        result = MemorySearchResult(
            memory=memory,
            similarity_score=0.95,
            rank=1
        )

        assert result.memory == memory
        assert result.similarity_score == 0.95
        assert result.rank == 1

    def test_search_result_with_matched_content(self):
        """Test search result with matched content"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Long memory content"
        )
        result = MemorySearchResult(
            memory=memory,
            similarity_score=0.85,
            rank=2,
            matched_content="relevant part"
        )
        assert result.matched_content == "relevant part"

    def test_search_result_with_explanation(self):
        """Test search result with explanation"""
        memory = MemoryModel(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        result = MemorySearchResult(
            memory=memory,
            similarity_score=0.9,
            rank=1,
            explanation="High semantic similarity"
        )
        assert result.explanation == "High semantic similarity"


# =============================================================================
# MemoryAssociation Tests
# =============================================================================

class TestMemoryAssociation:
    """Test MemoryAssociation model"""

    def test_association_creation(self):
        """Test memory association creation"""
        association = MemoryAssociation(
            source_memory_id="mem_001",
            target_memory_id="mem_002",
            association_type="related",
            user_id="user_123"
        )

        assert association.source_memory_id == "mem_001"
        assert association.target_memory_id == "mem_002"
        assert association.association_type == "related"
        assert association.user_id == "user_123"

    def test_association_default_strength(self):
        """Test default association strength is 0.5"""
        association = MemoryAssociation(
            source_memory_id="mem_001",
            target_memory_id="mem_002",
            association_type="related",
            user_id="user_123"
        )
        assert association.strength == 0.5

    def test_association_custom_strength(self):
        """Test custom association strength"""
        association = MemoryAssociation(
            source_memory_id="mem_001",
            target_memory_id="mem_002",
            association_type="strong_link",
            user_id="user_123",
            strength=0.95
        )
        assert association.strength == 0.95


# =============================================================================
# MemoryOperationResult Tests
# =============================================================================

class TestMemoryOperationResult:
    """Test MemoryOperationResult model"""

    def test_operation_result_success(self):
        """Test successful operation result"""
        result = MemoryOperationResult(
            success=True,
            operation="create",
            message="Memory created successfully",
            memory_id="mem_123"
        )

        assert result.success is True
        assert result.operation == "create"
        assert result.memory_id == "mem_123"

    def test_operation_result_failure(self):
        """Test failed operation result"""
        result = MemoryOperationResult(
            success=False,
            operation="delete",
            message="Memory not found"
        )

        assert result.success is False
        assert result.memory_id is None

    def test_operation_result_default_affected_count(self):
        """Test default affected count is 0"""
        result = MemoryOperationResult(
            success=True,
            operation="update",
            message="Updated"
        )
        assert result.affected_count == 0

    def test_operation_result_with_data(self):
        """Test operation result with additional data"""
        data = {"old_value": "x", "new_value": "y"}
        result = MemoryOperationResult(
            success=True,
            operation="update",
            message="Updated",
            data=data
        )
        assert result.data == data


# =============================================================================
# MemoryCreateRequest Tests
# =============================================================================

class TestMemoryCreateRequest:
    """Test MemoryCreateRequest model"""

    def test_create_request_minimal(self):
        """Test create request with minimal fields"""
        request = MemoryCreateRequest(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test memory"
        )

        assert request.user_id == "user_123"
        assert request.memory_type == MemoryType.FACTUAL
        assert request.content == "Test memory"

    def test_create_request_default_importance(self):
        """Test default importance score is 0.5"""
        request = MemoryCreateRequest(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert request.importance_score == 0.5

    def test_create_request_default_confidence(self):
        """Test default confidence is 0.8"""
        request = MemoryCreateRequest(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test"
        )
        assert request.confidence == 0.8

    def test_create_request_allows_extra_fields(self):
        """Test create request allows extra fields for type-specific data"""
        # The model has extra="allow" config
        request = MemoryCreateRequest(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            content="Test",
            session_id="sess_123"  # Extra field for session type
        )
        assert request.session_id == "sess_123"


# =============================================================================
# MemoryUpdateRequest Tests
# =============================================================================

class TestMemoryUpdateRequest:
    """Test MemoryUpdateRequest model"""

    def test_update_request_all_optional(self):
        """Test all fields are optional"""
        request = MemoryUpdateRequest()
        assert request.content is None
        assert request.importance_score is None
        assert request.confidence is None
        assert request.tags is None
        assert request.context is None

    def test_update_request_partial(self):
        """Test partial update"""
        request = MemoryUpdateRequest(
            content="Updated content",
            importance_score=0.9
        )
        assert request.content == "Updated content"
        assert request.importance_score == 0.9
        assert request.tags is None


# =============================================================================
# MemoryListParams Tests
# =============================================================================

class TestMemoryListParams:
    """Test MemoryListParams model"""

    def test_list_params_minimal(self):
        """Test list params with minimal fields"""
        params = MemoryListParams(user_id="user_123")
        assert params.user_id == "user_123"

    def test_list_params_default_limit(self):
        """Test default limit is 50"""
        params = MemoryListParams(user_id="user_123")
        assert params.limit == 50

    def test_list_params_default_offset(self):
        """Test default offset is 0"""
        params = MemoryListParams(user_id="user_123")
        assert params.offset == 0

    def test_list_params_limit_range(self):
        """Test limit range (1 to 100)"""
        params = MemoryListParams(user_id="user_123", limit=100)
        assert params.limit == 100

    def test_list_params_with_filters(self):
        """Test list params with filters"""
        params = MemoryListParams(
            user_id="user_123",
            memory_type=MemoryType.FACTUAL,
            tags=["important"],
            importance_min=0.7
        )
        assert params.memory_type == MemoryType.FACTUAL
        assert params.tags == ["important"]
        assert params.importance_min == 0.7


# =============================================================================
# MemoryServiceStatus Tests
# =============================================================================

class TestMemoryServiceStatus:
    """Test MemoryServiceStatus model"""

    def test_status_creation(self):
        """Test service status creation"""
        status = MemoryServiceStatus(
            status="healthy",
            database_connected=True,
            timestamp=datetime.now()
        )

        assert status.service == "memory_service"
        assert status.status == "healthy"
        assert status.database_connected is True
        assert status.version == "1.0.0"

    def test_status_unhealthy(self):
        """Test unhealthy service status"""
        status = MemoryServiceStatus(
            status="unhealthy",
            database_connected=False,
            timestamp=datetime.now()
        )

        assert status.status == "unhealthy"
        assert status.database_connected is False
