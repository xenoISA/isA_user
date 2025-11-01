#!/bin/bash

# JWT Authentication Testing Script
# Tests JWT token generation, verification, and user info extraction

BASE_URL="http://localhost:8201"
API_BASE="${BASE_URL}/api/v1/auth"

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
echo "JWT Authentication Service Tests"
echo "======================================================================"
echo ""

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN} PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED} FAILED${NC}: $2"
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
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Health check successful"
else
    print_result 1 "Health check failed"
fi

# Test 2: Get Auth Service Info
print_section "Test 2: Get Auth Service Info"
echo "GET ${API_BASE}/info"
INFO_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/info")
HTTP_CODE=$(echo "$INFO_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INFO_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Auth service info retrieved"
else
    print_result 1 "Failed to get auth service info"
fi

# Test 3: Generate Development Token
print_section "Test 3: Generate Development Token"
echo "POST ${API_BASE}/dev-token"
DEV_TOKEN_PAYLOAD='{
  "user_id": "test_user_123",
  "email": "testuser@example.com",
  "expires_in": 3600
}'
echo "Request Body:"
echo "$DEV_TOKEN_PAYLOAD" | jq '.'

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$DEV_TOKEN_PAYLOAD")
HTTP_CODE=$(echo "$TOKEN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

JWT_TOKEN=""
if [ "$HTTP_CODE" = "200" ]; then
    JWT_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.token')
    if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
        print_result 0 "Development token generated successfully"
        echo -e "${YELLOW}Token (first 50 chars): ${JWT_TOKEN:0:50}...${NC}"
    else
        print_result 1 "Token generation returned success but no token found"
    fi
else
    print_result 1 "Failed to generate development token"
fi

# Test 4: Verify JWT Token (with provider=local)
if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
    print_section "Test 4: Verify JWT Token (provider=local)"
    echo "POST ${API_BASE}/verify-token"
    VERIFY_PAYLOAD="{
  \"token\": \"$JWT_TOKEN\",
  \"provider\": \"local\"
}"
    echo "Request Body:"
    echo "$VERIFY_PAYLOAD" | jq '.'

    VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/verify-token" \
      -H "Content-Type: application/json" \
      -d "$VERIFY_PAYLOAD")
    HTTP_CODE=$(echo "$VERIFY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$VERIFY_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
    if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "true" ]; then
        print_result 0 "JWT token verified successfully (Issue #1 FIX)"
    else
        print_result 1 "JWT token verification failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 4: No token available${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: Verify JWT Token (auto-detect provider)
if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
    print_section "Test 5: Verify JWT Token (auto-detect provider)"
    echo "POST ${API_BASE}/verify-token"
    VERIFY_PAYLOAD="{
  \"token\": \"$JWT_TOKEN\"
}"
    echo "Request Body:"
    echo "$VERIFY_PAYLOAD" | jq '.'

    VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/verify-token" \
      -H "Content-Type: application/json" \
      -d "$VERIFY_PAYLOAD")
    HTTP_CODE=$(echo "$VERIFY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$VERIFY_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
    if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "true" ]; then
        print_result 0 "JWT token verified with auto-detect"
    else
        print_result 1 "JWT token verification with auto-detect failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 5: No token available${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Get User Info from Token
if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
    print_section "Test 6: Get User Info from Token"
    echo "GET ${API_BASE}/user-info?token=..."

    USER_INFO_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/user-info?token=${JWT_TOKEN}")
    HTTP_CODE=$(echo "$USER_INFO_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$USER_INFO_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        USER_ID=$(echo "$RESPONSE_BODY" | jq -r '.user_id')
        EMAIL=$(echo "$RESPONSE_BODY" | jq -r '.email')
        if [ -n "$USER_ID" ] && [ "$USER_ID" != "null" ]; then
            print_result 0 "User info extracted successfully (Issue #2 FIX)"
            echo -e "${YELLOW}User ID: $USER_ID${NC}"
            echo -e "${YELLOW}Email: $EMAIL${NC}"
        else
            print_result 1 "User info extraction returned 200 but no user_id"
        fi
    else
        print_result 1 "Failed to extract user info from token"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No token available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Verify Invalid Token
print_section "Test 7: Verify Invalid Token (should fail gracefully)"
echo "POST ${API_BASE}/verify-token"
INVALID_PAYLOAD='{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token",
  "provider": "local"
}'
echo "Request Body:"
echo "$INVALID_PAYLOAD" | jq '.'

INVALID_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/verify-token" \
  -H "Content-Type: application/json" \
  -d "$INVALID_PAYLOAD")
HTTP_CODE=$(echo "$INVALID_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INVALID_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "false" ]; then
    print_result 0 "Invalid token rejected correctly"
else
    print_result 1 "Invalid token handling failed"
fi

# Test 8: Generate Token with Custom Expiration
print_section "Test 8: Generate Token with Custom Expiration"
echo "POST ${API_BASE}/dev-token"
CUSTOM_TOKEN_PAYLOAD='{
  "user_id": "custom_user_456",
  "email": "custom@example.com",
  "expires_in": 7200
}'
echo "Request Body:"
echo "$CUSTOM_TOKEN_PAYLOAD" | jq '.'

CUSTOM_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$CUSTOM_TOKEN_PAYLOAD")
HTTP_CODE=$(echo "$CUSTOM_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CUSTOM_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    EXPIRES_IN=$(echo "$RESPONSE_BODY" | jq -r '.expires_in')
    if [ "$EXPIRES_IN" = "7200" ]; then
        print_result 0 "Custom expiration token generated"
    else
        print_result 1 "Custom expiration not applied correctly"
    fi
else
    print_result 1 "Failed to generate custom expiration token"
fi

# Test 9: Generate Token Pair (New Custom JWT Feature)
print_section "Test 9: Generate Token Pair (Access + Refresh Tokens)"
echo "POST ${API_BASE}/token-pair"
TOKEN_PAIR_PAYLOAD='{
  "user_id": "pair_user_789",
  "email": "pairuser@example.com",
  "organization_id": "org_123",
  "permissions": ["read:data", "write:data"],
  "metadata": {
    "role": "admin",
    "department": "engineering"
  }
}'
echo "Request Body:"
echo "$TOKEN_PAIR_PAYLOAD" | jq '.'

PAIR_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/token-pair" \
  -H "Content-Type: application/json" \
  -d "$TOKEN_PAIR_PAYLOAD")
HTTP_CODE=$(echo "$PAIR_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PAIR_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

ACCESS_TOKEN=""
REFRESH_TOKEN=""
if [ "$HTTP_CODE" = "200" ]; then
    ACCESS_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.access_token')
    REFRESH_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.refresh_token')
    if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ] && [ -n "$REFRESH_TOKEN" ] && [ "$REFRESH_TOKEN" != "null" ]; then
        print_result 0 "Token pair generated successfully (Custom JWT)"
        echo -e "${YELLOW}Access Token (first 50 chars): ${ACCESS_TOKEN:0:50}...${NC}"
        echo -e "${YELLOW}Refresh Token (first 50 chars): ${REFRESH_TOKEN:0:50}...${NC}"
    else
        print_result 1 "Token pair generation returned success but tokens missing"
    fi
else
    print_result 1 "Failed to generate token pair"
fi

# Test 10: Verify Custom JWT Access Token
if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
    print_section "Test 10: Verify Custom JWT Access Token"
    echo "POST ${API_BASE}/verify-token"
    VERIFY_CUSTOM_PAYLOAD="{
  \"token\": \"$ACCESS_TOKEN\"
}"
    echo "Request Body:"
    echo "$VERIFY_CUSTOM_PAYLOAD" | jq '.'

    VERIFY_CUSTOM_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/verify-token" \
      -H "Content-Type: application/json" \
      -d "$VERIFY_CUSTOM_PAYLOAD")
    HTTP_CODE=$(echo "$VERIFY_CUSTOM_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$VERIFY_CUSTOM_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
    PROVIDER=$(echo "$RESPONSE_BODY" | jq -r '.provider')
    if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "true" ]; then
        print_result 0 "Custom JWT access token verified (Provider: $PROVIDER)"
        # Check for custom claims
        ORG_ID=$(echo "$RESPONSE_BODY" | jq -r '.organization_id')
        PERMS=$(echo "$RESPONSE_BODY" | jq -r '.permissions')
        echo -e "${YELLOW}Organization ID: $ORG_ID${NC}"
        echo -e "${YELLOW}Permissions: $PERMS${NC}"
    else
        print_result 1 "Custom JWT access token verification failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 10: No access token available${NC}"
    ((TESTS_FAILED++))
fi

# Test 11: Refresh Access Token
if [ -n "$REFRESH_TOKEN" ] && [ "$REFRESH_TOKEN" != "null" ]; then
    print_section "Test 11: Refresh Access Token (New Feature)"
    echo "POST ${API_BASE}/refresh"
    REFRESH_PAYLOAD="{
  \"refresh_token\": \"$REFRESH_TOKEN\"
}"
    echo "Request Body:"
    echo "$REFRESH_PAYLOAD" | jq '.'

    REFRESH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/refresh" \
      -H "Content-Type: application/json" \
      -d "$REFRESH_PAYLOAD")
    HTTP_CODE=$(echo "$REFRESH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$REFRESH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    NEW_ACCESS_TOKEN=""
    if [ "$HTTP_CODE" = "200" ]; then
        NEW_ACCESS_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.access_token')
        if [ -n "$NEW_ACCESS_TOKEN" ] && [ "$NEW_ACCESS_TOKEN" != "null" ]; then
            print_result 0 "Access token refreshed successfully"
            echo -e "${YELLOW}New Access Token (first 50 chars): ${NEW_ACCESS_TOKEN:0:50}...${NC}"
        else
            print_result 1 "Token refresh returned success but no new token"
        fi
    else
        print_result 1 "Failed to refresh access token"
    fi

    # Test 11.1: Verify the new refreshed token works
    if [ -n "$NEW_ACCESS_TOKEN" ] && [ "$NEW_ACCESS_TOKEN" != "null" ]; then
        print_section "Test 11.1: Verify Refreshed Access Token"
        echo "POST ${API_BASE}/verify-token"
        VERIFY_REFRESHED_PAYLOAD="{
  \"token\": \"$NEW_ACCESS_TOKEN\"
}"

        VERIFY_REFRESHED_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/verify-token" \
          -H "Content-Type: application/json" \
          -d "$VERIFY_REFRESHED_PAYLOAD")
        HTTP_CODE=$(echo "$VERIFY_REFRESHED_RESPONSE" | tail -n1)
        RESPONSE_BODY=$(echo "$VERIFY_REFRESHED_RESPONSE" | sed '$d')

        echo "Response:"
        echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
        echo "HTTP Status: $HTTP_CODE"

        IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
        if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "true" ]; then
            print_result 0 "Refreshed access token verified successfully"
        else
            print_result 1 "Refreshed access token verification failed"
        fi
    fi
else
    echo -e "${YELLOW}Skipping Test 11: No refresh token available${NC}"
    ((TESTS_FAILED++))
fi

# Test 12: Get User Info from Custom JWT Token
if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
    print_section "Test 12: Get User Info from Custom JWT Token"
    echo "GET ${API_BASE}/user-info?token=..."

    CUSTOM_USER_INFO_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/user-info?token=${ACCESS_TOKEN}")
    HTTP_CODE=$(echo "$CUSTOM_USER_INFO_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CUSTOM_USER_INFO_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        USER_ID=$(echo "$RESPONSE_BODY" | jq -r '.user_id')
        EMAIL=$(echo "$RESPONSE_BODY" | jq -r '.email')
        ORG_ID=$(echo "$RESPONSE_BODY" | jq -r '.organization_id')
        PERMS=$(echo "$RESPONSE_BODY" | jq -r '.permissions')
        if [ -n "$USER_ID" ] && [ "$USER_ID" != "null" ]; then
            print_result 0 "User info with custom claims extracted successfully"
            echo -e "${YELLOW}User ID: $USER_ID${NC}"
            echo -e "${YELLOW}Email: $EMAIL${NC}"
            echo -e "${YELLOW}Organization ID: $ORG_ID${NC}"
            echo -e "${YELLOW}Permissions: $PERMS${NC}"
        else
            print_result 1 "User info extraction returned 200 but no user_id"
        fi
    else
        print_result 1 "Failed to extract user info from custom JWT token"
    fi
else
    echo -e "${YELLOW}Skipping Test 12: No custom access token available${NC}"
    ((TESTS_FAILED++))
fi

# Test 13: Get Auth Stats
print_section "Test 13: Get Auth Service Statistics"
echo "GET ${API_BASE}/stats"
STATS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/stats")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Auth service statistics retrieved"
else
    print_result 1 "Failed to get auth service statistics"
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
    echo -e "${GREEN}All tests passed! ${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
