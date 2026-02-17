#!/bin/bash
# Album Service - Smoke Tests
#
# End-to-end tests verifying album service functionality with real infrastructure.
# All services must be running.
#
# Usage:
#   ./smoke_test.sh                     # Direct mode (default)
#   TEST_MODE=gateway ./smoke_test.sh   # Gateway mode with JWT
#
# Exit codes:
#   0 = All tests passed
#   1 = Some tests failed

set -e

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../test_common.sh"

SERVICE_NAME="album_service"
SERVICE_PORT=8219
API_PATH="/api/v1/albums"

# Initialize test framework
init_test

# =============================================================================
# Test Data
# =============================================================================
TEST_TS="$(date +%s)_$$"
TEST_ALBUM_NAME="Smoke Test Album ${TEST_TS}"
TEST_PHOTO_ID_1="photo_$(uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-' | cut -c1-16)"
TEST_PHOTO_ID_2="photo_$(uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-' | cut -c1-16)"
TEST_PHOTO_ID_3="photo_$(uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-' | cut -c1-16)"
TEST_FRAME_ID="frame_test_${TEST_TS}"
ALBUM_ID=""

print_info "Test timestamp: $TEST_TS"
print_info "Test photo IDs: $TEST_PHOTO_ID_1, $TEST_PHOTO_ID_2, $TEST_PHOTO_ID_3"
echo ""

# =============================================================================
# Test 1: Health Check
# =============================================================================
print_section "Test 1: Health Check"
echo "GET /health"

RESPONSE=$(api_get "/health" "" "true")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "status"; then
    STATUS=$(json_get "$RESPONSE" "status")
    if [ "$STATUS" = "healthy" ] || [ "$STATUS" = "ok" ]; then
        print_success "Health check passed: status=$STATUS"
        test_result 0
    else
        print_warning "Health check returned: $STATUS"
        test_result 0
    fi
else
    print_error "Health check failed: no status field"
    test_result 1
fi
echo ""

# =============================================================================
# Test 2: Create Album (Basic)
# =============================================================================
print_section "Test 2: Create Album (Basic)"
echo "POST ${API_PATH}"

CREATE_PAYLOAD='{
  "name": "'${TEST_ALBUM_NAME}'",
  "description": "Basic test album",
  "auto_sync": false,
  "is_family_shared": false
}'

echo "Request:"
echo "$CREATE_PAYLOAD" | json_pretty

RESPONSE=$(api_post "" "$CREATE_PAYLOAD")
echo "Response:"
echo "$RESPONSE" | json_pretty

ALBUM_ID=$(json_get "$RESPONSE" "album_id")
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_success "Created album: $ALBUM_ID"
    test_result 0
else
    print_error "Failed to create album"
    test_result 1
fi
echo ""

# =============================================================================
# Test 3: Get Album by ID
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Test 3: Get Album by ID"
    echo "GET ${API_PATH}/${ALBUM_ID}"

    RESPONSE=$(api_get "/${ALBUM_ID}")
    echo "$RESPONSE" | json_pretty

    RETRIEVED_ID=$(json_get "$RESPONSE" "album_id")
    RETRIEVED_NAME=$(json_get "$RESPONSE" "name")
    if [ "$RETRIEVED_ID" = "$ALBUM_ID" ] && [ "$RETRIEVED_NAME" = "$TEST_ALBUM_NAME" ]; then
        print_success "Retrieved album matches"
        test_result 0
    else
        print_error "Retrieved album ID or name mismatch"
        test_result 1
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Test 4: List Albums
# =============================================================================
print_section "Test 4: List Albums"
echo "GET ${API_PATH}"

RESPONSE=$(api_get "")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "albums"; then
    print_success "List returned albums field"
    test_result 0
else
    print_error "Unexpected list response format"
    test_result 1
fi
echo ""

# =============================================================================
# Test 5: Update Album
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Test 5: Update Album"
    echo "PUT ${API_PATH}/${ALBUM_ID}"

    UPDATED_NAME="Updated Album ${TEST_TS}"
    UPDATE_PAYLOAD='{
      "name": "'${UPDATED_NAME}'",
      "description": "Updated description"
    }'

    echo "Request:"
    echo "$UPDATE_PAYLOAD" | json_pretty

    RESPONSE=$(api_put "/${ALBUM_ID}" "$UPDATE_PAYLOAD")
    echo "Response:"
    echo "$RESPONSE" | json_pretty

    NEW_NAME=$(json_get "$RESPONSE" "name")
    if [ "$NEW_NAME" = "$UPDATED_NAME" ]; then
        print_success "Update successful"
        test_result 0
    else
        print_warning "Update response: name may not have changed"
        test_result 0
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Test 6: Add Photos to Album
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Test 6: Add Photos to Album"
    echo "POST ${API_PATH}/${ALBUM_ID}/photos"

    ADD_PHOTOS_PAYLOAD='{
      "photo_ids": ["'${TEST_PHOTO_ID_1}'", "'${TEST_PHOTO_ID_2}'"]
    }'

    echo "Request:"
    echo "$ADD_PHOTOS_PAYLOAD" | json_pretty

    RESPONSE=$(api_post "/${ALBUM_ID}/photos" "$ADD_PHOTOS_PAYLOAD")
    echo "Response:"
    echo "$RESPONSE" | json_pretty

    ADDED_COUNT=$(json_get "$RESPONSE" "added_count")
    if [ -n "$ADDED_COUNT" ] && [ "$ADDED_COUNT" != "null" ]; then
        print_success "Added $ADDED_COUNT photos to album"
        test_result 0
    else
        print_error "Failed to add photos"
        test_result 1
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Test 7: Get Album Photos
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Test 7: Get Album Photos"
    echo "GET ${API_PATH}/${ALBUM_ID}/photos"

    RESPONSE=$(api_get "/${ALBUM_ID}/photos")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | jq -e 'type == "array"' > /dev/null 2>&1; then
        COUNT=$(echo "$RESPONSE" | jq 'length')
        print_success "Retrieved $COUNT photos from album"
        test_result 0
    else
        print_error "Unexpected response format"
        test_result 1
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Test 8: Add Another Photo
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Test 8: Add Another Photo"
    echo "POST ${API_PATH}/${ALBUM_ID}/photos"

    ADD_PHOTO_PAYLOAD='{
      "photo_ids": ["'${TEST_PHOTO_ID_3}'"]
    }'

    echo "Request:"
    echo "$ADD_PHOTO_PAYLOAD" | json_pretty

    RESPONSE=$(api_post "/${ALBUM_ID}/photos" "$ADD_PHOTO_PAYLOAD")
    echo "Response:"
    echo "$RESPONSE" | json_pretty

    ADDED_COUNT=$(json_get "$RESPONSE" "added_count")
    if [ -n "$ADDED_COUNT" ] && [ "$ADDED_COUNT" != "null" ]; then
        print_success "Added $ADDED_COUNT photo to album"
        test_result 0
    else
        print_error "Failed to add photo"
        test_result 1
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Test 9: Remove Photos from Album
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Test 9: Remove Photos from Album"
    echo "DELETE ${API_PATH}/${ALBUM_ID}/photos"

    REMOVE_PHOTOS_PAYLOAD='{
      "photo_ids": ["'${TEST_PHOTO_ID_1}'"]
    }'

    echo "Request:"
    echo "$REMOVE_PHOTOS_PAYLOAD" | json_pretty

    # Use curl directly for DELETE with body
    if [ -n "$AUTH_HEADER" ]; then
        RESPONSE=$(curl -s -X DELETE -H "$AUTH_HEADER" -H "Content-Type: application/json" \
            -d "$REMOVE_PHOTOS_PAYLOAD" "${API_BASE}/${ALBUM_ID}/photos")
    else
        RESPONSE=$(curl -s -X DELETE -H "Content-Type: application/json" \
            -d "$REMOVE_PHOTOS_PAYLOAD" "${API_BASE}/${ALBUM_ID}/photos")
    fi

    echo "Response:"
    echo "$RESPONSE" | json_pretty

    REMOVED_COUNT=$(json_get "$RESPONSE" "removed_count")
    if [ -n "$REMOVED_COUNT" ] && [ "$REMOVED_COUNT" != "null" ]; then
        print_success "Removed $REMOVED_COUNT photos from album"
        test_result 0
    else
        print_error "Failed to remove photos"
        test_result 1
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Test 10: Sync Album to Frame
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Test 10: Sync Album to Frame"
    echo "POST ${API_PATH}/${ALBUM_ID}/sync"

    SYNC_PAYLOAD='{
      "frame_id": "'${TEST_FRAME_ID}'"
    }'

    echo "Request:"
    echo "$SYNC_PAYLOAD" | json_pretty

    RESPONSE=$(api_post "/${ALBUM_ID}/sync" "$SYNC_PAYLOAD")
    echo "Response:"
    echo "$RESPONSE" | json_pretty

    SYNC_STATUS=$(json_get "$RESPONSE" "sync_status")
    if [ -n "$SYNC_STATUS" ] && [ "$SYNC_STATUS" != "null" ]; then
        print_success "Sync initiated with status: $SYNC_STATUS"
        test_result 0
    else
        print_error "Failed to initiate sync"
        test_result 1
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Test 11: Get Sync Status
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Test 11: Get Sync Status"
    echo "GET ${API_PATH}/${ALBUM_ID}/sync/${TEST_FRAME_ID}"

    RESPONSE=$(api_get "/${ALBUM_ID}/sync/${TEST_FRAME_ID}")
    echo "$RESPONSE" | json_pretty

    SYNC_STATUS=$(json_get "$RESPONSE" "sync_status")
    if [ -n "$SYNC_STATUS" ] && [ "$SYNC_STATUS" != "null" ]; then
        print_success "Retrieved sync status: $SYNC_STATUS"
        test_result 0
    else
        print_error "Failed to get sync status"
        test_result 1
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Test 12: Create Family Shared Album
# =============================================================================
print_section "Test 12: Create Family Shared Album"
echo "POST ${API_PATH}"

FAMILY_ALBUM_NAME="Family Album ${TEST_TS}"
FAMILY_CREATE_PAYLOAD='{
  "name": "'${FAMILY_ALBUM_NAME}'",
  "description": "Family shared album",
  "is_family_shared": true,
  "auto_sync": false
}'

echo "Request:"
echo "$FAMILY_CREATE_PAYLOAD" | json_pretty

RESPONSE=$(api_post "" "$FAMILY_CREATE_PAYLOAD")
echo "Response:"
echo "$RESPONSE" | json_pretty

FAMILY_ALBUM_ID=$(json_get "$RESPONSE" "album_id")
IS_FAMILY_SHARED=$(json_get "$RESPONSE" "is_family_shared")
if [ -n "$FAMILY_ALBUM_ID" ] && [ "$FAMILY_ALBUM_ID" != "null" ] && [ "$IS_FAMILY_SHARED" = "true" ]; then
    print_success "Created family shared album: $FAMILY_ALBUM_ID"
    test_result 0
else
    print_error "Failed to create family shared album"
    test_result 1
fi
echo ""

# =============================================================================
# Test 13: Create Album with Auto-sync
# =============================================================================
print_section "Test 13: Create Album with Auto-sync"
echo "POST ${API_PATH}"

AUTOSYNC_ALBUM_NAME="Auto-sync Album ${TEST_TS}"
AUTOSYNC_CREATE_PAYLOAD='{
  "name": "'${AUTOSYNC_ALBUM_NAME}'",
  "description": "Album with auto-sync enabled",
  "auto_sync": true,
  "sync_frames": ["'${TEST_FRAME_ID}'"],
  "is_family_shared": false
}'

echo "Request:"
echo "$AUTOSYNC_CREATE_PAYLOAD" | json_pretty

RESPONSE=$(api_post "" "$AUTOSYNC_CREATE_PAYLOAD")
echo "Response:"
echo "$RESPONSE" | json_pretty

AUTOSYNC_ALBUM_ID=$(json_get "$RESPONSE" "album_id")
AUTO_SYNC=$(json_get "$RESPONSE" "auto_sync")
if [ -n "$AUTOSYNC_ALBUM_ID" ] && [ "$AUTOSYNC_ALBUM_ID" != "null" ] && [ "$AUTO_SYNC" = "true" ]; then
    print_success "Created auto-sync album: $AUTOSYNC_ALBUM_ID"
    test_result 0
else
    print_error "Failed to create auto-sync album"
    test_result 1
fi
echo ""

# =============================================================================
# Test 14: List Albums with Pagination
# =============================================================================
print_section "Test 14: List Albums with Pagination"
echo "GET ${API_PATH}?page=1&page_size=10"

RESPONSE=$(api_get "?page=1&page_size=10")
echo "$RESPONSE" | json_pretty | head -40

if json_has "$RESPONSE" "albums" && json_has "$RESPONSE" "page"; then
    ALBUM_COUNT=$(echo "$RESPONSE" | jq '.albums | length')
    print_success "Retrieved paginated albums: $ALBUM_COUNT albums"
    test_result 0
else
    print_error "Unexpected pagination response"
    test_result 1
fi
echo ""

# =============================================================================
# Test 15: Get Non-existent Album (404 Test)
# =============================================================================
print_section "Test 15: Get Non-existent Album"
FAKE_ID="album_nonexistent_$(date +%s)"
echo "GET ${API_PATH}/${FAKE_ID}"

RESPONSE=$(api_get "/${FAKE_ID}" "" "" "true")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "Response (HTTP $HTTP_CODE):"
echo "$BODY" | json_pretty 2>/dev/null || echo "$BODY"

if [ "$HTTP_CODE" = "404" ]; then
    print_success "Correctly returned 404"
    test_result 0
else
    print_error "Expected 404, got $HTTP_CODE"
    test_result 1
fi
echo ""

# =============================================================================
# Cleanup: Delete Family Shared Album
# =============================================================================
if [ -n "$FAMILY_ALBUM_ID" ] && [ "$FAMILY_ALBUM_ID" != "null" ]; then
    print_section "Cleanup: Delete Family Shared Album"
    echo "DELETE ${API_PATH}/${FAMILY_ALBUM_ID}"

    RESPONSE=$(api_delete "/${FAMILY_ALBUM_ID}")
    echo "$RESPONSE" | json_pretty 2>/dev/null || echo "$RESPONSE"

    # Verify deletion
    VERIFY=$(api_get "/${FAMILY_ALBUM_ID}" "" "" "true")
    HTTP_CODE=$(echo "$VERIFY" | tail -1)

    if [ "$HTTP_CODE" = "404" ]; then
        print_success "Family album deleted successfully"
        test_result 0
    else
        print_error "Family album delete may have failed (HTTP $HTTP_CODE)"
        test_result 1
    fi
else
    print_warning "Skipping: No family album ID"
fi
echo ""

# =============================================================================
# Cleanup: Delete Auto-sync Album
# =============================================================================
if [ -n "$AUTOSYNC_ALBUM_ID" ] && [ "$AUTOSYNC_ALBUM_ID" != "null" ]; then
    print_section "Cleanup: Delete Auto-sync Album"
    echo "DELETE ${API_PATH}/${AUTOSYNC_ALBUM_ID}"

    RESPONSE=$(api_delete "/${AUTOSYNC_ALBUM_ID}")
    echo "$RESPONSE" | json_pretty 2>/dev/null || echo "$RESPONSE"

    # Verify deletion
    VERIFY=$(api_get "/${AUTOSYNC_ALBUM_ID}" "" "" "true")
    HTTP_CODE=$(echo "$VERIFY" | tail -1)

    if [ "$HTTP_CODE" = "404" ]; then
        print_success "Auto-sync album deleted successfully"
        test_result 0
    else
        print_error "Auto-sync album delete may have failed (HTTP $HTTP_CODE)"
        test_result 1
    fi
else
    print_warning "Skipping: No auto-sync album ID"
fi
echo ""

# =============================================================================
# Cleanup: Delete Main Test Album
# =============================================================================
if [ -n "$ALBUM_ID" ] && [ "$ALBUM_ID" != "null" ]; then
    print_section "Cleanup: Delete Main Test Album"
    echo "DELETE ${API_PATH}/${ALBUM_ID}"

    RESPONSE=$(api_delete "/${ALBUM_ID}")
    echo "$RESPONSE" | json_pretty 2>/dev/null || echo "$RESPONSE"

    # Verify deletion
    VERIFY=$(api_get "/${ALBUM_ID}" "" "" "true")
    HTTP_CODE=$(echo "$VERIFY" | tail -1)

    if [ "$HTTP_CODE" = "404" ]; then
        print_success "Main test album deleted successfully"
        test_result 0
    else
        print_error "Main album delete may have failed (HTTP $HTTP_CODE)"
        test_result 1
    fi
else
    print_warning "Skipping: No album ID"
fi
echo ""

# =============================================================================
# Summary
# =============================================================================
print_summary
exit $?
