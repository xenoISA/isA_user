#!/bin/bash
# Storage Service - File Operations Test Script (v2 - using test_common.sh)
# Usage:
#   ./1_file_operations_v2.sh              # Direct mode (default)
#   TEST_MODE=gateway ./1_file_operations_v2.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="storage_service"
API_PATH="/api/v1/storage"

# Initialize test (sets up BASE_URL, API_BASE, JWT if needed)
init_test

# ============================================================================
# Test Setup
# ============================================================================
print_info "Using test user: $TEST_USER_ID"
echo ""

# Create test files
TEST_FILE="/tmp/storage_test_file_$(date +%s).txt"
echo "This is a test file for storage service testing." > "$TEST_FILE"
echo "Created at: $(date)" >> "$TEST_FILE"
echo "Test user: $TEST_USER_ID" >> "$TEST_FILE"

TEST_FILE_2="/tmp/storage_indexed_file_$(date +%s).txt"
cat > "$TEST_FILE_2" << EOF
This is a comprehensive test document for the storage service.
It contains multiple paragraphs to test the intelligent indexing feature.
The storage service integrates with MinIO for scalable object storage.
EOF

# ============================================================================
# Tests
# ============================================================================

# Test 1: Upload File
print_section "Test 1: Upload File"
echo "POST ${API_PATH}/files/upload"

UPLOAD_RESPONSE=$(api_post_form "/files/upload" \
  -F "file=@${TEST_FILE}" \
  -F "user_id=${TEST_USER_ID}" \
  -F "access_level=private" \
  -F "tags=test,automated,storage" \
  -F "enable_indexing=false" \
  -F "metadata={\"test\":true,\"purpose\":\"automated_testing\"}")

echo "$UPLOAD_RESPONSE" | json_pretty

if json_has "$UPLOAD_RESPONSE" "file_id"; then
    FILE_ID=$(json_get "$UPLOAD_RESPONSE" "file_id")
    print_success "File uploaded: $FILE_ID"
    test_result 0
else
    print_error "Upload failed"
    test_result 1
    FILE_ID=""
fi
echo ""

# Test 2: List Files
print_section "Test 2: List User Files"
echo "GET ${API_PATH}/files?user_id=${TEST_USER_ID}"

RESPONSE=$(api_get "/files?user_id=${TEST_USER_ID}&limit=10")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q '\['; then
    FILE_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
    print_success "Found $FILE_COUNT files"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 3: Get File Info
if [ -n "$FILE_ID" ]; then
    print_section "Test 3: Get File Information"
    echo "GET ${API_PATH}/files/${FILE_ID}?user_id=${TEST_USER_ID}"

    RESPONSE=$(api_get "/files/${FILE_ID}?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "file_id"; then
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    print_section "Test 3: Get File Information - SKIPPED (no file_id)"
    echo ""
fi

# Test 4: Get Download URL
if [ -n "$FILE_ID" ]; then
    print_section "Test 4: Get File Download URL"
    echo "GET ${API_PATH}/files/${FILE_ID}/download?user_id=${TEST_USER_ID}"

    RESPONSE=$(api_get "/files/${FILE_ID}/download?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "download_url"; then
        print_success "Download URL obtained"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    print_section "Test 4: Get File Download URL - SKIPPED (no file_id)"
    echo ""
fi

# Test 5: Upload File with Auto-Indexing
print_section "Test 5: Upload File with Auto-Indexing"
echo "POST ${API_PATH}/files/upload (with enable_indexing=true)"

UPLOAD_RESPONSE_2=$(api_post_form "/files/upload" \
  -F "file=@${TEST_FILE_2}" \
  -F "user_id=${TEST_USER_ID}" \
  -F "access_level=private" \
  -F "tags=indexed,searchable,test" \
  -F "enable_indexing=true" \
  -F "metadata={\"indexed\":true,\"content_type\":\"text\"}")

echo "$UPLOAD_RESPONSE_2" | json_pretty

if json_has "$UPLOAD_RESPONSE_2" "file_id"; then
    FILE_ID_2=$(json_get "$UPLOAD_RESPONSE_2" "file_id")
    print_success "File uploaded with indexing: $FILE_ID_2"
    test_result 0
else
    print_error "Upload with indexing failed"
    test_result 1
    FILE_ID_2=""
fi
echo ""

# Test 6: List Files with Filters
print_section "Test 6: List Files with Filters"
echo "GET ${API_PATH}/files?user_id=${TEST_USER_ID}&prefix=storage&status=available"

RESPONSE=$(api_get "/files?user_id=${TEST_USER_ID}&prefix=storage&status=available&limit=5")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q '\['; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 7: Delete File (Soft Delete)
if [ -n "$FILE_ID" ]; then
    print_section "Test 7: Delete File (Soft Delete)"
    echo "DELETE ${API_PATH}/files/${FILE_ID}?user_id=${TEST_USER_ID}"

    RESPONSE=$(api_delete "/files/${FILE_ID}?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "deleted successfully"; then
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    print_section "Test 7: Delete File - SKIPPED (no file_id)"
    echo ""
fi

# Test 8: Verify File is Deleted
if [ -n "$FILE_ID" ]; then
    print_section "Test 8: Verify File is Deleted"
    echo "GET ${API_PATH}/files/${FILE_ID}?user_id=${TEST_USER_ID}"

    RESPONSE=$(api_get "/files/${FILE_ID}?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "not found\|deleted"; then
        print_success "File confirmed deleted"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    print_section "Test 8: Verify File is Deleted - SKIPPED"
    echo ""
fi

# Test 9: Permanent Delete
if [ -n "$FILE_ID_2" ]; then
    print_section "Test 9: Permanent Delete File"
    echo "DELETE ${API_PATH}/files/${FILE_ID_2}?user_id=${TEST_USER_ID}&permanent=true"

    RESPONSE=$(api_delete "/files/${FILE_ID_2}?user_id=${TEST_USER_ID}&permanent=true")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "deleted successfully"; then
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    print_section "Test 9: Permanent Delete File - SKIPPED"
    echo ""
fi

# ============================================================================
# Cleanup
# ============================================================================
rm -f "$TEST_FILE" "$TEST_FILE_2"

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
