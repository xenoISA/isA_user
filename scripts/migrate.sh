#!/bin/bash
# Helper script for running Alembic migrations across services.
#
# Usage:
#   ./scripts/migrate.sh upgrade account_service        # upgrade one service
#   ./scripts/migrate.sh upgrade all                    # upgrade all services
#   ./scripts/migrate.sh downgrade payment_service -1   # rollback one step
#   ./scripts/migrate.sh status auth_service            # show current revision
#   ./scripts/migrate.sh list                           # list migratable services

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

usage() {
    echo "Usage: $0 <command> [service] [args...]"
    echo ""
    echo "Commands:"
    echo "  upgrade <service|all> [revision]  Run upgrade (default: head)"
    echo "  downgrade <service> <revision>    Run downgrade (e.g., -1)"
    echo "  status <service|all>              Show current migration status"
    echo "  revision <service> -m 'message'   Create a new migration"
    echo "  list                              List services with alembic migrations"
    echo ""
    echo "Examples:"
    echo "  $0 upgrade account_service"
    echo "  $0 upgrade all"
    echo "  $0 downgrade payment_service -1"
    echo "  $0 status auth_service"
    echo "  $0 revision account_service -m 'add email index'"
    exit 1
}

list_services() {
    find microservices/*/alembic/versions -maxdepth 0 -type d 2>/dev/null | \
        sed 's|microservices/||;s|/alembic/versions||' | sort
}

run_alembic() {
    local service="$1"
    shift
    alembic -x "service=$service" "$@"
}

[ $# -lt 1 ] && usage

COMMAND="$1"
shift

case "$COMMAND" in
    list)
        echo -e "${CYAN}Services with Alembic migrations:${NC}"
        list_services | while read -r svc; do
            count=$(find "microservices/$svc/alembic/versions" -name "*.py" | wc -l | tr -d ' ')
            echo -e "  ${GREEN}$svc${NC} ($count revisions)"
        done
        ;;

    upgrade)
        SERVICE="${1:-}"
        REVISION="${2:-head}"
        [ -z "$SERVICE" ] && usage

        if [ "$SERVICE" = "all" ]; then
            for svc in $(list_services); do
                echo -e "${CYAN}Upgrading $svc to $REVISION...${NC}"
                run_alembic "$svc" upgrade "$REVISION"
                echo -e "${GREEN}  Done.${NC}"
            done
        else
            echo -e "${CYAN}Upgrading $SERVICE to $REVISION...${NC}"
            run_alembic "$SERVICE" upgrade "$REVISION"
            echo -e "${GREEN}Done.${NC}"
        fi
        ;;

    downgrade)
        SERVICE="${1:-}"
        REVISION="${2:-}"
        [ -z "$SERVICE" ] || [ -z "$REVISION" ] && usage

        echo -e "${CYAN}Downgrading $SERVICE to $REVISION...${NC}"
        run_alembic "$SERVICE" downgrade "$REVISION"
        echo -e "${GREEN}Done.${NC}"
        ;;

    status)
        SERVICE="${1:-}"
        [ -z "$SERVICE" ] && usage

        if [ "$SERVICE" = "all" ]; then
            for svc in $(list_services); do
                echo -e "${CYAN}$svc:${NC}"
                run_alembic "$svc" current 2>/dev/null || echo "  (no version table yet)"
                echo ""
            done
        else
            run_alembic "$SERVICE" current
        fi
        ;;

    revision)
        SERVICE="${1:-}"
        [ -z "$SERVICE" ] && usage
        shift
        run_alembic "$SERVICE" revision "$@"
        ;;

    *)
        usage
        ;;
esac
