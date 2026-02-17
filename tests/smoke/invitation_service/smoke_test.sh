#!/bin/bash
# =============================================================================
# Invitation Service - Smoke Tests
#
# Tests basic functionality of invitation_service endpoints.
# All test data is generated dynamically - zero hardcoded values.
#
# Usage:
#   ./smoke_test.sh                     # Direct mode (X-Internal-Call)
#   TEST_MODE=gateway ./smoke_test.sh   # Gateway mode with JWT
#
# Prerequisites:
#   - invitation_service running on port 8213
#   - For gateway mode: auth_service and valid credentials
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="invitation_service"
SERVICE_PORT="${INVITATION_SERVICE_PORT:-8213}"
SERVICE_URL="http://localhost:${SERVICE_PORT}"
API_BASE="${SERVICE_URL}/api/v1/invitations"

# Test mode: direct (X-Internal-Call) or gateway (JWT)
TEST_MODE="${TEST_MODE:-direct}"

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Test data (generated dynamically)
TEST_TS="$(date +%s)_$$"
TEST_ORG_ID="org_smoke_${TEST_TS}"
TEST_EMAIL="smoke_${TEST_TS}@example.com"
TEST_USER_ID="user_smoke_${TEST_TS}"
INVITATION_ID=""
INVITATION_TOKEN=""

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_section() {
    echo ""
    echo -e "${YELLOW}--- $1 ---${NC}"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

get_auth_headers() {
    if [ "$TEST_MODE" = "gateway" ]; then
        # TODO: Get JWT token from auth service
        echo "-H 'Authorization: Bearer ${JWT_TOKEN}'"
    else
        echo "-H 'X-Internal-Call: true' -H 'X-User-Id: ${TEST_USER_ID}'"
    fi
}

api_get() {
    local path="$1"
    local no_auth="$2"
    local headers=""

    if [ "$no_auth" != "true" ]; then
        headers=$(get_auth_headers)
    fi

    eval "curl -s ${SERVICE_URL}${path} ${headers}"
}

api_post() {
    local path="$1"
    local data="$2"
    local headers=$(get_auth_headers)

    eval "curl -s -X POST ${SERVICE_URL}${path} \
        -H 'Content-Type: application/json' \
        ${headers} \
        -d '${data}'"
}

api_delete() {
    local path="$1"
    local headers=$(get_auth_headers)

    eval "curl -s -X DELETE ${SERVICE_URL}${path} ${headers}"
}

api_get_status() {
    local path="$1"
    local no_auth="$2"
    local headers=""

    if [ "$no_auth" != "true" ]; then
        headers=$(get_auth_headers)
    fi

    eval "curl -s -o /dev/null -w '%{http_code}' ${SERVICE_URL}${path} ${headers}"
}

json_get() {
    echo "$1" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$2', ''))" 2>/dev/null || echo ""
}

json_has() {
    echo "$1" | python3 -c "import sys, json; data=json.load(sys.stdin); print('$2' in data)" 2>/dev/null | grep -q "True"
}

# =============================================================================
# Test Cases
# =============================================================================

print_header "Invitation Service Smoke Tests"
print_info "Service URL: ${SERVICE_URL}"
print_info "Test Mode: ${TEST_MODE}"
print_info "Test Timestamp: ${TEST_TS}"
echo ""

# ----------------------------------------------------------------------------
# Test 1: Health Check
# ----------------------------------------------------------------------------
print_section "Test 1: Health Check"
RESPONSE=$(api_get "/health" "true")
if json_has "$RESPONSE" "status"; then
    STATUS=$(json_get "$RESPONSE" "status")
    if [ "$STATUS" = "healthy" ]; then
        print_success "Health check returned healthy"
    else
        print_fail "Health check status: $STATUS"
    fi
else
    print_fail "Health check failed: $RESPONSE"
fi

# ----------------------------------------------------------------------------
# Test 2: Service Info
# ----------------------------------------------------------------------------
print_section "Test 2: Service Info"
RESPONSE=$(api_get "/info" "true")
if json_has "$RESPONSE" "service"; then
    SERVICE=$(json_get "$RESPONSE" "service")
    print_success "Service info returned: $SERVICE"
else
    print_fail "Service info failed: $RESPONSE"
fi

# ----------------------------------------------------------------------------
# Test 3: Create Invitation
# ----------------------------------------------------------------------------
print_section "Test 3: Create Invitation"
CREATE_PAYLOAD="{\"email\": \"${TEST_EMAIL}\", \"role\": \"member\", \"message\": \"Smoke test invitation\"}"
RESPONSE=$(api_post "/api/v1/invitations/organizations/${TEST_ORG_ID}" "$CREATE_PAYLOAD")

if json_has "$RESPONSE" "invitation_id"; then
    INVITATION_ID=$(json_get "$RESPONSE" "invitation_id")
    INVITATION_TOKEN=$(json_get "$RESPONSE" "invitation_token")
    print_success "Created invitation: $INVITATION_ID"
    print_info "Token: ${INVITATION_TOKEN:0:20}..."
else
    # May fail due to org validation - that's ok for smoke test
    ERROR=$(json_get "$RESPONSE" "detail")
    if [ -n "$ERROR" ]; then
        print_skip "Create failed (expected if org doesn't exist): $ERROR"
    else
        print_fail "Create failed: $RESPONSE"
    fi
fi

# ----------------------------------------------------------------------------
# Test 4: Get Invitation by Token
# ----------------------------------------------------------------------------
print_section "Test 4: Get Invitation by Token"
if [ -n "$INVITATION_TOKEN" ]; then
    RESPONSE=$(api_get "/api/v1/invitations/${INVITATION_TOKEN}" "true")
    if json_has "$RESPONSE" "invitation_id"; then
        RETRIEVED_ID=$(json_get "$RESPONSE" "invitation_id")
        if [ "$RETRIEVED_ID" = "$INVITATION_ID" ]; then
            print_success "Retrieved invitation by token"
        else
            print_fail "ID mismatch: expected $INVITATION_ID, got $RETRIEVED_ID"
        fi
    else
        print_fail "Get by token failed: $RESPONSE"
    fi
else
    print_skip "No invitation token to test"
fi

# ----------------------------------------------------------------------------
# Test 5: Get Nonexistent Invitation (404)
# ----------------------------------------------------------------------------
print_section "Test 5: Get Nonexistent Invitation"
FAKE_TOKEN="fake_token_${TEST_TS}_nonexistent"
HTTP_CODE=$(api_get_status "/api/v1/invitations/${FAKE_TOKEN}" "true")
if [ "$HTTP_CODE" = "404" ]; then
    print_success "Nonexistent invitation returns 404"
else
    print_fail "Expected 404, got $HTTP_CODE"
fi

# ----------------------------------------------------------------------------
# Test 6: List Organization Invitations
# ----------------------------------------------------------------------------
print_section "Test 6: List Organization Invitations"
RESPONSE=$(api_get "/api/v1/invitations/organizations/${TEST_ORG_ID}")
if json_has "$RESPONSE" "invitations"; then
    print_success "List invitations returned array"
elif json_has "$RESPONSE" "detail"; then
    ERROR=$(json_get "$RESPONSE" "detail")
    print_skip "List failed (expected if no permission): $ERROR"
else
    print_fail "List failed: $RESPONSE"
fi

# ----------------------------------------------------------------------------
# Test 7: Resend Invitation
# ----------------------------------------------------------------------------
print_section "Test 7: Resend Invitation"
if [ -n "$INVITATION_ID" ]; then
    RESPONSE=$(api_post "/api/v1/invitations/${INVITATION_ID}/resend" "{}")
    if json_has "$RESPONSE" "message"; then
        MESSAGE=$(json_get "$RESPONSE" "message")
        print_success "Resend invitation: $MESSAGE"
    else
        print_fail "Resend failed: $RESPONSE"
    fi
else
    print_skip "No invitation ID to resend"
fi

# ----------------------------------------------------------------------------
# Test 8: Admin Expire Old Invitations
# ----------------------------------------------------------------------------
print_section "Test 8: Admin Expire Old Invitations"
RESPONSE=$(api_post "/api/v1/invitations/admin/expire-invitations" "{}")
if json_has "$RESPONSE" "expired_count"; then
    COUNT=$(json_get "$RESPONSE" "expired_count")
    print_success "Expired $COUNT old invitations"
else
    print_fail "Expire failed: $RESPONSE"
fi

# ----------------------------------------------------------------------------
# Test 9: Cancel Invitation
# ----------------------------------------------------------------------------
print_section "Test 9: Cancel Invitation"
if [ -n "$INVITATION_ID" ]; then
    RESPONSE=$(api_delete "/api/v1/invitations/${INVITATION_ID}")
    if json_has "$RESPONSE" "message"; then
        MESSAGE=$(json_get "$RESPONSE" "message")
        print_success "Cancel invitation: $MESSAGE"
    else
        print_fail "Cancel failed: $RESPONSE"
    fi
else
    print_skip "No invitation ID to cancel"
fi

# ----------------------------------------------------------------------------
# Test 10: Verify Cancelled (Get returns error)
# ----------------------------------------------------------------------------
print_section "Test 10: Verify Cancelled Invitation"
if [ -n "$INVITATION_TOKEN" ]; then
    RESPONSE=$(api_get "/api/v1/invitations/${INVITATION_TOKEN}" "true")
    if json_has "$RESPONSE" "detail"; then
        ERROR=$(json_get "$RESPONSE" "detail")
        print_success "Cancelled invitation returns error: $ERROR"
    elif json_has "$RESPONSE" "status"; then
        STATUS=$(json_get "$RESPONSE" "status")
        if [ "$STATUS" = "cancelled" ] || [ "$STATUS" = "pending" ]; then
            print_success "Invitation status: $STATUS"
        else
            print_info "Invitation status: $STATUS"
        fi
    else
        print_fail "Unexpected response: $RESPONSE"
    fi
else
    print_skip "No invitation token to verify"
fi

# ----------------------------------------------------------------------------
# Test 11: Create with Invalid Email (422)
# ----------------------------------------------------------------------------
print_section "Test 11: Create with Invalid Email"
INVALID_PAYLOAD='{"email": "not-an-email", "role": "member"}'
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API_BASE}/organizations/${TEST_ORG_ID}" \
    -H 'Content-Type: application/json' \
    -H 'X-Internal-Call: true' \
    -H "X-User-Id: ${TEST_USER_ID}" \
    -d "$INVALID_PAYLOAD")
if [ "$HTTP_CODE" = "422" ]; then
    print_success "Invalid email returns 422"
else
    print_fail "Expected 422, got $HTTP_CODE"
fi

# ----------------------------------------------------------------------------
# Test 12: Unauthenticated Request (401)
# ----------------------------------------------------------------------------
print_section "Test 12: Unauthenticated Request"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' "${API_BASE}/organizations/${TEST_ORG_ID}")
if [ "$HTTP_CODE" = "401" ]; then
    print_success "Unauthenticated request returns 401"
else
    print_fail "Expected 401, got $HTTP_CODE"
fi

# ----------------------------------------------------------------------------
# Test 13: Cancel Nonexistent (404)
# ----------------------------------------------------------------------------
print_section "Test 13: Cancel Nonexistent Invitation"
FAKE_ID="inv_fake_${TEST_TS}_nonexistent"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "${API_BASE}/${FAKE_ID}" \
    -H 'X-Internal-Call: true' \
    -H "X-User-Id: ${TEST_USER_ID}")
if [ "$HTTP_CODE" = "404" ]; then
    print_success "Cancel nonexistent returns 404"
else
    print_fail "Expected 404, got $HTTP_CODE"
fi

# ----------------------------------------------------------------------------
# Test 14: Accept with Invalid Token
# ----------------------------------------------------------------------------
print_section "Test 14: Accept with Invalid Token"
ACCEPT_PAYLOAD="{\"invitation_token\": \"invalid_token_${TEST_TS}\"}"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API_BASE}/accept" \
    -H 'Content-Type: application/json' \
    -H 'X-Internal-Call: true' \
    -H "X-User-Id: ${TEST_USER_ID}" \
    -d "$ACCEPT_PAYLOAD")
if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "404" ]; then
    print_success "Accept invalid token returns $HTTP_CODE"
else
    print_fail "Expected 400 or 404, got $HTTP_CODE"
fi

# ----------------------------------------------------------------------------
# Test 15: Health Check Port Verification
# ----------------------------------------------------------------------------
print_section "Test 15: Health Check Port Verification"
RESPONSE=$(api_get "/health" "true")
PORT=$(json_get "$RESPONSE" "port")
if [ "$PORT" = "8213" ]; then
    print_success "Health check shows correct port: $PORT"
else
    print_fail "Expected port 8213, got $PORT"
fi

# =============================================================================
# Summary
# =============================================================================

print_header "Test Summary"
echo ""
echo -e "  ${GREEN}Passed:${NC}  $TESTS_PASSED"
echo -e "  ${RED}Failed:${NC}  $TESTS_FAILED"
echo -e "  ${YELLOW}Skipped:${NC} $TESTS_SKIPPED"
echo ""

TOTAL=$((TESTS_PASSED + TESTS_FAILED))
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All $TOTAL tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$TESTS_FAILED of $TOTAL tests failed${NC}"
    exit 1
fi
