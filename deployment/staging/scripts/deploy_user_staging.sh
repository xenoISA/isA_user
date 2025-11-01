#!/bin/bash
# Deploy script for isA User Staging Environment
# This script builds and deploys all user services using Docker Compose
# Includes build caching for fast updates

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Configuration
IMAGE_NAME="isa-user-staging"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORM="linux/amd64"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION="${VERSION:-0.1.0}"
COMPOSE_FILE="${SCRIPT_DIR}/../user_staging.yml"
ENV_FILE="${SCRIPT_DIR}/../config/.env.staging"
PROJECT_NAME="isa-user-staging"

# Build control flag
FORCE_BUILD=false
SKIP_BUILD=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force-build)
            FORCE_BUILD=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --force-build    Force rebuild without using cache"
            echo "  --skip-build     Skip build step, only deploy"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print deployment information
print_deploy_info() {
    log_info "========================================"
    log_info "Building and Deploying isA User Staging"
    log_info "========================================"
    log_info "Image Name:    ${IMAGE_NAME}:${IMAGE_TAG}"
    log_info "Platform:      ${PLATFORM}"
    log_info "Build Date:    ${BUILD_DATE}"
    log_info "VCS Ref:       ${VCS_REF}"
    log_info "Version:       ${VERSION}"
    log_info "Project Name:  ${PROJECT_NAME}"
    log_info "Compose File:  ${COMPOSE_FILE}"
    log_info "========================================"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Check Docker buildx
    if ! docker buildx version &> /dev/null; then
        log_error "Docker buildx is not available. Please update Docker to the latest version."
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi

    # Check if compose file exists
    if [ ! -f "${COMPOSE_FILE}" ]; then
        log_error "Compose file not found: ${COMPOSE_FILE}"
        exit 1
    fi

    # Check if env file exists
    if [ ! -f "${ENV_FILE}" ]; then
        log_error "Environment file not found: ${ENV_FILE}"
        exit 1
    fi

    log_success "All prerequisites met"
}

# Check if rebuild is needed
check_rebuild_needed() {
    if [ "$SKIP_BUILD" = true ]; then
        log_info "Skipping build check (--skip-build flag)"
        return 1
    fi

    if [ "$FORCE_BUILD" = true ]; then
        log_info "Force rebuild requested (--force-build flag)"
        return 0
    fi

    # Check if image exists
    if ! docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" &> /dev/null; then
        log_info "Image does not exist, rebuild needed"
        return 0
    fi

    # Get image creation time
    local image_created=$(docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" --format='{{.Created}}' 2>/dev/null)
    local image_timestamp=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${image_created:0:19}" +%s 2>/dev/null || echo 0)

    # Check if any Python files or Dockerfile changed since image was built
    local recent_changes=$(find "${PROJECT_ROOT}" \
        -type f \
        \( -name "*.py" -o -name "Dockerfile*" -o -name "requirements*.txt" \) \
        -newer <(date -r ${image_timestamp} +"%Y-%m-%d %H:%M:%S" 2>/dev/null) 2>/dev/null | wc -l)

    if [ "$recent_changes" -gt 0 ]; then
        log_info "Code changes detected (${recent_changes} files), rebuild needed"
        return 0
    fi

    log_info "No code changes detected, using cached image"
    return 1
}

# Prepare isa_common package
prepare_isa_common() {
    log_info "isa_common will be installed from requirements.txt"
    # No longer copying from external directory
    # isa-common is specified in requirements.staging.txt
}

# Cleanup isa_common after build
cleanup_isa_common() {
    # No cleanup needed - isa-common installed via pip
    :
}

# Build the Docker image with caching
build_image() {
    log_info "Building Docker image for platform: ${PLATFORM}"

    cd "${PROJECT_ROOT}"

    local BUILD_ARGS=(
        --platform "${PLATFORM}"
        --file deployment/staging/Dockerfile.staging
        --build-arg BUILD_DATE="${BUILD_DATE}"
        --build-arg VCS_REF="${VCS_REF}"
        --build-arg VERSION="${VERSION}"
        --tag "${IMAGE_NAME}:${IMAGE_TAG}"
        --tag "${IMAGE_NAME}:${VERSION}"
        --tag "${IMAGE_NAME}:v${VERSION}"
    )

    # Add cache options for faster builds
    if [ "$FORCE_BUILD" = false ]; then
        BUILD_ARGS+=(
            --cache-from "type=local,src=/tmp/docker-cache-${IMAGE_NAME}"
            --cache-to "type=local,dest=/tmp/docker-cache-${IMAGE_NAME},mode=max"
        )
        log_info "Using build cache for faster builds"
    else
        BUILD_ARGS+=(--no-cache)
        log_info "Building without cache (--force-build)"
    fi

    BUILD_ARGS+=(--load .)

    # Build the image
    docker buildx build "${BUILD_ARGS[@]}"

    if [ $? -eq 0 ]; then
        log_success "Docker image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
    else
        log_error "Failed to build Docker image"
        cleanup_isa_common
        exit 1
    fi
}

# Show image information
show_image_info() {
    log_info "Image information:"
    docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
}

# Check if infrastructure services are running
check_infrastructure() {
    log_info "Checking infrastructure services..."

    # Check Supabase
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:54321/health 2>/dev/null | grep -q "200"; then
        log_success "Supabase is running and accessible"
    else
        log_warn "Supabase may not be running on localhost:54321"
        log_info "Database features may be limited"
    fi

    # Check Consul
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8500/v1/status/leader 2>/dev/null | grep -q "200"; then
        log_success "Consul is running and accessible"
    else
        log_warn "Consul may not be running on localhost:8500"
        log_info "Service discovery will not work without Consul"
    fi

    # Check Redis
    if command -v redis-cli &> /dev/null && redis-cli -h localhost -p 6379 ping 2>/dev/null | grep -q "PONG"; then
        log_success "Redis is running and accessible"
    else
        log_warn "Redis may not be running on localhost:6379"
        log_info "Caching features may be limited"
    fi
}

# Stop and remove existing containers
cleanup_old_containers() {
    log_info "Checking for existing containers..."

    # Stop and remove containers using docker compose
    cd "${SCRIPT_DIR}"
    if docker compose -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" ps -q 2>/dev/null | grep -q .; then
        log_info "Stopping and removing old containers..."
        docker compose -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" down
        log_success "Old containers removed successfully"
    else
        log_info "No existing containers found"
    fi
}

# Deploy with Docker Compose
deploy() {
    log_info "Deploying services..."

    cd "${SCRIPT_DIR}"

    # Deploy services
    docker compose -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" up -d

    if [ $? -eq 0 ]; then
        log_success "Services deployed successfully"
    else
        log_error "Failed to deploy services"
        exit 1
    fi
}

# Show service status
show_status() {
    log_info "Service status:"
    docker compose -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" ps
}

# Wait for services to be healthy
wait_for_health() {
    log_info "Waiting for services to be healthy..."

    local max_attempts=30
    local attempt=1
    local services=("auth:8201" "account:8202" "payment:8205")

    while [ $attempt -le $max_attempts ]; do
        local all_healthy=true

        for service in "${services[@]}"; do
            IFS=':' read -r name port <<< "$service"
            if ! curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/health" 2>/dev/null | grep -q "200"; then
                all_healthy=false
                break
            fi
        done

        if [ "$all_healthy" = true ]; then
            log_success "All services are healthy!"
            return 0
        fi

        log_info "Attempt ${attempt}/${max_attempts}: Services not ready yet..."
        sleep 2
        ((attempt++))
    done

    log_warn "Services did not become healthy within expected time"
    log_info "Check logs with: docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} logs -f"
    return 1
}

# Show service logs
show_logs() {
    log_info "Recent logs (last 20 lines):"
    docker compose -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" logs --tail=20
}

# Show useful commands
show_commands() {
    log_info ""
    log_info "Useful commands:"
    echo "  View logs:       docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} logs -f"
    echo "  Stop services:   docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} down"
    echo "  Restart:         docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} restart"
    echo "  Shell access:    docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} exec user bash"
    echo "  Health check:    curl http://localhost:8201/health"
    echo "  Rebuild:         $0 --force-build"
    log_info ""
}

# Main execution
main() {
    print_deploy_info
    check_prerequisites
    check_infrastructure

    # Build phase (with intelligent caching)
    if check_rebuild_needed; then
        log_info "Starting build process..."
        prepare_isa_common
        build_image
        cleanup_isa_common
        show_image_info
    else
        log_success "Using cached image, skipping build"
    fi

    # Deploy phase
    cleanup_old_containers
    deploy
    show_status

    log_info "Waiting for services to start..."
    sleep 5

    wait_for_health
    show_logs
    show_commands

    log_success "Deployment complete!"
    log_info "User services are available:"
    log_info "  - Auth Service:    http://localhost:8201"
    log_info "  - Account Service: http://localhost:8202"
    log_info "  - Payment Service: http://localhost:8205"
    log_info "  - And more on ports 8201-8230"
}

# Trap to ensure cleanup on exit
trap cleanup_isa_common EXIT

# Run main function
main "$@"
