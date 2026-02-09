#!/bin/bash
# Auth Service JWT Test Script (v2 - using test_common.sh)
# Note: Auth service is special - it GENERATES tokens, so most endpoints don't need JWT
# Usage:
#   ./jwt_auth_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./jwt_auth_test_v2.sh  # Gateway mode

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="auth_service"
API_PATH="/api/v1/auth"

# Auth service doesn't need JWT for its own endpoints
# Override to direct mode
TEST_MODE="direct"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_AUTH_USER="test_auth_user_${TEST_TS}"

print_info "Test User ID: $TEST_AUTH_USER"
echo ""

# ============================================================================
# Tests
# ============================================================================

# Test 1: Get Auth Service Info
print_section "Test 1: Get Auth Service Info"
echo "GET ${API_PATH}/info"
RESPONSE=$(api_get "/info")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "service" || json_has "$RESPONSE" "version"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Generate Development Token
print_section "Test 2: Generate Development Token"
echo "POST ${API_PATH}/dev-token"

DEV_TOKEN_PAYLOAD="{
  \"user_id\": \"${TEST_AUTH_USER}\",
  \"email\": \"${TEST_AUTH_USER}@example.com\",
  \"expires_in\": 3600
}"
RESPONSE=$(api_post "/dev-token" "$DEV_TOKEN_PAYLOAD")
echo "$RESPONSE" | json_pretty

JWT_TOKEN=$(json_get "$RESPONSE" "token")
if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ] && [ "$JWT_TOKEN" != "" ]; then
    print_success "Development token generated"
    echo "Token (first 50 chars): ${JWT_TOKEN:0:50}..."
    test_result 0
else
    print_error "Failed to generate token"
    test_result 1
fi
echo ""

# Test 3: Verify JWT Token (with provider=local)
if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "" ]; then
    print_section "Test 3: Verify JWT Token (provider=local)"
    echo "POST ${API_PATH}/verify-token"

    VERIFY_PAYLOAD="{\"token\": \"$JWT_TOKEN\", \"provider\": \"local\"}"
    RESPONSE=$(api_post "/verify-token" "$VERIFY_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    IS_VALID=$(json_get "$RESPONSE" "valid")
    if [ "$IS_VALID" = "true" ] || [ "$IS_VALID" = "True" ]; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 3: SKIPPED - No token available"
fi
echo ""

# Test 4: Verify JWT Token (auto-detect provider)
if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "" ]; then
    print_section "Test 4: Verify JWT Token (auto-detect)"
    echo "POST ${API_PATH}/verify-token"

    VERIFY_PAYLOAD="{\"token\": \"$JWT_TOKEN\"}"
    RESPONSE=$(api_post "/verify-token" "$VERIFY_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    IS_VALID=$(json_get "$RESPONSE" "valid")
    if [ "$IS_VALID" = "true" ] || [ "$IS_VALID" = "True" ]; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 4: SKIPPED - No token available"
fi
echo ""

# Test 5: Get User Info from Token
if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "" ]; then
    print_section "Test 5: Get User Info from Token"
    echo "GET ${API_PATH}/user-info?token=..."

    RESPONSE=$(api_get "/user-info?token=${JWT_TOKEN}")
    echo "$RESPONSE" | json_pretty

    USER_ID=$(json_get "$RESPONSE" "user_id")
    if [ -n "$USER_ID" ] && [ "$USER_ID" != "null" ] && [ "$USER_ID" != "" ]; then
        print_success "User ID: $USER_ID"
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 5: SKIPPED - No token available"
fi
echo ""

# Test 6: Verify Invalid Token
print_section "Test 6: Verify Invalid Token (should fail gracefully)"
echo "POST ${API_PATH}/verify-token"

INVALID_PAYLOAD='{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token", "provider": "local"}'
RESPONSE=$(api_post "/verify-token" "$INVALID_PAYLOAD")
echo "$RESPONSE" | json_pretty

IS_VALID=$(json_get "$RESPONSE" "valid")
if [ "$IS_VALID" = "false" ] || [ "$IS_VALID" = "False" ]; then
    print_success "Invalid token rejected correctly"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 7: Generate Token with Custom Expiration
print_section "Test 7: Generate Token with Custom Expiration"
echo "POST ${API_PATH}/dev-token"

CUSTOM_PAYLOAD="{
  \"user_id\": \"custom_user_${TEST_TS}\",
  \"email\": \"custom@example.com\",
  \"expires_in\": 7200
}"
RESPONSE=$(api_post "/dev-token" "$CUSTOM_PAYLOAD")
echo "$RESPONSE" | json_pretty

EXPIRES_IN=$(json_get "$RESPONSE" "expires_in")
if [ "$EXPIRES_IN" = "7200" ]; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 8: Generate Token Pair (Access + Refresh)
print_section "Test 8: Generate Token Pair (Access + Refresh)"
echo "POST ${API_PATH}/token-pair"

TOKEN_PAIR_PAYLOAD="{
  \"user_id\": \"pair_user_${TEST_TS}\",
  \"email\": \"pairuser@example.com\",
  \"organization_id\": \"org_123\",
  \"permissions\": [\"read:data\", \"write:data\"],
  \"metadata\": {\"role\": \"admin\"}
}"
RESPONSE=$(api_post "/token-pair" "$TOKEN_PAIR_PAYLOAD")
echo "$RESPONSE" | json_pretty

ACCESS_TOKEN=$(json_get "$RESPONSE" "access_token")
REFRESH_TOKEN=$(json_get "$RESPONSE" "refresh_token")

if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ] && [ -n "$REFRESH_TOKEN" ] && [ "$REFRESH_TOKEN" != "null" ]; then
    print_success "Access Token (first 50 chars): ${ACCESS_TOKEN:0:50}..."
    print_success "Refresh Token (first 50 chars): ${REFRESH_TOKEN:0:50}..."
    test_result 0
else
    test_result 1
fi
echo ""

# Test 9: Verify Custom JWT Access Token
if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
    print_section "Test 9: Verify Custom JWT Access Token"
    echo "POST ${API_PATH}/verify-token"

    VERIFY_PAYLOAD="{\"token\": \"$ACCESS_TOKEN\"}"
    RESPONSE=$(api_post "/verify-token" "$VERIFY_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    IS_VALID=$(json_get "$RESPONSE" "valid")
    PROVIDER=$(json_get "$RESPONSE" "provider")
    if [ "$IS_VALID" = "true" ] || [ "$IS_VALID" = "True" ]; then
        print_success "Provider: $PROVIDER"
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 9: SKIPPED - No access token available"
fi
echo ""

# Test 10: Refresh Access Token
if [ -n "$REFRESH_TOKEN" ] && [ "$REFRESH_TOKEN" != "null" ]; then
    print_section "Test 10: Refresh Access Token"
    echo "POST ${API_PATH}/refresh"

    REFRESH_PAYLOAD="{\"refresh_token\": \"$REFRESH_TOKEN\"}"
    RESPONSE=$(api_post "/refresh" "$REFRESH_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    NEW_ACCESS_TOKEN=$(json_get "$RESPONSE" "access_token")
    if [ -n "$NEW_ACCESS_TOKEN" ] && [ "$NEW_ACCESS_TOKEN" != "null" ]; then
        print_success "New Access Token (first 50 chars): ${NEW_ACCESS_TOKEN:0:50}..."
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 10: SKIPPED - No refresh token available"
fi
echo ""

# Test 11: Get Auth Stats
print_section "Test 11: Get Auth Service Statistics"
echo "GET ${API_PATH}/stats"
RESPONSE=$(api_get "/stats")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "total_tokens" || json_has "$RESPONSE" "tokens_generated" || echo "$RESPONSE" | grep -q "token"; then
    test_result 0
else
    test_result 1
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
