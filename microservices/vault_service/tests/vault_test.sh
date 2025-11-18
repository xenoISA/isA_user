#!/bin/bash

# Vault Service Testing Script
# Tests secure credential management, encryption, sharing, and audit features

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1/vault"

# Test user ID (required for authentication)
TEST_USER_ID="test_user_vault_123"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

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
echo "Vault Service Tests"
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
# Test 1: Create API Key Secret
print_section "Test 1: Create API Key Secret"
echo "POST ${API_BASE}/secrets"
CREATE_SECRET_PAYLOAD='{
  "name": "Test API Key",
  "description": "Test API key for external service",
  "secret_type": "api_key",
  "provider": "openai",
  "secret_value": "sk-test1234567890abcdefghijklmnopqrstuvwxyz",
  "tags": ["test", "api", "openai"],
  "metadata": {
    "environment": "test",
    "purpose": "testing"
  },
  "rotation_enabled": true,
  "rotation_days": 90
}'
echo "Request Body:"
pretty_json "$CREATE_SECRET_PAYLOAD"

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
        print_result 0 "API key secret created successfully"
        echo -e "${YELLOW}Vault ID: ${VAULT_ID}${NC}"
    else
        print_result 1 "Secret creation returned 201 but no vault_id found"
    fi
else
    print_result 1 "Failed to create API key secret"
fi

# Test 2: Create Database Password Secret
print_section "Test 2: Create Database Password Secret"
echo "POST ${API_BASE}/secrets"
DB_SECRET_PAYLOAD='{
  "name": "Production Database Password",
  "description": "PostgreSQL production database credentials",
  "secret_type": "database_credential",
  "provider": "custom",
  "secret_value": "SuperSecureP@ssw0rd!2024",
  "tags": ["database", "production", "postgresql"],
  "metadata": {
    "environment": "production",
    "database": "main_db",
    "db_type": "postgresql"
  },
  "rotation_enabled": true,
  "rotation_days": 30
}'
echo "Request Body:"
pretty_json "$DB_SECRET_PAYLOAD"

DB_CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/secrets" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: ${TEST_USER_ID}" \
  -d "$DB_SECRET_PAYLOAD")
HTTP_CODE=$(echo "$DB_CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DB_CREATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

DB_VAULT_ID=""
if [ "$HTTP_CODE" = "201" ]; then
    DB_VAULT_ID=$(json_value "$RESPONSE_BODY" "vault_id")
    if [ -n "$DB_VAULT_ID" ] && [ "$DB_VAULT_ID" != "null" ]; then
        print_result 0 "Database password secret created successfully"
        echo -e "${YELLOW}DB Vault ID: ${DB_VAULT_ID}${NC}"
    else
        print_result 1 "DB secret creation returned 201 but no vault_id found"
    fi
else
    print_result 1 "Failed to create database password secret"
fi

# Test 3: List All Secrets
print_section "Test 3: List All Secrets"
echo "GET ${API_BASE}/secrets?page=1&page_size=10"
LIST_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/secrets?page=1&page_size=10" \
  -H "X-User-Id: ${TEST_USER_ID}")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Secrets listed successfully"
else
    print_result 1 "Failed to list secrets"
fi

# Test 4: Get Secret (Encrypted - No Decrypt)
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 4: Get Secret (Encrypted)"
    echo "GET ${API_BASE}/secrets/${VAULT_ID}?decrypt=false"
    
    GET_ENCRYPTED_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/secrets/${VAULT_ID}?decrypt=false" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$GET_ENCRYPTED_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_ENCRYPTED_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        SECRET_VALUE=$(json_value "$RESPONSE_BODY" "secret_value")
        if [ "$SECRET_VALUE" = "[ENCRYPTED]" ]; then
            print_result 0 "Secret retrieved in encrypted form"
        else
            print_result 1 "Expected [ENCRYPTED] but got different value"
        fi
    else
        print_result 1 "Failed to get encrypted secret"
    fi
else
    echo -e "${YELLOW}Skipping Test 4: No vault ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: Get Secret (Decrypted)
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 5: Get Secret (Decrypted)"
    echo "GET ${API_BASE}/secrets/${VAULT_ID}?decrypt=true"
    
    GET_DECRYPTED_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/secrets/${VAULT_ID}?decrypt=true" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$GET_DECRYPTED_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_DECRYPTED_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        SECRET_VALUE=$(json_value "$RESPONSE_BODY" "secret_value")
        if [ "$SECRET_VALUE" != "[ENCRYPTED]" ] && [ -n "$SECRET_VALUE" ]; then
            print_result 0 "Secret retrieved and decrypted successfully"
            echo -e "${YELLOW}Secret value retrieved (hidden for security)${NC}"
        else
            print_result 1 "Secret decryption failed or returned [ENCRYPTED]"
        fi
    else
        print_result 1 "Failed to get decrypted secret"
    fi
else
    echo -e "${YELLOW}Skipping Test 5: No vault ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Update Secret Metadata
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 6: Update Secret Metadata"
    echo "PUT ${API_BASE}/secrets/${VAULT_ID}"
    UPDATE_PAYLOAD='{
      "name": "Test API Key (Updated)",
      "description": "Updated test API key description",
      "tags": ["test", "api", "openai", "updated"],
      "metadata": {
        "environment": "test",
        "purpose": "testing",
        "updated": true
      }
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PAYLOAD"
    
    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/secrets/${VAULT_ID}" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$UPDATE_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret metadata updated successfully"
    else
        print_result 1 "Failed to update secret metadata"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No vault ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Rotate Secret
if [ -n "$DB_VAULT_ID" ] && [ "$DB_VAULT_ID" != "null" ]; then
    print_section "Test 7: Rotate Secret"
    echo "POST ${API_BASE}/secrets/${DB_VAULT_ID}/rotate?new_secret_value=NewRotatedP%40ssw0rd%212024"
    
    ROTATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
      "${API_BASE}/secrets/${DB_VAULT_ID}/rotate?new_secret_value=NewRotatedP%40ssw0rd%212024" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$ROTATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$ROTATE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret rotated successfully"
    else
        print_result 1 "Failed to rotate secret"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No DB vault ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Filter Secrets by Type
print_section "Test 8: Filter Secrets by Type"
echo "GET ${API_BASE}/secrets?secret_type=api_key&page=1&page_size=10"
FILTER_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/secrets?secret_type=api_key&page=1&page_size=10" \
  -H "X-User-Id: ${TEST_USER_ID}")
HTTP_CODE=$(echo "$FILTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$FILTER_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Secrets filtered by type successfully"
else
    print_result 1 "Failed to filter secrets by type"
fi

# Test 9: Filter Secrets by Tags
print_section "Test 9: Filter Secrets by Tags"
echo "GET ${API_BASE}/secrets?tags=test,api&page=1&page_size=10"
TAG_FILTER_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/secrets?tags=test,api&page=1&page_size=10" \
  -H "X-User-Id: ${TEST_USER_ID}")
HTTP_CODE=$(echo "$TAG_FILTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TAG_FILTER_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Secrets filtered by tags successfully"
else
    print_result 1 "Failed to filter secrets by tags"
fi

# Test 10: Share Secret with Another User
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 10: Share Secret with Another User"
    echo "POST ${API_BASE}/secrets/${VAULT_ID}/share"
    SHARE_PAYLOAD='{
      "shared_with_user_id": "test_user_vault_456",
      "permission_level": "read"
    }'
    echo "Request Body:"
    pretty_json "$SHARE_PAYLOAD"
    
    SHARE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/secrets/${VAULT_ID}/share" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$SHARE_PAYLOAD")
    HTTP_CODE=$(echo "$SHARE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$SHARE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret shared successfully"
    else
        print_result 1 "Failed to share secret"
    fi
else
    echo -e "${YELLOW}Skipping Test 10: No vault ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 11: Get Shared Secrets
print_section "Test 11: Get Shared Secrets"
echo "GET ${API_BASE}/shared"
SHARED_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/shared" \
  -H "X-User-Id: ${TEST_USER_ID}")
HTTP_CODE=$(echo "$SHARED_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SHARED_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Shared secrets retrieved successfully"
else
    print_result 1 "Failed to get shared secrets"
fi

# Test 12: Get Vault Statistics
print_section "Test 12: Get Vault Statistics"
echo "GET ${API_BASE}/stats"
STATS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/stats" \
  -H "X-User-Id: ${TEST_USER_ID}")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Vault statistics retrieved successfully"
else
    print_result 1 "Failed to get vault statistics"
fi

# Test 13: Get Audit Logs
print_section "Test 13: Get Audit Logs"
echo "GET ${API_BASE}/audit-logs?page=1&page_size=20"
AUDIT_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/audit-logs?page=1&page_size=20" \
  -H "X-User-Id: ${TEST_USER_ID}")
HTTP_CODE=$(echo "$AUDIT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$AUDIT_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Audit logs retrieved successfully"
else
    print_result 1 "Failed to get audit logs"
fi

# Test 14: Get Audit Logs for Specific Vault
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 14: Get Audit Logs for Specific Vault"
    echo "GET ${API_BASE}/audit-logs?vault_id=${VAULT_ID}&page=1&page_size=10"
    
    VAULT_AUDIT_RESPONSE=$(curl -s -w "\n%{http_code}" \
      "${API_BASE}/audit-logs?vault_id=${VAULT_ID}&page=1&page_size=10" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$VAULT_AUDIT_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$VAULT_AUDIT_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Vault-specific audit logs retrieved successfully"
    else
        print_result 1 "Failed to get vault-specific audit logs"
    fi
else
    echo -e "${YELLOW}Skipping Test 14: No vault ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 15: Test Credential
if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    print_section "Test 15: Test Credential"
    echo "POST ${API_BASE}/secrets/${VAULT_ID}/test"
    
    TEST_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/secrets/${VAULT_ID}/test" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d '{}')
    HTTP_CODE=$(echo "$TEST_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$TEST_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Credential tested successfully"
    else
        print_result 1 "Failed to test credential"
    fi
else
    echo -e "${YELLOW}Skipping Test 15: No vault ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 16: Delete Secret
if [ -n "$DB_VAULT_ID" ] && [ "$DB_VAULT_ID" != "null" ]; then
    print_section "Test 16: Delete Secret"
    echo "DELETE ${API_BASE}/secrets/${DB_VAULT_ID}"
    
    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/secrets/${DB_VAULT_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Secret deleted successfully"
    else
        print_result 1 "Failed to delete secret"
    fi
else
    echo -e "${YELLOW}Skipping Test 16: No DB vault ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 17: Verify Secret is Deleted
if [ -n "$DB_VAULT_ID" ] && [ "$DB_VAULT_ID" != "null" ]; then
    print_section "Test 17: Verify Secret is Deleted"
    echo "GET ${API_BASE}/secrets/${DB_VAULT_ID}"
    
    VERIFY_DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/secrets/${DB_VAULT_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    HTTP_CODE=$(echo "$VERIFY_DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$VERIFY_DELETE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "400" ]; then
        print_result 0 "Deleted secret is no longer accessible"
    else
        print_result 1 "Deleted secret is still accessible (should return 404)"
    fi
else
    echo -e "${YELLOW}Skipping Test 17: No DB vault ID available${NC}"
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
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Please review the output above.${NC}"
    exit 1
fi

