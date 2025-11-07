#!/bin/bash

# Factual Memory Testing Script
# Tests factual memory extraction and storage capabilities

BASE_URL="http://localhost:8223"
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
echo "Factual Memory Service Tests"
echo "======================================================================"
echo ""

# Cleanup: Delete existing test data for test_user_123
echo -e "${YELLOW}Cleaning up existing test data for test_user_123...${NC}"
CLEANUP_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_123&memory_type=factual&limit=100")
CLEANUP_HTTP_CODE=$(echo "$CLEANUP_RESPONSE" | tail -n1)
CLEANUP_BODY=$(echo "$CLEANUP_RESPONSE" | sed '$d')

if [ "$CLEANUP_HTTP_CODE" = "200" ]; then
    # Extract memory IDs and delete them
    if command -v jq &> /dev/null; then
        MEMORY_IDS=$(echo "$CLEANUP_BODY" | jq -r '.memories[].id')
    else
        MEMORY_IDS=$(echo "$CLEANUP_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('\n'.join([m['id'] for m in data.get('memories', [])]))" 2>/dev/null)
    fi

    DELETED_COUNT=0
    for MID in $MEMORY_IDS; do
        if [ -n "$MID" ] && [ "$MID" != "null" ]; then
            DELETE_RESULT=$(curl -s -X DELETE "${API_BASE}/factual/${MID}?user_id=test_user_123" -w "%{http_code}")
            if [[ "$DELETE_RESULT" == *"200" ]]; then
                ((DELETED_COUNT++))
            fi
        fi
    done
    echo -e "${GREEN}Deleted $DELETED_COUNT existing test memories${NC}"
else
    echo -e "${YELLOW}Could not retrieve existing memories (HTTP $CLEANUP_HTTP_CODE)${NC}"
fi
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

# Test 2: Extract Factual Memory from Dialog
print_section "Test 2: Extract Factual Memory from Dialog (AI-Powered)"
echo "POST ${API_BASE}/factual/extract"
EXTRACT_PAYLOAD='{
  "user_id": "test_user_123",
  "dialog_content": "My name is John Smith and I work as a software engineer at TechCorp. I have been working there for 5 years. My favorite programming language is Python and I specialize in machine learning.",
  "importance_score": 0.8
}'
echo "Request Body:"
pretty_json "$EXTRACT_PAYLOAD"

EXTRACT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/factual/extract" \
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
        print_result 0 "Factual memory extracted and stored successfully"
        echo -e "${YELLOW}Memory ID: $MEMORY_ID${NC}"
    else
        print_result 1 "Extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract factual memory"
fi

# Test 3: Get Factual Memory by ID
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 3: Get Factual Memory by ID"
    echo "GET ${API_BASE}/factual/${MEMORY_ID}?user_id=test_user_123"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/factual/${MEMORY_ID}?user_id=test_user_123")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(json_value "$RESPONSE_BODY" "id")
        if [ "$RETRIEVED_ID" = "$MEMORY_ID" ]; then
            print_result 0 "Factual memory retrieved successfully"
        else
            print_result 1 "Retrieved memory ID doesn't match"
        fi
    else
        print_result 1 "Failed to retrieve factual memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: Search Facts by Subject
print_section "Test 4: Search Facts by Subject"
echo "GET ${API_BASE}/factual/search/subject?user_id=test_user_123&subject=programming&limit=10"

SEARCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/factual/search/subject?user_id=test_user_123&subject=programming&limit=10")
HTTP_CODE=$(echo "$SEARCH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SEARCH_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Factual memory search completed (found: $COUNT)"
else
    print_result 1 "Failed to search factual memories"
fi

# Test 5: List All Factual Memories
print_section "Test 5: List All Factual Memories for User"
echo "GET ${API_BASE}?user_id=test_user_123&memory_type=factual&limit=50"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_123&memory_type=factual&limit=50")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Listed factual memories (found: $COUNT)"
else
    print_result 1 "Failed to list factual memories"
fi

# Test 6: Extract Multiple Facts
print_section "Test 6: Extract Multiple Facts from Complex Dialog"
echo "POST ${API_BASE}/factual/extract"
COMPLEX_PAYLOAD='{
  "user_id": "test_user_123",
  "dialog_content": "I live in San Francisco, California. My birthday is on March 15th. I graduated from Stanford University with a Computer Science degree. I am allergic to peanuts.",
  "importance_score": 0.9
}'
echo "Request Body:"
pretty_json "$COMPLEX_PAYLOAD"

COMPLEX_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/factual/extract" \
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
        print_result 0 "Multiple facts extracted successfully"
    else
        print_result 1 "Complex extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract multiple facts"
fi

# Test 7: Update Factual Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 7: Update Factual Memory"
    echo "PUT ${API_BASE}/factual/${MEMORY_ID}?user_id=test_user_123"
    UPDATE_PAYLOAD='{
      "importance_score": 0.95,
      "confidence": 1.0
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/factual/${MEMORY_ID}?user_id=test_user_123" \
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
            print_result 0 "Factual memory updated successfully"
        else
            print_result 1 "Update returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to update factual memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Delete Factual Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 8: Delete Factual Memory"
    echo "DELETE ${API_BASE}/factual/${MEMORY_ID}?user_id=test_user_123"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/factual/${MEMORY_ID}?user_id=test_user_123")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Factual memory deleted successfully"
        else
            print_result 1 "Delete returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to delete factual memory"
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
    echo -e "${GREEN}All factual memory tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
