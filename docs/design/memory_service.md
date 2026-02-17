# Memory Service - Design Document

## Design Overview

**Service Name**: memory_service
**Port**: 8223
**Version**: 1.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-11

### Design Principles
1. **Cognitive Science Foundation**: Memory types mirror human cognition
2. **Separation of Concerns**: Repository → Service → Orchestration → API
3. **Type Safety**: Pydantic models throughout the stack
4. **Dual Storage**: PostgreSQL (structured) + Qdrant (semantic)
5. **Event-Driven**: NATS for async communication
6. **AI-First**: LLM-powered extraction at the core

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│  (Chatbots, Apps, Workflow Systems, Analytics Services)    │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  Memory Service (Port 8223)                 │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)             │ │
│  │  - Request validation (Pydantic)                      │ │
│  │  - Response formatting                                │ │
│  │  - Error handling                                     │ │
│  │  - CORS, middleware                                   │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Orchestration Layer (memory_service.py)          │ │
│  │  - Coordinates across memory types                    │ │
│  │  - Unified API surface                                │ │
│  │  - Event publishing                                   │ │
│  │  - Statistics aggregation                             │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌────────────────────┴──────────────────────────────────┐ │
│  │         Service Layer (Type-Specific Services)        │ │
│  │                                                        │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │ │
│  │  │  Factual    │  │  Episodic   │  │ Procedural   │  │ │
│  │  │  Service    │  │  Service    │  │   Service    │  │ │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │ │
│  │  │  Semantic   │  │  Working    │  │   Session    │  │ │
│  │  │  Service    │  │  Service    │  │   Service    │  │ │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │ │
│  │                                                        │ │
│  │  Responsibilities:                                    │ │
│  │  - AI-powered extraction via ISA Model                │ │
│  │  - Business logic                                     │ │
│  │  - Data transformation                                │ │
│  │  - Embedding generation                               │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                      │
│  ┌────────────────────▼───────────────────────────────────┐ │
│  │      Repository Layer (Type-Specific Repositories)     │ │
│  │                                                         │ │
│  │  - Database CRUD operations                            │ │
│  │  - Type-specific queries                               │ │
│  │  - No business logic                                   │ │
│  │  - Uses PostgresClient (gRPC)                          │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                      │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐
│  PostgreSQL  │ │   Qdrant    │ │    NATS    │
│   (gRPC)     │ │   (Vector   │ │  (Events)  │
│              │ │    Store)   │ │            │
│  - Structured│ │  - Embeddings│ │  - Publish │
│    Data      │ │  - Semantic  │ │  - Subscribe│
│  - ACID      │ │    Search    │ │            │
└──────────────┘ └─────────────┘ └────────────┘

External Services:
┌─────────────┐
│ ISA Model   │ ← AI Extraction & Embeddings
│ (Port 8082) │
└─────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Memory Service                         │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Services  │───→│ Repositories │   │
│  │  (Pydantic) │    │ (Business)  │    │  (Data)      │   │
│  └─────────────┘    └─────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑           │
│         │                  │                    │           │
│  ┌──────┴──────────────────┴────────────────────┴───────┐  │
│  │              Orchestration Layer                      │  │
│  │              (memory_service.py)                      │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │                   Event Bus                           │  │
│  │              (events/publishers.py)                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request handling
- Request/response validation
- Route definitions
- Health checks
- CORS configuration
- Lifecycle management (startup/shutdown)

**Key Endpoints**:
```python
# AI Extraction
POST /api/v1/memories/factual/extract
POST /api/v1/memories/episodic/extract
POST /api/v1/memories/procedural/extract
POST /api/v1/memories/semantic/extract

# CRUD Operations
POST   /api/v1/memories
GET    /api/v1/memories/{memory_type}/{memory_id}
GET    /api/v1/memories
PUT    /api/v1/memories/{memory_type}/{memory_id}
DELETE /api/v1/memories/{memory_type}/{memory_id}

# Type-Specific Search
GET /api/v1/memories/factual/search/subject
GET /api/v1/memories/episodic/search/event_type
GET /api/v1/memories/semantic/search/category

# Session Management
POST /api/v1/memories/session/store
GET  /api/v1/memories/session/{session_id}
GET  /api/v1/memories/session/{session_id}/context
POST /api/v1/memories/session/{session_id}/deactivate

# Working Memory
POST /api/v1/memories/working/store
GET  /api/v1/memories/working/active
POST /api/v1/memories/working/cleanup

# Universal Search & Analytics
GET /api/v1/memories/search
GET /api/v1/memories/statistics

# Health
GET /health
```

### 2. Orchestration Layer (memory_service.py)

**Class**: `MemoryService`

**Responsibilities**:
- Route requests to appropriate service
- Coordinate cross-memory operations
- Event publishing
- Statistics aggregation
- Error handling

**Key Methods**:
```python
class MemoryService:
    # General Operations
    async def create_memory(request: MemoryCreateRequest) -> MemoryOperationResult
    async def get_memory(memory_id, memory_type, user_id) -> Optional[Dict]
    async def list_memories(params: MemoryListParams) -> List[Dict]
    async def update_memory(...) -> MemoryOperationResult
    async def delete_memory(...) -> MemoryOperationResult

    # AI-Powered Storage
    async def store_factual_memory(user_id, dialog_content, importance_score)
    async def store_episodic_memory(user_id, dialog_content, importance_score)
    async def store_procedural_memory(user_id, dialog_content, importance_score)
    async def store_semantic_memory(user_id, dialog_content, importance_score)

    # Type-Specific Search
    async def search_facts_by_subject(user_id, subject, limit)
    async def search_episodes_by_timeframe(user_id, start_date, end_date, limit)
    async def search_concepts_by_category(user_id, category, limit)

    # Working Memory
    async def get_active_working_memories(user_id)
    async def cleanup_expired_memories(user_id)

    # Session Memory
    async def get_session_memories(user_id, session_id)
    async def deactivate_session(user_id, session_id)

    # Utilities
    async def get_memory_statistics(user_id) -> Dict
    async def check_connection() -> bool
```

### 3. Service Layer (Type-Specific Services)

Each memory type has a dedicated service for business logic and AI extraction.

#### FactualMemoryService (factual_service.py)

**Responsibilities**:
- Extract facts from dialog using LLM
- Parse subject-predicate-object triples
- Generate embeddings
- Store in repository

**AI Extraction Flow**:
```python
async def store_factual_memory(user_id, dialog_content, importance_score):
    # 1. Call LLM to extract facts
    async with AsyncISAModel() as client:
        response = await client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{
                "role": "system",
                "content": "Extract facts in subject-predicate-object format..."
            }],
            response_format={"type": "json_object"}
        )

    # 2. Parse extracted facts
    facts = parse_facts_from_llm_response(response)

    # 3. Generate embeddings
    embeddings = await generate_embeddings([fact.content for fact in facts])

    # 4. Store each fact
    for fact, embedding in zip(facts, embeddings):
        fact_data = {
            "user_id": user_id,
            "subject": fact.subject,
            "predicate": fact.predicate,
            "object_value": fact.object_value,
            "content": fact.content,
            "importance_score": importance_score,
            "embedding": embedding  # Stored in Qdrant
        }
        await repository.create(fact_data)
```

#### EpisodicMemoryService (episodic_service.py)

**Extraction Focus**:
- Event type classification
- Location extraction
- Participant identification
- Emotional valence analysis (sentiment)
- Temporal information parsing

#### ProceduralMemoryService (procedural_service.py)

**Extraction Focus**:
- Step decomposition
- Prerequisite identification
- Domain classification
- Difficulty assessment

#### SemanticMemoryService (semantic_service.py)

**Extraction Focus**:
- Concept identification
- Definition extraction
- Category classification
- Property extraction

#### WorkingMemoryService (working_service.py)

**Special Features**:
- TTL management
- Expiration calculation
- Priority-based retrieval
- Automatic cleanup

#### SessionMemoryService (session_service.py)

**Special Features**:
- Interaction sequence management
- Conversation state tracking
- Session lifecycle (active/inactive)
- Context retrieval with summaries

### 4. Repository Layer (Type-Specific Repositories)

Base class: `BaseRepository` (base_repository.py)

**Common Operations**:
```python
class BaseRepository:
    async def create(data: Dict) -> Dict
    async def get_by_id(memory_id: str, user_id: str) -> Optional[Dict]
    async def list_by_user(user_id: str, limit: int, offset: int, filters: Dict) -> List[Dict]
    async def update(memory_id: str, updates: Dict, user_id: str) -> bool
    async def delete(memory_id: str, user_id: str) -> bool
    async def get_count(user_id: str) -> int
    async def increment_access_count(memory_id: str, user_id: str) -> bool
    async def check_connection() -> bool
```

**Type-Specific Methods** (e.g., FactualRepository):
```python
class FactualRepository(BaseRepository):
    async def search_by_subject(user_id: str, subject: str, limit: int) -> List[Dict]
    async def search_by_fact_type(user_id: str, fact_type: str, limit: int) -> List[Dict]
    async def get_related_facts(memory_id: str, user_id: str) -> List[Dict]
```

---

## Database Schema Design

### PostgreSQL Schema: `memory`

#### Table: memory.factual_memories
```sql
CREATE TABLE memory.factual_memories (
    -- Primary Key
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'factual',

    -- Content (NO embedding - stored in Qdrant)
    content TEXT NOT NULL,

    -- Fact Structure (SPO)
    fact_type VARCHAR(100) NOT NULL,     -- person, place, preference, skill
    subject TEXT NOT NULL,                -- What the fact is about
    predicate TEXT NOT NULL,              -- Relationship/attribute
    object_value TEXT NOT NULL,           -- Related entity/value

    -- Factual-Specific
    fact_context TEXT,                    -- Additional context
    source VARCHAR(255),                  -- Source of fact
    verification_status VARCHAR(50) DEFAULT 'unverified',
    related_facts JSONB DEFAULT '[]',     -- Array of related fact IDs

    -- Cognitive Attributes
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score BETWEEN 0 AND 1),
    confidence FLOAT DEFAULT 0.8 CHECK (confidence BETWEEN 0 AND 1),
    access_count INTEGER DEFAULT 0,

    -- Metadata
    tags JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_factual_user_id ON memory.factual_memories(user_id);
CREATE INDEX idx_factual_fact_type ON memory.factual_memories(fact_type);
CREATE INDEX idx_factual_subject_gin ON memory.factual_memories USING gin(to_tsvector('english', subject));
CREATE INDEX idx_factual_importance ON memory.factual_memories(importance_score DESC);
CREATE UNIQUE INDEX idx_factual_unique ON memory.factual_memories(user_id, subject, predicate);
```

#### Table: memory.episodic_memories
```sql
CREATE TABLE memory.episodic_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'episodic',
    content TEXT NOT NULL,

    -- Episode Structure
    event_type VARCHAR(100) NOT NULL,     -- social, work, travel, milestone
    location TEXT,                        -- Where it happened
    participants JSONB DEFAULT '[]',      -- Array of participant names

    -- Episodic-Specific
    emotional_valence FLOAT DEFAULT 0.0 CHECK (emotional_valence BETWEEN -1 AND 1),
    vividness FLOAT DEFAULT 0.5 CHECK (vividness BETWEEN 0 AND 1),
    episode_date TIMESTAMPTZ,             -- When the episode occurred

    -- Cognitive Attributes
    importance_score FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 0.8,
    access_count INTEGER DEFAULT 0,

    -- Metadata
    tags JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_episodic_user_id ON memory.episodic_memories(user_id);
CREATE INDEX idx_episodic_event_type ON memory.episodic_memories(event_type);
CREATE INDEX idx_episodic_episode_date ON memory.episodic_memories(episode_date DESC);
CREATE INDEX idx_episodic_emotional ON memory.episodic_memories(emotional_valence);
```

#### Table: memory.procedural_memories
```sql
CREATE TABLE memory.procedural_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'procedural',
    content TEXT NOT NULL,

    -- Procedure Structure
    skill_type VARCHAR(100) NOT NULL,     -- technical, personal, creative
    steps JSONB NOT NULL,                 -- Array of step objects
    prerequisites JSONB DEFAULT '[]',     -- Required prior knowledge

    -- Procedural-Specific
    difficulty_level VARCHAR(50) DEFAULT 'medium',  -- easy, medium, hard
    success_rate FLOAT DEFAULT 0.0 CHECK (success_rate BETWEEN 0 AND 1),
    domain VARCHAR(100) NOT NULL,         -- Category of procedure

    -- Cognitive Attributes
    importance_score FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 0.8,
    access_count INTEGER DEFAULT 0,

    -- Metadata
    tags JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_procedural_user_id ON memory.procedural_memories(user_id);
CREATE INDEX idx_procedural_skill_type ON memory.procedural_memories(skill_type);
CREATE INDEX idx_procedural_domain ON memory.procedural_memories(domain);
CREATE INDEX idx_procedural_difficulty ON memory.procedural_memories(difficulty_level);
```

#### Table: memory.semantic_memories
```sql
CREATE TABLE memory.semantic_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'semantic',
    content TEXT NOT NULL,

    -- Concept Structure
    concept_type VARCHAR(100) NOT NULL,   -- technical, philosophical, scientific
    definition TEXT NOT NULL,              -- Core meaning
    properties JSONB DEFAULT '{}',         -- Concept attributes

    -- Semantic-Specific
    abstraction_level VARCHAR(50) DEFAULT 'medium',  -- concrete, medium, abstract
    related_concepts JSONB DEFAULT '[]',   -- Array of related concept IDs
    category VARCHAR(100) NOT NULL,        -- Classification

    -- Cognitive Attributes
    importance_score FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 0.8,
    access_count INTEGER DEFAULT 0,

    -- Metadata
    tags JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_semantic_user_id ON memory.semantic_memories(user_id);
CREATE INDEX idx_semantic_concept_type ON memory.semantic_memories(concept_type);
CREATE INDEX idx_semantic_category ON memory.semantic_memories(category);
CREATE INDEX idx_semantic_abstraction ON memory.semantic_memories(abstraction_level);
```

#### Table: memory.working_memories
```sql
CREATE TABLE memory.working_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'working',
    content TEXT NOT NULL,

    -- Working Memory Structure
    task_id VARCHAR(255) NOT NULL,        -- Associated task
    task_context JSONB NOT NULL,          -- Current task state

    -- Working-Specific
    ttl_seconds INTEGER NOT NULL CHECK (ttl_seconds > 0),
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 10),
    expires_at TIMESTAMPTZ NOT NULL,      -- Auto-calculated from TTL

    -- Cognitive Attributes
    importance_score FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 0.8,
    access_count INTEGER DEFAULT 0,

    -- Metadata
    tags JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_working_user_id ON memory.working_memories(user_id);
CREATE INDEX idx_working_task_id ON memory.working_memories(task_id);
CREATE INDEX idx_working_expires_at ON memory.working_memories(expires_at);
CREATE INDEX idx_working_priority ON memory.working_memories(priority DESC);
```

#### Table: memory.session_memories
```sql
CREATE TABLE memory.session_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'session',
    content TEXT NOT NULL,

    -- Session Structure
    session_id VARCHAR(255) NOT NULL,     -- Session identifier
    interaction_sequence INTEGER NOT NULL, -- Message order
    conversation_state JSONB DEFAULT '{}', -- Dialogue state

    -- Session-Specific
    session_type VARCHAR(50) DEFAULT 'chat',  -- chat, task, support
    active BOOLEAN DEFAULT TRUE,           -- Session status

    -- Cognitive Attributes
    importance_score FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 0.8,
    access_count INTEGER DEFAULT 0,

    -- Metadata
    tags JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_session_user_id ON memory.session_memories(user_id);
CREATE INDEX idx_session_session_id ON memory.session_memories(session_id);
CREATE INDEX idx_session_sequence ON memory.session_memories(interaction_sequence);
CREATE INDEX idx_session_active ON memory.session_memories(active);
```

#### Additional Tables

**memory.memory_metadata**: Tracks access patterns and quality metrics
**memory.memory_associations**: Cross-memory relationships
**memory.session_summaries**: Condensed session summaries

---

## Qdrant Vector Storage Design

### Collections (One per Memory Type)

```python
collections = [
    "memory_factual",
    "memory_episodic",
    "memory_procedural",
    "memory_semantic",
    "memory_working",
    "memory_session"
]

# Collection Configuration
{
    "vectors": {
        "size": 1536,  # text-embedding-3-small dimension
        "distance": "Cosine"
    },
    "payload_schema": {
        "user_id": "keyword",
        "memory_id": "keyword",  # Same as PostgreSQL ID
        "content": "text",
        "importance_score": "float",
        "created_at": "datetime"
    }
}
```

### Synchronization Strategy

**Dual-Write Pattern**:
1. Write to PostgreSQL (structured data)
2. Write to Qdrant (embedding + metadata)
3. Use same ID in both systems

**Search Flow**:
1. Query Qdrant for semantic similarity
2. Get memory IDs from results
3. Fetch full data from PostgreSQL using IDs

---

## Event-Driven Architecture

### Event Publishing

**NATS Subjects**:
```
memory.created                      # Any memory created
memory.updated                      # Any memory updated
memory.deleted                      # Any memory deleted
memory.factual.stored               # Factual extraction complete
memory.episodic.stored              # Episodic extraction complete
memory.procedural.stored            # Procedural extraction complete
memory.semantic.stored              # Semantic extraction complete
memory.session.deactivated          # Session ended
```

### Event Models

```python
class MemoryCreatedEvent(BaseModel):
    memory_id: str
    memory_type: str
    user_id: str
    content: str
    importance_score: Optional[float]
    tags: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]
    timestamp: str  # ISO 8601

class FactualMemoryStoredEvent(BaseModel):
    user_id: str
    count: int              # Number of facts extracted
    importance_score: float
    source: str             # "dialog", "document", etc.
    timestamp: str
```

### Event Flow Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /memories/factual/extract
       ↓
┌──────────────────┐
│  Memory Service  │
│                  │
│  1. Extract      │───→ ISA Model (LLM)
│  2. Store        │───→ PostgreSQL
│  3. Publish      │───→ NATS Event Bus
└──────────────────┘
       │
       │ memory.factual.stored
       ↓
┌────────────────────────────────┐
│     Event Subscribers          │
│                                │
│  - Analytics Service           │
│  - Knowledge Graph Service     │
│  - Audit Service               │
└────────────────────────────────┘
```

---

## Data Flow Diagrams

### AI-Powered Extraction Flow

```
User Dialog
    │
    ↓
┌────────────────────┐
│  POST /extract     │
│  {dialog_content}  │
└─────────┬──────────┘
          │
          ↓
┌─────────────────────────────────┐
│  FactualMemoryService            │
│                                  │
│  1. LLM Extraction               │
│     AsyncISAModel.chat() ────────┼──→ ISA Model Service
│                                  │    (gpt-5-nano)
│  2. Parse JSON Response          │         │
│     Extract SPO triples     ←────┼─────────┘
│                                  │
│  3. Generate Embeddings          │
│     AsyncISAModel.embeddings() ──┼──→ ISA Model Service
│                                  │    (text-embedding-3-small)
│  4. Store Memories          ←────┼─────────┘
│     repository.create()          │
└──────────┬───────────────────────┘
           │
    ┌──────┴───────┐
    │              │
    ↓              ↓
┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Qdrant  │
│          │  │          │
│ Structured│  │ Embeddings│
│   Data   │  │          │
└──────────┘  └──────────┘
    │
    │ Success
    ↓
┌─────────────────────┐
│  Publish Event      │
│  NATS: factual.stored│
└─────────────────────┘
```

### Semantic Search Flow

```
User Query: "machine learning"
    │
    ↓
┌────────────────────────┐
│  GET /memories/search  │
└─────────┬──────────────┘
          │
          ↓
┌──────────────────────────────┐
│  MemoryService               │
│                              │
│  1. Generate Query Embedding │──→ ISA Model
│                              │       │
│  2. Vector Search       ←────┼───────┘
│     qdrant.search()          │
│     → Returns memory IDs     │
│                              │
│  3. Fetch Full Data          │
│     For each memory_id:      │
│       repository.get_by_id() │──→ PostgreSQL
│                              │       │
│  4. Assemble Results    ←────┼───────┘
│     - memory data            │
│     - similarity scores      │
│     - ranked by relevance    │
└──────────┬───────────────────┘
           │
           ↓
    ┌──────────────┐
    │   Response   │
    │  {results}   │
    └──────────────┘
```

### Session Context Flow

```
Chatbot Request: Get session context
    │
    ↓
┌─────────────────────────────────┐
│ GET /session/{id}/context       │
│   ?user_id=usr_123              │
│   &max_recent_messages=5        │
│   &include_summaries=true       │
└─────────┬───────────────────────┘
          │
          ↓
┌─────────────────────────────────────┐
│  SessionMemoryService                │
│                                      │
│  1. Get All Session Memories         │
│     repository.get_session_memories()│──→ PostgreSQL
│     ORDER BY interaction_sequence    │       │
│                                 ←────┼───────┘
│  2. Filter Recent N Messages         │
│     memories[-5:]                    │
│                                      │
│  3. Get Session Summary (optional)   │
│     repository.get_session_summary() │──→ PostgreSQL
│                                 ←────┼───────┘
│  4. Assemble Context                 │
│     {                                │
│       session_id,                    │
│       total_messages,                │
│       recent_messages,               │
│       summary                        │
│     }                                │
└──────────┬───────────────────────────┘
           │
           ↓
    ┌──────────────┐
    │  Response    │
    │  {context}   │
    └──────────────┘
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI**: HTTP framework
- **Pydantic**: Data validation
- **asyncio**: Async operations
- **uvicorn**: ASGI server

### Data Storage
- **PostgreSQL 15+**: Structured data storage
- **Qdrant**: Vector database for embeddings
- **PostgresClient (gRPC)**: Database communication

### AI/ML
- **ISA Model Service**: LLM inference and embeddings
- **Models**:
  - gpt-5-nano: Extraction
  - text-embedding-3-small: Embeddings (1536 dimensions)

### Event-Driven
- **NATS**: Event bus for pub/sub
- **Event Types**: memory.*, memory.factual.*, etc.

### Service Discovery
- **Consul**: Service registration and discovery
- **Health Checks**: HTTP health endpoint

### Observability
- **Structured Logging**: JSON format
- **Metrics**: Prometheus-compatible (future)
- **Tracing**: Request correlation IDs

---

## Security Considerations

### Input Validation
- **Pydantic Models**: Validate all inputs
- **SQL Injection**: Use parameterized queries (gRPC handles this)
- **XSS Prevention**: Sanitize content before storage

### Access Control
- **User Isolation**: All queries filtered by user_id
- **Authorization**: Future: JWT-based authentication
- **RBAC**: Future: Role-based access control

### Data Privacy
- **GDPR Compliance**: Support for data deletion
- **Encryption in Transit**: TLS for all external communication
- **Encryption at Rest**: Future: Database encryption

### Rate Limiting
- **API Rate Limits**: 1000 req/hour per user
- **Burst Protection**: 100 req/minute
- **DDoS Protection**: Future: WAF integration

---

## Performance Optimization

### Caching Strategy
- **Memory Cache**: Frequently accessed memories (Redis - future)
- **Query Cache**: Common search queries
- **TTL**: 5-60 minutes depending on data type

### Database Optimization
- **Indexes**: Strategic indexes on search columns
- **Connection Pooling**: gRPC connection pool
- **Query Optimization**: Avoid N+1 queries

### Vector Search Optimization
- **HNSW Algorithm**: Qdrant's efficient nearest-neighbor search
- **Batch Embedding**: Generate embeddings in batches
- **Filtering**: Pre-filter by user_id before vector search

---

## Error Handling

### Error Response Format
```json
{
  "success": false,
  "operation": "create_memory",
  "message": "Validation error: content field required",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {...}
  }
}
```

### Error Codes
- `VALIDATION_ERROR`: Input validation failed
- `NOT_FOUND`: Resource not found
- `DATABASE_ERROR`: Database operation failed
- `AI_SERVICE_ERROR`: ISA Model service unavailable
- `INTERNAL_ERROR`: Unexpected server error

---

## Testing Strategy

### Contract Testing
- **Data Contracts**: Pydantic schema validation
- **Logic Contracts**: Business rule validation
- **API Contracts**: OpenAPI schema validation

### Component Testing
- **Repository Tests**: Database operations
- **Service Tests**: Business logic
- **API Tests**: HTTP endpoints

### Integration Testing
- **End-to-End Tests**: Full extraction + storage + retrieval
- **Event Tests**: Event publishing and handling
- **Database Tests**: Migration validation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-11
**Maintained By**: Memory Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/memory_service.md
- PRD: docs/prd/memory_service.md
- Data Contract: tests/contracts/memory/data_contract.py (next)
- Logic Contract: tests/contracts/memory/logic_contract.md (next)
