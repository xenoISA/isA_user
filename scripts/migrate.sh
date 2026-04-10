#!/bin/bash
# Helper script for running tracked migrations across services.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

usage() {
    echo "Usage: $0 <command> [service] [args...]"
    echo ""
    echo "Alembic commands:"
    echo "  upgrade <service|all> [revision]   Run Alembic upgrade (default: head)"
    echo "  downgrade <service> <revision>     Run Alembic downgrade"
    echo "  status <service|all>               Show Alembic status"
    echo "  revision <service> -m 'message'    Create an Alembic revision"
    echo "  list                               List services with Alembic migrations"
    echo ""
    echo "Raw SQL commands:"
    echo "  sql-upgrade <service|all>          Run tracked raw SQL migrations"
    echo "  sql-status <service|all>           Show tracked raw SQL migration status"
    echo "  sql-baseline <service|all> [ver]   Mark tracked raw SQL migrations as already applied"
    echo "  sql-list                           List services with tracked raw SQL migrations"
    exit 1
}

list_alembic_services() {
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
        list_alembic_services | while read -r svc; do
            count=$(find "microservices/$svc/alembic/versions" -name "*.py" | wc -l | tr -d ' ')
            echo -e "  ${GREEN}$svc${NC} ($count revisions)"
        done
        ;;

    upgrade)
        SERVICE="${1:-}"
        REVISION="${2:-head}"
        [ -z "$SERVICE" ] && usage

        if [ "$SERVICE" = "all" ]; then
            for svc in $(list_alembic_services); do
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
            for svc in $(list_alembic_services); do
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

    sql-list)
        echo -e "${CYAN}Services with tracked raw SQL migrations:${NC}"
        python scripts/migrate_sql.py list
        ;;

    sql-upgrade)
        SERVICE="${1:-all}"
        echo -e "${CYAN}Running tracked raw SQL migrations for $SERVICE...${NC}"
        python scripts/migrate_sql.py upgrade "$SERVICE"
        echo -e "${GREEN}Done.${NC}"
        ;;

    sql-status)
        SERVICE="${1:-all}"
        python scripts/migrate_sql.py status "$SERVICE"
        ;;

    sql-baseline)
        SERVICE="${1:-all}"
        THROUGH_VERSION="${2:-}"
        if [ -n "$THROUGH_VERSION" ]; then
            python scripts/migrate_sql.py baseline "$SERVICE" --through-version "$THROUGH_VERSION"
        else
            python scripts/migrate_sql.py baseline "$SERVICE"
        fi
        ;;

    *)
        usage
        ;;
esac
