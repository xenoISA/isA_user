#!/bin/bash
# Redeploy microservice to Kind Kubernetes cluster
# Usage: ./scripts/redeploy_k8s.sh <service_name>
# Example: ./scripts/redeploy_k8s.sh storage

set -e

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

SERVICE_SHORT_NAME="$1"
SERVICE_FULL_NAME="${SERVICE_SHORT_NAME}_service"
SERVICE_IMAGE="isa-${SERVICE_SHORT_NAME}:latest"
DEPLOYMENT_NAME="${SERVICE_SHORT_NAME}"

log_step "🚀 Redeploying ${SERVICE_FULL_NAME} to Kind Kubernetes"

# Step 1: Build Docker image
log_step "Step 1: Building Docker image"
log_info "Running build-all-images.sh --service ${SERVICE_SHORT_NAME} --no-cache..."

cd /Users/xenodennis/Documents/Fun/isA_user

if ./deployment/k8s/build-all-images.sh --service "${SERVICE_SHORT_NAME}" --no-load --no-cache; then
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

# Step 3: Delete old pod
log_step "Step 3: Deleting old pod"
log_info "Finding pods for deployment: ${DEPLOYMENT_NAME}..."

POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "app=${DEPLOYMENT_NAME}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$POD_NAME" ]; then
    log_warning "No existing pod found for ${DEPLOYMENT_NAME}"
else
    log_info "Deleting pod: ${POD_NAME}"
    if kubectl delete pod "${POD_NAME}" -n "${NAMESPACE}"; then
        log_success "Pod deleted successfully"
    else
        log_error "Failed to delete pod"
        exit 1
    fi
fi

# Step 4: Wait for new pod to start
log_step "Step 4: Waiting for new pod to start"
log_info "Waiting for pod to be ready (timeout: ${WAIT_TIMEOUT}s)..."

START_TIME=$(date +%s)
while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    if [ $ELAPSED -gt $WAIT_TIMEOUT ]; then
        log_error "Timeout waiting for pod to start"
        exit 1
    fi

    POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "app=${DEPLOYMENT_NAME}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -n "$POD_NAME" ]; then
        POD_STATUS=$(kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        POD_READY=$(kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")

        log_info "Pod: ${POD_NAME} | Status: ${POD_STATUS} | Ready: ${POD_READY}"

        if [ "$POD_STATUS" = "Running" ] && [ "$POD_READY" = "True" ]; then
            log_success "Pod is running and ready"
            break
        fi
    fi

    sleep 3
done

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
echo "  Restart pod:  kubectl delete pod ${POD_NAME} -n ${NAMESPACE}"
echo "  Service info: kubectl get svc ${DEPLOYMENT_NAME} -n ${NAMESPACE}"
echo ""

log_success "✨ Redeploy complete!"
