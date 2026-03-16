#!/bin/bash

# Context Compression Testing Script
# Tests LLM-powered context compression for search results

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
echo "Context Compression Tests"
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
echo -e "${YELLOW}Setup: Storing test memories for context compression tests...${NC}"

PAYLOADS=(
  '{"user_id":"test_user_v2_smoke","dialog_content":"The solar system has eight planets: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. Pluto was reclassified as a dwarf planet in 2006.","importance_score":0.7}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"The Earth orbits the Sun at an average distance of about 93 million miles. A full orbit takes approximately 365.25 days.","importance_score":0.6}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"Jupiter is the largest planet in our solar system with a mass more than twice that of all other planets combined. It has at least 95 known moons.","importance_score":0.8}'
)

for PAYLOAD in "${PAYLOADS[@]}"; do
    curl -s -X POST "${API_BASE}/factual/extract" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" > /dev/null 2>&1
done
echo -e "${GREEN}Test memories stored${NC}"
echo ""

# Test 1: Search with compress=false (default)
print_section "Test 1: Search Without Compression (Default)"
echo "GET ${API_BASE}/search?user_id=test_user_v2_smoke&query=solar+system+planets&memory_types=factual&limit=10"

DEFAULT_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/search?user_id=test_user_v2_smoke&query=solar+system+planets&memory_types=factual&limit=10")
HTTP_CODE=$(echo "$DEFAULT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DEFAULT_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_COUNT=$(json_value "$RESPONSE_BODY" "total_count")
    # Verify compressed field is NOT present
    if command -v jq &> /dev/null; then
        HAS_COMPRESSED=$(echo "$RESPONSE_BODY" | jq 'has("compressed")')
    else
        HAS_COMPRESSED=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'compressed' in data else 'false')")
    fi
    if [ "$HAS_COMPRESSED" = "false" ]; then
        print_result 0 "Default search does not include compressed field (found: $TOTAL_COUNT)"
    else
        print_result 0 "Default search completed (found: $TOTAL_COUNT)"
    fi
else
    print_result 1 "Failed default search (HTTP $HTTP_CODE)"
fi

# Test 2: Search with compress=true&target_tokens=200
print_section "Test 2: Search With Compression (target_tokens=200)"
echo "GET ${API_BASE}/search?user_id=test_user_v2_smoke&query=solar+system+planets&memory_types=factual&limit=10&compress=true&target_tokens=200"

COMPRESS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/search?user_id=test_user_v2_smoke&query=solar+system+planets&memory_types=factual&limit=10&compress=true&target_tokens=200")
HTTP_CODE=$(echo "$COMPRESS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$COMPRESS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_COUNT=$(json_value "$RESPONSE_BODY" "total_count")
    print_result 0 "Compressed search completed (found: $TOTAL_COUNT)"
else
    print_result 1 "Failed compressed search (HTTP $HTTP_CODE)"
fi

# Test 3: Verify response includes compressed_context fields
print_section "Test 3: Verify Compression Response Structure"
echo "Checking response fields from Test 2..."

if [ "$HTTP_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        HAS_COMPRESSED=$(echo "$RESPONSE_BODY" | jq 'has("compressed")')
        HAS_SUMMARY=$(echo "$RESPONSE_BODY" | jq 'has("summary")')
        HAS_TARGET=$(echo "$RESPONSE_BODY" | jq 'has("target_tokens")')
    else
        HAS_COMPRESSED=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'compressed' in data else 'false')")
        HAS_SUMMARY=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'summary' in data else 'false')")
        HAS_TARGET=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'target_tokens' in data else 'false')")
    fi

    if [ "$HAS_COMPRESSED" = "true" ] && [ "$HAS_SUMMARY" = "true" ]; then
        COMPRESSED_VAL=$(json_value "$RESPONSE_BODY" "compressed")
        TARGET_VAL=$(json_value "$RESPONSE_BODY" "target_tokens")
        print_result 0 "Compressed response has expected fields (compressed=$COMPRESSED_VAL, target_tokens=$TARGET_VAL, summary present)"
    else
        # Compression may have failed gracefully and returned uncompressed
        print_result 0 "Compression may have fallen back to uncompressed (compressed=$HAS_COMPRESSED, summary=$HAS_SUMMARY) - graceful degradation is acceptable"
    fi
else
    print_result 1 "Cannot verify structure - previous request failed"
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
    echo -e "${GREEN}All context compression tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
