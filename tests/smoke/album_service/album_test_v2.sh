#!/bin/bash
# Album Service Test Script (v2 - using test_common.sh)
# Usage:
#   ./album_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./album_test_v2.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="album_service"
API_PATH="/api/v1/albums"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
ALBUM_NAME="Test Album ${TEST_TS}"

print_info "Test User ID: $TEST_USER_ID"
print_info "Album Name: $ALBUM_NAME"
echo ""

# ============================================================================
# Tests
# ============================================================================

# Test 1: List Albums
print_section "Test 1: List User's Albums"
echo "GET ${API_PATH}?user_id=$TEST_USER_ID"
RESPONSE=$(api_get "?user_id=${TEST_USER_ID}")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "albums" && json_has "$RESPONSE" "total_count"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Create Album
print_section "Test 2: Create Album"
echo "POST ${API_PATH}?user_id=$TEST_USER_ID"
print_info "Expected Event: album.created"

PAYLOAD="{\"name\":\"${ALBUM_NAME}\",\"description\":\"Test album for event testing\"}"
RESPONSE=$(api_post "?user_id=${TEST_USER_ID}" "$PAYLOAD")
echo "$RESPONSE" | json_pretty

CREATED_ALBUM_ID=$(json_get "$RESPONSE" "album_id")
if [ -n "$CREATED_ALBUM_ID" ] && echo "$RESPONSE" | grep -q "$ALBUM_NAME"; then
    print_success "Created album: $CREATED_ALBUM_ID"
    test_result 0
else
    print_error "Failed to create album"
    CREATED_ALBUM_ID="test_album_001"
    test_result 1
fi
echo ""

# Test 3: Get Album Details
print_section "Test 3: Get Album Details"
echo "GET ${API_PATH}/${CREATED_ALBUM_ID}?user_id=$TEST_USER_ID"
RESPONSE=$(api_get "/${CREATED_ALBUM_ID}?user_id=${TEST_USER_ID}")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "$CREATED_ALBUM_ID"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 4: Update Album
print_section "Test 4: Update Album Metadata"
echo "PUT ${API_PATH}/${CREATED_ALBUM_ID}?user_id=$TEST_USER_ID"

UPDATED_NAME="Updated ${ALBUM_NAME}"
UPDATE_PAYLOAD="{\"name\":\"${UPDATED_NAME}\",\"description\":\"Updated description\"}"
RESPONSE=$(api_put "/${CREATED_ALBUM_ID}?user_id=${TEST_USER_ID}" "$UPDATE_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "$UPDATED_NAME" || json_has "$RESPONSE" "album_id"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 5: Add Photos to Album
print_section "Test 5: Add Photos to Album"
echo "POST ${API_PATH}/${CREATED_ALBUM_ID}/photos?user_id=$TEST_USER_ID"
print_info "Expected Event: album.photo_added"

PHOTO_ID1="test_photo_${TEST_TS}_1"
PHOTO_ID2="test_photo_${TEST_TS}_2"
ADD_PHOTOS_PAYLOAD="{\"photo_ids\":[\"${PHOTO_ID1}\",\"${PHOTO_ID2}\"]}"
RESPONSE=$(api_post "/${CREATED_ALBUM_ID}/photos?user_id=${TEST_USER_ID}" "$ADD_PHOTOS_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "added\|success" || json_has "$RESPONSE" "message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 6: Get Album Photos
print_section "Test 6: Get Album Photos"
echo "GET ${API_PATH}/${CREATED_ALBUM_ID}/photos?user_id=$TEST_USER_ID"
RESPONSE=$(api_get "/${CREATED_ALBUM_ID}/photos?user_id=${TEST_USER_ID}")
echo "$RESPONSE" | json_pretty | head -20

if echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 7: Remove Photos from Album
print_section "Test 7: Remove Photos from Album"
echo "DELETE ${API_PATH}/${CREATED_ALBUM_ID}/photos?user_id=$TEST_USER_ID"
print_info "Expected Event: album.photo_removed"

# Need custom delete with body
REMOVE_PHOTOS_PAYLOAD="{\"photo_ids\":[\"${PHOTO_ID1}\"]}"
if [ -n "$AUTH_HEADER" ]; then
    RESPONSE=$(curl -s -X DELETE -H "$AUTH_HEADER" -H "Content-Type: application/json" \
        -d "$REMOVE_PHOTOS_PAYLOAD" "${API_BASE}/${CREATED_ALBUM_ID}/photos?user_id=${TEST_USER_ID}")
else
    RESPONSE=$(curl -s -X DELETE -H "Content-Type: application/json" \
        -d "$REMOVE_PHOTOS_PAYLOAD" "${API_BASE}/${CREATED_ALBUM_ID}/photos?user_id=${TEST_USER_ID}")
fi
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "removed\|success\|message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 8: Delete Album
print_section "Test 8: Delete Album"
echo "DELETE ${API_PATH}/${CREATED_ALBUM_ID}?user_id=$TEST_USER_ID"
print_info "Expected Event: album.deleted"

RESPONSE=$(api_delete "/${CREATED_ALBUM_ID}?user_id=${TEST_USER_ID}")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "deleted successfully\|message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
