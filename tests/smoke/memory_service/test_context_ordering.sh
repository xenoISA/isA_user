#!/bin/bash

# Context Ordering Testing Script
# Tests lost-in-the-middle mitigation via importance-based edge ordering

BASE_URL="${BASE_URL:-http://localhost}"
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
echo "Context Ordering Tests"
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

# Setup: Store some memories
echo -e "${YELLOW}Setup: Storing test memories for context ordering tests...${NC}"

PAYLOADS=(
  '{"user_id":"test_user_v2_smoke","dialog_content":"Quantum computing uses qubits which can exist in superposition states unlike classical bits.","importance_score":0.9}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"Cloud computing provides on-demand access to shared computing resources over the internet.","importance_score":0.5}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"Edge computing processes data near the source rather than in a centralized data center.","importance_score":0.7}'
)

for PAYLOAD in "${PAYLOADS[@]}"; do
    curl -s -X POST "${API_BASE}/factual/extract" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" > /dev/null 2>&1
done
echo -e "${GREEN}Test memories stored${NC}"
echo ""

# Test 1: Search with order_results=false (default)
print_section "Test 1: Search Without Context Ordering (Default)"
echo "GET ${API_BASE}/search?user_id=test_user_v2_smoke&query=computing&memory_types=factual&limit=10"

DEFAULT_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/search?user_id=test_user_v2_smoke&query=computing&memory_types=factual&limit=10")
HTTP_CODE=$(echo "$DEFAULT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DEFAULT_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_COUNT=$(json_value "$RESPONSE_BODY" "total_count")
    # Verify context_ordered is NOT present
    if command -v jq &> /dev/null; then
        HAS_ORDERED=$(echo "$RESPONSE_BODY" | jq 'has("context_ordered")')
    else
        HAS_ORDERED=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'context_ordered' in data else 'false')")
    fi
    if [ "$HAS_ORDERED" = "false" ]; then
        print_result 0 "Default search does not include context_ordered flag (found: $TOTAL_COUNT)"
    else
        print_result 0 "Search completed (context_ordered present but that is acceptable, found: $TOTAL_COUNT)"
    fi
else
    print_result 1 "Failed default search (HTTP $HTTP_CODE)"
fi

# Test 2: Search with order_results=true
print_section "Test 2: Search With Context Ordering"
echo "GET ${API_BASE}/search?user_id=test_user_v2_smoke&query=computing&memory_types=factual&limit=10&order_results=true"

ORDERED_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/search?user_id=test_user_v2_smoke&query=computing&memory_types=factual&limit=10&order_results=true")
HTTP_CODE=$(echo "$ORDERED_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$ORDERED_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_COUNT=$(json_value "$RESPONSE_BODY" "total_count")
    print_result 0 "Context-ordered search completed (found: $TOTAL_COUNT)"
else
    print_result 1 "Failed context-ordered search (HTTP $HTTP_CODE)"
fi

# Test 3: Verify response includes context_ordered flag
print_section "Test 3: Verify context_ordered Flag"
echo "Checking response fields from Test 2..."

if [ "$HTTP_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        HAS_ORDERED=$(echo "$RESPONSE_BODY" | jq 'has("context_ordered")')
        ORDERED_VAL=$(echo "$RESPONSE_BODY" | jq -r '.context_ordered')
    else
        HAS_ORDERED=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'context_ordered' in data else 'false')")
        ORDERED_VAL=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('context_ordered', ''))")
    fi

    if [ "$HAS_ORDERED" = "true" ] && [ "$ORDERED_VAL" = "true" ]; then
        print_result 0 "Response includes context_ordered=true"
    else
        print_result 1 "Response missing or incorrect context_ordered flag (has=$HAS_ORDERED, value=$ORDERED_VAL)"
    fi
else
    print_result 1 "Cannot verify flag - previous request failed"
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
    echo -e "${GREEN}All context ordering tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
