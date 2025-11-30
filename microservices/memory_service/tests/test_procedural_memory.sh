#!/bin/bash

# Procedural Memory Testing Script
# Tests procedural memory extraction and storage capabilities

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
echo "Procedural Memory Service Tests"
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

# Test 1: Extract Procedural Memory from Dialog
print_section "Test 1: Extract Procedural Memory from Dialog (AI-Powered)"
echo "POST ${API_BASE}/procedural/extract"
EXTRACT_PAYLOAD='{
  "user_id": "test_user_789",
  "dialog_content": "To make my morning coffee, first I grind 20 grams of beans using the medium setting. Then I heat water to 92 degrees Celsius. I pour water over the grounds in a circular motion for 30 seconds to bloom. After that, I continue pouring until I reach 300ml total water, which takes about 3 minutes.",
  "importance_score": 0.75
}'
echo "Request Body:"
pretty_json "$EXTRACT_PAYLOAD"

EXTRACT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/procedural/extract" \
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
        print_result 0 "Procedural memory extracted and stored successfully"
        echo -e "${YELLOW}Memory ID: $MEMORY_ID${NC}"
    else
        print_result 1 "Extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract procedural memory"
fi

# Test 2: Get Procedural Memory by ID
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 2: Get Procedural Memory by ID"
    echo "GET ${API_BASE}/procedural/${MEMORY_ID}?user_id=test_user_789"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/procedural/${MEMORY_ID}?user_id=test_user_789")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(json_value "$RESPONSE_BODY" "id")
        if [ "$RETRIEVED_ID" = "$MEMORY_ID" ]; then
            print_result 0 "Procedural memory retrieved successfully"
        else
            print_result 1 "Retrieved memory ID doesn't match"
        fi
    else
        print_result 1 "Failed to retrieve procedural memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: List All Procedural Memories
print_section "Test 3: List All Procedural Memories for User"
echo "GET ${API_BASE}?user_id=test_user_789&memory_type=procedural&limit=50"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?user_id=test_user_789&memory_type=procedural&limit=50")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "Listed procedural memories (found: $COUNT)"
else
    print_result 1 "Failed to list procedural memories"
fi

# Test 4: Extract Complex Procedure
print_section "Test 4: Extract Complex Procedure with Multiple Steps"
echo "POST ${API_BASE}/procedural/extract"
COMPLEX_PAYLOAD='{
  "user_id": "test_user_789",
  "dialog_content": "When deploying the application: Step 1 - Run all unit tests and ensure they pass. Step 2 - Build the Docker image using the production Dockerfile. Step 3 - Tag the image with the version number. Step 4 - Push to the container registry. Step 5 - Update the Kubernetes deployment with the new image tag. Step 6 - Monitor the rollout and check for any errors. Step 7 - Run smoke tests on the production environment.",
  "importance_score": 0.9
}'
echo "Request Body:"
pretty_json "$COMPLEX_PAYLOAD"

COMPLEX_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/procedural/extract" \
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
        print_result 0 "Complex procedure extracted successfully"
    else
        print_result 1 "Complex extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract complex procedure"
fi

# Test 5: Extract Recipe Procedure
print_section "Test 5: Extract Recipe Procedure"
echo "POST ${API_BASE}/procedural/extract"
RECIPE_PAYLOAD='{
  "user_id": "test_user_789",
  "dialog_content": "My grandmother'\''s secret pasta sauce recipe: Dice 2 onions and 4 cloves of garlic. Heat olive oil in a large pot. Sauté onions until translucent, about 5 minutes. Add garlic and cook for 1 minute. Add 3 cans of crushed tomatoes, 2 tablespoons of sugar, salt and pepper. Simmer for 45 minutes, stirring occasionally. Add fresh basil at the end.",
  "importance_score": 0.85
}'
echo "Request Body:"
pretty_json "$RECIPE_PAYLOAD"

RECIPE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/procedural/extract" \
  -H "Content-Type: application/json" \
  -d "$RECIPE_PAYLOAD")
HTTP_CODE=$(echo "$RECIPE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RECIPE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Recipe procedure extracted successfully"
    else
        print_result 1 "Recipe extraction returned 200 but success=false"
    fi
else
    print_result 1 "Failed to extract recipe procedure"
fi

# Test 6: Update Procedural Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 6: Update Procedural Memory"
    echo "PUT ${API_BASE}/procedural/${MEMORY_ID}?user_id=test_user_789"
    UPDATE_PAYLOAD='{
      "importance_score": 0.95,
      "confidence": 0.9
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/procedural/${MEMORY_ID}?user_id=test_user_789" \
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
            print_result 0 "Procedural memory updated successfully"
        else
            print_result 1 "Update returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to update procedural memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No memory ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Delete Procedural Memory
if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    print_section "Test 7: Delete Procedural Memory"
    echo "DELETE ${API_BASE}/procedural/${MEMORY_ID}?user_id=test_user_789"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/procedural/${MEMORY_ID}?user_id=test_user_789")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Procedural memory deleted successfully"
        else
            print_result 1 "Delete returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to delete procedural memory"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No memory ID available${NC}"
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
    echo -e "${GREEN}All procedural memory tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
