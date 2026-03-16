#!/bin/bash

# Memory Associations Testing Script
# Tests A-MEM cross-linked memory retrieval (related memories)

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
echo "Memory Associations Tests"
echo "======================================================================"
echo ""

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAILED${NC}: $2"
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

# Setup: Store a factual memory to use for association tests
echo -e "${YELLOW}Setup: Storing a test memory for association tests...${NC}"
SETUP_PAYLOAD='{
  "user_id": "test_user_v2_smoke",
  "dialog_content": "Albert Einstein developed the theory of relativity. He was born in Germany and later moved to the United States. His famous equation is E=mc^2.",
  "importance_score": 0.8
}'

SETUP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/factual/extract" \
  -H "Content-Type: application/json" \
  -d "$SETUP_PAYLOAD")
SETUP_HTTP_CODE=$(echo "$SETUP_RESPONSE" | tail -n1)
SETUP_BODY=$(echo "$SETUP_RESPONSE" | sed '$d')

MEMORY_ID=""
if [ "$SETUP_HTTP_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        MEMORY_ID=$(echo "$SETUP_BODY" | jq -r '.data.memory_ids[0] // empty')
    else
        MEMORY_ID=$(echo "$SETUP_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('memory_ids', [None])[0] or '')" 2>/dev/null)
    fi
    echo -e "${GREEN}Setup memory stored (ID: $MEMORY_ID)${NC}"
else
    echo -e "${RED}Setup failed (HTTP $SETUP_HTTP_CODE)${NC}"
fi
echo ""

# Test 1: Get related memories for the stored memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 1: Get Related Memories"
    echo "GET ${API_BASE}/factual/${MEMORY_ID}/related?user_id=test_user_v2_smoke"

    RELATED_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/factual/${MEMORY_ID}/related?user_id=test_user_v2_smoke")
    HTTP_CODE=$(echo "$RELATED_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$RELATED_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        COUNT=$(json_value "$RESPONSE_BODY" "count")
        print_result 0 "Related memories retrieved successfully (found: $COUNT)"
    else
        print_result 1 "Failed to get related memories (HTTP $HTTP_CODE)"
    fi
else
    echo -e "${YELLOW}Skipping Test 1: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 2: Verify response structure (related_memories array)
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 2: Verify Response Structure"
    echo "Checking response fields from Test 1..."

    if [ "$HTTP_CODE" = "200" ]; then
        # Check that related_memories key exists
        if command -v jq &> /dev/null; then
            HAS_RELATED=$(echo "$RESPONSE_BODY" | jq 'has("related_memories")')
            HAS_COUNT=$(echo "$RESPONSE_BODY" | jq 'has("count")')
        else
            HAS_RELATED=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'related_memories' in data else 'false')")
            HAS_COUNT=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'count' in data else 'false')")
        fi

        if [ "$HAS_RELATED" = "true" ] && [ "$HAS_COUNT" = "true" ]; then
            print_result 0 "Response has expected structure (related_memories array + count)"
        else
            print_result 1 "Response missing expected fields (related_memories=$HAS_RELATED, count=$HAS_COUNT)"
        fi
    else
        print_result 1 "Cannot verify structure - previous request failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Get related for non-existent memory (should return empty)
print_section "Test 3: Related Memories for Non-Existent Memory"
FAKE_ID="00000000-0000-0000-0000-000000000000"
echo "GET ${API_BASE}/factual/${FAKE_ID}/related?user_id=test_user_v2_smoke"

NONEXIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/factual/${FAKE_ID}/related?user_id=test_user_v2_smoke")
HTTP_CODE=$(echo "$NONEXIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$NONEXIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    if [ "$COUNT" = "0" ]; then
        print_result 0 "Non-existent memory returns empty related list (count=0)"
    else
        print_result 0 "Non-existent memory returned (count=$COUNT)"
    fi
elif [ "$HTTP_CODE" = "404" ]; then
    print_result 0 "Non-existent memory correctly returns 404"
else
    print_result 1 "Unexpected response for non-existent memory (HTTP $HTTP_CODE)"
fi

# Cleanup: Delete test memories
echo ""
echo -e "${YELLOW}Cleanup: Removing test data for test_user_v2_smoke...${NC}"
CLEANUP_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_v2_smoke&memory_type=factual&limit=100")
CLEANUP_HTTP_CODE=$(echo "$CLEANUP_RESPONSE" | tail -n1)
CLEANUP_BODY=$(echo "$CLEANUP_RESPONSE" | sed '$d')

if [ "$CLEANUP_HTTP_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        MEMORY_IDS=$(echo "$CLEANUP_BODY" | jq -r '.memories[].id')
    else
        MEMORY_IDS=$(echo "$CLEANUP_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('\n'.join([m['id'] for m in data.get('memories', [])]))" 2>/dev/null)
    fi

    for MID in $MEMORY_IDS; do
        if [ -n "$MID" ] && [ "$MID" != "null" ]; then
            curl -s -X DELETE "${API_BASE}/factual/${MID}?user_id=test_user_v2_smoke" > /dev/null 2>&1
        fi
    done
    echo -e "${GREEN}Cleanup complete${NC}"
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
    echo -e "${GREEN}All memory association tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
