#!/bin/bash
# =============================================================================
# Local Development Script - isA_user (Microservices)
# =============================================================================
# Usage:
#   ./deployment/local-dev.sh --setup                    # Setup venv
#   ./deployment/local-dev.sh --run auth_service         # Run specific service
#   ./deployment/local-dev.sh --run-core                 # Run core services only (tiers 1-3)
#   ./deployment/local-dev.sh --run-all                  # Run ALL services (tiered startup)
#   ./deployment/local-dev.sh --run-group <1-4>          # Run a specific tier
#   ./deployment/local-dev.sh --stop-all                 # Stop ALL services
#   ./deployment/local-dev.sh --status                   # Show status
#
# Service Tiers:
#   Tier 1 — Foundation:  auth, account, organization (no internal deps)
#   Tier 2 — Core Platform: session, authorization, wallet, memory, storage,
#                            event, audit, notification (needed by platform)
#   Tier 3 — Business:    billing, subscription, product, telemetry, vault
#                          (needed by isA_Model/Agent SDK/OS)
#   Tier 4 — Optional:    payment, order, task, calendar, weather, album,
#                          device, ota, media, location, compliance, document,
#                          credit, invitation, membership, campaign, inventory,
#                          tax, fulfillment (domain features)
# =============================================================================
set -e

PROJECT_NAME="isa_user"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# =============================================================================
# Service Tiers — startup order based on real dependency analysis
# =============================================================================
# Platform dependency map (what external isA services require):
#   isA_Agent   → auth, account
#   isA_MCP     → auth, account, session, authorization, storage, memory
#   isA_Model   → auth, authorization, billing, subscription, product
#   isA_Agent_SDK → auth, account, session, authorization, audit, notification,
#                   payment, wallet, storage, telemetry, memory, task, campaign
#   isA_OS      → auth, account, billing, telemetry
#   isA_Data    → auth
# =============================================================================

# Tier 1: Foundation — no isA_user deps, everything else depends on these
TIER1_SERVICES="auth_service account_service organization_service"

# Tier 2: Core Platform — depends on Tier 1, required by MCP/Agent SDK
TIER2_SERVICES="session_service authorization_service wallet_service memory_service storage_service event_service audit_service notification_service"

# Tier 3: Business — depends on Tier 1+2, required by Model/Agent SDK/OS
TIER3_SERVICES="billing_service subscription_service product_service telemetry_service vault_service"

# Tier 4: Optional — domain features, not required for core platform
TIER4_SERVICES="payment_service order_service task_service calendar_service weather_service album_service device_service ota_service media_service location_service compliance_service document_service credit_service invitation_service membership_service campaign_service inventory_service tax_service fulfillment_service"

TIER_NAMES=("" "Foundation" "Core Platform" "Business" "Optional")

get_tier_services() {
    local tier=$1
    case "$tier" in
        1) echo "$TIER1_SERVICES" ;;
        2) echo "$TIER2_SERVICES" ;;
        3) echo "$TIER3_SERVICES" ;;
        4) echo "$TIER4_SERVICES" ;;
        *) echo "" ;;
    esac
}

# Get all microservices and their ports from ports.yaml
get_microservices() {
    grep -E "^\s+[a-z_]+_service:" config/ports.yaml | sed 's/://g' | awk '{print $1}'
}

get_service_port() {
    local service=$1
    grep -A1 "^  $service:" config/ports.yaml 2>/dev/null | grep "port:" | awk '{print $2}'
}

get_consul_url() {
    local consul_port="${CONSUL_PORT:-8500}"
    echo "http://127.0.0.1:${consul_port}"
}

# =============================================================================
# Health check — poll /health until healthy or timeout
# =============================================================================
wait_for_healthy() {
    local service_name=$1
    local service_port=$2
    local max_wait=${3:-30}
    local waited=0

    while [ "$waited" -lt "$max_wait" ]; do
        local status
        status=$(curl -fsS -m 2 "http://127.0.0.1:${service_port}/health" 2>/dev/null \
            | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))' 2>/dev/null || true)
        if [ "$status" = "healthy" ] || [ "$status" = "degraded" ]; then
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
    done
    return 1
}

# Start all services in a tier, then health-check them before proceeding
start_tier() {
    local tier_num=$1
    local tier_name="${TIER_NAMES[$tier_num]}"
    local services
    services=$(get_tier_services "$tier_num")

    if [ -z "$services" ]; then
        return 0
    fi

    local tier_count=0
    local started_services=""

    echo ""
    echo "--- Tier $tier_num: $tier_name ---"

    for SERVICE_NAME in $services; do
        if [ ! -d "microservices/$SERVICE_NAME" ]; then
            echo "  - $SERVICE_NAME — directory not found, skipping"
            continue
        fi

        SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
        if [ -z "$SERVICE_PORT" ]; then
            echo "  - $SERVICE_NAME — no port in ports.yaml, skipping"
            continue
        fi

        stop_service_on_port "$SERVICE_PORT" "$SERVICE_NAME"
        cleanup_consul_critical_checks_for_service "$SERVICE_NAME"

        echo "  Starting $SERVICE_NAME on port $SERVICE_PORT..."
        SERVICE_PORT_ENV="$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]')_PORT"
        env "$SERVICE_PORT_ENV=$SERVICE_PORT" PORT="$SERVICE_PORT" \
        PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/microservices/$SERVICE_NAME" \
        nohup .venv/bin/python -m uvicorn microservices.$SERVICE_NAME.main:app \
            --host 0.0.0.0 --port "$SERVICE_PORT" \
            --reload --reload-dir "microservices/$SERVICE_NAME" --reload-dir "core" \
            > "logs/$SERVICE_NAME.log" 2>&1 &

        started_services="$started_services $SERVICE_NAME:$SERVICE_PORT"
        tier_count=$((tier_count + 1))
        sleep 1
    done

    if [ "$tier_count" -eq 0 ]; then
        echo "  (no services to start)"
        return 0
    fi

    # Wait for all services in this tier to become healthy
    echo "  Waiting for health checks..."
    local healthy=0
    local failed=""
    for entry in $started_services; do
        local svc="${entry%%:*}"
        local port="${entry##*:}"
        if wait_for_healthy "$svc" "$port" 30; then
            echo "    ✓ $svc"
            healthy=$((healthy + 1))
        else
            echo "    ✗ $svc — not healthy after 30s (check logs/$svc.log)"
            failed="$failed $svc"
        fi
    done

    echo "  Tier $tier_num: $healthy/$tier_count healthy"
    if [ -n "$failed" ]; then
        echo "  Failed:$failed"
    fi

    TOTAL_STARTED=$((TOTAL_STARTED + tier_count))
    TOTAL_HEALTHY=$((TOTAL_HEALTHY + healthy))
}

stop_service_on_port() {
    local service_port=$1
    local service_name=${2:-service}
    local pids

    pids=$(lsof -ti:"$service_port" 2>/dev/null | sort -u || true)
    if [ -z "$pids" ]; then
        return 0
    fi

    echo "  Stopping $service_name on port $service_port..."
    echo "$pids" | xargs kill -TERM 2>/dev/null || true

    local waited=0
    while [ "$waited" -lt 10 ]; do
        if ! lsof -ti:"$service_port" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done

    if lsof -ti:"$service_port" >/dev/null 2>&1; then
        echo "  Force-stopping $service_name on port $service_port..."
        lsof -ti:"$service_port" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

cleanup_consul_critical_checks_for_service() {
    local service_name=$1

    if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi

    local critical_json
    critical_json=$(curl -fsS -m 5 "$(get_consul_url)/v1/health/state/critical" 2>/dev/null || true)
    if [ -z "$critical_json" ] || [ "$critical_json" = "[]" ]; then
        return 0
    fi

    local stale_ids
    stale_ids=$(printf '%s' "$critical_json" | python3 -c 'import json, sys
service_name = sys.argv[1]
items = json.load(sys.stdin)
service_ids = sorted(
    {item.get("ServiceID", "") for item in items if item.get("ServiceName") == service_name and item.get("ServiceID")}
)
print("\n".join(service_ids))' "$service_name" 2>/dev/null || true)

    if [ -z "$stale_ids" ]; then
        return 0
    fi

    echo "  Cleaning stale Consul registrations for $service_name..."
    while IFS= read -r service_id; do
        [ -z "$service_id" ] && continue
        curl -fsS -m 5 -X PUT "$(get_consul_url)/v1/agent/service/deregister/${service_id}" >/dev/null 2>&1 || true
        echo "    deregistered $service_id"
    done <<< "$stale_ids"
}

show_consul_critical_checks() {
    if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
        echo "Consul critical checks: unavailable (curl/python3 missing)"
        return 0
    fi

    local critical_json
    critical_json=$(curl -fsS -m 5 "$(get_consul_url)/v1/health/state/critical" 2>/dev/null || true)
    if [ -z "$critical_json" ]; then
        echo "Consul critical checks: unavailable"
        return 0
    fi

    local critical_lines
    critical_lines=$(printf '%s' "$critical_json" | python3 -c 'import json, sys
items = json.load(sys.stdin)
for item in items:
    service_name = item.get("ServiceName", "unknown")
    service_id = item.get("ServiceID", "")
    output = item.get("Output", "").replace("\n", " ").strip()
    print(f"{service_name}|{service_id}|{output}")' 2>/dev/null || true)

    if [ -z "$critical_lines" ]; then
        echo "Consul critical checks: none"
        return 0
    fi

    echo "Consul critical checks:"
    while IFS='|' read -r service_name service_id output; do
        echo "  ✗ ${service_name} (${service_id}) - ${output}"
    done <<< "$critical_lines"
}

case "${1:-}" in
    --setup)
        echo "Setting up $PROJECT_NAME..."

        # Create venv
        rm -rf .venv
        uv venv .venv --python 3.12

        # Install base (ISA packages editable) + dev packages
        uv pip install -r deployment/requirements/base_dev.txt --python .venv/bin/python
        uv pip install -r deployment/requirements/dev.txt --python .venv/bin/python 2>/dev/null || true
        uv pip install -r deployment/requirements/agent.txt --python .venv/bin/python 2>/dev/null || true

        # Port-forwards (native service ports - no gRPC gateway needed)
        pkill -f "kubectl port-forward" 2>/dev/null || true
        kubectl port-forward -n isa-cloud-staging svc/postgres 5432:5432 &>/dev/null &
        kubectl port-forward -n isa-cloud-staging svc/redis 6379:6379 &>/dev/null &
        kubectl port-forward -n isa-cloud-staging svc/qdrant 6333:6333 &>/dev/null &
        kubectl port-forward -n isa-cloud-staging svc/minio 9000:9000 &>/dev/null &
        kubectl port-forward -n isa-cloud-staging svc/neo4j 7687:7687 &>/dev/null &
        kubectl port-forward -n isa-cloud-staging svc/nats 4222:4222 &>/dev/null &
        kubectl port-forward -n isa-cloud-staging svc/mosquitto 1883:1883 &>/dev/null &
        kubectl port-forward -n isa-cloud-staging svc/consul-expose-servers 8500:8500 &>/dev/null &
        sleep 2

        echo "Setup complete!"
        echo "Run a service with: $0 --run <service_name>"
        echo "Run all services with: $0 --run-all"
        echo ""
        echo "Available services:"
        ls microservices/ | sed 's/^/  /'
        ;;

    --run)
        SERVICE_NAME="${2:-auth_service}"

        if [ ! -d "microservices/$SERVICE_NAME" ]; then
            echo "Service not found: $SERVICE_NAME"
            echo "Available services:"
            ls microservices/ | sed 's/^/  /'
            exit 1
        fi

        # Get port from config/ports.yaml
        SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
        if [ -z "$SERVICE_PORT" ]; then
            echo "Port not found in config/ports.yaml for $SERVICE_NAME, using default 8200"
            SERVICE_PORT=8200
        fi

        # Stop any existing process on the target port so it can deregister cleanly
        stop_service_on_port "$SERVICE_PORT" "$SERVICE_NAME"
        cleanup_consul_critical_checks_for_service "$SERVICE_NAME"

        # Export all env vars from dev.env
        if [ -f "deployment/environments/dev.env" ]; then
            export $(grep -v '^#' deployment/environments/dev.env | grep -v '^$' | xargs)
        fi

        echo "Starting $SERVICE_NAME on port $SERVICE_PORT..."
        # Set PYTHONPATH to include project root and service directory (for clients import)
        export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/microservices/$SERVICE_NAME"
        SERVICE_PORT_ENV="$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]')_PORT"
        env "$SERVICE_PORT_ENV=$SERVICE_PORT" PORT="$SERVICE_PORT" \
        .venv/bin/python -m uvicorn microservices.$SERVICE_NAME.main:app --host 0.0.0.0 --port $SERVICE_PORT \
            --reload --reload-dir "microservices/$SERVICE_NAME" --reload-dir "core"
        ;;

    --restart)
        SERVICE_NAME="${2:-}"
        if [ -z "$SERVICE_NAME" ]; then
            echo "Usage: $0 --restart <service_name>"
            exit 1
        fi

        SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
        if [ -z "$SERVICE_PORT" ]; then
            echo "Service not found: $SERVICE_NAME"
            exit 1
        fi

        echo "Restarting $SERVICE_NAME..."

        stop_service_on_port "$SERVICE_PORT" "$SERVICE_NAME"
        cleanup_consul_critical_checks_for_service "$SERVICE_NAME"

        # Export all env vars from dev.env
        if [ -f "deployment/environments/dev.env" ]; then
            export $(grep -v '^#' deployment/environments/dev.env | grep -v '^$' | xargs)
        fi

        # Clear Python cache for this service
        find "microservices/$SERVICE_NAME" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

        echo "  Starting $SERVICE_NAME on port $SERVICE_PORT..."
        export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/microservices/$SERVICE_NAME"
        SERVICE_PORT_ENV="$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]')_PORT"
        env "$SERVICE_PORT_ENV=$SERVICE_PORT" PORT="$SERVICE_PORT" \
        .venv/bin/python -m uvicorn microservices.$SERVICE_NAME.main:app --host 0.0.0.0 --port $SERVICE_PORT \
            --reload --reload-dir "microservices/$SERVICE_NAME" --reload-dir "core"
        ;;

    --run-core)
        echo "Starting CORE microservices (tiers 1-3)..."

        # Export all env vars from dev.env
        if [ -f "deployment/environments/dev.env" ]; then
            export $(grep -v '^#' deployment/environments/dev.env | grep -v '^$' | xargs)
        fi

        mkdir -p logs
        TOTAL_STARTED=0
        TOTAL_HEALTHY=0

        start_tier 1
        start_tier 2
        start_tier 3

        echo ""
        echo "Core startup complete: $TOTAL_HEALTHY/$TOTAL_STARTED healthy. Logs in ./logs/"
        echo "Use '$0 --run-group 4' to add optional services"
        echo "Use '$0 --status' to check running services"
        echo "Use '$0 --stop-all' to stop all services"
        ;;

    --run-group)
        TIER="${2:-}"
        if [ -z "$TIER" ] || ! echo "$TIER" | grep -qE '^[1-4]$'; then
            echo "Usage: $0 --run-group <1-4>"
            echo ""
            echo "Tiers:"
            echo "  1 — Foundation:    auth, account, organization"
            echo "  2 — Core Platform: session, authorization, wallet, memory, storage, event, audit, notification"
            echo "  3 — Business:      billing, subscription, product, telemetry, vault"
            echo "  4 — Optional:      payment, order, task, calendar, weather, album, device, ota, media,"
            echo "                     location, compliance, document, credit, invitation, membership,"
            echo "                     campaign, inventory, tax, fulfillment"
            exit 1
        fi

        echo "Starting Tier $TIER services..."

        # Export all env vars from dev.env
        if [ -f "deployment/environments/dev.env" ]; then
            export $(grep -v '^#' deployment/environments/dev.env | grep -v '^$' | xargs)
        fi

        mkdir -p logs
        TOTAL_STARTED=0
        TOTAL_HEALTHY=0

        start_tier "$TIER"

        echo ""
        echo "Tier $TIER complete: $TOTAL_HEALTHY/$TOTAL_STARTED healthy. Logs in ./logs/"
        ;;

    --run-all)
        echo "Starting ALL microservices (tiered startup with health gating)..."

        # Export all env vars from dev.env
        if [ -f "deployment/environments/dev.env" ]; then
            export $(grep -v '^#' deployment/environments/dev.env | grep -v '^$' | xargs)
        fi

        mkdir -p logs
        TOTAL_STARTED=0
        TOTAL_HEALTHY=0

        start_tier 1
        start_tier 2
        start_tier 3
        start_tier 4

        echo ""
        echo "All tiers complete: $TOTAL_HEALTHY/$TOTAL_STARTED healthy. Logs in ./logs/"
        echo "Use '$0 --status' to check running services"
        echo "Use '$0 --stop-all' to stop all services"
        ;;

    --stop-all)
        echo "Stopping ALL microservices..."

        for SERVICE_NAME in $(get_microservices); do
            SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
            if [ -n "$SERVICE_PORT" ]; then
                if lsof -ti:$SERVICE_PORT >/dev/null 2>&1; then
                    stop_service_on_port "$SERVICE_PORT" "$SERVICE_NAME"
                    cleanup_consul_critical_checks_for_service "$SERVICE_NAME"
                    echo "  Stopped $SERVICE_NAME (port $SERVICE_PORT)"
                fi
            fi
        done

        echo "All services stopped."
        ;;

    --status)
        echo "Venv: .venv"
        .venv/bin/pip show isa-common isa-model 2>/dev/null | grep -E "Name|Version|Location" || echo "Not installed"
        echo ""

        for tier_num in 1 2 3 4; do
            tier_name="${TIER_NAMES[$tier_num]}"
            echo "Tier $tier_num — $tier_name:"
            for SERVICE_NAME in $(get_tier_services "$tier_num"); do
                if [ -d "microservices/$SERVICE_NAME" ]; then
                    SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
                    if [ -n "$SERVICE_PORT" ]; then
                        if lsof -ti:"$SERVICE_PORT" >/dev/null 2>&1; then
                            echo "  ✓ $SERVICE_NAME (port $SERVICE_PORT) - RUNNING"
                        else
                            echo "  ✗ $SERVICE_NAME (port $SERVICE_PORT) - stopped"
                        fi
                    fi
                fi
            done
            echo ""
        done

        # Check for any services not in tier lists (e.g. new services added to ports.yaml)
        ALL_TIERED="$TIER1_SERVICES $TIER2_SERVICES $TIER3_SERVICES $TIER4_SERVICES"
        UNTIERED=""
        for SERVICE_NAME in $(get_microservices); do
            if ! echo " $ALL_TIERED " | grep -q " $SERVICE_NAME "; then
                UNTIERED="$UNTIERED $SERVICE_NAME"
            fi
        done
        if [ -n "$UNTIERED" ]; then
            echo "Untiered (add to a tier in local-dev.sh):"
            for SERVICE_NAME in $UNTIERED; do
                SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
                if [ -n "$SERVICE_PORT" ]; then
                    if lsof -ti:"$SERVICE_PORT" >/dev/null 2>&1; then
                        echo "  ✓ $SERVICE_NAME (port $SERVICE_PORT) - RUNNING"
                    else
                        echo "  ✗ $SERVICE_NAME (port $SERVICE_PORT) - stopped"
                    fi
                fi
            done
            echo ""
        fi

        show_consul_critical_checks
        ;;

    *)
        echo "Usage:"
        echo "  $0 --setup                    # Setup venv and port-forwards"
        echo "  $0 --run <service>            # Run a single microservice"
        echo "  $0 --restart <service>        # Restart a single microservice"
        echo "  $0 --run-core                 # Run core services (tiers 1-3, health-gated)"
        echo "  $0 --run-all                  # Run ALL services (tiers 1-4, health-gated)"
        echo "  $0 --run-group <1-4>          # Run a specific tier"
        echo "  $0 --stop-all                 # Stop ALL microservices"
        echo "  $0 --status                   # Show status by tier"
        echo ""
        echo "Service Tiers:"
        echo "  1 — Foundation:    auth, account, organization"
        echo "  2 — Core Platform: session, authorization, wallet, memory, storage, event, audit, notification"
        echo "  3 — Business:      billing, subscription, product, telemetry, vault"
        echo "  4 — Optional:      payment, order, task, calendar, weather, album, device, ota, media,"
        echo "                     location, compliance, document, credit, invitation, membership,"
        echo "                     campaign, inventory, tax, fulfillment"
        echo ""
        echo "Examples:"
        echo "  $0 --setup"
        echo "  $0 --run auth_service"
        echo "  $0 --restart memory_service"
        echo "  $0 --run-core                 # Most common — starts what the platform needs"
        echo "  $0 --run-all                  # Everything including optional services"
        echo "  $0 --run-group 4              # Add optional services after core is running"
        ;;
esac
