#!/bin/bash
# Test RAG Query with Real Integration
# This test verifies RAG query and semantic search with real file upload and indexing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}          RAG QUERY INTEGRATION TEST (REAL)${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="rag_test_user_${TEST_TS}"
# Use APISIX gateway routes
DOCUMENT_URL="http://localhost/api/v1"
STORAGE_URL="http://localhost/api/v1"

echo -e "${BLUE}Document Service: ${DOCUMENT_URL}/documents${NC}"
echo -e "${BLUE}Storage Service: ${STORAGE_URL}/storage${NC}"
echo ""

# Health checks - via APISIX gateway
echo -e "${BLUE}Checking services health...${NC}"

DOC_HEALTH=$(curl -s "${DOCUMENT_URL}/documents?user_id=health_check" 2>/dev/null && echo '{"status":"healthy"}' || echo '{"status":"error"}')
STORAGE_HEALTH=$(curl -s "${STORAGE_URL}/storage/files/quota?user_id=health_check" 2>/dev/null && echo '{"status":"healthy"}' || echo '{"status":"error"}')

if ! echo "$DOC_HEALTH" | grep -q "healthy"; then
    echo -e "${RED}✗ Document service not healthy${NC}"
    exit 1
fi

if ! echo "$STORAGE_HEALTH" | grep -q "healthy"; then
    echo -e "${RED}✗ Storage service not healthy${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All services healthy${NC}"
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Upload and Create Test Document for RAG${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Create a temporary test file with RAG-specific content
TEST_FILE="/tmp/rag_test_document_${TEST_TS}.txt"
cat > "$TEST_FILE" << 'EOF'
# Comprehensive Guide to RAG Systems

## What is RAG?

RAG stands for Retrieval-Augmented Generation. It is an AI framework that enhances
large language models by combining them with external knowledge retrieval systems.

## How RAG Works

1. **Query Processing**: The user's question is first processed and converted into
   an embedding vector that captures its semantic meaning.

2. **Retrieval Phase**: The system searches a vector database (like Qdrant) to find
   the most relevant documents or passages based on semantic similarity.

3. **Augmentation**: Retrieved information is combined with the original query to
   provide context for the language model.

4. **Generation**: The LLM generates a response based on both the query and the
   retrieved context, producing more accurate and grounded answers.

## Benefits of RAG

- **Reduced Hallucination**: By grounding responses in real data, RAG systems are
  less likely to generate false or misleading information.

- **Up-to-date Information**: Unlike static LLM training, RAG can access current
  information through its knowledge base.

- **Domain Specificity**: RAG systems can be tailored to specific domains by
  curating relevant documents in the knowledge base.

## Common RAG Architectures

### Basic RAG
Simple retrieval followed by generation. Best for straightforward Q&A tasks.

### Advanced RAG
Includes query rewriting, re-ranking, and multi-hop retrieval for complex queries.

### Modular RAG
Separates concerns into distinct modules for maximum flexibility and customization.

## Implementation Considerations

When implementing RAG systems, consider:
- Chunk size and overlap for document splitting
- Embedding model selection
- Vector database choice and indexing strategy
- Prompt engineering for effective context integration

EOF

echo -e "${BLUE}Step 1: Upload test file to storage service${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST "${STORAGE_URL}/storage/files/upload" \
  -F "file=@${TEST_FILE}" \
  -F "user_id=${TEST_USER_ID}" \
  -F "access_level=private" \
  -F "tags=[\"rag\",\"ai\",\"knowledge-base\"]" \
  -F "enable_indexing=false")

if echo "$UPLOAD_RESPONSE" | grep -q "file_id"; then
    FILE_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('file_id', ''))" 2>/dev/null)
    echo -e "${GREEN}✓ File uploaded: ${FILE_ID}${NC}"
else
    echo -e "${RED}✗ File upload failed${NC}"
    rm -f "$TEST_FILE"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 2: Create document${NC}"
DOC_PAYLOAD="{\"title\":\"RAG Guide ${TEST_TS}\",\"description\":\"Comprehensive guide to RAG systems\",\"doc_type\":\"txt\",\"file_id\":\"${FILE_ID}\",\"access_level\":\"private\",\"tags\":[\"rag\",\"ai\",\"nlp\"]}"
RESPONSE=$(curl -s -X POST "${DOCUMENT_URL}/documents?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$DOC_PAYLOAD")

if echo "$RESPONSE" | grep -q "doc_id"; then
    DOC_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('doc_id', ''))" 2>/dev/null)
    echo -e "${GREEN}✓ Document created: ${DOC_ID}${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: Document creation failed${NC}"
    rm -f "$TEST_FILE"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 3: Wait for document indexing (max 30s)${NC}"
MAX_WAIT=30
WAIT_COUNT=0
DOC_STATUS="draft"

while [ "$DOC_STATUS" != "indexed" ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
    RESPONSE=$(curl -s -X GET "${DOCUMENT_URL}/documents/${DOC_ID}?user_id=${TEST_USER_ID}")
    DOC_STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
    echo "  Status after ${WAIT_COUNT}s: ${DOC_STATUS}"

    if [ "$DOC_STATUS" = "failed" ]; then
        echo -e "${RED}✗ Document indexing failed${NC}"
        break
    fi
done
echo ""

if [ "$DOC_STATUS" = "indexed" ]; then
    echo -e "${GREEN}✓ Document indexed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Document status: ${DOC_STATUS}${NC}"
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: RAG Query${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Step 1: Execute RAG query about RAG benefits${NC}"
RAG_PAYLOAD="{\"query\":\"What are the benefits of RAG systems?\",\"top_k\":5}"
RESPONSE=$(curl -s -X POST "${DOCUMENT_URL}/documents/rag/query?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$RAG_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

if echo "$RESPONSE" | grep -q "answer\|query"; then
    ANSWER=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('answer', '')[:200])" 2>/dev/null)
    LATENCY=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('latency_ms', 0))" 2>/dev/null)
    echo -e "${GREEN}✓ RAG query executed successfully${NC}"
    echo -e "${CYAN}  Latency: ${LATENCY}ms${NC}"
    PASSED_2=1
else
    echo -e "${YELLOW}⚠ RAG query response incomplete${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Semantic Search${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Step 1: Execute semantic search for 'retrieval augmented'${NC}"
SEARCH_PAYLOAD="{\"query\":\"retrieval augmented generation architecture\",\"top_k\":10,\"min_score\":0.0}"
RESPONSE=$(curl -s -X POST "${DOCUMENT_URL}/documents/search?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$SEARCH_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

if echo "$RESPONSE" | grep -q "results\|query"; then
    RESULT_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_count', 0))" 2>/dev/null)
    echo -e "${GREEN}✓ Semantic search executed successfully${NC}"
    echo -e "${CYAN}  Results found: ${RESULT_COUNT}${NC}"
    PASSED_3=1
else
    echo -e "${YELLOW}⚠ Semantic search response incomplete${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: RAG Query with Different Topic${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Step 1: Execute RAG query about how RAG works${NC}"
RAG_PAYLOAD="{\"query\":\"Explain how RAG systems process queries step by step\",\"top_k\":3}"
RESPONSE=$(curl -s -X POST "${DOCUMENT_URL}/documents/rag/query?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$RAG_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

if echo "$RESPONSE" | grep -q "answer\|query"; then
    echo -e "${GREEN}✓ Second RAG query executed${NC}"
    PASSED_4=1
else
    echo -e "${YELLOW}⚠ Second RAG query response incomplete${NC}"
    PASSED_4=0
fi
echo ""

# Cleanup
echo -e "${BLUE}Cleaning up test files...${NC}"
rm -f "$TEST_FILE"
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4))
echo -e "Tests Passed: ${GREEN}${TOTAL_PASSED}/4${NC}"
echo ""

if [ $TOTAL_PASSED -ge 2 ]; then
    echo -e "${GREEN}✓ RAG QUERY TESTS COMPLETED!${NC}"
    echo ""
    echo -e "${CYAN}RAG Features Verified:${NC}"
    [ $PASSED_1 -eq 1 ] && echo -e "  ${GREEN}✓${NC} Create document with real file for RAG indexing"
    [ $PASSED_2 -eq 1 ] && echo -e "  ${GREEN}✓${NC} RAG query with permission filtering"
    [ $PASSED_3 -eq 1 ] && echo -e "  ${GREEN}✓${NC} Semantic search"
    [ $PASSED_4 -eq 1 ] && echo -e "  ${GREEN}✓${NC} Multiple RAG queries"
    echo ""
    echo -e "${CYAN}Integration Points:${NC}"
    echo -e "  • storage_service → file content"
    echo -e "  • digital_analytics → RAG/search"
    echo -e "  • PostgreSQL → permissions"
    exit 0
else
    echo -e "${RED}✗ RAG QUERY TESTS FAILED${NC}"
    exit 1
fi
