#!/bin/bash
# Media Service Test Data Management Script
# Manages test data for media_service

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
    echo -e "${BLUE}Seeding Media Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cat "$SCRIPT_DIR/seed_test_data.sql" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    echo ""
    echo -e "${GREEN}✓ Media test data seeded successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Run tests with:${NC}"
    echo -e "  cd microservices/media_service/tests"
    echo -e "  python -m pytest test_media.py"
}

# Cleanup test data
cleanup() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Cleaning Up Media Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cat "$SCRIPT_DIR/cleanup_test_data.sql" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    echo ""
    echo -e "${GREEN}✓ Media test data cleaned successfully!${NC}"
}

# Reset (cleanup + seed)
reset() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Resetting Media Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cleanup
    echo ""
    seed
}

# List test data
list() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Current Media Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    echo -e "${YELLOW}Photo Versions:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT version_id, photo_id, version_name, version_type, is_current, file_size FROM media.photo_versions WHERE user_id LIKE 'test_%' ORDER BY photo_id, version_number;"

    echo ""
    echo -e "${YELLOW}Photo Metadata:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT file_id, camera_model, location_name, quality_score, ai_labels FROM media.photo_metadata WHERE user_id LIKE 'test_%' ORDER BY file_id;"

    echo ""
    echo -e "${YELLOW}Playlists:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT playlist_id, name, playlist_type, user_id, shuffle, loop, transition_duration FROM media.playlists WHERE user_id LIKE 'test_%' ORDER BY playlist_id;"

    echo ""
    echo -e "${YELLOW}Rotation Schedules:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT schedule_id, frame_id, playlist_id, schedule_type, is_active, rotation_interval FROM media.rotation_schedules WHERE user_id LIKE 'test_%' ORDER BY schedule_id;"

    echo ""
    echo -e "${YELLOW}Photo Cache:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT cache_id, frame_id, photo_id, cache_status, cache_size, hit_count FROM media.photo_cache WHERE user_id LIKE 'test_%' ORDER BY cache_id;"
}

# Show usage
usage() {
    echo "Media Service Test Data Management"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  seed      - Create test data (versions, metadata, playlists, schedules, cache)"
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
    echo "NOTE: Media test data requires storage_service test data"
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
