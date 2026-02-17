#!/bin/bash
# =============================================================================
# Build ISA User Platform Docker Images
# =============================================================================
# Usage:
#   ./deployment/docker/build.sh                    # Build base + all services (staging)
#   ./deployment/docker/build.sh prod               # Build for production
#   ./deployment/docker/build.sh --base-only        # Build only base image
#   ./deployment/docker/build.sh --service auth     # Build base + auth service
#   ./deployment/docker/build.sh --service auth --no-base  # Build auth using existing base
# =============================================================================

set -e

cd "$(dirname "$0")/../.."

# Microservices with ports
SERVICES=(
    "auth_service:8201"
    "account_service:8202"
    "session_service:8203"
    "authorization_service:8204"
    "audit_service:8205"
    "notification_service:8206"
    "payment_service:8207"
    "wallet_service:8208"
    "storage_service:8209"
    "order_service:8210"
    "task_service:8211"
    "organization_service:8212"
    "invitation_service:8213"
    "vault_service:8214"
    "product_service:8215"
    "billing_service:8216"
    "calendar_service:8217"
    "weather_service:8218"
    "album_service:8219"
    "device_service:8220"
    "ota_service:8221"
    "media_service:8222"
    "memory_service:8223"
    "location_service:8224"
    "telemetry_service:8225"
    "compliance_service:8226"
    "document_service:8227"
    "subscription_service:8228"
    "credit_service:8229"
    "event_service:8230"
    "membership_service:8250"
)

# Parse command line arguments
ENV="staging"
SPECIFIC_SERVICE=""
LOAD_TO_KIND=true
NO_CACHE=false
BUILD_BASE=true
BASE_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        prod|production)
            ENV="production"
            shift
            ;;
        staging)
            ENV="staging"
            shift
            ;;
        --service)
            SPECIFIC_SERVICE="$2"
            shift 2
            ;;
        --no-load)
            LOAD_TO_KIND=false
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --no-base)
            BUILD_BASE=false
            shift
            ;;
        --base-only)
            BASE_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [ENV] [OPTIONS]"
            echo ""
            echo "Environments:"
            echo "  staging      Build for staging (harbor.local:30443) [default]"
            echo "  prod         Build for production (harbor.isa.io)"
            echo ""
            echo "Options:"
            echo "  --service <name>   Build only specific service (e.g., auth, billing)"
            echo "  --no-load          Skip loading images to Kind cluster"
            echo "  --no-cache         Build without using Docker cache"
            echo "  --no-base          Skip building base image (use existing)"
            echo "  --base-only        Build only the base image"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                          # Build base + all services for staging"
            echo "  $0 prod                     # Build base + all services for production"
            echo "  $0 --base-only              # Build only base image"
            echo "  $0 --service billing        # Build base + billing service"
            echo "  $0 --service wallet --no-base   # Build wallet using existing base"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# Set registry based on environment
if [ "$ENV" = "production" ]; then
    REGISTRY="harbor.isa.io"
else
    REGISTRY="harbor.local:30443"
fi

echo "========================================="
echo "Environment: $ENV"
echo "Registry: $REGISTRY"
echo "========================================="
echo ""

# Build Base Image
if [ "$BUILD_BASE" = true ]; then
    echo "Building ${REGISTRY}/isa/user-base:latest..."

    BUILD_CMD="docker build"
    if [ "$NO_CACHE" = true ]; then
        BUILD_CMD="$BUILD_CMD --no-cache"
    fi

    $BUILD_CMD \
        -f deployment/docker/Dockerfile.base \
        -t ${REGISTRY}/isa/user-base:latest \
        .

    echo "Built ${REGISTRY}/isa/user-base:latest"
    echo ""

    if [ "$LOAD_TO_KIND" = true ] && [ "$ENV" = "staging" ]; then
        echo "Loading user-base to Kind cluster..."
        kind load docker-image ${REGISTRY}/isa/user-base:latest --name isa-cloud-local
        echo "Base image loaded to Kind"
        echo ""
    fi
fi

# Exit if base-only mode
if [ "$BASE_ONLY" = true ]; then
    echo "Base-only mode complete!"
    exit 0
fi

# Filter services if specific service requested
BUILD_LIST=("${SERVICES[@]}")
if [ -n "$SPECIFIC_SERVICE" ]; then
    BUILD_LIST=()
    for svc in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port <<< "$svc"
        short_name="${service_name%_service}"
        if [ "$short_name" = "$SPECIFIC_SERVICE" ] || [ "$service_name" = "$SPECIFIC_SERVICE" ]; then
            BUILD_LIST+=("$svc")
            break
        fi
    done

    if [ ${#BUILD_LIST[@]} -eq 0 ]; then
        echo "Error: Service '$SPECIFIC_SERVICE' not found"
        echo "Available services:"
        for svc in "${SERVICES[@]}"; do
            IFS=':' read -r service_name port <<< "$svc"
            short_name="${service_name%_service}"
            echo "  - $short_name"
        done
        exit 1
    fi
fi

echo "========================================="
echo "Building microservice images..."
echo "Services to build: ${#BUILD_LIST[@]}"
echo "========================================="
echo ""

for svc in "${BUILD_LIST[@]}"; do
    IFS=':' read -r service_name port <<< "$svc"
    short_name="${service_name%_service}"

    echo "Building ${REGISTRY}/isa/user-${short_name}:latest..."

    docker build \
        --build-arg REGISTRY=${REGISTRY} \
        --build-arg SERVICE_NAME=${service_name} \
        --build-arg SERVICE_PORT=${port} \
        -f deployment/docker/Dockerfile.microservice \
        -t ${REGISTRY}/isa/user-${short_name}:latest \
        .

    echo "Built ${REGISTRY}/isa/user-${short_name}:latest"
done

echo ""
echo "All images built successfully!"
echo ""

if [ "$LOAD_TO_KIND" = true ] && [ "$ENV" = "staging" ]; then
    echo "Loading images to Kind cluster..."

    for svc in "${BUILD_LIST[@]}"; do
        IFS=':' read -r service_name port <<< "$svc"
        short_name="${service_name%_service}"

        echo "Loading user-${short_name} to Kind..."
        kind load docker-image ${REGISTRY}/isa/user-${short_name}:latest --name isa-cloud-local
    done

    echo ""
    echo "All images loaded to Kind cluster!"
else
    echo "To push to Harbor:"
    echo "  docker push ${REGISTRY}/isa/user-base:latest"
    for svc in "${BUILD_LIST[@]}"; do
        IFS=':' read -r service_name port <<< "$svc"
        short_name="${service_name%_service}"
        echo "  docker push ${REGISTRY}/isa/user-${short_name}:latest"
    done
fi
