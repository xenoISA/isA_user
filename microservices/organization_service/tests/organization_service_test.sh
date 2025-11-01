#!/bin/bash

# Organization Service Testing Script
# Tests organization creation, member management, family sharing, and context switching

BASE_URL="http://localhost:8212"
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

# Test data storage
TEST_USER_ID="test_user_$(date +%s)"
TEST_ORG_ID=""
TEST_MEMBER_ID="test_member_$(date +%s)"
TEST_SHARING_ID=""

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
echo "Organization Service Tests"
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

# Test 1: Health Check
print_section "Test 1: Health Check"
echo "GET ${BASE_URL}/health"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Health check successful"
else
    print_result 1 "Health check failed"
fi

# Test 2: Get Service Info
print_section "Test 2: Get Service Info"
echo "GET ${BASE_URL}/info"
INFO_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/info")
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

# Test 3: Create Organization
print_section "Test 3: Create Organization"
echo "POST ${API_BASE}/organizations"
CREATE_ORG_PAYLOAD=$(cat <<EOF
{
  "name": "Test Organization $(date +%s)",
  "billing_email": "billing@testorg.com",
  "plan": "professional",
  "settings": {
    "allow_external_sharing": true,
    "require_2fa": false
  }
}
EOF
)
echo "Request Body:"
pretty_json "$CREATE_ORG_PAYLOAD"

ORG_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/organizations" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: ${TEST_USER_ID}" \
  -d "$CREATE_ORG_PAYLOAD")
HTTP_CODE=$(echo "$ORG_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$ORG_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TEST_ORG_ID=$(json_value "$RESPONSE_BODY" "organization_id")
    if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
        print_result 0 "Organization created successfully"
        echo -e "${YELLOW}Organization ID: $TEST_ORG_ID${NC}"
    else
        print_result 1 "Organization creation returned 200 but no organization_id"
    fi
else
    print_result 1 "Failed to create organization"
fi

# Test 4: Get Organization
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 4: Get Organization"
    echo "GET ${API_BASE}/organizations/${TEST_ORG_ID}"

    GET_ORG_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/organizations/${TEST_ORG_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$GET_ORG_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_ORG_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        ORG_NAME=$(json_value "$RESPONSE_BODY" "name")
        if [ -n "$ORG_NAME" ] && [ "$ORG_NAME" != "null" ]; then
            print_result 0 "Organization retrieved successfully"
            echo -e "${YELLOW}Organization Name: $ORG_NAME${NC}"
        else
            print_result 1 "Organization retrieval returned 200 but no name"
        fi
    else
        print_result 1 "Failed to retrieve organization"
    fi
else
    echo -e "${YELLOW}Skipping Test 4: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: Update Organization
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 5: Update Organization"
    echo "PUT ${API_BASE}/organizations/${TEST_ORG_ID}"
    UPDATE_ORG_PAYLOAD=$(cat <<EOF
{
  "name": "Updated Test Organization",
  "settings": {
    "allow_external_sharing": false,
    "require_2fa": true
  }
}
EOF
)
    echo "Request Body:"
    pretty_json "$UPDATE_ORG_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/organizations/${TEST_ORG_ID}" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$UPDATE_ORG_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        UPDATED_NAME=$(json_value "$RESPONSE_BODY" "name")
        if [ "$UPDATED_NAME" = "Updated Test Organization" ]; then
            print_result 0 "Organization updated successfully"
        else
            print_result 1 "Organization update failed - name not updated"
        fi
    else
        print_result 1 "Failed to update organization"
    fi
else
    echo -e "${YELLOW}Skipping Test 5: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Get User Organizations
print_section "Test 6: Get User Organizations"
echo "GET ${API_BASE}/users/organizations"

USER_ORGS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/users/organizations" \
  -H "X-User-Id: ${TEST_USER_ID}")
HTTP_CODE=$(echo "$USER_ORGS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_ORGS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL=$(json_value "$RESPONSE_BODY" "total")
    if [ -n "$TOTAL" ]; then
        print_result 0 "User organizations retrieved successfully"
        echo -e "${YELLOW}Total Organizations: $TOTAL${NC}"
    else
        print_result 1 "User organizations response invalid"
    fi
else
    print_result 1 "Failed to get user organizations"
fi

# Test 7: Add Organization Member
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 7: Add Organization Member"
    echo "POST ${API_BASE}/organizations/${TEST_ORG_ID}/members"
    ADD_MEMBER_PAYLOAD=$(cat <<EOF
{
  "user_id": "${TEST_MEMBER_ID}",
  "role": "member",
  "permissions": ["read", "write"]
}
EOF
)
    echo "Request Body:"
    pretty_json "$ADD_MEMBER_PAYLOAD"

    ADD_MEMBER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/organizations/${TEST_ORG_ID}/members" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$ADD_MEMBER_PAYLOAD")
    HTTP_CODE=$(echo "$ADD_MEMBER_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$ADD_MEMBER_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        MEMBER_USER_ID=$(json_value "$RESPONSE_BODY" "user_id")
        if [ "$MEMBER_USER_ID" = "$TEST_MEMBER_ID" ]; then
            print_result 0 "Member added successfully"
        else
            print_result 1 "Member addition failed - user_id mismatch"
        fi
    else
        print_result 1 "Failed to add member"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Get Organization Members
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 8: Get Organization Members"
    echo "GET ${API_BASE}/organizations/${TEST_ORG_ID}/members"

    GET_MEMBERS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/organizations/${TEST_ORG_ID}/members?limit=50&offset=0" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$GET_MEMBERS_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_MEMBERS_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        TOTAL_MEMBERS=$(json_value "$RESPONSE_BODY" "total")
        if [ -n "$TOTAL_MEMBERS" ]; then
            print_result 0 "Organization members retrieved successfully"
            echo -e "${YELLOW}Total Members: $TOTAL_MEMBERS${NC}"
        else
            print_result 1 "Members response invalid"
        fi
    else
        print_result 1 "Failed to get organization members"
    fi
else
    echo -e "${YELLOW}Skipping Test 8: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 9: Update Organization Member
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 9: Update Organization Member"
    echo "PUT ${API_BASE}/organizations/${TEST_ORG_ID}/members/${TEST_MEMBER_ID}"
    UPDATE_MEMBER_PAYLOAD=$(cat <<EOF
{
  "role": "admin",
  "permissions": ["read", "write", "delete"]
}
EOF
)
    echo "Request Body:"
    pretty_json "$UPDATE_MEMBER_PAYLOAD"

    UPDATE_MEMBER_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/organizations/${TEST_ORG_ID}/members/${TEST_MEMBER_ID}" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$UPDATE_MEMBER_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_MEMBER_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_MEMBER_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        MEMBER_ROLE=$(json_value "$RESPONSE_BODY" "role")
        if [ "$MEMBER_ROLE" = "admin" ]; then
            print_result 0 "Member updated successfully"
        else
            print_result 1 "Member update failed - role not updated"
        fi
    else
        print_result 1 "Failed to update member"
    fi
else
    echo -e "${YELLOW}Skipping Test 9: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 10: Switch Organization Context
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 10: Switch Organization Context"
    echo "POST ${API_BASE}/organizations/context"
    SWITCH_CONTEXT_PAYLOAD=$(cat <<EOF
{
  "organization_id": "${TEST_ORG_ID}"
}
EOF
)
    echo "Request Body:"
    pretty_json "$SWITCH_CONTEXT_PAYLOAD"

    SWITCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/organizations/context" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$SWITCH_CONTEXT_PAYLOAD")
    HTTP_CODE=$(echo "$SWITCH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$SWITCH_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        CONTEXT_TYPE=$(json_value "$RESPONSE_BODY" "context_type")
        if [ "$CONTEXT_TYPE" = "organization" ]; then
            print_result 0 "Context switched successfully"
        else
            print_result 1 "Context switch failed - context_type not organization"
        fi
    else
        print_result 1 "Failed to switch context"
    fi
else
    echo -e "${YELLOW}Skipping Test 10: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 11: Get Organization Stats
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 11: Get Organization Stats"
    echo "GET ${API_BASE}/organizations/${TEST_ORG_ID}/stats"

    STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/organizations/${TEST_ORG_ID}/stats" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        MEMBER_COUNT=$(json_value "$RESPONSE_BODY" "member_count")
        if [ -n "$MEMBER_COUNT" ]; then
            print_result 0 "Organization stats retrieved successfully"
            echo -e "${YELLOW}Member Count: $MEMBER_COUNT${NC}"
        else
            print_result 1 "Stats response invalid"
        fi
    else
        print_result 1 "Failed to get organization stats"
    fi
else
    echo -e "${YELLOW}Skipping Test 11: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 12: Create Family Sharing Resource
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 12: Create Family Sharing Resource"
    echo "POST ${API_BASE}/organizations/${TEST_ORG_ID}/sharing"
    CREATE_SHARING_PAYLOAD=$(cat <<EOF
{
  "resource_type": "album",
  "resource_id": "album_$(date +%s)",
  "name": "Family Vacation Photos",
  "description": "Photos from our 2024 vacation",
  "member_permissions": {
    "${TEST_MEMBER_ID}": {
      "can_view": true,
      "can_edit": false,
      "can_delete": false,
      "can_share": false
    }
  }
}
EOF
)
    echo "Request Body:"
    pretty_json "$CREATE_SHARING_PAYLOAD"

    SHARING_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/organizations/${TEST_ORG_ID}/sharing" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$CREATE_SHARING_PAYLOAD")
    HTTP_CODE=$(echo "$SHARING_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$SHARING_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        TEST_SHARING_ID=$(json_value "$RESPONSE_BODY" "sharing_id")
        if [ -n "$TEST_SHARING_ID" ] && [ "$TEST_SHARING_ID" != "null" ]; then
            print_result 0 "Family sharing resource created successfully"
            echo -e "${YELLOW}Sharing ID: $TEST_SHARING_ID${NC}"
        else
            print_result 1 "Sharing creation returned 200 but no sharing_id"
        fi
    else
        print_result 1 "Failed to create sharing resource"
    fi
else
    echo -e "${YELLOW}Skipping Test 12: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 13: Get Sharing Resource
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ] && [ -n "$TEST_SHARING_ID" ] && [ "$TEST_SHARING_ID" != "null" ]; then
    print_section "Test 13: Get Sharing Resource"
    echo "GET ${API_BASE}/organizations/${TEST_ORG_ID}/sharing/${TEST_SHARING_ID}"

    GET_SHARING_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/organizations/${TEST_ORG_ID}/sharing/${TEST_SHARING_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$GET_SHARING_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_SHARING_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        # Check if response has sharing object
        SHARING_ID_CHECK=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('sharing', {}).get('sharing_id', ''))" 2>/dev/null || echo "")
        if [ -n "$SHARING_ID_CHECK" ] && [ "$SHARING_ID_CHECK" != "null" ] && [ "$SHARING_ID_CHECK" != "" ]; then
            print_result 0 "Sharing resource retrieved successfully"
            echo -e "${YELLOW}Sharing retrieved with ID: $SHARING_ID_CHECK${NC}"
        else
            print_result 1 "Sharing retrieval returned 200 but invalid structure"
        fi
    else
        print_result 1 "Failed to retrieve sharing resource"
    fi
else
    echo -e "${YELLOW}Skipping Test 13: No sharing ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 14: List Organization Sharings
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 14: List Organization Sharings"
    echo "GET ${API_BASE}/organizations/${TEST_ORG_ID}/sharing"

    LIST_SHARING_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/organizations/${TEST_ORG_ID}/sharing?limit=50&offset=0" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$LIST_SHARING_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$LIST_SHARING_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Organization sharings listed successfully"
    else
        print_result 1 "Failed to list organization sharings"
    fi
else
    echo -e "${YELLOW}Skipping Test 14: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 15: Remove Organization Member
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 15: Remove Organization Member"
    echo "DELETE ${API_BASE}/organizations/${TEST_ORG_ID}/members/${TEST_MEMBER_ID}"

    REMOVE_MEMBER_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/organizations/${TEST_ORG_ID}/members/${TEST_MEMBER_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$REMOVE_MEMBER_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$REMOVE_MEMBER_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        MESSAGE=$(json_value "$RESPONSE_BODY" "message")
        if [[ "$MESSAGE" == *"removed"* ]]; then
            print_result 0 "Member removed successfully"
        else
            print_result 1 "Member removal failed"
        fi
    else
        print_result 1 "Failed to remove member"
    fi
else
    echo -e "${YELLOW}Skipping Test 15: No organization ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 16: Delete Organization
if [ -n "$TEST_ORG_ID" ] && [ "$TEST_ORG_ID" != "null" ]; then
    print_section "Test 16: Delete Organization"
    echo "DELETE ${API_BASE}/organizations/${TEST_ORG_ID}"

    DELETE_ORG_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/organizations/${TEST_ORG_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$DELETE_ORG_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_ORG_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        MESSAGE=$(json_value "$RESPONSE_BODY" "message")
        if [[ "$MESSAGE" == *"deleted"* ]]; then
            print_result 0 "Organization deleted successfully"
        else
            print_result 1 "Organization deletion failed"
        fi
    else
        print_result 1 "Failed to delete organization"
    fi
else
    echo -e "${YELLOW}Skipping Test 16: No organization ID available${NC}"
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
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
