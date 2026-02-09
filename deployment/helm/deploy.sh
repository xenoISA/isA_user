#!/bin/bash
# =============================================================================
# Deploy ISA User Platform Microservices via Helm
# =============================================================================
# Usage:
#   ./deployment/helm/deploy.sh staging         # Deploy all to staging
#   ./deployment/helm/deploy.sh production      # Deploy all to production
#   ./deployment/helm/deploy.sh staging auth    # Deploy only auth service
#   ./deployment/helm/deploy.sh staging --dry-run  # Dry run
# =============================================================================

set -e

cd "$(dirname "$0")/../.."

CHART_PATH="${HOME}/Documents/Fun/isA/isA_Cloud/deployments/charts/isa-service"

# Microservices with ports
declare -A SERVICES=(
    ["auth"]="8201"
    ["account"]="8202"
    ["session"]="8203"
    ["authorization"]="8204"
    ["audit"]="8205"
    ["notification"]="8206"
    ["payment"]="8207"
    ["wallet"]="8208"
    ["storage"]="8209"
    ["order"]="8210"
    ["task"]="8211"
    ["organization"]="8212"
    ["invitation"]="8213"
    ["vault"]="8214"
    ["product"]="8215"
    ["billing"]="8216"
    ["calendar"]="8217"
    ["weather"]="8218"
    ["album"]="8219"
    ["device"]="8220"
    ["ota"]="8221"
    ["media"]="8222"
    ["memory"]="8223"
    ["location"]="8224"
    ["telemetry"]="8225"
    ["compliance"]="8226"
    ["document"]="8227"
    ["subscription"]="8228"
    ["credit"]="8229"
    ["event"]="8230"
    ["membership"]="8250"
)

# Parse arguments
ENV="${1:-staging}"
SPECIFIC_SERVICE="$2"
DRY_RUN=""

if [ "$ENV" = "--help" ]; then
    echo "Usage: $0 <environment> [service] [--dry-run]"
    echo ""
    echo "Environments:"
    echo "  staging      Deploy to isa-cloud-staging namespace"
    echo "  production   Deploy to isa-cloud-production namespace"
    echo ""
    echo "Options:"
    echo "  [service]    Deploy only specific service (e.g., auth, billing)"
    echo "  --dry-run    Show what would be deployed without deploying"
    echo ""
    echo "Examples:"
    echo "  $0 staging              # Deploy all to staging"
    echo "  $0 staging auth         # Deploy only auth to staging"
    echo "  $0 production --dry-run # Dry run for production"
    exit 0
fi

if [ "$2" = "--dry-run" ] || [ "$3" = "--dry-run" ]; then
    DRY_RUN="--dry-run"
fi

if [ "$2" != "--dry-run" ] && [ -n "$2" ]; then
    SPECIFIC_SERVICE="$2"
fi

# Set namespace and values file
if [ "$ENV" = "production" ]; then
    NAMESPACE="isa-cloud-production"
    VALUES_FILE="deployment/helm/values-production.yaml"
    REGISTRY="harbor.isa.io"
else
    NAMESPACE="isa-cloud-staging"
    VALUES_FILE="deployment/helm/values-staging.yaml"
    REGISTRY="harbor.local:30443"
fi

echo "========================================="
echo "Deploying ISA User Platform"
echo "Environment: $ENV"
echo "Namespace: $NAMESPACE"
echo "Registry: $REGISTRY"
echo "========================================="
echo ""

# Build service list
if [ -n "$SPECIFIC_SERVICE" ]; then
    if [ -z "${SERVICES[$SPECIFIC_SERVICE]}" ]; then
        echo "Error: Service '$SPECIFIC_SERVICE' not found"
        echo "Available services: ${!SERVICES[*]}"
        exit 1
    fi
    DEPLOY_SERVICES=("$SPECIFIC_SERVICE")
else
    DEPLOY_SERVICES=("${!SERVICES[@]}")
fi

echo "Services to deploy: ${#DEPLOY_SERVICES[@]}"
echo ""

for svc in "${DEPLOY_SERVICES[@]}"; do
    port="${SERVICES[$svc]}"
    release_name="user-${svc}-service"

    echo "Deploying ${release_name} (port ${port})..."

    helm upgrade --install "${release_name}" "${CHART_PATH}" \
        -f "${VALUES_FILE}" \
        --set name="${release_name}" \
        --set image.registry="${REGISTRY}" \
        --set image.repository="isa/user-${svc}" \
        --set port="${port}" \
        --set "env[0].name=SERVICE_NAME" \
        --set "env[0].value=${svc}_service" \
        --set "env[1].name=SERVICE_PORT" \
        --set "env[1].value=${port}" \
        -n "${NAMESPACE}" \
        ${DRY_RUN}

    echo "Deployed ${release_name}"
    echo ""
done

echo "========================================="
echo "Deployment complete!"
echo "========================================="

if [ -z "$DRY_RUN" ]; then
    echo ""
    echo "Check status with:"
    echo "  kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=user-*"
fi
