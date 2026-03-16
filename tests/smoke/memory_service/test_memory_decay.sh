#!/bin/bash

# Memory Decay Testing Script
# Tests Ebbinghaus forgetting-curve decay on memory importance scores

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
echo "Memory Decay Tests"
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

# Setup: Store a factual memory so there is something to decay
echo -e "${YELLOW}Setup: Storing a test memory for decay tests...${NC}"
SETUP_PAYLOAD='{
  "user_id": "test_user_v2_smoke",
  "dialog_content": "Memory decay test data. The capital of France is Paris. This fact should be subject to decay over time.",
  "importance_score": 0.5
}'
curl -s -X POST "${API_BASE}/factual/extract" \
  -H "Content-Type: application/json" \
  -d "$SETUP_PAYLOAD" > /dev/null 2>&1
echo ""

# Test 1: Run decay cycle with default params
print_section "Test 1: Run Decay Cycle (Default Params)"
echo "POST ${API_BASE}/decay"
DECAY_PAYLOAD='{}'
echo "Request Body:"
pretty_json "$DECAY_PAYLOAD"

DECAY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/decay" \
  -H "Content-Type: application/json" \
  -d "$DECAY_PAYLOAD")
HTTP_CODE=$(echo "$DECAY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DECAY_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Decay cycle ran successfully with default params"
    else
        print_result 1 "Decay returned 200 but success=false"
    fi
else
    print_result 1 "Failed to run decay cycle (HTTP $HTTP_CODE)"
fi

# Test 2: Run decay with custom half_life_days=1
print_section "Test 2: Run Decay with Custom half_life_days=1"
echo "POST ${API_BASE}/decay"
DECAY_CUSTOM_PAYLOAD='{
  "half_life_days": 1,
  "floor_threshold": 0.05,
  "protected_threshold": 0.9
}'
echo "Request Body:"
pretty_json "$DECAY_CUSTOM_PAYLOAD"

DECAY_CUSTOM_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/decay" \
  -H "Content-Type: application/json" \
  -d "$DECAY_CUSTOM_PAYLOAD")
HTTP_CODE=$(echo "$DECAY_CUSTOM_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DECAY_CUSTOM_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Decay cycle ran with custom half_life_days=1"
    else
        print_result 1 "Custom decay returned 200 but success=false"
    fi
else
    print_result 1 "Failed to run custom decay cycle (HTTP $HTTP_CODE)"
fi

# Test 3: Run per-user decay
print_section "Test 3: Run Per-User Decay"
echo "POST ${API_BASE}/decay"
DECAY_USER_PAYLOAD='{
  "user_id": "test_user_v2_smoke",
  "half_life_days": 30
}'
echo "Request Body:"
pretty_json "$DECAY_USER_PAYLOAD"

DECAY_USER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/decay" \
  -H "Content-Type: application/json" \
  -d "$DECAY_USER_PAYLOAD")
HTTP_CODE=$(echo "$DECAY_USER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DECAY_USER_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Per-user decay cycle ran successfully"
    else
        print_result 1 "Per-user decay returned 200 but success=false"
    fi
else
    print_result 1 "Failed to run per-user decay cycle (HTTP $HTTP_CODE)"
fi

# Test 4: Verify response has expected fields
print_section "Test 4: Verify Decay Response Structure"
echo "Checking response fields from Test 3..."

if [ "$HTTP_CODE" = "200" ]; then
    DECAYED_COUNT=$(json_value "$RESPONSE_BODY" "decayed_count")
    FLOORED_COUNT=$(json_value "$RESPONSE_BODY" "floored_count")
    PROTECTED_COUNT=$(json_value "$RESPONSE_BODY" "protected_count")
    SKIPPED_COUNT=$(json_value "$RESPONSE_BODY" "skipped_count")
    TOTAL_PROCESSED=$(json_value "$RESPONSE_BODY" "total_processed")
    MESSAGE=$(json_value "$RESPONSE_BODY" "message")

    # Verify all expected fields exist (not null/empty)
    FIELDS_OK=true
    for FIELD in "$DECAYED_COUNT" "$FLOORED_COUNT" "$PROTECTED_COUNT" "$SKIPPED_COUNT" "$TOTAL_PROCESSED"; do
        if [ -z "$FIELD" ] || [ "$FIELD" = "null" ]; then
            FIELDS_OK=false
            break
        fi
    done

    if [ "$FIELDS_OK" = true ] && [ -n "$MESSAGE" ] && [ "$MESSAGE" != "null" ]; then
        print_result 0 "Decay response has all expected fields (decayed_count=$DECAYED_COUNT, floored_count=$FLOORED_COUNT, protected_count=$PROTECTED_COUNT, skipped_count=$SKIPPED_COUNT, total_processed=$TOTAL_PROCESSED)"
    else
        print_result 1 "Decay response missing expected fields"
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
    echo -e "${GREEN}All memory decay tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
