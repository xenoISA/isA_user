#!/bin/bash

# Product Service Smoke Tests
# Quick validation that product_service is running and responding correctly
#
# Usage:
#   ./tests/smoke/product_service/smoke_test.sh
#
# Prerequisites:
#   - product_service running on port 8215
#   - curl available

set -e

SERVICE_URL="http://localhost:8215"
API_BASE="$SERVICE_URL/api/v1/product"
PASS_COUNT=0
FAIL_COUNT=0
TOTAL_TESTS=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Generate unique IDs for testing
TEST_USER_ID="user_smoke_$(date +%s)"
TEST_PRODUCT_ID="prod_smoke_$(date +%s)"
TEST_PLAN_ID="plan_smoke_$(date +%s)"

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS_COUNT++))
    ((TOTAL_TESTS++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL_COUNT++))
    ((TOTAL_TESTS++))
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

log_info() {
    echo -e "[INFO] $1"
}

# Test helper function
test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local expected_code="$4"
    local data="$5"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    else
        response=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$url")
    fi

    if [ "$response" = "$expected_code" ]; then
        log_pass "$name (HTTP $response)"
        return 0
    else
        log_fail "$name - Expected $expected_code, got $response"
        return 1
    fi
}

# Test with response body check
test_endpoint_contains() {
    local name="$1"
    local url="$2"
    local expected_field="$3"

    response=$(curl -s "$url")

    if echo "$response" | grep -q "$expected_field"; then
        log_pass "$name"
        return 0
    else
        log_fail "$name - Response missing '$expected_field'"
        return 1
    fi
}

echo "=============================================="
echo "Product Service Smoke Tests"
echo "Service URL: $SERVICE_URL"
echo "=============================================="
echo ""

# ============================================
# 1. Health Check Tests
# ============================================
echo "--- Health Check Tests ---"

test_endpoint "Health endpoint returns 200" "GET" "$SERVICE_URL/health" "200"
test_endpoint_contains "Health response has status field" "$SERVICE_URL/health" '"status"'
test_endpoint_contains "Health response has service field" "$SERVICE_URL/health" '"service"'
test_endpoint_contains "Health response shows product_service" "$SERVICE_URL/health" '"product_service"'

# ============================================
# 2. Service Info Tests
# ============================================
echo ""
echo "--- Service Info Tests ---"

test_endpoint "Service info endpoint returns 200" "GET" "$API_BASE/info" "200"
test_endpoint_contains "Info response has capabilities" "$API_BASE/info" '"capabilities"'

# ============================================
# 3. Product Catalog Tests
# ============================================
echo ""
echo "--- Product Catalog Tests ---"

test_endpoint "Categories endpoint returns 200" "GET" "$API_BASE/categories" "200"
test_endpoint "Products endpoint returns 200" "GET" "$API_BASE/products" "200"
test_endpoint "Products with filter returns 200" "GET" "$API_BASE/products?is_active=true" "200"
test_endpoint "Products invalid type returns 4xx" "GET" "$API_BASE/products?product_type=invalid_xyz" "400" || test_endpoint "Products invalid type returns 422" "GET" "$API_BASE/products?product_type=invalid_xyz" "422"

# ============================================
# 4. Product Detail Tests
# ============================================
echo ""
echo "--- Product Detail Tests ---"

test_endpoint "Non-existent product returns 404" "GET" "$API_BASE/products/prod_nonexistent_12345" "404"
test_endpoint "Product pricing non-existent returns 404 or 500" "GET" "$API_BASE/products/prod_nonexistent/pricing" "404" || test_endpoint "Product pricing non-existent returns 500" "GET" "$API_BASE/products/prod_nonexistent/pricing" "500"

# Availability check requires user_id
test_endpoint "Availability without user_id returns 4xx" "GET" "$API_BASE/products/$TEST_PRODUCT_ID/availability" "400" || test_endpoint "Availability without user_id returns 422" "GET" "$API_BASE/products/$TEST_PRODUCT_ID/availability" "422"

# ============================================
# 5. Subscription Tests
# ============================================
echo ""
echo "--- Subscription Tests ---"

test_endpoint "Non-existent subscription returns 404" "GET" "$API_BASE/subscriptions/sub_nonexistent_12345" "404"
test_endpoint "User subscriptions returns 200" "GET" "$API_BASE/subscriptions/user/$TEST_USER_ID" "200"
test_endpoint "User subscriptions with filter returns 200" "GET" "$API_BASE/subscriptions/user/$TEST_USER_ID?status=active" "200"
test_endpoint "User subscriptions invalid status returns 4xx" "GET" "$API_BASE/subscriptions/user/$TEST_USER_ID?status=invalid_status" "400" || test_endpoint "User subscriptions invalid status returns 422" "GET" "$API_BASE/subscriptions/user/$TEST_USER_ID?status=invalid_status" "422"

# Subscription creation validation
test_endpoint "Create subscription missing user_id returns 4xx" "POST" "$API_BASE/subscriptions" "400" '{"plan_id": "plan_test"}' || test_endpoint "Create subscription missing user_id returns 422" "POST" "$API_BASE/subscriptions" "422" '{"plan_id": "plan_test"}'
test_endpoint "Create subscription missing plan_id returns 4xx" "POST" "$API_BASE/subscriptions" "400" '{"user_id": "user_test"}' || test_endpoint "Create subscription missing plan_id returns 422" "POST" "$API_BASE/subscriptions" "422" '{"user_id": "user_test"}'

# Status update
test_endpoint "Update non-existent subscription returns 404" "PUT" "$API_BASE/subscriptions/sub_nonexistent/status" "404" '{"status": "canceled"}'

# ============================================
# 6. Usage Recording Tests
# ============================================
echo ""
echo "--- Usage Recording Tests ---"

test_endpoint "Usage records returns 200" "GET" "$API_BASE/usage/records?user_id=$TEST_USER_ID" "200"
test_endpoint "Usage records with filters returns 200" "GET" "$API_BASE/usage/records?user_id=$TEST_USER_ID&limit=10" "200"

# Usage recording validation
test_endpoint "Record usage missing user_id returns 4xx" "POST" "$API_BASE/usage/record" "400" '{"product_id": "prod_test", "usage_amount": 100}' || test_endpoint "Record usage missing user_id returns 422" "POST" "$API_BASE/usage/record" "422" '{"product_id": "prod_test", "usage_amount": 100}'
test_endpoint "Record usage missing product_id returns 4xx" "POST" "$API_BASE/usage/record" "400" '{"user_id": "user_test", "usage_amount": 100}' || test_endpoint "Record usage missing product_id returns 422" "POST" "$API_BASE/usage/record" "422" '{"user_id": "user_test", "usage_amount": 100}'

# ============================================
# 7. Statistics Tests
# ============================================
echo ""
echo "--- Statistics Tests ---"

test_endpoint "Usage statistics returns 200" "GET" "$API_BASE/statistics/usage?user_id=$TEST_USER_ID" "200"
test_endpoint "Service statistics returns 200" "GET" "$API_BASE/statistics/service" "200"

# ============================================
# Summary
# ============================================
echo ""
echo "=============================================="
echo "Smoke Test Summary"
echo "=============================================="
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASS_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some smoke tests failed.${NC}"
    exit 1
fi
