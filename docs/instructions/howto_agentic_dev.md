# Agentic Development Methodology

**AI-SDLC: A Complete Framework for AI-Driven Software Development**

---

## Executive Summary

This document describes a comprehensive methodology for AI-driven software development that combines:

1. **Contract-Driven Development (CDD)** - 6-layer documentation architecture
2. **Test-Driven Development (TDD)** - 5-layer test pyramid
3. **isA Vibe Agent Framework** - Specialized agents with multi-project targeting
4. **Claude Code Integration** - Skills and commands for interactive development

The methodology enforces **Single Point of Truth** principles and enables both:
- **CLI Mode (Default)** - Uses Claude Code skills, no API key required
- **API Mode** - Uses Claude API for automated pipelines (requires `ANTHROPIC_API_KEY`)

**Agent Framework Location**: `isA_Vibe` repository (shared across all isA projects)

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [Architecture Overview](#2-architecture-overview)
3. [Directory Structure](#3-directory-structure)
4. [The 6-Layer CDD Architecture](#4-the-6-layer-cdd-architecture)
5. [The 5-Layer Test Pyramid](#5-the-5-layer-test-pyramid)
6. [isA Vibe Agent Framework](#6-isa-vibe-agent-framework)
7. [Claude Code Integration](#7-claude-code-integration)
8. [Toolchain Setup](#8-toolchain-setup)
9. [Workflow Guide](#9-workflow-guide)
10. [Best Practices](#10-best-practices)
11. [Adopting This Methodology](#11-adopting-this-methodology)
12. [Current Gaps & Roadmap](#12-current-gaps--roadmap)

---

## 1. Core Philosophy

### 1.1 Single Point of Truth

Every concept has ONE authoritative source:

| Concept | Single Source | Location |
|---------|---------------|----------|
| Agent definitions | `agents/definitions.py` | isA_Vibe |
| CDD templates | `templates/service/cdd/` | isA_Vibe |
| TDD templates | `templates/service/tdd/` | isA_Vibe |
| Infrastructure ports | `config/ports.yaml` | Target project |
| Project metadata | `config/vibe.yaml` | Target project |
| Skills | `.claude/skills/` | Target project |

### 1.2 Contract-First Development

1. **Define contracts before code** - Documentation drives implementation
2. **Contracts are executable** - They generate tests and validate code
3. **Zero hardcoded data** - All test data from TestDataFactory

### 1.3 Dependency Injection by Design

```python
# Protocol-based interfaces (no I/O imports)
from .protocols import RepositoryProtocol

class Service:
    def __init__(self, repository: RepositoryProtocol):
        self.repo = repository  # Injected, not created
```

### 1.4 Event-Driven Architecture

```
Service A → NATS → [Event] → Service B subscribes
```

All significant state changes publish events.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI-SDLC Framework                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      isA_Vibe (Agent Framework)                       │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │  agents/cli.py  │  │  vibe_service/  │  │    templates/       │   │  │
│  │  │  (CLI Mode)     │  │  (API Mode)     │  │    service/         │   │  │
│  │  │                 │  │                 │  │                     │   │  │
│  │  │  --target flag  │  │  FastAPI +      │  │  - cdd/ (6 layers)  │   │  │
│  │  │  No API key     │  │  WebSocket      │  │  - tdd/ (5 layers)  │   │  │
│  │  │  DEFAULT        │  │  Needs API key  │  │  - system_contracts │   │  │
│  │  └────────┬────────┘  └────────┬────────┘  └─────────────────────┘   │  │
│  │           │                    │                                      │  │
│  └───────────┼────────────────────┼──────────────────────────────────────┘  │
│              │                    │                                         │
│              ▼                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Target Projects (via --target)                      │  │
│  │                                                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │  isA_user   │  │  isA_MCP    │  │  isA_Agent  │  │  Other...   │   │  │
│  │  │             │  │             │  │             │  │             │   │  │
│  │  │ config/     │  │ config/     │  │ config/     │  │ config/     │   │  │
│  │  │ vibe.yaml   │  │ vibe.yaml   │  │ vibe.yaml   │  │ vibe.yaml   │   │  │
│  │  │ ports.yaml  │  │ ports.yaml  │  │ ports.yaml  │  │ ports.yaml  │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Two Operating Modes

| Mode | Tool | API Key | Use Case |
|------|------|---------|----------|
| **CLI (Default)** | `agents/cli.py` + Claude Code | Not required | Interactive development, single service |
| **API** | `vibe_service/` + Claude API | Required | CI/CD, batch processing, automation |

### Project Targeting

isA_Vibe can target ANY project using the `--target` flag:

```bash
# Target isA_user project
cd isA_Vibe
python agents/cli.py --target ../isA_user --service memory --mode cdd

# Target isA_MCP project
python agents/cli.py --target ../isA_MCP --service tool --mode cdd
```

---

## 3. Directory Structure

### isA_Vibe (Agent Framework)

```
isA_Vibe/
├── agents/                           # AI-SDLC Agent Framework
│   ├── definitions.py                # All agent definitions
│   ├── orchestrator.py               # Agent orchestration engine
│   ├── cli.py                        # CLI interface with --target
│   ├── config/
│   │   ├── vibe.py                   # VibeConfig loader
│   │   └── ports.py                  # PortsConfig loader
│   ├── validators/                   # Contract validators
│   └── mcp_servers/                  # Custom MCP implementations
│
├── vibe_service/                     # API Mode (FastAPI)
│   ├── main.py                       # FastAPI app
│   ├── cli.py                        # Service CLI
│   ├── engines/                      # Project type engines
│   │   ├── base.py                   # Base engine
│   │   ├── microservice.py           # Python microservices
│   │   ├── data_product.py           # Data Mesh products
│   │   └── react_app.py              # React applications
│   └── models.py                     # Pydantic models
│
├── vibe_client/                      # Python SDK
│   └── __init__.py                   # VibeClient class
│
└── templates/                        # Single Point of Truth
    └── service/                      # Microservice templates
        ├── cdd/                      # CDD layer templates
        │   ├── domain_template.md
        │   ├── prd_template.md
        │   ├── design_template.md
        │   └── contracts/
        │       ├── data_contract_template.py
        │       ├── logic_contract_template.md
        │       └── system_contracts/
        │           ├── README.md
        │           ├── repository_service.md
        │           ├── cache_service.md
        │           ├── vector_service.md
        │           ├── facade_service.md
        │           ├── synchronizer_service.md
        │           └── mcp_component.md
        └── tdd/                      # TDD test templates
            ├── unit_template.py
            ├── component_template.py
            ├── integration_template.py
            ├── api_template.py
            └── smoke_template.py
```

### Target Project Structure (e.g., isA_user)

```
isA_user/
├── config/                           # Project configuration
│   ├── vibe.yaml                     # Project metadata (REQUIRED)
│   ├── ports.yaml                    # Port assignments
│   ├── dependencies.yaml             # Python dependencies
│   └── init.yaml                     # Initialization config
│
├── .claude/                          # Claude Code configuration
│   ├── settings.local.json           # MCP servers, permissions
│   └── skills/                       # Skills (linked to target)
│
├── docs/                             # Generated documentation
│   ├── domain/                       # Layer 1 outputs
│   ├── prd/                          # Layer 2 outputs
│   ├── design/                       # Layer 3 outputs
│   └── current_status.md             # Progress tracking
│
├── tests/                            # Test pyramid
│   ├── contracts/                    # Layer 4-6 outputs
│   ├── unit/
│   ├── component/
│   ├── integration/
│   ├── api/
│   └── smoke/
│
└── microservices/                    # Service implementations
    └── {service}_service/
        ├── main.py                   # FastAPI app
        ├── {service}_service.py      # Business logic
        ├── {service}_repository.py   # Data access
        ├── protocols.py              # DI interfaces
        ├── factory.py                # DI factory
        ├── clients/                  # HTTP clients
        ├── events/                   # NATS pub/sub
        └── migrations/               # SQL migrations
```

---

## 4. The 6-Layer CDD Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Documentation Layer (docs/)                                      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: Domain Context    │ Business taxonomy, rules, events   │
│ Layer 2: PRD               │ Epics, user stories, API surface   │
│ Layer 3: Design            │ Architecture, DB schema, data flow │
├─────────────────────────────────────────────────────────────────┤
│ Contract Layer (tests/contracts/)                                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: Data Contract     │ Pydantic schemas, TestDataFactory  │
│ Layer 5: Logic Contract    │ Business rules, state machines     │
│ Layer 6: System Contract   │ Implementation patterns            │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Details

| Layer | Output | Lines | Key Content |
|-------|--------|-------|-------------|
| 1 | `docs/domain/{svc}.md` | 500-600 | 25-35 business rules (BR-XXX-001) |
| 2 | `docs/prd/{svc}.md` | 700-800 | 5-7 epics, user stories |
| 3 | `docs/design/{svc}.md` | 900-1100 | SQL DDL, architecture diagrams |
| 4 | `tests/contracts/{svc}/data_contract.py` | 1100-1300 | 35+ factory methods |
| 5 | `tests/contracts/{svc}/logic_contract.md` | 1200-1400 | 40-50 rules, state machines |
| 6 | `tests/contracts/{svc}/system_contract.md` | ~400 | Pattern-specific implementation |

### System Contract Patterns (Layer 6)

isA_Vibe provides multiple system contract templates based on design patterns:

| Pattern | Based On | Use Case |
|---------|----------|----------|
| `repository_service` | Fowler Repository | Data-heavy services (account, storage) |
| `cache_service` | Fowler Cache-Aside | Caching services (session, config) |
| `vector_service` | Fowler Repository + Vector | Embedding services (memory, search) |
| `facade_service` | GoF Facade | Aggregation services (billing, auth) |
| `synchronizer_service` | EIP Synchronizer | Integration services (sync, import) |
| `mcp_component` | GoF Template Method | MCP tools, prompts, resources |

---

## 5. The 5-Layer Test Pyramid

```
                    ┌─────────────────┐
                    │   Layer 5       │  15-18 bash scripts
                    │   Smoke Tests   │  E2E validation
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 4       │  25-30 tests
                    │   API Tests     │  JWT auth, authorization
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 3       │  30-35 tests
                    │ Integration     │  Real HTTP + DB
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 2       │  75-85 tests
                    │ Component Tests │  Mocked dependencies
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 1       │  75-85 tests
                    │   Unit Tests    │  Pure functions
                    └─────────────────┘
```

### Infrastructure Requirements

| Layer | PostgreSQL | NATS | Auth | Service |
|-------|:----------:|:----:|:----:|:-------:|
| Unit | - | - | - | - |
| Component | - | - | - | - |
| Integration | Required | Optional | - | Required |
| API | Required | Optional | Required | Required |
| Smoke | Required | Required | Required | Required |

---

## 6. isA Vibe Agent Framework

### Agent Phases (5 Phases)

**Phase 1: Research & Design (CDD 6 Layers)**
- `cdd-domain-context` - Generate Layer 1
- `cdd-prd-specification` - Generate Layer 2
- `cdd-design-document` - Generate Layer 3
- `cdd-data-contract` - Generate Layer 4
- `cdd-logic-contract` - Generate Layer 5
- `cdd-system-contract` - Generate Layer 6

**Phase 2: TDD Development (5-Layer Test Pyramid)**
- `test-unit` - Unit tests (75-85)
- `test-component` - Component tests (75-85)
- `test-integration` - Integration tests (30-35)
- `test-api` - API tests (25-30)
- `test-smoke` - Smoke tests (15-18)

**Phase 3: Cloud Native Deployment**
- `docker-builder` - Build images
- `k8s-deployer` - Deploy to K8s
- `health-checker` - Verify health
- `traffic-shifter` - Blue-green/canary

**Phase 4: Operations & Feedback Loop**
- `monitor` - Monitor metrics
- `alert-handler` - Process alerts
- `auto-fix` - Auto-remediation
- `feedback-loop` - Capture learnings

**Phase 5: Tools & Configuration**
- `generate_config` - ConfigMap, env files from ports.yaml
- `port_forward` - kubectl port-forward management

### CLI Mode (Default) - No API Key Required

```bash
# Navigate to isA_Vibe
cd /path/to/isA_Vibe

# Target a project and run CDD
python agents/cli.py --target /path/to/isA_user --service credit --mode cdd

# Full pipeline for a service
python agents/cli.py --target /path/to/isA_user --service credit --mode full

# Multiple services in parallel
python agents/cli.py --target /path/to/isA_user \
  --services credit,membership,billing --mode cdd --parallel

# Specific layer only
python agents/cli.py --target /path/to/isA_user \
  --service credit --layer cdd-domain-context

# Check CDD status
python agents/cli.py --target /path/to/isA_user --status credit

# List available agents
python agents/cli.py --list-agents

# List services in target project
python agents/cli.py --target /path/to/isA_user --list-services

# Dry run (preview without executing)
python agents/cli.py --target /path/to/isA_user --service credit --mode cdd --dry-run
```

### API Mode - Requires Claude API Key

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Start Vibe service
cd /path/to/isA_Vibe
python -m vibe_service.cli server --port 8400

# Use vibe_client SDK
python -c "
from vibe_client import VibeClient

async def main():
    client = VibeClient('http://localhost:8400')
    result = await client.run_cdd(
        project_path='/path/to/isA_user',
        service='credit'
    )
    print(result)
"
```

### API Endpoints (API Mode)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects` | Create new project |
| GET | `/projects` | List all projects |
| GET | `/projects/{id}` | Get project details |
| POST | `/projects/{id}/cdd` | Run CDD pipeline |
| POST | `/projects/{id}/tdd` | Run TDD pipeline |
| POST | `/projects/{id}/deploy` | Deploy project |
| WS | `/projects/{id}/stream` | Stream execution output |

---

## 7. Claude Code Integration

### Skills (In Target Project)

Skills are defined in the target project's `.claude/skills/` directory:

| Skill | Purpose | Output |
|-------|---------|--------|
| `cdd-domain-context` | Generate Layer 1 | `docs/domain/{svc}.md` |
| `cdd-prd-specification` | Generate Layer 2 | `docs/prd/{svc}.md` |
| `cdd-design-document` | Generate Layer 3 | `docs/design/{svc}.md` |
| `cdd-data-contract` | Generate Layer 4 | `tests/contracts/{svc}/data_contract.py` |
| `cdd-logic-contract` | Generate Layer 5 | `tests/contracts/{svc}/logic_contract.md` |
| `cdd-system-contract` | Generate Layer 6 | `tests/contracts/{svc}/system_contract.md` |
| `cdd-test-pyramid` | Generate all tests | `tests/*/{svc}/` |
| `environment-context` | Infrastructure info | (read-only) |

### Commands (User-Invoked)

| Command | Usage | Action |
|---------|-------|--------|
| `/new-cdd-service` | `/new-cdd-service credit` | Full CDD workflow |
| `/check-cdd-status` | `/check-cdd-status credit` | Verify completion |
| `/run-service-tests` | `/run-service-tests credit` | Execute test pyramid |
| `/health-check` | `/health-check credit` | Check service health |
| `/port-forward` | `/port-forward` | Setup port forwarding |

---

## 8. Toolchain Setup

### Prerequisites

```bash
# Python environment
uv venv
source .venv/bin/activate

# Core dependencies (CLI mode - no API key needed)
uv pip install pyyaml click rich

# API mode dependencies (requires ANTHROPIC_API_KEY)
uv pip install anthropic fastapi uvicorn websockets httpx

# MCP dependencies
uv pip install mcp

# Infrastructure (for full pipeline)
# - Kubernetes cluster (Kind or real)
# - PostgreSQL with gRPC gateway
# - NATS JetStream
# - Redis with gRPC gateway
# - Consul
```

### Project Configuration (Required)

Each target project needs a `config/vibe.yaml`:

```yaml
# config/vibe.yaml
project:
  name: "isA_user"
  type: "microservice"
  version: "0.1.0"

source:
  services_path: "microservices"
  docs_path: "docs"
  tests_path: "tests"
  contracts_path: "tests/contracts"

cdd:
  layers:
    - domain
    - prd
    - design
    - data_contract
    - logic_contract
    - system_contract

tdd:
  layers:
    - unit
    - component
    - integration
    - api
    - smoke
```

### MCP Server Configuration (Optional)

```json
// .claude/settings.local.json
{
  "mcpServers": {
    "postgres": {
      "command": "python",
      "args": ["agents/mcp_servers/postgres_grpc_mcp.py"],
      "env": {"POSTGRES_GRPC_PORT": "50061"}
    },
    "nats": {
      "command": "python",
      "args": ["agents/mcp_servers/nats_mcp.py"],
      "env": {"NATS_GRPC_PORT": "50056"}
    }
  }
}
```

---

## 9. Workflow Guide

### 9.1 New Service (CLI Mode - Recommended)

```bash
# From isA_Vibe directory
cd /path/to/isA_Vibe

# Run full CDD for a new service
python agents/cli.py \
  --target /path/to/isA_user \
  --service credit \
  --description "Credit system for user rewards" \
  --mode cdd

# This generates:
# 1. docs/domain/credit_service.md      (Layer 1)
# 2. docs/prd/credit_service.md         (Layer 2)
# 3. docs/design/credit_service.md      (Layer 3)
# 4. tests/contracts/credit/data_contract.py     (Layer 4)
# 5. tests/contracts/credit/logic_contract.md    (Layer 5)
# 6. tests/contracts/credit/system_contract.md   (Layer 6)

# Then run TDD
python agents/cli.py \
  --target /path/to/isA_user \
  --service credit \
  --mode tdd

# This generates:
# 1. tests/unit/credit/
# 2. tests/component/credit/
# 3. tests/integration/credit/
# 4. tests/api/credit/
# 5. tests/smoke/credit/
```

### 9.2 New Service (Interactive Mode with Claude Code)

```bash
# In Claude Code within target project
/new-cdd-service credit

# Claude executes skills in sequence:
# 1. cdd-domain-context
# 2. cdd-prd-specification
# 3. cdd-design-document
# 4. cdd-data-contract
# 5. cdd-logic-contract
# 6. cdd-system-contract
# 7. cdd-test-pyramid
```

### 9.3 New Service (API Mode)

```python
# Requires ANTHROPIC_API_KEY
import asyncio
from vibe_client import VibeClient

async def create_service():
    client = VibeClient("http://localhost:8400")

    # Create project entry
    project = await client.create_project(
        name="credit_service",
        type="microservice",
        path="/path/to/isA_user/microservices/credit_service"
    )

    # Run CDD with streaming
    async for output in client.run_cdd_stream(project.id):
        print(output)

    # Run TDD
    async for output in client.run_tdd_stream(project.id):
        print(output)

asyncio.run(create_service())
```

### 9.4 TDD Red-Green-Refactor Cycle

```bash
# 1. RED: Write failing test from logic_contract
python agents/cli.py --target ../isA_user --service credit --layer tdd-red

# 2. GREEN: Implement minimal code
python agents/cli.py --target ../isA_user --service credit --layer tdd-green

# 3. REFACTOR: Optimize
python agents/cli.py --target ../isA_user --service credit --layer tdd-refactor
```

---

## 10. Best Practices

### 10.1 Zero Hardcoded Data

```python
# ❌ Wrong
user_id = "user_123"

# ✅ Correct
user_id = CreditTestDataFactory.make_user_id()
```

### 10.2 Protocol-Based Imports

```python
# ❌ Wrong - imports I/O at module level
from .credit_repository import CreditRepository

# ✅ Correct - import protocol (no I/O)
from .protocols import CreditRepositoryProtocol
```

### 10.3 Factory for Production

```python
# factory.py - ONLY place that imports real repository
def create_credit_service(config, event_bus):
    from .credit_repository import CreditRepository  # Import HERE
    return CreditService(
        repository=CreditRepository(config),
        event_bus=event_bus
    )
```

### 10.4 Event Publishing

```python
# Always publish events after successful operations
async def create_credit(self, request):
    credit = await self.repo.create(request.dict())
    await self.event_bus.publish(CreditCreatedEvent(credit))
    return credit
```

### 10.5 Business Rule Naming

```
BR-{SERVICE_CODE}-{NUMBER}: Rule Description
BR-CRE-001: Credit balance cannot be negative
BR-CRE-002: Credits expire after 365 days
```

---

## 11. Adopting This Methodology

### For New Projects

1. **Create config/vibe.yaml** (Required)
   ```yaml
   project:
     name: "my-project"
     type: "microservice"
     version: "0.1.0"
   source:
     services_path: "microservices"
     docs_path: "docs"
     tests_path: "tests"
   ```

2. **Create directory structure**
   ```bash
   mkdir -p config docs/{domain,prd,design} tests/{contracts,unit,component,integration,api,smoke}
   ```

3. **Run CDD from isA_Vibe**
   ```bash
   cd /path/to/isA_Vibe
   python agents/cli.py --target /path/to/my-project --service my_service --mode cdd
   ```

### For Existing Projects

1. **Add config/vibe.yaml** pointing to existing structure

2. **Start with contracts** (Layer 4-6)
   - Generate data_contract.py from existing models
   - Document business rules in logic_contract.md

3. **Add test layers incrementally**
   - Unit tests first (no infrastructure needed)
   - Then component tests with mocks
   - Finally integration/API/smoke

4. **Adopt DI pattern**
   - Create `protocols.py` for each service
   - Create `factory.py` for production instantiation

---

## 12. Current Gaps & Roadmap

### Completed

- [x] **Multi-project targeting** - `--target` flag in CLI
- [x] **Project scaffolding** - `scripts/init-agentic-project.sh`
- [x] **Port configuration** - `config/ports.yaml` (Single Point of Truth)
- [x] **System contract patterns** - 6 pattern templates
- [x] **API mode** - FastAPI service with WebSocket streaming

### Planned Improvements

- [ ] **Plugin system** - Custom agents without modifying core
- [ ] **Metrics dashboard** - Track CDD/TDD coverage
- [ ] **GitHub Actions integration** - CI/CD with Vibe agents
- [ ] **More project types** - data_product, react_app

### Contributing

1. Add new agents in `isA_Vibe/agents/definitions.py`
2. Add validation rules in `isA_Vibe/agents/validators/`
3. Update templates in `isA_Vibe/templates/`
4. Maintain Single Point of Truth principle

---

## Quick Reference

### Key Files

| Purpose | Location |
|---------|----------|
| Agent definitions | `isA_Vibe/agents/definitions.py` |
| CLI entry point | `isA_Vibe/agents/cli.py` |
| API service | `isA_Vibe/vibe_service/main.py` |
| CDD templates | `isA_Vibe/templates/service/cdd/` |
| TDD templates | `isA_Vibe/templates/service/tdd/` |
| Project config | `{target}/config/vibe.yaml` |
| Port config | `{target}/config/ports.yaml` |

### CLI Commands (isA_Vibe)

```bash
# Full pipeline
python agents/cli.py --target <path> --service <name> --mode full

# CDD only
python agents/cli.py --target <path> --service <name> --mode cdd

# TDD only
python agents/cli.py --target <path> --service <name> --mode tdd

# Specific layer
python agents/cli.py --target <path> --service <name> --layer cdd-domain-context

# Multiple services
python agents/cli.py --target <path> --services s1,s2,s3 --mode cdd --parallel

# Status check
python agents/cli.py --target <path> --status <service>

# List options
python agents/cli.py --list-agents
python agents/cli.py --target <path> --list-services
```

### Claude Code Commands (Target Project)

```
/new-cdd-service <service>      # Full CDD workflow
/check-cdd-status <service>     # Verify completion
/run-service-tests <service>    # Execute tests
/health-check [service]         # Check health
/port-forward                   # Setup port-forwarding
```

---

**Version**: 2.0.0
**Last Updated**: 2025-12
**Methodology**: AI-SDLC (AI-driven Software Development Lifecycle)
**Agent Framework**: isA_Vibe
