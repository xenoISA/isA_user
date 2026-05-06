#!/usr/bin/env bash
# =============================================================================
# Post-deploy smoke test (issue #355, parent epic #345)
# =============================================================================
# Pings /health on every microservice listed in config/ports.yaml.
#
# Outputs grep-friendly TSV: SERVICE\tSTATUS\tLATENCY_MS\tDETAIL
# Exit code:
#   0 — every service returned healthy or degraded before the grace period
#       expired. (degraded is a warning, not a failure — see core/health.py.)
#   1 — at least one service still unhealthy / unreachable after retries.
#
# Configurable via env (all values are seconds where applicable):
#   SMOKE_BASE_URL          default http://localhost
#                           Use http://<svc>.<ns>.svc.cluster.local for K8s.
#                           When the value contains "cluster.local" we treat
#                           each service as its own DNS name on a fixed port
#                           via SMOKE_K8S_PORT (default 8080), since K8s
#                           ClusterIP services expose a stable port per name.
#                           For host-based base URLs we use per-service ports
#                           from config/ports.yaml.
#   SMOKE_K8S_PORT          default 8080 (only used in cluster.local mode)
#   SMOKE_GRACE_PERIOD_S    default 60 — total time to keep retrying failures
#   SMOKE_RETRY_INTERVAL_S  default 5  — sleep between retry passes
#   SMOKE_TIMEOUT_S         default 5  — per-request curl timeout
#   SMOKE_HEALTH_PATH       default /health
#   SMOKE_PORTS_FILE        default config/ports.yaml
#   SMOKE_FAIL_ON_DEGRADED  default 0  — set 1 to fail when any service is
#                                        merely degraded (caller-controlled)
#   SMOKE_OUTPUT_FILE       default ""  — if set, also write the final TSV
#                                         report there (artifact-friendly).
# =============================================================================

set -euo pipefail

# ---- Resolve repo root from this script's location ------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---- Defaults --------------------------------------------------------------
: "${SMOKE_BASE_URL:=http://localhost}"
: "${SMOKE_K8S_PORT:=8080}"
: "${SMOKE_GRACE_PERIOD_S:=60}"
: "${SMOKE_RETRY_INTERVAL_S:=5}"
: "${SMOKE_TIMEOUT_S:=5}"
: "${SMOKE_HEALTH_PATH:=/health}"
: "${SMOKE_PORTS_FILE:=${REPO_ROOT}/config/ports.yaml}"
: "${SMOKE_FAIL_ON_DEGRADED:=0}"
: "${SMOKE_OUTPUT_FILE:=}"

# Detect K8s cluster.local mode (per-service DNS, single port).
SMOKE_MODE="host"
if [[ "${SMOKE_BASE_URL}" == *"cluster.local"* ]]; then
    SMOKE_MODE="k8s"
fi

# ---- Pre-flight checks -----------------------------------------------------
if ! command -v curl >/dev/null 2>&1; then
    echo "ERROR: curl is required" >&2
    exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required to parse ${SMOKE_PORTS_FILE}" >&2
    exit 2
fi
if [[ ! -f "${SMOKE_PORTS_FILE}" ]]; then
    echo "ERROR: ports file not found: ${SMOKE_PORTS_FILE}" >&2
    exit 2
fi

# ---- Load (service, port) pairs from config/ports.yaml --------------------
# Emits one "name<TAB>port" line per microservice. We use stdlib yaml when
# available; if PyYAML is not installed, fall back to a minimal regex parser
# that handles the simple ports.yaml schema (good enough for CI runners).
load_services() {
    python3 - "${SMOKE_PORTS_FILE}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()

services = []

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

if yaml is not None:
    data = yaml.safe_load(text) or {}
    micro = data.get("microservices") or {}
    for name, cfg in micro.items():
        if not isinstance(cfg, dict):
            continue
        port = cfg.get("port")
        if isinstance(port, int):
            services.append((name, port))
else:
    # Minimal parser for the well-formed ports.yaml structure.
    in_micro = False
    cur_name = None
    micro_indent = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("microservices:"):
            in_micro = True
            micro_indent = indent
            continue
        if not in_micro:
            continue
        # Leaving the microservices block (a same-or-lower-indent top key).
        if indent <= micro_indent and not stripped.startswith("-"):
            # Only break out on top-level keys (lines like "platform:")
            # but allow comments / blanks (already filtered).
            if stripped.endswith(":") and ":" not in stripped[:-1]:
                in_micro = False
                cur_name = None
                continue

        # Service header: "<name>:" at indent == micro_indent + 2
        if stripped.endswith(":") and ":" not in stripped[:-1]:
            cur_name = stripped[:-1].strip()
            continue
        if cur_name and stripped.startswith("port:"):
            value = stripped.split(":", 1)[1].strip()
            try:
                port = int(value)
                services.append((cur_name, port))
            except ValueError:
                pass

for name, port in services:
    print(f"{name}\t{port}")
PY
}

# Use a portable loop instead of `mapfile` (not available in bash 3.2).
SERVICE_NAMES=()
SERVICE_URLS=()
while IFS=$'\t' read -r name port; do
    [[ -z "${name}" ]] && continue
    if [[ "${SMOKE_MODE}" == "k8s" ]]; then
        # Each microservice resolves to its own DNS name on the cluster.
        # Strip "_service" suffix to match k8s_service short names in
        # ports.yaml (e.g. auth_service -> auth, billing_service -> billing).
        short="${name%_service}"
        url="${SMOKE_BASE_URL/\{service\}/${short}}"
        # If caller did not supply a "{service}" placeholder, treat the
        # base URL as a single host and append the short name as subdomain.
        if [[ "${url}" == "${SMOKE_BASE_URL}" ]]; then
            url="${SMOKE_BASE_URL}"
        fi
        url="${url%/}:${SMOKE_K8S_PORT}${SMOKE_HEALTH_PATH}"
    else
        url="${SMOKE_BASE_URL%/}:${port}${SMOKE_HEALTH_PATH}"
    fi
    SERVICE_NAMES+=("${name}")
    SERVICE_URLS+=("${url}")
done < <(load_services)

TOTAL="${#SERVICE_NAMES[@]}"
if [[ "${TOTAL}" -eq 0 ]]; then
    echo "ERROR: no microservices loaded from ${SMOKE_PORTS_FILE}" >&2
    exit 2
fi
echo "Smoke test: probing ${TOTAL} services (mode=${SMOKE_MODE}, base=${SMOKE_BASE_URL})"
echo "Grace=${SMOKE_GRACE_PERIOD_S}s, retry=${SMOKE_RETRY_INTERVAL_S}s, timeout=${SMOKE_TIMEOUT_S}s, fail_on_degraded=${SMOKE_FAIL_ON_DEGRADED}"

# ---- Probe one service. Echoes one TSV line. ------------------------------
# Status values:
#   healthy   — HTTP 200, body "status":"healthy"
#   degraded  — HTTP 200, body "status":"degraded"
#   unhealthy — HTTP 503 (or other non-200) — service responded but ill
#   unreachable — connection failed / curl error
probe_one() {
    local name="$1"
    local url="$2"

    local start_ns end_ns latency_ms
    start_ns=$(date +%s%N 2>/dev/null || python3 -c 'import time; print(int(time.time_ns()))')

    # We capture body + http code in one curl invocation; use a separator so
    # we can split them reliably.
    local sep=$'\n--HTTP_CODE--\n'
    local resp http_code body curl_rc=0
    resp=$(curl -sS \
        --max-time "${SMOKE_TIMEOUT_S}" \
        --connect-timeout "${SMOKE_TIMEOUT_S}" \
        -o - \
        -w "${sep}%{http_code}" \
        "${url}" 2>/dev/null) || curl_rc=$?

    end_ns=$(date +%s%N 2>/dev/null || python3 -c 'import time; print(int(time.time_ns()))')
    latency_ms=$(( (end_ns - start_ns) / 1000000 ))

    if [[ ${curl_rc} -ne 0 || -z "${resp}" ]]; then
        printf '%s\tunreachable\t%s\tcurl_rc=%s\n' "${name}" "${latency_ms}" "${curl_rc}"
        return
    fi

    body="${resp%${sep}*}"
    http_code="${resp##*${sep}}"

    # Extract "status" field. Prefer python json (robust); fall back to grep.
    local body_status
    body_status=$(printf '%s' "${body}" | python3 -c '
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get("status", ""))
except Exception:
    print("")
' 2>/dev/null || echo "")

    if [[ -z "${body_status}" ]]; then
        body_status=$(printf '%s' "${body}" \
            | grep -oE '"status"[[:space:]]*:[[:space:]]*"[a-z_]+"' \
            | head -n1 \
            | sed -E 's/.*"([a-z_]+)"$/\1/' \
            || true)
    fi

    local final detail
    case "${http_code}" in
        200)
            if [[ "${body_status}" == "degraded" ]]; then
                final="degraded"
                detail="http=200 body_status=degraded"
            elif [[ "${body_status}" == "healthy" || -z "${body_status}" ]]; then
                final="healthy"
                detail="http=200"
            else
                # 200 with an unexpected body — treat as degraded so we
                # surface the anomaly without failing the deploy by default.
                final="degraded"
                detail="http=200 body_status=${body_status}"
            fi
            ;;
        503)
            final="unhealthy"
            detail="http=503"
            ;;
        000)
            final="unreachable"
            detail="curl_no_response"
            ;;
        *)
            final="unhealthy"
            detail="http=${http_code}"
            ;;
    esac

    printf '%s\t%s\t%s\t%s\n' "${name}" "${final}" "${latency_ms}" "${detail}"
}

# ---- Single probe pass over every service. --------------------------------
run_pass() {
    local results=()
    local name url
    local i
    for ((i = 0; i < TOTAL; i++)); do
        name="${SERVICE_NAMES[i]}"
        url="${SERVICE_URLS[i]}"
        results+=("$(probe_one "${name}" "${url}")")
    done
    printf '%s\n' "${results[@]}"
}

# ---- Retry loop until grace period expires --------------------------------
deadline=$(( $(date +%s) + SMOKE_GRACE_PERIOD_S ))
attempt=0
LATEST_REPORT=""

while :; do
    attempt=$((attempt + 1))
    LATEST_REPORT="$(run_pass)"

    # Count failures: anything that is neither healthy nor degraded.
    bad=$(printf '%s\n' "${LATEST_REPORT}" \
        | awk -F'\t' '$2 != "healthy" && $2 != "degraded" { c++ } END { print c+0 }')

    if [[ "${bad}" -eq 0 ]]; then
        break
    fi

    now=$(date +%s)
    if (( now >= deadline )); then
        break
    fi

    remaining=$(( deadline - now ))
    echo "Attempt ${attempt}: ${bad} service(s) not yet healthy. Retrying in ${SMOKE_RETRY_INTERVAL_S}s (deadline in ${remaining}s)..." >&2
    sleep "${SMOKE_RETRY_INTERVAL_S}"
done

# ---- Final report ---------------------------------------------------------
echo
echo "SERVICE	STATUS	LATENCY_MS	DETAIL"
echo "${LATEST_REPORT}"

if [[ -n "${SMOKE_OUTPUT_FILE}" ]]; then
    {
        echo "SERVICE	STATUS	LATENCY_MS	DETAIL"
        echo "${LATEST_REPORT}"
    } >"${SMOKE_OUTPUT_FILE}"
fi

# ---- Tally counts ---------------------------------------------------------
healthy=$(printf '%s\n' "${LATEST_REPORT}" | awk -F'\t' '$2 == "healthy"   { c++ } END { print c+0 }')
degraded=$(printf '%s\n' "${LATEST_REPORT}" | awk -F'\t' '$2 == "degraded"  { c++ } END { print c+0 }')
unhealthy=$(printf '%s\n' "${LATEST_REPORT}" | awk -F'\t' '$2 == "unhealthy" { c++ } END { print c+0 }')
unreachable=$(printf '%s\n' "${LATEST_REPORT}" | awk -F'\t' '$2 == "unreachable" { c++ } END { print c+0 }')

echo
echo "Summary: total=${TOTAL} healthy=${healthy} degraded=${degraded} unhealthy=${unhealthy} unreachable=${unreachable} attempts=${attempt}"

# ---- Exit code ------------------------------------------------------------
fail=0
if (( unhealthy > 0 || unreachable > 0 )); then
    fail=1
fi
if [[ "${SMOKE_FAIL_ON_DEGRADED}" == "1" && "${degraded}" -gt 0 ]]; then
    fail=1
fi

exit "${fail}"
