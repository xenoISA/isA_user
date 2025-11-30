# isA User Platform

A comprehensive microservices-based user management platform built with FastAPI, featuring 27 specialized services for authentication, payments, storage, IoT device management, AI-powered intelligence, and more.

## 🏗️ Architecture Overview

The isA User Platform follows a modern microservices architecture with:

- **27 Microservices**: Specialized services handling different aspects of user management and business logic
- **gRPC Infrastructure Layer**: All infrastructure services accessed via gRPC for performance and type safety
- **Service Discovery**: Consul-based service registration and discovery
- **Event-Driven**: NATS-based event streaming for inter-service communication
- **Centralized Logging**: Loki integration for unified log aggregation
- **Multi-Database Architecture**: PostgreSQL, Redis, Neo4j, Qdrant, DuckDB for different data workloads
- **AI/ML Integration**: Intelligent indexing, embeddings, and analytics
- **API Gateway**: Unified entry point for all services
- **Docker & Kubernetes Support**: Containerized deployment with K8s orchestration

## 📦 Microservices

### Core Authentication & Authorization Services

| Service | Port | Description |
|---------|------|-------------|
| **auth_service** | 8201 | Authentication, JWT verification, API key management, device auth |
| **account_service** | 8202 | User account management and profiles |
| **session_service** | 8203 | User session tracking and management |
| **authorization_service** | 8204 | Role-based access control (RBAC) |
| **audit_service** | 8205 | Audit logging and compliance tracking |
| **compliance_service** | 8226 | Regulatory compliance and data governance |

### Business Services

| Service | Port | Description |
|---------|------|-------------|
| **payment_service** | 8207 | Stripe integration, subscriptions, invoices |
| **wallet_service** | 8209 | Virtual wallet and credit management |
| **order_service** | 8210 | Order processing and management |
| **billing_service** | 8216 | Billing cycles, invoices, usage tracking |
| **product_service** | 8215 | Product catalog and management |
| **organization_service** | 8212 | Multi-tenant organization and family sharing |
| **invitation_service** | 8213 | User invitation system |
| **task_service** | 8211 | Asynchronous task management |
| **vault_service** | 8214 | Secure data vault with encryption |

### Media & Content Services

| Service | Port | Description |
|---------|------|-------------|
| **storage_service** | 8208 | MinIO-based file storage with S3 compatibility, intelligent indexing |
| **media_service** | - | Media processing and management |
| **album_service** | - | Photo album management and organization |
| **memory_service** | - | Multi-type memory system (episodic, semantic, working, procedural, factual) |

### Calendar & Location Services

| Service | Port | Description |
|---------|------|-------------|
| **calendar_service** | - | Calendar and event management |
| **location_service** | - | Location tracking and geospatial services |
| **weather_service** | - | Weather data integration |

### Infrastructure Services

| Service | Port | Description |
|---------|------|-------------|
| **notification_service** | 8206 | Multi-channel notification delivery |
| **event_service** | 8230 | Event sourcing and NATS integration |

### IoT Services

| Service | Port | Description |
|---------|------|-------------|
| **device_service** | 8220 | IoT device registration and management |
| **ota_service** | 8221 | Over-the-air firmware updates |
| **telemetry_service** | 8225 | Device telemetry data collection and analytics |

## 🚀 Quick Start

### Prerequisites

**Databases & Storage:**
- PostgreSQL 15+ (with pgvector extension)
- Redis (caching and pub/sub)
- Neo4j (graph database for relationships)
- Qdrant (vector database for embeddings)
- DuckDB (analytics database)
- MinIO (S3-compatible object storage)

**Message & Events:**
- NATS (event streaming)
- MQTT (IoT device messaging)
- Consul (service discovery)

**Observability:**
- Loki (centralized logging)
- Grafana (log visualization)

**Runtime:**
- Python 3.11+
- Docker & Docker Compose
- Kubernetes (for production deployment)

### Local Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd isA_user
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
uv pip install -r deployment/dev/requirements.txt
# or
pip install -r deployment/dev/requirements.txt
```

4. **Configure environment**
```bash
# Copy example environment file
cp deployment/.env.example deployment/dev/.env

# Edit configuration
nano deployment/dev/.env
```

5. **Start infrastructure services**
```bash
# Start Supabase (PostgreSQL)
cd /path/to/supabase && supabase start

# Start Consul
consul agent -dev

# Start NATS
nats-server

# Start MinIO
minio server /data

# Start Loki & Grafana (via Docker)
docker-compose -f deployment/docker/loki-stack.yml up -d
```

6. **Start all services**
```bash
# Start all microservices in development environment
./deployment/scripts/start_user_service.sh start

# Or start specific service in dev mode (with auto-reload)
./deployment/scripts/start_user_service.sh dev payment_service
```

### Docker Deployment

1. **Build all service images**
```bash
./deployment/docker/build.sh all dev latest
```

2. **Build specific service**
```bash
./deployment/docker/build.sh payment_service dev latest
```

3. **Run service container**
```bash
docker run -d \
  --name payment_service \
  -p 8207:8207 \
  --env-file deployment/dev/.env \
  isa-user/payment:latest
```

### Kubernetes Deployment

```bash
# Deploy to staging namespace
kubectl apply -f deployment/k8s/namespace.yaml
kubectl apply -f deployment/k8s/user-configmap.yaml
kubectl apply -f deployment/k8s/deployments/

# Check deployment status
kubectl get pods -n isa-cloud-staging
kubectl get svc -n isa-cloud-staging
```

## 🛠️ Service Management

### Start/Stop Services

```bash
# Start all services
./deployment/scripts/start_user_service.sh start

# Stop all services
./deployment/scripts/start_user_service.sh stop

# Restart all services
./deployment/scripts/start_user_service.sh restart

# Restart specific service
./deployment/scripts/start_user_service.sh restart payment_service

# Start in development mode (auto-reload)
./deployment/scripts/start_user_service.sh dev payment_service
```

### Check Service Status

```bash
# View all service status
./deployment/scripts/start_user_service.sh status

# View service logs
./deployment/scripts/start_user_service.sh logs payment_service

# Test service endpoints
./deployment/scripts/start_user_service.sh test
```

### Environment Management

```bash
# Start with specific environment
./deployment/scripts/start_user_service.sh --env test start
./deployment/scripts/start_user_service.sh --env staging start
./deployment/scripts/start_user_service.sh --env prod start
```

## 📚 API Documentation

Each service exposes Swagger/OpenAPI documentation:

- **Auth Service**: http://localhost:8201/docs
- **Account Service**: http://localhost:8202/docs
- **Session Service**: http://localhost:8203/docs
- **Authorization Service**: http://localhost:8204/docs
- **Audit Service**: http://localhost:8205/docs
- **Notification Service**: http://localhost:8206/docs
- **Payment Service**: http://localhost:8207/docs
- **Storage Service**: http://localhost:8208/docs
- **Wallet Service**: http://localhost:8209/docs
- **Order Service**: http://localhost:8210/docs
- **Task Service**: http://localhost:8211/docs
- **Organization Service**: http://localhost:8212/docs
- **Invitation Service**: http://localhost:8213/docs
- **Vault Service**: http://localhost:8214/docs
- **Product Service**: http://localhost:8215/docs
- **Billing Service**: http://localhost:8216/docs
- **Device Service**: http://localhost:8220/docs
- **OTA Service**: http://localhost:8221/docs
- **Telemetry Service**: http://localhost:8225/docs
- **Compliance Service**: http://localhost:8226/docs
- **Event Service**: http://localhost:8230/docs

## 🔧 Configuration

### Environment Variables

Key configuration variables in `deployment/dev/.env`:

```bash
# Environment
ENV=development
DB_SCHEMA=dev

# Database (Supabase Local)
SUPABASE_LOCAL_URL=http://127.0.0.1:54321
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres?options=-c%20search_path%3Ddev

# Service Discovery (Consul)
CONSUL_ENABLED=true
CONSUL_HOST=localhost
CONSUL_PORT=8500

# Event Streaming (NATS)
NATS_ENABLED=true
NATS_URL=nats://localhost:4222

# Object Storage (MinIO)
MINIO_ENABLED=true
MINIO_ENDPOINT=localhost:9000

# Centralized Logging (Loki)
LOKI_ENABLED=true
LOKI_URL=http://localhost:3100
LOG_LEVEL=DEBUG
```

### gRPC Infrastructure Services (Kubernetes)

In Kubernetes environments, all infrastructure services are accessed via gRPC:

```bash
# PostgreSQL gRPC
POSTGRES_GRPC_HOST=postgres-grpc.isa-cloud-staging.svc.cluster.local
POSTGRES_GRPC_PORT=50061

# Redis gRPC
REDIS_GRPC_HOST=redis-grpc.isa-cloud-staging.svc.cluster.local
REDIS_GRPC_PORT=50055

# NATS gRPC
NATS_GRPC_HOST=nats-grpc.isa-cloud-staging.svc.cluster.local
NATS_GRPC_PORT=50056

# MinIO gRPC
MINIO_GRPC_HOST=minio-grpc.isa-cloud-staging.svc.cluster.local
MINIO_GRPC_PORT=50051

# MQTT gRPC
MQTT_GRPC_HOST=mqtt-grpc.isa-cloud-staging.svc.cluster.local
MQTT_GRPC_PORT=50053

# Neo4j gRPC (Graph Database)
NEO4J_GRPC_HOST=neo4j-grpc.isa-cloud-staging.svc.cluster.local
NEO4J_GRPC_PORT=50063

# Qdrant gRPC (Vector Database)
QDRANT_GRPC_HOST=qdrant-grpc.isa-cloud-staging.svc.cluster.local
QDRANT_GRPC_PORT=50062

# DuckDB gRPC (Analytics Database)
DUCKDB_GRPC_HOST=duckdb-grpc.isa-cloud-staging.svc.cluster.local
DUCKDB_GRPC_PORT=50052

# Loki gRPC (Logging)
LOKI_GRPC_HOST=loki-grpc.isa-cloud-staging.svc.cluster.local
LOKI_GRPC_PORT=50054
```

### AI/ML Services

```bash
# MCP Service (Intelligence/Analytics)
MCP_ENDPOINT=http://mcp.isa-cloud-staging.svc.cluster.local:8081

# ISA Model Service (AI extraction + embeddings)
ISA_MODEL_URL=http://model.isa-cloud-staging.svc.cluster.local:8082
```

### Service-Specific Configuration

Each service can have specific overrides using the pattern `{SERVICE_NAME}_{VARIABLE}`:

```bash
PAYMENT_SERVICE_PORT=8207
PAYMENT_SERVICE_STRIPE_SECRET_KEY=sk_test_...
STORAGE_SERVICE_MINIO_BUCKET_NAME=custom-bucket
VAULT_SERVICE_MASTER_KEY=your-master-key
```

## 📊 Centralized Logging with Loki

All services automatically send logs to Loki for centralized aggregation:

```bash
# View logs in Grafana
http://localhost:3003

# Query logs via LogQL
{service="payment"}
{service="payment", logger="API"}
{service="payment"} |= "error"
{service=~"payment|wallet|order"} |= "transaction"
```

**Log Labels:**
- `service`: Service name (payment, auth, wallet, etc.)
- `logger`: Component (main, API, Stripe, etc.)
- `environment`: development/staging/production
- `job`: {service}_service

## 🐳 Docker Images

All services use a unified naming convention:

```
isa-user/{service}:{tag}
```

**Example Images:**
- `isa-user/auth:latest`
- `isa-user/payment:latest`
- `isa-user/wallet:latest`
- `isa-user/storage:latest`
- `isa-user/memory:latest`
- `isa-user/media:latest`

All images share the same base layer for efficiency.

## 🗄️ Multi-Database Architecture

The platform uses specialized databases for different workloads:

### PostgreSQL (Primary Relational DB)
- User accounts, authentication, sessions
- Orders, payments, billing records
- Organizations, invitations
- Accessed via gRPC in K8s, direct connection in dev

### Redis (Cache & Pub/Sub)
- Session caching
- Rate limiting
- Real-time notifications
- Accessed via gRPC adapter

### Neo4j (Graph Database)
- Social relationships
- Organization hierarchies
- Family sharing graphs
- Accessed via gRPC adapter

### Qdrant (Vector Database)
- Semantic search
- AI embeddings
- Similar content discovery
- Memory service (episodic, semantic memory)
- Accessed via gRPC adapter

### DuckDB (Analytics Database)
- OLAP queries
- Telemetry analytics
- Usage reports
- Accessed via gRPC adapter

### MinIO (Object Storage)
- File storage (S3-compatible)
- Media files
- Backups
- Accessed via gRPC adapter

## 🧠 Memory Service Architecture

The memory service implements a multi-layered memory system:

- **Episodic Memory**: Event sequences and experiences (Qdrant)
- **Semantic Memory**: Facts and knowledge (Qdrant)
- **Working Memory**: Short-term active information (Redis)
- **Procedural Memory**: Skills and procedures (PostgreSQL)
- **Factual Memory**: Structured facts (PostgreSQL)
- **Session Memory**: Context within sessions (Redis)

## 🔒 Security Features

- **JWT Authentication**: Auth0 and local JWT support
- **API Key Management**: Service-to-service authentication
- **Role-Based Access Control**: Fine-grained permissions
- **Rate Limiting**: Configurable request throttling
- **Audit Logging**: Complete audit trail for compliance
- **Encryption**: Data encryption at rest and in transit (Vault Service)
- **Compliance Tracking**: Regulatory compliance monitoring

## 🧪 Testing

```bash
# Run tests for specific service
pytest tests/test_payments.py

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=microservices

# Run integration tests (event-driven)
./microservices/payment_service/tests/integration/test_event_publishing.sh
./microservices/order_service/tests/integration/test_event_subscriptions.sh
```

**Test Status**: 25/27 services passing integration tests

## 📁 Project Structure

```
isA_user/
├── core/                      # Shared core modules
│   ├── config_manager.py      # Configuration management
│   ├── consul_registry.py     # Service discovery
│   ├── logger.py              # Centralized logging setup
│   ├── logging_config.py      # Loki integration
│   ├── nats_client.py         # Event streaming
│   └── database/              # Database utilities
├── isa_common_local/          # Common gRPC client library
│   ├── isa_common/
│   │   ├── postgres_client.py # PostgreSQL gRPC client
│   │   ├── redis_client.py    # Redis gRPC client
│   │   ├── neo4j_client.py    # Neo4j gRPC client
│   │   ├── qdrant_client.py   # Qdrant gRPC client
│   │   ├── duckdb_client.py   # DuckDB gRPC client
│   │   ├── minio_client.py    # MinIO gRPC client
│   │   ├── mqtt_client.py     # MQTT gRPC client
│   │   ├── nats_client.py     # NATS client
│   │   ├── loki_client.py     # Loki gRPC client
│   │   └── consul_client.py   # Consul client
│   └── proto/                 # Protocol buffer definitions
├── microservices/             # Individual microservices (27 services)
│   ├── auth_service/
│   ├── account_service/
│   ├── session_service/
│   ├── authorization_service/
│   ├── audit_service/
│   ├── compliance_service/
│   ├── payment_service/
│   ├── wallet_service/
│   ├── order_service/
│   ├── billing_service/
│   ├── product_service/
│   ├── organization_service/
│   ├── invitation_service/
│   ├── task_service/
│   ├── vault_service/
│   ├── storage_service/
│   ├── media_service/
│   ├── album_service/
│   ├── memory_service/
│   ├── notification_service/
│   ├── event_service/
│   ├── calendar_service/
│   ├── location_service/
│   ├── weather_service/
│   ├── device_service/
│   ├── ota_service/
│   └── telemetry_service/
├── deployment/                # Deployment configurations
│   ├── dev/                   # Development environment
│   │   ├── .env
│   │   └── requirements.txt
│   ├── docker/                # Docker configurations
│   │   ├── Dockerfile.user
│   │   └── build.sh
│   ├── k8s/                   # Kubernetes manifests
│   │   ├── namespace.yaml
│   │   ├── user-configmap.yaml
│   │   └── deployments/
│   └── scripts/               # Management scripts
│       └── start_user_service.sh
├── tests/                     # Test suites
└── docs/                      # Documentation
```

## 🔄 Service Dependencies

```
┌─────────────────────────────────────────┐
│         API Gateway (Kong/Nginx)        │
└────────────────┬────────────────────────┘
                 │
    ┌────────────▼─────────────────────────┐
    │  Service Discovery (Consul)          │
    └────────────┬─────────────────────────┘
                 │
    ┌────────────▼─────────────────────────┐
    │  Event Bus (NATS)                    │
    └────────────┬─────────────────────────┘
                 │
    ┌────────────▼─────────────────────────┐
    │  27 Microservices                    │
    │  - Core: Auth, Account, Session...   │
    │  - Business: Payment, Order, Wallet  │
    │  - Media: Storage, Album, Memory     │
    │  - IoT: Device, OTA, Telemetry       │
    │  - Calendar: Calendar, Location...   │
    └────────────┬─────────────────────────┘
                 │
    ┌────────────▼─────────────────────────┐
    │  gRPC Infrastructure Layer           │
    │  - PostgreSQL, Redis, Neo4j          │
    │  - Qdrant, DuckDB, MinIO             │
    │  - MQTT, Loki                        │
    └────────────┬─────────────────────────┘
                 │
    ┌────────────▼─────────────────────────┐
    │  AI/ML Services                      │
    │  - MCP (Intelligence)                │
    │  - ISA Model (Embeddings)            │
    └──────────────────────────────────────┘
```

## 🚢 Deployment Environments

### Development
```bash
./deployment/scripts/start_user_service.sh --env dev start
```

### Testing
```bash
./deployment/scripts/start_user_service.sh --env test start
```

### Staging (Kubernetes)
```bash
kubectl apply -f deployment/k8s/ -n isa-cloud-staging
```

### Production (Kubernetes)
```bash
kubectl apply -f deployment/k8s/ -n isa-cloud-production
```

## 📈 Monitoring & Observability

- **Health Checks**: `/health` endpoint on each service
- **Service Status**: Consul UI at http://localhost:8500
- **Logs**: Grafana + Loki at http://localhost:3003
- **Metrics**: Prometheus-compatible metrics (optional)
- **Tracing**: OpenTelemetry integration (planned)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push branch: `git push origin feature/new-feature`
5. Create Pull Request

## 📝 Development Workflow

1. **Add new service**:
   - Create service directory in `microservices/`
   - Implement service logic
   - Add to service list in deployment configs
   - Build Docker image
   - Add K8s deployment manifest

2. **Update existing service**:
   - Modify service code
   - Run tests
   - Rebuild Docker image
   - Restart service

3. **Deploy changes**:
   - Build images: `./deployment/docker/build.sh all dev latest`
   - Push to registry (if needed)
   - Update K8s deployment: `kubectl apply -f deployment/k8s/`

## 🆘 Troubleshooting

### Service won't start
```bash
# Check logs
./deployment/scripts/start_user_service.sh logs <service_name>

# Check port availability
lsof -i :8207

# Verify environment variables
cat deployment/dev/.env
```

### Database connection issues
```bash
# Check database is running
psql -h localhost -U postgres -d isa_platform

# Verify DATABASE_URL in .env
echo $DATABASE_URL

# Test gRPC connection (in K8s)
grpcurl -plaintext postgres-grpc:50061 list
```

### Consul registration failed
```bash
# Check Consul is running
curl http://localhost:8500/v1/status/leader

# Check service registration
curl http://localhost:8500/v1/agent/services

# Restart Consul
consul agent -dev
```

### gRPC connection issues (Kubernetes)
```bash
# Check gRPC services are running
kubectl get svc -n isa-cloud-staging | grep grpc

# Test gRPC endpoint
kubectl run -it --rm grpcurl --image=fullstorydev/grpcurl:latest \
  --restart=Never -- -plaintext postgres-grpc.isa-cloud-staging:50061 list
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 📞 Support

- **Documentation**: Check service-specific `/docs` endpoints
- **Issues**: Submit via GitHub Issues
- **Community**: Join our discussion forum

---

**Version**: 3.0.0  
**Last Updated**: 2025-11-20  
**Branch**: release/staging-v0.1.0  
**Status**: ✅ Production Ready with gRPC Infrastructure

**Key Features**:
- ✅ 27 Microservices (expanded from 17)
- ✅ gRPC Infrastructure Layer
- ✅ Multi-Database Architecture (PostgreSQL, Redis, Neo4j, Qdrant, DuckDB)
- ✅ Centralized Loki Logging
- ✅ Docker & Kubernetes Support
- ✅ Service Discovery (Consul)
- ✅ Event Streaming (NATS)
- ✅ AI/ML Integration (MCP, ISA Model)
- ✅ IoT Support (MQTT, Device Management)
- ✅ Memory System (Multi-layered cognitive architecture)
- ✅ Unified Management Scripts
- ✅ 25/27 Services Passing Integration Tests

**Recent Updates**:
- Added 10 new microservices (album, billing, calendar, compliance, location, media, memory, product, vault, weather)
- Implemented gRPC infrastructure layer for all database and messaging services
- Integrated Neo4j for graph relationships
- Integrated Qdrant for vector search and AI embeddings
- Added DuckDB for analytics workloads
- Implemented multi-layered memory service
- Added intelligent storage indexing with AI extraction
- Kubernetes deployment with staging environment
- Event-driven architecture improvements
