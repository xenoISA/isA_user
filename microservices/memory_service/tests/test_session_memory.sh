#!/bin/bash

# Session Memory Testing Script
# Tests session memory operations (conversation context)

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1/memories"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Generate unique session ID
SESSION_ID="session_$(date +%s)"

# JSON parsing function
json_value() {
    local json="$1"
    local key="$2"

    if command -v jq &> /dev/null; then
        echo "$json" | jq -r ".$key"
    else
        echo "$json" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$key', ''))"
    fi
}

# Pretty print JSON
pretty_json() {
    local json="$1"

    if command -v jq &> /dev/null; then
        echo "$json" | jq '.'
    else
        echo "$json" | python3 -m json.tool 2>/dev/null || echo "$json"
    fi
}

echo "======================================================================"
echo "Session Memory Service Tests"
echo "======================================================================"
echo -e "${YELLOW}Session ID: $SESSION_ID${NC}"
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

# Test 1: Create First Session Memory
print_section "Test 1: Create First Session Memory"
echo "POST ${API_BASE}"

# Create payload using heredoc to avoid escaping issues
CREATE1_PAYLOAD=$(cat <<EOF
{
  "user_id": "test_user_session",
  "memory_type": "session",
  "content": "User: Hello! I need help with my project.",
  "session_id": "$SESSION_ID",
  "interaction_sequence": 1,
  "context": {
    "role": "user",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  },
  "importance_score": 0.5
}
EOF
)
echo "Request Body:"
echo "$CREATE1_PAYLOAD" | pretty_json

CREATE1_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -d "$CREATE1_PAYLOAD")
HTTP_CODE=$(echo "$CREATE1_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE1_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

MEMORY_ID_1=""
if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        MEMORY_ID_1=$(json_value "$RESPONSE_BODY" "memory_id")
        print_result 0 "First session memory created successfully"
        echo -e "${YELLOW}Memory ID: $MEMORY_ID_1${NC}"
    else
        print_result 1 "Creation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to create first session memory"
fi

# Test 2: Create Second Session Memory (Response)
print_section "Test 2: Create Second Session Memory (Response)"
echo "POST ${API_BASE}"

CREATE2_PAYLOAD=$(cat <<EOF
{
  "user_id": "test_user_session",
  "memory_type": "session",
  "content": "Assistant: I'd be happy to help! What kind of project are you working on?",
  "session_id": "$SESSION_ID",
  "interaction_sequence": 2,
  "context": {
    "role": "assistant",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  },
  "importance_score": 0.5
}
EOF
)
echo "Request Body:"
echo "$CREATE2_PAYLOAD" | pretty_json

CREATE2_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -d "$CREATE2_PAYLOAD")
HTTP_CODE=$(echo "$CREATE2_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE2_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Second session memory created successfully"
    else
        print_result 1 "Second creation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to create second session memory"
fi

# Test 3: Create Third Session Memory
print_section "Test 3: Create Third Session Memory"
echo "POST ${API_BASE}"

CREATE3_PAYLOAD=$(cat <<EOF
{
  "user_id": "test_user_session",
  "memory_type": "session",
  "content": "User: It's a web application using Python and FastAPI. I'm having issues with database connections.",
  "session_id": "$SESSION_ID",
  "interaction_sequence": 3,
  "context": {
    "role": "user",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  },
  "importance_score": 0.7
}
EOF
)
echo "Request Body:"
echo "$CREATE3_PAYLOAD" | pretty_json

CREATE3_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -d "$CREATE3_PAYLOAD")
HTTP_CODE=$(echo "$CREATE3_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE3_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Third session memory created successfully"
    else
        print_result 1 "Third creation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to create third session memory"
fi

# Test 4: Get Session Memories
print_section "Test 4: Get All Memories for Session"
echo "GET ${API_BASE}/session/${SESSION_ID}?user_id=test_user_session"

SESSION_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/session/${SESSION_ID}?user_id=test_user_session")
HTTP_CODE=$(echo "$SESSION_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SESSION_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    if [ "$COUNT" -ge 3 ]; then
        print_result 0 "Retrieved session memories (found: $COUNT)"
    else
        print_result 1 "Expected at least 3 session memories, found: $COUNT"
    fi
else
    print_result 1 "Failed to get session memories"
fi

# Test 5: Get Session Context (with AI-enhanced summaries)
print_section "Test 5: Get Session Context"
echo "GET ${API_BASE}/session/${SESSION_ID}/context?user_id=test_user_session&include_summaries=true&max_recent_messages=5"

CONTEXT_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/session/${SESSION_ID}/context?user_id=test_user_session&include_summaries=true&max_recent_messages=5")
HTTP_CODE=$(echo "$CONTEXT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CONTEXT_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_MESSAGES=$(json_value "$RESPONSE_BODY" "total_messages")
    if [ "$TOTAL_MESSAGES" -ge 1 ]; then
        print_result 0 "Session context retrieved successfully (total_messages: $TOTAL_MESSAGES)"
    else
        print_result 1 "Session context returned but no messages found"
    fi
else
    print_result 1 "Failed to get session context"
fi

# Test 6: List All Session Memories for User
print_section "Test 6: List All Session Memories for User"
echo "GET ${API_BASE}?user_id=test_user_session&memory_type=session&limit=50"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_session&memory_type=session&limit=50")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Listed session memories (found: $COUNT)"
else
    print_result 1 "Failed to list session memories"
fi

# Test 7: Update Session Memory
if [ -n "$MEMORY_ID_1" ] && [ "$MEMORY_ID_1" != "null" ]; then
    print_section "Test 7: Update Session Memory"
    echo "PUT ${API_BASE}/session/${MEMORY_ID_1}?user_id=test_user_session"
    UPDATE_PAYLOAD='{
      "importance_score": 0.8,
      "context": {
        "role": "user",
        "marked_important": true
      }
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/session/${MEMORY_ID_1}?user_id=test_user_session" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Session memory updated successfully"
        else
            print_result 1 "Update returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to update session memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Deactivate Session
print_section "Test 8: Deactivate Session"
echo "POST ${API_BASE}/session/${SESSION_ID}/deactivate?user_id=test_user_session"

DEACTIVATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/session/${SESSION_ID}/deactivate?user_id=test_user_session")
HTTP_CODE=$(echo "$DEACTIVATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DEACTIVATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Session deactivated successfully"
    else
        print_result 1 "Deactivation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to deactivate session"
fi

# Test 9: Delete Session Memory
if [ -n "$MEMORY_ID_1" ] && [ "$MEMORY_ID_1" != "null" ]; then
    print_section "Test 9: Delete Session Memory"
    echo "DELETE ${API_BASE}/session/${MEMORY_ID_1}?user_id=test_user_session"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/session/${MEMORY_ID_1}?user_id=test_user_session")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Session memory deleted successfully"
        else
            print_result 1 "Delete returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to delete session memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 9: No memory ID available${NC}"
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
    echo -e "${GREEN}All session memory tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
