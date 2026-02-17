#!/bin/bash
# Storage Service Test Data Management Script
# Manages test data for storage_service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER="staging-postgres"
DB_USER="postgres"
DB_NAME="isa_platform"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if container is running
check_container() {
    if ! docker ps | grep -q "$CONTAINER"; then
        echo -e "${RED}Error: Container '$CONTAINER' is not running${NC}"
        exit 1
    fi
}

# Seed test data
seed() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Seeding Storage Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cat "$SCRIPT_DIR/seed_test_data.sql" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    echo ""
    echo -e "${GREEN}✓ Storage test data seeded successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Run tests with:${NC}"
    echo -e "  cd microservices/storage_service/tests"
    echo -e "  python -m pytest test_storage.py"
}

# Cleanup test data
cleanup() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Cleaning Up Storage Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cat "$SCRIPT_DIR/cleanup_test_data.sql" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    echo ""
    echo -e "${GREEN}✓ Storage test data cleaned successfully!${NC}"
}

# Reset (cleanup + seed)
reset() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Resetting Storage Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cleanup
    echo ""
    seed
}

# List test data
list() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Current Storage Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    echo -e "${YELLOW}Storage Files:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT file_id, user_id, file_name, file_size, content_type, status, access_level FROM storage.storage_files WHERE user_id LIKE 'test_%' ORDER BY file_id;"

    echo ""
    echo -e "${YELLOW}File Shares:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT share_id, file_id, shared_by, shared_with, permissions, is_active FROM storage.file_shares WHERE shared_by LIKE 'test_%' ORDER BY share_id;"

    echo ""
    echo -e "${YELLOW}Storage Quotas:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT quota_type, entity_id, used_bytes, total_quota_bytes, file_count, max_file_count FROM storage.storage_quotas WHERE entity_id LIKE 'test_%' ORDER BY quota_type, entity_id;"

    echo ""
    echo -e "${YELLOW}Intelligence Index:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT doc_id, file_id, title, status, chunk_count, search_count FROM storage.storage_intelligence_index WHERE user_id LIKE 'test_%' ORDER BY doc_id;"
}

# Show usage
usage() {
    echo "Storage Service Test Data Management"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  seed      - Create test data (files, shares, quotas, intelligence index)"
    echo "  cleanup   - Remove all test data"
    echo "  reset     - Cleanup and recreate test data"
    echo "  list      - List current test data"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 seed              # Create test data"
    echo "  $0 list              # View test data"
    echo "  $0 cleanup           # Remove test data"
    echo "  $0 reset             # Reset test data"
}

# Main
check_container

case "${1:-help}" in
    seed)
        seed
        ;;
    cleanup)
        cleanup
        ;;
    reset)
        reset
        ;;
    list)
        list
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$1'${NC}"
        echo ""
        usage
        exit 1
        ;;
esac
