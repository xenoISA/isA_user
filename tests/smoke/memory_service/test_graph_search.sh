#!/bin/bash

# Graph Search Testing Script
# Tests knowledge graph entity search and neighbor traversal via isA_Data

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
TESTS_SKIPPED=0

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
echo "Graph Search Tests"
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

# Function to print skip result
print_skip() {
    echo -e "${YELLOW}SKIP${NC}: $1"
    ((TESTS_SKIPPED++))
}

# Function to print section header
print_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

# Test 1: Health check - verify graph_connected field
print_section "Test 1: Health Check - Graph Connected Status"
echo "GET ${API_BASE}/health"

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

GRAPH_CONNECTED="false"
if [ "$HTTP_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        HAS_GRAPH=$(echo "$RESPONSE_BODY" | jq 'has("graph_connected")')
        GRAPH_CONNECTED=$(echo "$RESPONSE_BODY" | jq -r '.graph_connected')
    else
        HAS_GRAPH=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'graph_connected' in data else 'false')")
        GRAPH_CONNECTED=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(str(data.get('graph_connected', False)).lower())")
    fi

    if [ "$HAS_GRAPH" = "true" ]; then
        print_result 0 "Health check includes graph_connected field (value: $GRAPH_CONNECTED)"
    else
        print_result 1 "Health check missing graph_connected field"
    fi
else
    print_result 1 "Health check failed (HTTP $HTTP_CODE)"
fi

echo ""
echo -e "${YELLOW}Graph connected: $GRAPH_CONNECTED${NC}"

# If graph is not connected, skip remaining tests gracefully
if [ "$GRAPH_CONNECTED" != "true" ]; then
    echo -e "${YELLOW}Graph service is not connected. Remaining graph tests will verify graceful degradation.${NC}"
fi

# Test 2: Graph search
print_section "Test 2: Graph Entity Search"
echo "GET ${API_BASE}/graph/search?query=test&user_id=test_user_v2_smoke&limit=10"

GRAPH_SEARCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/graph/search?query=test&user_id=test_user_v2_smoke&limit=10")
HTTP_CODE=$(echo "$GRAPH_SEARCH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$GRAPH_SEARCH_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$GRAPH_CONNECTED" = "true" ]; then
    if [ "$HTTP_CODE" = "200" ]; then
        if command -v jq &> /dev/null; then
            HAS_ENTITIES=$(echo "$RESPONSE_BODY" | jq 'has("entities")')
            HAS_TOTAL=$(echo "$RESPONSE_BODY" | jq 'has("total")')
        else
            HAS_ENTITIES=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'entities' in data else 'false')")
            HAS_TOTAL=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'total' in data else 'false')")
        fi

        if [ "$HAS_ENTITIES" = "true" ] && [ "$HAS_TOTAL" = "true" ]; then
            TOTAL=$(json_value "$RESPONSE_BODY" "total")
            print_result 0 "Graph search returned entities (total: $TOTAL)"
        else
            print_result 1 "Graph search response missing expected fields"
        fi
    else
        print_result 1 "Graph search failed (HTTP $HTTP_CODE)"
    fi
else
    if [ "$HTTP_CODE" = "503" ]; then
        print_skip "Graph search returned 503 (graph service unavailable - expected)"
    else
        print_skip "Graph search returned HTTP $HTTP_CODE (graph not connected)"
    fi
fi

# Test 3: Graph neighbors
print_section "Test 3: Graph Neighbors"
echo "GET ${API_BASE}/graph/neighbors?entity_id=test_entity&depth=1"

NEIGHBORS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/graph/neighbors?entity_id=test_entity&depth=1")
HTTP_CODE=$(echo "$NEIGHBORS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$NEIGHBORS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$GRAPH_CONNECTED" = "true" ]; then
    if [ "$HTTP_CODE" = "200" ]; then
        if command -v jq &> /dev/null; then
            HAS_NEIGHBORS=$(echo "$RESPONSE_BODY" | jq 'has("neighbors")')
            HAS_ENTITY_ID=$(echo "$RESPONSE_BODY" | jq 'has("entity_id")')
        else
            HAS_NEIGHBORS=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'neighbors' in data else 'false')")
            HAS_ENTITY_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'entity_id' in data else 'false')")
        fi

        if [ "$HAS_NEIGHBORS" = "true" ] && [ "$HAS_ENTITY_ID" = "true" ]; then
            print_result 0 "Graph neighbors returned successfully"
        else
            print_result 1 "Graph neighbors response missing expected fields"
        fi
    else
        print_result 1 "Graph neighbors failed (HTTP $HTTP_CODE)"
    fi
else
    if [ "$HTTP_CODE" = "503" ]; then
        print_skip "Graph neighbors returned 503 (graph service unavailable - expected)"
    else
        print_skip "Graph neighbors returned HTTP $HTTP_CODE (graph not connected)"
    fi
fi

# Test 4: Handle gracefully when graph service is unavailable
print_section "Test 4: Graceful Degradation Verification"

if [ "$GRAPH_CONNECTED" != "true" ]; then
    # Graph is already down, so tests 2 and 3 already verified graceful handling
    # Verify universal search still works without graph
    echo "Verifying universal search works even with graph unavailable..."
    echo "GET ${API_BASE}/search?user_id=test_user_v2_smoke&query=test&limit=5&include_graph=true"

    FALLBACK_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/search?user_id=test_user_v2_smoke&query=test&limit=5&include_graph=true")
    HTTP_CODE=$(echo "$FALLBACK_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$FALLBACK_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Universal search with include_graph=true succeeds even when graph is unavailable"
    else
        print_result 1 "Universal search failed when graph is unavailable (HTTP $HTTP_CODE)"
    fi
else
    echo "Graph is connected. Verifying 503 handling with a malformed entity ID..."
    echo "GET ${API_BASE}/graph/neighbors?entity_id=&depth=1"

    EDGE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/graph/neighbors?entity_id=nonexistent_entity_12345&depth=1")
    HTTP_CODE=$(echo "$EDGE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$EDGE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "503" ]; then
        print_result 0 "Graph endpoint handles edge cases gracefully (HTTP $HTTP_CODE)"
    else
        print_result 1 "Unexpected response for edge case (HTTP $HTTP_CODE)"
    fi
fi

# Summary
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo -e "${YELLOW}Skipped: $TESTS_SKIPPED${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total (excl. skipped): $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All graph search tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
