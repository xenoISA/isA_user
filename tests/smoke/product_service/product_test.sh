#!/bin/bash

# Product Service CRUD Tests
# Tests product catalog, subscriptions, pricing, usage tracking, and statistics

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1/product"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

echo "======================================================================"
echo "Product Service CRUD Tests"
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

# Test 1: Get Service Info
print_section "Test 1: Get Service Info"
echo "GET ${BASE_URL}/api/v1/product/info"
INFO_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/api/v1/product/info")
HTTP_CODE=$(echo "$INFO_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INFO_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service info retrieved successfully"
else
    print_result 1 "Failed to get service info"
fi

# Test 2: Get Product Categories
print_section "Test 2: Get Product Categories"
echo "GET ${API_BASE}/categories"

CATEGORIES_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/categories")
HTTP_CODE=$(echo "$CATEGORIES_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CATEGORIES_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    CATEGORIES_COUNT=$(echo "$RESPONSE_BODY" | jq 'length' 2>/dev/null || echo "0")
    print_result 0 "Product categories retrieved (count: $CATEGORIES_COUNT)"

    # Save first category_id if available
    CATEGORY_ID=$(echo "$RESPONSE_BODY" | jq -r '.[0].category_id' 2>/dev/null || echo "")
    if [ -n "$CATEGORY_ID" ] && [ "$CATEGORY_ID" != "null" ]; then
        echo -e "${YELLOW}First Category ID: ${CATEGORY_ID}${NC}"
    fi
else
    print_result 1 "Failed to get product categories"
fi

# Test 3: Get All Products
print_section "Test 3: Get All Products"
echo "GET ${API_BASE}/products"

PRODUCTS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/products")
HTTP_CODE=$(echo "$PRODUCTS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PRODUCTS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

PRODUCT_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    PRODUCTS_COUNT=$(echo "$RESPONSE_BODY" | jq 'length' 2>/dev/null || echo "0")
    print_result 0 "Products retrieved (count: $PRODUCTS_COUNT)"

    # Save first product_id if available
    PRODUCT_ID=$(echo "$RESPONSE_BODY" | jq -r '.[0].product_id' 2>/dev/null || echo "")
    if [ -n "$PRODUCT_ID" ] && [ "$PRODUCT_ID" != "null" ]; then
        echo -e "${YELLOW}First Product ID: ${PRODUCT_ID}${NC}"
    fi
else
    print_result 1 "Failed to get products"
fi

# Test 4: Get Product by ID
if [ -n "$PRODUCT_ID" ] && [ "$PRODUCT_ID" != "null" ]; then
    print_section "Test 4: Get Product by ID"
    echo "GET ${API_BASE}/products/${PRODUCT_ID}"

    PRODUCT_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/products/${PRODUCT_ID}")
    HTTP_CODE=$(echo "$PRODUCT_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$PRODUCT_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_PRODUCT_ID=$(echo "$RESPONSE_BODY" | jq -r '.product_id' 2>/dev/null)
        if [ "$RETRIEVED_PRODUCT_ID" = "$PRODUCT_ID" ]; then
            print_result 0 "Product retrieved successfully"
        else
            print_result 1 "Product ID mismatch"
        fi
    else
        print_result 1 "Failed to get product"
    fi
else
    echo -e "${RED}ERROR: No product ID available for Test 5${NC}"
    print_result 1 "Cannot test without product ID"
fi

# Test 5: Get Product Pricing
if [ -n "$PRODUCT_ID" ] && [ "$PRODUCT_ID" != "null" ]; then
    print_section "Test 5: Get Product Pricing"
    echo "GET ${API_BASE}/products/${PRODUCT_ID}/pricing"

    PRICING_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/products/${PRODUCT_ID}/pricing")
    HTTP_CODE=$(echo "$PRICING_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$PRICING_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Product pricing retrieved successfully"
    else
        print_result 1 "Failed to get product pricing"
    fi
else
    echo -e "${RED}ERROR: No product ID available for Test 6${NC}"
    print_result 1 "Cannot test without product ID"
fi

# Test 6: Check Product Availability
if [ -n "$PRODUCT_ID" ] && [ "$PRODUCT_ID" != "null" ]; then
    print_section "Test 6: Check Product Availability"
    TEST_USER_ID="test_user_123"
    echo "GET ${API_BASE}/products/${PRODUCT_ID}/availability?user_id=${TEST_USER_ID}"

    AVAILABILITY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/products/${PRODUCT_ID}/availability?user_id=${TEST_USER_ID}")
    HTTP_CODE=$(echo "$AVAILABILITY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$AVAILABILITY_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Product availability checked successfully"
    else
        print_result 1 "Failed to check product availability"
    fi
else
    echo -e "${RED}ERROR: No product ID available for Test 7${NC}"
    print_result 1 "Cannot test without product ID"
fi

# Test 7: Get Products by Category
if [ -n "$CATEGORY_ID" ] && [ "$CATEGORY_ID" != "null" ]; then
    print_section "Test 7: Get Products by Category"
    echo "GET ${API_BASE}/products?category_id=${CATEGORY_ID}"

    CATEGORY_PRODUCTS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/products?category_id=${CATEGORY_ID}")
    HTTP_CODE=$(echo "$CATEGORY_PRODUCTS_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CATEGORY_PRODUCTS_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        CATEGORY_PRODUCTS_COUNT=$(echo "$RESPONSE_BODY" | jq 'length' 2>/dev/null || echo "0")
        print_result 0 "Products by category retrieved (count: $CATEGORY_PRODUCTS_COUNT)"
    else
        print_result 1 "Failed to get products by category"
    fi
else
    echo -e "${YELLOW}INFO: Skipping Test 8 - no category ID available${NC}"
    print_result 1 "Cannot test without category ID"
fi

# Test 8: Create Subscription
print_section "Test 8: Create Subscription"

# First, create a test user directly in the database to satisfy foreign key constraint
TEST_USER_ID="product_test_user_$(date +%s)"
TEST_USER_EMAIL="${TEST_USER_ID}@example.com"
echo "Creating test user ${TEST_USER_ID} in database..."

USER_CREATED=$(docker exec user-staging python3 -c "
import sys
sys.path.append('/app')
from core.database.supabase_client import get_supabase_client

try:
    db = get_supabase_client()
    # Insert test user into users table
    user_data = {
        'user_id': '${TEST_USER_ID}',
        'email': '${TEST_USER_EMAIL}',
        'full_name': 'Test User for Product Service',
        'is_active': True
    }
    result = db.table('users').insert(user_data).execute()
    if result.data:
        print('success')
    else:
        print('failed')
except Exception as e:
    print('failed')
" 2>&1)

if [[ "$USER_CREATED" == *"success"* ]]; then
    echo "✓ Test user created in database"
else
    echo "⚠ User creation failed, using existing user test_user_2"
    TEST_USER_ID="test_user_2"
fi

TEST_PLAN_ID="pro-plan"  # Using the correct plan ID from migration
echo "POST ${API_BASE}/subscriptions"
CREATE_SUB_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"plan_id\": \"${TEST_PLAN_ID}\",
  \"billing_cycle\": \"monthly\",
  \"metadata\": {
    \"source\": \"test_suite\"
  }
}"
echo "Request Body:"
echo "$CREATE_SUB_PAYLOAD" | jq '.'

CREATE_SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/subscriptions" \
  -H "Content-Type: application/json" \
  -d "$CREATE_SUB_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_SUB_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_SUB_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

SUBSCRIPTION_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    SUBSCRIPTION_ID=$(echo "$RESPONSE_BODY" | jq -r '.subscription_id' 2>/dev/null || echo "")
    if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
        print_result 0 "Subscription created successfully"
        echo -e "${YELLOW}Subscription ID: ${SUBSCRIPTION_ID}${NC}"
    else
        print_result 1 "Failed to get subscription ID from response"
    fi
else
    print_result 1 "Failed to create subscription"
fi

# Test 9: Get User Subscriptions
print_section "Test 9: Get User Subscriptions"
echo "GET ${API_BASE}/subscriptions/user/${TEST_USER_ID}"

USER_SUBS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/subscriptions/user/${TEST_USER_ID}")
HTTP_CODE=$(echo "$USER_SUBS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_SUBS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUBS_COUNT=$(echo "$RESPONSE_BODY" | jq 'length' 2>/dev/null || echo "0")
    print_result 0 "User subscriptions retrieved (count: $SUBS_COUNT)"
else
    print_result 1 "Failed to get user subscriptions"
fi

# Test 10: Get Subscription by ID
if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    print_section "Test 10: Get Subscription by ID"
    echo "GET ${API_BASE}/subscriptions/${SUBSCRIPTION_ID}"

    SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/subscriptions/${SUBSCRIPTION_ID}")
    HTTP_CODE=$(echo "$SUB_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$SUB_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_SUB_ID=$(echo "$RESPONSE_BODY" | jq -r '.subscription_id' 2>/dev/null)
        if [ "$RETRIEVED_SUB_ID" = "$SUBSCRIPTION_ID" ]; then
            print_result 0 "Subscription retrieved successfully"
        else
            print_result 1 "Subscription ID mismatch"
        fi
    else
        print_result 1 "Failed to get subscription"
    fi
else
    echo -e "${RED}ERROR: No subscription ID available for Test 11${NC}"
    print_result 1 "Cannot test without subscription ID"
fi

# Test 11: Record Product Usage
if [ -n "$PRODUCT_ID" ] && [ "$PRODUCT_ID" != "null" ]; then
    print_section "Test 11: Record Product Usage"
    echo "POST ${API_BASE}/usage/record"
    USAGE_PAYLOAD="{
      \"user_id\": \"${TEST_USER_ID}\",
      \"product_id\": \"${PRODUCT_ID}\",
      \"usage_amount\": 100.5,
      \"organization_id\": \"org_test\",
      \"subscription_id\": \"${SUBSCRIPTION_ID}\",
      \"usage_details\": {
        \"endpoint\": \"/api/test\",
        \"method\": \"POST\"
      }
    }"
    echo "Request Body:"
    echo "$USAGE_PAYLOAD" | jq '.'

    USAGE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/usage/record" \
      -H "Content-Type: application/json" \
      -d "$USAGE_PAYLOAD")
    HTTP_CODE=$(echo "$USAGE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$USAGE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Product usage recorded successfully"
    else
        print_result 1 "Failed to record product usage"
    fi
else
    echo -e "${RED}ERROR: No product ID available for Test 12${NC}"
    print_result 1 "Cannot test without product ID"
fi

# Test 12: Get Usage Records
print_section "Test 12: Get Usage Records"
echo "GET ${API_BASE}/usage/records?user_id=${TEST_USER_ID}&limit=10"

USAGE_RECORDS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/usage/records?user_id=${TEST_USER_ID}&limit=10")
HTTP_CODE=$(echo "$USAGE_RECORDS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USAGE_RECORDS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    RECORDS_COUNT=$(echo "$RESPONSE_BODY" | jq 'length' 2>/dev/null || echo "0")
    print_result 0 "Usage records retrieved (count: $RECORDS_COUNT)"
else
    print_result 1 "Failed to get usage records"
fi

# Test 13: Get Usage Statistics
print_section "Test 13: Get Usage Statistics"
echo "GET ${API_BASE}/statistics/usage?user_id=${TEST_USER_ID}"

USAGE_STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/statistics/usage?user_id=${TEST_USER_ID}")
HTTP_CODE=$(echo "$USAGE_STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USAGE_STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Usage statistics retrieved successfully"
else
    print_result 1 "Failed to get usage statistics"
fi

# Test 14: Get Service Statistics
print_section "Test 14: Get Service Statistics"
echo "GET ${API_BASE}/statistics/service"

SERVICE_STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/statistics/service")
HTTP_CODE=$(echo "$SERVICE_STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SERVICE_STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service statistics retrieved successfully"
else
    print_result 1 "Failed to get service statistics"
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
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
