#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8202}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
ORG_ID="${ORG_ID:-org_partner_001}"

if [[ -z "$ADMIN_TOKEN" ]]; then
  echo "ADMIN_TOKEN is required" >&2
  exit 1
fi

create_resp=$(curl -sS -X POST "$BASE_URL/api/v1/auth/oauth/clients" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d "{\"client_name\":\"partner-agent\",\"organization_id\":\"${ORG_ID}\",\"allowed_scopes\":[\"a2a.invoke\",\"a2a.tasks.read\"],\"token_ttl_seconds\":3600}")

client_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["client_id"])' <<<"$create_resp")
client_secret=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["client_secret"])' <<<"$create_resp")

token_resp=$(curl -sS -X POST "$BASE_URL/oauth/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=client_credentials&client_id=${client_id}&client_secret=${client_secret}&scope=a2a.invoke")

access_token=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])' <<<"$token_resp")

verify_resp=$(curl -sS -X POST "$BASE_URL/api/v1/auth/verify-token" \
  -H 'Content-Type: application/json' \
  -d "{\"token\":\"${access_token}\",\"provider\":\"isa_user\"}")

valid=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("valid"))' <<<"$verify_resp")

echo "client_id=${client_id}"
echo "token_valid=${valid}"

echo "Rotate client secret"
curl -sS -X POST "$BASE_URL/api/v1/auth/oauth/clients/${client_id}/rotate-secret" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" >/dev/null

echo "Deactivate client"
curl -sS -X DELETE "$BASE_URL/api/v1/auth/oauth/clients/${client_id}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" >/dev/null

echo "Done"
