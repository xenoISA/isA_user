#!/bin/bash

# Wallet Service CRUD Tests
# Tests wallet creation, balance operations, transactions, and statistics
#
# Usage:
#   Local:       ./wallet_test.sh
#   Kubernetes:  ./wallet_test.sh k8s
#   Custom URL:  WALLET_URL=http://custom:8208 AUTH_URL=http://custom:8201 ./wallet_test.sh

# Determine test environment
TEST_ENV="${1:-local}"

if [ "$TEST_ENV" = "k8s" ] || [ "$TEST_ENV" = "kubernetes" ]; then
    # Kubernetes environment - use kubectl port-forward
    echo "🔧 Testing in Kubernetes environment (requires kubectl port-forward)"
    echo "📝 Run these commands in separate terminals:"
    echo "   kubectl port-forward -n isa-cloud-staging svc/wallet 8208:8208"
    echo "   kubectl port-forward -n isa-cloud-staging svc/auth 8201:8201"
    echo ""
    read -p "Press Enter when port-forwards are ready..."
    BASE_URL="http://localhost"
    AUTH_URL="http://localhost/api/v1/auth"
elif [ -n "$WALLET_URL" ]; then
    # Custom URLs via environment variables
    BASE_URL="${WALLET_URL}"
    AUTH_URL="${AUTH_URL:-http://localhost/api/v1/auth}"
else
    # Local development environment
    BASE_URL="http://localhost"
    AUTH_URL="http://localhost/api/v1/auth"
fi

API_BASE="${BASE_URL}/api/v1"

echo "🎯 Test Configuration:"
echo "   Wallet Service: ${BASE_URL}"
echo "   Auth Service:   ${AUTH_URL}"
echo ""

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
echo "Wallet Service CRUD Tests"
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

# Test 0: Generate test token from auth service
print_section "Test 0: Generate Test Token from Auth Service"
echo "POST ${AUTH_URL}/dev-token"
TOKEN_PAYLOAD='{
  "user_id": "test_wallet_user_123",
  "email": "wallettest@example.com",
  "organization_id": "org_test_123",
  "role": "user",
  "expires_in": 3600
}'
echo "Request Body:"
echo "$TOKEN_PAYLOAD" | jq '.'

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_URL}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$TOKEN_PAYLOAD")
HTTP_CODE=$(echo "$TOKEN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

JWT_TOKEN=""
if [ "$HTTP_CODE" = "200" ]; then
    JWT_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.token')
    if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
        print_result 0 "Test token generated successfully"
        echo -e "${YELLOW}Token (first 50 chars): ${JWT_TOKEN:0:50}...${NC}"
    else
        print_result 1 "Token generation failed"
        exit 1
    fi
else
    print_result 1 "Failed to generate test token"
    exit 1
fi

USER_ID="test_wallet_user_123"

# Test 1: Create Wallet or Get Existing
print_section "Test 2: Create Wallet or Get Existing"
WALLET_ID=""
echo "POST ${API_BASE}/wallets"
CREATE_PAYLOAD="{
  \"user_id\": \"$USER_ID\",
  \"wallet_type\": \"fiat\",
  \"initial_balance\": 1000.00,
  \"currency\": \"CREDIT\",
  \"metadata\": {
    \"purpose\": \"testing\",
    \"environment\": \"test\"
  }
}"
echo "Request Body:"
echo "$CREATE_PAYLOAD" | jq '.'

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/wallets" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
    if [ "$SUCCESS" = "true" ]; then
        WALLET_ID=$(echo "$RESPONSE_BODY" | jq -r '.wallet_id')
        print_result 0 "Wallet created successfully"
        echo -e "${YELLOW}Wallet ID: ${WALLET_ID}${NC}"
    else
        # Wallet creation failed (probably already exists)
        MESSAGE=$(echo "$RESPONSE_BODY" | jq -r '.message')
        print_result 1 "Wallet creation response: $MESSAGE (will fetch existing wallet)"
    fi
elif [ "$HTTP_CODE" = "400" ]; then
    # Wallet already exists - fetch it from user wallets
    print_result 0 "Wallet already exists, fetching existing wallet"
fi

# If we don't have wallet_id yet, fetch from user wallets
if [ -z "$WALLET_ID" ] || [ "$WALLET_ID" = "null" ]; then
    echo "Fetching existing wallet from user wallets..."
    USER_WALLETS_FETCH=$(curl -s -X GET "${API_BASE}/wallets?user_id=${USER_ID}")
    WALLET_ID=$(echo "$USER_WALLETS_FETCH" | jq -r '.wallets[0].wallet_id')
    if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
        echo -e "${YELLOW}Found existing Wallet ID: ${WALLET_ID}${NC}"
    else
        print_result 1 "Failed to get wallet ID from user wallets"
        echo -e "${RED}Cannot continue tests without wallet ID${NC}"
    fi
fi

# Test 2: Get Wallet Details
if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
    print_section "Test 3: Get Wallet Details"
    echo "GET ${API_BASE}/wallets/${WALLET_ID}"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/wallets/${WALLET_ID}")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(echo "$RESPONSE_BODY" | jq -r '.wallet_id')
        if [ "$RETRIEVED_ID" = "$WALLET_ID" ]; then
            print_result 0 "Wallet details retrieved successfully"
        else
            print_result 1 "Wallet ID mismatch in retrieved data"
        fi
    else
        print_result 1 "Failed to get wallet details"
    fi
else
    echo -e "${RED}ERROR: No wallet ID available for Test 3${NC}"
    print_result 1 "Cannot test without wallet ID"
fi

# Test 3: Get User Wallets
print_section "Test 4: Get User Wallets"
echo "GET ${API_BASE}/wallets?user_id=${USER_ID}"

USER_WALLETS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/wallets?user_id=${USER_ID}")
HTTP_CODE=$(echo "$USER_WALLETS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_WALLETS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(echo "$RESPONSE_BODY" | jq -r '.count')
    print_result 0 "User wallets retrieved successfully (count: $COUNT)"
else
    print_result 1 "Failed to retrieve user wallets"
fi

# Test 4: Get Wallet Balance
if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
    print_section "Test 5: Get Wallet Balance"
    echo "GET ${API_BASE}/wallets/${WALLET_ID}/balance"

    BALANCE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/wallets/${WALLET_ID}/balance")
    HTTP_CODE=$(echo "$BALANCE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$BALANCE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
        if [ "$SUCCESS" = "true" ]; then
            BALANCE=$(echo "$RESPONSE_BODY" | jq -r '.balance')
            print_result 0 "Wallet balance retrieved successfully (balance: $BALANCE)"
        else
            print_result 1 "Failed to get wallet balance"
        fi
    else
        print_result 1 "Failed to retrieve wallet balance"
    fi
else
    echo -e "${RED}ERROR: No wallet ID available for Test 5${NC}"
    print_result 1 "Cannot test without wallet ID"
fi

# Test 5: Deposit to Wallet
if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
    print_section "Test 6: Deposit to Wallet"
    echo "POST ${API_BASE}/wallets/${WALLET_ID}/deposit"
    DEPOSIT_PAYLOAD='{
      "amount": 500.00,
      "description": "Test deposit",
      "reference_id": "test_deposit_001",
      "metadata": {
        "source": "test_suite"
      }
    }'
    echo "Request Body:"
    echo "$DEPOSIT_PAYLOAD" | jq '.'

    DEPOSIT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/wallets/${WALLET_ID}/deposit" \
      -H "Content-Type: application/json" \
      -d "$DEPOSIT_PAYLOAD")
    HTTP_CODE=$(echo "$DEPOSIT_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DEPOSIT_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
        if [ "$SUCCESS" = "true" ]; then
            NEW_BALANCE=$(echo "$RESPONSE_BODY" | jq -r '.balance')
            TRANSACTION_ID=$(echo "$RESPONSE_BODY" | jq -r '.transaction_id')
            print_result 0 "Deposit successful (new balance: $NEW_BALANCE)"
            echo -e "${YELLOW}Transaction ID: ${TRANSACTION_ID}${NC}"
        else
            print_result 1 "Deposit failed"
        fi
    else
        print_result 1 "Failed to deposit"
    fi
else
    echo -e "${RED}ERROR: No wallet ID available for Test 6${NC}"
    print_result 1 "Cannot test without wallet ID"
fi

# Test 6: Consume from Wallet
if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
    print_section "Test 7: Consume from Wallet"
    echo "POST ${API_BASE}/wallets/${WALLET_ID}/consume"
    CONSUME_PAYLOAD='{
      "amount": 100.00,
      "description": "Test consumption",
      "metadata": {
        "purpose": "test_usage"
      }
    }'
    echo "Request Body:"
    echo "$CONSUME_PAYLOAD" | jq '.'

    CONSUME_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/wallets/${WALLET_ID}/consume" \
      -H "Content-Type: application/json" \
      -d "$CONSUME_PAYLOAD")
    HTTP_CODE=$(echo "$CONSUME_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CONSUME_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
        if [ "$SUCCESS" = "true" ]; then
            NEW_BALANCE=$(echo "$RESPONSE_BODY" | jq -r '.balance')
            print_result 0 "Consumption successful (new balance: $NEW_BALANCE)"
        else
            print_result 1 "Consumption failed"
        fi
    else
        print_result 1 "Failed to consume"
    fi
else
    echo -e "${RED}ERROR: No wallet ID available for Test 7${NC}"
    print_result 1 "Cannot test without wallet ID"
fi

# Test 7: Withdraw from Wallet
if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
    print_section "Test 8: Withdraw from Wallet"
    echo "POST ${API_BASE}/wallets/${WALLET_ID}/withdraw"
    WITHDRAW_PAYLOAD='{
      "amount": 50.00,
      "description": "Test withdrawal",
      "destination": "test_bank_account",
      "metadata": {
        "purpose": "test_withdrawal"
      }
    }'
    echo "Request Body:"
    echo "$WITHDRAW_PAYLOAD" | jq '.'

    WITHDRAW_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/wallets/${WALLET_ID}/withdraw" \
      -H "Content-Type: application/json" \
      -d "$WITHDRAW_PAYLOAD")
    HTTP_CODE=$(echo "$WITHDRAW_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$WITHDRAW_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
        if [ "$SUCCESS" = "true" ]; then
            NEW_BALANCE=$(echo "$RESPONSE_BODY" | jq -r '.balance')
            print_result 0 "Withdrawal successful (new balance: $NEW_BALANCE)"
        else
            print_result 1 "Withdrawal failed"
        fi
    else
        print_result 1 "Failed to withdraw"
    fi
else
    echo -e "${RED}ERROR: No wallet ID available for Test 8${NC}"
    print_result 1 "Cannot test without wallet ID"
fi

# Test 8: Get Wallet Transactions
if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
    print_section "Test 9: Get Wallet Transactions"
    echo "GET ${API_BASE}/wallets/${WALLET_ID}/transactions"

    TRANSACTIONS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/wallets/${WALLET_ID}/transactions?limit=10")
    HTTP_CODE=$(echo "$TRANSACTIONS_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$TRANSACTIONS_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        COUNT=$(echo "$RESPONSE_BODY" | jq -r '.count')
        print_result 0 "Wallet transactions retrieved successfully (count: $COUNT)"
    else
        print_result 1 "Failed to retrieve wallet transactions"
    fi
else
    echo -e "${RED}ERROR: No wallet ID available for Test 9${NC}"
    print_result 1 "Cannot test without wallet ID"
fi

# Test 9: Get Wallet Statistics
if [ -n "$WALLET_ID" ] && [ "$WALLET_ID" != "null" ]; then
    print_section "Test 11: Get Wallet Statistics"
    echo "GET ${API_BASE}/wallets/${WALLET_ID}/statistics"

    STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/wallets/${WALLET_ID}/statistics")
    HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Wallet statistics retrieved successfully"
    else
        print_result 1 "Failed to retrieve wallet statistics"
    fi
else
    echo -e "${RED}ERROR: No wallet ID available for Test 11${NC}"
    print_result 1 "Cannot test without wallet ID"
fi

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
