#!/bin/bash
# ============================================================================
# Event Service Smoke Test - Event Creation
# ============================================================================
# Tests event creation endpoints for the Event Service
# Target: localhost:8230
# Tests: 4 (single event, batch events, with metadata, get event)
# ============================================================================

set -e

# ============================================================================
# Configuration
# ============================================================================
BASE_URL="${EVENT_SERVICE_URL:-http://localhost:8230}"
API_BASE="${BASE_URL}/api/v1/events"
SCRIPT_NAME="event_service_test_create.sh"
TEST_TS=$(date +%s)

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

# Stored event IDs for later tests
CREATED_EVENT_ID=""

# ============================================================================
# Helper Functions
# ============================================================================
print_header() {
    echo ""
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN}  EVENT SERVICE SMOKE TEST - EVENT CREATION${NC}"
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
# Tests
# ============================================================================

print_header

# ---------------------------------------------------------------------------
# Test 1: Create Single Event
# ---------------------------------------------------------------------------
print_test "1/4" "Create Single Event - POST /api/v1/events/create"

PAYLOAD=$(cat <<EOF
{
    "event_type": "smoke_test.event_created",
    "event_source": "backend",
    "event_category": "system",
    "user_id": "smoke_test_user_${TEST_TS}",
    "data": {
        "test_id": "${TEST_TS}",
        "message": "Smoke test event creation"
    },
    "metadata": {
        "test_suite": "smoke_tests",
        "script": "${SCRIPT_NAME}"
    }
}
EOF
)

echo "  Request: POST ${API_BASE}/create"
echo "  Payload: $PAYLOAD"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "${API_BASE}/create" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    CREATED_EVENT_ID=$(extract_json_field "$BODY" "event_id")
    if [ -n "$CREATED_EVENT_ID" ] && [ "$CREATED_EVENT_ID" != "null" ]; then
        echo "  Created Event ID: $CREATED_EVENT_ID"
        test_passed
    else
        test_failed "Response does not contain event_id"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 2: Create Event with All Event Sources
# ---------------------------------------------------------------------------
print_test "2/4" "Create Event with Frontend Source - POST /api/v1/events/create"

PAYLOAD=$(cat <<EOF
{
    "event_type": "smoke_test.frontend_event",
    "event_source": "frontend",
    "event_category": "user_action",
    "user_id": "smoke_test_user_${TEST_TS}",
    "data": {
        "action": "button_click",
        "element_id": "submit_button",
        "page": "/dashboard"
    },
    "context": {
        "browser": "Chrome",
        "os": "macOS"
    }
}
EOF
)

echo "  Request: POST ${API_BASE}/create"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "${API_BASE}/create" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    EVENT_SOURCE=$(extract_json_field "$BODY" "event_source")
    if [ "$EVENT_SOURCE" = "frontend" ]; then
        test_passed
    else
        test_failed "Event source should be 'frontend', got '$EVENT_SOURCE'"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 3: Create Batch Events
# ---------------------------------------------------------------------------
print_test "3/4" "Create Batch Events - POST /api/v1/events/batch"

PAYLOAD=$(cat <<EOF
[
    {
        "event_type": "smoke_test.batch_event_1",
        "event_source": "backend",
        "event_category": "system",
        "user_id": "smoke_test_user_${TEST_TS}",
        "data": {"batch_index": 1}
    },
    {
        "event_type": "smoke_test.batch_event_2",
        "event_source": "backend",
        "event_category": "system",
        "user_id": "smoke_test_user_${TEST_TS}",
        "data": {"batch_index": 2}
    },
    {
        "event_type": "smoke_test.batch_event_3",
        "event_source": "backend",
        "event_category": "system",
        "user_id": "smoke_test_user_${TEST_TS}",
        "data": {"batch_index": 3}
    }
]
EOF
)

echo "  Request: POST ${API_BASE}/batch"
echo "  Batch Size: 3 events"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "${API_BASE}/batch" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response (truncated): ${BODY:0:300}..."

if [ "$HTTP_CODE" = "200" ]; then
    # Check if response is an array with 3 elements
    COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    if [ "$COUNT" = "3" ]; then
        echo "  Created $COUNT events in batch"
        test_passed
    else
        test_failed "Expected 3 events in response, got $COUNT"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 4: Get Created Event by ID
# ---------------------------------------------------------------------------
print_test "4/4" "Get Event by ID - GET /api/v1/events/{event_id}"

if [ -z "$CREATED_EVENT_ID" ] || [ "$CREATED_EVENT_ID" = "null" ]; then
    echo "  Skipping: No event ID from previous test"
    test_failed "No event ID available from test 1"
else
    echo "  Request: GET ${API_BASE}/${CREATED_EVENT_ID}"

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        "${API_BASE}/${CREATED_EVENT_ID}" 2>/dev/null)

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    echo "  HTTP Status: $HTTP_CODE"
    echo "  Response: $BODY"

    if [ "$HTTP_CODE" = "200" ]; then
        RETURNED_ID=$(extract_json_field "$BODY" "event_id")
        if [ "$RETURNED_ID" = "$CREATED_EVENT_ID" ]; then
            test_passed
        else
            test_failed "Returned event_id '$RETURNED_ID' does not match '$CREATED_EVENT_ID'"
        fi
    else
        test_failed "Expected HTTP 200, got $HTTP_CODE"
    fi
fi

# ============================================================================
# Summary
# ============================================================================
print_summary
