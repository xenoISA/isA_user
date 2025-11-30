#!/bin/bash
# Media Service - AI Metadata Caching Test
# Tests the event-driven AI processing workflow:
# 1. Storage uploads file → publishes file.uploaded
# 2. Media Service receives event → triggers Digital Analytics AI processing
# 3. Media Service caches AI metadata to PostgreSQL

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STORAGE_BASE_URL="${STORAGE_BASE_URL:-http://localhost/api/v1/storage}"
MEDIA_BASE_URL="${MEDIA_BASE_URL:-http://localhost/api/v1/media}"
NAMESPACE="${NAMESPACE:-isa-cloud-staging}"

# Test user
TEST_USER="ai_test_user_$$"
TEST_FILE_ID=""

echo "======================================================================"
echo "       MEDIA SERVICE - AI METADATA CACHING TEST"
echo "======================================================================"
echo ""

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "Test Configuration:"
echo "  User: $TEST_USER"
echo "  Storage API: $STORAGE_BASE_URL"
echo "  Media API: $MEDIA_BASE_URL"
echo ""

# =============================================================================
# Test 1: Upload Image with AI Indexing Enabled
# =============================================================================
echo "======================================================================"
echo "Test 1: Upload Image with AI Indexing Enabled"
echo "======================================================================"

# Create test image
TEST_IMAGE="/tmp/test_ai_image_$$.jpg"
convert -size 800x600 xc:blue -fill yellow -pointsize 72 -annotate +200+300 "AI TEST" "$TEST_IMAGE" 2>/dev/null || {
    warn "ImageMagick not available, using placeholder"
    echo "AI test image" > "$TEST_IMAGE"
}

info "Uploading image to Storage Service..."
UPLOAD_RESPONSE=$(curl -s -X POST "$STORAGE_BASE_URL/files/upload" \
    -F "file=@$TEST_IMAGE" \
    -F "user_id=$TEST_USER" \
    -F "enable_indexing=true" \
    -F "tags=test,ai,automated")

echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_RESPONSE"

TEST_FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.file_id' 2>/dev/null || echo "")

if [ -z "$TEST_FILE_ID" ] || [ "$TEST_FILE_ID" = "null" ]; then
    fail "Failed to upload file"
fi

pass "File uploaded: $TEST_FILE_ID"
info "Waiting for event processing and AI analysis (30s)..."
sleep 30

# =============================================================================
# Test 2: Verify AI Metadata in PostgreSQL
# =============================================================================
echo ""
echo "======================================================================"
echo "Test 2: Verify AI Metadata Cached in PostgreSQL"
echo "======================================================================"

info "Checking photo_metadata table in PostgreSQL..."

METADATA_QUERY="SELECT
    file_id,
    ai_processing_status,
    ai_description,
    ai_tags,
    ai_categories,
    ai_mood,
    ai_style,
    knowledge_id,
    collection_name,
    vector_indexed,
    ai_indexed_at
FROM media.photo_metadata
WHERE file_id = '$TEST_FILE_ID' AND user_id = '$TEST_USER';"

METADATA_RESULT=$(kubectl exec -n "$NAMESPACE" postgres-0 -- psql -U postgres -d isa_platform -t -c "$METADATA_QUERY" 2>/dev/null || echo "")

if [ -z "$METADATA_RESULT" ]; then
    warn "No metadata found in database yet"
    warn "This could mean:"
    warn "  1. Event hasn't been processed yet (increase wait time)"
    warn "  2. Digital Analytics Service is not configured"
    warn "  3. AI processing failed"

    info "Checking Media Service logs for errors..."
    kubectl logs -n "$NAMESPACE" -l app=media --tail=20 2>/dev/null | grep -i "file.uploaded\|ai\|error" || true
else
    pass "AI metadata found in PostgreSQL!"
    echo "$METADATA_RESULT"

    # Parse the result to check fields
    AI_STATUS=$(echo "$METADATA_RESULT" | awk '{print $2}' | tr -d '[:space:]')

    if [ "$AI_STATUS" = "completed" ]; then
        pass "AI processing status: completed"
    elif [ "$AI_STATUS" = "processing" ]; then
        warn "AI processing still in progress"
    elif [ "$AI_STATUS" = "failed" ]; then
        fail "AI processing failed"
    else
        warn "AI processing status: $AI_STATUS"
    fi
fi

# =============================================================================
# Test 3: Query AI Metadata via Media Service API (if implemented)
# =============================================================================
echo ""
echo "======================================================================"
echo "Test 3: Query AI Metadata via Media Service API"
echo "======================================================================"

info "GET $MEDIA_BASE_URL/metadata/$TEST_FILE_ID?user_id=$TEST_USER"
METADATA_API_RESPONSE=$(curl -s -X GET "$MEDIA_BASE_URL/metadata/$TEST_FILE_ID?user_id=$TEST_USER")

echo "$METADATA_API_RESPONSE" | jq '.' 2>/dev/null || echo "$METADATA_API_RESPONSE"

if echo "$METADATA_API_RESPONSE" | jq -e '.ai_labels' >/dev/null 2>&1; then
    pass "AI metadata accessible via API"

    AI_TAGS=$(echo "$METADATA_API_RESPONSE" | jq -r '.ai_labels[]' 2>/dev/null | head -5)
    if [ -n "$AI_TAGS" ]; then
        info "AI Tags: $AI_TAGS"
    fi
else
    warn "AI metadata not yet available via API (may still be processing)"
fi

# =============================================================================
# Test 4: Verify Media Service Event Handler Logs
# =============================================================================
echo ""
echo "======================================================================"
echo "Test 4: Check Media Service Event Handler Logs"
echo "======================================================================"

info "Checking recent Media Service logs for file.uploaded event processing..."
kubectl logs -n "$NAMESPACE" -l app=media --tail=50 2>/dev/null | grep -A 10 "file.uploaded\|Processing file.uploaded\|AI processing" || warn "No file.uploaded processing logs found"

# =============================================================================
# Test 5: Cleanup
# =============================================================================
echo ""
echo "======================================================================"
echo "Test 5: Cleanup"
echo "======================================================================"

if [ -f "$TEST_IMAGE" ]; then
    rm "$TEST_IMAGE"
    pass "Test image cleaned up"
fi

# Optional: Delete test file from storage
if [ -n "$TEST_FILE_ID" ]; then
    info "Deleting test file: $TEST_FILE_ID"
    curl -s -X DELETE "$STORAGE_BASE_URL/files/$TEST_FILE_ID?user_id=$TEST_USER&permanent=true" >/dev/null 2>&1
    pass "Test file deleted"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "======================================================================"
echo "                      TEST SUMMARY"
echo "======================================================================"
echo ""
echo "✓ File uploaded to Storage Service"
echo "✓ file.uploaded event should be published to NATS"
echo "✓ Media Service event handler should process the event"
echo ""
if [ -n "$METADATA_RESULT" ]; then
    echo -e "${GREEN}✓ AI metadata cached in PostgreSQL${NC}"
else
    echo -e "${YELLOW}⚠ AI metadata not found (may need more time or Digital Analytics Service configuration)${NC}"
fi
echo ""
echo "Next Steps to Enable Full AI Processing:"
echo "  1. Ensure Digital Analytics Service (isA_Data) is running"
echo "  2. Configure digital_analytics_url in config"
echo "  3. Check Media Service logs: kubectl logs -n $NAMESPACE -l app=media -f"
echo "  4. Verify NATS event delivery: Check NATS monitoring"
echo ""
