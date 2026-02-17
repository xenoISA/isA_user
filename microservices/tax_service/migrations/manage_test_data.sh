#!/bin/bash

# Test Data Management Script for Tax Service
# Usage: ./manage_test_data.sh [seed|cleanup]

set -e

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-staging-postgres}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-isa_platform}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

execute_sql() {
    local sql_file=$1
    if [ ! -f "$sql_file" ]; then
        print_error "SQL file not found: $sql_file"
        exit 1
    fi
    cat "$sql_file" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
}

case "$1" in
    seed)
        print_info "Seeding test data for Tax Service..."
        execute_sql "$SCRIPT_DIR/seed_test_data.sql"
        ;;
    cleanup)
        print_info "Cleaning test data for Tax Service..."
        execute_sql "$SCRIPT_DIR/cleanup_test_data.sql"
        ;;
    *)
        echo "Usage: $0 {seed|cleanup}"
        exit 1
        ;;
esac
