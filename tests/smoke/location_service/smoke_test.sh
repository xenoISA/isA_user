#!/bin/bash
# =============================================================================
# Smoke Tests: Location Service
#
# Quick health and connectivity checks for location_service deployment.
# Run before integration tests to verify service availability.
#
# Service: location_service
# Port: 8224
#
# 访问方式:
#   - API 测试: 通过 APISIX 网关 (GATEWAY_URL)
#   - Health 检查: 直连服务 (SERVICE_URL) - 因为 /health 不同步到网关
#
# 环境变量:
#   GATEWAY_URL  - APISIX 网关地址 (默认: http://localhost:8000)
#   SERVICE_URL  - 直连服务地址 (默认: http://localhost:8224)
#
# Usage:
#   ./smoke_test.sh                       # 使用默认配置
#   GATEWAY_URL=http://localhost:8000 SERVICE_URL=http://localhost:8224 ./smoke_test.sh
# =============================================================================

set -e

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
SERVICE_URL="${SERVICE_URL:-http://localhost:8224}"
# 保留旧变量以保持兼容性
LOCATION_SERVICE_URL="${LOCATION_SERVICE_URL:-$SERVICE_URL}"
TEST_TIMEOUT="${TEST_TIMEOUT:-10}"
VERBOSE="${VERBOSE:-false}"

# API paths
API_BASE_PATH="/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
TOTAL=0

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "  ${YELLOW}TEST:${NC} $1"
}

log_pass() {
    echo -e "  ${GREEN}PASS:${NC} $1"
    ((PASSED++))
    ((TOTAL++))
}

log_fail() {
    echo -e "  ${RED}FAIL:${NC} $1"
    ((FAILED++))
    ((TOTAL++))
}

# Make HTTP request and check response
check_endpoint() {
    local method="$1"
    local url="$2"
    local expected_codes="$3"
    local description="$4"
    local data="$5"

    log_test "$description"

    local response_code
    local curl_opts="-s -o /dev/null -w %{http_code} --connect-timeout $TEST_TIMEOUT"

    if [ -n "$data" ]; then
        response_code=$(curl $curl_opts -X "$method" -H "Content-Type: application/json" -d "$data" "$url")
    else
        response_code=$(curl $curl_opts -X "$method" "$url")
    fi

    # Check if response code matches any expected code
    if echo "$expected_codes" | grep -q "$response_code"; then
        log_pass "$description (HTTP $response_code)"
        return 0
    else
        log_fail "$description (HTTP $response_code, expected: $expected_codes)"
        return 1
    fi
}

# Check if response contains expected content
check_endpoint_content() {
    local url="$1"
    local expected_content="$2"
    local description="$3"

    log_test "$description"

    local response
    response=$(curl -s --connect-timeout "$TEST_TIMEOUT" "$url" 2>/dev/null || echo "")

    if echo "$response" | grep -q "$expected_content"; then
        log_pass "$description"
        return 0
    else
        log_fail "$description (content not found: $expected_content)"
        return 1
    fi
}

# =============================================================================
# Smoke Tests
# =============================================================================

echo "=========================================="
echo " Location Service Smoke Tests"
echo "=========================================="
echo " Gateway URL: $GATEWAY_URL"
echo " Service URL: $SERVICE_URL (for health check)"
echo "=========================================="
echo ""

# -----------------------------------------------------------------------------
# Health Check Tests (直连服务 - /health 不同步到网关)
# -----------------------------------------------------------------------------
echo "Health Check Tests (Direct Service Access)"
echo "-------------------------------------------"

check_endpoint "GET" "$SERVICE_URL/health" "200" \
    "Health endpoint returns 200 (direct)"

check_endpoint_content "$SERVICE_URL/health" "status" \
    "Health response contains status field"

# -----------------------------------------------------------------------------
# API Endpoint Availability Tests (通过网关)
# -----------------------------------------------------------------------------
echo ""
echo "API Endpoint Availability Tests (via Gateway)"
echo "----------------------------------------------"

# Location endpoints (使用实际的 API 路径)
check_endpoint "GET" "$GATEWAY_URL/api/v1/locations/device/test-device" "200 401 403 404" \
    "Device locations endpoint accessible"

check_endpoint "GET" "$GATEWAY_URL/api/v1/locations/device/test-device/latest" "200 401 403 404" \
    "Latest location endpoint accessible"

# Geofence endpoints
check_endpoint "GET" "$GATEWAY_URL/api/v1/geofences" "200 401 403" \
    "Geofences list endpoint accessible"

# Place endpoints (使用实际的 API 路径)
check_endpoint "GET" "$GATEWAY_URL/api/v1/places/user/test-user" "200 401 403 404" \
    "User places endpoint accessible"

# Search endpoints (使用实际的 API 路径)
check_endpoint "GET" "$GATEWAY_URL/api/v1/locations/nearby?latitude=37.7749&longitude=-122.4194&radius_meters=1000" "200 401 403 404" \
    "Nearby search endpoint accessible"

# Distance endpoint
check_endpoint "GET" "$GATEWAY_URL/api/v1/distance?from_lat=37.7749&from_lon=-122.4194&to_lat=40.7128&to_lon=-74.0060" "200 401 403 422" \
    "Distance endpoint accessible"

# Stats endpoint (使用实际的 API 路径)
check_endpoint "GET" "$GATEWAY_URL/api/v1/stats/user/test-user" "200 401 403 404" \
    "Stats endpoint accessible"

# -----------------------------------------------------------------------------
# POST Endpoint Tests (通过网关)
# -----------------------------------------------------------------------------
echo ""
echo "POST Endpoint Tests (via Gateway)"
echo "----------------------------------"

# Location report (使用实际的 API 路径)
check_endpoint "POST" "$GATEWAY_URL/api/v1/locations" "200 201 400 401 403 422" \
    "Location report endpoint accessible" \
    '{"device_id":"smoke-test-device","latitude":37.7749,"longitude":-122.4194,"accuracy":10.0}'

# Batch location report
check_endpoint "POST" "$GATEWAY_URL/api/v1/locations/batch" "200 201 400 401 403 422" \
    "Batch location endpoint accessible" \
    '{"locations":[{"device_id":"smoke-test","latitude":37.7749,"longitude":-122.4194,"accuracy":10}]}'

# Geofence creation
check_endpoint "POST" "$GATEWAY_URL/api/v1/geofences" "200 201 400 401 403 422 500" \
    "Geofence creation endpoint accessible" \
    '{"name":"Smoke Test Geofence","shape_type":"circle","center_lat":37.7749,"center_lon":-122.4194,"radius":500}'

# Place creation
check_endpoint "POST" "$GATEWAY_URL/api/v1/places" "200 201 400 401 403 422" \
    "Place creation endpoint accessible" \
    '{"name":"Smoke Test Place","category":"home","latitude":37.7749,"longitude":-122.4194}'

# -----------------------------------------------------------------------------
# Validation Tests (通过网关)
# -----------------------------------------------------------------------------
echo ""
echo "Input Validation Tests (via Gateway)"
echo "-------------------------------------"

# Invalid latitude (> 90)
check_endpoint "POST" "$GATEWAY_URL/api/v1/locations" "400 422" \
    "Invalid latitude rejected" \
    '{"device_id":"test","latitude":91.0,"longitude":0,"accuracy":10}'

# Invalid longitude (> 180)
check_endpoint "POST" "$GATEWAY_URL/api/v1/locations" "400 422" \
    "Invalid longitude rejected" \
    '{"device_id":"test","latitude":0,"longitude":181,"accuracy":10}'

# Invalid accuracy (negative)
check_endpoint "POST" "$GATEWAY_URL/api/v1/locations" "400 422" \
    "Invalid accuracy rejected" \
    '{"device_id":"test","latitude":0,"longitude":0,"accuracy":-10}'

# Empty geofence name
check_endpoint "POST" "$GATEWAY_URL/api/v1/geofences" "400 422" \
    "Empty geofence name rejected" \
    '{"name":"","shape_type":"circle","center_lat":0,"center_lon":0,"radius":500}'

# Invalid polygon (< 3 points)
check_endpoint "POST" "$GATEWAY_URL/api/v1/geofences" "400 422" \
    "Invalid polygon rejected" \
    '{"name":"Test","shape_type":"polygon","center_lat":0,"center_lon":0,"polygon_coordinates":[[0,0],[1,1]]}'

# Empty batch
check_endpoint "POST" "$GATEWAY_URL/api/v1/locations/batch" "400 422" \
    "Empty batch rejected" \
    '{"locations":[]}'

# -----------------------------------------------------------------------------
# Error Handling Tests (通过网关)
# -----------------------------------------------------------------------------
echo ""
echo "Error Handling Tests (via Gateway)"
echo "-----------------------------------"

# Non-existent endpoint
check_endpoint "GET" "$GATEWAY_URL/api/v1/locations/nonexistent" "404" \
    "Non-existent endpoint returns 404"

# Invalid JSON
response_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$TEST_TIMEOUT" \
    -X POST -H "Content-Type: application/json" -d "not valid json" \
    "$GATEWAY_URL/api/v1/locations" 2>/dev/null || echo "000")
if [ "$response_code" = "400" ] || [ "$response_code" = "422" ]; then
    log_pass "Invalid JSON body rejected (HTTP $response_code)"
    ((PASSED++))
    ((TOTAL++))
else
    log_fail "Invalid JSON body not properly rejected (HTTP $response_code)"
    ((FAILED++))
    ((TOTAL++))
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=========================================="
echo " Smoke Test Summary"
echo "=========================================="
echo -e " Total:  ${TOTAL}"
echo -e " Passed: ${GREEN}${PASSED}${NC}"
echo -e " Failed: ${RED}${FAILED}${NC}"
echo "=========================================="

if [ "$FAILED" -gt 0 ]; then
    log_error "Some smoke tests failed!"
    exit 1
else
    log_info "All smoke tests passed!"
    exit 0
fi
