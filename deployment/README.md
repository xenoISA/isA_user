# isA User Platform - Deployment Configuration

## Overview

TDD/CDD AI Agent 驱动的开发模式，只需要两个环境：

| Environment | Purpose | Where | Tests |
|------------|---------|-------|-------|
| **dev** | 本地开发 | Local venv | unit, component |
| **test** | K8s 测试 | Kind K8s + port-forward | integration, api, smoke |

## K8s 环境详情

### Cluster & Namespace

| 项目 | 值 | 说明 |
|-----|-----|------|
| **Cluster** | `kind-isa-cloud-local` | Kind 本地 K8s 集群 |
| **Namespace** | `isa-cloud-staging` | 所有服务部署的 namespace |
| **Context** | `kind-isa-cloud-local` | kubectl 默认 context |

### 架构组件

```
                                    ┌─────────────────────────────────────┐
                                    │         Kind K8s Cluster            │
                                    │       (kind-isa-cloud-local)        │
                                    │                                     │
    External                        │   ┌─────────────────────────────┐   │
    ────────►  Port 8000  ─────────►│   │    APISIX Gateway           │   │
    (Smoke Tests)                   │   │    (API Gateway + LB)       │   │
                                    │   └──────────┬──────────────────┘   │
                                    │              │                      │
                                    │   ┌──────────▼──────────────────┐   │
                                    │   │    Consul                    │   │
                                    │   │    (Service Discovery)       │   │
                                    │   │    - 服务注册                │   │
                                    │   │    - 路由元数据              │   │
                                    │   └──────────┬──────────────────┘   │
                                    │              │                      │
                                    │   ┌──────────▼──────────────────┐   │
                                    │   │    Microservices            │   │
                                    │   │    (8201-8230 ports)        │   │
                                    │   └─────────────────────────────┘   │
                                    │                                     │
    Port-Forward                    │   ┌─────────────────────────────┐   │
    ────────►  8201-8230 ──────────►│   │    Direct Service Access    │   │
    (Integration/API Tests)         │   │    (bypass gateway)         │   │
                                    │   └─────────────────────────────┘   │
                                    │                                     │
                                    └─────────────────────────────────────┘
```

### APISIX 网关

| 项目 | 值 |
|-----|-----|
| **Service** | `apisix-gateway.isa-cloud-staging.svc.cluster.local` |
| **External Port** | `8000` (HTTP), `8443` (HTTPS) |
| **Admin Port** | `9180` |
| **Admin Key** | `edd1c9f034335f136f87ad84b625c8f1` |

**路由同步**: Consul → APISIX 自动同步
- CronJob: `consul-apisix-sync` (每5分钟)
- 脚本: `/Users/xenodennis/Documents/Fun/isA_Cloud/deployments/scripts/apisix/sync_routes_from_consul_k8s.sh`
- 只同步有 `api_path` 或 `base_path` 元数据的服务

> **注意**: `/health` 端点不会同步到网关，因为它不在服务的 api_path 中

### Consul 服务发现

| 项目 | 值 |
|-----|-----|
| **Service** | `consul-agent.isa-cloud-staging.svc.cluster.local` |
| **Port** | `8500` |
| **UI** | `http://localhost:8500/ui` (需 port-forward) |

**服务注册元数据**:
```json
{
  "api_path": "/api/v1/accounts",
  "base_path": "/api/v1/accounts",
  "auth_required": "true",
  "rate_limit": "100"
}
```

### 测试环境访问方式

| 测试类型 | 访问方式 | URL 示例 |
|---------|---------|---------|
| **Integration** | Port-forward 直连服务 | `http://localhost:8224/api/v1/locations` |
| **API** | Port-forward 直连服务 | `http://localhost:8224/api/v1/locations` |
| **Smoke** | APISIX 网关 | `http://localhost:8000/api/v1/locations` |

## Directory Structure

```
deployment/
├── README.md                    # This file
├── requirements/
│   ├── base.txt                 # Runtime dependencies (K8s images)
│   ├── dev.txt                  # Development + test dependencies (local venv)
│   └── agent.txt                # AI-SDLC Agent Framework (MCP + Anthropic SDK)
│
├── environments/
│   ├── dev.env                  # Local development config
│   └── test.env                 # K8s test config (port-forward)
│
└── k8s/                         # Kubernetes deployment
    ├── Dockerfile.base          # Base image with dependencies
    ├── Dockerfile.microservice  # Per-service image
    ├── build-all-images.sh      # Build script
    ├── user-configmap.yaml      # K8s ConfigMap
    ├── generate-manifests.sh    # Generate K8s manifests
    └── manifests/               # Service deployments
        └── *-deployment.yaml
```

## Quick Start

### 1. Local Development (Unit + Component Tests)

```bash
# Create venv with uv (first time only)
uv venv .venv
source .venv/bin/activate

# Install dev dependencies
uv pip install -r deployment/requirements/dev.txt

# Load dev environment
export $(cat deployment/environments/dev.env | xargs)

# Run unit and component tests
pytest tests/unit -v
pytest tests/component -v
```

### 2. K8s Testing (Integration + API + Smoke Tests)

```bash
# Start port forwarding (in separate terminal)
./scripts/port-forward-test.sh

# Load test environment
export $(cat deployment/environments/test.env | xargs)

# Run integration, API and smoke tests
pytest tests/integration -v
pytest tests/api -v
pytest tests/smoke -v
```

### 3. Build and Deploy to K8s

```bash
# Build base image
docker build -t isa-user-base:latest -f deployment/k8s/Dockerfile.base .
kind load docker-image isa-user-base:latest --name isa-cloud-local

# Build and deploy a service
./deployment/k8s/build-all-images.sh account
kubectl rollout restart deployment/account -n isa-cloud-staging
```

### 4. Port-Forward for Testing

```bash
# Terminal 1: Infrastructure
kubectl port-forward -n isa-cloud-staging svc/isa-postgres-grpc 50061:50061 &
kubectl port-forward -n isa-cloud-staging svc/nats 4222:4222 &
kubectl port-forward -n isa-cloud-staging svc/redis 6379:6379 &

# Terminal 2: APISIX Gateway (for smoke tests)
kubectl port-forward -n isa-cloud-staging svc/apisix-gateway 8000:8000 &

# Terminal 3: Services (for integration/api tests)
kubectl port-forward -n isa-cloud-staging svc/location 8224:8224 &
# ... other services as needed
```

### 5. Verify Environment

```bash
# Check cluster context
kubectl config current-context
# Expected: kind-isa-cloud-local

# Check pods in staging namespace
kubectl get pods -n isa-cloud-staging

# Test gateway access
curl http://localhost:8000/api/v1/accounts

# Test direct service access
curl http://localhost:8224/health
```

## Dependencies

### base.txt (Runtime)

Used by K8s Docker images. Contains only what's needed to run services:
- FastAPI, uvicorn, pydantic
- Database drivers (asyncpg, psycopg)
- Message queue (nats-py)
- Object storage (minio)
- Auth (python-jose, PyJWT, argon2-cffi)
- Monitoring (structlog, prometheus-client)
- isa-common, isa-model

### dev.txt (Development)

Includes base.txt plus development and testing tools:
- pytest, pytest-asyncio, pytest-cov, pytest-mock
- factory-boy, faker, syrupy
- black, isort, flake8, mypy
- mkdocs

### agent.txt (AI-SDLC Framework)

Includes dev.txt plus AI agent dependencies:
- claude-agent-sdk (Official Claude Agent SDK - same infra as Claude Code)
- mcp (Model Context Protocol SDK)
- python-consul (Consul service discovery)
- jsonschema (Contract validation)
- mistune (Markdown processing)

> Claude Agent SDK: https://github.com/anthropics/claude-agent-sdk-python

## Environment Variables

### dev.env

For local development without K8s:
- Uses localhost for all infrastructure
- Consul disabled by default
- Suitable for unit/component tests

### test.env

For testing against K8s:
- All service URLs point to localhost (via port-forward)
- Full service URL list for inter-service calls
- JWT configuration for API tests

## Service Ports

| Port | Service | Port | Service |
|------|---------|------|---------|
| 8201 | auth | 8216 | billing |
| 8202 | account | 8217 | calendar |
| 8203 | session | 8218 | weather |
| 8204 | authorization | 8219 | album |
| 8205 | audit | 8220 | device |
| 8206 | notification | 8221 | ota |
| 8207 | payment | 8222 | media |
| 8208 | wallet | 8223 | memory |
| 8209 | storage | 8224 | location |
| 8210 | order | 8225 | telemetry |
| 8211 | task | 8226 | compliance |
| 8212 | organization | 8227 | document |
| 8213 | invitation | 8228 | subscription |
| 8214 | vault | 8229 | credit |
| 8215 | product | 8230 | event |

### New Services (8250+)

Reserved ports for new services from `new_features.md`:

| Port | Service | Status | Description |
|------|---------|--------|-------------|
| 8250 | membership | ✅ Deployed | 会员等级、积分、特权管理 |
| 8251 | comments | Reserved | 通用评论系统，嵌套回复、点赞 |
| 8252 | relations | Reserved | 用户关系管理（关注、好友、拉黑）|

> **Note**: Infrastructure services use 50xxx range (gRPC), no conflict with 82xx range.

## Test Pyramid

```
                    ┌─────────────┐
                    │   Smoke     │  ← K8s
                    ├─────────────┤
                    │    API      │  ← K8s
                    ├─────────────┤
                    │ Integration │  ← K8s
                ────┼─────────────┼────
                    │  Component  │  ← Local
                    ├─────────────┤
                    │    Unit     │  ← Local
                    └─────────────┘
```

## AI-SDLC Agent Development

### Setup Agent Environment

```bash
# Install agent dependencies (includes dev.txt)
uv pip install -r deployment/requirements/agent.txt

# Verify Claude Agent SDK installed
python -c "from claude_agent_sdk import query; print('Claude Agent SDK OK')"

# Verify MCP SDK installed
python -c "from mcp.server import Server; print('MCP SDK OK')"

# Test agents package
python -m agents.task_coordinator
```

### Agent Usage

```python
from agents import TaskCoordinator, create_task_prompt, create_pipeline_prompt

# Create prompts for Claude Code Task tool
config = create_task_prompt("memory", "domain-context")
cdd_prompt = create_pipeline_prompt("memory", "cdd")
```

### Run MCP Servers

```bash
# PostgreSQL MCP (requires port-forward to 50061)
python agents/mcp_servers/postgres_grpc_mcp.py

# NATS MCP (requires port-forward to 50056)
python agents/mcp_servers/nats_mcp.py

# Consul MCP (requires Consul at 8500)
python agents/mcp_servers/consul_mcp.py
```

## Related Docs

- [Testing Guide](../tests/README.md)
- [CDD Guide](../docs/CDD_GUIDE.md)
- [AI-SDLC Architecture](../agents/docs/ai_sdlc_architecture.md)
- [Deployment Status](../agents/docs/deployment_status.md)
