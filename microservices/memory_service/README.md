# Memory Service

AI-powered memory service for intelligent information storage and retrieval across multiple memory types.

## Features

### 🧠 Memory Types (Based on Cognitive Science)
- **Factual Memory**: Facts and declarative knowledge (subject-predicate-object triples)
- **Procedural Memory**: How-to knowledge and skills with step-by-step procedures
- **Episodic Memory**: Personal experiences and events with temporal/spatial context
- **Semantic Memory**: Concepts and general knowledge with definitions
- **Working Memory**: Temporary task-related information with TTL
- **Session Memory**: Conversation context and interaction history

### 🤖 AI-Powered Extraction
- Automatic fact extraction from conversations using LLM
- Intelligent episode detection with emotional valence analysis
- Procedure extraction with step decomposition
- Concept extraction with relationship mapping
- **Direct integration with ISA Model service** (no wrapper overhead)
- Automatic embedding generation for semantic search

## Architecture

```
memory_service/
├── models.py                    # Pydantic models for all memory types
├── base_repository.py           # Base repository with common DB operations
├── *_repository.py              # Type-specific repositories (factual, episodic, etc.)
├── *_service.py                 # Type-specific services with AI extraction
├── memory_service.py            # Orchestration layer
├── main.py                      # FastAPI HTTP service on port 8210
├── client.py                    # HTTP client (TODO)
├── migrations/                  # PostgreSQL migrations (9 files)
│   ├── 000_init_schema.sql
│   ├── 001-006_create_*_table.sql
│   ├── 007_create_memory_metadata_table.sql
│   ├── 008_create_memory_associations_table.sql
│   └── 009_create_memory_functions.sql
└── tests/                       # Bash test scripts
    ├── test_factual_memory.sh
    ├── test_episodic_memory.sh
    ├── test_procedural_memory.sh
    ├── test_semantic_memory.sh
    ├── test_working_memory.sh
    ├── test_session_memory.sh
    └── run_all_tests.sh
```

### Architecture Principles

**PostgreSQL + Qdrant Dual Storage:**
- **PostgreSQL**: Stores structured memory data (NO embedding field)
- **Qdrant**: Stores vector embeddings for semantic search
- **Memory ID**: Same ID used in both systems for synchronization
- **NO pgvector**: We use Qdrant as dedicated vector database

**Key Design Decisions:**
1. No foreign keys across services (microservices independence)
2. Direct AsyncISAModel usage (no wrapper overhead)
3. Separate repositories and services for each memory type
4. gRPC for PostgreSQL communication
5. HTTP REST API for external clients

### Layer Responsibilities

1. **Repository Layer**: Direct database access via PostgresClient (gRPC)
   - CRUD operations
   - Type-specific queries
   - No business logic

2. **Service Layer**: Business logic + AI integration
   - AI-powered extraction using AsyncISAModel
   - Embedding generation
   - Validation and data transformation
   - Calls repository for persistence

3. **Orchestration Layer** (`memory_service.py`):
   - Coordinates across memory types
   - Provides unified API
   - Statistics and utility functions

## AI Integration

### ISA Model Service
All AI features use **ISA Model service directly** via `AsyncISAModel` client:

```python
from isa_model.inference_client import AsyncISAModel

# LLM for extraction
async with AsyncISAModel(base_url=ISA_MODEL_URL) as client:
    response = await client.chat.completions.create(
        model="gpt-5-nano",
        messages=[...],
        response_format={"type": "json_object"}
    )

# Embeddings for semantic search
async with AsyncISAModel(base_url=ISA_MODEL_URL) as client:
    embedding = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
```

### Configuration
Set `ISA_MODEL_URL` environment variable (default: `http://localhost:8082`)

## Usage Examples

### Store Factual Memory (AI-powered)
```python
from memory_service import MemoryService

service = MemoryService()

# AI automatically extracts facts from conversation
result = await service.store_factual_memory(
    user_id="user123",
    dialog_content="John lives in Tokyo and works as a software engineer at Google",
    importance_score=0.8
)
# Result: Extracts multiple facts:
# - "John" "lives in" "Tokyo"
# - "John" "works as" "software engineer"
# - "John" "works at" "Google"
```

### Store Episodic Memory (AI-powered)
```python
result = await service.store_episodic_memory(
    user_id="user123",
    dialog_content="Yesterday I went to the beach with Sarah and Tom. We had a great time swimming and playing volleyball. The sunset was beautiful.",
    importance_score=0.7
)
# AI extracts: event type, location, participants, emotional valence, etc.
```

### Search Memories
```python
# Search facts by subject
facts = await service.search_facts_by_subject(
    user_id="user123",
    subject="John",
    limit=10
)

# Search episodes by timeframe
from datetime import datetime
episodes = await service.search_episodes_by_timeframe(
    user_id="user123",
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 1, 31),
    limit=10
)

# Get memory statistics
stats = await service.get_memory_statistics(user_id="user123")
```

## Database Schema

Uses PostgreSQL with `memory` schema:
- `memory.factual_memories` - Facts with subject-predicate-object structure
- `memory.procedural_memories` - Procedures with steps and conditions
- `memory.episodic_memories` - Episodes with temporal/spatial context
- `memory.semantic_memories` - Concepts with definitions and categories
- `memory.working_memories` - Temporary memories with TTL
- `memory.session_memories` - Conversation history with sequence
- `memory.session_summaries` - Condensed session summaries
- `memory.memory_metadata` - Access tracking and quality metrics
- `memory.memory_associations` - Cross-memory relationships

**IMPORTANT**: Tables do NOT contain embedding fields. Vector embeddings are stored in Qdrant.

Each table includes:
- Common fields: id, user_id, content, timestamps, importance, confidence
- Type-specific fields (e.g., subject/predicate/object for facts, steps for procedures)
- Indexes for efficient querying
- Triggers for automatic metadata tracking

## Testing

### Run All Tests
```bash
cd tests
./run_all_tests.sh
```

### Run Individual Test Suites
```bash
./test_factual_memory.sh      # Test factual memory extraction and retrieval
./test_episodic_memory.sh     # Test episodic memory for events
./test_procedural_memory.sh   # Test procedural memory for how-to knowledge
./test_semantic_memory.sh     # Test semantic memory for concepts
./test_working_memory.sh      # Test working memory with TTL
./test_session_memory.sh      # Test session memory for conversations
```

All test scripts:
- Use bash with curl for HTTP requests
- Support both jq and python for JSON parsing
- Color-coded output (green=pass, red=fail, yellow=warning)
- Track test statistics
- Exit with appropriate codes for CI/CD

## Next Steps

### TODO
- [x] Create `main.py` - FastAPI HTTP service with REST endpoints
- [x] Create database migrations (SQL files)
- [x] Create test scripts for all memory types
- [ ] Create `client.py` - HTTP client for service communication
- [ ] Create `__init__.py` for package exports
- [ ] Add Postman collection
- [ ] Integrate Qdrant for vector storage
- [ ] Add semantic search across all memory types
- [ ] Add memory consolidation/optimization
- [ ] Add comprehensive integration tests

## Dependencies

- `isa_common.postgres_client` - PostgreSQL gRPC client
- `isa_model.inference_client` - ISA Model API client
- `pydantic` - Data validation and models
- `fastapi` - HTTP service framework (TODO)
- `asyncio` - Async operations

## Benefits

✅ **No AI Wrapper Overhead**: Direct `AsyncISAModel` usage
✅ **Cognitive Science Foundation**: Based on human memory types
✅ **Intelligent Extraction**: LLM automatically extracts structured data
✅ **Semantic Search**: Vector embeddings for similarity search
✅ **Type Safety**: Pydantic models throughout
✅ **Clean Architecture**: Repository → Service → Orchestration
✅ **PostgreSQL + gRPC**: Efficient database access
✅ **Modular Design**: Each memory type is independent

## Service Configuration

**Port**: 8223
**Service Name**: memory_service
**Consul Tags**: `["microservice", "memory", "ai", "api"]`

### Environment Variables
```bash
# ISA Model Service (for AI extraction and embeddings)
ISA_MODEL_URL=http://localhost:8082

# PostgreSQL gRPC Client
POSTGRES_GRPC_HOST=isa-postgres-grpc
POSTGRES_GRPC_PORT=50061

# Qdrant (Vector Database)
QDRANT_HOST=isa-qdrant
QDRANT_PORT=6333

# Consul (Service Discovery)
CONSUL_HOST=localhost
CONSUL_PORT=8500
```

## HTTP API Endpoints

### AI-Powered Memory Extraction
- `POST /memories/factual/extract` - Extract facts from dialog
- `POST /memories/episodic/extract` - Extract episodes from dialog
- `POST /memories/procedural/extract` - Extract procedures from dialog
- `POST /memories/semantic/extract` - Extract concepts from dialog

### CRUD Operations
- `POST /memories` - Create memory
- `GET /memories/{memory_type}/{memory_id}` - Get memory by ID
- `PUT /memories/{memory_type}/{memory_id}` - Update memory
- `DELETE /memories/{memory_type}/{memory_id}` - Delete memory
- `GET /memories` - List memories (with filters)

### Search Operations
- `GET /memories/factual/search/subject` - Search facts by subject
- `GET /memories/episodic/search/event_type` - Search episodes by event type
- `GET /memories/working/active` - Get active working memories
- `POST /memories/working/cleanup` - Cleanup expired memories

### Session Operations
- `GET /memories/session/{session_id}` - Get session memories
- `POST /memories/session/{session_id}/deactivate` - Deactivate session

### Statistics
- `GET /memories/statistics` - Get memory statistics for user
- `GET /health` - Health check endpoint

## Running the Service

### Local Development
```bash
# Start the service
python main.py

# Service will run on http://localhost:8223
```

### Docker Deployment
```bash
# Build image
docker build -t isa-memory-service:latest .

# Run container
docker run -p 8223:8223 \
  -e ISA_MODEL_URL=http://isa-model:8082 \
  -e POSTGRES_GRPC_HOST=isa-postgres-grpc \
  -e QDRANT_HOST=isa-qdrant \
  isa-memory-service:latest
```

## Database Setup

### Run Migrations
```bash
# Connect to PostgreSQL
psql -h localhost -p 5432 -U postgres -d isa_db

# Run migrations in order
\i migrations/000_init_schema.sql
\i migrations/001_create_factual_memories_table.sql
\i migrations/002_create_procedural_memories_table.sql
\i migrations/003_create_episodic_memories_table.sql
\i migrations/004_create_semantic_memories_table.sql
\i migrations/005_create_working_memories_table.sql
\i migrations/006_create_session_memories_table.sql
\i migrations/007_create_memory_metadata_table.sql
\i migrations/008_create_memory_associations_table.sql
\i migrations/009_create_memory_functions.sql
```
