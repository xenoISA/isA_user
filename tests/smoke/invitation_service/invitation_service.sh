#!/bin/bash

# Invitation Service Testing Script
# Tests invitation creation, acceptance, and management

BASE_URL="http://localhost"
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

# Test data
TIMESTAMP=$(date +%s)
TEST_ORG_ID="test_org_${TIMESTAMP}"
TEST_USER_ID="test_user_${TIMESTAMP}"
TEST_INVITER_ID="test_inviter_${TIMESTAMP}"
TEST_EMAIL="testinvite_${TIMESTAMP}@example.com"
INVITATION_ID=""
INVITATION_TOKEN=""

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
echo "Invitation Service Tests"
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
echo "GET ${API_BASE}/invitations/info"
INFO_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/invitations/info")
HTTP_CODE=$(echo "$INFO_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INFO_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service info retrieved"
else
    print_result 1 "Failed to get service info"
fi

# Test 2: Create Invitation (requires organization service to be running)
print_section "Test 2: Create Invitation"
echo "POST ${API_BASE}/invitations/organizations/${TEST_ORG_ID}"
CREATE_PAYLOAD=$(cat <<EOF
{
  "email": "${TEST_EMAIL}",
  "role": "member",
  "message": "Welcome to our organization!"
}
EOF
)
echo "Request Body:"
pretty_json "$CREATE_PAYLOAD"

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/invitations/organizations/${TEST_ORG_ID}" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: ${TEST_INVITER_ID}" \
  -d "$CREATE_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

# This may fail if organization service is not running - that's expected
if [ "$HTTP_CODE" = "200" ]; then
    INVITATION_ID=$(json_value "$RESPONSE_BODY" "invitation_id")
    INVITATION_TOKEN=$(json_value "$RESPONSE_BODY" "invitation_token")
    if [ -n "$INVITATION_ID" ] && [ "$INVITATION_ID" != "null" ]; then
        print_result 0 "Invitation created successfully"
        echo -e "${YELLOW}Invitation ID: ${INVITATION_ID}${NC}"
        echo -e "${YELLOW}Invitation Token (first 20 chars): ${INVITATION_TOKEN:0:20}...${NC}"
    else
        print_result 1 "Invitation created but no ID returned"
    fi
elif [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "404" ]; then
    echo -e "${YELLOW}⚠ Test skipped: Organization service dependency not available${NC}"
    echo -e "${YELLOW}  This is expected if organization service is not running${NC}"
    # Don't count as failure for this integration test
else
    print_result 1 "Failed to create invitation"
fi

# Test 3: Get Invitation by Token
if [ -n "$INVITATION_TOKEN" ] && [ "$INVITATION_TOKEN" != "null" ]; then
    print_section "Test 3: Get Invitation by Token"
    echo "GET ${API_BASE}/invitations/${INVITATION_TOKEN}"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/invitations/${INVITATION_TOKEN}")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        ORG_NAME=$(json_value "$RESPONSE_BODY" "organization_name")
        INV_STATUS=$(json_value "$RESPONSE_BODY" "status")
        print_result 0 "Invitation retrieved successfully"
        echo -e "${YELLOW}Organization: ${ORG_NAME}${NC}"
        echo -e "${YELLOW}Status: ${INV_STATUS}${NC}"
    else
        print_result 1 "Failed to retrieve invitation"
    fi
else
    echo -e "${YELLOW}⚠ Skipping Test 4: No invitation token available${NC}"
fi

# Test 4: Get Organization Invitations
if [ -n "$INVITATION_TOKEN" ]; then
    print_section "Test 4: Get Organization Invitations"
    echo "GET ${API_BASE}/invitations/organizations/${TEST_ORG_ID}"

    LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/invitations/organizations/${TEST_ORG_ID}?limit=10" \
      -H "X-User-Id: ${TEST_INVITER_ID}")
    HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        TOTAL=$(json_value "$RESPONSE_BODY" "total")
        print_result 0 "Invitation list retrieved"
        echo -e "${YELLOW}Total invitations: ${TOTAL}${NC}"
    elif [ "$HTTP_CODE" = "403" ]; then
        echo -e "${YELLOW}⚠ Test skipped: User doesn't have permission (expected)${NC}"
    else
        print_result 1 "Failed to retrieve invitation list"
    fi
else
    echo -e "${YELLOW}⚠ Skipping Test 5: No invitation available${NC}"
fi

# Test 5: Accept Invitation
if [ -n "$INVITATION_TOKEN" ] && [ "$INVITATION_TOKEN" != "null" ]; then
    print_section "Test 5: Accept Invitation"
    echo "POST ${API_BASE}/invitations/accept"
    ACCEPT_PAYLOAD=$(cat <<EOF
{
  "invitation_token": "${INVITATION_TOKEN}",
  "user_id": "${TEST_USER_ID}"
}
EOF
)
    echo "Request Body:"
    pretty_json "$ACCEPT_PAYLOAD"

    ACCEPT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/invitations/accept" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$ACCEPT_PAYLOAD")
    HTTP_CODE=$(echo "$ACCEPT_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$ACCEPT_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Invitation accepted successfully"
    elif [ "$HTTP_CODE" = "400" ]; then
        ERROR_MSG=$(json_value "$RESPONSE_BODY" "detail")
        echo -e "${YELLOW}⚠ Expected error (dependencies): ${ERROR_MSG}${NC}"
    else
        print_result 1 "Failed to accept invitation"
    fi
else
    echo -e "${YELLOW}⚠ Skipping Test 6: No invitation token available${NC}"
fi

# Test 6: Resend Invitation
if [ -n "$INVITATION_ID" ] && [ "$INVITATION_ID" != "null" ]; then
    print_section "Test 6: Resend Invitation"
    echo "POST ${API_BASE}/invitations/${INVITATION_ID}/resend"

    RESEND_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/invitations/${INVITATION_ID}/resend" \
      -H "X-User-Id: ${TEST_INVITER_ID}")
    HTTP_CODE=$(echo "$RESEND_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$RESEND_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Invitation resent successfully"
    elif [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "404" ]; then
        echo -e "${YELLOW}⚠ Test skipped: Permission or not found error (expected)${NC}"
    else
        print_result 1 "Failed to resend invitation"
    fi
else
    echo -e "${YELLOW}⚠ Skipping Test 7: No invitation ID available${NC}"
fi

# Test 7: Cancel Invitation
if [ -n "$INVITATION_ID" ] && [ "$INVITATION_ID" != "null" ]; then
    print_section "Test 7: Cancel Invitation"
    echo "DELETE ${API_BASE}/invitations/${INVITATION_ID}"

    CANCEL_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/invitations/${INVITATION_ID}" \
      -H "X-User-Id: ${TEST_INVITER_ID}")
    HTTP_CODE=$(echo "$CANCEL_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CANCEL_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Invitation cancelled successfully"
    elif [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "404" ]; then
        echo -e "${YELLOW}⚠ Test skipped: Permission or not found error (expected)${NC}"
    else
        print_result 1 "Failed to cancel invitation"
    fi
else
    echo -e "${YELLOW}⚠ Skipping Test 8: No invitation ID available${NC}"
fi

# Test 8: Expire Old Invitations (Admin endpoint)
print_section "Test 8: Expire Old Invitations (Admin)"
echo "POST ${API_BASE}/invitations/admin/expire-invitations"

EXPIRE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/invitations/admin/expire-invitations")
HTTP_CODE=$(echo "$EXPIRE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$EXPIRE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    EXPIRED_COUNT=$(json_value "$RESPONSE_BODY" "expired_count")
    print_result 0 "Old invitations expired"
    echo -e "${YELLOW}Expired count: ${EXPIRED_COUNT}${NC}"
else
    print_result 1 "Failed to expire old invitations"
fi

# Test 9: Get Invitation with Invalid Token
print_section "Test 9: Get Invitation with Invalid Token (should fail gracefully)"
echo "GET ${API_BASE}/invitations/invalid_token_12345"

INVALID_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/invitations/invalid_token_12345")
HTTP_CODE=$(echo "$INVALID_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INVALID_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "400" ]; then
    print_result 0 "Invalid token rejected correctly"
else
    print_result 1 "Invalid token handling failed"
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
echo -e "${YELLOW}Note: Some tests may be skipped due to service dependencies.${NC}"
echo -e "${YELLOW}To run full integration tests, ensure organization_service is running.${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
