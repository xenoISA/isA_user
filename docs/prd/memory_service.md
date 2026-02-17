# Memory Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Memory Service
**Version**: 1.0
**Status**: Active Development
**Owner**: AI Platform Team
**Last Updated**: 2025-12-11

### Vision
Enable AI systems to maintain human-like memory capabilities with intelligent extraction, semantic search, and contextual understanding across six cognitive memory types.

### Mission
Provide a scalable, intelligent memory service that transforms conversational AI from stateless to stateful by storing, retrieving, and managing memories based on cognitive science principles.

### Target Users
- AI Assistant Applications (Chatbots, Voice Assistants)
- Recommendation Systems
- Knowledge Management Platforms
- Workflow Automation Systems
- Analytics and Insight Services

### Key Differentiators
1. **Cognitive Science Foundation**: Six memory types based on human cognition
2. **AI-Powered Extraction**: LLM automatically extracts structured memories
3. **Dual Storage**: PostgreSQL (structured) + Qdrant (semantic) for optimal retrieval
4. **Event-Driven**: Real-time notifications for memory mutations
5. **Type Safety**: Full Pydantic validation throughout

---

## Product Goals

### Primary Goals
1. **Intelligent Storage**: Extract and store structured memories from unstructured content with 90%+ accuracy
2. **Fast Retrieval**: Sub-100ms retrieval for direct queries, sub-200ms for semantic search
3. **Scalability**: Support millions of memories per user with consistent performance
4. **Context Awareness**: Enable AI systems to maintain multi-turn conversation context
5. **Memory Quality**: High-confidence, well-structured memories with validation

### Secondary Goals
1. **Analytics**: Provide insights into memory usage patterns
2. **Memory Management**: Automatic cleanup of expired/low-priority memories
3. **Cross-Memory Search**: Unified search across all memory types
4. **Event Integration**: Real-time notifications for downstream services

---

## Epics and User Stories

### Epic 1: AI-Powered Memory Extraction

**Objective**: Enable automatic extraction of structured memories from unstructured dialog using AI.

#### E1-US1: Extract Factual Memories from Dialog
**As a** Chatbot Developer
**I want to** automatically extract facts from user conversations
**So that** the AI can remember user preferences, relationships, and declarative knowledge

**Acceptance Criteria**:
- AC1: POST /api/v1/memories/factual/extract accepts user_id, dialog_content, importance_score
- AC2: AI extracts subject-predicate-object triples from dialog
- AC3: Multiple facts can be extracted from single dialog
- AC4: Each fact stored with unique ID, verification status, and source
- AC5: Returns count of extracted facts and success status
- AC6: Publishes factual_memory.stored event
- AC7: Response time <500ms for typical dialog (100-500 words)

**Example Request**:
```json
{
  "user_id": "usr_123",
  "dialog_content": "I live in San Francisco and work as a software engineer at Apple",
  "importance_score": 0.7
}
```

**Example Response**:
```json
{
  "success": true,
  "operation": "store_factual",
  "message": "Extracted and stored 3 factual memories",
  "affected_count": 3,
  "data": {
    "memory_ids": ["fact_abc", "fact_def", "fact_ghi"]
  }
}
```

#### E1-US2: Extract Episodic Memories from Dialog
**As a** AI Assistant
**I want to** extract personal experiences and events from user stories
**So that** I can remember significant life events and provide contextual recommendations

**Acceptance Criteria**:
- AC1: POST /api/v1/memories/episodic/extract accepts user_id, dialog_content, importance_score
- AC2: AI extracts event_type, location, participants, emotional_valence
- AC3: Episode date automatically extracted or inferred
- AC4: Vividness score calculated based on detail level
- AC5: Returns count of extracted episodes
- AC6: Publishes episodic_memory.stored event
- AC7: Handles multiple episodes in single dialog

#### E1-US3: Extract Procedural Memories from Dialog
**As a** Workflow Automation System
**I want to** extract step-by-step procedures from user descriptions
**So that** I can store and execute workflows automatically

**Acceptance Criteria**:
- AC1: POST /api/v1/memories/procedural/extract accepts user_id, dialog_content, importance_score
- AC2: AI extracts skill_type, domain, ordered steps
- AC3: Prerequisites identified if mentioned
- AC4: Difficulty level assessed from complexity
- AC5: Returns count of extracted procedures
- AC6: Publishes procedural_memory.stored event

#### E1-US4: Extract Semantic Memories from Dialog
**As a** Knowledge Management System
**I want to** extract concepts and definitions from content
**So that** I can build semantic knowledge base

**Acceptance Criteria**:
- AC1: POST /api/v1/memories/semantic/extract accepts user_id, dialog_content, importance_score
- AC2: AI extracts concept_type, definition, category
- AC3: Properties and related concepts identified
- AC4: Abstraction level determined
- AC5: Returns count of extracted concepts
- AC6: Publishes semantic_memory.stored event

---

### Epic 2: Memory CRUD Operations

**Objective**: Provide comprehensive create, read, update, delete operations for all memory types.

#### E2-US1: Create Memory Directly
**As an** API Client
**I want to** create a memory with explicit structured data
**So that** I can store pre-structured information without AI extraction

**Acceptance Criteria**:
- AC1: POST /api/v1/memories accepts MemoryCreateRequest
- AC2: Validates memory type is one of six valid types
- AC3: Validates required fields based on memory type
- AC4: Auto-generates UUID if not provided
- AC5: Sets default values for cognitive attributes
- AC6: Returns created memory with ID
- AC7: Publishes memory.created event
- AC8: Response time <50ms

**API Reference**: `POST /api/v1/memories`

#### E2-US2: Retrieve Memory by ID
**As an** AI Assistant
**I want to** retrieve a specific memory by ID and type
**So that** I can access detailed information about stored memories

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/{memory_type}/{memory_id} returns memory
- AC2: Supports optional user_id filter for security
- AC3: Increments access_count on successful retrieval
- AC4: Updates last_accessed_at timestamp
- AC5: Returns 404 if memory not found
- AC6: Response time <100ms
- AC7: Returns full memory with all attributes

**API Reference**: `GET /api/v1/memories/{memory_type}/{memory_id}`

#### E2-US3: List Memories with Filters
**As a** Dashboard Developer
**I want to** list memories with pagination and filters
**So that** I can display memory collections to users

**Acceptance Criteria**:
- AC1: GET /api/v1/memories accepts query parameters: user_id, memory_type, limit, offset, importance_min
- AC2: Supports filtering by single memory type or all types
- AC3: Returns paginated results (limit: 1-100, default: 50)
- AC4: Results sorted by created_at DESC
- AC5: Returns total count
- AC6: Response time <200ms for 50 results
- AC7: Supports importance_min threshold filter

**API Reference**: `GET /api/v1/memories?user_id=usr_123&memory_type=factual&limit=20`

#### E2-US4: Update Memory Attributes
**As an** AI System
**I want to** update memory content or attributes
**So that** I can correct errors or update information

**Acceptance Criteria**:
- AC1: PUT /api/v1/memories/{memory_type}/{memory_id} accepts MemoryUpdateRequest
- AC2: Supports updating: content, importance_score, confidence, tags, context
- AC3: Updates updated_at timestamp automatically
- AC4: Requires user_id for ownership validation
- AC5: Returns success status and updated memory
- AC6: Publishes memory.updated event with updated_fields
- AC7: Returns 404 if memory not found

**API Reference**: `PUT /api/v1/memories/{memory_type}/{memory_id}`

#### E2-US5: Delete Memory
**As a** User Privacy Controller
**I want to** permanently delete a memory
**So that** users can exercise right to deletion

**Acceptance Criteria**:
- AC1: DELETE /api/v1/memories/{memory_type}/{memory_id} removes memory
- AC2: Requires user_id for ownership validation
- AC3: Returns success status
- AC4: Publishes memory.deleted event
- AC5: Returns 404 if memory not found
- AC6: Triggers Qdrant embedding cleanup (async)

**API Reference**: `DELETE /api/v1/memories/{memory_type}/{memory_id}`

---

### Epic 3: Type-Specific Search Operations

**Objective**: Enable efficient retrieval by memory-type-specific attributes.

#### E3-US1: Search Factual Memories by Subject
**As a** Knowledge Graph Service
**I want to** search factual memories by subject
**So that** I can find all facts about a specific entity

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/factual/search/subject accepts user_id, subject, limit
- AC2: Performs PostgreSQL text search on subject field
- AC3: Returns matching memories sorted by relevance
- AC4: Limit: 1-100 (default: 10)
- AC5: Response time <100ms
- AC6: Returns empty array if no matches

**API Reference**: `GET /api/v1/memories/factual/search/subject?user_id=usr_123&subject=John&limit=10`

#### E3-US2: Search Episodic Memories by Event Type
**As a** Recommendation Engine
**I want to** search episodic memories by event type
**So that** I can find similar experiences

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/episodic/search/event_type accepts user_id, event_type, limit
- AC2: Filters by exact event_type match
- AC3: Returns results sorted by episode_date DESC
- AC4: Limit: 1-100 (default: 10)
- AC5: Response time <100ms

**API Reference**: `GET /api/v1/memories/episodic/search/event_type?user_id=usr_123&event_type=social&limit=10`

#### E3-US3: Search Episodic Memories by Timeframe
**As a** Timeline Visualizer
**I want to** retrieve episodic memories within a date range
**So that** I can display chronological experiences

**Acceptance Criteria**:
- AC1: Accepts user_id, start_date, end_date, limit
- AC2: Filters by episode_date between start and end
- AC3: Returns results sorted by episode_date ASC
- AC4: Handles timezone-aware dates
- AC5: Response time <100ms

#### E3-US4: Search Semantic Memories by Category
**As a** Concept Browser
**I want to** search semantic memories by category
**So that** I can explore related concepts

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/semantic/search/category accepts user_id, category, limit
- AC2: Filters by category field
- AC3: Returns results with related_concepts
- AC4: Response time <100ms

**API Reference**: `GET /api/v1/memories/semantic/search/category?user_id=usr_123&category=technology&limit=10`

---

### Epic 4: Session Memory Management

**Objective**: Manage conversation context across multi-turn interactions.

#### E4-US1: Store Session Message
**As a** Chatbot
**I want to** store each conversation message with context
**So that** I can maintain dialogue state

**Acceptance Criteria**:
- AC1: POST /api/v1/memories/session/store accepts user_id, session_id, message_content, message_type, role
- AC2: Auto-increments interaction_sequence based on existing messages
- AC3: Stores conversation_state with message metadata
- AC4: Sets session as active
- AC5: Returns success status and memory_id
- AC6: Response time <50ms

**API Reference**: `POST /api/v1/memories/session/store`

#### E4-US2: Get Session Memories
**As a** Chatbot
**I want to** retrieve all messages for a session
**So that** I can provide context-aware responses

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/session/{session_id} accepts user_id, session_id
- AC2: Returns all memories for session sorted by interaction_sequence ASC
- AC3: Includes total count
- AC4: Response time <100ms
- AC5: Returns empty array if session not found

**API Reference**: `GET /api/v1/memories/session/{session_id}?user_id=usr_123`

#### E4-US3: Get Session Context with Summaries
**As an** AI Assistant
**I want to** retrieve session context with recent messages and summaries
**So that** I can efficiently load conversation state

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/session/{session_id}/context accepts user_id, include_summaries, max_recent_messages
- AC2: Returns recent N messages (default: 5)
- AC3: Optionally includes session summary
- AC4: Returns total message count
- AC5: Response time <150ms

**API Reference**: `GET /api/v1/memories/session/{session_id}/context?user_id=usr_123&include_summaries=true&max_recent_messages=5`

#### E4-US4: Deactivate Session
**As a** Session Manager
**I want to** mark a session as inactive
**So that** I can track session lifecycle

**Acceptance Criteria**:
- AC1: POST /api/v1/memories/session/{session_id}/deactivate accepts user_id, session_id
- AC2: Sets active=false for all session memories
- AC3: Publishes session_memory.deactivated event
- AC4: Returns success status
- AC5: Response time <50ms

**API Reference**: `POST /api/v1/memories/session/{session_id}/deactivate?user_id=usr_123`

---

### Epic 5: Working Memory and Cleanup

**Objective**: Manage temporary task-related memories with automatic cleanup.

#### E5-US1: Store Working Memory
**As a** Task Execution System
**I want to** store temporary task state
**So that** I can maintain context during multi-step workflows

**Acceptance Criteria**:
- AC1: POST /api/v1/memories/working/store accepts user_id, dialog_content, ttl_seconds, importance_score
- AC2: Auto-generates task_id and task_context
- AC3: Calculates expires_at from ttl_seconds
- AC4: Default TTL: 3600 seconds (1 hour)
- AC5: Returns success status and memory_id
- AC6: Response time <50ms

**API Reference**: `POST /api/v1/memories/working/store`

#### E5-US2: Get Active Working Memories
**As a** Task Coordinator
**I want to** retrieve all non-expired working memories
**So that** I can resume in-progress tasks

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/working/active accepts user_id
- AC2: Filters where expires_at > NOW()
- AC3: Returns results sorted by priority DESC, created_at DESC
- AC4: Response time <100ms
- AC5: Returns empty array if no active memories

**API Reference**: `GET /api/v1/memories/working/active?user_id=usr_123`

#### E5-US3: Cleanup Expired Working Memories
**As a** System Administrator
**I want to** remove expired working memories
**So that** I can maintain database efficiency

**Acceptance Criteria**:
- AC1: POST /api/v1/memories/working/cleanup accepts optional user_id
- AC2: Deletes memories where expires_at <= NOW()
- AC3: If user_id provided, only cleans that user's memories
- AC4: Returns count of deleted memories
- AC5: Response time <500ms for 1000 deletions
- AC6: Can be called by scheduled cron job

**API Reference**: `POST /api/v1/memories/working/cleanup?user_id=usr_123`

---

### Epic 6: Universal Search and Analytics

**Objective**: Provide cross-memory search and usage analytics.

#### E6-US1: Universal Memory Search
**As a** User
**I want to** search across all my memories with a single query
**So that** I can find relevant information regardless of memory type

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/search accepts user_id, query, memory_types (optional), limit
- AC2: If memory_types not specified, searches all six types
- AC3: Returns results grouped by memory type
- AC4: Each type has up to {limit} results
- AC5: Returns total_count across all types
- AC6: Response time <500ms

**API Reference**: `GET /api/v1/memories/search?user_id=usr_123&query=machine learning&memory_types=factual,episodic&limit=10`

**Example Response**:
```json
{
  "query": "machine learning",
  "user_id": "usr_123",
  "searched_types": ["factual", "episodic"],
  "results": {
    "factual": [...],
    "episodic": [...]
  },
  "total_count": 15
}
```

#### E6-US2: Get Memory Statistics
**As a** Dashboard
**I want to** display memory usage statistics
**So that** users can see their memory profile

**Acceptance Criteria**:
- AC1: GET /api/v1/memories/statistics accepts user_id
- AC2: Returns total memory count
- AC3: Returns count by memory type
- AC4: Response time <200ms
- AC5: Includes timestamp

**API Reference**: `GET /api/v1/memories/statistics?user_id=usr_123`

**Example Response**:
```json
{
  "user_id": "usr_123",
  "total_memories": 1247,
  "by_type": {
    "factual": 543,
    "episodic": 321,
    "procedural": 89,
    "semantic": 156,
    "working": 12,
    "session": 126
  },
  "timestamp": "2025-12-11T10:30:00Z"
}
```

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8223`
- **Staging**: `https://staging-memory.isa.ai`
- **Production**: `https://memory.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Header**: `Authorization: Bearer <token>` (future implementation)
- **Current**: user_id in request body or query params

### Common Response Format
```json
{
  "success": boolean,
  "operation": string,
  "message": string,
  "data": object | null,
  "affected_count": integer,
  "memory_id": string | null
}
```

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: Resource created
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service degraded

### Rate Limits
- **Per User**: 1000 requests/hour
- **Per IP**: 10000 requests/hour
- **Burst**: 100 requests/minute

### Pagination
```
?limit=50&offset=0
```
- **limit**: 1-100 (default: 50)
- **offset**: 0+ (default: 0)

---

## Functional Requirements

### FR-1: Memory Type Support
System SHALL support six memory types: factual, episodic, procedural, semantic, working, session

### FR-2: AI-Powered Extraction
System SHALL use LLM to extract structured memories from unstructured dialog

### FR-3: Dual Storage
System SHALL store structured data in PostgreSQL and vector embeddings in Qdrant

### FR-4: Event Publishing
System SHALL publish events for all memory mutations (create, update, delete)

### FR-5: Access Tracking
System SHALL increment access_count and update last_accessed_at on retrieval

### FR-6: Validation
System SHALL validate all inputs using Pydantic models

### FR-7: Search Capabilities
System SHALL support both attribute-based search and semantic search

### FR-8: Memory Cleanup
System SHALL automatically cleanup expired working memories

### FR-9: Session Management
System SHALL maintain conversation context with sequential interaction tracking

### FR-10: Statistics
System SHALL provide memory usage statistics per user

---

## Non-Functional Requirements

### NFR-1: Performance
- **Extraction Latency**: <500ms for typical dialog (100-500 words)
- **Retrieval Latency**: <100ms for single memory by ID
- **Search Latency**: <200ms for semantic search
- **List Latency**: <200ms for 50 results

### NFR-2: Scalability
- **Users**: Support 1M+ concurrent users
- **Memories**: 1M+ memories per user
- **Throughput**: 10K requests/second

### NFR-3: Availability
- **Uptime**: 99.9% (excluding planned maintenance)
- **Health Check**: /health endpoint responds in <50ms

### NFR-4: Data Integrity
- **ACID**: PostgreSQL transactions ensure consistency
- **Validation**: Pydantic models validate all data
- **Constraints**: Database constraints prevent duplicates

### NFR-5: Security
- **Authentication**: JWT-based (future)
- **Authorization**: User-scoped data isolation
- **Input Sanitization**: Prevent SQL injection, XSS

### NFR-6: Observability
- **Logging**: Structured logs for all operations
- **Metrics**: Prometheus-compatible metrics
- **Tracing**: Request tracing for debugging
- **Health Checks**: Database and service health monitoring

### NFR-7: API Compatibility
- **Versioning**: /api/v1/ prefix for version control
- **Deprecation**: 6-month notice for breaking changes
- **Documentation**: OpenAPI/Swagger specs

---

## Dependencies

### External Services
1. **ISA Model Service**: AI extraction and embeddings
   - Endpoint: `http://isa-model:8082`
   - Models: gpt-5-nano, text-embedding-3-small
   - SLA: 95% availability

2. **PostgreSQL gRPC Service**: Database operations
   - Host: `isa-postgres-grpc:50061`
   - Schema: `memory`
   - SLA: 99.9% availability

3. **Qdrant**: Vector storage
   - Host: `isa-qdrant:6333`
   - Collections: memory_factual, memory_episodic, etc.
   - SLA: 99.5% availability

4. **NATS Event Bus**: Event publishing
   - Host: `isa-nats:4222`
   - Subjects: memory.*, memory.factual.*, etc.
   - SLA: 99.9% availability

5. **Consul**: Service discovery
   - Host: `localhost:8500`
   - Service: memory_service
   - SLA: 99.9% availability

---

## Success Criteria

### Phase 1: Core Functionality (Complete)
- [x] All six memory types implemented
- [x] CRUD operations working
- [x] AI extraction functional
- [x] PostgreSQL storage working
- [x] Event publishing active

### Phase 2: Enhanced Features (Current)
- [ ] Qdrant integration for semantic search
- [ ] Memory consolidation and optimization
- [ ] Advanced search with filters
- [ ] Memory decay algorithms

### Phase 3: Production Ready (Future)
- [ ] Authentication and authorization
- [ ] Rate limiting
- [ ] Comprehensive monitoring
- [ ] Load testing and optimization
- [ ] Documentation completion

---

## Out of Scope

The following are explicitly NOT included in this release:
1. Multi-user shared memories (future: memory_sharing service)
2. Memory encryption at rest (future: security enhancement)
3. Real-time memory synchronization across devices (future: sync service)
4. Memory analytics dashboard (future: separate UI service)
5. Memory export to external formats (future: export service)

---

## Appendix: Request/Response Examples

### Create Factual Memory (Direct)
```bash
curl -X POST http://localhost:8223/api/v1/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_123",
    "memory_type": "factual",
    "content": "John lives in Tokyo",
    "fact_type": "person_location",
    "subject": "John",
    "predicate": "lives in",
    "object_value": "Tokyo",
    "importance_score": 0.7
  }'
```

### Extract Episodic Memory (AI-Powered)
```bash
curl -X POST http://localhost:8223/api/v1/memories/episodic/extract \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_123",
    "dialog_content": "Last weekend I went hiking in Yosemite with Tom and Lisa. The views were breathtaking!",
    "importance_score": 0.8
  }'
```

### List Memories with Filters
```bash
curl -X GET "http://localhost:8223/api/v1/memories?user_id=usr_123&memory_type=factual&limit=20&importance_min=0.5"
```

### Universal Search
```bash
curl -X GET "http://localhost:8223/api/v1/memories/search?user_id=usr_123&query=machine%20learning&memory_types=factual,semantic&limit=10"
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-11
**Maintained By**: Memory Service Product Team
**Related Documents**:
- Domain Context: docs/domain/memory_service.md
- Design Doc: docs/design/memory_service.md (next)
