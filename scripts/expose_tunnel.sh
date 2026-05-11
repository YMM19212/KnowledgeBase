#!/usr/bin/env bash

set -euo pipefail

LOG_FILE="/tmp/knowledgebase-cloudflared.log"
SCREEN_NAME="knowledgebase-tunnel"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-$(command -v cloudflared || true)}"
LOCAL_URL="${LOCAL_URL:-http://127.0.0.1:8000}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-3}"
WAIT_SECONDS="${WAIT_SECONDS:-30}"

if [[ -z "${CLOUDFLARED_BIN}" ]]; then
  echo "cloudflared not found. Install it first: brew install cloudflared" >&2
  exit 1
fi

if ! command -v screen >/dev/null 2>&1; then
  echo "screen not found. Install it or run cloudflared manually." >&2
  exit 1
fi

if ! curl -fsS "${LOCAL_URL}/health" >/dev/null 2>&1; then
  echo "Local backend is not reachable at ${LOCAL_URL}. Start it first, for example: make dev" >&2
  exit 1
fi

for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
  screen -S "${SCREEN_NAME}" -X quit >/dev/null 2>&1 || true
  rm -f "${LOG_FILE}"

  screen -dmS "${SCREEN_NAME}" \
    "${CLOUDFLARED_BIN}" tunnel --url "${LOCAL_URL}" --no-autoupdate --logfile "${LOG_FILE}"

  for _ in $(seq 1 "${WAIT_SECONDS}"); do
    if [[ -f "${LOG_FILE}" ]]; then
      URL="$(grep -Eo 'https://[-a-zA-Z0-9]+\.trycloudflare\.com' "${LOG_FILE}" | tail -n 1 || true)"
      if [[ -n "${URL}" ]]; then
        echo "${URL}/v1"
        exit 0
      fi
    fi
    sleep 1
  done

  if [[ -f "${LOG_FILE}" ]]; then
    if grep -q "Error unmarshaling QuickTunnel response" "${LOG_FILE}"; then
      echo "Cloudflare quick tunnel failed on attempt ${attempt}/${MAX_ATTEMPTS}, retrying..." >&2
      continue
    fi
  fi

  break
done

echo "Tunnel URL was not discovered. Check ${LOG_FILE} for details." >&2
exit 1
