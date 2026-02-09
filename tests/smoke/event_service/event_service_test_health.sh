#!/bin/bash
# ============================================================================
# Event Service Smoke Test - Health Endpoints
# ============================================================================
# Tests health check endpoints for the Event Service
# Target: localhost:8230
# Tests: 3 (health check, frontend health, service readiness)
# ============================================================================

set -e

# ============================================================================
# Configuration
# ============================================================================
BASE_URL="${EVENT_SERVICE_URL:-http://localhost:8230}"
SCRIPT_NAME="event_service_test_health.sh"

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# Test Counters
# ============================================================================
PASSED=0
FAILED=0
TOTAL=0

# ============================================================================
# Helper Functions
# ============================================================================
print_header() {
    echo ""
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN}  EVENT SERVICE SMOKE TEST - HEALTH ENDPOINTS${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${YELLOW}Base URL: ${BASE_URL}${NC}"
    echo ""
}

print_test() {
    echo -e "${YELLOW}[$1] $2${NC}"
}

test_passed() {
    PASSED=$((PASSED + 1))
    TOTAL=$((TOTAL + 1))
    echo -e "${GREEN}  PASSED${NC}"
}

test_failed() {
    FAILED=$((FAILED + 1))
    TOTAL=$((TOTAL + 1))
    echo -e "${RED}  FAILED: $1${NC}"
}

print_summary() {
    echo ""
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN}  TEST SUMMARY${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "Total Tests: ${TOTAL}"
    echo -e "${GREEN}Passed: ${PASSED}${NC}"
    echo -e "${RED}Failed: ${FAILED}${NC}"
    echo ""
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}ALL TESTS PASSED${NC}"
        exit 0
    else
        echo -e "${RED}SOME TESTS FAILED${NC}"
        exit 1
    fi
}

# ============================================================================
# Tests
# ============================================================================

print_header

# ---------------------------------------------------------------------------
# Test 1: Main Health Check Endpoint
# ---------------------------------------------------------------------------
print_test "1/3" "Main Health Check - GET /health"

RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | grep -q '"status"' && echo "$BODY" | grep -q '"healthy"'; then
        test_passed
    else
        test_failed "Response does not contain expected status:healthy"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 2: Frontend Event Collection Health Check
# ---------------------------------------------------------------------------
print_test "2/3" "Frontend Health Check - GET /api/v1/events/frontend/health"

RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/api/v1/events/frontend/health" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | grep -q '"status"' && echo "$BODY" | grep -q '"healthy"'; then
        test_passed
    else
        test_failed "Response does not contain expected status:healthy"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 3: Service Version and Metadata Verification
# ---------------------------------------------------------------------------
print_test "3/3" "Health Response Contains Service Metadata"

RESPONSE=$(curl -s "${BASE_URL}/health" 2>/dev/null)

echo "  Checking for service name..."
if echo "$RESPONSE" | grep -q '"service"'; then
    echo "  Service name present: YES"

    # Check for version
    if echo "$RESPONSE" | grep -q '"version"'; then
        echo "  Version present: YES"

        # Check for timestamp
        if echo "$RESPONSE" | grep -q '"timestamp"'; then
            echo "  Timestamp present: YES"
            test_passed
        else
            test_failed "Missing timestamp in health response"
        fi
    else
        test_failed "Missing version in health response"
    fi
else
    test_failed "Missing service name in health response"
fi

# ============================================================================
# Summary
# ============================================================================
print_summary
