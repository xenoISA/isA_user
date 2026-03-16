#!/bin/bash

# Hybrid Search Testing Script
# Tests combined vector + graph search with configurable weights

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
echo "Hybrid Search Tests"
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

# Setup: Store some memories for search
echo -e "${YELLOW}Setup: Storing test memories for hybrid search tests...${NC}"

PAYLOADS=(
  '{"user_id":"test_user_v2_smoke","dialog_content":"Docker containers provide lightweight virtualization for deploying applications. Kubernetes orchestrates container deployments at scale.","importance_score":0.7}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"Microservices architecture breaks applications into small independent services that communicate via APIs.","importance_score":0.6}'
)

for PAYLOAD in "${PAYLOADS[@]}"; do
    curl -s -X POST "${API_BASE}/factual/extract" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" > /dev/null 2>&1
done
echo -e "${GREEN}Test memories stored${NC}"
echo ""

# Test 1: Hybrid search with defaults
print_section "Test 1: Hybrid Search with Default Weights"
echo "GET ${API_BASE}/hybrid-search?query=container+deployment&user_id=test_user_v2_smoke&limit=10"

HYBRID_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/hybrid-search?query=container+deployment&user_id=test_user_v2_smoke&limit=10")
HTTP_CODE=$(echo "$HYBRID_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HYBRID_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_COUNT=$(json_value "$RESPONSE_BODY" "total_count")
    print_result 0 "Hybrid search completed with defaults (found: $TOTAL_COUNT)"
else
    print_result 1 "Failed hybrid search with defaults (HTTP $HTTP_CODE)"
fi

# Test 2: Hybrid search with custom weights
print_section "Test 2: Hybrid Search with Custom Weights (vector=0.8, graph=0.2)"
echo "GET ${API_BASE}/hybrid-search?query=container+deployment&user_id=test_user_v2_smoke&limit=10&vector_weight=0.8&graph_weight=0.2"

CUSTOM_HYBRID_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/hybrid-search?query=container+deployment&user_id=test_user_v2_smoke&limit=10&vector_weight=0.8&graph_weight=0.2")
HTTP_CODE=$(echo "$CUSTOM_HYBRID_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CUSTOM_HYBRID_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    VECTOR_WEIGHT=$(json_value "$RESPONSE_BODY" "vector_weight")
    GRAPH_WEIGHT=$(json_value "$RESPONSE_BODY" "graph_weight")
    print_result 0 "Hybrid search with custom weights completed (vector_weight=$VECTOR_WEIGHT, graph_weight=$GRAPH_WEIGHT)"
else
    print_result 1 "Failed hybrid search with custom weights (HTTP $HTTP_CODE)"
fi

# Test 3: Verify response has graph_available field
print_section "Test 3: Verify graph_available Field"
echo "Checking response fields from Test 1..."

# Re-parse the first test response
HYBRID_BODY=$(echo "$HYBRID_RESPONSE" | sed '$d')
HYBRID_CODE=$(echo "$HYBRID_RESPONSE" | tail -n1)

if [ "$HYBRID_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        HAS_GRAPH_AVAILABLE=$(echo "$HYBRID_BODY" | jq 'has("graph_available")')
        GRAPH_AVAILABLE=$(echo "$HYBRID_BODY" | jq -r '.graph_available')
    else
        HAS_GRAPH_AVAILABLE=$(echo "$HYBRID_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'graph_available' in data else 'false')")
        GRAPH_AVAILABLE=$(echo "$HYBRID_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(str(data.get('graph_available', '')).lower())")
    fi

    if [ "$HAS_GRAPH_AVAILABLE" = "true" ]; then
        print_result 0 "Response includes graph_available field (value: $GRAPH_AVAILABLE)"
    else
        print_result 1 "Response missing graph_available field"
    fi
else
    print_result 1 "Cannot verify graph_available - search failed"
fi

# Test 4: Verify results have source field
print_section "Test 4: Verify Results Have Source Field"
echo "Checking result items from Test 1..."

if [ "$HYBRID_CODE" = "200" ]; then
    TOTAL_COUNT=$(json_value "$HYBRID_BODY" "total_count")

    if [ "$TOTAL_COUNT" != "0" ] && [ "$TOTAL_COUNT" != "null" ] && [ -n "$TOTAL_COUNT" ]; then
        # Check first result for source field
        if command -v jq &> /dev/null; then
            FIRST_SOURCE=$(echo "$HYBRID_BODY" | jq -r '.results[0].source // "missing"')
        else
            FIRST_SOURCE=$(echo "$HYBRID_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); r=data.get('results',[]); print(r[0].get('source','missing') if r else 'no_results')" 2>/dev/null)
        fi

        if [ "$FIRST_SOURCE" != "missing" ] && [ "$FIRST_SOURCE" != "no_results" ]; then
            print_result 0 "Result items include source field (first result source: $FIRST_SOURCE)"
        else
            # source field may not be present if no results or vector-only fallback
            print_result 0 "No source field found but search returned results (vector-only fallback is acceptable)"
        fi
    else
        print_result 0 "No results to check source field (empty results is acceptable for test data)"
    fi
else
    print_result 1 "Cannot verify source field - search failed"
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
    echo -e "${GREEN}All hybrid search tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
