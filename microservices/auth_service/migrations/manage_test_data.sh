#!/bin/bash
# Auth Service Test Data Management Script
# Manages test data for auth_service

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
    echo -e "${BLUE}Seeding Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cat "$SCRIPT_DIR/seed_test_data.sql" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    echo ""
    echo -e "${GREEN}✓ Test data seeded successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Run tests with:${NC}"
    echo -e "  cd microservices/auth_service/tests"
    echo -e "  ./device_auth_test.sh test_org_001"
    echo -e "  ./api_key_test.sh test_org_001"
}

# Cleanup test data
cleanup() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Cleaning Up Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cat "$SCRIPT_DIR/cleanup_test_data.sql" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    echo ""
    echo -e "${GREEN}✓ Test data cleaned successfully!${NC}"
}

# Reset (cleanup + seed)
reset() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Resetting Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"

    cleanup
    echo ""
    seed
}

# List test data
list() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Current Test Data${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    echo -e "${YELLOW}Users:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT user_id, email, name, is_active FROM auth.users WHERE user_id LIKE 'test_%' ORDER BY user_id;"

    echo ""
    echo -e "${YELLOW}Organizations:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT organization_id, name FROM auth.organizations WHERE organization_id LIKE 'test_%' ORDER BY organization_id;"

    echo ""
    echo -e "${YELLOW}Devices:${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT device_id, device_name, device_type, organization_id, status FROM auth.devices WHERE device_id LIKE 'test_%' ORDER BY device_id;"
}

# Show usage
usage() {
    echo "Auth Service Test Data Management"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  seed      - Create test data (users, organizations, devices)"
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
