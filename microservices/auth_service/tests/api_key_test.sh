#!/bin/bash

# API Key Management Testing Script
# Tests API key creation, verification, listing, and revocation

BASE_URL="http://localhost:8201"
API_BASE="${BASE_URL}/api/v1/auth"

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
echo "API Key Management Service Tests"
echo "======================================================================"
echo ""

# Get organization ID - either from command line or fetch from database
if [ -n "$1" ]; then
    ORG_ID="$1"
    echo -e "${CYAN}Using provided organization: $ORG_ID${NC}"
else
    echo -e "${CYAN}Fetching available organizations from database...${NC}"

    # Query database for organizations using docker exec
    ORGS=$(docker exec user-staging python3 -c "
import sys
sys.path.insert(0, '/app')
from core.database.supabase_client import get_supabase_client

try:
    client = get_supabase_client()
    result = client.table('organizations').select('organization_id, name').limit(10).execute()
    if result.data:
        for org in result.data:
            print(f\"{org.get('organization_id')}|{org.get('name', 'N/A')}\")
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
" 2>&1)

    if echo "$ORGS" | grep -q "ERROR"; then
        echo -e "${RED}Failed to fetch organizations from database${NC}"
        echo -e "${YELLOW}Using default: org_test_001 (from seed data)${NC}"
        ORG_ID="org_test_001"
    elif [ -z "$ORGS" ]; then
        echo -e "${RED}No organizations found in database${NC}"
        echo -e "${YELLOW}Using default: org_test_001 (from seed data)${NC}"
        ORG_ID="org_test_001"
    else
        echo -e "${GREEN}Available organizations:${NC}"
        echo "$ORGS" | nl -w2 -s'. '
        echo ""

        # Use the first organization by default
        ORG_ID=$(echo "$ORGS" | head -n1 | cut -d'|' -f1)
        ORG_NAME=$(echo "$ORGS" | head -n1 | cut -d'|' -f2)

        echo -e "${GREEN}✓ Using first organization:${NC}"
        echo -e "  ID: ${CYAN}$ORG_ID${NC}"
        echo -e "  Name: ${CYAN}$ORG_NAME${NC}"
        echo ""
        echo -e "${YELLOW}Tip: To test with a different org, run:${NC}"
        echo -e "${YELLOW}  ./api_key.sh <organization_id>${NC}"
    fi
fi

echo ""
echo -e "${BLUE}Testing with Organization: $ORG_ID${NC}"
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

# Test 1: Create API Key
print_section "Test 1: Create API Key"
echo "POST ${API_BASE}/api-keys"
CREATE_PAYLOAD="{
  \"organization_id\": \"$ORG_ID\",
  \"name\": \"Test API Key $(date +%s)\",
  \"permissions\": [\"read\", \"write\", \"admin\"],
  \"expires_days\": 365
}"
echo "Request Body:"
echo "$CREATE_PAYLOAD" | jq '.'

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/api-keys" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

API_KEY=""
KEY_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    API_KEY=$(echo "$RESPONSE_BODY" | jq -r '.api_key')
    KEY_ID=$(echo "$RESPONSE_BODY" | jq -r '.key_id')
    if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
        print_result 0 "API key created successfully"
        echo -e "${YELLOW}API Key (first 20 chars): ${API_KEY:0:20}...${NC}"
        echo -e "${YELLOW}Key ID: $KEY_ID${NC}"
    else
        print_result 1 "API key creation returned 200 but no key found"
    fi
elif [ "$HTTP_CODE" = "400" ]; then
    ERROR_MSG=$(echo "$RESPONSE_BODY" | jq -r '.detail')
    if [[ "$ERROR_MSG" == *"not found"* ]] || [[ "$ERROR_MSG" == *"Organization"* ]]; then
        print_result 1 "Organization not found (expected - Issue #3 improved error)"
        echo -e "${YELLOW}Fix: Create organization '$ORG_ID' in database first${NC}"
        echo -e "${YELLOW}Or run: ./api_key.sh <existing_org_id>${NC}"
    else
        print_result 1 "API key creation failed with unclear error"
    fi
else
    print_result 1 "Failed to create API key"
fi

# Test 2: Verify API Key
if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
    print_section "Test 2: Verify API Key"
    echo "POST ${API_BASE}/verify-api-key"
    VERIFY_PAYLOAD="{
  \"api_key\": \"$API_KEY\"
}"
    echo "Request Body:"
    echo "$VERIFY_PAYLOAD" | jq '.'

    VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/verify-api-key" \
      -H "Content-Type: application/json" \
      -d "$VERIFY_PAYLOAD")
    HTTP_CODE=$(echo "$VERIFY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$VERIFY_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
    if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "true" ]; then
        print_result 0 "API key verified successfully"
    else
        print_result 1 "API key verification failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No API key available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Verify Invalid API Key
print_section "Test 3: Verify Invalid API Key (should fail gracefully)"
echo "POST ${API_BASE}/verify-api-key"
INVALID_PAYLOAD='{
  "api_key": "mcp_invalid_key_12345678901234567890"
}'
echo "Request Body:"
echo "$INVALID_PAYLOAD" | jq '.'

INVALID_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/verify-api-key" \
  -H "Content-Type: application/json" \
  -d "$INVALID_PAYLOAD")
HTTP_CODE=$(echo "$INVALID_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INVALID_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "false" ]; then
    print_result 0 "Invalid API key rejected correctly"
else
    print_result 1 "Invalid API key handling failed"
fi

# Test 4: List API Keys
print_section "Test 4: List Organization API Keys"
echo "GET ${API_BASE}/api-keys/${ORG_ID}"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/api-keys/${ORG_ID}")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    KEY_COUNT=$(echo "$RESPONSE_BODY" | jq -r '.api_keys | length' 2>/dev/null || echo "0")
    print_result 0 "API keys listed successfully (count: $KEY_COUNT)"
elif [ "$HTTP_CODE" = "400" ]; then
    ERROR_MSG=$(echo "$RESPONSE_BODY" | jq -r '.detail')
    if [[ "$ERROR_MSG" == *"not found"* ]]; then
        print_result 1 "Organization not found (expected - improved error)"
    else
        print_result 1 "List API keys failed"
    fi
else
    print_result 1 "Failed to list API keys"
fi

# Test 5: Create Multiple API Keys with Different Permissions
print_section "Test 5: Create API Key with Limited Permissions"
echo "POST ${API_BASE}/api-keys"
LIMITED_PAYLOAD="{
  \"organization_id\": \"$ORG_ID\",
  \"name\": \"Read-Only API Key $(date +%s)\",
  \"permissions\": [\"read\"],
  \"expires_days\": 30
}"
echo "Request Body:"
echo "$LIMITED_PAYLOAD" | jq '.'

LIMITED_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/api-keys" \
  -H "Content-Type: application/json" \
  -d "$LIMITED_PAYLOAD")
HTTP_CODE=$(echo "$LIMITED_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIMITED_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    LIMITED_KEY=$(echo "$RESPONSE_BODY" | jq -r '.api_key')
    LIMITED_KEY_ID=$(echo "$RESPONSE_BODY" | jq -r '.key_id')
    print_result 0 "Limited permission API key created"
    echo -e "${YELLOW}Key ID: $LIMITED_KEY_ID${NC}"
elif [ "$HTTP_CODE" = "400" ]; then
    print_result 1 "Organization not found (expected)"
else
    print_result 1 "Failed to create limited permission key"
fi

# Test 6: Revoke API Key
if [ -n "$KEY_ID" ] && [ "$KEY_ID" != "null" ]; then
    print_section "Test 6: Revoke API Key"
    echo "DELETE ${API_BASE}/api-keys/${KEY_ID}?organization_id=${ORG_ID}"

    REVOKE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE \
      "${API_BASE}/api-keys/${KEY_ID}?organization_id=${ORG_ID}")
    HTTP_CODE=$(echo "$REVOKE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$REVOKE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "API key revoked successfully"
    else
        print_result 1 "Failed to revoke API key"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No API key to revoke${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Verify Revoked API Key (should fail)
if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ] && [ -n "$KEY_ID" ] && [ "$KEY_ID" != "null" ]; then
    print_section "Test 7: Verify Revoked API Key (should fail)"
    echo "POST ${API_BASE}/verify-api-key"
    REVOKED_PAYLOAD="{
  \"api_key\": \"$API_KEY\"
}"
    echo "Request Body:"
    echo "$REVOKED_PAYLOAD" | jq '.'

    REVOKED_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/verify-api-key" \
      -H "Content-Type: application/json" \
      -d "$REVOKED_PAYLOAD")
    HTTP_CODE=$(echo "$REVOKED_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$REVOKED_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
    if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "false" ]; then
        print_result 0 "Revoked API key correctly rejected"
    else
        print_result 1 "Revoked API key validation failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No revoked key to test${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Create API Key Without Expiration
print_section "Test 8: Create API Key Without Expiration"
echo "POST ${API_BASE}/api-keys"
NO_EXPIRY_PAYLOAD="{
  \"organization_id\": \"$ORG_ID\",
  \"name\": \"Permanent API Key $(date +%s)\",
  \"permissions\": [\"read\", \"write\"]
}"
echo "Request Body:"
echo "$NO_EXPIRY_PAYLOAD" | jq '.'

NO_EXPIRY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/api-keys" \
  -H "Content-Type: application/json" \
  -d "$NO_EXPIRY_PAYLOAD")
HTTP_CODE=$(echo "$NO_EXPIRY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$NO_EXPIRY_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    EXPIRES_AT=$(echo "$RESPONSE_BODY" | jq -r '.expires_at')
    if [ "$EXPIRES_AT" = "null" ] || [ -z "$EXPIRES_AT" ]; then
        print_result 0 "API key created without expiration"
    else
        print_result 1 "API key unexpectedly has expiration"
    fi
elif [ "$HTTP_CODE" = "400" ]; then
    print_result 1 "Organization not found (expected)"
else
    print_result 1 "Failed to create permanent API key"
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
    echo -e "${YELLOW}Some tests failed.${NC}"
    echo -e "${YELLOW}If organization not found errors occurred, create the organization first:${NC}"
    echo -e "${YELLOW}  Organization ID: $ORG_ID${NC}"
    exit 1
fi
