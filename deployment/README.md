# isA User Platform - Deployment Configuration

## Active Deployment Paths

The checked-in deployment assets now use one active layout:

- `deployment/docker/`: build Docker images for local Kind or remote registries
- `deployment/helm/`: render and deploy Kubernetes releases
- `deployment/_legacy/k8s/`: archived manifests and scripts, kept only for historical reference

## Environments

| Environment | Purpose | Active Assets |
|------------|---------|---------------|
| `dev` | local development and unit/component tests | `deployment/environments/dev.env`, `deployment/local-dev.sh` |
| `staging` | local Kind / shared staging clusters | `deployment/docker/*`, `deployment/helm/*` |
| `production` | production deploys | `deployment/docker/*`, `deployment/helm/*` |

Canonical Kubernetes namespaces are defined in `config/ports.yaml`:

- `staging`: `isa-cloud-staging`
- `production`: `isa-cloud-production`

## Directory Structure

```text
deployment/
├── README.md
├── docker/
│   ├── Dockerfile.base
│   ├── Dockerfile.microservice
│   └── build.sh
├── environments/
│   ├── dev.env
│   ├── staging.env
│   └── production.env
├── helm/
│   ├── deploy.sh
│   ├── values.yaml
│   ├── values-staging.yaml
│   └── values-production.yaml
├── local-dev.sh
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── agent.txt
└── _legacy/
    └── k8s/
```

## Quick Start

### 1. Local Development

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r deployment/requirements/dev.txt

set -a
source deployment/environments/dev.env
set +a

pytest tests/unit -v
pytest tests/component -v
```

### 2. Build Service Images

```bash
# Build base + every service for staging
./deployment/docker/build.sh

# Build one service only
./deployment/docker/build.sh --service auth
```

### 3. Preview or Deploy a Helm Release

`deployment/helm/deploy.sh` expects the shared `isa-service` chart from `isA_Cloud`.
If the chart is not in the default sibling repo location, set `ISA_SERVICE_CHART_PATH`.

```bash
# Dry-run a staging deploy
ISA_SERVICE_CHART_PATH=../isA_Cloud/deployments/charts/isa-service \
  ./deployment/helm/deploy.sh staging auth --dry-run

# Apply for real
ISA_SERVICE_CHART_PATH=../isA_Cloud/deployments/charts/isa-service \
  ./deployment/helm/deploy.sh staging auth
```

### 4. Kind Redeploy Helper

```bash
# Rebuild, load, and restart a single service in Kind
./scripts/redeploy_k8s.sh auth
```

### 5. Verify the Cluster

```bash
kubectl get pods -n isa-cloud-staging
kubectl get svc -n isa-cloud-staging
kubectl rollout status deployment/user-auth-service -n isa-cloud-staging
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
| 8251 | campaign | ✅ Deployed | Campaign management |
| 8252 | inventory | ✅ Deployed | Inventory management |
| 8253 | tax | ✅ Deployed | Tax calculation |
| 8254 | fulfillment | ✅ Deployed | Order fulfillment |
| 8260 | project | ✅ Deployed | Project workspaces, custom instructions |

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
