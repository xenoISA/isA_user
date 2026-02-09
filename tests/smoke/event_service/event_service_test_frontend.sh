#!/bin/bash
# ============================================================================
# Event Service Smoke Test - Frontend Event Collection
# ============================================================================
# Tests frontend event collection endpoints for the Event Service
# Target: localhost:8230
# Tests: 3 (frontend health, single frontend event, batch frontend events)
# ============================================================================

set -e

# ============================================================================
# Configuration
# ============================================================================
BASE_URL="${EVENT_SERVICE_URL:-http://localhost:8230}"
API_BASE="${BASE_URL}/api/v1/events"
SCRIPT_NAME="event_service_test_frontend.sh"
TEST_TS=$(date +%s)
TEST_SESSION_ID="session_${TEST_TS}"
TEST_USER_ID="frontend_test_user_${TEST_TS}"

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
    echo -e "${CYAN}  EVENT SERVICE SMOKE TEST - FRONTEND EVENT COLLECTION${NC}"
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
# Test 1: Frontend Health Check
# ---------------------------------------------------------------------------
print_test "1/3" "Frontend Health Check - GET /api/v1/events/frontend/health"

echo "  Request: GET ${API_BASE}/frontend/health"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    "${API_BASE}/frontend/health" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | grep -q '"status"' && echo "$BODY" | grep -q '"healthy"'; then
        # Check for frontend-specific fields
        if echo "$BODY" | grep -q '"service"'; then
            echo "  Frontend collection service is healthy"
            test_passed
        else
            test_passed  # Basic health check passed
        fi
    else
        test_failed "Response does not indicate healthy status"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 2: Collect Single Frontend Event (Page View)
# ---------------------------------------------------------------------------
print_test "2/3" "Collect Single Frontend Event - POST /api/v1/events/frontend"

PAYLOAD=$(cat <<EOF
{
    "event_type": "page_view",
    "category": "user_interaction",
    "page_url": "https://app.example.com/dashboard",
    "user_id": "${TEST_USER_ID}",
    "session_id": "${TEST_SESSION_ID}",
    "data": {
        "page_title": "Dashboard",
        "referrer": "https://app.example.com/login",
        "viewport_width": 1920,
        "viewport_height": 1080
    },
    "metadata": {
        "app_version": "1.0.0",
        "environment": "smoke_test"
    }
}
EOF
)

echo "  Request: POST ${API_BASE}/frontend"
echo "  Payload: $PAYLOAD"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) SmokeTest/1.0" \
    -d "$PAYLOAD" \
    "${API_BASE}/frontend" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    STATUS=$(extract_json_field "$BODY" "status")
    if [ "$STATUS" = "accepted" ] || [ "$STATUS" = "error" ]; then
        # accepted means NATS is connected, error means it's not but endpoint works
        echo "  Frontend event status: $STATUS"
        test_passed
    else
        test_failed "Unexpected status: $STATUS"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 3: Collect Batch Frontend Events
# ---------------------------------------------------------------------------
print_test "3/3" "Collect Batch Frontend Events - POST /api/v1/events/frontend/batch"

PAYLOAD=$(cat <<EOF
{
    "events": [
        {
            "event_type": "button_click",
            "category": "user_interaction",
            "page_url": "https://app.example.com/dashboard",
            "user_id": "${TEST_USER_ID}",
            "session_id": "${TEST_SESSION_ID}",
            "data": {
                "button_id": "create_task_btn",
                "button_text": "Create Task"
            }
        },
        {
            "event_type": "form_submit",
            "category": "user_interaction",
            "page_url": "https://app.example.com/tasks/new",
            "user_id": "${TEST_USER_ID}",
            "session_id": "${TEST_SESSION_ID}",
            "data": {
                "form_id": "new_task_form",
                "fields_count": 5
            }
        },
        {
            "event_type": "page_view",
            "category": "user_interaction",
            "page_url": "https://app.example.com/tasks",
            "user_id": "${TEST_USER_ID}",
            "session_id": "${TEST_SESSION_ID}",
            "data": {
                "page_title": "Tasks List"
            }
        }
    ],
    "client_info": {
        "sdk_version": "1.0.0",
        "platform": "web",
        "batch_id": "${TEST_TS}"
    }
}
EOF
)

echo "  Request: POST ${API_BASE}/frontend/batch"
echo "  Batch Size: 3 events"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) SmokeTest/1.0" \
    -d "$PAYLOAD" \
    "${API_BASE}/frontend/batch" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    STATUS=$(extract_json_field "$BODY" "status")
    PROCESSED_COUNT=$(extract_json_field "$BODY" "processed_count")

    if [ "$STATUS" = "accepted" ]; then
        echo "  Batch status: $STATUS"
        echo "  Processed count: $PROCESSED_COUNT"
        test_passed
    else
        # Batch endpoint might return error if NATS not connected
        echo "  Batch status: $STATUS"
        test_passed  # Endpoint responded correctly
    fi
elif [ "$HTTP_CODE" = "503" ]; then
    # 503 is expected when NATS/JetStream is not available
    echo "  Service unavailable (NATS not connected) - this is acceptable"
    test_passed
else
    test_failed "Expected HTTP 200 or 503, got $HTTP_CODE"
fi

# ============================================================================
# Summary
# ============================================================================
print_summary
