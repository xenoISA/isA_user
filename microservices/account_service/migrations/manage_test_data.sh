#!/bin/bash

# Account Service Test Data Management Script
# Usage: ./manage_test_data.sh [seed|cleanup]

set -e

# PostgreSQL connection settings
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-isa_db}"
DB_USER="${POSTGRES_USER:-isa_user}"
DB_PASSWORD="${POSTGRES_PASSWORD:-isa_password}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to execute SQL file
execute_sql() {
    local sql_file=$1
    echo -e "${YELLOW}Executing: $sql_file${NC}"

    PGPASSWORD=$DB_PASSWORD psql \
        -h $DB_HOST \
        -p $DB_PORT \
        -U $DB_USER \
        -d $DB_NAME \
        -f "$sql_file"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully executed: $sql_file${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to execute: $sql_file${NC}"
        return 1
    fi
}

# Main script
case "$1" in
    seed)
        echo -e "${GREEN}=== Seeding Account Service Test Data ===${NC}"
        execute_sql "$SCRIPT_DIR/seed_test_data.sql"
        ;;
    cleanup)
        echo -e "${YELLOW}=== Cleaning Up Account Service Test Data ===${NC}"
        execute_sql "$SCRIPT_DIR/cleanup_test_data.sql"
        ;;
    *)
        echo "Usage: $0 {seed|cleanup}"
        echo ""
        echo "Commands:"
        echo "  seed    - Insert test data into database"
        echo "  cleanup - Remove test data from database"
        echo ""
        echo "Environment Variables:"
        echo "  POSTGRES_HOST     (default: localhost)"
        echo "  POSTGRES_PORT     (default: 5432)"
        echo "  POSTGRES_DB       (default: isa_db)"
        echo "  POSTGRES_USER     (default: isa_user)"
        echo "  POSTGRES_PASSWORD (default: isa_password)"
        exit 1
        ;;
esac
