#!/bin/bash

set -e

cd /Users/xenodennis/Documents/Fun/isA_user

# 微服务列表
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
    "event_service:8230"
)

# Parse command line arguments
SPECIFIC_SERVICE=""
LOAD_TO_KIND=true
NO_CACHE=false
BUILD_BASE=true
BASE_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
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
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --service <name>   Build only specific service (e.g., billing, wallet)"
            echo "  --no-load          Skip loading images to Kind cluster"
            echo "  --no-cache         Build without using Docker cache (forces fresh build)"
            echo "  --no-base          Skip building base image (use existing)"
            echo "  --base-only        Build only the base image"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                          # Build base + all services"
            echo "  $0 --base-only              # Build only base image (for isa-common upgrade)"
            echo "  $0 --service billing        # Build base + billing service"
            echo "  $0 --service wallet --no-base   # Build wallet using existing base"
            echo "  $0 --no-cache               # Fresh build of everything"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# =========================================
# Build Base Image (contains isa-common and all shared deps)
# =========================================
if [ "$BUILD_BASE" = true ]; then
    echo "========================================="
    echo "Building isa-user-base:latest (shared dependencies)"
    echo "========================================="

    if [ "$NO_CACHE" = true ]; then
        echo "Building with --no-cache..."
        docker build --no-cache \
            -f deployment/k8s/Dockerfile.base \
            -t isa-user-base:latest \
            .
    else
        docker build \
            -f deployment/k8s/Dockerfile.base \
            -t isa-user-base:latest \
            .
    fi

    echo "✓ Built isa-user-base:latest"
    echo ""

    if [ "$LOAD_TO_KIND" = true ]; then
        echo "Loading isa-user-base:latest to kind cluster..."
        kind load docker-image isa-user-base:latest --name isa-cloud-local
        echo "✓ Base image loaded to kind"
        echo ""
    fi
fi

# Exit if base-only mode
if [ "$BASE_ONLY" = true ]; then
    echo "✓ Base-only mode complete!"
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

    echo "Building isa-${short_name}:latest..."

    # Microservice builds are always fast (just copies code on top of base)
    docker build \
        --build-arg SERVICE_NAME=${service_name} \
        --build-arg SERVICE_PORT=${port} \
        -f deployment/k8s/Dockerfile.microservice \
        -t isa-${short_name}:latest \
        .

    echo "✓ Built isa-${short_name}:latest"
done

echo ""
echo "✓ All images built successfully!"
echo ""

if [ "$LOAD_TO_KIND" = true ]; then
    echo "Loading images to kind cluster..."

    for svc in "${BUILD_LIST[@]}"; do
        IFS=':' read -r service_name port <<< "$svc"
        short_name="${service_name%_service}"

        echo "Loading isa-${short_name}:latest to kind..."
        kind load docker-image isa-${short_name}:latest --name isa-cloud-local
    done

    echo ""
    echo "✓ All images loaded to kind cluster!"
else
    echo "Skipping Kind load (--no-load flag set)"
fi
