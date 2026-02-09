#!/usr/bin/env bash
# ============================================================================
# Agentic Development Project Initialization Script
# ============================================================================
# Initializes or updates a project with the AI-SDLC framework structure
#
# Usage:
#   ./init-agentic-project.sh [OPTIONS]
#
# Options:
#   --name NAME           Project name (default: current directory name)
#   --mode MODE           Init mode: 'new' or 'existing' (auto-detected)
#   --force               Overwrite existing files
#   --dry-run             Show what would be done without making changes
#   --skip-deps           Skip dependency installation
#   --skip-mcp            Skip MCP server setup
#   --verbose             Verbose output
#   --help                Show this help message
#
# Examples:
#   # Initialize new project
#   ./init-agentic-project.sh --name myproject
#
#   # Update existing project (auto-detects existing structure)
#   ./init-agentic-project.sh
#
#   # Preview changes without applying
#   ./init-agentic-project.sh --dry-run
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
PROJECT_NAME="${PWD##*/}"
MODE="auto"
FORCE=false
DRY_RUN=false
SKIP_DEPS=false
SKIP_MCP=false
VERBOSE=false

# Script directory (for copying templates)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if $VERBOSE; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

print_help() {
    head -n 30 "$0" | tail -n 27 | sed 's/^# //' | sed 's/^#//'
}

# ============================================================================
# Argument Parsing
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --skip-mcp)
            SKIP_MCP=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            print_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

# ============================================================================
# Structure Detection
# ============================================================================

detect_existing_structure() {
    local has_claude=false
    local has_agents=false
    local has_templates=false
    local has_tests=false
    local has_docs=false
    local has_config=false

    [[ -d ".claude" ]] && has_claude=true
    [[ -d "agents" ]] && has_agents=true
    [[ -d "templates" ]] && has_templates=true
    [[ -d "tests" ]] && has_tests=true
    [[ -d "docs" ]] && has_docs=true
    [[ -f "config/ports.yaml" ]] && has_config=true

    # Return detection results
    echo "CLAUDE=$has_claude"
    echo "AGENTS=$has_agents"
    echo "TEMPLATES=$has_templates"
    echo "TESTS=$has_tests"
    echo "DOCS=$has_docs"
    echo "CONFIG=$has_config"
}

auto_detect_mode() {
    local existing_count=0

    [[ -d ".claude" ]] && ((existing_count++)) || true
    [[ -d "agents" ]] && ((existing_count++)) || true
    [[ -d "templates" ]] && ((existing_count++)) || true
    [[ -d "tests" ]] && ((existing_count++)) || true

    if [[ $existing_count -eq 0 ]]; then
        echo "new"
    else
        echo "existing"
    fi
}

# ============================================================================
# Directory Creation Functions
# ============================================================================

create_directory_structure() {
    log_info "Creating directory structure..."

    local dirs=(
        # Claude Code structure
        ".claude/commands"
        ".claude/skills/cdd-domain-context"
        ".claude/skills/cdd-prd-specification"
        ".claude/skills/cdd-design-document"
        ".claude/skills/cdd-data-contract"
        ".claude/skills/cdd-logic-contract"
        ".claude/skills/cdd-system-contract"
        ".claude/skills/cdd-test-pyramid"
        ".claude/skills/environment-context"

        # Agent framework
        "agents/mcp_servers"
        "agents/validators"
        "agents/deployment"
        "agents/ops"
        "agents/docs"

        # Templates - CDD
        "templates/cdd/contracts"

        # Templates - TDD
        "templates/tdd/unit"
        "templates/tdd/component"
        "templates/tdd/integration"
        "templates/tdd/api"
        "templates/tdd/smoke"

        # Documentation
        "docs/domain"
        "docs/prd"
        "docs/design"

        # Tests
        "tests/contracts"
        "tests/fixtures"
        "tests/unit"
        "tests/component"
        "tests/integration/golden"
        "tests/integration/tdd"
        "tests/api"
        "tests/smoke"
        "tests/scripts"

        # Configuration
        "config"

        # Deployment
        "deployment/environments"
        "deployment/k8s/manifests"
        "deployment/requirements"

        # Microservices
        "microservices"

        # Scripts
        "scripts"
    )

    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            if $DRY_RUN; then
                log_info "[DRY-RUN] Would create: $dir"
            else
                mkdir -p "$dir"
                log_verbose "Created: $dir"
            fi
        else
            log_verbose "Exists: $dir"
        fi
    done

    log_success "Directory structure ready"
}

# ============================================================================
# Configuration File Generation
# ============================================================================

create_ports_config() {
    local target="config/ports.yaml"

    if [[ -f "$target" ]] && ! $FORCE; then
        log_verbose "Skipping existing: $target"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY-RUN] Would create: $target"
        return
    fi

    cat > "$target" << 'EOF'
# ============================================================================
# Port Configuration - Single Point of Truth for All Port Assignments
# ============================================================================
# Customize these values for your infrastructure setup
# ============================================================================

# Infrastructure Services - gRPC Ports
infrastructure:
  postgres_grpc:
    port: 50061
    k8s_service: "postgres-grpc"
    description: "PostgreSQL gRPC gateway"

  nats_grpc:
    port: 50056
    k8s_service: "nats-grpc"
    description: "NATS gRPC gateway"

  nats_native:
    port: 4222
    k8s_service: "nats"
    description: "NATS native protocol"

  redis_grpc:
    port: 50055
    k8s_service: "redis-grpc"
    description: "Redis gRPC gateway"

  consul:
    port: 8500
    k8s_service: "consul"
    description: "Consul HTTP API"

# Microservice Ports - Add your services here
# Port range recommendation: 8201-8299 for microservices
microservices:
  # example_service:
  #   port: 8201
  #   k8s_service: "example-service"

# Kubernetes Namespace Configuration
kubernetes:
  staging_namespace: "default"
  production_namespace: "production"
  default_namespace: "default"

# Host Configuration
hosts:
  default: "localhost"
  k8s_cluster: "kubernetes.default.svc"
EOF

    log_success "Created: $target"
}

create_claude_settings() {
    local target=".claude/settings.local.json"

    if [[ -f "$target" ]] && ! $FORCE; then
        log_verbose "Skipping existing: $target"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY-RUN] Would create: $target"
        return
    fi

    cat > "$target" << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(mkdir:*)",
      "Bash(curl:*)",
      "Bash(python3 -m py_compile:*)"
    ],
    "deny": [],
    "ask": []
  },
  "mcpServers": {
    "postgres": {
      "command": "python",
      "args": ["agents/mcp_servers/postgres_grpc_mcp.py"],
      "env": {
        "POSTGRES_GRPC_HOST": "localhost",
        "POSTGRES_GRPC_PORT": "50061"
      }
    },
    "nats": {
      "command": "python",
      "args": ["agents/mcp_servers/nats_mcp.py"],
      "env": {
        "NATS_GRPC_HOST": "localhost",
        "NATS_GRPC_PORT": "50056"
      }
    },
    "redis": {
      "command": "python",
      "args": ["agents/mcp_servers/redis_grpc_mcp.py"],
      "env": {
        "REDIS_GRPC_HOST": "localhost",
        "REDIS_GRPC_PORT": "50055"
      }
    },
    "git": {
      "command": "npx",
      "args": ["@anthropic-ai/mcp-git"],
      "env": {}
    }
  }
}
EOF

    log_success "Created: $target"
}

create_claude_readme() {
    local target=".claude/README.md"

    if [[ -f "$target" ]] && ! $FORCE; then
        log_verbose "Skipping existing: $target"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY-RUN] Would create: $target"
        return
    fi

    cat > "$target" << EOF
# Claude Code Configuration

Project: ${PROJECT_NAME}

## Structure

\`\`\`
.claude/
├── settings.local.json    # MCP servers, permissions
├── commands/              # User-invoked slash commands
│   ├── new-cdd-service.md
│   ├── check-cdd-status.md
│   └── run-service-tests.md
└── skills/                # Auto-discovered skills
    ├── cdd-domain-context/
    ├── cdd-prd-specification/
    ├── cdd-design-document/
    ├── cdd-data-contract/
    ├── cdd-logic-contract/
    ├── cdd-system-contract/
    ├── cdd-test-pyramid/
    └── environment-context/
\`\`\`

## Skills (Auto-Discovered)

| Skill | Purpose |
|-------|---------|
| \`cdd-domain-context\` | Generate Layer 1 domain documentation |
| \`cdd-prd-specification\` | Generate Layer 2 PRD |
| \`cdd-design-document\` | Generate Layer 3 design |
| \`cdd-data-contract\` | Generate Layer 4 data contracts |
| \`cdd-logic-contract\` | Generate Layer 5 logic contracts |
| \`cdd-system-contract\` | Generate Layer 6 system contracts |
| \`cdd-test-pyramid\` | Generate 5-layer test pyramid |
| \`environment-context\` | Infrastructure awareness |

## Commands

| Command | Usage |
|---------|-------|
| \`/new-cdd-service\` | \`/new-cdd-service <name>\` - Start full CDD workflow |
| \`/check-cdd-status\` | \`/check-cdd-status <name>\` - Verify completion |
| \`/run-service-tests\` | \`/run-service-tests <name>\` - Execute tests |

## MCP Servers

Configured in \`settings.local.json\`:
- **postgres** - PostgreSQL gRPC gateway
- **nats** - NATS gRPC gateway
- **redis** - Redis gRPC gateway
- **git** - Git operations
EOF

    log_success "Created: $target"
}

# ============================================================================
# Skill Creation Functions
# ============================================================================

create_skill_environment_context() {
    local target=".claude/skills/environment-context/SKILL.md"

    if [[ -f "$target" ]] && ! $FORCE; then
        log_verbose "Skipping existing: $target"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY-RUN] Would create: $target"
        return
    fi

    cat > "$target" << EOF
---
name: environment-context
description: Understand project infrastructure, service ports, and environment configuration. Use when testing services, debugging connectivity, or setting up test environment.
allowed-tools: Read, Glob, Grep, Bash
---

# Environment Context - Infrastructure Awareness

## Purpose
Provide Claude with comprehensive knowledge of the project infrastructure.

## Port Configuration

All ports are defined in: \`config/ports.yaml\`

### Reading Port Configuration

\`\`\`bash
# View port configuration
cat config/ports.yaml
\`\`\`

### Quick Reference

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL gRPC | 50061 | Primary database |
| NATS gRPC | 50056 | Event bus (gRPC) |
| NATS Native | 4222 | Event bus (native) |
| Redis gRPC | 50055 | Caching |
| Consul | 8500 | Service discovery |

## Environment Setup

\`\`\`bash
# Activate venv (uv managed)
source .venv/bin/activate

# Load environment
export \$(cat deployment/environments/test.env | xargs)
\`\`\`

## Testing Infrastructure

| Test Layer | Database | NATS | Auth | Service |
|------------|:--------:|:----:|:----:|:-------:|
| Unit | - | - | - | - |
| Component | - | - | - | - |
| Integration | Required | Optional | - | Required |
| API | Required | Optional | Required | Required |
| Smoke | Required | Required | Required | Required |

## Key Files

| File | Purpose |
|------|---------|
| \`config/ports.yaml\` | Port configuration (Single Point of Truth) |
| \`deployment/environments/test.env\` | Test environment variables |
| \`.claude/settings.local.json\` | MCP server configuration |
EOF

    log_success "Created: $target"
}

create_skill_placeholder() {
    local skill_name="$1"
    local target=".claude/skills/${skill_name}/SKILL.md"

    if [[ -f "$target" ]] && ! $FORCE; then
        log_verbose "Skipping existing: $target"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY-RUN] Would create: $target"
        return
    fi

    local description=""
    local tools="Read, Write, Edit, Glob, Grep"

    case "$skill_name" in
        "cdd-domain-context")
            description="Create Layer 1 domain context documentation - business taxonomy, domain scenarios, domain events, core concepts, and business rules."
            ;;
        "cdd-prd-specification")
            description="Create Layer 2 PRD (Product Requirements Document) - product overview, target users, epics with user stories, API surface documentation."
            ;;
        "cdd-design-document")
            description="Create Layer 3 design documents - architecture diagrams, component design, database schemas, data flow diagrams."
            ;;
        "cdd-data-contract")
            description="Create Layer 4 data contracts - Pydantic request/response schemas, TestDataFactory with 35+ methods."
            ;;
        "cdd-logic-contract")
            description="Create Layer 5 logic contracts - business rules (40-50 numbered), state machines, edge cases."
            ;;
        "cdd-system-contract")
            description="Generate Layer 6 system contracts - 12 implementation patterns (DI, events, clients, migrations, etc.)."
            ;;
        "cdd-test-pyramid")
            description="Generate 5-layer test pyramid - unit tests, component tests, integration tests, API tests, and smoke tests."
            tools="Read, Write, Edit, Glob, Grep, Bash"
            ;;
    esac

    cat > "$target" << EOF
---
name: ${skill_name}
description: ${description}
allowed-tools: ${tools}
---

# ${skill_name}

## Purpose
${description}

## Usage

This skill is used as part of the CDD (Contract-Driven Development) workflow.

## Templates

Reference templates are located in \`templates/cdd/\`:
- Domain template: \`templates/cdd/domain_template.md\`
- PRD template: \`templates/cdd/prd_template.md\`
- Design template: \`templates/cdd/design_template.md\`
- Contract templates: \`templates/cdd/contracts/\`

## Output Location

Output files are generated in:
- Layer 1-3: \`docs/domain/\`, \`docs/prd/\`, \`docs/design/\`
- Layer 4-6: \`tests/contracts/{service}/\`

## See Also

- \`docs/CDD_GUIDE.md\` - Complete CDD documentation
- \`tests/README.md\` - Test pyramid documentation
EOF

    log_success "Created: $target"
}

create_all_skills() {
    log_info "Creating skill definitions..."

    create_skill_environment_context
    create_skill_placeholder "cdd-domain-context"
    create_skill_placeholder "cdd-prd-specification"
    create_skill_placeholder "cdd-design-document"
    create_skill_placeholder "cdd-data-contract"
    create_skill_placeholder "cdd-logic-contract"
    create_skill_placeholder "cdd-system-contract"
    create_skill_placeholder "cdd-test-pyramid"

    log_success "Skills created"
}

# ============================================================================
# Command Creation Functions
# ============================================================================

create_commands() {
    log_info "Creating slash commands..."

    # /new-cdd-service command
    local new_cdd=".claude/commands/new-cdd-service.md"
    if [[ ! -f "$new_cdd" ]] || $FORCE; then
        if $DRY_RUN; then
            log_info "[DRY-RUN] Would create: $new_cdd"
        else
            cat > "$new_cdd" << 'EOF'
---
name: new-cdd-service
description: Start CDD workflow for a new or existing microservice
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task
arguments:
  - name: service
    description: Service name (e.g., credit, membership)
    required: true
---

# New CDD Service Workflow

Start the complete CDD (Contract-Driven Development) workflow for: **$ARGUMENTS.service**

## Execution Steps

Execute these steps in order:

1. **Layer 1: Domain Context**
   - Read `templates/cdd/domain_template.md`
   - Generate `docs/domain/$ARGUMENTS.service_service.md`

2. **Layer 2: PRD**
   - Read `templates/cdd/prd_template.md`
   - Generate `docs/prd/$ARGUMENTS.service_service.md`

3. **Layer 3: Design**
   - Read `templates/cdd/design_template.md`
   - Generate `docs/design/$ARGUMENTS.service_service.md`

4. **Layer 4: Data Contract**
   - Read `templates/cdd/contracts/data_contract_template.py`
   - Generate `tests/contracts/$ARGUMENTS.service/data_contract.py`

5. **Layer 5: Logic Contract**
   - Read `templates/cdd/contracts/logic_contract_template.md`
   - Generate `tests/contracts/$ARGUMENTS.service/logic_contract.md`

6. **Layer 6: System Contract**
   - Read `templates/cdd/contracts/system_contract_template.md`
   - Generate `tests/contracts/$ARGUMENTS.service/system_contract.md`

7. **Test Pyramid**
   - Generate tests in `tests/unit/`, `tests/component/`, etc.

8. **Update Status**
   - Update `docs/current_status.md`

## Reference

- `docs/CDD_GUIDE.md` - Complete CDD documentation
- `templates/cdd/contracts/system_contract_template.md` - 12 implementation patterns
EOF
            log_success "Created: $new_cdd"
        fi
    fi

    # /check-cdd-status command
    local check_status=".claude/commands/check-cdd-status.md"
    if [[ ! -f "$check_status" ]] || $FORCE; then
        if $DRY_RUN; then
            log_info "[DRY-RUN] Would create: $check_status"
        else
            cat > "$check_status" << 'EOF'
---
name: check-cdd-status
description: Check CDD completion status for a microservice
allowed-tools: Read, Glob, Grep
arguments:
  - name: service
    description: Service name to check
    required: true
---

# Check CDD Status

Check CDD (Contract-Driven Development) completion for: **$ARGUMENTS.service**

## Checklist

### Documentation Layer
- [ ] Layer 1: `docs/domain/$ARGUMENTS.service_service.md`
- [ ] Layer 2: `docs/prd/$ARGUMENTS.service_service.md`
- [ ] Layer 3: `docs/design/$ARGUMENTS.service_service.md`

### Contract Layer
- [ ] Layer 4: `tests/contracts/$ARGUMENTS.service/data_contract.py`
- [ ] Layer 5: `tests/contracts/$ARGUMENTS.service/logic_contract.md`
- [ ] Layer 6: `tests/contracts/$ARGUMENTS.service/system_contract.md`

### Test Pyramid
- [ ] Unit tests: `tests/unit/$ARGUMENTS.service/`
- [ ] Component tests: `tests/component/$ARGUMENTS.service/`
- [ ] Integration tests: `tests/integration/*/$ARGUMENTS.service/`
- [ ] API tests: `tests/api/$ARGUMENTS.service/`
- [ ] Smoke tests: `tests/smoke/$ARGUMENTS.service/`

### Implementation
- [ ] Service code: `microservices/$ARGUMENTS.service_service/`
- [ ] Protocols: `microservices/$ARGUMENTS.service_service/protocols.py`
- [ ] Factory: `microservices/$ARGUMENTS.service_service/factory.py`

## Verification

Use Glob and Read tools to verify each item exists and contains expected content.
EOF
            log_success "Created: $check_status"
        fi
    fi

    # /run-service-tests command
    local run_tests=".claude/commands/run-service-tests.md"
    if [[ ! -f "$run_tests" ]] || $FORCE; then
        if $DRY_RUN; then
            log_info "[DRY-RUN] Would create: $run_tests"
        else
            cat > "$run_tests" << 'EOF'
---
name: run-service-tests
description: Run all test layers for a microservice
allowed-tools: Read, Bash, Glob
arguments:
  - name: service
    description: Service name to test
    required: true
---

# Run Service Tests

Execute all test layers for: **$ARGUMENTS.service**

## Test Execution Order

```bash
# 1. Unit Tests (no infrastructure)
pytest tests/unit/$ARGUMENTS.service/ -v

# 2. Component Tests (no infrastructure)
pytest tests/component/$ARGUMENTS.service/ -v

# 3. Integration Tests (requires database + service)
pytest tests/integration/*/$ARGUMENTS.service/ -v

# 4. API Tests (requires auth + service)
pytest tests/api/$ARGUMENTS.service/ -v

# 5. Smoke Tests (requires full stack)
bash tests/smoke/$ARGUMENTS.service/*.sh
```

## Prerequisites

Check `config/ports.yaml` for required infrastructure ports.

## Results

Report test results for each layer including:
- Tests passed/failed/skipped
- Coverage percentage
- Any errors or failures
EOF
            log_success "Created: $run_tests"
        fi
    fi

    log_success "Commands created"
}

# ============================================================================
# Template Creation Functions
# ============================================================================

create_cdd_guide() {
    local target="docs/CDD_GUIDE.md"

    if [[ -f "$target" ]] && ! $FORCE; then
        log_verbose "Skipping existing: $target"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY-RUN] Would create: $target"
        return
    fi

    cat > "$target" << 'EOF'
# Contract-Driven Development (CDD) Guide

**6-Layer CDD + 5-Layer Test Pyramid Specification**

---

## Core Principles

1. **Contract-First**: Define contracts before implementation
2. **Zero Hardcoded Data**: All test data via TestDataFactory
3. **Documentation as Code**: Contracts are executable and verifiable
4. **Testability by Design**: Dependency injection, Protocol-based interfaces
5. **Event-Driven**: Inter-service communication via message bus

---

## 6-Layer CDD Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Documentation Layer (docs/)                                      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: Domain Context    │ docs/domain/{service}.md           │
│ Layer 2: PRD               │ docs/prd/{service}.md              │
│ Layer 3: Design            │ docs/design/{service}.md           │
├─────────────────────────────────────────────────────────────────┤
│ Contract Layer (tests/contracts/)                                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: Data Contract     │ tests/contracts/{svc}/data_contract.py    │
│ Layer 5: Logic Contract    │ tests/contracts/{svc}/logic_contract.md   │
│ Layer 6: System Contract   │ tests/contracts/{svc}/system_contract.md  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5-Layer Test Pyramid

```
                    ┌─────────────────┐
                    │   Layer 5       │  E2E Bash scripts
                    │   Smoke Tests   │  tests/smoke/{service}/
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 4       │  Real HTTP + JWT Auth
                    │   API Tests     │  tests/api/{service}/
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 3       │  Real HTTP + DB
                    │ Integration     │  tests/integration/{service}/
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 2       │  Mocked dependencies
                    │ Component Tests │  tests/component/{service}/
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 1       │  Pure functions
                    │   Unit Tests    │  tests/unit/{service}/
                    └─────────────────┘
```

---

## Key Files

| Purpose | Location |
|---------|----------|
| Port configuration | `config/ports.yaml` |
| CDD templates | `templates/cdd/` |
| TDD templates | `templates/tdd/` |
| 12 Implementation patterns | `templates/cdd/contracts/system_contract_template.md` |

---

## Quick Start

```bash
# Check CDD status for a service
/check-cdd-status <service>

# Start CDD workflow for a service
/new-cdd-service <service>

# Run tests for a service
/run-service-tests <service>
```
EOF

    log_success "Created: $target"
}

create_tests_readme() {
    local target="tests/README.md"

    if [[ -f "$target" ]] && ! $FORCE; then
        log_verbose "Skipping existing: $target"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY-RUN] Would create: $target"
        return
    fi

    cat > "$target" << 'EOF'
# Test Guide

## 5-Layer Test Pyramid

| Layer | Location | Infrastructure | Purpose |
|-------|----------|----------------|---------|
| Unit | `tests/unit/` | None | Pure functions |
| Component | `tests/component/` | None | Mocked dependencies |
| Integration | `tests/integration/` | Database + Service | Real HTTP + DB |
| API | `tests/api/` | Database + Auth + Service | JWT authentication |
| Smoke | `tests/smoke/` | Full stack | E2E validation |

## Directory Structure

```
tests/
├── contracts/           # Layer 4-6 contracts
│   └── {service}/
│       ├── data_contract.py
│       ├── logic_contract.md
│       └── system_contract.md
├── fixtures/            # Shared test fixtures
├── unit/               # Layer 1: Unit tests
├── component/          # Layer 2: Component tests
├── integration/        # Layer 3: Integration tests
│   ├── golden/         # Reference implementation tests
│   └── tdd/            # TDD cycle tests
├── api/                # Layer 4: API tests
└── smoke/              # Layer 5: Smoke tests
```

## Running Tests

```bash
# Run unit tests
pytest tests/unit -v

# Run component tests
pytest tests/component -v

# Run integration tests (requires infrastructure)
pytest tests/integration -v

# Run API tests (requires auth)
pytest tests/api -v

# Run smoke tests
bash tests/smoke/{service}/*.sh
```

## Zero Hardcoded Data

All test data MUST come from TestDataFactory:

```python
# Wrong
user_id = "user_123"

# Correct
from tests.contracts.{service}.data_contract import {Service}TestDataFactory
user_id = {Service}TestDataFactory.make_user_id()
```
EOF

    log_success "Created: $target"
}

create_current_status() {
    local target="docs/current_status.md"

    if [[ -f "$target" ]] && ! $FORCE; then
        log_verbose "Skipping existing: $target"
        return
    fi

    if $DRY_RUN; then
        log_info "[DRY-RUN] Would create: $target"
        return
    fi

    cat > "$target" << "EOF"
# Current Status

## CDD Progress Tracking

| Service | L1 | L2 | L3 | L4 | L5 | L6 | Unit | Comp | Int | API | Smoke |
|---------|:--:|:--:|:--:|:--:|:--:|:--:|:----:|:----:|:---:|:---:|:-----:|
| example | - | - | - | - | - | - | - | - | - | - | - |

Legend:
- L1-L6: CDD Layers (Domain, PRD, Design, Data, Logic, System)
- ✅ Complete
- 🔄 In Progress
- ❌ Not Started
- `-` Not Applicable

## Last Updated

Date: $(date +%Y-%m-%d)
EOF

    log_success "Created: $target"
}

# ============================================================================
# Environment Setup
# ============================================================================

create_env_files() {
    log_info "Creating environment files..."

    # Test environment
    local test_env="deployment/environments/test.env"
    if [[ ! -f "$test_env" ]] || $FORCE; then
        if $DRY_RUN; then
            log_info "[DRY-RUN] Would create: $test_env"
        else
            cat > "$test_env" << 'EOF'
# Test Environment Configuration
# Load with: export $(cat deployment/environments/test.env | xargs)

# Database
POSTGRES_GRPC_HOST=localhost
POSTGRES_GRPC_PORT=50061

# NATS
NATS_GRPC_HOST=localhost
NATS_GRPC_PORT=50056
NATS_URL=nats://localhost:4222

# Redis
REDIS_GRPC_HOST=localhost
REDIS_GRPC_PORT=50055

# Consul
CONSUL_HTTP_ADDR=http://localhost:8500

# Auth
JWT_SECRET=test-jwt-secret-do-not-use-in-production
EOF
            log_success "Created: $test_env"
        fi
    fi

    # Dev environment
    local dev_env="deployment/environments/dev.env"
    if [[ ! -f "$dev_env" ]] || $FORCE; then
        if $DRY_RUN; then
            log_info "[DRY-RUN] Would create: $dev_env"
        else
            cat > "$dev_env" << 'EOF'
# Development Environment Configuration

# Database
POSTGRES_GRPC_HOST=localhost
POSTGRES_GRPC_PORT=50061

# NATS
NATS_GRPC_HOST=localhost
NATS_GRPC_PORT=50056
NATS_URL=nats://localhost:4222

# Redis
REDIS_GRPC_HOST=localhost
REDIS_GRPC_PORT=50055

# Consul
CONSUL_HTTP_ADDR=http://localhost:8500

# Debug
LOG_LEVEL=DEBUG
EOF
            log_success "Created: $dev_env"
        fi
    fi
}

# ============================================================================
# Dependency Setup
# ============================================================================

setup_dependencies() {
    if $SKIP_DEPS; then
        log_info "Skipping dependency setup (--skip-deps)"
        return
    fi

    log_info "Setting up dependencies..."

    # Check for uv
    if ! command -v uv &> /dev/null; then
        log_warn "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        return
    fi

    # Create requirements files
    local base_req="deployment/requirements/base.txt"
    if [[ ! -f "$base_req" ]] || $FORCE; then
        if $DRY_RUN; then
            log_info "[DRY-RUN] Would create: $base_req"
        else
            cat > "$base_req" << 'EOF'
# Base requirements for production
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
httpx>=0.24.0
grpcio>=1.50.0
protobuf>=4.21.0
EOF
            log_success "Created: $base_req"
        fi
    fi

    local dev_req="deployment/requirements/dev.txt"
    if [[ ! -f "$dev_req" ]] || $FORCE; then
        if $DRY_RUN; then
            log_info "[DRY-RUN] Would create: $dev_req"
        else
            cat > "$dev_req" << 'EOF'
# Development requirements
-r base.txt

# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0

# Agent SDK
anthropic>=0.18.0
claude-agent-sdk>=0.1.11
mcp>=0.1.0

# Development
black>=23.0.0
ruff>=0.1.0
mypy>=1.0.0
EOF
            log_success "Created: $dev_req"
        fi
    fi

    # Create venv if it doesn't exist
    if [[ ! -d ".venv" ]]; then
        if $DRY_RUN; then
            log_info "[DRY-RUN] Would create venv"
        else
            log_info "Creating virtual environment..."
            uv venv
            log_success "Virtual environment created"
        fi
    fi

    log_success "Dependencies setup complete"
}

# ============================================================================
# Summary Functions
# ============================================================================

print_summary() {
    echo ""
    echo "============================================================================"
    echo -e "${GREEN}Agentic Development Project Initialized${NC}"
    echo "============================================================================"
    echo ""
    echo "Project: ${PROJECT_NAME}"
    echo "Mode: ${MODE}"
    echo ""
    echo "Next Steps:"
    echo ""
    echo "  1. Activate the virtual environment:"
    echo "     source .venv/bin/activate"
    echo ""
    echo "  2. Install dependencies:"
    echo "     uv pip install -r deployment/requirements/dev.txt"
    echo ""
    echo "  3. Configure port settings:"
    echo "     Edit config/ports.yaml"
    echo ""
    echo "  4. Start Claude Code and run:"
    echo "     /new-cdd-service <service-name>"
    echo ""
    echo "Documentation:"
    echo "  - CDD Guide: docs/CDD_GUIDE.md"
    echo "  - Test Guide: tests/README.md"
    echo "  - Status: docs/current_status.md"
    echo ""
    echo "============================================================================"
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    echo ""
    echo "============================================================================"
    echo "Agentic Development Project Initialization"
    echo "============================================================================"
    echo ""

    # Auto-detect mode if not specified
    if [[ "$MODE" == "auto" ]]; then
        MODE=$(auto_detect_mode)
        log_info "Auto-detected mode: $MODE"
    fi

    # Show what exists
    if [[ "$MODE" == "existing" ]]; then
        log_info "Detected existing project structure:"
        detect_existing_structure | while read -r line; do
            log_verbose "  $line"
        done
    fi

    # Execute initialization steps
    create_directory_structure
    create_ports_config
    create_claude_settings
    create_claude_readme
    create_all_skills
    create_commands
    create_cdd_guide
    create_tests_readme
    create_current_status
    create_env_files
    setup_dependencies

    # Print summary
    if ! $DRY_RUN; then
        print_summary
    else
        echo ""
        log_info "[DRY-RUN] No changes were made. Run without --dry-run to apply."
    fi
}

main
