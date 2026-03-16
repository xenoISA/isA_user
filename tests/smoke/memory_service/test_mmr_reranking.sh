#!/bin/bash

# MMR Re-ranking Testing Script
# Tests Maximal Marginal Relevance re-ranking for diverse search results

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
echo "MMR Re-ranking Tests"
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

# Setup: Store some factual memories for search
echo -e "${YELLOW}Setup: Storing test memories for MMR re-ranking tests...${NC}"

PAYLOADS=(
  '{"user_id":"test_user_v2_smoke","dialog_content":"Python is a high-level programming language used for web development, data science, and automation. It has a clean syntax.","importance_score":0.7}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"JavaScript is a scripting language primarily used for web browsers. Node.js allows JavaScript to run on servers.","importance_score":0.6}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"Machine learning uses algorithms to learn patterns from data. Python and TensorFlow are commonly used for ML projects.","importance_score":0.8}'
)

for PAYLOAD in "${PAYLOADS[@]}"; do
    curl -s -X POST "${API_BASE}/factual/extract" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" > /dev/null 2>&1
done
echo -e "${GREEN}Test memories stored${NC}"
echo ""

# Test 1: Search without rerank (baseline)
print_section "Test 1: Search Without Rerank (Baseline)"
echo "GET ${API_BASE}/factual/search/vector?user_id=test_user_v2_smoke&query=programming+language&limit=10"

BASELINE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/factual/search/vector?user_id=test_user_v2_smoke&query=programming+language&limit=10")
HTTP_CODE=$(echo "$BASELINE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$BASELINE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Baseline search completed (found: $COUNT)"
else
    print_result 1 "Failed baseline search (HTTP $HTTP_CODE)"
fi

# Test 2: Search with rerank=true&mmr_lambda=0.5
print_section "Test 2: Search with MMR Rerank (lambda=0.5)"
echo "GET ${API_BASE}/factual/search/vector?user_id=test_user_v2_smoke&query=programming+language&limit=10&rerank=true&mmr_lambda=0.5"

RERANK_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/factual/search/vector?user_id=test_user_v2_smoke&query=programming+language&limit=10&rerank=true&mmr_lambda=0.5")
HTTP_CODE=$(echo "$RERANK_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RERANK_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "MMR reranked search completed with lambda=0.5 (found: $COUNT)"
else
    print_result 1 "Failed MMR reranked search (HTTP $HTTP_CODE)"
fi

# Test 3: Search with rerank=true&mmr_lambda=1.0 (max relevance, no diversity penalty)
print_section "Test 3: Search with MMR Rerank (lambda=1.0 - Max Relevance)"
echo "GET ${API_BASE}/factual/search/vector?user_id=test_user_v2_smoke&query=programming+language&limit=10&rerank=true&mmr_lambda=1.0"

MAX_REL_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/factual/search/vector?user_id=test_user_v2_smoke&query=programming+language&limit=10&rerank=true&mmr_lambda=1.0")
HTTP_CODE=$(echo "$MAX_REL_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$MAX_REL_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "MMR reranked search completed with lambda=1.0 (found: $COUNT)"
else
    print_result 1 "Failed MMR reranked search with lambda=1.0 (HTTP $HTTP_CODE)"
fi

# Test 4: Verify reranked flag in universal search response
print_section "Test 4: Verify Reranked Flag in Universal Search"
echo "GET ${API_BASE}/search?user_id=test_user_v2_smoke&query=programming&memory_types=factual&limit=10&rerank=true&mmr_lambda=0.5"

UNIVERSAL_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/search?user_id=test_user_v2_smoke&query=programming&memory_types=factual&limit=10&rerank=true&mmr_lambda=0.5")
HTTP_CODE=$(echo "$UNIVERSAL_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$UNIVERSAL_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    RERANKED=$(json_value "$RESPONSE_BODY" "reranked")
    MMR_LAMBDA_VAL=$(json_value "$RESPONSE_BODY" "mmr_lambda")
    if [ "$RERANKED" = "true" ]; then
        print_result 0 "Universal search response includes reranked=true and mmr_lambda=$MMR_LAMBDA_VAL"
    else
        print_result 1 "Universal search response missing reranked flag"
    fi
else
    print_result 1 "Failed universal search with rerank (HTTP $HTTP_CODE)"
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
    echo -e "${GREEN}All MMR re-ranking tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
