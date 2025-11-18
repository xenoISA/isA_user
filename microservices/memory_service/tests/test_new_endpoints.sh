#!/bin/bash

# Test script for newly implemented memory service endpoints
# Tests: store_working_memory, store_session_message, search_concepts_by_category, get_session_context

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BASE_URL="http://localhost"
USER_ID="test_user_$(date +%s)"
SESSION_ID="test_session_$(date +%s)"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo ""
echo "======================================================================"
echo -e "${BLUE}Testing New Memory Service Endpoints${NC}"
echo "======================================================================"
echo ""
echo "Base URL: $BASE_URL"
echo "User ID: $USER_ID"
echo "Session ID: $SESSION_ID"
echo ""

# Function to run a test
run_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"

    ((TOTAL_TESTS++))

    echo -e "${YELLOW}TEST $TOTAL_TESTS: $test_name${NC}"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    # Split response and status code
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Status: $http_code"

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED_TESTS++))
        echo "Response: $body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED_TESTS++))
        echo "Response: $body"
    fi

    echo ""
}


# Test 2: Store Working Memory
echo "----------------------------------------"
run_test "Store Working Memory" "POST" "/memories/working/store" \
'{
    "user_id": "'"$USER_ID"'",
    "dialog_content": "Remember to review the quarterly report by Friday",
    "ttl_seconds": 3600,
    "importance_score": 0.8
}'

# Test 3: Store Session Message (first message)
echo "----------------------------------------"
run_test "Store Session Message (Message 1)" "POST" "/memories/session/store" \
'{
    "user_id": "'"$USER_ID"'",
    "session_id": "'"$SESSION_ID"'",
    "message_content": "Hello, I need help with Python programming",
    "message_type": "human",
    "role": "user"
}'

# Test 4: Store Session Message (second message)
echo "----------------------------------------"
run_test "Store Session Message (Message 2)" "POST" "/memories/session/store" \
'{
    "user_id": "'"$USER_ID"'",
    "session_id": "'"$SESSION_ID"'",
    "message_content": "I can help you with Python. What specific topic do you need assistance with?",
    "message_type": "ai",
    "role": "assistant"
}'

# Test 5: Get Session Context
echo "----------------------------------------"
run_test "Get Session Context" "GET" "/memories/session/$SESSION_ID/context?user_id=$USER_ID&include_summaries=true&max_recent_messages=5" ""

# Test 6: Store Semantic Memory (for category search test)
echo "----------------------------------------"
run_test "Store Semantic Memory" "POST" "/memories/semantic/extract" \
'{
    "user_id": "'"$USER_ID"'",
    "dialog_content": "Machine learning is a branch of artificial intelligence that focuses on building applications that learn from data and improve their accuracy over time without being programmed to do so.",
    "importance_score": 0.9
}'

# Wait a moment for semantic extraction to complete
sleep 2

# Test 7: Search Semantic Concepts by Category
echo "----------------------------------------"
run_test "Search Concepts by Category (technology)" "GET" "/memories/semantic/search/category?user_id=$USER_ID&category=technology&limit=10" ""

# Test 8: Universal Search - All Memory Types
echo "----------------------------------------"
run_test "Universal Search (All Types)" "GET" "/memories/search?user_id=$USER_ID&query=help&limit=5" ""

# Test 9: Universal Search - Specific Types
echo "----------------------------------------"
run_test "Universal Search (Factual,Semantic)" "GET" "/memories/search?user_id=$USER_ID&query=python&memory_types=factual,semantic&limit=5" ""

# Test 10: Get Active Working Memories
echo "----------------------------------------"
run_test "Get Active Working Memories" "GET" "/memories/working/active?user_id=$USER_ID" ""

# Print Summary
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    exit 1
fi
