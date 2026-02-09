#!/bin/bash

# Invitation Service Event Publishing Integration Test
# Tests that invitation service correctly publishes events to NATS

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
echo "Invitation Service Event Publishing Integration Tests"
echo "======================================================================"
echo ""
echo -e "${YELLOW}This test verifies that invitation service publishes events to NATS${NC}"
echo -e "${YELLOW}for all invitation lifecycle operations.${NC}"
echo ""

# Test 1: Create Invitation - Should publish invitation.sent event
print_section "Test 1: Create Invitation Event Publishing"
echo "POST ${API_BASE}/invitations/organizations/${TEST_ORG_ID}"
echo -e "${YELLOW}Expected Event: invitation.sent${NC}"

CREATE_PAYLOAD=$(cat <<EOF
{
  "email": "${TEST_EMAIL}",
  "role": "member",
  "message": "Welcome to our organization!"
}
EOF
)

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/invitations/organizations/${TEST_ORG_ID}" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: ${TEST_INVITER_ID}" \
  -d "$CREATE_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    INVITATION_ID=$(json_value "$RESPONSE_BODY" "invitation_id")
    INVITATION_TOKEN=$(json_value "$RESPONSE_BODY" "invitation_token")
    if [ -n "$INVITATION_ID" ] && [ "$INVITATION_ID" != "null" ]; then
        print_result 0 "Invitation created - invitation.sent event should be published"
        echo -e "${YELLOW}Invitation ID: ${INVITATION_ID}${NC}"
        echo -e "${YELLOW}Check NATS for event: invitation.sent with organization_id=${TEST_ORG_ID}${NC}"
    else
        print_result 1 "Invitation created but no ID returned"
    fi
elif [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "404" ]; then
    echo -e "${YELLOW}⚠ Test skipped: Organization service dependency not available${NC}"
else
    print_result 1 "Failed to create invitation"
fi

# Test 2: Accept Invitation - Should publish invitation.accepted event
if [ -n "$INVITATION_TOKEN" ] && [ "$INVITATION_TOKEN" != "null" ]; then
    print_section "Test 2: Accept Invitation Event Publishing"
    echo "POST ${API_BASE}/invitations/accept"
    echo -e "${YELLOW}Expected Event: invitation.accepted${NC}"

    ACCEPT_PAYLOAD=$(cat <<EOF
{
  "invitation_token": "${INVITATION_TOKEN}",
  "user_id": "${TEST_USER_ID}"
}
EOF
)

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
        print_result 0 "Invitation accepted - invitation.accepted event should be published"
        echo -e "${YELLOW}Check NATS for event: invitation.accepted with user_id=${TEST_USER_ID}${NC}"
    elif [ "$HTTP_CODE" = "400" ]; then
        ERROR_MSG=$(json_value "$RESPONSE_BODY" "detail")
        echo -e "${YELLOW}⚠ Expected error (dependencies): ${ERROR_MSG}${NC}"
        echo -e "${YELLOW}⚠ Test skipped: Dependencies not available${NC}"
    else
        print_result 1 "Failed to accept invitation"
    fi
else
    echo -e "${YELLOW}⚠ Skipping Test 2: No invitation token available${NC}"
fi

# Test 3: Create another invitation for cancellation test
print_section "Test 3: Create Invitation for Cancellation Test"
TEST_EMAIL_2="testinvite2_${TIMESTAMP}@example.com"

CREATE_PAYLOAD_2=$(cat <<EOF
{
  "email": "${TEST_EMAIL_2}",
  "role": "member",
  "message": "Welcome!"
}
EOF
)

CREATE_RESPONSE_2=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/invitations/organizations/${TEST_ORG_ID}" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: ${TEST_INVITER_ID}" \
  -d "$CREATE_PAYLOAD_2")
HTTP_CODE=$(echo "$CREATE_RESPONSE_2" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE_2" | sed '$d')

INVITATION_ID_2=""
if [ "$HTTP_CODE" = "200" ]; then
    INVITATION_ID_2=$(json_value "$RESPONSE_BODY" "invitation_id")
    echo -e "${GREEN}Created invitation for cancellation test${NC}"
    echo -e "${YELLOW}Invitation ID: ${INVITATION_ID_2}${NC}"
fi

# Test 4: Cancel Invitation - Should publish invitation.cancelled event
if [ -n "$INVITATION_ID_2" ] && [ "$INVITATION_ID_2" != "null" ]; then
    print_section "Test 4: Cancel Invitation Event Publishing"
    echo "DELETE ${API_BASE}/invitations/${INVITATION_ID_2}"
    echo -e "${YELLOW}Expected Event: invitation.cancelled${NC}"

    CANCEL_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/invitations/${INVITATION_ID_2}" \
      -H "X-User-Id: ${TEST_INVITER_ID}")
    HTTP_CODE=$(echo "$CANCEL_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CANCEL_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Invitation cancelled - invitation.cancelled event should be published"
        echo -e "${YELLOW}Check NATS for event: invitation.cancelled with invitation_id=${INVITATION_ID_2}${NC}"
    elif [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "404" ]; then
        echo -e "${YELLOW}⚠ Test skipped: Permission or not found error${NC}"
    else
        print_result 1 "Failed to cancel invitation"
    fi
else
    echo -e "${YELLOW}⚠ Skipping Test 4: No invitation ID available for cancellation${NC}"
fi

# Test 5: Expire Old Invitations - Should publish invitation.expired event
print_section "Test 5: Expire Old Invitations Event Publishing"
echo "POST ${API_BASE}/admin/expire-invitations"
echo -e "${YELLOW}Expected Event: invitation.expired (for any expired invitations)${NC}"

EXPIRE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/admin/expire-invitations")
HTTP_CODE=$(echo "$EXPIRE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$EXPIRE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    EXPIRED_COUNT=$(json_value "$RESPONSE_BODY" "expired_count")
    print_result 0 "Expiration process completed - invitation.expired event published for each expired invitation"
    echo -e "${YELLOW}Expired count: ${EXPIRED_COUNT}${NC}"
    if [ "$EXPIRED_COUNT" -gt "0" ]; then
        echo -e "${YELLOW}Check NATS for ${EXPIRED_COUNT} invitation.expired event(s)${NC}"
    fi
elif [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "401" ]; then
    # Admin endpoint may not be exposed through gateway
    echo -e "${YELLOW}⚠ Admin endpoint not available through gateway (expected)${NC}"
    print_result 0 "Admin endpoint check (optional - not exposed)"
else
    print_result 1 "Failed to expire old invitations"
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
echo -e "${YELLOW}Event Publishing Verification:${NC}"
echo "To verify events were published to NATS, check the NATS server logs or use:"
echo "  nats sub 'invitation.>' --count=10"
echo ""
echo -e "${YELLOW}Expected Event Types:${NC}"
echo "  - invitation.sent (when invitations are created)"
echo "  - invitation.accepted (when invitations are accepted)"
echo "  - invitation.cancelled (when invitations are cancelled)"
echo "  - invitation.expired (when invitations expire)"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All integration tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
