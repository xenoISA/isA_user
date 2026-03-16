"""
Memory Service Models
Pydantic models for different memory types based on cognitive science
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum
import uuid


class MemoryType(str, Enum):
    """Memory types based on cognitive science"""
    FACTUAL = "factual"           # Facts and declarative knowledge
    PROCEDURAL = "procedural"     # How-to knowledge and skills
    EPISODIC = "episodic"         # Personal experiences and events
    SEMANTIC = "semantic"         # Concepts and general knowledge
    WORKING = "working"           # Temporary working memory
    SESSION = "session"           # Current session context


class MemoryModel(BaseModel):
    """Base memory model with common fields"""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User identifier")
    memory_type: MemoryType = Field(..., description="Type of memory")
    content: str = Field(..., description="Memory content")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of content")

    # Cognitive attributes
    importance_score: float = Field(0.5, ge=0.0, le=1.0, description="Importance level")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="Confidence in memory accuracy")
    access_count: int = Field(0, ge=0, description="Number of times accessed")

    # Temporal attributes
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    last_accessed_at: Optional[datetime] = None

    # Context and metadata
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    tags: List[str] = Field(default_factory=list, description="Memory tags")

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )


class FactualMemory(MemoryModel):
    """Factual memory for storing facts and declarative knowledge"""

    memory_type: Literal[MemoryType.FACTUAL] = Field(MemoryType.FACTUAL)

    # Fact structure (subject-predicate-object)
    fact_type: str = Field(..., description="Type of fact (person, place, concept, etc.)")
    subject: str = Field(..., description="What the fact is about")
    predicate: str = Field(..., description="Relationship or attribute")
    object_value: str = Field(..., description="Value or related entity")

    # Factual memory specific attributes
    fact_context: Optional[str] = Field(None, description="Additional context for the fact")
    source: Optional[str] = Field(None, description="Source of the fact")
    verification_status: str = Field("unverified", description="Verification status")
    related_facts: List[str] = Field(default_factory=list, description="Related fact IDs")

    @field_validator('content', mode='before')
    @classmethod
    def generate_content(cls, v, info):
        """Auto-generate content from fact structure"""
        if not v and info.data:
            data = info.data
            if all(k in data for k in ['subject', 'predicate', 'object_value']):
                return f"{data['subject']} {data['predicate']} {data['object_value']}"
        return v


class ProceduralMemory(MemoryModel):
    """Procedural memory for storing how-to knowledge and skills"""

    memory_type: Literal[MemoryType.PROCEDURAL] = Field(MemoryType.PROCEDURAL)

    # Procedure structure
    skill_type: str = Field(..., description="Type of skill or procedure")
    steps: List[Dict[str, Any]] = Field(..., description="Procedure steps")
    prerequisites: List[str] = Field(default_factory=list, description="Required prior knowledge")

    # Procedural memory specific attributes
    difficulty_level: str = Field("medium", description="Difficulty level")
    success_rate: float = Field(0.0, ge=0.0, le=1.0, description="Success rate when applied")
    domain: str = Field(..., description="Domain or category of procedure")


class EpisodicMemory(MemoryModel):
    """Episodic memory for storing personal experiences and events"""

    memory_type: Literal[MemoryType.EPISODIC] = Field(MemoryType.EPISODIC)

    # Episode structure
    event_type: str = Field(..., description="Type of event or experience")
    location: Optional[str] = Field(None, description="Where the event occurred")
    participants: List[str] = Field(default_factory=list, description="People involved")

    # Episodic memory specific attributes
    emotional_valence: float = Field(0.0, ge=-1.0, le=1.0, description="Emotional tone (-1 negative, 1 positive)")
    vividness: float = Field(0.5, ge=0.0, le=1.0, description="How vivid the memory is")
    episode_date: Optional[datetime] = Field(None, description="When the episode occurred")


class SemanticMemory(MemoryModel):
    """Semantic memory for storing concepts and general knowledge"""

    memory_type: Literal[MemoryType.SEMANTIC] = Field(MemoryType.SEMANTIC)

    # Concept structure
    concept_type: str = Field(..., description="Type of concept")
    definition: str = Field(..., description="Concept definition")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Concept properties")

    # Semantic memory specific attributes
    abstraction_level: str = Field("medium", description="Level of abstraction")
    related_concepts: List[str] = Field(default_factory=list, description="Related concept IDs")
    category: str = Field(..., description="Concept category")


class WorkingMemory(MemoryModel):
    """Working memory for temporary information during tasks"""

    memory_type: Literal[MemoryType.WORKING] = Field(MemoryType.WORKING)

    # Working memory structure
    task_id: str = Field(..., description="Associated task identifier")
    task_context: Dict[str, Any] = Field(..., description="Current task context")

    # Working memory specific attributes
    ttl_seconds: int = Field(3600, ge=1, description="Time to live in seconds")
    priority: int = Field(1, ge=1, le=10, description="Priority level")
    expires_at: Optional[datetime] = Field(None, description="When this memory expires")

    @field_validator('expires_at', mode='before')
    @classmethod
    def set_expiry(cls, v, info):
        """Auto-set expiry based on TTL"""
        if not v and info.data:
            data = info.data
            if 'ttl_seconds' in data and 'created_at' in data:
                from datetime import timedelta
                created_at = data.get('created_at')
                if created_at:
                    return created_at + timedelta(seconds=data['ttl_seconds'])
        return v


class SessionMemory(MemoryModel):
    """Session memory for current interaction context"""

    memory_type: Literal[MemoryType.SESSION] = Field(MemoryType.SESSION)

    # Session structure
    session_id: str = Field(..., description="Session identifier")
    interaction_sequence: int = Field(..., description="Sequence number in session")
    conversation_state: Dict[str, Any] = Field(default_factory=dict, description="Current conversation state")

    # Session memory specific attributes
    session_type: str = Field("chat", description="Type of session")
    active: bool = Field(True, description="Whether session is active")


class MemorySearchQuery(BaseModel):
    """Model for memory search queries"""

    query: str = Field(..., description="Search query text")
    memory_types: Optional[List[MemoryType]] = Field(None, description="Memory types to search")
    user_id: Optional[str] = Field(None, description="User to search for")

    # Search parameters
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")

    # Filters
    importance_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    tags: Optional[List[str]] = None


class MemorySearchResult(BaseModel):
    """Model for memory search results"""

    memory: MemoryModel = Field(..., description="Retrieved memory")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity to query")
    rank: int = Field(..., ge=1, description="Result rank")

    # Additional context
    matched_content: Optional[str] = Field(None, description="Specific content that matched")
    explanation: Optional[str] = Field(None, description="Why this result was selected")


class MemoryAssociation(BaseModel):
    """Model for memory associations"""

    source_memory_id: str = Field(..., description="Source memory ID")
    target_memory_id: str = Field(..., description="Target memory ID")
    association_type: str = Field(..., description="Type of association")
    strength: float = Field(0.5, ge=0.0, le=1.0, description="Association strength")

    created_at: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(..., description="User who owns the association")


class MemoryOperationResult(BaseModel):
    """Result of memory operations"""

    success: bool = Field(..., description="Whether operation succeeded")
    memory_id: Optional[str] = Field(None, description="ID of affected memory")
    operation: str = Field(..., description="Type of operation performed")
    message: str = Field(..., description="Result message")

    # Additional data
    data: Optional[Dict[str, Any]] = Field(None, description="Additional result data")
    affected_count: int = Field(0, description="Number of memories affected")


# Request/Response models for service operations
class MemoryCreateRequest(BaseModel):
    """Request model for creating memory"""
    model_config = {"extra": "allow"}  # Allow extra fields for memory-type-specific attributes

    user_id: str
    memory_type: MemoryType
    content: str
    embedding: Optional[List[float]] = None
    importance_score: float = 0.5
    confidence: float = 0.8
    tags: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)

    # Optional memory-type-specific fields
    session_id: Optional[str] = None
    interaction_sequence: Optional[int] = None
    ttl_minutes: Optional[int] = None
    ttl_seconds: Optional[int] = None


class MemoryUpdateRequest(BaseModel):
    """Request model for updating memory"""
    content: Optional[str] = None
    importance_score: Optional[float] = None
    confidence: Optional[float] = None
    tags: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class MemoryListParams(BaseModel):
    """Parameters for listing memories"""
    user_id: str
    memory_type: Optional[MemoryType] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    tags: Optional[List[str]] = None
    importance_min: Optional[float] = None


class DecayRequest(BaseModel):
    """Request model for running a memory decay cycle"""
    user_id: Optional[str] = Field(None, description="User ID to decay (None for global)")
    half_life_days: int = Field(30, ge=1, description="Days for importance to halve")
    floor_threshold: float = Field(0.1, ge=0.0, le=1.0, description="Below this, importance is set to 0")
    protected_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Memories at or above this are never decayed")

    @model_validator(mode="after")
    def floor_below_protected(self) -> "DecayRequest":
        if self.floor_threshold >= self.protected_threshold:
            raise ValueError(
                f"floor_threshold ({self.floor_threshold}) must be less than "
                f"protected_threshold ({self.protected_threshold})"
            )
        return self


class DecayResponse(BaseModel):
    """Response model for a decay cycle"""
    success: bool
    total_processed: int = 0
    decayed_count: int = 0
    floored_count: int = 0
    protected_count: int = 0
    skipped_count: int = 0
    message: str = ""


class ConsolidationRequest(BaseModel):
    """Request model for triggering memory consolidation"""
    user_id: Optional[str] = Field(None, description="User ID to consolidate (None for all)")
    min_access_count: int = Field(5, ge=1, description="Minimum access count for candidates")
    min_age_days: int = Field(7, ge=1, description="Minimum age in days for candidates")
    max_cluster_size: int = Field(10, ge=1, le=50, description="Maximum memories per cluster")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Embedding similarity threshold for clustering")


class ConsolidationResponse(BaseModel):
    """Response model for memory consolidation"""
    success: bool
    consolidated_count: int = 0
    new_semantic_ids: List[str] = Field(default_factory=list)
    source_episodic_ids: List[str] = Field(default_factory=list)
    message: str = ""


class HybridSearchResult(BaseModel):
    """A single result from hybrid search (vector + graph)."""
    memory_id: str = Field(..., description="Unique memory identifier")
    content: str = Field("", description="Memory content")
    memory_type: str = Field("", description="Memory type (factual, episodic, etc.)")
    final_score: float = Field(..., ge=0.0, description="Combined weighted score")
    source: Literal["vector", "graph", "both"] = Field(..., description="Which retrieval method found this result")


class HybridSearchResponse(BaseModel):
    """Response model for the hybrid search endpoint."""
    query: str = Field(..., description="Original search query")
    user_id: str = Field(..., description="User who performed the search")
    vector_weight: float = Field(..., description="Weight applied to vector results")
    graph_weight: float = Field(..., description="Weight applied to graph results")
    results: List[HybridSearchResult] = Field(default_factory=list, description="Merged results")
    total_count: int = Field(0, description="Total number of results")
    graph_available: bool = Field(True, description="Whether graph service was reachable")


class MemoryServiceStatus(BaseModel):
    """Memory service status"""
    service: str = "memory_service"
    status: str
    version: str = "1.0.0"
    database_connected: bool
    graph_connected: bool = False
    timestamp: datetime


# ==================== Graph Models ====================

class GraphEntity(BaseModel):
    """An entity node in the knowledge graph."""
    id: str = Field(..., description="Entity ID")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (e.g. technology, person)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")


class GraphNeighbor(BaseModel):
    """A neighbor entity with its relationship."""
    id: str = Field(..., description="Neighbor entity ID")
    name: str = Field(..., description="Neighbor entity name")
    type: str = Field(..., description="Neighbor entity type")
    relationship: str = Field(..., description="Relationship type to the source entity")
    depth: int = Field(1, ge=1, description="Hop distance from source entity")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")


class GraphSearchRequest(BaseModel):
    """Request model for graph entity search."""
    query: str = Field(..., description="Search query text")
    user_id: str = Field(..., description="User ID to scope results")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    max_depth: int = Field(2, ge=1, le=5, description="Maximum traversal depth")
    entity_types: Optional[List[str]] = Field(None, description="Filter by entity types")


class GraphSearchResponse(BaseModel):
    """Response model for graph entity search."""
    entities: List[GraphEntity] = Field(default_factory=list, description="Matching entities")
    total: int = Field(0, ge=0, description="Total number of matches")


class GraphNeighborsRequest(BaseModel):
    """Request model for graph neighbor lookup."""
    entity_id: str = Field(..., description="Source entity ID")
    depth: int = Field(2, ge=1, le=5, description="Maximum traversal depth")
    user_id: Optional[str] = Field(None, description="Optional user ID for scoping")
    relationship_types: Optional[List[str]] = Field(None, description="Filter by relationship types")


class GraphNeighborsResponse(BaseModel):
    """Response model for graph neighbor lookup."""
    neighbors: List[GraphNeighbor] = Field(default_factory=list, description="Neighbor entities")
    entity_id: str = Field(..., description="Source entity ID")
