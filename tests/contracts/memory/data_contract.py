"""
Memory Service Data Contract

Defines all request/response schemas and test data factories for memory service.
This contract ensures consistent data structures across the service and enables
zero-hardcoded-data testing with factory-generated test data.

Contract Layers:
1. Request/Response Schemas (Pydantic models)
2. Test Data Factory (generates consistent test data)
3. Request Builders (fluent API for complex requests)

Related Documents:
- Domain Context: docs/domain/memory_service.md
- PRD: docs/prd/memory_service.md
- Design: docs/design/memory_service.md
- Logic Contract: tests/contracts/memory/logic_contract.md
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator
import uuid
import random


# ===================================================================================
# SECTION 1: REQUEST SCHEMAS
# ===================================================================================

class ExtractFactualMemoryRequest(BaseModel):
    """Request schema for AI-powered factual memory extraction"""
    user_id: str = Field(..., min_length=1, description="User identifier")
    dialog_content: str = Field(..., min_length=1, description="Dialog to extract facts from")
    importance_score: float = Field(0.5, ge=0.0, le=1.0, description="Importance level")


class ExtractEpisodicMemoryRequest(BaseModel):
    """Request schema for AI-powered episodic memory extraction"""
    user_id: str = Field(..., min_length=1, description="User identifier")
    dialog_content: str = Field(..., min_length=1, description="Dialog to extract episodes from")
    importance_score: float = Field(0.5, ge=0.0, le=1.0, description="Importance level")


class ExtractProceduralMemoryRequest(BaseModel):
    """Request schema for AI-powered procedural memory extraction"""
    user_id: str = Field(..., min_length=1, description="User identifier")
    dialog_content: str = Field(..., min_length=1, description="Dialog to extract procedures from")
    importance_score: float = Field(0.5, ge=0.0, le=1.0, description="Importance level")


class ExtractSemanticMemoryRequest(BaseModel):
    """Request schema for AI-powered semantic memory extraction"""
    user_id: str = Field(..., min_length=1, description="User identifier")
    dialog_content: str = Field(..., min_length=1, description="Dialog to extract concepts from")
    importance_score: float = Field(0.5, ge=0.0, le=1.0, description="Importance level")


class CreateMemoryRequest(BaseModel):
    """Request schema for creating a memory with explicit data"""
    user_id: str = Field(..., min_length=1)
    memory_type: Literal["factual", "episodic", "procedural", "semantic", "working", "session"]
    content: str = Field(..., min_length=1)
    importance_score: float = Field(0.5, ge=0.0, le=1.0)
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)

    # Type-specific fields (optional)
    # Factual
    fact_type: Optional[str] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object_value: Optional[str] = None

    # Episodic
    event_type: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = None
    emotional_valence: Optional[float] = Field(None, ge=-1.0, le=1.0)
    vividness: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Procedural
    skill_type: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    domain: Optional[str] = None

    # Semantic
    concept_type: Optional[str] = None
    definition: Optional[str] = None
    category: Optional[str] = None

    # Working
    task_id: Optional[str] = None
    task_context: Optional[Dict[str, Any]] = None
    ttl_seconds: Optional[int] = Field(None, gt=0)

    # Session
    session_id: Optional[str] = None
    interaction_sequence: Optional[int] = Field(None, gt=0)


class UpdateMemoryRequest(BaseModel):
    """Request schema for updating a memory"""
    content: Optional[str] = Field(None, min_length=1)
    importance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class StoreSessionMessageRequest(BaseModel):
    """Request schema for storing session message"""
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    message_content: str = Field(..., min_length=1)
    message_type: str = Field("human", pattern="^(human|ai|system)$")
    role: str = Field("user", pattern="^(user|assistant|system)$")


class StoreWorkingMemoryRequest(BaseModel):
    """Request schema for storing working memory"""
    user_id: str = Field(..., min_length=1)
    dialog_content: str = Field(..., min_length=1)
    ttl_seconds: int = Field(3600, gt=0, description="Time to live in seconds")
    importance_score: float = Field(0.5, ge=0.0, le=1.0)


# ===================================================================================
# SECTION 2: RESPONSE SCHEMAS
# ===================================================================================

class MemoryOperationResult(BaseModel):
    """Response schema for memory operations"""
    success: bool = Field(..., description="Operation success status")
    operation: str = Field(..., description="Type of operation performed")
    message: str = Field(..., description="Result message")
    memory_id: Optional[str] = Field(None, description="ID of affected memory")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional result data")
    affected_count: int = Field(0, description="Number of memories affected")


class MemoryResponse(BaseModel):
    """Response schema for single memory"""
    id: str
    user_id: str
    memory_type: str
    content: str
    importance_score: float
    confidence: float
    access_count: int
    tags: List[str]
    context: Dict[str, Any]
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    last_accessed_at: Optional[str]  # ISO 8601

    # Type-specific fields returned conditionally
    # Factual
    fact_type: Optional[str] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object_value: Optional[str] = None

    # Episodic
    event_type: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = None
    emotional_valence: Optional[float] = None
    vividness: Optional[float] = None
    episode_date: Optional[str] = None  # ISO 8601

    # Procedural
    skill_type: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    domain: Optional[str] = None

    # Semantic
    concept_type: Optional[str] = None
    definition: Optional[str] = None
    category: Optional[str] = None

    # Working
    task_id: Optional[str] = None
    task_context: Optional[Dict[str, Any]] = None
    ttl_seconds: Optional[int] = None
    expires_at: Optional[str] = None  # ISO 8601

    # Session
    session_id: Optional[str] = None
    interaction_sequence: Optional[int] = None
    conversation_state: Optional[Dict[str, Any]] = None


class MemoryListResponse(BaseModel):
    """Response schema for memory list"""
    memories: List[MemoryResponse]
    count: int


class MemoryStatisticsResponse(BaseModel):
    """Response schema for memory statistics"""
    user_id: str
    total_memories: int
    by_type: Dict[str, int]
    timestamp: str  # ISO 8601


class SessionContextResponse(BaseModel):
    """Response schema for session context"""
    session_id: str
    user_id: str
    total_messages: int
    recent_messages: List[MemoryResponse]
    summary: Optional[Dict[str, Any]] = None


class UniversalSearchResponse(BaseModel):
    """Response schema for universal search"""
    query: str
    user_id: str
    searched_types: List[str]
    results: Dict[str, List[MemoryResponse]]
    total_count: int


# ===================================================================================
# SECTION 3: TEST DATA FACTORY
# ===================================================================================

class MemoryTestDataFactory:
    """
    Test data factory for memory service.

    Generates consistent, valid test data for all memory types.
    Zero hardcoded data - all test data generated dynamically.

    Usage:
        factory = MemoryTestDataFactory()
        factual_req = factory.factual_extract_request()
        episodic_req = factory.episodic_extract_request()
    """

    def __init__(self, seed: Optional[int] = None):
        """Initialize factory with optional seed for reproducibility"""
        self.seed = seed
        if seed:
            random.seed(seed)

        # Counter for unique IDs
        self._counter = 0

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID with prefix"""
        self._counter += 1
        return f"{prefix}_{self._counter:04d}"

    def _generate_user_id(self) -> str:
        """Generate test user ID"""
        return self._generate_id("usr")

    def _generate_memory_id(self, memory_type: str) -> str:
        """Generate test memory ID"""
        prefix_map = {
            "factual": "fact",
            "episodic": "epis",
            "procedural": "proc",
            "semantic": "sem",
            "working": "work",
            "session": "sess"
        }
        prefix = prefix_map.get(memory_type, "mem")
        return self._generate_id(prefix)

    def _generate_session_id(self) -> str:
        """Generate test session ID"""
        return self._generate_id("session")

    def _generate_task_id(self) -> str:
        """Generate test task ID"""
        return self._generate_id("task")

    # ==================== Factual Memory ====================

    def factual_extract_request(
        self,
        user_id: Optional[str] = None,
        dialog_content: Optional[str] = None,
        importance_score: float = 0.7
    ) -> ExtractFactualMemoryRequest:
        """Generate factual memory extraction request"""
        return ExtractFactualMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            dialog_content=dialog_content or "John lives in Tokyo and works as a software engineer at Apple. He prefers dark mode.",
            importance_score=importance_score
        )

    def create_factual_memory_request(
        self,
        user_id: Optional[str] = None,
        subject: str = "John",
        predicate: str = "lives in",
        object_value: str = "Tokyo",
        importance_score: float = 0.7
    ) -> CreateMemoryRequest:
        """Generate create factual memory request"""
        return CreateMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            memory_type="factual",
            content=f"{subject} {predicate} {object_value}",
            fact_type="person_location",
            subject=subject,
            predicate=predicate,
            object_value=object_value,
            importance_score=importance_score,
            confidence=0.9,
            tags=["fact", "personal"],
            context={"source": "test"}
        )

    def factual_memory_response(
        self,
        user_id: Optional[str] = None,
        subject: str = "John",
        predicate: str = "lives in",
        object_value: str = "Tokyo"
    ) -> MemoryResponse:
        """Generate factual memory response"""
        memory_id = self._generate_memory_id("factual")
        now = datetime.now(timezone.utc).isoformat()
        return MemoryResponse(
            id=memory_id,
            user_id=user_id or self._generate_user_id(),
            memory_type="factual",
            content=f"{subject} {predicate} {object_value}",
            importance_score=0.7,
            confidence=0.9,
            access_count=0,
            tags=["fact", "personal"],
            context={"source": "test"},
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
            fact_type="person_location",
            subject=subject,
            predicate=predicate,
            object_value=object_value
        )

    # ==================== Episodic Memory ====================

    def episodic_extract_request(
        self,
        user_id: Optional[str] = None,
        dialog_content: Optional[str] = None,
        importance_score: float = 0.8
    ) -> ExtractEpisodicMemoryRequest:
        """Generate episodic memory extraction request"""
        return ExtractEpisodicMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            dialog_content=dialog_content or "Last weekend I went hiking in Yosemite with Tom and Lisa. The views were breathtaking!",
            importance_score=importance_score
        )

    def create_episodic_memory_request(
        self,
        user_id: Optional[str] = None,
        event_type: str = "outdoor_activity",
        location: str = "Yosemite",
        participants: Optional[List[str]] = None,
        emotional_valence: float = 0.9
    ) -> CreateMemoryRequest:
        """Generate create episodic memory request"""
        return CreateMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            memory_type="episodic",
            content="Went hiking in Yosemite with friends. Amazing experience!",
            event_type=event_type,
            location=location,
            participants=participants or ["Tom", "Lisa"],
            emotional_valence=emotional_valence,
            vividness=0.85,
            importance_score=0.8,
            confidence=0.9,
            tags=["outdoor", "social"],
            context={"weather": "sunny", "duration_hours": 6}
        )

    def episodic_memory_response(
        self,
        user_id: Optional[str] = None,
        event_type: str = "outdoor_activity",
        location: str = "Yosemite"
    ) -> MemoryResponse:
        """Generate episodic memory response"""
        memory_id = self._generate_memory_id("episodic")
        now = datetime.now(timezone.utc).isoformat()
        episode_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        return MemoryResponse(
            id=memory_id,
            user_id=user_id or self._generate_user_id(),
            memory_type="episodic",
            content="Went hiking in Yosemite with friends. Amazing experience!",
            importance_score=0.8,
            confidence=0.9,
            access_count=0,
            tags=["outdoor", "social"],
            context={"weather": "sunny"},
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
            event_type=event_type,
            location=location,
            participants=["Tom", "Lisa"],
            emotional_valence=0.9,
            vividness=0.85,
            episode_date=episode_date
        )

    # ==================== Procedural Memory ====================

    def procedural_extract_request(
        self,
        user_id: Optional[str] = None,
        dialog_content: Optional[str] = None,
        importance_score: float = 0.6
    ) -> ExtractProceduralMemoryRequest:
        """Generate procedural memory extraction request"""
        return ExtractProceduralMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            dialog_content=dialog_content or "To deploy, first run tests, then build Docker image, push to registry, and finally update k8s deployment",
            importance_score=importance_score
        )

    def create_procedural_memory_request(
        self,
        user_id: Optional[str] = None,
        skill_type: str = "deployment",
        domain: str = "devops"
    ) -> CreateMemoryRequest:
        """Generate create procedural memory request"""
        steps = [
            {"step": 1, "action": "run tests", "command": "pytest"},
            {"step": 2, "action": "build Docker image", "command": "docker build -t app:latest ."},
            {"step": 3, "action": "push to registry", "command": "docker push app:latest"},
            {"step": 4, "action": "update k8s", "command": "kubectl apply -f deployment.yaml"}
        ]
        return CreateMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            memory_type="procedural",
            content="Deployment procedure for microservices",
            skill_type=skill_type,
            steps=steps,
            domain=domain,
            importance_score=0.6,
            confidence=0.85,
            tags=["deployment", "devops"],
            context={"environment": "production"}
        )

    def procedural_memory_response(
        self,
        user_id: Optional[str] = None,
        skill_type: str = "deployment",
        domain: str = "devops"
    ) -> MemoryResponse:
        """Generate procedural memory response"""
        memory_id = self._generate_memory_id("procedural")
        now = datetime.now(timezone.utc).isoformat()
        steps = [
            {"step": 1, "action": "run tests"},
            {"step": 2, "action": "build Docker image"},
            {"step": 3, "action": "push to registry"},
            {"step": 4, "action": "update k8s"}
        ]
        return MemoryResponse(
            id=memory_id,
            user_id=user_id or self._generate_user_id(),
            memory_type="procedural",
            content="Deployment procedure for microservices",
            importance_score=0.6,
            confidence=0.85,
            access_count=0,
            tags=["deployment", "devops"],
            context={"environment": "production"},
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
            skill_type=skill_type,
            steps=steps,
            domain=domain
        )

    # ==================== Semantic Memory ====================

    def semantic_extract_request(
        self,
        user_id: Optional[str] = None,
        dialog_content: Optional[str] = None,
        importance_score: float = 0.65
    ) -> ExtractSemanticMemoryRequest:
        """Generate semantic memory extraction request"""
        return ExtractSemanticMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            dialog_content=dialog_content or "Machine learning is a subset of artificial intelligence that enables systems to learn from data",
            importance_score=importance_score
        )

    def create_semantic_memory_request(
        self,
        user_id: Optional[str] = None,
        concept_type: str = "technical",
        category: str = "artificial_intelligence"
    ) -> CreateMemoryRequest:
        """Generate create semantic memory request"""
        return CreateMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            memory_type="semantic",
            content="Machine learning is a subset of AI",
            concept_type=concept_type,
            definition="A subset of AI that enables systems to learn from data without explicit programming",
            category=category,
            importance_score=0.65,
            confidence=0.9,
            tags=["ai", "ml", "technical"],
            context={"abstraction_level": "medium"}
        )

    def semantic_memory_response(
        self,
        user_id: Optional[str] = None,
        concept_type: str = "technical",
        category: str = "artificial_intelligence"
    ) -> MemoryResponse:
        """Generate semantic memory response"""
        memory_id = self._generate_memory_id("semantic")
        now = datetime.now(timezone.utc).isoformat()
        return MemoryResponse(
            id=memory_id,
            user_id=user_id or self._generate_user_id(),
            memory_type="semantic",
            content="Machine learning is a subset of AI",
            importance_score=0.65,
            confidence=0.9,
            access_count=0,
            tags=["ai", "ml", "technical"],
            context={"abstraction_level": "medium"},
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
            concept_type=concept_type,
            definition="A subset of AI that enables systems to learn from data",
            category=category
        )

    # ==================== Working Memory ====================

    def working_memory_store_request(
        self,
        user_id: Optional[str] = None,
        dialog_content: str = "Analyzing 10 files for security issues",
        ttl_seconds: int = 3600
    ) -> StoreWorkingMemoryRequest:
        """Generate working memory store request"""
        return StoreWorkingMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            dialog_content=dialog_content,
            ttl_seconds=ttl_seconds,
            importance_score=0.7
        )

    def create_working_memory_request(
        self,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        ttl_seconds: int = 3600
    ) -> CreateMemoryRequest:
        """Generate create working memory request"""
        task_id = task_id or self._generate_task_id()
        task_context = {
            "files_to_analyze": 10,
            "current_file": 1,
            "issues_found": 0
        }
        return CreateMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            memory_type="working",
            content="Security analysis task in progress",
            task_id=task_id,
            task_context=task_context,
            ttl_seconds=ttl_seconds,
            importance_score=0.7,
            confidence=0.95,
            tags=["task", "security"],
            context={"priority": 8}
        )

    def working_memory_response(
        self,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        ttl_seconds: int = 3600
    ) -> MemoryResponse:
        """Generate working memory response"""
        memory_id = self._generate_memory_id("working")
        task_id = task_id or self._generate_task_id()
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        return MemoryResponse(
            id=memory_id,
            user_id=user_id or self._generate_user_id(),
            memory_type="working",
            content="Security analysis task in progress",
            importance_score=0.7,
            confidence=0.95,
            access_count=0,
            tags=["task", "security"],
            context={"priority": 8},
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            last_accessed_at=None,
            task_id=task_id,
            task_context={"files_to_analyze": 10},
            ttl_seconds=ttl_seconds,
            expires_at=expires_at
        )

    # ==================== Session Memory ====================

    def session_message_store_request(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        message_content: str = "What's the weather like today?",
        message_type: str = "human",
        role: str = "user"
    ) -> StoreSessionMessageRequest:
        """Generate session message store request"""
        return StoreSessionMessageRequest(
            user_id=user_id or self._generate_user_id(),
            session_id=session_id or self._generate_session_id(),
            message_content=message_content,
            message_type=message_type,
            role=role
        )

    def create_session_memory_request(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        interaction_sequence: int = 1
    ) -> CreateMemoryRequest:
        """Generate create session memory request"""
        conversation_state = {
            "message_type": "human",
            "role": "user",
            "sequence": interaction_sequence
        }
        return CreateMemoryRequest(
            user_id=user_id or self._generate_user_id(),
            memory_type="session",
            content="What's the weather like today?",
            session_id=session_id or self._generate_session_id(),
            interaction_sequence=interaction_sequence,
            importance_score=0.5,
            confidence=1.0,
            tags=["conversation"],
            context={"conversation_state": conversation_state}
        )

    def session_memory_response(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        interaction_sequence: int = 1
    ) -> MemoryResponse:
        """Generate session memory response"""
        memory_id = self._generate_memory_id("session")
        now = datetime.now(timezone.utc).isoformat()
        return MemoryResponse(
            id=memory_id,
            user_id=user_id or self._generate_user_id(),
            memory_type="session",
            content="What's the weather like today?",
            importance_score=0.5,
            confidence=1.0,
            access_count=0,
            tags=["conversation"],
            context={},
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
            session_id=session_id or self._generate_session_id(),
            interaction_sequence=interaction_sequence,
            conversation_state={"message_type": "human", "role": "user"}
        )

    # ==================== Operation Results ====================

    def memory_operation_result(
        self,
        success: bool = True,
        operation: str = "create",
        message: str = "Memory created successfully",
        memory_id: Optional[str] = None,
        affected_count: int = 1
    ) -> MemoryOperationResult:
        """Generate memory operation result"""
        return MemoryOperationResult(
            success=success,
            operation=operation,
            message=message,
            memory_id=memory_id or self._generate_memory_id("factual"),
            data={"status": "completed"},
            affected_count=affected_count
        )

    # ==================== Lists and Statistics ====================

    def memory_list_response(
        self,
        user_id: Optional[str] = None,
        memory_type: str = "factual",
        count: int = 3
    ) -> MemoryListResponse:
        """Generate memory list response"""
        user_id = user_id or self._generate_user_id()
        memories = []

        for i in range(count):
            if memory_type == "factual":
                memories.append(self.factual_memory_response(user_id=user_id))
            elif memory_type == "episodic":
                memories.append(self.episodic_memory_response(user_id=user_id))
            elif memory_type == "procedural":
                memories.append(self.procedural_memory_response(user_id=user_id))
            elif memory_type == "semantic":
                memories.append(self.semantic_memory_response(user_id=user_id))
            elif memory_type == "working":
                memories.append(self.working_memory_response(user_id=user_id))
            elif memory_type == "session":
                memories.append(self.session_memory_response(user_id=user_id))

        return MemoryListResponse(memories=memories, count=len(memories))

    def memory_statistics_response(
        self,
        user_id: Optional[str] = None
    ) -> MemoryStatisticsResponse:
        """Generate memory statistics response"""
        return MemoryStatisticsResponse(
            user_id=user_id or self._generate_user_id(),
            total_memories=150,
            by_type={
                "factual": 60,
                "episodic": 35,
                "procedural": 15,
                "semantic": 25,
                "working": 5,
                "session": 10
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )


# ===================================================================================
# SECTION 4: REQUEST BUILDERS
# ===================================================================================

class FactualMemoryRequestBuilder:
    """Fluent builder for factual memory requests"""

    def __init__(self):
        self._user_id: Optional[str] = None
        self._subject: str = "John"
        self._predicate: str = "lives in"
        self._object_value: str = "Tokyo"
        self._importance_score: float = 0.7
        self._fact_type: str = "person_location"
        self._tags: List[str] = []

    def for_user(self, user_id: str) -> "FactualMemoryRequestBuilder":
        self._user_id = user_id
        return self

    def with_fact(self, subject: str, predicate: str, object_value: str) -> "FactualMemoryRequestBuilder":
        self._subject = subject
        self._predicate = predicate
        self._object_value = object_value
        return self

    def with_importance(self, score: float) -> "FactualMemoryRequestBuilder":
        self._importance_score = score
        return self

    def with_fact_type(self, fact_type: str) -> "FactualMemoryRequestBuilder":
        self._fact_type = fact_type
        return self

    def with_tags(self, tags: List[str]) -> "FactualMemoryRequestBuilder":
        self._tags = tags
        return self

    def build(self) -> CreateMemoryRequest:
        factory = MemoryTestDataFactory()
        return CreateMemoryRequest(
            user_id=self._user_id or factory._generate_user_id(),
            memory_type="factual",
            content=f"{self._subject} {self._predicate} {self._object_value}",
            fact_type=self._fact_type,
            subject=self._subject,
            predicate=self._predicate,
            object_value=self._object_value,
            importance_score=self._importance_score,
            confidence=0.9,
            tags=self._tags if self._tags else ["fact"],
            context={"source": "builder"}
        )


class SessionMemoryRequestBuilder:
    """Fluent builder for session memory requests"""

    def __init__(self):
        self._user_id: Optional[str] = None
        self._session_id: Optional[str] = None
        self._messages: List[Dict[str, str]] = []

    def for_user(self, user_id: str) -> "SessionMemoryRequestBuilder":
        self._user_id = user_id
        return self

    def with_session(self, session_id: str) -> "SessionMemoryRequestBuilder":
        self._session_id = session_id
        return self

    def add_message(self, content: str, message_type: str = "human", role: str = "user") -> "SessionMemoryRequestBuilder":
        self._messages.append({
            "content": content,
            "message_type": message_type,
            "role": role
        })
        return self

    def build_messages(self) -> List[CreateMemoryRequest]:
        """Build multiple session memory requests"""
        factory = MemoryTestDataFactory()
        user_id = self._user_id or factory._generate_user_id()
        session_id = self._session_id or factory._generate_session_id()

        requests = []
        for i, msg in enumerate(self._messages, start=1):
            conversation_state = {
                "message_type": msg["message_type"],
                "role": msg["role"],
                "sequence": i
            }
            requests.append(CreateMemoryRequest(
                user_id=user_id,
                memory_type="session",
                content=msg["content"],
                session_id=session_id,
                interaction_sequence=i,
                importance_score=0.5,
                confidence=1.0,
                tags=["conversation"],
                context={"conversation_state": conversation_state}
            ))

        return requests


# ===================================================================================
# EXPORTS
# ===================================================================================

__all__ = [
    # Request Schemas
    "ExtractFactualMemoryRequest",
    "ExtractEpisodicMemoryRequest",
    "ExtractProceduralMemoryRequest",
    "ExtractSemanticMemoryRequest",
    "CreateMemoryRequest",
    "UpdateMemoryRequest",
    "StoreSessionMessageRequest",
    "StoreWorkingMemoryRequest",

    # Response Schemas
    "MemoryOperationResult",
    "MemoryResponse",
    "MemoryListResponse",
    "MemoryStatisticsResponse",
    "SessionContextResponse",
    "UniversalSearchResponse",

    # Factory
    "MemoryTestDataFactory",

    # Builders
    "FactualMemoryRequestBuilder",
    "SessionMemoryRequestBuilder",
]
