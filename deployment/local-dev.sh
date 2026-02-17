#!/bin/bash
# =============================================================================
# Local Development Script - isA_user (Microservices)
# =============================================================================
# Usage:
#   ./deployment/local-dev.sh --setup                    # Setup venv
#   ./deployment/local-dev.sh --run auth_service         # Run specific service
#   ./deployment/local-dev.sh --run-all                  # Run ALL services
#   ./deployment/local-dev.sh --stop-all                 # Stop ALL services
#   ./deployment/local-dev.sh --status                   # Show status
# =============================================================================
set -e

PROJECT_NAME="isa_user"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Get all microservices and their ports from ports.yaml
get_microservices() {
    grep -E "^\s+[a-z_]+_service:" config/ports.yaml | sed 's/://g' | awk '{print $1}'
}

get_service_port() {
    local service=$1
    grep -A1 "^  $service:" config/ports.yaml 2>/dev/null | grep "port:" | awk '{print $2}'
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

        # Kill existing process on port
        lsof -ti:$SERVICE_PORT | xargs kill -9 2>/dev/null || true

        # Export all env vars from dev.env
        if [ -f "deployment/environments/dev.env" ]; then
            export $(grep -v '^#' deployment/environments/dev.env | grep -v '^$' | xargs)
        fi

        echo "Starting $SERVICE_NAME on port $SERVICE_PORT..."
        # Set PYTHONPATH to include project root and service directory (for clients import)
        export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/microservices/$SERVICE_NAME"
        SERVICE_PORT_ENV="$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]')_PORT"
        env "$SERVICE_PORT_ENV=$SERVICE_PORT" PORT="$SERVICE_PORT" \
        .venv/bin/python -m uvicorn microservices.$SERVICE_NAME.main:app --host 0.0.0.0 --port $SERVICE_PORT --reload
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

        # Kill existing process on port
        if lsof -ti:$SERVICE_PORT >/dev/null 2>&1; then
            lsof -ti:$SERVICE_PORT | xargs kill -9 2>/dev/null || true
            echo "  Stopped old process"
            sleep 1
        fi

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
        .venv/bin/python -m uvicorn microservices.$SERVICE_NAME.main:app --host 0.0.0.0 --port $SERVICE_PORT --reload
        ;;

    --run-all)
        echo "Starting ALL microservices (with 2s delay between each)..."

        # Export all env vars from dev.env
        if [ -f "deployment/environments/dev.env" ]; then
            export $(grep -v '^#' deployment/environments/dev.env | grep -v '^$' | xargs)
        fi

        # Create logs directory
        mkdir -p logs

        # Start each microservice in background with delay
        COUNT=0
        for SERVICE_NAME in $(get_microservices); do
            if [ -d "microservices/$SERVICE_NAME" ]; then
                SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
                if [ -n "$SERVICE_PORT" ]; then
                    # Kill existing process on port
                    lsof -ti:$SERVICE_PORT | xargs kill -9 2>/dev/null || true

                    echo "  [$((COUNT+1))] Starting $SERVICE_NAME on port $SERVICE_PORT..."
                    SERVICE_PORT_ENV="$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]')_PORT"
                    env "$SERVICE_PORT_ENV=$SERVICE_PORT" PORT="$SERVICE_PORT" \
                    PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/microservices/$SERVICE_NAME" \
                    nohup .venv/bin/python -m uvicorn microservices.$SERVICE_NAME.main:app \
                        --host 0.0.0.0 --port $SERVICE_PORT --reload \
                        > logs/$SERVICE_NAME.log 2>&1 &

                    COUNT=$((COUNT+1))
                    # Delay between services to avoid overwhelming K8s
                    sleep 2
                fi
            fi
        done

        echo ""
        echo "All $COUNT services started. Logs in ./logs/"
        echo "Use '$0 --status' to check running services"
        echo "Use '$0 --stop-all' to stop all services"
        ;;

    --stop-all)
        echo "Stopping ALL microservices..."

        for SERVICE_NAME in $(get_microservices); do
            SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
            if [ -n "$SERVICE_PORT" ]; then
                if lsof -ti:$SERVICE_PORT >/dev/null 2>&1; then
                    lsof -ti:$SERVICE_PORT | xargs kill -9 2>/dev/null || true
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
        echo "Microservices status:"
        for SERVICE_NAME in $(get_microservices); do
            if [ -d "microservices/$SERVICE_NAME" ]; then
                SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
                if [ -n "$SERVICE_PORT" ]; then
                    if lsof -ti:$SERVICE_PORT >/dev/null 2>&1; then
                        echo "  ✓ $SERVICE_NAME (port $SERVICE_PORT) - RUNNING"
                    else
                        echo "  ✗ $SERVICE_NAME (port $SERVICE_PORT) - stopped"
                    fi
                fi
            fi
        done
        ;;

    *)
        echo "Usage:"
        echo "  $0 --setup                    # Setup venv and port-forwards"
        echo "  $0 --run <service>            # Run a single microservice"
        echo "  $0 --restart <service>        # Restart a single microservice (kills, clears cache, starts)"
        echo "  $0 --run-all                  # Run ALL microservices"
        echo "  $0 --stop-all                 # Stop ALL microservices"
        echo "  $0 --status                   # Show status of all services"
        echo ""
        echo "Examples:"
        echo "  $0 --setup"
        echo "  $0 --run auth_service"
        echo "  $0 --restart memory_service"
        echo "  $0 --run-all"
        ;;
esac
