#!/bin/bash

# Working Memory Testing Script
# Tests working memory operations (short-term, temporary memory)

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/memories"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

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
echo "Working Memory Service Tests"
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

# Test 1: Create Working Memory
print_section "Test 1: Create Working Memory"
echo "POST ${API_BASE}"
CREATE_PAYLOAD='{
  "user_id": "test_user_xyz",
  "memory_type": "working",
  "content": "Currently working on quarterly report. Need to compile data from marketing, sales, and finance departments. Deadline is Friday.",
  "context": {
    "task": "quarterly_report",
    "priority": 8
  },
  "importance_score": 0.7,
  "ttl_minutes": 120
}'
echo "Request Body:"
pretty_json "$CREATE_PAYLOAD"

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

MEMORY_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        MEMORY_ID=$(json_value "$RESPONSE_BODY" "memory_id")
        print_result 0 "Working memory created successfully"
        echo -e "${YELLOW}Memory ID: $MEMORY_ID${NC}"
    else
        print_result 1 "Creation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to create working memory"
fi

# Test 2: Get Working Memory by ID
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 2: Get Working Memory by ID"
    echo "GET ${API_BASE}/working/${MEMORY_ID}?user_id=test_user_xyz"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/working/${MEMORY_ID}?user_id=test_user_xyz")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(json_value "$RESPONSE_BODY" "id")
        if [ "$RETRIEVED_ID" = "$MEMORY_ID" ]; then
            print_result 0 "Working memory retrieved successfully"
        else
            print_result 1 "Retrieved memory ID doesn't match"
        fi
    else
        print_result 1 "Failed to retrieve working memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Get Active Working Memories
print_section "Test 3: Get Active Working Memories"
echo "GET ${API_BASE}/working/active?user_id=test_user_xyz"

ACTIVE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/working/active?user_id=test_user_xyz")
HTTP_CODE=$(echo "$ACTIVE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$ACTIVE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Retrieved active working memories (found: $COUNT)"
else
    print_result 1 "Failed to get active working memories"
fi

# Test 4: Create Multiple Working Memories
print_section "Test 4: Create Multiple Working Memories"
echo "POST ${API_BASE}"
MULTI_PAYLOAD='{
  "user_id": "test_user_xyz",
  "memory_type": "working",
  "content": "Pending code review for PR #456. Waiting for feedback from senior developer.",
  "context": {
    "task": "code_review",
    "priority": 5
  },
  "importance_score": 0.6,
  "ttl_minutes": 60
}'
echo "Request Body:"
pretty_json "$MULTI_PAYLOAD"

MULTI_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -d "$MULTI_PAYLOAD")
HTTP_CODE=$(echo "$MULTI_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$MULTI_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Second working memory created successfully"
    else
        print_result 1 "Second creation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to create second working memory"
fi

# Test 5: List All Working Memories
print_section "Test 5: List All Working Memories for User"
echo "GET ${API_BASE}?user_id=test_user_xyz&memory_type=working&limit=50"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_xyz&memory_type=working&limit=50")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Listed working memories (found: $COUNT)"
else
    print_result 1 "Failed to list working memories"
fi

# Test 6: Update Working Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 6: Update Working Memory"
    echo "PUT ${API_BASE}/working/${MEMORY_ID}?user_id=test_user_xyz"
    UPDATE_PAYLOAD='{
      "importance_score": 0.9,
      "context": {
        "task": "quarterly_report",
        "priority": 10,
        "status": "in_progress"
      }
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/working/${MEMORY_ID}?user_id=test_user_xyz" \
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
            print_result 0 "Working memory updated successfully"
        else
            print_result 1 "Update returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to update working memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Cleanup Expired Memories
print_section "Test 7: Cleanup Expired Working Memories"
echo "POST ${API_BASE}/working/cleanup?user_id=test_user_xyz"

CLEANUP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/working/cleanup?user_id=test_user_xyz")
HTTP_CODE=$(echo "$CLEANUP_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CLEANUP_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Expired memories cleaned up successfully"
    else
        print_result 1 "Cleanup returned 200 but success=false"
    fi
else
    print_result 1 "Failed to cleanup expired memories"
fi

# Test 8: Delete Working Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 8: Delete Working Memory"
    echo "DELETE ${API_BASE}/working/${MEMORY_ID}?user_id=test_user_xyz"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/working/${MEMORY_ID}?user_id=test_user_xyz")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Working memory deleted successfully"
        else
            print_result 1 "Delete returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to delete working memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 8: No memory ID available${NC}"
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
    echo -e "${GREEN}All working memory tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
