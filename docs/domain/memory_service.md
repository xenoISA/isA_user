# Memory Service - Domain Context

## Overview

The Memory Service is an AI-powered cognitive memory system based on cognitive science principles. It provides intelligent storage, retrieval, and management of different types of human-like memory for AI assistants and applications.

**Business Context**: Enable AI systems to maintain persistent, contextual understanding of users by storing and retrieving information in cognitively-structured memory types that mirror how humans process and recall information.

**Core Value Proposition**: Transform conversational AI from stateless interactions into contextually-aware experiences by providing human-like memory capabilities with AI-powered extraction and semantic search.

---

## Business Taxonomy

### Memory Types (Based on Cognitive Science)

#### 1. Factual Memory
**Definition**: Stores declarative knowledge and facts in structured subject-predicate-object format.

**Business Purpose**:
- Remember facts about users, preferences, relationships
- Track entity attributes and relationships
- Build knowledge graphs from conversations

**Examples**:
- "John lives in Tokyo"
- "User prefers dark mode"
- "Sarah works at Google"

**Key Attributes**:
- Subject (what/who the fact is about)
- Predicate (relationship/attribute)
- Object Value (related entity/value)
- Verification Status (unverified, verified, disputed)
- Fact Type (person, place, preference, skill, etc.)

#### 2. Episodic Memory
**Definition**: Stores personal experiences and events with temporal and spatial context.

**Business Purpose**:
- Remember significant user experiences
- Track life events and milestones
- Provide contextual recommendations based on past experiences

**Examples**:
- "Yesterday I went to the beach with Sarah"
- "Last week I completed my first marathon"
- "My birthday party in 2024 was amazing"

**Key Attributes**:
- Event Type (social, work, personal, etc.)
- Location (where it happened)
- Participants (who was involved)
- Episode Date (when it occurred)
- Emotional Valence (-1.0 negative to 1.0 positive)
- Vividness (how clear the memory is)

#### 3. Procedural Memory
**Definition**: Stores how-to knowledge, skills, and step-by-step procedures.

**Business Purpose**:
- Remember user workflows and processes
- Track learned skills and abilities
- Provide procedural guidance

**Examples**:
- "How to make coffee with French press"
- "Steps for deploying to production"
- "My morning routine"

**Key Attributes**:
- Skill Type (technical, personal, creative, etc.)
- Steps (ordered sequence of actions)
- Prerequisites (required prior knowledge)
- Difficulty Level (easy, medium, hard)
- Success Rate (0.0 to 1.0)
- Domain (category of procedure)

#### 4. Semantic Memory
**Definition**: Stores concepts, definitions, and general knowledge independent of personal experience.

**Business Purpose**:
- Build concept understanding
- Store abstract knowledge
- Create semantic relationships

**Examples**:
- "Recursion is a programming technique"
- "Democracy is a system of government"
- "Photosynthesis converts light to energy"

**Key Attributes**:
- Concept Type (technical, philosophical, scientific, etc.)
- Definition (core meaning)
- Properties (attributes of the concept)
- Category (classification)
- Abstraction Level (concrete, medium, abstract)
- Related Concepts (semantic relationships)

#### 5. Working Memory
**Definition**: Stores temporary information needed for ongoing tasks with time-to-live.

**Business Purpose**:
- Maintain task context during execution
- Track temporary state
- Enable multi-step workflows

**Examples**:
- "Current file being edited: config.yaml"
- "Calculation in progress: sum = 1245"
- "User is reviewing PR #423"

**Key Attributes**:
- Task ID (associated task identifier)
- Task Context (current state)
- TTL Seconds (time to live)
- Expires At (expiration timestamp)
- Priority (1-10, for memory management)

#### 6. Session Memory
**Definition**: Stores conversation context and interaction history for active sessions.

**Business Purpose**:
- Maintain conversation context
- Track interaction sequences
- Enable coherent multi-turn conversations

**Examples**:
- "User asked about weather in Tokyo"
- "Discussed deployment strategy for microservices"
- "Requested code review for PR #123"

**Key Attributes**:
- Session ID (unique session identifier)
- Interaction Sequence (message order number)
- Conversation State (current dialogue state)
- Session Type (chat, task, support, etc.)
- Active (whether session is ongoing)

---

## Domain Scenarios

### Scenario 1: AI-Powered Fact Extraction
**Actor**: AI Assistant, User
**Trigger**: User shares information in conversation
**Flow**:
1. User says: "I live in San Francisco and work as a software engineer at Apple"
2. Memory Service receives dialog content
3. AI extraction service analyzes content using LLM
4. Extracts multiple facts:
   - Subject: "User", Predicate: "lives in", Object: "San Francisco"
   - Subject: "User", Predicate: "works as", Object: "software engineer"
   - Subject: "User", Predicate: "works at", Object: "Apple"
5. Stores each fact as factual memory
6. Generates embeddings for semantic search
7. Publishes `factual_memory.stored` event
**Outcome**: Multiple structured facts stored, searchable, and available for future recall

### Scenario 2: Episodic Memory for Life Events
**Actor**: User, AI Assistant
**Trigger**: User shares personal experience
**Flow**:
1. User: "Last weekend I went hiking in Yosemite with Tom and Lisa. The views were breathtaking!"
2. AI extraction identifies episodic content
3. Extracts episodic attributes:
   - Event Type: "outdoor_activity"
   - Location: "Yosemite"
   - Participants: ["Tom", "Lisa"]
   - Emotional Valence: 0.9 (very positive)
   - Episode Date: Last weekend timestamp
4. Stores episodic memory with full context
5. Memory becomes searchable by timeframe, location, participants
**Outcome**: Rich personal experience stored for future context and recommendations

### Scenario 3: Procedural Memory for Workflows
**Actor**: Developer, AI Assistant
**Trigger**: User shares workflow process
**Flow**:
1. User explains: "To deploy, first run tests, then build Docker image, push to registry, and finally update k8s deployment"
2. AI extraction identifies procedural pattern
3. Extracts procedure structure:
   - Skill Type: "deployment"
   - Domain: "devops"
   - Steps: [
       {"step": 1, "action": "run tests", "command": "pytest"},
       {"step": 2, "action": "build Docker image", "command": "docker build"},
       {"step": 3, "action": "push to registry", "command": "docker push"},
       {"step": 4, "action": "update k8s", "command": "kubectl apply"}
     ]
4. Stores procedural memory
5. Future queries like "how do I deploy?" retrieve this procedure
**Outcome**: Reusable workflow knowledge stored for future execution

### Scenario 4: Working Memory for Task Context
**Actor**: AI Assistant, Task Execution System
**Trigger**: Multi-step task begins
**Flow**:
1. User starts task: "Analyze these 10 files for security issues"
2. System creates working memory:
   - Task ID: task_12345
   - Task Context: {"files_to_analyze": 10, "current_file": 1, "issues_found": 0}
   - TTL: 3600 seconds (1 hour)
   - Priority: 8
3. As task progresses, working memory updates
4. After completion or expiration, memory cleaned up
**Outcome**: Task state maintained during execution, automatically cleaned up

### Scenario 5: Session Memory for Conversations
**Actor**: User, Chatbot
**Trigger**: Conversation begins
**Flow**:
1. User starts new chat session (session_id: sess_abc123)
2. Each message stored as session memory:
   - Interaction 1: User asks "What's the weather?"
   - Interaction 2: Bot responds with weather data
   - Interaction 3: User asks "Should I bring an umbrella?"
3. Bot retrieves session context (recent messages)
4. Provides contextual response referencing previous weather info
5. Session deactivated after 30 minutes of inactivity
**Outcome**: Coherent multi-turn conversation with context retention

### Scenario 6: Semantic Search Across Memories
**Actor**: User, Search System
**Trigger**: User searches for information
**Flow**:
1. User queries: "What do I know about machine learning?"
2. System generates embedding for query
3. Searches across all memory types using Qdrant
4. Returns relevant memories:
   - Factual: "I'm learning PyTorch"
   - Episodic: "Attended ML conference last month"
   - Procedural: "How to train neural networks"
   - Semantic: "Machine learning is AI technique"
5. Results ranked by similarity score
**Outcome**: Comprehensive multi-type memory retrieval

### Scenario 7: Memory Decay and Importance
**Actor**: System, Memory Management Service
**Trigger**: Scheduled maintenance
**Flow**:
1. System evaluates memory importance and access patterns
2. Memories with low importance + low access count flagged
3. Expired working memories cleaned up
4. Inactive sessions archived
5. Memory statistics updated
**Outcome**: Efficient memory management with focus on important information

---

## Domain Events

### Published Events

#### 1. memory.created
**Trigger**: New memory of any type created
**Payload**:
- memory_id: Unique memory identifier
- memory_type: Type of memory (factual, episodic, etc.)
- user_id: Owner of the memory
- content: Memory content preview
- importance_score: Importance level (0.0-1.0)
- tags: Associated tags
- metadata: Additional context
- timestamp: Creation time

**Subscribers**: Audit Service, Analytics Service, Notification Service

#### 2. memory.updated
**Trigger**: Memory content or attributes modified
**Payload**:
- memory_id: Memory identifier
- memory_type: Type of memory
- user_id: Owner
- updated_fields: List of changed fields
- timestamp: Update time

**Subscribers**: Audit Service, Sync Service

#### 3. memory.deleted
**Trigger**: Memory permanently removed
**Payload**:
- memory_id: Memory identifier
- memory_type: Type of memory
- user_id: Owner
- timestamp: Deletion time

**Subscribers**: Audit Service, Qdrant Cleanup Service

#### 4. factual_memory.stored
**Trigger**: AI extracts and stores factual memories from dialog
**Payload**:
- user_id: Owner
- count: Number of facts extracted
- importance_score: Average importance
- source: Source of extraction (dialog, document, etc.)
- timestamp: Storage time

**Subscribers**: Knowledge Graph Service, Analytics Service

#### 5. episodic_memory.stored
**Trigger**: AI extracts and stores episodic memories
**Payload**:
- user_id: Owner
- count: Number of episodes extracted
- importance_score: Average importance
- source: Source of extraction
- timestamp: Storage time

**Subscribers**: Timeline Service, Recommendation Service

#### 6. procedural_memory.stored
**Trigger**: AI extracts and stores procedural memories
**Payload**:
- user_id: Owner
- count: Number of procedures extracted
- importance_score: Average importance
- source: Source of extraction
- timestamp: Storage time

**Subscribers**: Workflow Service, Automation Service

#### 7. semantic_memory.stored
**Trigger**: AI extracts and stores semantic memories
**Payload**:
- user_id: Owner
- count: Number of concepts extracted
- importance_score: Average importance
- source: Source of extraction
- timestamp: Storage time

**Subscribers**: Knowledge Service, Search Service

#### 8. session_memory.deactivated
**Trigger**: Conversation session ends
**Payload**:
- user_id: Owner
- session_id: Session identifier
- duration_seconds: Session length
- message_count: Number of interactions
- timestamp: Deactivation time

**Subscribers**: Analytics Service, Session Manager Service

---

## Core Concepts

### Memory Lifecycle
1. **Extraction**: AI analyzes content and extracts structured information
2. **Validation**: Pydantic models validate data structure
3. **Storage**: PostgreSQL stores structured data
4. **Embedding**: Vector embeddings generated and stored in Qdrant
5. **Indexing**: Database indexes enable efficient retrieval
6. **Retrieval**: Memories retrieved by query or semantic search
7. **Access Tracking**: Access count incremented, last_accessed_at updated
8. **Decay**: Importance and access patterns inform retention
9. **Cleanup**: Expired/low-priority memories removed

### Cognitive Attributes
All memories share these cognitive attributes:
- **Importance Score** (0.0-1.0): How significant the memory is
- **Confidence** (0.0-1.0): How certain we are about accuracy
- **Access Count**: How many times memory retrieved (indicates usefulness)
- **Created At**: When memory was formed
- **Updated At**: Last modification time
- **Last Accessed At**: Most recent retrieval time

### AI-Powered Extraction
Memory Service uses ISA Model (LLM) for intelligent extraction:
- **LLM Models**: gpt-5-nano for extraction, text-embedding-3-small for embeddings
- **Structured Output**: JSON schema validation ensures consistency
- **Context-Aware**: Considers conversation context for better extraction
- **Multi-Memory**: Single dialog can generate multiple memories of different types

### Dual Storage Architecture
- **PostgreSQL**: Structured data, relational queries, ACID guarantees
- **Qdrant**: Vector embeddings, semantic similarity search, fast nearest-neighbor
- **Synchronization**: Same memory ID used in both systems for coordination

---

## Business Rules (High-Level)

### Memory Creation Rules
- BR-MEM-001: All memories must have unique IDs (UUID format)
- BR-MEM-002: User ID is required for all memories
- BR-MEM-003: Memory type must be one of six valid types
- BR-MEM-004: Content field is required and non-empty
- BR-MEM-005: Importance score must be between 0.0 and 1.0
- BR-MEM-006: Confidence must be between 0.0 and 1.0

### Factual Memory Rules
- BR-FACT-001: Subject, predicate, and object are required
- BR-FACT-002: Duplicate facts (same subject+predicate for user) prevented by unique constraint
- BR-FACT-003: Content auto-generated from subject-predicate-object if not provided
- BR-FACT-004: Verification status defaults to "unverified"

### Episodic Memory Rules
- BR-EPIS-001: Emotional valence must be between -1.0 (negative) and 1.0 (positive)
- BR-EPIS-002: Vividness must be between 0.0 and 1.0
- BR-EPIS-003: Episode date can be in the past or present, not future

### Procedural Memory Rules
- BR-PROC-001: Steps must be a non-empty array
- BR-PROC-002: Success rate must be between 0.0 and 1.0
- BR-PROC-003: Difficulty level must be one of: easy, medium, hard

### Working Memory Rules
- BR-WORK-001: TTL must be positive integer (seconds)
- BR-WORK-002: Expires_at automatically calculated from created_at + TTL
- BR-WORK-003: Priority must be between 1 and 10
- BR-WORK-004: Expired memories auto-cleaned by background job
- BR-WORK-005: Task ID and task context are required

### Session Memory Rules
- BR-SESS-001: Session ID is required
- BR-SESS-002: Interaction sequence must be positive integer
- BR-SESS-003: New messages increment sequence number
- BR-SESS-004: Active sessions can be deactivated but not deleted
- BR-SESS-005: Conversation state is JSONB dictionary

### Search and Retrieval Rules
- BR-SRCH-001: Semantic search uses Qdrant vector similarity
- BR-SRCH-002: Retrieved memories increment access_count
- BR-SRCH-003: Search results ranked by similarity score or relevance
- BR-SRCH-004: Filters can be applied: importance_min, date ranges, tags

### Event Publishing Rules
- BR-EVNT-001: All memory mutations publish corresponding events
- BR-EVNT-002: Event publishing failures don't block operations (async)
- BR-EVNT-003: Events include timestamp in ISO 8601 format

---

## Memory Service in the Ecosystem

### Upstream Dependencies
- **ISA Model Service**: AI extraction and embedding generation
- **PostgreSQL gRPC Service**: Database operations
- **Qdrant**: Vector storage and similarity search
- **NATS Event Bus**: Event publishing and subscriptions
- **Consul**: Service discovery and registration

### Downstream Consumers
- **Chatbot Services**: Retrieve conversation context
- **Recommendation Services**: Use episodic and factual memories
- **Knowledge Graph Services**: Build entity relationships from facts
- **Analytics Services**: Memory usage and patterns
- **Workflow Services**: Execute procedural memories
- **Session Manager**: Manage active conversations

### Integration Patterns
- **Synchronous**: REST API for CRUD operations
- **Asynchronous**: NATS events for real-time updates
- **AI-Powered**: LLM extraction for intelligent storage
- **Dual Storage**: PostgreSQL + Qdrant for structured + vector data

---

## Success Metrics

### Memory Quality Metrics
- **Extraction Accuracy**: % of correctly extracted facts/episodes/procedures
- **Search Relevance**: Average similarity scores for queries
- **Memory Completeness**: % of memories with all required fields populated

### Performance Metrics
- **Extraction Latency**: Time from dialog to stored memory (target: <500ms)
- **Retrieval Latency**: Time to fetch memories (target: <100ms)
- **Search Latency**: Semantic search response time (target: <200ms)

### Usage Metrics
- **Memories Per User**: Average count by type
- **Access Frequency**: Memories retrieved per day
- **Memory Growth Rate**: New memories created per day
- **Session Duration**: Average active session length

### System Health Metrics
- **Database Connection**: PostgreSQL availability
- **Vector Store Health**: Qdrant responsiveness
- **AI Service Availability**: ISA Model uptime
- **Event Bus Health**: NATS connectivity

---

## Glossary

**Memory**: A structured piece of information stored with cognitive attributes
**Extraction**: AI-powered analysis to derive structured data from unstructured content
**Embedding**: Vector representation of content for semantic similarity
**Subject-Predicate-Object (SPO)**: Triple format for factual knowledge (e.g., "John lives in Tokyo")
**Semantic Search**: Finding similar content using vector embeddings
**Memory Type**: Category of memory based on cognitive science (6 types)
**Cognitive Attributes**: Metadata modeling human memory characteristics (importance, confidence, access)
**Session**: Continuous conversation or interaction context
**Working Memory**: Short-term task-specific information with TTL
**Memory Decay**: Natural reduction in memory importance over time
**Qdrant**: Vector database for embedding storage and similarity search
**ISA Model**: Internal LLM service for AI extraction and embeddings

---

**Document Version**: 1.0
**Last Updated**: 2025-12-11
**Maintained By**: Memory Service Team
