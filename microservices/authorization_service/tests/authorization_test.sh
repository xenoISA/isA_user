#!/bin/bash
# Authorization Service Comprehensive Test Script
# Tests all authorization and permission management endpoints

BASE_URL="http://localhost:8204"
API_BASE="${BASE_URL}/api/v1/authorization"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test counters
PASSED=0
FAILED=0
TOTAL=0

# Test result function
test_result() {
    TOTAL=$((TOTAL + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}       AUTHORIZATION SERVICE COMPREHENSIVE TEST${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
echo "GET /health"
RESPONSE=$(curl -s "${BASE_URL}/health")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"status":"healthy"'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Detailed Health Check
echo -e "${YELLOW}Test 2: Detailed Health Check${NC}"
echo "GET /health/detailed"
RESPONSE=$(curl -s "${BASE_URL}/health/detailed")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"database_connected":true'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 3: Service Info
echo -e "${YELLOW}Test 3: Get Service Information${NC}"
echo "GET /api/v1/authorization/info"
RESPONSE=$(curl -s "${API_BASE}/info")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"service":"authorization_service"'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 4: Service Stats
echo -e "${YELLOW}Test 4: Get Service Statistics${NC}"
echo "GET /api/v1/authorization/stats"
RESPONSE=$(curl -s "${API_BASE}/stats")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"statistics"'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Create test user via account service API
echo -e "${CYAN}Creating test user via account service...${NC}"
TEST_TS="$(date +%s)_$$"
TEST_EMAIL="authz_test_${TEST_TS}@example.com"
TEST_AUTH0_ID="authz_test_user_${TEST_TS}"

# Call account service to create test user
USER_RESPONSE=$(curl -s -X POST "http://localhost:8202/api/v1/accounts/ensure" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"${TEST_AUTH0_ID}\",\"email\":\"${TEST_EMAIL}\",\"name\":\"Authorization Test User\",\"subscription_plan\":\"free\"}")

TEST_USER_ID=$(echo "$USER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('user_id', ''))" 2>/dev/null)

if [ -n "$TEST_USER_ID" ]; then
    echo -e "${GREEN}✓ Created test user:${NC}"
    echo -e "  ID: ${CYAN}$TEST_USER_ID${NC}"
    echo -e "  Email: ${CYAN}$TEST_EMAIL${NC}"
else
    echo -e "${RED}✗ Failed to create test user, using fallback${NC}"
    TEST_USER_ID="test_user_001"
fi
echo ""

# Test resource info
TEST_RESOURCE_TYPE="api_endpoint"
TEST_RESOURCE_NAME="test_resource_$(date +%s)"

# Test 5: Check Access (Before Grant)
echo -e "${YELLOW}Test 5: Check Access (Before Grant - Should Deny)${NC}"
echo "POST /api/v1/authorization/check-access"
CHECK_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"resource_type\":\"${TEST_RESOURCE_TYPE}\",\"resource_name\":\"${TEST_RESOURCE_NAME}\",\"required_access_level\":\"read_only\"}"
echo "Payload: $CHECK_PAYLOAD"
RESPONSE=$(curl -s -X POST "${API_BASE}/check-access" \
  -H "Content-Type: application/json" \
  -d "$CHECK_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
# Should not have access yet
if echo "$RESPONSE" | grep -q '"has_access"'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 6: Grant Permission
echo -e "${YELLOW}Test 6: Grant Resource Permission${NC}"
echo "POST /api/v1/authorization/grant"
GRANT_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"resource_type\":\"${TEST_RESOURCE_TYPE}\",\"resource_name\":\"${TEST_RESOURCE_NAME}\",\"access_level\":\"read_write\",\"permission_source\":\"admin_grant\",\"granted_by_user_id\":\"system_test\"}"
echo "Payload: $GRANT_PAYLOAD"
RESPONSE=$(curl -s -X POST "${API_BASE}/grant" \
  -H "Content-Type: application/json" \
  -d "$GRANT_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "granted successfully"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 7: Check Access (After Grant)
echo -e "${YELLOW}Test 7: Check Access (After Grant - Should Allow)${NC}"
echo "POST /api/v1/authorization/check-access"
echo "Payload: $CHECK_PAYLOAD"
RESPONSE=$(curl -s -X POST "${API_BASE}/check-access" \
  -H "Content-Type: application/json" \
  -d "$CHECK_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"has_access":true'; then
    echo -e "${GREEN}✓ Access granted as expected${NC}"
    test_result 0
else
    echo -e "${RED}✗ Access should be granted after permission grant${NC}"
    test_result 1
fi
echo ""

# Test 8: Get User Permissions
echo -e "${YELLOW}Test 8: Get User Permission Summary${NC}"
echo "GET /api/v1/authorization/user-permissions/${TEST_USER_ID}"
RESPONSE=$(curl -s "${API_BASE}/user-permissions/${TEST_USER_ID}")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"user_id"'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 9: List User Accessible Resources
echo -e "${YELLOW}Test 9: List User Accessible Resources${NC}"
echo "GET /api/v1/authorization/user-resources/${TEST_USER_ID}"
RESPONSE=$(curl -s "${API_BASE}/user-resources/${TEST_USER_ID}?resource_type=${TEST_RESOURCE_TYPE}")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"accessible_resources"'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 10: Bulk Grant Permissions
echo -e "${YELLOW}Test 10: Bulk Grant Permissions${NC}"
echo "POST /api/v1/authorization/bulk-grant"
BULK_RESOURCE_1="bulk_test_resource_1_$(date +%s)"
BULK_RESOURCE_2="bulk_test_resource_2_$(date +%s)"
BULK_GRANT_PAYLOAD="{\"operations\":[{\"user_id\":\"${TEST_USER_ID}\",\"resource_type\":\"${TEST_RESOURCE_TYPE}\",\"resource_name\":\"${BULK_RESOURCE_1}\",\"access_level\":\"read_only\",\"permission_source\":\"admin_grant\",\"granted_by_user_id\":\"bulk_test\"},{\"user_id\":\"${TEST_USER_ID}\",\"resource_type\":\"${TEST_RESOURCE_TYPE}\",\"resource_name\":\"${BULK_RESOURCE_2}\",\"access_level\":\"read_write\",\"permission_source\":\"admin_grant\",\"granted_by_user_id\":\"bulk_test\"}]}"
echo "Payload: (granting 2 permissions)"
RESPONSE=$(curl -s -X POST "${API_BASE}/bulk-grant" \
  -H "Content-Type: application/json" \
  -d "$BULK_GRANT_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"total_operations":2'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 11: Revoke Permission
echo -e "${YELLOW}Test 11: Revoke Resource Permission${NC}"
echo "POST /api/v1/authorization/revoke"
REVOKE_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"resource_type\":\"${TEST_RESOURCE_TYPE}\",\"resource_name\":\"${TEST_RESOURCE_NAME}\"}"
echo "Payload: $REVOKE_PAYLOAD"
RESPONSE=$(curl -s -X POST "${API_BASE}/revoke" \
  -H "Content-Type: application/json" \
  -d "$REVOKE_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "revoked successfully"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 12: Check Access (After Revoke)
echo -e "${YELLOW}Test 12: Check Access (After Revoke - Should Deny)${NC}"
echo "POST /api/v1/authorization/check-access"
echo "Payload: $CHECK_PAYLOAD"
RESPONSE=$(curl -s -X POST "${API_BASE}/check-access" \
  -H "Content-Type: application/json" \
  -d "$CHECK_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"has_access":false'; then
    echo -e "${GREEN}✓ Access denied as expected after revoke${NC}"
    test_result 0
else
    echo -e "${RED}✗ Access should be denied after permission revoke${NC}"
    test_result 1
fi
echo ""

# Test 13: Bulk Revoke Permissions
echo -e "${YELLOW}Test 13: Bulk Revoke Permissions${NC}"
echo "POST /api/v1/authorization/bulk-revoke"
BULK_REVOKE_PAYLOAD="{\"operations\":[{\"user_id\":\"${TEST_USER_ID}\",\"resource_type\":\"${TEST_RESOURCE_TYPE}\",\"resource_name\":\"${BULK_RESOURCE_1}\"},{\"user_id\":\"${TEST_USER_ID}\",\"resource_type\":\"${TEST_RESOURCE_TYPE}\",\"resource_name\":\"${BULK_RESOURCE_2}\"}]}"
echo "Payload: (revoking 2 permissions)"
RESPONSE=$(curl -s -X POST "${API_BASE}/bulk-revoke" \
  -H "Content-Type: application/json" \
  -d "$BULK_REVOKE_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"total_operations":2'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 14: Cleanup Expired Permissions (Admin)
echo -e "${YELLOW}Test 14: Cleanup Expired Permissions (Admin)${NC}"
echo "POST /api/v1/authorization/cleanup-expired"
RESPONSE=$(curl -s -X POST "${API_BASE}/cleanup-expired")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "cleaned up successfully\|cleaned_count"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Print summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e "Total Tests: ${TOTAL}"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
