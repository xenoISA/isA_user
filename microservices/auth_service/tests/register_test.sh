#!/usr/bin/env bash

set -euo pipefail

# Simple E2E registration test for auth_service
# Requirements: curl, jq

AUTH_BASE_URL=${AUTH_BASE_URL:-"http://localhost:8201"}

usage() {
  echo "Usage: AUTH_BASE_URL=<url> $0 <email> <password> [name]" >&2
  echo "Example: AUTH_BASE_URL=http://localhost:8201 $0 alice@example.com Strong#123 Alice" >&2
}

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required. Please install jq (e.g., brew install jq)." >&2
  exit 1
fi

if [ "$#" -lt 2 ]; then
  usage
  exit 1
fi

EMAIL="$1"
PASSWORD="$2"
NAME="${3:-${EMAIL%@*}}"

echo "[1/3] Starting registration at: ${AUTH_BASE_URL}"
REGISTER_RESP=$(curl -sS -X POST "${AUTH_BASE_URL}/api/v1/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\", \"name\": \"${NAME}\"}")

echo "Register response: ${REGISTER_RESP}" | jq '.' || true

PENDING_ID=$(echo "${REGISTER_RESP}" | jq -r '.pending_registration_id // empty')
EXPIRES_AT=$(echo "${REGISTER_RESP}" | jq -r '.expires_at // empty')

if [ -z "${PENDING_ID}" ]; then
  echo "Failed to obtain pending_registration_id from response." >&2
  exit 1
fi

echo "Pending Registration ID: ${PENDING_ID}"
echo "Expires At: ${EXPIRES_AT}"

# Try to get verification code from dev endpoint (if available in debug mode)
CODE=""
DEV_CODE_RESP=$(curl -sS "${AUTH_BASE_URL}/api/v1/auth/dev/pending-registration/${PENDING_ID}" 2>/dev/null || echo "")

if [ -n "${DEV_CODE_RESP}" ]; then
  DEV_CODE=$(echo "${DEV_CODE_RESP}" | jq -r '.verification_code // empty' 2>/dev/null || echo "")
  EXPIRED=$(echo "${DEV_CODE_RESP}" | jq -r '.expired // false' 2>/dev/null || echo "false")
  
  if [ "${EXPIRED}" = "true" ]; then
    echo "⚠ WARNING: Pending registration has expired."
    exit 1
  fi
  
  if [ -n "${DEV_CODE}" ] && [ "${DEV_CODE}" != "null" ]; then
    echo "✓ Retrieved verification code from dev endpoint: ${DEV_CODE}"
    CODE="${DEV_CODE}"
  fi
fi

# Fallback: prompt user or use env var
if [ -z "${CODE}" ]; then
  CODE="${VERIFICATION_CODE:-}"
  if [ -z "${CODE}" ]; then
    echo "A verification code should have been emailed to ${EMAIL}."
    echo "If running locally, check auth_service logs for the code (dev mode)."
    read -r -p "Enter verification code: " CODE
  fi
fi

if [ -z "${CODE}" ]; then
  echo "Verification code cannot be empty." >&2
  exit 1
fi

echo "[2/3] Verifying registration..."
VERIFY_RESP=$(curl -sS -X POST "${AUTH_BASE_URL}/api/v1/auth/verify" \
  -H 'Content-Type: application/json' \
  -d "{\"pending_registration_id\": \"${PENDING_ID}\", \"code\": \"${CODE}\"}")

echo "Verify response: ${VERIFY_RESP}" | jq '.' || true

SUCCESS=$(echo "${VERIFY_RESP}" | jq -r '.success // false')
if [ "${SUCCESS}" != "true" ]; then
  echo "Verification failed." >&2
  exit 2
fi

USER_ID=$(echo "${VERIFY_RESP}" | jq -r '.user_id')
ACCESS_TOKEN=$(echo "${VERIFY_RESP}" | jq -r '.access_token')

echo "[3/3] Registration completed successfully."
echo "User ID: ${USER_ID}"
echo "Access Token (truncated): ${ACCESS_TOKEN:0:32}..."

echo "Done."


