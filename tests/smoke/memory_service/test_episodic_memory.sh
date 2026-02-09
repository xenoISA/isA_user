#!/bin/bash

# Episodic Memory Testing Script
# Tests episodic memory extraction and storage capabilities

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

# JSON parsing function (works with or without jq)
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
echo "Episodic Memory Service Tests"
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

# Test 1: Extract Episodic Memory from Dialog
print_section "Test 1: Extract Episodic Memory from Dialog (AI-Powered)"
echo "POST ${API_BASE}/episodic/extract"
EXTRACT_PAYLOAD='{
  "user_id": "test_user_456",
  "dialog_content": "Last Tuesday, I went to the new Italian restaurant downtown with my colleagues after the team meeting. We ordered the seafood pasta and tiramisu. It was a great evening celebrating our project completion.",
  "importance_score": 0.7
}'
echo "Request Body:"
pretty_json "$EXTRACT_PAYLOAD"

EXTRACT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/episodic/extract" \
  -H "Content-Type: application/json" \
  -d "$EXTRACT_PAYLOAD")
HTTP_CODE=$(echo "$EXTRACT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$EXTRACT_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

MEMORY_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        # Extract first memory ID from the array
        if command -v jq &> /dev/null; then
            MEMORY_ID=$(echo "$RESPONSE_BODY" | jq -r '.data.memory_ids[0] // empty')
        else
            MEMORY_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('memory_ids', [None])[0] or '')" 2>/dev/null)
        fi
        print_result 0 "Episodic memory extracted and stored successfully"
        echo -e "${YELLOW}Memory ID: $MEMORY_ID${NC}"
    else
        print_result 1 "Extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract episodic memory"
fi

# Test 2: Get Episodic Memory by ID
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 2: Get Episodic Memory by ID"
    echo "GET ${API_BASE}/episodic/${MEMORY_ID}?user_id=test_user_456"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/episodic/${MEMORY_ID}?user_id=test_user_456")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(json_value "$RESPONSE_BODY" "id")
        if [ "$RETRIEVED_ID" = "$MEMORY_ID" ]; then
            print_result 0 "Episodic memory retrieved successfully"
        else
            print_result 1 "Retrieved memory ID doesn't match"
        fi
    else
        print_result 1 "Failed to retrieve episodic memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Search Episodes by Event Type
print_section "Test 3: Search Episodes by Event Type"
echo "GET ${API_BASE}/episodic/search/event_type?user_id=test_user_456&event_type=celebration&limit=10"

SEARCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/episodic/search/event_type?user_id=test_user_456&event_type=celebration&limit=10")
HTTP_CODE=$(echo "$SEARCH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SEARCH_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Episodic memory search completed (found: $COUNT)"
else
    print_result 1 "Failed to search episodic memories"
fi

# Test 4: List All Episodic Memories
print_section "Test 4: List All Episodic Memories for User"
echo "GET ${API_BASE}?user_id=test_user_456&memory_type=episodic&limit=50"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_456&memory_type=episodic&limit=50")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Listed episodic memories (found: $COUNT)"
else
    print_result 1 "Failed to list episodic memories"
fi

# Test 5: Extract Complex Episode
print_section "Test 5: Extract Complex Episode with Multiple Elements"
echo "POST ${API_BASE}/episodic/extract"
COMPLEX_PAYLOAD='{
  "user_id": "test_user_456",
  "dialog_content": "On my wedding day last summer, July 20th 2024, at the Grand Hotel in Paris, I married my partner Sarah. We had 150 guests, and my best friend Mike gave an amazing speech. The ceremony was in the garden, and we danced until midnight. The weather was perfect.",
  "importance_score": 0.95
}'
echo "Request Body:"
pretty_json "$COMPLEX_PAYLOAD"

COMPLEX_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/episodic/extract" \
  -H "Content-Type: application/json" \
  -d "$COMPLEX_PAYLOAD")
HTTP_CODE=$(echo "$COMPLEX_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$COMPLEX_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Complex episode extracted successfully"
    else
        print_result 1 "Complex extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract complex episode"
fi

# Test 6: Update Episodic Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 6: Update Episodic Memory"
    echo "PUT ${API_BASE}/episodic/${MEMORY_ID}?user_id=test_user_456"
    UPDATE_PAYLOAD='{
      "importance_score": 0.85,
      "confidence": 0.95
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/episodic/${MEMORY_ID}?user_id=test_user_456" \
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
            print_result 0 "Episodic memory updated successfully"
        else
            print_result 1 "Update returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to update episodic memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Delete Episodic Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 7: Delete Episodic Memory"
    echo "DELETE ${API_BASE}/episodic/${MEMORY_ID}?user_id=test_user_456"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/episodic/${MEMORY_ID}?user_id=test_user_456")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Episodic memory deleted successfully"
        else
            print_result 1 "Delete returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to delete episodic memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No memory ID available${NC}"
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
    echo -e "${GREEN}All episodic memory tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
