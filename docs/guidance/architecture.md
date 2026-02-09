# Architecture

Infrastructure, service discovery, and system design.

## Overview

isA User employs a modern microservices architecture with:

- **31 microservices** across 3 tiers
- **Service discovery** via Consul
- **API gateway** via APISIX
- **Event-driven** communication via NATS
- **Multi-database** strategy
- **Kubernetes** deployment

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL TRAFFIC                                   │
│                         (Port 80/443)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          APISIX GATEWAY                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Rate limiting      • Authentication    • Load balancing           │   │
│  │ • Request routing    • SSL termination   • Request transformation   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                         Consul Integration                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONSUL SERVICE REGISTRY                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Service registration    • Health checking    • KV store           │   │
│  │ • Dynamic routing         • Service metadata   • DNS interface      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MICROSERVICES LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    31 FastAPI Services                               │   │
│  │                    Ports 8201-8250                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                      ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────────────┐
│      NATS JETSTREAM             │ │              gRPC LAYER                  │
│  ┌───────────────────────────┐  │ │  ┌─────────────────────────────────┐   │
│  │ • Event streaming         │  │ │  │ • PostgreSQL gRPC (50051)       │   │
│  │ • Async messaging         │  │ │  │ • Redis gRPC (50052)            │   │
│  │ • Message persistence     │  │ │  │ • Qdrant gRPC (50053)           │   │
│  │ • Consumer groups         │  │ │  │ • MinIO gRPC (50054)            │   │
│  └───────────────────────────┘  │ │  │ • Neo4j gRPC (50055)            │   │
└─────────────────────────────────┘ │  └─────────────────────────────────┘   │
                                    └─────────────────────────────────────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │PostgreSQL│ │  Redis  │  │  Neo4j  │  │ Qdrant  │  │  MinIO  │          │
│  │ :5432   │  │ :6379   │  │ :7687   │  │ :6333   │  │ :9000   │          │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │
│  ┌─────────┐  ┌─────────┐                                                  │
│  │ DuckDB  │  │  MQTT   │                                                  │
│  │(Analytics)│ │ :1883   │                                                  │
│  └─────────┘  └─────────┘                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Discovery (Consul)

### Service Registration

Each service registers with Consul on startup:

```python
# core/consul_registry.py
async def register_service(
    service_name: str,
    port: int,
    health_check_path: str = "/health"
):
    await consul.agent.service.register(
        name=service_name,
        service_id=f"{service_name}-{instance_id}",
        port=port,
        check={
            "http": f"http://localhost:{port}{health_check_path}",
            "interval": "10s",
            "timeout": "5s"
        },
        meta={
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT")
        }
    )
```

### Route Metadata

Services register their routes for API gateway:

```python
# routes_registry.py
ROUTE_METADATA = {
    "service": "auth_service",
    "routes": [
        {"path": "/api/v1/auth/login", "methods": ["POST"], "auth": False},
        {"path": "/api/v1/auth/refresh", "methods": ["POST"], "auth": False},
        {"path": "/api/v1/auth/api-keys", "methods": ["GET", "POST"], "auth": True}
    ]
}
```

### Service Discovery

```python
# Find service instances
instances = await consul.catalog.service("auth_service")
# Returns: [{"Address": "10.0.0.1", "Port": 8201}, ...]
```

## API Gateway (APISIX)

### Route Configuration

```yaml
# APISIX route for auth service
routes:
  - uri: /api/v1/auth/*
    upstream:
      type: roundrobin
      discovery_type: consul
      service_name: auth_service
    plugins:
      jwt-auth:
        _meta:
          disable: true  # Login doesn't require auth
      rate-limit:
        count: 100
        time_window: 60
```

### Rate Limiting

| Endpoint Type | Limit |
|--------------|-------|
| Public (login) | 5/minute |
| Authenticated | 1000/hour |
| Admin | 10000/hour |

## Event-Driven Architecture (NATS)

### Event Publishing

```python
# Publish event
await nats.publish(
    "user.created",
    json.dumps({
        "user_id": "user_123",
        "email": "user@example.com",
        "timestamp": datetime.utcnow().isoformat()
    }).encode()
)
```

### Event Subscription

```python
# Subscribe to events
async def handle_user_created(msg):
    data = json.loads(msg.data.decode())
    # Process event
    await notification_service.send_welcome_email(data["user_id"])

await nats.subscribe("user.created", cb=handle_user_created)
```

### JetStream (Persistence)

```python
# Create durable stream
js = nats.jetstream()
await js.add_stream(
    name="USERS",
    subjects=["user.*"],
    retention="limits",
    max_msgs=1000000
)

# Durable consumer
await js.subscribe(
    "user.*",
    durable="user_processor",
    deliver_policy="all"
)
```

### Event Types

| Stream | Events |
|--------|--------|
| USERS | user.created, user.updated, user.deleted |
| PAYMENTS | payment.succeeded, payment.failed, refund.created |
| STORAGE | file.uploaded, file.deleted, file.shared |
| DEVICES | device.registered, device.online, device.offline |

## Database Strategy

### PostgreSQL (Primary)

Primary relational database with pgvector extension:

```python
# Connection via gRPC client
from core.postgres_client import PostgresClient

async with PostgresClient() as db:
    result = await db.execute(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
```

### Redis (Cache & Sessions)

```python
from core.redis_client import RedisClient

redis = RedisClient()

# Cache
await redis.set(f"user:{user_id}", user_data, ex=3600)
user = await redis.get(f"user:{user_id}")

# Session
await redis.hset(f"session:{session_id}", mapping=session_data)
```

### Neo4j (Graph)

For social relationships and hierarchies:

```python
from core.neo4j_client import Neo4jClient

async with Neo4jClient() as neo4j:
    # Create relationship
    await neo4j.run("""
        MATCH (u:User {id: $user_id})
        MATCH (o:Organization {id: $org_id})
        CREATE (u)-[:MEMBER_OF {role: $role}]->(o)
    """, user_id=user_id, org_id=org_id, role="admin")
```

### Qdrant (Vector)

For semantic search and memory:

```python
from core.qdrant_client import QdrantClient

qdrant = QdrantClient()

# Store embedding
await qdrant.upsert(
    collection_name="memories",
    points=[{
        "id": memory_id,
        "vector": embedding,
        "payload": {"content": content, "user_id": user_id}
    }]
)

# Search
results = await qdrant.search(
    collection_name="memories",
    query_vector=query_embedding,
    limit=10
)
```

### MinIO (Object Storage)

S3-compatible file storage:

```python
from core.minio_client import MinioClient

minio = MinioClient()

# Upload
await minio.put_object(
    bucket="user-files",
    object_name=f"{user_id}/{file_id}",
    data=file_data,
    content_type="image/jpeg"
)

# Generate presigned URL
url = await minio.presigned_get_object(
    bucket="user-files",
    object_name=f"{user_id}/{file_id}",
    expires=timedelta(hours=1)
)
```

## Service Structure

Each microservice follows a consistent pattern:

```
microservices/{service_name}/
├── main.py                    # FastAPI app entry point
├── {service}_service.py       # Business logic
├── {service}_repository.py    # Data access layer
├── models.py                  # Pydantic schemas
├── protocols.py               # Interface definitions
├── factory.py                 # Dependency injection
├── routes_registry.py         # API metadata for Consul
├── events/                    # Event definitions
│   ├── publishers.py
│   └── subscribers.py
├── clients/                   # Service-to-service clients
│   └── {other_service}_client.py
├── migrations/                # Database migrations
├── docs/                      # Service documentation
│   ├── domain.md
│   ├── prd.md
│   └── design.md
└── tests/                     # Test suite
    ├── unit/
    ├── component/
    └── integration/
```

## Dependency Injection

```python
# factory.py
from functools import lru_cache

@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(
        repository=get_auth_repository(),
        jwt_manager=get_jwt_manager(),
        event_publisher=get_event_publisher()
    )

# main.py
@app.post("/api/v1/auth/login")
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    return await service.login(request)
```

## Observability

### Logging (Loki)

```python
# Centralized logging
from core.logger import get_logger

logger = get_logger(__name__)

logger.info("User logged in", extra={
    "user_id": user_id,
    "ip_address": request.client.host,
    "user_agent": request.headers.get("user-agent")
})
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "auth_service",
        "version": "1.0.0",
        "dependencies": {
            "postgres": await check_postgres(),
            "redis": await check_redis(),
            "consul": await check_consul()
        }
    }
```

### Metrics

```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)
```

## Deployment

### Kubernetes

```yaml
# deployment/k8s/manifests/auth-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
  namespace: isa-cloud-staging
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    spec:
      containers:
        - name: auth-service
          image: isa/auth-service:latest
          ports:
            - containerPort: 8201
          envFrom:
            - configMapRef:
                name: user-config
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8201
            initialDelaySeconds: 10
            periodSeconds: 30
```

### Environment Configuration

```bash
# deployment/environments/staging.env
ENVIRONMENT=staging
DEBUG=false

# Database
POSTGRES_HOST=postgres.isa-cloud-staging
REDIS_HOST=redis.isa-cloud-staging

# Service Discovery
CONSUL_HOST=consul.isa-cloud-staging
CONSUL_PORT=8500

# Observability
LOKI_URL=http://loki.monitoring:3100
```

## Port Assignments

| Range | Purpose |
|-------|---------|
| 80, 443 | APISIX Gateway |
| 8201-8210 | Tier 1 Services |
| 8211-8230 | Tier 2 Services |
| 8250+ | Extended Services |
| 50051-50070 | gRPC Infrastructure |

## Security

### Authentication Flow

```
Client → APISIX → JWT Validation → Service
                      │
                      ▼
              auth_service (verify)
```

### Secrets Management

- Vault service for encrypted secrets
- Environment variables for non-sensitive config
- Kubernetes secrets for deployment

### Network Security

- Service mesh isolation
- mTLS between services (optional)
- Network policies in Kubernetes

## Next Steps

- [Quick Start](./quickstart) - Get started
- [Authentication](./authentication) - Auth details
- [Memory](./memory) - AI cognitive memory
