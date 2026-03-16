#!/bin/bash

# Memory Consolidation Testing Script
# Tests promotion of frequently-accessed episodic memories into semantic knowledge

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
echo "Memory Consolidation Tests"
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

# Setup: Store some episodic memories
echo -e "${YELLOW}Setup: Storing test episodic memories for consolidation tests...${NC}"

PAYLOADS=(
  '{"user_id":"test_user_v2_smoke","dialog_content":"Today I had a meeting with the product team where we discussed the new search feature. We decided to use vector embeddings for semantic search.","importance_score":0.7}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"During the sprint review, the team demoed the vector search prototype. The results were impressive and stakeholders approved moving forward.","importance_score":0.6}'
  '{"user_id":"test_user_v2_smoke","dialog_content":"I attended a workshop on embedding models and learned about different approaches to similarity search including cosine and dot product.","importance_score":0.8}'
)

for PAYLOAD in "${PAYLOADS[@]}"; do
    curl -s -X POST "${API_BASE}/episodic/extract" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" > /dev/null 2>&1
done
echo -e "${GREEN}Test episodic memories stored${NC}"
echo ""

# Test 1: Run consolidation with default params
print_section "Test 1: Run Consolidation (Default Params)"
echo "POST ${API_BASE}/consolidate"
CONSOLIDATE_PAYLOAD='{}'
echo "Request Body:"
pretty_json "$CONSOLIDATE_PAYLOAD"

CONSOLIDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/consolidate" \
  -H "Content-Type: application/json" \
  -d "$CONSOLIDATE_PAYLOAD")
HTTP_CODE=$(echo "$CONSOLIDATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CONSOLIDATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Consolidation ran successfully with default params"
    else
        print_result 1 "Consolidation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to run consolidation (HTTP $HTTP_CODE)"
fi

# Test 2: Run with custom thresholds (low thresholds for testing)
print_section "Test 2: Run Consolidation with Custom Thresholds"
echo "POST ${API_BASE}/consolidate"
CONSOLIDATE_CUSTOM_PAYLOAD='{
  "min_access_count": 1,
  "min_age_days": 1,
  "max_cluster_size": 5,
  "similarity_threshold": 0.5
}'
echo "Request Body:"
pretty_json "$CONSOLIDATE_CUSTOM_PAYLOAD"

CONSOLIDATE_CUSTOM_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/consolidate" \
  -H "Content-Type: application/json" \
  -d "$CONSOLIDATE_CUSTOM_PAYLOAD")
HTTP_CODE=$(echo "$CONSOLIDATE_CUSTOM_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CONSOLIDATE_CUSTOM_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Consolidation ran with custom thresholds"
    else
        print_result 1 "Custom consolidation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to run custom consolidation (HTTP $HTTP_CODE)"
fi

# Test 3: Run per-user consolidation
print_section "Test 3: Run Per-User Consolidation"
echo "POST ${API_BASE}/consolidate"
CONSOLIDATE_USER_PAYLOAD='{
  "user_id": "test_user_v2_smoke",
  "min_access_count": 1,
  "min_age_days": 1
}'
echo "Request Body:"
pretty_json "$CONSOLIDATE_USER_PAYLOAD"

CONSOLIDATE_USER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/consolidate" \
  -H "Content-Type: application/json" \
  -d "$CONSOLIDATE_USER_PAYLOAD")
HTTP_CODE=$(echo "$CONSOLIDATE_USER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CONSOLIDATE_USER_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Per-user consolidation ran successfully"
    else
        print_result 1 "Per-user consolidation returned 200 but success=false"
    fi
else
    print_result 1 "Failed to run per-user consolidation (HTTP $HTTP_CODE)"
fi

# Test 4: Verify response has expected fields
print_section "Test 4: Verify Consolidation Response Structure"
echo "Checking response fields from Test 3..."

if [ "$HTTP_CODE" = "200" ]; then
    CONSOLIDATED_COUNT=$(json_value "$RESPONSE_BODY" "consolidated_count")
    MESSAGE=$(json_value "$RESPONSE_BODY" "message")

    # Check for new_semantic_ids and source_episodic_ids arrays
    if command -v jq &> /dev/null; then
        HAS_SEMANTIC_IDS=$(echo "$RESPONSE_BODY" | jq 'has("new_semantic_ids")')
        HAS_SOURCE_IDS=$(echo "$RESPONSE_BODY" | jq 'has("source_episodic_ids")')
    else
        HAS_SEMANTIC_IDS=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'new_semantic_ids' in data else 'false')")
        HAS_SOURCE_IDS=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if 'source_episodic_ids' in data else 'false')")
    fi

    if [ "$HAS_SEMANTIC_IDS" = "true" ] && [ "$HAS_SOURCE_IDS" = "true" ] && [ -n "$CONSOLIDATED_COUNT" ] && [ "$CONSOLIDATED_COUNT" != "null" ]; then
        print_result 0 "Consolidation response has expected fields (consolidated_count=$CONSOLIDATED_COUNT, new_semantic_ids present, source_episodic_ids present)"
    else
        print_result 1 "Consolidation response missing expected fields (semantic_ids=$HAS_SEMANTIC_IDS, source_ids=$HAS_SOURCE_IDS, count=$CONSOLIDATED_COUNT)"
    fi
else
    print_result 1 "Cannot verify structure - previous request failed"
fi

# Cleanup: Delete test episodic memories
echo ""
echo -e "${YELLOW}Cleanup: Removing test data for test_user_v2_smoke...${NC}"
CLEANUP_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_v2_smoke&memory_type=episodic&limit=100")
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
            curl -s -X DELETE "${API_BASE}/episodic/${MID}?user_id=test_user_v2_smoke" > /dev/null 2>&1
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
    echo -e "${GREEN}All memory consolidation tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
