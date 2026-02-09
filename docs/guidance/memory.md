# Memory

AI-powered cognitive memory system for intelligent agents.

## Overview

The memory_service (port 8223) implements a sophisticated multi-layered cognitive memory system inspired by human memory architecture.

## Memory Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COGNITIVE MEMORY ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    SHORT-TERM MEMORY                                   │ │
│  │  ┌─────────────┐  ┌─────────────┐                                     │ │
│  │  │   Working   │  │   Session   │  ← Redis (Fast Access)              │ │
│  │  │   Memory    │  │   Memory    │                                     │ │
│  │  └─────────────┘  └─────────────┘                                     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                              │                                             │
│                              ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    LONG-TERM MEMORY                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │
│  │  │  Episodic   │  │  Semantic   │  │ Procedural  │  │   Factual   │  │ │
│  │  │  (Events)   │  │  (Concepts) │  │  (Skills)   │  │   (Facts)   │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │
│  │        │                │                │                │          │ │
│  │        ▼                ▼                ▼                ▼          │ │
│  │    Qdrant           Qdrant          PostgreSQL       PostgreSQL     │ │
│  │   (Vector)         (Vector)        (Structured)      (Structured)   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Memory Type | Description | Storage | Retrieval |
|-------------|-------------|---------|-----------|
| **Working** | Active context, current focus | Redis | Key-value |
| **Session** | Conversation context | Redis | Session ID |
| **Episodic** | Personal experiences, events | Qdrant | Semantic search |
| **Semantic** | Facts, concepts, knowledge | Qdrant | Semantic search |
| **Procedural** | How-to knowledge, skills | PostgreSQL | Structured query |
| **Factual** | Subject-predicate-object facts | PostgreSQL | Structured query |

## Working Memory

Active context for current operations.

### Store Working Memory

```bash
curl -X POST "http://localhost:8223/api/v1/memory/working" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "current_task",
    "value": {
      "task_id": "task_123",
      "description": "Writing documentation",
      "context": {
        "project": "isA_user",
        "files_open": ["memory.md"]
      }
    },
    "ttl_seconds": 3600
  }'
```

### Get Working Memory

```bash
curl "http://localhost:8223/api/v1/memory/working/current_task" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Clear Working Memory

```bash
curl -X DELETE "http://localhost:8223/api/v1/memory/working" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Session Memory

Context within a conversation session.

### Store Session Context

```bash
curl -X POST "http://localhost:8223/api/v1/memory/session" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123",
    "messages": [
      {"role": "user", "content": "Help me with documentation"},
      {"role": "assistant", "content": "I can help with that..."}
    ],
    "metadata": {
      "topic": "documentation",
      "started_at": "2024-01-28T10:00:00Z"
    }
  }'
```

### Get Session Context

```bash
curl "http://localhost:8223/api/v1/memory/session/sess_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Append to Session

```bash
curl -X POST "http://localhost:8223/api/v1/memory/session/sess_abc123/append" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "user",
      "content": "Can you show me an example?"
    }
  }'
```

## Episodic Memory

Personal experiences and events with temporal context.

### Store Episodic Memory

```bash
curl -X POST "http://localhost:8223/api/v1/memory/episodic" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User completed their first project deployment successfully",
    "timestamp": "2024-01-28T15:30:00Z",
    "location": "San Francisco",
    "participants": ["user_123", "assistant"],
    "emotion": "proud",
    "importance": 0.8,
    "metadata": {
      "project": "my_app",
      "milestone": "first_deployment"
    }
  }'
```

### Search Episodic Memory

```bash
curl -X POST "http://localhost:8223/api/v1/memory/episodic/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "project deployment success",
    "time_range": {
      "from": "2024-01-01T00:00:00Z",
      "to": "2024-01-31T23:59:59Z"
    },
    "limit": 10
  }'
```

Response:
```json
{
  "memories": [
    {
      "memory_id": "mem_abc123",
      "content": "User completed their first project deployment successfully",
      "timestamp": "2024-01-28T15:30:00Z",
      "relevance_score": 0.92,
      "emotion": "proud",
      "importance": 0.8
    }
  ]
}
```

## Semantic Memory

General knowledge, concepts, and facts.

### Store Semantic Memory

```bash
curl -X POST "http://localhost:8223/api/v1/memory/semantic" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "concept": "Docker",
    "definition": "A platform for developing, shipping, and running applications in containers",
    "category": "technology",
    "related_concepts": ["containers", "kubernetes", "microservices"],
    "source": "documentation",
    "confidence": 0.95
  }'
```

### Search Semantic Memory

```bash
curl -X POST "http://localhost:8223/api/v1/memory/semantic/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "container orchestration",
    "category": "technology",
    "limit": 5
  }'
```

### Get Related Concepts

```bash
curl "http://localhost:8223/api/v1/memory/semantic/Docker/related" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Procedural Memory

Skills, procedures, and how-to knowledge.

### Store Procedure

```bash
curl -X POST "http://localhost:8223/api/v1/memory/procedural" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "deploy_to_kubernetes",
    "description": "Deploy application to Kubernetes cluster",
    "steps": [
      {"order": 1, "action": "Build Docker image", "command": "docker build -t app ."},
      {"order": 2, "action": "Push to registry", "command": "docker push app"},
      {"order": 3, "action": "Apply manifests", "command": "kubectl apply -f k8s/"}
    ],
    "prerequisites": ["docker_installed", "kubectl_configured"],
    "category": "deployment"
  }'
```

### Get Procedure

```bash
curl "http://localhost:8223/api/v1/memory/procedural/deploy_to_kubernetes" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Search Procedures

```bash
curl -X POST "http://localhost:8223/api/v1/memory/procedural/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "kubernetes deployment",
    "category": "deployment"
  }'
```

## Factual Memory

Structured facts in subject-predicate-object format.

### Store Fact

```bash
curl -X POST "http://localhost:8223/api/v1/memory/factual" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user_123",
    "predicate": "prefers",
    "object": "dark_theme",
    "confidence": 1.0,
    "source": "user_settings",
    "valid_from": "2024-01-01T00:00:00Z"
  }'
```

### Query Facts

```bash
curl -X POST "http://localhost:8223/api/v1/memory/factual/query" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user_123",
    "predicate": "prefers"
  }'
```

Response:
```json
{
  "facts": [
    {
      "subject": "user_123",
      "predicate": "prefers",
      "object": "dark_theme",
      "confidence": 1.0
    },
    {
      "subject": "user_123",
      "predicate": "prefers",
      "object": "vim_keybindings",
      "confidence": 0.9
    }
  ]
}
```

## Memory Consolidation

### Consolidate Session to Long-Term

```bash
curl -X POST "http://localhost:8223/api/v1/memory/consolidate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123",
    "extract": ["episodic", "semantic", "factual"],
    "importance_threshold": 0.5
  }'
```

### AI-Powered Extraction

The memory service uses AI to automatically extract:
- Key events → Episodic memory
- Learned concepts → Semantic memory
- User preferences → Factual memory
- Procedures mentioned → Procedural memory

## Memory Search (Unified)

### Cross-Memory Search

```bash
curl -X POST "http://localhost:8223/api/v1/memory/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "user preferences for code editor",
    "memory_types": ["episodic", "semantic", "factual"],
    "limit": 10,
    "min_relevance": 0.7
  }'
```

Response:
```json
{
  "results": [
    {
      "type": "factual",
      "content": {"subject": "user_123", "predicate": "prefers", "object": "vim_keybindings"},
      "relevance": 0.95
    },
    {
      "type": "episodic",
      "content": "User mentioned they've been using VS Code for 3 years",
      "relevance": 0.82
    },
    {
      "type": "semantic",
      "content": "VS Code is a popular code editor by Microsoft",
      "relevance": 0.75
    }
  ]
}
```

## Python SDK

```python
from isa_user import MemoryClient

memory = MemoryClient("http://localhost:8223")

# Store episodic memory
await memory.store_episodic(
    token=access_token,
    content="User completed project setup",
    emotion="satisfied",
    importance=0.7
)

# Store fact
await memory.store_fact(
    token=access_token,
    subject="user_123",
    predicate="likes",
    object="python"
)

# Search memories
results = await memory.search(
    token=access_token,
    query="python programming preferences",
    memory_types=["episodic", "semantic", "factual"]
)

# Get session context
context = await memory.get_session(
    token=access_token,
    session_id="sess_abc123"
)
```

## Integration with RAG

```python
# Use memory for RAG context
memories = await memory.search(
    token=access_token,
    query=user_question,
    limit=5
)

context = "\n".join([m.content for m in memories])

# Generate response with memory context
response = await llm.generate(
    prompt=f"Context from memory:\n{context}\n\nQuestion: {user_question}"
)
```

## Next Steps

- [Architecture](./architecture) - Infrastructure details
- [Authentication](./authentication) - Auth services
- [Storage](./storage) - File management
