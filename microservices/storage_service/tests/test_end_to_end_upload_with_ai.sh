#!/usr/bin/env bash
#
# End-to-End Test: 图片上传 → AI 提取 → 事件发布 → Media Service 存储
#
# 测试完整流程：
# 1. 用户上传图片到 Storage Service
# 2. Storage Service 自动调用 MCP 进行 AI 提取
# 3. Storage Service 发布 FILE_UPLOADED_WITH_AI 事件
# 4. Media Service 监听事件并存储 AI 元数据
# 5. 验证数据在 Media Service 中正确保存
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration - Using APISIX Ingress
BASE_URL="http://localhost"
STORAGE_URL="${BASE_URL}/api/v1/storage"
MEDIA_URL="${BASE_URL}/api/v1/media"
MCP_URL="${MCP_URL:-http://localhost:8081}"
TEST_USER="test_user_e2e_$$"
TEST_ORG="test_org_e2e"
TEST_IMAGE_URL="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800"
TEST_IMAGE_PATH="/tmp/test_e2e_image_$$.jpg"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ End-to-End Test: Upload → AI → Event → Media Storage         ║${NC}"
echo -e "${CYAN}║ Event-Driven Architecture v2.0 (via APISIX Ingress)          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  Base URL: $BASE_URL (via APISIX Ingress)"
echo "  Storage API: $STORAGE_URL"
echo "  Media API: $MEDIA_URL"
echo "  MCP Service: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  Test Image: $TEST_IMAGE_URL"
echo ""
echo -e "${BLUE}Event-Driven Architecture:${NC}"
echo "  ✓ Events published via events/publishers.py"
echo "  ✓ Event handlers in events/handlers.py"
echo "  ✓ Service clients in clients/"
echo ""

# Test counter
PASS=0
FAIL=0

pass_test() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASS++))
}

fail_test() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAIL++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Cleanup
cleanup() {
    if [ -f "$TEST_IMAGE_PATH" ]; then
        rm -f "$TEST_IMAGE_PATH"
    fi
}

trap cleanup EXIT

# ==============================================================================
# Test 0: 准备测试图片
# ==============================================================================
echo -e "${BLUE}[TEST 0]${NC} Download Test Image"

# Try downloading with proper headers
HTTP_CODE=$(curl -sL -w "%{http_code}" \
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
    -H "Accept: image/*" \
    --max-time 30 \
    "$TEST_IMAGE_URL" -o "$TEST_IMAGE_PATH")

if [ -f "$TEST_IMAGE_PATH" ] && [ -s "$TEST_IMAGE_PATH" ]; then
    FILE_SIZE=$(wc -c < "$TEST_IMAGE_PATH" | tr -d ' ')
    pass_test "Downloaded test image ($FILE_SIZE bytes)"
else
    fail_test "Failed to download test image (HTTP: $HTTP_CODE)"
    info "Trying alternative: using a local test image or different URL..."

    # Alternative: Try a different reliable test image
    ALT_URL="https://picsum.photos/800/600"
    info "Attempting download from alternative source: $ALT_URL"

    HTTP_CODE=$(curl -sL -w "%{http_code}" \
        -H "User-Agent: Mozilla/5.0" \
        --max-time 30 \
        "$ALT_URL" -o "$TEST_IMAGE_PATH")

    if [ -f "$TEST_IMAGE_PATH" ] && [ -s "$TEST_IMAGE_PATH" ]; then
        FILE_SIZE=$(wc -c < "$TEST_IMAGE_PATH" | tr -d ' ')
        pass_test "Downloaded alternative test image ($FILE_SIZE bytes)"
    else
        fail_test "All download attempts failed (HTTP: $HTTP_CODE)"
        info "Please check network connectivity or provide a local test image"
        exit 1
    fi
fi

# ==============================================================================
# Test 1: 上传图片到 Storage Service (触发 AI 提取)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 1]${NC} Upload Image to Storage Service"
info "This will trigger automatic AI extraction via MCP (10-15 seconds)..."
echo -e "${BLUE}Expected Event: file.uploaded_with_ai will be published to NATS${NC}"

UPLOAD_RESP=$(curl -s -X POST "$STORAGE_URL/files/upload" \
  -F "file=@$TEST_IMAGE_PATH" \
  -F "user_id=$TEST_USER" \
  -F "organization_id=$TEST_ORG")

UPLOAD_FILE_ID=$(echo "$UPLOAD_RESP" | jq -r '.file_id' 2>/dev/null)
UPLOAD_SUCCESS=$(echo "$UPLOAD_RESP" | jq -r '.file_id' 2>/dev/null)

if [ -n "$UPLOAD_FILE_ID" ] && [ "$UPLOAD_FILE_ID" != "null" ]; then
    pass_test "Image uploaded successfully, file_id=$UPLOAD_FILE_ID"
    info "Waiting 15 seconds for AI extraction and event processing..."
    sleep 15
else
    fail_test "Image upload failed"
    echo "Response: $UPLOAD_RESP" | jq '.' 2>/dev/null || echo "$UPLOAD_RESP"
    exit 1
fi

# ==============================================================================
# Test 3: 验证 Storage Service 的 Intelligence Index
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Verify Storage Intelligence Index (chunk_id mapping)"
info "Checking if chunk_id was saved in storage.storage_intelligence_index..."

# 通过 PostgreSQL 查询（需要有访问权限）
# 这里我们通过 Storage Service API 间接验证
INTEL_SEARCH=$(curl -s -X POST "$STORAGE_URL/intelligence/image/search" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$TEST_USER\",
    \"query\": \"mountains\",
    \"top_k\": 5
  }")

INTEL_SUCCESS=$(echo "$INTEL_SEARCH" | jq -r '.success' 2>/dev/null)
INTEL_RESULTS=$(echo "$INTEL_SEARCH" | jq -r '.total_images_found' 2>/dev/null)

if [ "$INTEL_SUCCESS" = "true" ] && [ "$INTEL_RESULTS" -gt 0 ]; then
    pass_test "Intelligence index working (found $INTEL_RESULTS results)"
else
    fail_test "Intelligence index not working or no results"
fi

# ==============================================================================
# Test 4: 验证 Media Service 收到并存储了 AI 元数据
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Verify Media Service Received AI Metadata"
info "Checking if Media Service stored the AI metadata from event..."

# 等待更长时间以确保事件被处理
sleep 3

# 查询 Media Service 的 photo metadata
MEDIA_METADATA=$(curl -s -X GET "$MEDIA_URL/metadata/$UPLOAD_FILE_ID?user_id=$TEST_USER")

MEDIA_FILE_ID=$(echo "$MEDIA_METADATA" | jq -r '.file_id' 2>/dev/null)
MEDIA_AI_LABELS=$(echo "$MEDIA_METADATA" | jq -r '.ai_labels | length' 2>/dev/null)
MEDIA_AI_SCENES=$(echo "$MEDIA_METADATA" | jq -r '.ai_scenes | length' 2>/dev/null)
MEDIA_QUALITY=$(echo "$MEDIA_METADATA" | jq -r '.quality_score' 2>/dev/null)

if [ "$MEDIA_FILE_ID" = "$UPLOAD_FILE_ID" ] && [ "$MEDIA_AI_LABELS" -gt 0 ]; then
    pass_test "Media Service has AI metadata (labels=$MEDIA_AI_LABELS, scenes=$MEDIA_AI_SCENES)"

    # 显示 AI 标签
    AI_LABELS_LIST=$(echo "$MEDIA_METADATA" | jq -r '.ai_labels[:5] | join(", ")' 2>/dev/null)
    info "AI Labels: $AI_LABELS_LIST"

    # 显示 AI 场景
    AI_SCENES_LIST=$(echo "$MEDIA_METADATA" | jq -r '.ai_scenes[:3] | join(", ")' 2>/dev/null)
    info "AI Scenes: $AI_SCENES_LIST"

    # 显示质量分数
    if [ -n "$MEDIA_QUALITY" ] && [ "$MEDIA_QUALITY" != "null" ]; then
        info "Quality Score: $MEDIA_QUALITY"
    fi
else
    fail_test "Media Service does not have AI metadata"
    echo "Response: $MEDIA_METADATA" | jq '.' 2>/dev/null || echo "$MEDIA_METADATA"
fi

# ==============================================================================
# Test 5: 验证 chunk_id 关联
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Verify chunk_id → file_id Mapping"

# 从 Media Service metadata 中提取 chunk_id
CHUNK_ID=$(echo "$MEDIA_METADATA" | jq -r '.full_metadata.chunk_id' 2>/dev/null)

if [ -n "$CHUNK_ID" ] && [ "$CHUNK_ID" != "null" ]; then
    pass_test "chunk_id found in Media metadata: ${CHUNK_ID:0:16}..."
    info "Relationship: chunk_id (Qdrant) → file_id (PostgreSQL) → object (MinIO)"
else
    fail_test "chunk_id not found in Media metadata"
fi

# ==============================================================================
# Test 6: 端到端语义搜索测试
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} End-to-End Semantic Search"
info "Searching for 'snow mountains sunset' to verify full integration..."

E2E_SEARCH=$(curl -s -X POST "$STORAGE_URL/intelligence/image/search" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$TEST_USER\",
    \"query\": \"snow mountains sunset\",
    \"top_k\": 3
  }")

E2E_SUCCESS=$(echo "$E2E_SEARCH" | jq -r '.success' 2>/dev/null)
E2E_FOUND=$(echo "$E2E_SEARCH" | jq -r '.total_images_found' 2>/dev/null)
E2E_FIRST_FILE_ID=$(echo "$E2E_SEARCH" | jq -r '.image_results[0].metadata.file_id' 2>/dev/null)

if [ "$E2E_SUCCESS" = "true" ] && [ "$E2E_FOUND" -gt 0 ] && [ "$E2E_FIRST_FILE_ID" = "$UPLOAD_FILE_ID" ]; then
    pass_test "Semantic search returned uploaded image (score: $(echo "$E2E_SEARCH" | jq -r '.image_results[0].relevance_score'))"
else
    fail_test "Semantic search did not return uploaded image"
    echo "Response: $E2E_SEARCH" | jq '.' 2>/dev/null || echo "$E2E_SEARCH"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ Test Summary                                                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Passed:${NC} $PASS"
echo -e "${RED}Failed:${NC} $FAIL"
echo ""

TOTAL=$((PASS + FAIL))
echo "Total Tests: $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All end-to-end tests passed!${NC}"
    echo ""
    echo "✨ Complete Flow Verified!"
    echo ""
    echo "The system successfully:"
    echo "  ✓ Uploaded image to Storage Service"
    echo "  ✓ Automatically extracted AI metadata via MCP"
    echo "  ✓ Saved chunk_id mapping (Qdrant ↔ PostgreSQL ↔ MinIO)"
    echo "  ✓ Published FILE_UPLOADED_WITH_AI event"
    echo "  ✓ Media Service received and stored AI metadata"
    echo "  ✓ Semantic search returns uploaded image"
    echo ""
    echo "🔗 Data Flow:"
    echo "  User → Storage Service → MCP (AI) → Qdrant (vectors)"
    echo "                       ↓"
    echo "                    PostgreSQL (chunk_id ↔ file_id)"
    echo "                       ↓"
    echo "                    NATS Event"
    echo "                       ↓"
    echo "                  Media Service (AI metadata)"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check service logs:"
    echo "  - Storage Service"
    echo "  - Media Service"
    echo "  - MCP server"
    exit 1
fi
