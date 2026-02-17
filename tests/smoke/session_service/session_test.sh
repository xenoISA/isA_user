#!/bin/bash

# Session Service Testing Script
# Tests session management, messages, and memory operations

BASE_URL="http://localhost"
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

# Test data
TEST_USER_ID="test_user_$(date +%s)"
SESSION_ID=""
MESSAGE_ID=""
MEMORY_ID=""

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
echo "Session Service Tests"
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

# Test 1: Create Session
print_section "Test 1: Create Session"
echo "POST ${API_BASE}/sessions"
CREATE_SESSION_PAYLOAD=$(cat <<EOF
{
  "user_id": "${TEST_USER_ID}",
  "conversation_data": {
    "topic": "session_service_testing",
    "context": "Testing session creation endpoint"
  },
  "metadata": {
    "test_type": "integration",
    "created_by": "test_script"
  }
}
EOF
)
echo "Request Body:"
pretty_json "$CREATE_SESSION_PAYLOAD"

SESSION_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/sessions" \
  -H "Content-Type: application/json" \
  -d "$CREATE_SESSION_PAYLOAD")
HTTP_CODE=$(echo "$SESSION_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SESSION_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SESSION_ID=$(json_value "$RESPONSE_BODY" "session_id")
    if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
        print_result 0 "Session created successfully"
        echo -e "${YELLOW}Session ID: $SESSION_ID${NC}"
    else
        print_result 1 "Session creation returned 200 but no session_id found"
    fi
else
    print_result 1 "Failed to create session"
fi

# Test 2: Get Session
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    print_section "Test 2: Get Session"
    echo "GET ${API_BASE}/sessions/${SESSION_ID}"

    GET_SESSION_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/sessions/${SESSION_ID}?user_id=${TEST_USER_ID}")
    HTTP_CODE=$(echo "$GET_SESSION_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_SESSION_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_SESSION_ID=$(json_value "$RESPONSE_BODY" "session_id")
        if [ "$RETRIEVED_SESSION_ID" = "$SESSION_ID" ]; then
            print_result 0 "Session retrieved successfully"
        else
            print_result 1 "Retrieved session ID does not match"
        fi
    else
        print_result 1 "Failed to retrieve session"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No session available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Add User Message
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    print_section "Test 3: Add User Message"
    echo "POST ${API_BASE}/sessions/${SESSION_ID}/messages"

    ADD_MESSAGE_PAYLOAD=$(cat <<EOF
{
  "role": "user",
  "content": "Hello! This is a test message from the user.",
  "message_type": "chat",
  "metadata": {
    "test": true,
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  },
  "tokens_used": 10,
  "cost_usd": 0.0001
}
EOF
)
    echo "Request Body:"
    pretty_json "$ADD_MESSAGE_PAYLOAD"

    MESSAGE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/sessions/${SESSION_ID}/messages?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$ADD_MESSAGE_PAYLOAD")
    HTTP_CODE=$(echo "$MESSAGE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$MESSAGE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        MESSAGE_ID=$(json_value "$RESPONSE_BODY" "message_id")
        print_result 0 "User message added successfully"
        echo -e "${YELLOW}Message ID: $MESSAGE_ID${NC}"
    else
        print_result 1 "Failed to add user message"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No session available${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: Add Assistant Message
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    print_section "Test 4: Add Assistant Message"
    echo "POST ${API_BASE}/sessions/${SESSION_ID}/messages"

    ASSISTANT_MESSAGE_PAYLOAD=$(cat <<EOF
{
  "role": "assistant",
  "content": "Hello! This is a test response from the assistant. How can I help you today?",
  "message_type": "chat",
  "metadata": {
    "model": "test-model",
    "temperature": 0.7
  },
  "tokens_used": 15,
  "cost_usd": 0.00015
}
EOF
)
    echo "Request Body:"
    pretty_json "$ASSISTANT_MESSAGE_PAYLOAD"

    ASSISTANT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/sessions/${SESSION_ID}/messages?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$ASSISTANT_MESSAGE_PAYLOAD")
    HTTP_CODE=$(echo "$ASSISTANT_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$ASSISTANT_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Assistant message added successfully"
    else
        print_result 1 "Failed to add assistant message"
    fi
else
    echo -e "${YELLOW}Skipping Test 4: No session available${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: Get Session Messages
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    print_section "Test 5: Get Session Messages"
    echo "GET ${API_BASE}/sessions/${SESSION_ID}/messages"

    MESSAGES_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/sessions/${SESSION_ID}/messages?user_id=${TEST_USER_ID}&page=1&page_size=100")
    HTTP_CODE=$(echo "$MESSAGES_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$MESSAGES_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        MESSAGE_COUNT=$(json_value "$RESPONSE_BODY" "total")
        print_result 0 "Session messages retrieved successfully"
        echo -e "${YELLOW}Message Count: $MESSAGE_COUNT${NC}"
    else
        print_result 1 "Failed to retrieve session messages"
    fi
else
    echo -e "${YELLOW}Skipping Test 5: No session available${NC}"
    ((TESTS_FAILED++))
fi

# Note: Memory tests (Test 8 & 9) removed - memory is handled by memory_service

# Test 6: Update Session
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    print_section "Test 6: Update Session"
    echo "PUT ${API_BASE}/sessions/${SESSION_ID}"

    UPDATE_SESSION_PAYLOAD=$(cat <<EOF
{
  "status": "completed",
  "metadata": {
    "completion_reason": "test_completed",
    "final_message_count": 2
  }
}
EOF
)
    echo "Request Body:"
    pretty_json "$UPDATE_SESSION_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/sessions/${SESSION_ID}?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_SESSION_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        STATUS=$(json_value "$RESPONSE_BODY" "status")
        if [ "$STATUS" = "completed" ]; then
            print_result 0 "Session updated successfully"
        else
            print_result 1 "Session status not updated correctly"
        fi
    else
        print_result 1 "Failed to update session"
    fi
else
    echo -e "${YELLOW}Skipping Test 10: No session available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Get Session Summary
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    print_section "Test 9: Get Session Summary"
    echo "GET ${API_BASE}/sessions/${SESSION_ID}/summary"

    SUMMARY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/sessions/${SESSION_ID}/summary?user_id=${TEST_USER_ID}")
    HTTP_CODE=$(echo "$SUMMARY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$SUMMARY_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        MESSAGE_COUNT=$(json_value "$RESPONSE_BODY" "message_count")
        HAS_MEMORY=$(json_value "$RESPONSE_BODY" "has_memory")
        print_result 0 "Session summary retrieved successfully"
        echo -e "${YELLOW}Message Count: $MESSAGE_COUNT${NC}"
        echo -e "${YELLOW}Has Memory: $HAS_MEMORY${NC}"
    else
        print_result 1 "Failed to retrieve session summary"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No session available${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Get User Sessions
print_section "Test 10: Get User Sessions"
echo "GET ${API_BASE}/sessions?user_id=${TEST_USER_ID}"

USER_SESSIONS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/sessions?user_id=${TEST_USER_ID}&active_only=false&page=1&page_size=50")
HTTP_CODE=$(echo "$USER_SESSIONS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_SESSIONS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_SESSIONS=$(json_value "$RESPONSE_BODY" "total")
    print_result 0 "User sessions retrieved successfully"
    echo -e "${YELLOW}Total Sessions: $TOTAL_SESSIONS${NC}"
else
    print_result 1 "Failed to retrieve user sessions"
fi

# Test 9: Get Service Stats
print_section "Test 7: Get Service Statistics"
echo "GET ${API_BASE}/sessions/stats"

STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/sessions/stats")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service statistics retrieved successfully"
else
    print_result 1 "Failed to retrieve service statistics"
fi

# Test 10: End Session
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    print_section "Test 8: End Session"
    echo "DELETE ${API_BASE}/sessions/${SESSION_ID}"

    END_SESSION_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/sessions/${SESSION_ID}?user_id=${TEST_USER_ID}")
    HTTP_CODE=$(echo "$END_SESSION_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$END_SESSION_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Session ended successfully"
    else
        print_result 1 "Failed to end session"
    fi
else
    echo -e "${YELLOW}Skipping Test 10: No session available${NC}"
    ((TESTS_FAILED++))
fi

# Test 11: Verify Session is Ended
if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
    print_section "Test 9: Verify Session is Ended"
    echo "GET ${API_BASE}/sessions/${SESSION_ID}"

    VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/sessions/${SESSION_ID}?user_id=${TEST_USER_ID}")
    HTTP_CODE=$(echo "$VERIFY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$VERIFY_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        STATUS=$(json_value "$RESPONSE_BODY" "status")
        IS_ACTIVE=$(json_value "$RESPONSE_BODY" "is_active")
        if [ "$STATUS" = "ended" ] && [ "$IS_ACTIVE" = "false" ]; then
            print_result 0 "Session verified as ended"
        else
            print_result 1 "Session not properly ended"
        fi
    else
        print_result 1 "Failed to verify session status"
    fi
else
    echo -e "${YELLOW}Skipping Test 11: No session available${NC}"
    ((TESTS_FAILED++))
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
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
