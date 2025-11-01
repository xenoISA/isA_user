# Memory Service - Complete Guide

A comprehensive cognitive memory management system supporting six types of human-like memory storage and retrieval with AI-powered extraction capabilities.

## Table of Contents

- [Overview](#overview)
- [Memory Types](#memory-types)
- [Quick Start](#quick-start)
- [AI-Powered Extraction](#ai-powered-extraction)
- [API Reference](#api-reference)
- [Python Client Usage](#python-client-usage)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

The Memory Service implements a cognitive science-based memory system that mimics human memory organization. It provides:

- **6 Memory Types**: Factual, Episodic, Procedural, Semantic, Working, and Session
- **AI-Powered Extraction**: Automatically extract structured memories from natural language
- **Vector Search**: Semantic similarity search using embeddings (Qdrant)
- **Flexible Storage**: PostgreSQL for structured data with JSONB support
- **RESTful API**: Complete HTTP API for all operations
- **Python Client**: Both async and sync client libraries

**Base URL**: \`http://localhost:8223\`

---

## Memory Types

### 1. Factual Memory 📋
**What**: Personal facts and declarative knowledge about the user

**Use Cases**:
- User preferences (favorite color, food allergies)
- Personal information (birthday, address)
- Factual statements ("I work at TechCorp")

**Key Fields**:
- \`fact_type\`: Type of fact (preference, attribute, statement)
- \`subject\`: Main subject of the fact
- \`predicate\`: Relationship or property
- \`object\`: Value or object of the fact
- \`related_facts\`: Array of related fact IDs

**Example**:
\`\`\`json
{
  "user_id": "user_123",
  "memory_type": "factual",
  "content": "My favorite programming language is Python",
  "fact_type": "preference",
  "subject": "programming language",
  "predicate": "favorite",
  "object": "Python",
  "importance_score": 0.8
}
\`\`\`

---

### 2. Episodic Memory 📅
**What**: Personal experiences and events with temporal/spatial context

**Use Cases**:
- Life events ("I graduated from Stanford in 2020")
- Experiences ("Last Tuesday I went to an Italian restaurant")
- Conversations and interactions

**Key Fields**:
- \`event_type\`: Type of event (meeting, celebration, travel, etc.)
- \`event_time\`: When the event occurred
- \`location\`: Where it happened
- \`participants\`: Who was involved (array)
- \`emotional_valence\`: Emotional tone (-1 to 1)
- \`event_details\`: JSONB with rich event information

**Example**:
\`\`\`json
{
  "user_id": "user_123",
  "memory_type": "episodic",
  "content": "Celebrated project completion at Italian restaurant",
  "event_type": "celebration",
  "event_time": "2025-10-24T19:00:00Z",
  "location": "Downtown Italian Restaurant",
  "participants": ["colleagues", "team_lead"],
  "emotional_valence": 0.8,
  "importance_score": 0.7
}
\`\`\`

---

### 3. Procedural Memory 🔧
**What**: How-to knowledge and sequential procedures

**Use Cases**:
- Recipes and cooking instructions
- Deployment procedures
- Step-by-step guides
- User workflows

**Key Fields**:
- \`skill_type\`: Type of skill (cooking, technical, etc.)
- \`steps\`: Array of sequential steps with order and description
- \`domain\`: Broader category
- \`difficulty_level\`: easy/medium/hard
- \`success_rate\`: How often it works (0-1)
- \`prerequisites\`: Required conditions (JSONB array)

**Example**:
\`\`\`json
{
  "user_id": "user_123",
  "memory_type": "procedural",
  "content": "How to deploy the application",
  "skill_type": "deployment",
  "domain": "software engineering",
  "steps": [
    {"order": 1, "description": "Run all unit tests"},
    {"order": 2, "description": "Build Docker image"},
    {"order": 3, "description": "Push to registry"},
    {"order": 4, "description": "Update Kubernetes deployment"}
  ],
  "difficulty_level": "medium",
  "importance_score": 0.9
}
\`\`\`

---

### 4. Semantic Memory 💡
**What**: General knowledge and concepts independent of personal experience

**Use Cases**:
- Definitions and concepts
- General knowledge ("Photosynthesis converts light to energy")
- Category relationships
- Abstract understanding

**Key Fields**:
- \`concept_type\`: Type (definition, principle, relationship, etc.)
- \`category\`: Broader category (technology, biology, etc.)
- \`related_concepts\`: Related concept structures (JSONB array)
- \`properties\`: Key properties (JSONB array)
- \`abstraction_level\`: low/medium/high
- \`definition\`: Formal definition

**Example**:
\`\`\`json
{
  "user_id": "user_123",
  "memory_type": "semantic",
  "content": "Machine learning is a subset of AI",
  "concept_type": "definition",
  "category": "technology",
  "related_concepts": [
    {"concept": "artificial intelligence", "relationship": "parent"},
    {"concept": "deep learning", "relationship": "sibling"}
  ],
  "abstraction_level": "medium",
  "importance_score": 0.8
}
\`\`\`

---

### 5. Working Memory ⏰
**What**: Temporary short-term memory with auto-expiration

**Use Cases**:
- Current tasks and context
- Temporary notes
- Active goals
- Short-term reminders

**Key Fields**:
- \`task_id\`: Optional task identifier
- \`task_context\`: JSONB with task-specific data
- \`priority\`: Priority level (1-10, higher = more important)
- \`ttl_seconds\`: Time to live in seconds
- \`expires_at\`: Expiration timestamp

**Example**:
\`\`\`json
{
  "user_id": "user_123",
  "memory_type": "working",
  "content": "Reviewing PR #456 - waiting for feedback",
  "task_context": {
    "task": "code_review",
    "pr_number": 456,
    "status": "pending",
    "priority": 5
  },
  "priority": 5,
  "ttl_minutes": 60,
  "importance_score": 0.6
}
\`\`\`

---

### 6. Session Memory 💬
**What**: Conversation context within a session

**Use Cases**:
- Chat history
- Conversation turns
- Session-specific context
- Interaction tracking

**Key Fields**:
- \`session_id\`: Session identifier
- \`session_type\`: Type (chat, voice, etc.)
- \`interaction_sequence\`: Order in session
- \`conversation_state\`: JSONB with state info
- \`active\`: Whether session is active

**Example**:
\`\`\`json
{
  "user_id": "user_123",
  "memory_type": "session",
  "session_id": "session_12345",
  "session_type": "chat",
  "interaction_sequence": 1,
  "content": "User: Hello! I need help with my project.",
  "context": {
    "role": "user",
    "timestamp": "2025-10-26T10:00:00Z"
  },
  "active": true,
  "importance_score": 0.5
}
\`\`\`

---

## Quick Start

### Health Check

\`\`\`bash
curl http://localhost:8223/health
\`\`\`

Response:
\`\`\`json
{
  "status": "operational",
  "service": "memory_service",
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2025-10-26T14:00:00.000000"
}
\`\`\`

### Create a Memory

\`\`\`bash
curl -X POST http://localhost:8223/memories \\
  -H "Content-Type: application/json" \\
  -d '{
    "user_id": "user_123",
    "memory_type": "factual",
    "content": "I prefer dark theme for my IDE",
    "fact_type": "preference",
    "subject": "IDE theme",
    "importance_score": 0.7
  }'
\`\`\`

### Get Memory by ID

\`\`\`bash
curl "http://localhost:8223/memories/factual/{memory_id}?user_id=user_123"
\`\`\`

### List All Memories

\`\`\`bash
curl "http://localhost:8223/memories?user_id=user_123&memory_type=factual&limit=50"
\`\`\`

---

## AI-Powered Extraction

The Memory Service can automatically extract structured memories from natural language using AI models.

### Extract Factual Memories

\`\`\`bash
curl -X POST http://localhost:8223/memories/factual/extract \\
  -H "Content-Type: application/json" \\
  -d '{
    "user_id": "user_123",
    "dialog_content": "My name is John Smith and I work as a software engineer at TechCorp. My favorite programming language is Python.",
    "importance_score": 0.8
  }'
\`\`\`

**Response**:
\`\`\`json
{
  "success": true,
  "memory_id": null,
  "operation": "store_factual_memory",
  "message": "Successfully stored 3 factual memories",
  "data": {
    "memory_ids": [
      "uuid-1",
      "uuid-2",
      "uuid-3"
    ]
  },
  "affected_count": 3
}
\`\`\`

The AI extracts:
- Name: "John Smith"
- Job: "Software engineer at TechCorp"
- Preference: "Favorite language is Python"

### All Extract Endpoints

- \`POST /memories/factual/extract\` - Extract facts
- \`POST /memories/episodic/extract\` - Extract events
- \`POST /memories/procedural/extract\` - Extract procedures
- \`POST /memories/semantic/extract\` - Extract concepts

---

## API Reference

### Core Memory Operations

#### Create Memory
\`\`\`http
POST /memories
Content-Type: application/json

{
  "user_id": "string",
  "memory_type": "factual|episodic|procedural|semantic|working|session",
  "content": "string",
  "importance_score": 0.0-1.0,
  ... (type-specific fields)
}
\`\`\`

#### Get Memory
\`\`\`http
GET /memories/{memory_type}/{memory_id}?user_id={user_id}
\`\`\`

#### List Memories
\`\`\`http
GET /memories?user_id={user_id}&memory_type={type}&limit={limit}&offset={offset}&importance_min={score}
\`\`\`

#### Update Memory
\`\`\`http
PUT /memories/{memory_type}/{memory_id}?user_id={user_id}
Content-Type: application/json

{
  "importance_score": 0.9,
  "context": {...}
}
\`\`\`

#### Delete Memory
\`\`\`http
DELETE /memories/{memory_type}/{memory_id}?user_id={user_id}
\`\`\`

---

### Search Operations

#### Search Facts by Subject
\`\`\`http
GET /memories/factual/search/subject?user_id={user_id}&subject={subject}&limit={limit}
\`\`\`

#### Search Episodes by Event Type
\`\`\`http
GET /memories/episodic/search/event_type?user_id={user_id}&event_type={event_type}&limit={limit}
\`\`\`

---

### Working Memory Operations

#### Get Active Working Memories
\`\`\`http
GET /memories/working/active?user_id={user_id}
\`\`\`

#### Cleanup Expired Memories
\`\`\`http
POST /memories/working/cleanup?user_id={user_id}
\`\`\`

---

### Session Operations

#### Get Session Memories
\`\`\`http
GET /memories/session/{session_id}?user_id={user_id}
\`\`\`

#### Deactivate Session
\`\`\`http
POST /memories/session/{session_id}/deactivate?user_id={user_id}
\`\`\`

---

### Statistics

#### Get Memory Statistics
\`\`\`http
GET /memories/statistics?user_id={user_id}
\`\`\`

---

## Python Client Usage

### Async Client

\`\`\`python
from memory_service.client import MemoryServiceClient
from memory_service.models import MemoryType, MemoryCreateRequest
import asyncio

# Initialize
client = MemoryServiceClient(base_url="http://localhost:8223")

async def main():
    # Health check
    health = await client.health_check()
    
    # AI extraction
    result = await client.extract_factual_memory(
        user_id="user_123",
        dialog_content="I am allergic to peanuts",
        importance_score=0.9
    )
    
    # Create memory
    request = MemoryCreateRequest(
        user_id="user_123",
        memory_type=MemoryType.FACTUAL,
        content="My timezone is EST",
        importance_score=0.7
    )
    result = await client.create_memory(request)
    
    # Get memory
    memory = await client.get_memory(
        memory_type=MemoryType.FACTUAL,
        memory_id=result.memory_id,
        user_id="user_123"
    )
    
    # List memories
    memories = await client.list_memories(
        user_id="user_123",
        memory_type=MemoryType.FACTUAL,
        limit=50
    )
    
    # Search
    results = await client.search_facts_by_subject(
        user_id="user_123",
        subject="food"
    )
    
    # Session operations
    session_memories = await client.get_session_memories(
        session_id="session_123",
        user_id="user_123"
    )
    
    # Working memory
    active = await client.get_active_working_memories("user_123")
    await client.cleanup_expired_memories("user_123")
    
    # Statistics
    stats = await client.get_memory_statistics("user_123")

asyncio.run(main())
\`\`\`

### Sync Client

\`\`\`python
from memory_service.client import MemoryServiceSyncClient

client = MemoryServiceSyncClient()

# Health check
health = client.health_check()

# Extract
result = client.extract_factual_memory(
    user_id="user_123",
    dialog_content="I prefer dark mode",
    importance_score=0.7
)

# List
memories = client.list_memories(user_id="user_123")

# Statistics
stats = client.get_memory_statistics(user_id="user_123")
\`\`\`

---

## Best Practices

### 1. Memory Type Selection
- **Factual**: User preferences and attributes
- **Episodic**: Time/place-specific events
- **Procedural**: Step-by-step instructions
- **Semantic**: General knowledge
- **Working**: Temporary context with TTL
- **Session**: Conversation history

### 2. Importance Scores
- **0.9-1.0**: Critical (allergies, security)
- **0.7-0.9**: Important preferences
- **0.5-0.7**: Useful context
- **0.3-0.5**: Optional info
- **0.0-0.3**: Low priority

### 3. Working Memory TTL
- Short tasks: 5-15 minutes
- Active work: 30-120 minutes
- Session duration: 2-4 hours
- Day-long context: 24 hours

### 4. Session Management
- New session per conversation
- Unique session_id
- Increment interaction_sequence
- Deactivate when done

---

## Testing

\`\`\`bash
# All tests
./run_all_tests.sh

# Individual
bash microservices/memory_service/tests/test_factual_memory.sh
bash microservices/memory_service/tests/test_episodic_memory.sh
bash microservices/memory_service/tests/test_procedural_memory.sh
bash microservices/memory_service/tests/test_semantic_memory.sh
bash microservices/memory_service/tests/test_working_memory.sh
bash microservices/memory_service/tests/test_session_memory.sh
\`\`\`

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-26  
**Port**: 8223
