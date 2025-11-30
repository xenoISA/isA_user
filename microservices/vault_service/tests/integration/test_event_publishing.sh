#!/bin/bash

# Vault Service Event Publishing Test Script
# Tests that vault service correctly publishes events to NATS

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1/vault"

# Test user ID
TEST_USER_ID="test_event_user_123"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

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
echo "Vault Service Event Publishing Tests"
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

# Test 1: Create Secret and Check Event
print_section "Test 1: Create Secret (Publishes vault.secret.created event)"
echo "POST ${API_BASE}/secrets"
CREATE_SECRET_PAYLOAD='{
  "name": "Test Event API Key",
  "description": "Testing event publishing",
  "secret_type": "api_key",
  "provider": "openai",
  "secret_value": "sk-event-test-123456789",
  "tags": ["test", "events"],
  "metadata": {
    "test": "event_publishing"
  }
}'

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/secrets" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: ${TEST_USER_ID}" \
  -d "$CREATE_SECRET_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

VAULT_ID=""
if [ "$HTTP_CODE" = "201" ]; then
    VAULT_ID=$(json_value "$RESPONSE_BODY" "vault_id")
    if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
        print_result 0 "Secret created - vault.secret.created event should be published"
        echo -e "${YELLOW}Vault ID: ${VAULT_ID}${NC}"
        echo -e "${YELLOW}Expected Event: vault.secret.created${NC}"
    else
        print_result 1 "Secret creation returned 201 but no vault_id found"
    fi
else
    print_result 1 "Failed to create secret"
fi

# Test 3: Access Secret (Publishes vault.secret.accessed event)
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 3: Access Secret (Publishes vault.secret.accessed event)"
    echo "GET ${API_BASE}/secrets/${VAULT_ID}?decrypt=true"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/secrets/${VAULT_ID}?decrypt=true" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret accessed - vault.secret.accessed event should be published"
        echo -e "${YELLOW}Expected Event: vault.secret.accessed${NC}"
    else
        print_result 1 "Failed to access secret"
    fi
fi

# Test 4: Update Secret (Publishes vault.secret.updated event)
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 4: Update Secret (Publishes vault.secret.updated event)"
    echo "PUT ${API_BASE}/secrets/${VAULT_ID}"
    UPDATE_PAYLOAD='{
      "name": "Updated Event Test",
      "description": "Testing update event",
      "tags": ["test", "events", "updated"]
    }'

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/secrets/${VAULT_ID}" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$UPDATE_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)

    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret updated - vault.secret.updated event should be published"
        echo -e "${YELLOW}Expected Event: vault.secret.updated${NC}"
    else
        print_result 1 "Failed to update secret"
    fi
fi

# Test 5: Share Secret (Publishes vault.secret.shared event)
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 5: Share Secret (Publishes vault.secret.shared event)"
    echo "POST ${API_BASE}/secrets/${VAULT_ID}/share"
    SHARE_PAYLOAD='{
      "shared_with_user_id": "test_user_event_456",
      "permission_level": "read"
    }'

    SHARE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/secrets/${VAULT_ID}/share" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$SHARE_PAYLOAD")
    HTTP_CODE=$(echo "$SHARE_RESPONSE" | tail -n1)

    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret shared - vault.secret.shared event should be published"
        echo -e "${YELLOW}Expected Event: vault.secret.shared${NC}"
    else
        print_result 1 "Failed to share secret"
    fi
fi

# Test 6: Rotate Secret (Publishes vault.secret.rotated event)
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 6: Rotate Secret (Publishes vault.secret.rotated event)"
    echo "POST ${API_BASE}/secrets/${VAULT_ID}/rotate"

    ROTATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
      "${API_BASE}/secrets/${VAULT_ID}/rotate?new_secret_value=sk-rotated-event-test-999" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$ROTATE_RESPONSE" | tail -n1)

    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret rotated - vault.secret.rotated event should be published"
        echo -e "${YELLOW}Expected Event: vault.secret.rotated${NC}"
    else
        print_result 1 "Failed to rotate secret"
    fi
fi

# Test 7: Delete Secret (Publishes vault.secret.deleted event)
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 7: Delete Secret (Publishes vault.secret.deleted event)"
    echo "DELETE ${API_BASE}/secrets/${VAULT_ID}"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/secrets/${VAULT_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)

    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret deleted - vault.secret.deleted event should be published"
        echo -e "${YELLOW}Expected Event: vault.secret.deleted${NC}"
    else
        print_result 1 "Failed to delete secret"
    fi
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
echo -e "${YELLOW}Note: This script tests that API operations complete successfully.${NC}"
echo -e "${YELLOW}Actual event publishing is verified by checking NATS logs or using${NC}"
echo -e "${YELLOW}the Python event subscription tests.${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All API operations completed successfully!${NC}"
    echo -e "${GREEN}Events should have been published to NATS.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Please review the output above.${NC}"
    exit 1
fi
