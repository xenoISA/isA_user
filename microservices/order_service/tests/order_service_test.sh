#!/bin/bash

# Order Service Testing Script
# Tests order creation, management, querying, and statistics

BASE_URL="http://localhost:8210"
API_BASE="${BASE_URL}/api/v1"

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
        # Fallback to python
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
echo "Order Service Tests"
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

# Test 2: Detailed Health Check
print_section "Test 2: Detailed Health Check"
echo "GET ${BASE_URL}/health/detailed"
DETAILED_HEALTH=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health/detailed")
HTTP_CODE=$(echo "$DETAILED_HEALTH" | tail -n1)
RESPONSE_BODY=$(echo "$DETAILED_HEALTH" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Detailed health check successful"
else
    print_result 1 "Detailed health check failed"
fi

# Test 3: Get Service Info
print_section "Test 3: Get Service Info"
echo "GET ${API_BASE}/order/info"
INFO_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/order/info")
HTTP_CODE=$(echo "$INFO_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INFO_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service info retrieved successfully"
else
    print_result 1 "Failed to retrieve service info"
fi

# Test 4: Create Order
print_section "Test 4: Create Order"
echo "POST ${API_BASE}/orders"
CREATE_ORDER_PAYLOAD='{
  "user_id": "test_user_123",
  "order_type": "purchase",
  "total_amount": 99.99,
  "currency": "USD",
  "items": [
    {
      "product_id": "prod_001",
      "name": "Test Product",
      "quantity": 2,
      "price": 49.99
    }
  ],
  "metadata": {
    "source": "web",
    "campaign": "summer_sale"
  }
}'
echo "Request Body:"
pretty_json "$CREATE_ORDER_PAYLOAD"

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/orders" \
  -H "Content-Type: application/json" \
  -d "$CREATE_ORDER_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

ORDER_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    # Extract order_id from nested order object
    if command -v jq &> /dev/null; then
        ORDER_ID=$(echo "$RESPONSE_BODY" | jq -r '.order.order_id')
    else
        ORDER_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('order', {}).get('order_id', ''))")
    fi
    if [ -n "$ORDER_ID" ] && [ "$ORDER_ID" != "null" ]; then
        print_result 0 "Order created successfully"
        echo -e "${YELLOW}Order ID: $ORDER_ID${NC}"
    else
        print_result 1 "Order creation returned success but no order_id"
    fi
else
    print_result 1 "Failed to create order"
fi

# Test 5: Get Order by ID
if [ -n "$ORDER_ID" ] && [ "$ORDER_ID" != "null" ]; then
    print_section "Test 5: Get Order by ID"
    echo "GET ${API_BASE}/orders/${ORDER_ID}"
    
    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/orders/${ORDER_ID}")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(json_value "$RESPONSE_BODY" "order_id")
        if [ "$RETRIEVED_ID" = "$ORDER_ID" ]; then
            print_result 0 "Order retrieved successfully"
        else
            print_result 1 "Order ID mismatch"
        fi
    else
        print_result 1 "Failed to retrieve order"
    fi
else
    echo -e "${YELLOW}Skipping Test 5: No order ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Update Order
if [ -n "$ORDER_ID" ] && [ "$ORDER_ID" != "null" ]; then
    print_section "Test 6: Update Order"
    echo "PUT ${API_BASE}/orders/${ORDER_ID}"
    UPDATE_PAYLOAD='{
      "metadata": {
        "source": "web",
        "campaign": "summer_sale",
        "updated": true,
        "notes": "Customer requested express shipping"
      }
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PAYLOAD"
    
    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/orders/${ORDER_ID}" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Order updated successfully"
    else
        print_result 1 "Failed to update order"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No order ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: List Orders
print_section "Test 7: List Orders"
echo "GET ${API_BASE}/orders?page=1&page_size=10"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/orders?page=1&page_size=10")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Orders listed successfully"
else
    print_result 1 "Failed to list orders"
fi

# Test 8: Get User Orders
print_section "Test 8: Get User Orders"
echo "GET ${API_BASE}/users/test_user_123/orders?limit=10&offset=0"

USER_ORDERS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/users/test_user_123/orders?limit=10&offset=0")
HTTP_CODE=$(echo "$USER_ORDERS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_ORDERS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(json_value "$RESPONSE_BODY" "count")
    print_result 0 "User orders retrieved successfully (Count: $COUNT)"
else
    print_result 1 "Failed to retrieve user orders"
fi

# Test 9: Search Orders
print_section "Test 9: Search Orders"
echo "GET ${API_BASE}/orders/search?query=test&limit=10"

SEARCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/orders/search?query=test&limit=10")
HTTP_CODE=$(echo "$SEARCH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SEARCH_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Orders searched successfully"
else
    print_result 1 "Failed to search orders"
fi

# Test 10: Get Order Statistics
print_section "Test 10: Get Order Statistics"
echo "GET ${API_BASE}/orders/statistics"

STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/orders/statistics")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Statistics retrieved successfully"
else
    print_result 1 "Failed to retrieve statistics"
fi

# Test 11: Complete Order
if [ -n "$ORDER_ID" ] && [ "$ORDER_ID" != "null" ]; then
    print_section "Test 11: Complete Order"
    echo "POST ${API_BASE}/orders/${ORDER_ID}/complete"
    COMPLETE_PAYLOAD='{
      "payment_confirmed": true,
      "transaction_id": "txn_test_12345"
    }'
    echo "Request Body:"
    pretty_json "$COMPLETE_PAYLOAD"
    
    COMPLETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/orders/${ORDER_ID}/complete" \
      -H "Content-Type: application/json" \
      -d "$COMPLETE_PAYLOAD")
    HTTP_CODE=$(echo "$COMPLETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$COMPLETE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Order completed successfully"
    else
        print_result 1 "Failed to complete order"
    fi
else
    echo -e "${YELLOW}Skipping Test 11: No order ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 12: Create Another Order for Cancel Test
print_section "Test 12: Create Order for Cancel Test"
echo "POST ${API_BASE}/orders"
CREATE_ORDER_PAYLOAD2='{
  "user_id": "test_user_123",
  "order_type": "purchase",
  "total_amount": 29.99,
  "currency": "USD",
  "items": [
    {
      "product_id": "prod_002",
      "name": "Premium Plan",
      "quantity": 1,
      "price": 29.99
    }
  ]
}'
echo "Request Body:"
pretty_json "$CREATE_ORDER_PAYLOAD2"

CREATE_RESPONSE2=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/orders" \
  -H "Content-Type: application/json" \
  -d "$CREATE_ORDER_PAYLOAD2")
HTTP_CODE=$(echo "$CREATE_RESPONSE2" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE2" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

ORDER_ID_2=""
if [ "$HTTP_CODE" = "200" ]; then
    # Extract order_id from nested order object
    if command -v jq &> /dev/null; then
        ORDER_ID_2=$(echo "$RESPONSE_BODY" | jq -r '.order.order_id')
    else
        ORDER_ID_2=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('order', {}).get('order_id', ''))")
    fi
    if [ -n "$ORDER_ID_2" ] && [ "$ORDER_ID_2" != "null" ]; then
        print_result 0 "Second order created successfully"
        echo -e "${YELLOW}Order ID: $ORDER_ID_2${NC}"
    else
        print_result 1 "Second order creation returned success but no order_id"
    fi
else
    print_result 1 "Failed to create second order"
fi

# Test 13: Cancel Order
if [ -n "$ORDER_ID_2" ] && [ "$ORDER_ID_2" != "null" ]; then
    print_section "Test 13: Cancel Order"
    echo "POST ${API_BASE}/orders/${ORDER_ID_2}/cancel"
    CANCEL_PAYLOAD='{
      "reason": "Customer requested cancellation"
    }'
    echo "Request Body:"
    pretty_json "$CANCEL_PAYLOAD"
    
    CANCEL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/orders/${ORDER_ID_2}/cancel" \
      -H "Content-Type: application/json" \
      -d "$CANCEL_PAYLOAD")
    HTTP_CODE=$(echo "$CANCEL_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CANCEL_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Order cancelled successfully"
    else
        print_result 1 "Failed to cancel order"
    fi
else
    echo -e "${YELLOW}Skipping Test 13: No order ID available for cancellation${NC}"
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
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
