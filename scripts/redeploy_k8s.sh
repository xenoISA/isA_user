#!/bin/bash
# Redeploy microservice to Kind Kubernetes cluster
# Usage: ./scripts/redeploy_k8s.sh <service_name>
# Example: ./scripts/redeploy_k8s.sh storage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

resolve_target() {
    resolved_target="$(python3 core/deployment_targets.py "$1" --format env)" || return 1
    while IFS='=' read -r key value; do
        printf -v "$key" '%s' "$value"
    done <<< "${resolved_target}"
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
KIND_CLUSTER_NAME="isa-cloud-local"
NAMESPACE="isa-cloud-staging"
CONSUL_POD=""
WAIT_TIMEOUT=120  # seconds

# Function to print colored messages
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Check if service name provided
if [ -z "$1" ]; then
    log_error "Service name required"
    echo "Usage: $0 <service_name>"
    echo ""
    echo "Available services:"
    echo "  auth, account, session, authorization, audit"
    echo "  notification, payment, wallet, storage, order"
    echo "  task, organization, invitation, vault, product"
    echo "  billing, calendar, weather, album, device"
    echo "  ota, media, memory, location, telemetry"
    echo "  compliance, event"
    echo ""
    echo "Example: $0 storage"
    exit 1
fi

SERVICE_INPUT="$1"
cd "${REPO_ROOT}"
resolve_target "${SERVICE_INPUT}"

SERVICE_SHORT_NAME="${TARGET_SHORT_NAME}"
SERVICE_FULL_NAME="${TARGET_SERVICE_DIR}"
SERVICE_IMAGE="harbor.local:30443/isa/user-${TARGET_IMAGE_NAME}:latest"
DEPLOYMENT_NAME="${TARGET_DEPLOYMENT_NAME}"
NAMESPACE="$(python3 core/deployment_targets.py --namespace staging)"

log_step "🚀 Redeploying ${SERVICE_FULL_NAME} to Kind Kubernetes"

# Step 1: Build Docker image
log_step "Step 1: Building Docker image"
log_info "Running deployment/docker/build.sh staging --service ${SERVICE_SHORT_NAME} --no-cache..."

if ./deployment/docker/build.sh staging --service "${SERVICE_SHORT_NAME}" --no-load --no-cache; then
    log_success "Docker image built successfully"
else
    log_error "Failed to build Docker image"
    exit 1
fi

# Step 2: Load image to Kind
log_step "Step 2: Loading image to Kind cluster"
log_info "Loading ${SERVICE_IMAGE} to ${KIND_CLUSTER_NAME}..."

if kind load docker-image "${SERVICE_IMAGE}" --name "${KIND_CLUSTER_NAME}"; then
    log_success "Image loaded to Kind cluster"
else
    log_error "Failed to load image to Kind"
    exit 1
fi

# Step 3: Restart deployment
log_step "Step 3: Restarting deployment"
log_info "Restarting deployment/${DEPLOYMENT_NAME} in ${NAMESPACE}..."

if kubectl rollout restart "deployment/${DEPLOYMENT_NAME}" -n "${NAMESPACE}"; then
    log_success "Deployment restart triggered"
else
    log_error "Failed to restart deployment"
    exit 1
fi

# Step 4: Wait for rollout
log_step "Step 4: Waiting for rollout to complete"
log_info "Waiting for deployment/${DEPLOYMENT_NAME} rollout (timeout: ${WAIT_TIMEOUT}s)..."

if kubectl rollout status "deployment/${DEPLOYMENT_NAME}" -n "${NAMESPACE}" --timeout="${WAIT_TIMEOUT}s"; then
    log_success "Deployment rollout completed"
else
    log_error "Timeout waiting for rollout to complete"
    exit 1
fi

POD_NAME=$(kubectl get pods -n "${NAMESPACE}" --sort-by=.metadata.creationTimestamp -o name | grep "${DEPLOYMENT_NAME}-" | tail -1 | cut -d/ -f2)

# Step 5: Verify Consul registration
log_step "Step 5: Verifying Consul registration"
log_info "Finding Consul pod..."

CONSUL_POD=$(kubectl get pods -n "${NAMESPACE}" -l "app=consul" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$CONSUL_POD" ]; then
    log_warning "Consul pod not found, skipping registration check"
else
    log_info "Waiting for service to register with Consul..."
    sleep 10  # Give service time to register

    # Check Consul for service registration
    log_info "Checking Consul catalog..."
    CONSUL_SERVICES=$(kubectl exec -n "${NAMESPACE}" "${CONSUL_POD}" -- consul catalog services 2>/dev/null || echo "")

    if echo "$CONSUL_SERVICES" | grep -q "${SERVICE_FULL_NAME}"; then
        log_success "Service registered in Consul: ${SERVICE_FULL_NAME}"

        # Get service details
        log_info "Service details:"
        kubectl exec -n "${NAMESPACE}" "${CONSUL_POD}" -- consul catalog service "${SERVICE_FULL_NAME}" 2>/dev/null || true
    else
        log_warning "Service not yet visible in Consul catalog"
        log_info "Available services in Consul:"
        echo "$CONSUL_SERVICES"
    fi
fi

# Step 6: Check pod logs
log_step "Step 6: Checking pod logs"
log_info "Recent logs from ${POD_NAME}:"
echo "----------------------------------------"
kubectl logs "${POD_NAME}" -n "${NAMESPACE}" --tail=20 || log_warning "Could not fetch logs"
echo "----------------------------------------"

# Step 7: Show pod status
log_step "Step 7: Final status"
kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" -o wide

log_success "Deployment completed successfully!"
log_info "Service: ${SERVICE_FULL_NAME}"
log_info "Pod: ${POD_NAME}"
log_info "Namespace: ${NAMESPACE}"

echo ""
log_info "Useful commands:"
echo "  Watch logs:   kubectl logs -f ${POD_NAME} -n ${NAMESPACE}"
echo "  Pod details:  kubectl describe pod ${POD_NAME} -n ${NAMESPACE}"
echo "  Restart pod:  kubectl rollout restart deployment/${DEPLOYMENT_NAME} -n ${NAMESPACE}"
echo "  Service info: kubectl get svc ${TARGET_K8S_SERVICE_NAME} -n ${NAMESPACE}"
echo ""

log_success "✨ Redeploy complete!"
