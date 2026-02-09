#!/bin/bash
# Document Service Test Script (v2 - using test_common.sh)
# Usage:
#   ./document_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./document_test_v2.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="document_service"
API_PATH="/api/v1/documents"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_DOC_USER="doc_test_user_${TEST_TS}"

print_info "Test User ID: $TEST_DOC_USER"
echo ""

# ============================================================================
# Setup: Create Test User
# ============================================================================
print_section "Setup: Create Test User"
ACCOUNT_URL="http://localhost:$(get_service_port account_service)/api/v1/accounts/ensure"
USER_RESPONSE=$(curl -s -X POST "$ACCOUNT_URL" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"${TEST_DOC_USER}\",\"email\":\"doc_${TEST_TS}@example.com\",\"name\":\"Document Test User\",\"subscription_plan\":\"free\"}")
echo "$USER_RESPONSE" | json_pretty
echo ""

# ============================================================================
# Tests
# ============================================================================

# Test 1: Get Document Stats
print_section "Test 1: Get Document Stats"
echo "GET ${API_PATH}/stats?user_id=${TEST_DOC_USER}"
RESPONSE=$(api_get "/stats?user_id=${TEST_DOC_USER}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "total_documents" || json_has "$RESPONSE" "user_id"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Upload File to Storage Service First
print_section "Test 2: Upload File to Storage"
echo "POST /api/v1/storage/files/upload"

# Create temp file
TEST_FILE="/tmp/test_doc_${TEST_TS}.txt"
echo "This is a test document content for testing purposes. Created at ${TEST_TS}." > "$TEST_FILE"

STORAGE_URL="http://localhost:$(get_service_port storage_service)/api/v1/storage/files/upload"
UPLOAD_RESPONSE=$(curl -s -X POST "$STORAGE_URL" \
  -F "file=@${TEST_FILE}" \
  -F "user_id=${TEST_DOC_USER}" \
  -F "access_level=private" \
  -F "enable_indexing=false")
echo "$UPLOAD_RESPONSE" | json_pretty
rm -f "$TEST_FILE"

FILE_ID=$(json_get "$UPLOAD_RESPONSE" "file_id")
if [ -n "$FILE_ID" ] && [ "$FILE_ID" != "null" ] && [ "$FILE_ID" != "" ]; then
    print_success "Uploaded file: $FILE_ID"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 3: Create Document with file_id
print_section "Test 3: Create Document"
echo "POST ${API_PATH}?user_id=${TEST_DOC_USER}"
print_info "Expected Event: document.created"

if [ -n "$FILE_ID" ] && [ "$FILE_ID" != "null" ]; then
    DOC_PAYLOAD="{
      \"title\": \"Test Document ${TEST_TS}\",
      \"description\": \"Test document for service testing\",
      \"doc_type\": \"txt\",
      \"file_id\": \"${FILE_ID}\",
      \"access_level\": \"private\",
      \"tags\": [\"test\", \"document\", \"automated\"]
    }"
    RESPONSE=$(api_post "?user_id=${TEST_DOC_USER}" "$DOC_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    DOC_ID=$(json_get "$RESPONSE" "doc_id")
    if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "null" ] && [ "$DOC_ID" != "" ]; then
        print_success "Created document: $DOC_ID"
        test_result 0
    else
        test_result 1
    fi
else
    print_info "SKIPPED - No file_id available"
    test_result 0
fi
echo ""

# Test 4: Get Document Details
if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "null" ]; then
    print_section "Test 4: Get Document Details"
    echo "GET ${API_PATH}/${DOC_ID}?user_id=${TEST_DOC_USER}"
    RESPONSE=$(api_get "/${DOC_ID}?user_id=${TEST_DOC_USER}")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "$DOC_ID" || json_has "$RESPONSE" "title"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 3: SKIPPED - No document ID"
fi
echo ""

# Test 4: List Documents
print_section "Test 4: List User Documents"
echo "GET ${API_PATH}?user_id=${TEST_DOC_USER}"
RESPONSE=$(api_get "?user_id=${TEST_DOC_USER}&limit=10")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q "\[" || json_has "$RESPONSE" "documents"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 5: Update Document
if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "null" ]; then
    print_section "Test 5: Update Document"
    echo "PUT ${API_PATH}/${DOC_ID}/update?user_id=${TEST_DOC_USER}"
    print_info "Expected Event: document.updated"

    UPDATE_PAYLOAD="{
      \"title\": \"Updated Test Document ${TEST_TS}\",
      \"description\": \"Updated description\"
    }"
    RESPONSE=$(api_put "/${DOC_ID}/update?user_id=${TEST_DOC_USER}" "$UPDATE_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "Updated Test Document" || json_has "$RESPONSE" "doc_id"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 5: SKIPPED - No document ID"
fi
echo ""

# Test 6: Get Document Permissions
if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "null" ]; then
    print_section "Test 6: Get Document Permissions"
    echo "GET ${API_PATH}/${DOC_ID}/permissions?user_id=${TEST_DOC_USER}"
    RESPONSE=$(api_get "/${DOC_ID}/permissions?user_id=${TEST_DOC_USER}")
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "doc_id" || json_has "$RESPONSE" "access_level" || json_has "$RESPONSE" "permissions"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 6: SKIPPED - No document ID"
fi
echo ""

# Test 7: Update Document Permissions
if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "null" ]; then
    print_section "Test 7: Update Document Permissions"
    echo "PUT ${API_PATH}/${DOC_ID}/permissions?user_id=${TEST_DOC_USER}"

    PERM_PAYLOAD="{
      \"access_level\": \"shared\",
      \"shared_with\": [\"test_user_2\"]
    }"
    RESPONSE=$(api_put "/${DOC_ID}/permissions?user_id=${TEST_DOC_USER}" "$PERM_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "doc_id" || json_has "$RESPONSE" "access_level" || echo "$RESPONSE" | grep -q "success\|message"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 7: SKIPPED - No document ID"
fi
echo ""

# Test 8: Semantic Search
print_section "Test 8: Semantic Search"
echo "POST ${API_PATH}/search?user_id=${TEST_DOC_USER}"

SEARCH_PAYLOAD="{
  \"query\": \"test document\",
  \"limit\": 5
}"
RESPONSE=$(api_post "/search?user_id=${TEST_DOC_USER}" "$SEARCH_PAYLOAD")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "results" || echo "$RESPONSE" | grep -q "\[\|documents\|query"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 9: Delete Document
if [ -n "$DOC_ID" ] && [ "$DOC_ID" != "null" ]; then
    print_section "Test 9: Delete Document"
    echo "DELETE ${API_PATH}/${DOC_ID}?user_id=${TEST_DOC_USER}&permanent=false"
    print_info "Expected Event: document.deleted"

    RESPONSE=$(api_delete "/${DOC_ID}?user_id=${TEST_DOC_USER}&permanent=false")
    echo "$RESPONSE" | json_pretty

    if [ -z "$RESPONSE" ] || echo "$RESPONSE" | grep -q "success\|deleted\|message"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 9: SKIPPED - No document ID"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
