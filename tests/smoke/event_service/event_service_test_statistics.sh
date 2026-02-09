#!/bin/bash
# ============================================================================
# Event Service Smoke Test - Statistics Endpoints
# ============================================================================
# Tests statistics and metrics endpoints for the Event Service
# Target: localhost:8230
# Tests: 2 (overall statistics, statistics with user filter)
# ============================================================================

set -e

# ============================================================================
# Configuration
# ============================================================================
BASE_URL="${EVENT_SERVICE_URL:-http://localhost:8230}"
API_BASE="${BASE_URL}/api/v1/events"
SCRIPT_NAME="event_service_test_statistics.sh"
TEST_TS=$(date +%s)
TEST_USER_ID="stats_test_user_${TEST_TS}"

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
    echo -e "${CYAN}  EVENT SERVICE SMOKE TEST - STATISTICS ENDPOINTS${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${YELLOW}Base URL: ${BASE_URL}${NC}"
    echo -e "${YELLOW}API Base: ${API_BASE}${NC}"
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

extract_json_field() {
    local json="$1"
    local field="$2"
    echo "$json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('$field', ''))" 2>/dev/null || echo ""
}

# ============================================================================
# Setup: Create some events to ensure statistics have data
# ============================================================================
echo -e "${YELLOW}Setting up test data for statistics...${NC}"

for i in 1 2 3; do
    SETUP_PAYLOAD=$(cat <<EOF
{
    "event_type": "stats_test.event_${i}",
    "event_source": "backend",
    "event_category": "system",
    "user_id": "${TEST_USER_ID}",
    "data": {"index": ${i}, "test_ts": "${TEST_TS}"}
}
EOF
)
    curl -s -X POST -H "Content-Type: application/json" -d "$SETUP_PAYLOAD" "${API_BASE}/create" > /dev/null 2>&1
done
echo "  Created 3 test events for statistics"
echo ""

# ============================================================================
# Tests
# ============================================================================

print_header

# ---------------------------------------------------------------------------
# Test 1: Get Overall Event Statistics
# ---------------------------------------------------------------------------
print_test "1/2" "Get Overall Event Statistics - GET /api/v1/events/statistics"

echo "  Request: GET ${API_BASE}/statistics"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    "${API_BASE}/statistics" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    # Check for required statistics fields
    HAS_TOTAL=$(echo "$BODY" | grep -c '"total_events"' || echo "0")
    HAS_PENDING=$(echo "$BODY" | grep -c '"pending_events"' || echo "0")
    HAS_PROCESSED=$(echo "$BODY" | grep -c '"processed_events"' || echo "0")
    HAS_FAILED=$(echo "$BODY" | grep -c '"failed_events"' || echo "0")

    echo "  Statistics fields found:"
    echo "    - total_events: $([ "$HAS_TOTAL" -gt 0 ] && echo 'YES' || echo 'NO')"
    echo "    - pending_events: $([ "$HAS_PENDING" -gt 0 ] && echo 'YES' || echo 'NO')"
    echo "    - processed_events: $([ "$HAS_PROCESSED" -gt 0 ] && echo 'YES' || echo 'NO')"
    echo "    - failed_events: $([ "$HAS_FAILED" -gt 0 ] && echo 'YES' || echo 'NO')"

    if [ "$HAS_TOTAL" -gt 0 ] && [ "$HAS_PENDING" -gt 0 ]; then
        TOTAL_EVENTS=$(extract_json_field "$BODY" "total_events")
        PENDING=$(extract_json_field "$BODY" "pending_events")
        PROCESSED=$(extract_json_field "$BODY" "processed_events")
        FAILED_EVENTS=$(extract_json_field "$BODY" "failed_events")

        echo "  Statistics values:"
        echo "    - Total Events: $TOTAL_EVENTS"
        echo "    - Pending: $PENDING"
        echo "    - Processed: $PROCESSED"
        echo "    - Failed: $FAILED_EVENTS"

        test_passed
    else
        test_failed "Response missing required statistics fields"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 2: Get Statistics with User Filter
# ---------------------------------------------------------------------------
print_test "2/2" "Get Statistics with User Filter - GET /api/v1/events/statistics?user_id=..."

echo "  Request: GET ${API_BASE}/statistics?user_id=${TEST_USER_ID}"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    "${API_BASE}/statistics?user_id=${TEST_USER_ID}" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    # Check for total_events field
    if echo "$BODY" | grep -q '"total_events"'; then
        TOTAL_EVENTS=$(extract_json_field "$BODY" "total_events")
        echo "  User-filtered total events: $TOTAL_EVENTS"
        test_passed
    else
        test_failed "Response missing total_events field"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ============================================================================
# Summary
# ============================================================================
print_summary
