#!/bin/bash

# Semantic Memory Testing Script
# Tests semantic memory extraction and storage capabilities

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

# JSON parsing function
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
echo "Semantic Memory Service Tests"
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

# Test 2: Extract Semantic Memory from Dialog
print_section "Test 2: Extract Semantic Memory from Dialog (AI-Powered)"
echo "POST ${API_BASE}/semantic/extract"
EXTRACT_PAYLOAD='{
  "user_id": "test_user_abc",
  "dialog_content": "Machine learning is a subset of artificial intelligence that focuses on building systems that learn from data. Deep learning uses neural networks with multiple layers. Common algorithms include decision trees, random forests, and support vector machines.",
  "importance_score": 0.8
}'
echo "Request Body:"
pretty_json "$EXTRACT_PAYLOAD"

EXTRACT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/semantic/extract" \
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
        print_result 0 "Semantic memory extracted and stored successfully"
        echo -e "${YELLOW}Memory ID: $MEMORY_ID${NC}"
    else
        print_result 1 "Extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract semantic memory"
fi

# Test 3: Get Semantic Memory by ID
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 3: Get Semantic Memory by ID"
    echo "GET ${API_BASE}/semantic/${MEMORY_ID}?user_id=test_user_abc"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/semantic/${MEMORY_ID}?user_id=test_user_abc")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(json_value "$RESPONSE_BODY" "id")
        if [ "$RETRIEVED_ID" = "$MEMORY_ID" ]; then
            print_result 0 "Semantic memory retrieved successfully"
        else
            print_result 1 "Retrieved memory ID doesn't match"
        fi
    else
        print_result 1 "Failed to retrieve semantic memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: List All Semantic Memories
print_section "Test 4: List All Semantic Memories for User"
echo "GET ${API_BASE}?user_id=test_user_abc&memory_type=semantic&limit=50"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_abc&memory_type=semantic&limit=50")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Listed semantic memories (found: $COUNT)"
else
    print_result 1 "Failed to list semantic memories"
fi

# Test 5: Extract Domain Knowledge
print_section "Test 5: Extract Domain Knowledge (Biology)"
echo "POST ${API_BASE}/semantic/extract"
DOMAIN_PAYLOAD='{
  "user_id": "test_user_abc",
  "dialog_content": "Photosynthesis is the process by which plants convert light energy into chemical energy. It occurs in chloroplasts and involves two stages: light-dependent reactions and the Calvin cycle. The overall equation is: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2.",
  "importance_score": 0.85
}'
echo "Request Body:"
pretty_json "$DOMAIN_PAYLOAD"

DOMAIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/semantic/extract" \
  -H "Content-Type: application/json" \
  -d "$DOMAIN_PAYLOAD")
HTTP_CODE=$(echo "$DOMAIN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DOMAIN_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Domain knowledge extracted successfully"
    else
        print_result 1 "Domain extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract domain knowledge"
fi

# Test 6: Extract Conceptual Knowledge
print_section "Test 6: Extract Conceptual Knowledge (Economics)"
echo "POST ${API_BASE}/semantic/extract"
CONCEPT_PAYLOAD='{
  "user_id": "test_user_abc",
  "dialog_content": "Supply and demand is a fundamental economic principle. When supply exceeds demand, prices tend to fall. When demand exceeds supply, prices tend to rise. Market equilibrium occurs when supply equals demand. External factors like government policies can shift these curves.",
  "importance_score": 0.75
}'
echo "Request Body:"
pretty_json "$CONCEPT_PAYLOAD"

CONCEPT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/semantic/extract" \
  -H "Content-Type: application/json" \
  -d "$CONCEPT_PAYLOAD")
HTTP_CODE=$(echo "$CONCEPT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CONCEPT_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Conceptual knowledge extracted successfully"
    else
        print_result 1 "Concept extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract conceptual knowledge"
fi

# Test 7: Update Semantic Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 7: Update Semantic Memory"
    echo "PUT ${API_BASE}/semantic/${MEMORY_ID}?user_id=test_user_abc"
    UPDATE_PAYLOAD='{
      "importance_score": 0.9,
      "confidence": 0.95
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/semantic/${MEMORY_ID}?user_id=test_user_abc" \
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
            print_result 0 "Semantic memory updated successfully"
        else
            print_result 1 "Update returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to update semantic memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Delete Semantic Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 8: Delete Semantic Memory"
    echo "DELETE ${API_BASE}/semantic/${MEMORY_ID}?user_id=test_user_abc"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/semantic/${MEMORY_ID}?user_id=test_user_abc")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Semantic memory deleted successfully"
        else
            print_result 1 "Delete returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to delete semantic memory"
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
    echo -e "${GREEN}All semantic memory tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
