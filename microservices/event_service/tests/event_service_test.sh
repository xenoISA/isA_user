#!/bin/bash

# Event Service Testing Script
# Tests event creation, querying, statistics, and subscriptions

BASE_URL="http://localhost:8230"
API_BASE="${BASE_URL}/api/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# JSON parsing function (works with or without jq)
json_value() {
    local json="$1"
    local key="$2"

    if command -v jq &> /dev/null; then
        echo "$json" | jq -r ".$key"
    else
        # Fallback to python
        echo "$json" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$key', ''))"
    fi
}

# Pretty print JSON (works with or without jq)
pretty_json() {
    local json="$1"

    if command -v jq &> /dev/null; then
        echo "$json" | jq '.'
    else
        echo "$json" | python3 -m json.tool 2>/dev/null || echo "$json"
    fi
}

echo "======================================================================"
echo "Event Service Tests"
echo "======================================================================"
echo ""

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Function to print section header
print_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

# Test 1: Health Check
print_section "Test 1: Health Check"
echo "GET ${BASE_URL}/health"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Health check successful"
else
    print_result 1 "Health check failed"
fi

# Test 2: Create Event
print_section "Test 2: Create Event"
echo "POST ${API_BASE}/events/create"
CREATE_EVENT_PAYLOAD='{
  "event_type": "user_login",
  "event_source": "backend",
  "event_category": "security",
  "user_id": "test_user_123",
  "data": {
    "ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0",
    "timestamp": "2025-10-14T12:00:00Z"
  },
  "metadata": {
    "service": "auth_service",
    "version": "1.0.0"
  }
}'
echo "Request Body:"
pretty_json "$CREATE_EVENT_PAYLOAD"

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/events/create" \
  -H "Content-Type: application/json" \
  -d "$CREATE_EVENT_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

EVENT_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    EVENT_ID=$(json_value "$RESPONSE_BODY" "event_id")
    if [ -n "$EVENT_ID" ] && [ "$EVENT_ID" != "null" ]; then
        print_result 0 "Event created successfully"
        echo -e "${YELLOW}Event ID: $EVENT_ID${NC}"
    else
        print_result 1 "Event creation returned success but no event_id"
    fi
else
    print_result 1 "Failed to create event"
fi

# Test 3: Get Event by ID
if [ -n "$EVENT_ID" ] && [ "$EVENT_ID" != "null" ]; then
    print_section "Test 3: Get Event by ID"
    echo "GET ${API_BASE}/events/${EVENT_ID}"
    
    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/events/${EVENT_ID}")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(json_value "$RESPONSE_BODY" "event_id")
        if [ "$RETRIEVED_ID" = "$EVENT_ID" ]; then
            print_result 0 "Event retrieved successfully"
        else
            print_result 1 "Event ID mismatch"
        fi
    else
        print_result 1 "Failed to retrieve event"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No event ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: Create Batch Events
print_section "Test 4: Create Batch Events"
echo "POST ${API_BASE}/events/batch"
BATCH_PAYLOAD='[
  {
    "event_type": "page_view",
    "event_source": "frontend",
    "event_category": "page_view",
    "user_id": "test_user_123",
    "data": {"page": "/dashboard", "duration": 5000}
  },
  {
    "event_type": "button_click",
    "event_source": "frontend",
    "event_category": "click",
    "user_id": "test_user_123",
    "data": {"button_id": "save_settings", "page": "/settings"}
  }
]'
echo "Request Body:"
pretty_json "$BATCH_PAYLOAD"

BATCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/events/batch" \
  -H "Content-Type: application/json" \
  -d "$BATCH_PAYLOAD")
HTTP_CODE=$(echo "$BATCH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$BATCH_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Batch events created successfully"
else
    print_result 1 "Failed to create batch events"
fi

# Test 5: Query Events
print_section "Test 5: Query Events"
echo "POST ${API_BASE}/events/query"
QUERY_PAYLOAD='{
  "user_id": "test_user_123",
  "limit": 10,
  "offset": 0
}'
echo "Request Body:"
pretty_json "$QUERY_PAYLOAD"

QUERY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/events/query" \
  -H "Content-Type: application/json" \
  -d "$QUERY_PAYLOAD")
HTTP_CODE=$(echo "$QUERY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$QUERY_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL=$(json_value "$RESPONSE_BODY" "total")
    if [ -n "$TOTAL" ] && [ "$TOTAL" != "null" ]; then
        print_result 0 "Events queried successfully (Total: $TOTAL)"
    else
        print_result 1 "Query returned success but no total count"
    fi
else
    print_result 1 "Failed to query events"
fi

# Test 6: Get Event Statistics
print_section "Test 6: Get Event Statistics"
echo "GET ${API_BASE}/events/statistics?user_id=test_user_123"

STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/events/statistics?user_id=test_user_123")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Statistics retrieved successfully"
else
    print_result 1 "Failed to retrieve statistics"
fi

# Test 7: Create Event Subscription
print_section "Test 7: Create Event Subscription"
echo "POST ${API_BASE}/events/subscriptions"
TIMESTAMP=$(date +%s)
SUB_PAYLOAD="{
  \"subscription_id\": \"test_sub_${TIMESTAMP}\",
  \"event_types\": [\"user_login\", \"user_logout\"],
  \"endpoint\": \"http://localhost:9000/webhooks/events\",
  \"enabled\": true,
  \"filters\": {
    \"user_id\": \"test_user_123\"
  }
}"
echo "Request Body:"
pretty_json "$SUB_PAYLOAD"

SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/events/subscriptions" \
  -H "Content-Type: application/json" \
  -d "$SUB_PAYLOAD")
HTTP_CODE=$(echo "$SUB_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SUB_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

SUB_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    SUB_ID=$(json_value "$RESPONSE_BODY" "subscription_id")
    if [ -n "$SUB_ID" ] && [ "$SUB_ID" != "null" ]; then
        print_result 0 "Subscription created successfully"
    else
        print_result 1 "Subscription creation returned success but no subscription_id"
    fi
else
    print_result 1 "Failed to create subscription"
fi

# Test 8: List Subscriptions
print_section "Test 8: List Subscriptions"
echo "GET ${API_BASE}/events/subscriptions"

LIST_SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/events/subscriptions")
HTTP_CODE=$(echo "$LIST_SUB_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_SUB_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Subscriptions listed successfully"
else
    print_result 1 "Failed to list subscriptions"
fi

# Test 9: Frontend Event Collection
print_section "Test 9: Frontend Event Collection"
echo "POST ${API_BASE}/frontend/events"
FRONTEND_EVENT='{
  "event_type": "page_view",
  "category": "page_view",
  "page_url": "https://example.com/dashboard",
  "user_id": "test_user_123",
  "session_id": "sess_12345",
  "data": {
    "page_title": "Dashboard",
    "load_time": 250
  },
  "metadata": {
    "browser": "Chrome",
    "os": "MacOS"
  }
}'
echo "Request Body:"
pretty_json "$FRONTEND_EVENT"

FRONTEND_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/frontend/events" \
  -H "Content-Type: application/json" \
  -d "$FRONTEND_EVENT")
HTTP_CODE=$(echo "$FRONTEND_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$FRONTEND_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    STATUS=$(json_value "$RESPONSE_BODY" "status")
    if [ "$STATUS" = "accepted" ]; then
        print_result 0 "Frontend event collected successfully"
    elif [ "$STATUS" = "error" ]; then
        MESSAGE=$(json_value "$RESPONSE_BODY" "message")
        if [[ "$MESSAGE" == *"not available"* ]]; then
            print_result 0 "Frontend event endpoint working (NATS not connected)"
        else
            print_result 1 "Frontend event collection returned error: $MESSAGE"
        fi
    else
        print_result 1 "Frontend event collection returned unexpected status: $STATUS"
    fi
else
    print_result 1 "Failed to collect frontend event"
fi

# Test 10: Frontend Health Check
print_section "Test 10: Frontend Health Check"
echo "GET ${API_BASE}/frontend/health"

FRONTEND_HEALTH=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/frontend/health")
HTTP_CODE=$(echo "$FRONTEND_HEALTH" | tail -n1)
RESPONSE_BODY=$(echo "$FRONTEND_HEALTH" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Frontend health check successful"
else
    print_result 1 "Frontend health check failed"
fi

# Summary
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total: $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi

