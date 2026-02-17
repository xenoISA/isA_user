#!/bin/bash
# Album Service Test Data Management Script
# Manages test data for album_service

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
    echo -e "${BLUE}Seeding Album Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cat "$SCRIPT_DIR/seed_test_data.sql" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    echo ""
    echo -e "${GREEN}✓ Album test data seeded successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Run tests with:${NC}"
    echo -e "  cd microservices/album_service/tests"
    echo -e "  python -m pytest test_album.py"
}

# Cleanup test data
cleanup() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Cleaning Up Album Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cat "$SCRIPT_DIR/cleanup_test_data.sql" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    echo ""
    echo -e "${GREEN}✓ Album test data cleaned successfully!${NC}"
}

# Reset (cleanup + seed)
reset() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Resetting Album Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cleanup
    echo ""
    seed
}

# List test data
list() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Current Album Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    echo -e "${YELLOW}Albums:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT album_id, name, user_id, organization_id, photo_count, is_family_shared, auto_sync FROM album.albums WHERE user_id LIKE 'test_%' ORDER BY album_id;"

    echo ""
    echo -e "${YELLOW}Album Photos:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT album_id, photo_id, added_by, is_featured, display_order FROM album.album_photos WHERE album_id IN (SELECT album_id FROM album.albums WHERE user_id LIKE 'test_%') ORDER BY album_id, display_order;"

    echo ""
    echo -e "${YELLOW}Sync Status:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT album_id, frame_id, sync_status, total_photos, synced_photos, pending_photos, failed_photos, last_sync_timestamp FROM album.album_sync_status WHERE user_id LIKE 'test_%' ORDER BY album_id, frame_id;"
}

# Show usage
usage() {
    echo "Album Service Test Data Management"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  seed      - Create test data (albums, photos, sync status)"
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
    echo ""
    echo "NOTE: Album test data requires storage_service test data"
    echo "      Run storage_service/migrations/manage_test_data.sh seed first"
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
