#!/usr/bin/env bash
# ============================================================================
# Test Common Framework for isA_user Microservices
# Requires Bash 4.0+ for associative arrays
# ============================================================================
# Usage: source this file at the beginning of your test script
#
# Example:
#   #!/bin/bash
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/../../../tests/test_common.sh"
#
#   # Set service-specific config
#   SERVICE_NAME="storage_service"
#   SERVICE_PORT="8209"
#   API_PATH="/api/v1/storage"
#
#   # Initialize (call after setting SERVICE_NAME, SERVICE_PORT, API_PATH)
#   init_test
#
#   # Your tests here using: api_get, api_post, api_put, api_delete
# ============================================================================

# ============================================================================
# Service Port Registry (compatible with bash 3.x on macOS)
# ============================================================================
get_service_port() {
    local service_name="$1"
    case "$service_name" in
        auth_service) echo "8201" ;;
        account_service) echo "8202" ;;
        session_service) echo "8203" ;;
        authorization_service) echo "8204" ;;
        audit_service) echo "8205" ;;
        notification_service) echo "8206" ;;
        payment_service) echo "8207" ;;
        wallet_service) echo "8208" ;;
        storage_service) echo "8209" ;;
        order_service) echo "8210" ;;
        task_service) echo "8211" ;;
        organization_service) echo "8212" ;;
        invitation_service) echo "8213" ;;
        vault_service) echo "8214" ;;
        product_service) echo "8215" ;;
        billing_service) echo "8216" ;;
        calendar_service) echo "8217" ;;
        weather_service) echo "8218" ;;
        album_service) echo "8219" ;;
        device_service) echo "8220" ;;
        ota_service) echo "8221" ;;
        media_service) echo "8222" ;;
        memory_service) echo "8223" ;;
        location_service) echo "8224" ;;
        telemetry_service) echo "8225" ;;
        compliance_service) echo "8226" ;;
        document_service) echo "8227" ;;
        subscription_service) echo "8228" ;;
        event_service) echo "8230" ;;
        *) echo "" ;;
    esac
}

# ============================================================================
# Configuration
# ============================================================================
# Test mode: "gateway" (via APISIX) or "direct" (service port)
TEST_MODE="${TEST_MODE:-direct}"

# Gateway URL
GATEWAY_URL="${GATEWAY_URL:-http://localhost}"

# Default test user
TEST_USER_ID="${TEST_USER_ID:-test_user_001}"
TEST_USER_EMAIL="${TEST_USER_EMAIL:-testuser@example.com}"

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ============================================================================
# Test Counters
# ============================================================================
PASSED=0
FAILED=0
TOTAL=0

# ============================================================================
# JWT Token (set by init_test)
# ============================================================================
JWT_TOKEN=""
AUTH_HEADER=""

# ============================================================================
# Core Functions
# ============================================================================

# Test result function
test_result() {
    TOTAL=$((TOTAL + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# Print section header
print_section() {
    echo ""
    echo -e "${YELLOW}$1${NC}"
}

# Print info
print_info() {
    echo -e "${BLUE}$1${NC}"
}

# Print success
print_success() {
    echo -e "${GREEN}$1${NC}"
}

# Print error
print_error() {
    echo -e "${RED}$1${NC}"
}

# Uppercase string (bash 3.x compatible)
to_uppercase() {
    echo "$1" | tr '[:lower:]' '[:upper:]'
}

# ============================================================================
# JWT Token Management
# ============================================================================

# Obtain JWT token from auth service
obtain_jwt_token() {
    local user_id="${1:-$TEST_USER_ID}"
    local email="${2:-$TEST_USER_EMAIL}"
    local expires_in="${3:-3600}"

    local auth_url
    local auth_port=$(get_service_port "auth_service")
    if [ "$TEST_MODE" = "gateway" ]; then
        auth_url="${GATEWAY_URL}/api/v1/auth/dev-token"
    else
        auth_url="http://localhost:${auth_port}/api/v1/auth/dev-token"
    fi

    local response
    response=$(curl -s -X POST "$auth_url" \
        -H "Content-Type: application/json" \
        -d "{\"user_id\": \"${user_id}\", \"email\": \"${email}\", \"expires_in\": ${expires_in}}")

    JWT_TOKEN=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

    if [ -z "$JWT_TOKEN" ] || [ "$JWT_TOKEN" = "null" ]; then
        print_error "Failed to obtain JWT token"
        echo "Response: $response"
        return 1
    fi

    AUTH_HEADER="Authorization: Bearer $JWT_TOKEN"
    return 0
}

# ============================================================================
# HTTP Request Helpers
# ============================================================================

# GET request
api_get() {
    local endpoint="$1"
    local url="${API_BASE}${endpoint}"

    if [ -n "$AUTH_HEADER" ]; then
        curl -s -H "$AUTH_HEADER" "$url"
    else
        curl -s "$url"
    fi
}

# POST request with JSON body
api_post() {
    local endpoint="$1"
    local data="$2"
    local url="${API_BASE}${endpoint}"

    if [ -n "$AUTH_HEADER" ]; then
        curl -s -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" -d "$data" "$url"
    else
        curl -s -X POST -H "Content-Type: application/json" -d "$data" "$url"
    fi
}

# POST request with form data
api_post_form() {
    local endpoint="$1"
    shift  # Remove first argument, rest are form fields
    local url="${API_BASE}${endpoint}"

    if [ -n "$AUTH_HEADER" ]; then
        curl -s -X POST -H "$AUTH_HEADER" "$@" "$url"
    else
        curl -s -X POST "$@" "$url"
    fi
}

# PUT request with JSON body
api_put() {
    local endpoint="$1"
    local data="$2"
    local url="${API_BASE}${endpoint}"

    if [ -n "$AUTH_HEADER" ]; then
        curl -s -X PUT -H "$AUTH_HEADER" -H "Content-Type: application/json" -d "$data" "$url"
    else
        curl -s -X PUT -H "Content-Type: application/json" -d "$data" "$url"
    fi
}

# DELETE request
api_delete() {
    local endpoint="$1"
    local url="${API_BASE}${endpoint}"

    if [ -n "$AUTH_HEADER" ]; then
        curl -s -X DELETE -H "$AUTH_HEADER" "$url"
    else
        curl -s -X DELETE "$url"
    fi
}

# ============================================================================
# Initialization
# ============================================================================

# Initialize test environment
# Call after setting SERVICE_NAME, SERVICE_PORT (optional), API_PATH
init_test() {
    # Get service port from registry if not set
    if [ -z "$SERVICE_PORT" ] && [ -n "$SERVICE_NAME" ]; then
        SERVICE_PORT=$(get_service_port "$SERVICE_NAME")
    fi

    # Validate required variables
    if [ -z "$SERVICE_NAME" ]; then
        print_error "SERVICE_NAME not set"
        exit 1
    fi

    if [ -z "$SERVICE_PORT" ]; then
        print_error "SERVICE_PORT not set and not found in registry for $SERVICE_NAME"
        exit 1
    fi

    # Set base URL based on test mode
    if [ "$TEST_MODE" = "gateway" ]; then
        BASE_URL="$GATEWAY_URL"
        API_BASE="${BASE_URL}${API_PATH:-/api/v1}"
    else
        BASE_URL="http://localhost:${SERVICE_PORT}"
        API_BASE="${BASE_URL}${API_PATH:-/api/v1}"
    fi

    # Print header
    local SERVICE_NAME_UPPER=$(to_uppercase "$SERVICE_NAME")
    echo -e "${CYAN}======================================================================${NC}"
    echo -e "${CYAN}     ${SERVICE_NAME_UPPER} TEST${NC}"
    echo -e "${CYAN}======================================================================${NC}"

    if [ "$TEST_MODE" = "gateway" ]; then
        echo -e "${BLUE}Test Mode: GATEWAY (via APISIX, JWT required)${NC}"
    else
        echo -e "${BLUE}Test Mode: DIRECT (port ${SERVICE_PORT}, no JWT required)${NC}"
    fi
    echo -e "${BLUE}Base URL: ${BASE_URL}${NC}"
    echo -e "${BLUE}API Base: ${API_BASE}${NC}"
    echo ""

    # Obtain JWT token if in gateway mode
    if [ "$TEST_MODE" = "gateway" ]; then
        echo -e "${YELLOW}Obtaining JWT Token...${NC}"
        if obtain_jwt_token; then
            echo -e "${GREEN}✓ JWT Token obtained (first 50 chars): ${JWT_TOKEN:0:50}...${NC}"
        else
            exit 1
        fi
        echo ""
    fi
}

# Print test summary
print_summary() {
    echo ""
    echo -e "${CYAN}======================================================================${NC}"
    echo -e "${CYAN}                         TEST SUMMARY${NC}"
    echo -e "${CYAN}======================================================================${NC}"
    echo -e "Total Tests: ${TOTAL}"
    echo -e "${GREEN}Passed: ${PASSED}${NC}"
    echo -e "${RED}Failed: ${FAILED}${NC}"
    echo ""

    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
        return 0
    else
        echo -e "${RED}✗ SOME TESTS FAILED${NC}"
        return 1
    fi
}

# ============================================================================
# JSON Helpers
# ============================================================================

# Pretty print JSON
json_pretty() {
    python3 -m json.tool 2>/dev/null || cat
}

# Extract JSON field
json_get() {
    local json="$1"
    local field="$2"
    echo "$json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('$field', ''))" 2>/dev/null
}

# Check if JSON contains field
json_has() {
    local json="$1"
    local field="$2"
    echo "$json" | grep -q "\"$field\""
}

# ============================================================================
# Health Check
# ============================================================================

# Check service health
check_health() {
    local health_url="${BASE_URL}/health"
    local response
    response=$(curl -s "$health_url")

    if echo "$response" | grep -q '"status".*"healthy"'; then
        print_success "✓ Service is healthy"
        return 0
    else
        print_error "✗ Service health check failed"
        echo "Response: $response"
        return 1
    fi
}

# ============================================================================
# Export for sourcing scripts
# ============================================================================
export TEST_MODE GATEWAY_URL TEST_USER_ID TEST_USER_EMAIL
export RED GREEN YELLOW CYAN BLUE MAGENTA NC
export PASSED FAILED TOTAL
export JWT_TOKEN AUTH_HEADER
export BASE_URL API_BASE
