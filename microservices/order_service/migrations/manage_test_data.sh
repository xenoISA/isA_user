#!/bin/bash

# Test Data Management Script for Order Service
# Usage: ./manage_test_data.sh [seed|cleanup]

set -e

# Configuration
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-staging-postgres}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-isa_platform}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to execute SQL file
execute_sql() {
    local sql_file=$1
    print_info "Executing: $sql_file"

    if [ ! -f "$sql_file" ]; then
        print_error "SQL file not found: $sql_file"
        exit 1
    fi

    cat "$sql_file" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

    if [ $? -eq 0 ]; then
        print_info "Successfully executed: $sql_file"
    else
        print_error "Failed to execute: $sql_file"
        exit 1
    fi
}

# Function to seed test data
seed_data() {
    print_info "Seeding test data for Order Service..."
    execute_sql "$SCRIPT_DIR/seed_test_data.sql"
    print_info "Test data seeded successfully!"
}

# Function to cleanup test data
cleanup_data() {
    print_info "Cleaning up test data for Order Service..."
    execute_sql "$SCRIPT_DIR/cleanup_test_data.sql"
    print_info "Test data cleaned up successfully!"
}

# Main script logic
case "$1" in
    seed)
        seed_data
        ;;
    cleanup)
        cleanup_data
        ;;
    *)
        echo "Usage: $0 {seed|cleanup}"
        echo ""
        echo "Commands:"
        echo "  seed    - Insert test data into the database"
        echo "  cleanup - Remove test data from the database"
        echo ""
        echo "Environment Variables:"
        echo "  POSTGRES_CONTAINER - PostgreSQL container name (default: staging-postgres)"
        echo "  POSTGRES_USER      - PostgreSQL user (default: postgres)"
        echo "  POSTGRES_DB        - PostgreSQL database (default: isa_platform)"
        exit 1
        ;;
esac
