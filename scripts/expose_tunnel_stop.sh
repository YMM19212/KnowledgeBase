#!/usr/bin/env bash

set -euo pipefail

SCREEN_NAME="knowledgebase-tunnel"

if ! command -v screen >/dev/null 2>&1; then
  echo "screen not found." >&2
  exit 1
fi

screen -S "${SCREEN_NAME}" -X quit >/dev/null 2>&1 || true
echo "Stopped tunnel screen: ${SCREEN_NAME}"
