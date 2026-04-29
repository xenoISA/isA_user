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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

DEFAULT_CHART_PATH="$(cd "${REPO_ROOT}/.." && pwd)/isA_Cloud/deployments/charts/isa-service"
CHART_PATH="${ISA_SERVICE_CHART_PATH:-${DEFAULT_CHART_PATH}}"

resolve_target() {
    resolved_target="$(python3 core/deployment_targets.py "$1" --format env)" || return 1
    while IFS='=' read -r key value; do
        printf -v "$key" '%s' "$value"
    done <<< "${resolved_target}"
}

# Parse arguments
ENV="${1:-staging}"
SPECIFIC_SERVICE="$2"
DRY_RUN=""

if [ "$ENV" = "--help" ]; then
    echo "Usage: $0 <environment> [service] [--dry-run]"
    echo ""
    echo "Environments:"
    echo "  staging      Deploy to isa-cloud-staging namespace"
    echo "  production   Deploy to isa-cloud-prod namespace"
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

if [ ! -d "${CHART_PATH}" ]; then
    echo "Error: Helm chart path not found: ${CHART_PATH}"
    echo "Set ISA_SERVICE_CHART_PATH to the isa-service chart directory."
    exit 1
fi

# Set namespace and values file
if [ "$ENV" = "production" ]; then
    NAMESPACE="$(python3 core/deployment_targets.py --namespace production)"
    VALUES_FILE="deployment/helm/values-production.yaml"
    REGISTRY="harbor.isa.io"
else
    NAMESPACE="$(python3 core/deployment_targets.py --namespace staging)"
    VALUES_FILE="deployment/helm/values-staging.yaml"
    REGISTRY="harbor.local:30443"
fi

echo "========================================="
echo "Deploying ISA User Platform"
echo "Environment: $ENV"
echo "Namespace: $NAMESPACE"
echo "Registry: $REGISTRY"
echo "Chart path: $CHART_PATH"
echo "========================================="
echo ""

# Build service list
if [ -n "$SPECIFIC_SERVICE" ]; then
    if ! resolve_target "$SPECIFIC_SERVICE" >/dev/null 2>&1; then
        echo "Error: Service '$SPECIFIC_SERVICE' not found"
        echo "Available services:"
        python3 core/deployment_targets.py --list-service-dirs
        exit 1
    fi
    DEPLOY_SERVICES=("$TARGET_SERVICE_DIR")
else
    IFS=',' read -r -a DEPLOY_SERVICES <<< "$(python3 core/deployment_targets.py --list-service-dirs --format csv)"
fi

echo "Services to deploy: ${#DEPLOY_SERVICES[@]}"
echo ""

for svc in "${DEPLOY_SERVICES[@]}"; do
    resolve_target "$svc"
    release_name="${TARGET_RELEASE_NAME}"

    echo "Deploying ${release_name} (port ${TARGET_SERVICE_PORT})..."

    helm upgrade --install "${release_name}" "${CHART_PATH}" \
        -f "${VALUES_FILE}" \
        --set name="${release_name}" \
        --set image.registry="${REGISTRY}" \
        --set image.repository="isa/user-${TARGET_IMAGE_NAME}" \
        --set port="${TARGET_SERVICE_PORT}" \
        --set "env[0].name=SERVICE_NAME" \
        --set "env[0].value=${TARGET_SERVICE_DIR}" \
        --set "env[1].name=SERVICE_PORT" \
        --set "env[1].value=${TARGET_SERVICE_PORT}" \
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
