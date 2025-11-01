#!/bin/bash

# Device Service - Manage Test Data
# Seed or cleanup test data for development and testing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Database configuration
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-isa_platform}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-staging_postgres_2024}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to run SQL file
run_sql_file() {
    local sql_file=$1
    echo -e "${YELLOW}Running: ${sql_file}${NC}"

    PGPASSWORD=$POSTGRES_PASSWORD psql \
        -h $POSTGRES_HOST \
        -p $POSTGRES_PORT \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        -f "$sql_file"
}

# Function to run SQL via Docker
run_sql_docker() {
    local sql_file=$1
    echo -e "${YELLOW}Running via Docker: ${sql_file}${NC}"

    docker exec -i staging-postgres psql \
        -U postgres \
        -d isa_platform \
        < "$sql_file"
}

# Main script
case "$1" in
    seed)
        echo -e "${GREEN}Seeding test data for Device Service...${NC}"

        if command -v psql &> /dev/null; then
            run_sql_file "$SCRIPT_DIR/seed_test_data.sql"
        else
            echo -e "${YELLOW}psql not found, using Docker...${NC}"
            run_sql_docker "$SCRIPT_DIR/seed_test_data.sql"
        fi

        echo -e "${GREEN}✓ Test data seeded successfully${NC}"
        ;;

    cleanup)
        echo -e "${YELLOW}Cleaning up test data for Device Service...${NC}"

        if command -v psql &> /dev/null; then
            run_sql_file "$SCRIPT_DIR/cleanup_test_data.sql"
        else
            echo -e "${YELLOW}psql not found, using Docker...${NC}"
            run_sql_docker "$SCRIPT_DIR/cleanup_test_data.sql"
        fi

        echo -e "${GREEN}✓ Test data cleaned up successfully${NC}"
        ;;

    *)
        echo -e "${RED}Usage: $0 {seed|cleanup}${NC}"
        echo ""
        echo "Commands:"
        echo "  seed    - Insert test data into device schema"
        echo "  cleanup - Remove all test data from device schema"
        echo ""
        echo "Environment Variables:"
        echo "  POSTGRES_HOST     - PostgreSQL host (default: localhost)"
        echo "  POSTGRES_PORT     - PostgreSQL port (default: 5432)"
        echo "  POSTGRES_DB       - Database name (default: isa_platform)"
        echo "  POSTGRES_USER     - Database user (default: postgres)"
        echo "  POSTGRES_PASSWORD - Database password (default: staging_postgres_2024)"
        exit 1
        ;;
esac
