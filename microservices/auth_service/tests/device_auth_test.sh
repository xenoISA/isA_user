
#!/bin/bash

# Device Authentication Testing Script
# Tests device registration, authentication, token verification, and management

BASE_URL="http://localhost"
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
echo "Device Authentication Service Tests"
echo "======================================================================"
echo ""

# Get organization ID - either from command line or use test data
if [ -n "$1" ]; then
    ORG_ID="$1"
    echo -e "${CYAN}Using provided organization: $ORG_ID${NC}"
else
    # Use test data from seed_test_data.sql
    ORG_ID="test_org_001"
    echo -e "${CYAN}Using default test organization: $ORG_ID${NC}"
    echo -e "${YELLOW}Available test organizations (from seed data):${NC}"
    echo -e "  ${CYAN}test_org_001${NC} - Test Organization Alpha"
    echo -e "  ${CYAN}test_org_002${NC} - Test Organization Beta"
    echo -e "  ${CYAN}test_org_003${NC} - Test Organization Gamma"
    echo ""
    echo -e "${YELLOW}Tip: To test with a different org, run:${NC}"
    echo -e "${YELLOW}  ./device_auth_test.sh <organization_id>${NC}"
fi

# Generate unique device ID for this test run
DEVICE_ID="device_test_$(date +%s)"

echo ""
echo -e "${BLUE}Testing with Organization: $ORG_ID${NC}"
echo -e "${BLUE}Device ID: $DEVICE_ID${NC}"
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

# Test 1: Register Device
print_section "Test 1: Register Device"
echo "POST ${API_BASE}/device/register"
REGISTER_PAYLOAD="{
  \"device_id\": \"$DEVICE_ID\",
  \"organization_id\": \"$ORG_ID\",
  \"device_name\": \"Test Smart Frame\",
  \"device_type\": \"smart_frame\",
  \"metadata\": {
    \"model\": \"SF-2024\",
    \"firmware\": \"1.0.0\",
    \"location\": \"Living Room\"
  },
  \"expires_days\": 365
}"
echo "Request Body:"
echo "$REGISTER_PAYLOAD" | jq '.'

REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/device/register" \
  -H "Content-Type: application/json" \
  -d "$REGISTER_PAYLOAD")
HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

DEVICE_SECRET=""
if [ "$HTTP_CODE" = "200" ]; then
    DEVICE_SECRET=$(echo "$RESPONSE_BODY" | jq -r '.device_secret')
    if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
        print_result 0 "Device registered successfully"
        echo -e "${YELLOW}Device Secret (first 20 chars): ${DEVICE_SECRET:0:20}...${NC}"
        echo -e "${RED}�  Save this secret! It won't be shown again.${NC}"
    else
        print_result 1 "Device registration returned 200 but no secret found"
    fi
elif [ "$HTTP_CODE" = "400" ]; then
    ERROR_MSG=$(echo "$RESPONSE_BODY" | jq -r '.detail')
    if [[ "$ERROR_MSG" == *"not found"* ]] || [[ "$ERROR_MSG" == *"Organization"* ]]; then
        print_result 1 "Organization not found (expected - Issue #4 improved error)"
        echo -e "${YELLOW}Fix: Create organization '$ORG_ID' in database first${NC}"
    elif [[ "$ERROR_MSG" == *"table"* ]] || [[ "$ERROR_MSG" == *"device_credentials"* ]]; then
        print_result 1 "Database table 'device_credentials' not found (expected)"
        echo -e "${YELLOW}Fix: Run database migrations to create device_credentials table${NC}"
    else
        print_result 1 "Device registration failed"
    fi
else
    print_result 1 "Failed to register device"
fi

# Test 2: Authenticate Device
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 2: Authenticate Device"
    echo "POST ${API_BASE}/device/authenticate"
    AUTH_PAYLOAD="{
  \"device_id\": \"$DEVICE_ID\",
  \"device_secret\": \"$DEVICE_SECRET\"
}"
    echo "Request Body:"
    echo "$AUTH_PAYLOAD" | jq '.'

    AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/device/authenticate" \
      -H "Content-Type: application/json" \
      -d "$AUTH_PAYLOAD")
    HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$AUTH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    DEVICE_TOKEN=""
    IS_AUTHENTICATED=$(echo "$RESPONSE_BODY" | jq -r '.authenticated')
    if [ "$HTTP_CODE" = "200" ] && [ "$IS_AUTHENTICATED" = "true" ]; then
        DEVICE_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.access_token')
        print_result 0 "Device authenticated successfully"
        echo -e "${YELLOW}Access Token (first 50 chars): ${DEVICE_TOKEN:0:50}...${NC}"
    else
        print_result 1 "Device authentication failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No device secret available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Authenticate with Invalid Secret
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 3: Authenticate with Invalid Secret (should fail)"
    echo "POST ${API_BASE}/device/authenticate"
    INVALID_AUTH_PAYLOAD="{
  \"device_id\": \"$DEVICE_ID\",
  \"device_secret\": \"invalid_secret_12345\"
}"
    echo "Request Body:"
    echo "$INVALID_AUTH_PAYLOAD" | jq '.'

    INVALID_AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/device/authenticate" \
      -H "Content-Type: application/json" \
      -d "$INVALID_AUTH_PAYLOAD")
    HTTP_CODE=$(echo "$INVALID_AUTH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$INVALID_AUTH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_AUTHENTICATED=$(echo "$RESPONSE_BODY" | jq -r '.authenticated')
    if [ "$IS_AUTHENTICATED" = "false" ] || [ "$HTTP_CODE" = "401" ]; then
        print_result 0 "Invalid device credentials rejected correctly"
    else
        print_result 1 "Invalid credentials handling failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No device registered${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: Verify Device Token
if [ -n "$DEVICE_TOKEN" ] && [ "$DEVICE_TOKEN" != "null" ]; then
    print_section "Test 4: Verify Device Token"
    echo "POST ${API_BASE}/device/verify-token"
    VERIFY_PAYLOAD="{
  \"token\": \"$DEVICE_TOKEN\"
}"
    echo "Request Body:"
    echo "$VERIFY_PAYLOAD" | jq '.'

    VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/device/verify-token" \
      -H "Content-Type: application/json" \
      -d "$VERIFY_PAYLOAD")
    HTTP_CODE=$(echo "$VERIFY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$VERIFY_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
    if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "true" ]; then
        print_result 0 "Device token verified successfully"
    else
        print_result 1 "Device token verification failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 4: No device token available${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: Verify Invalid Device Token
print_section "Test 5: Verify Invalid Device Token (should fail)"
echo "POST ${API_BASE}/device/verify-token"
INVALID_TOKEN_PAYLOAD='{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token"
}'
echo "Request Body:"
echo "$INVALID_TOKEN_PAYLOAD" | jq '.'

INVALID_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/device/verify-token" \
  -H "Content-Type: application/json" \
  -d "$INVALID_TOKEN_PAYLOAD")
HTTP_CODE=$(echo "$INVALID_TOKEN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INVALID_TOKEN_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

IS_VALID=$(echo "$RESPONSE_BODY" | jq -r '.valid')
if [ "$HTTP_CODE" = "200" ] && [ "$IS_VALID" = "false" ]; then
    print_result 0 "Invalid device token rejected correctly"
else
    print_result 1 "Invalid device token handling failed"
fi

# Test 6: List Devices
print_section "Test 6: List Organization Devices"
echo "GET ${API_BASE}/device/list?organization_id=${ORG_ID}"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET \
  "${API_BASE}/device/list?organization_id=${ORG_ID}")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    DEVICE_COUNT=$(echo "$RESPONSE_BODY" | jq -r '.devices | length' 2>/dev/null || echo "0")
    print_result 0 "Devices listed successfully (count: $DEVICE_COUNT)"
else
    print_result 1 "Failed to list devices"
fi

# Test 7: Refresh Device Secret
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 7: Refresh Device Secret"
    echo "POST ${API_BASE}/device/${DEVICE_ID}/refresh-secret?organization_id=${ORG_ID}"

    REFRESH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
      "${API_BASE}/device/${DEVICE_ID}/refresh-secret?organization_id=${ORG_ID}")
    HTTP_CODE=$(echo "$REFRESH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$REFRESH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        NEW_SECRET=$(echo "$RESPONSE_BODY" | jq -r '.device_secret')
        if [ -n "$NEW_SECRET" ] && [ "$NEW_SECRET" != "null" ] && [ "$NEW_SECRET" != "$DEVICE_SECRET" ]; then
            print_result 0 "Device secret refreshed successfully"
            echo -e "${YELLOW}New Secret (first 20 chars): ${NEW_SECRET:0:20}...${NC}"
            DEVICE_SECRET="$NEW_SECRET"  # Update for subsequent tests
        else
            print_result 1 "Secret refresh returned 200 but secret unchanged or missing"
        fi
    else
        print_result 1 "Failed to refresh device secret"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No device registered${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Authenticate with New Secret (after refresh)
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 8: Authenticate with Refreshed Secret"
    echo "POST ${API_BASE}/device/authenticate"
    NEW_AUTH_PAYLOAD="{
  \"device_id\": \"$DEVICE_ID\",
  \"device_secret\": \"$DEVICE_SECRET\"
}"
    echo "Request Body:"
    echo "$NEW_AUTH_PAYLOAD" | jq '.'

    NEW_AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/device/authenticate" \
      -H "Content-Type: application/json" \
      -d "$NEW_AUTH_PAYLOAD")
    HTTP_CODE=$(echo "$NEW_AUTH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$NEW_AUTH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_AUTHENTICATED=$(echo "$RESPONSE_BODY" | jq -r '.authenticated')
    if [ "$HTTP_CODE" = "200" ] && [ "$IS_AUTHENTICATED" = "true" ]; then
        print_result 0 "Authentication with refreshed secret successful"
    else
        print_result 1 "Authentication with refreshed secret failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 8: No refreshed secret available${NC}"
    ((TESTS_FAILED++))
fi

# Test 9: Register Another Device
print_section "Test 9: Register Second Device"
DEVICE_ID_2="device_test_2_$(date +%s)"
echo "POST ${API_BASE}/device/register"
REGISTER2_PAYLOAD="{
  \"device_id\": \"$DEVICE_ID_2\",
  \"organization_id\": \"$ORG_ID\",
  \"device_name\": \"Test Smart Frame #2\",
  \"device_type\": \"smart_frame\",
  \"metadata\": {
    \"model\": \"SF-2024-Pro\",
    \"firmware\": \"1.1.0\",
    \"location\": \"Bedroom\"
  },
  \"expires_days\": 180
}"
echo "Request Body:"
echo "$REGISTER2_PAYLOAD" | jq '.'

REGISTER2_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/device/register" \
  -H "Content-Type: application/json" \
  -d "$REGISTER2_PAYLOAD")
HTTP_CODE=$(echo "$REGISTER2_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REGISTER2_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Second device registered successfully"
else
    print_result 1 "Failed to register second device"
fi

# Test 10: Revoke Device
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 10: Revoke Device"
    echo "DELETE ${API_BASE}/device/${DEVICE_ID}?organization_id=${ORG_ID}"

    REVOKE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE \
      "${API_BASE}/device/${DEVICE_ID}?organization_id=${ORG_ID}")
    HTTP_CODE=$(echo "$REVOKE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$REVOKE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Device revoked successfully"
    else
        print_result 1 "Failed to revoke device"
    fi
else
    echo -e "${YELLOW}Skipping Test 10: No device to revoke${NC}"
    ((TESTS_FAILED++))
fi

# Test 11: Authenticate with Revoked Device (should fail)
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 11: Authenticate Revoked Device (should fail)"
    echo "POST ${API_BASE}/device/authenticate"
    REVOKED_AUTH_PAYLOAD="{
  \"device_id\": \"$DEVICE_ID\",
  \"device_secret\": \"$DEVICE_SECRET\"
}"
    echo "Request Body:"
    echo "$REVOKED_AUTH_PAYLOAD" | jq '.'

    REVOKED_AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/device/authenticate" \
      -H "Content-Type: application/json" \
      -d "$REVOKED_AUTH_PAYLOAD")
    HTTP_CODE=$(echo "$REVOKED_AUTH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$REVOKED_AUTH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    IS_AUTHENTICATED=$(echo "$RESPONSE_BODY" | jq -r '.authenticated')
    if [ "$IS_AUTHENTICATED" = "false" ] || [ "$HTTP_CODE" = "401" ]; then
        print_result 0 "Revoked device correctly rejected"
    else
        print_result 1 "Revoked device authentication handling failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 11: No revoked device to test${NC}"
    ((TESTS_FAILED++))
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
    echo -e "${YELLOW}Common issues:${NC}"
    echo -e "${YELLOW}  1. Organization not found - Create organization '$ORG_ID' in database${NC}"
    echo -e "${YELLOW}  2. Table not found - Run database migrations for device_credentials table${NC}"
    echo -e "${YELLOW}  3. Run: ./device_auth.sh <existing_org_id>${NC}"
    exit 1
fi
