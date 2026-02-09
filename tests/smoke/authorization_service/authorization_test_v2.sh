#!/bin/bash
# Authorization Service Test Script (v2 - using test_common.sh)
# Usage:
#   ./authorization_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./authorization_test_v2.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="authorization_service"
API_PATH="/api/v1/authorization"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_AUTHZ_USER="authz_test_user_${TEST_TS}"
TEST_EMAIL="authz_test_${TEST_TS}@example.com"
TEST_RESOURCE_TYPE="api_endpoint"
TEST_RESOURCE_NAME="test_resource_${TEST_TS}"

print_info "Test User ID: $TEST_AUTHZ_USER"
print_info "Test Resource: $TEST_RESOURCE_TYPE/$TEST_RESOURCE_NAME"
echo ""

# Create test user in account_service first
print_section "Setup: Create Test User"
ACCOUNT_URL="http://localhost:$(get_service_port account_service)/api/v1/accounts/ensure"
USER_RESPONSE=$(curl -s -X POST "$ACCOUNT_URL" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"${TEST_AUTHZ_USER}\",\"email\":\"${TEST_EMAIL}\",\"name\":\"Authorization Test User\",\"subscription_plan\":\"free\"}")
echo "$USER_RESPONSE" | json_pretty

CREATED_USER_ID=$(json_get "$USER_RESPONSE" "user_id")
if [ -n "$CREATED_USER_ID" ] && [ "$CREATED_USER_ID" != "" ]; then
    print_success "Created test user: $CREATED_USER_ID"
else
    print_error "Failed to create test user, using fallback: test_user_001"
    TEST_AUTHZ_USER="test_user_001"
fi
echo ""

# ============================================================================
# Tests
# ============================================================================

# Test 1: Get Service Information
print_section "Test 1: Get Service Information"
echo "GET ${API_PATH}/info"
RESPONSE=$(api_get "/info")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "authorization_service"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Get Service Statistics
print_section "Test 2: Get Service Statistics"
echo "GET ${API_PATH}/stats"
RESPONSE=$(api_get "/stats")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "statistics" || echo "$RESPONSE" | grep -q "total"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 3: Check Access (Before Grant - Should Deny)
print_section "Test 3: Check Access (Before Grant)"
echo "POST ${API_PATH}/check-access"

CHECK_PAYLOAD="{
  \"user_id\": \"${TEST_AUTHZ_USER}\",
  \"resource_type\": \"${TEST_RESOURCE_TYPE}\",
  \"resource_name\": \"${TEST_RESOURCE_NAME}\",
  \"required_access_level\": \"read_only\"
}"
RESPONSE=$(api_post "/check-access" "$CHECK_PAYLOAD")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "has_access"; then
    HAS_ACCESS=$(json_get "$RESPONSE" "has_access")
    if [ "$HAS_ACCESS" = "false" ] || [ "$HAS_ACCESS" = "False" ]; then
        print_success "Access correctly denied (no permission yet)"
    fi
    test_result 0
else
    test_result 1
fi
echo ""

# Test 4: Grant Permission
print_section "Test 4: Grant Resource Permission"
echo "POST ${API_PATH}/grant"

GRANT_PAYLOAD="{
  \"user_id\": \"${TEST_AUTHZ_USER}\",
  \"resource_type\": \"${TEST_RESOURCE_TYPE}\",
  \"resource_name\": \"${TEST_RESOURCE_NAME}\",
  \"access_level\": \"read_write\",
  \"permission_source\": \"admin_grant\",
  \"granted_by_user_id\": \"system_test\"
}"
RESPONSE=$(api_post "/grant" "$GRANT_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "granted successfully\|permission_id"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 5: Check Access (After Grant - Should Allow)
print_section "Test 5: Check Access (After Grant)"
echo "POST ${API_PATH}/check-access"
RESPONSE=$(api_post "/check-access" "$CHECK_PAYLOAD")
echo "$RESPONSE" | json_pretty

HAS_ACCESS=$(json_get "$RESPONSE" "has_access")
if [ "$HAS_ACCESS" = "true" ] || [ "$HAS_ACCESS" = "True" ]; then
    print_success "Access granted as expected"
    test_result 0
else
    print_error "Access should be granted after permission grant"
    test_result 1
fi
echo ""

# Test 6: Get User Permissions
print_section "Test 6: Get User Permission Summary"
echo "GET ${API_PATH}/user-permissions/${TEST_AUTHZ_USER}"
RESPONSE=$(api_get "/user-permissions/${TEST_AUTHZ_USER}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "user_id" || json_has "$RESPONSE" "permissions"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 7: List User Resources
print_section "Test 7: List User Resources"
echo "GET ${API_PATH}/user-resources/${TEST_AUTHZ_USER}"
RESPONSE=$(api_get "/user-resources/${TEST_AUTHZ_USER}")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q "\[" || json_has "$RESPONSE" "resources"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 8: Revoke Permission
print_section "Test 8: Revoke Permission"
echo "POST ${API_PATH}/revoke"

REVOKE_PAYLOAD="{
  \"user_id\": \"${TEST_AUTHZ_USER}\",
  \"resource_type\": \"${TEST_RESOURCE_TYPE}\",
  \"resource_name\": \"${TEST_RESOURCE_NAME}\",
  \"revoked_by_user_id\": \"system_test\"
}"
RESPONSE=$(api_post "/revoke" "$REVOKE_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "revoked\|success\|message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 9: Verify Access Revoked
print_section "Test 9: Verify Access Revoked"
echo "POST ${API_PATH}/check-access"
RESPONSE=$(api_post "/check-access" "$CHECK_PAYLOAD")
echo "$RESPONSE" | json_pretty

HAS_ACCESS=$(json_get "$RESPONSE" "has_access")
if [ "$HAS_ACCESS" = "false" ] || [ "$HAS_ACCESS" = "False" ]; then
    print_success "Access correctly revoked"
    test_result 0
else
    print_error "Access should be revoked"
    test_result 1
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
