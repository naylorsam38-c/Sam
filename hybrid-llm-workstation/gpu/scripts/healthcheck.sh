#!/usr/bin/env bash
# Standalone health probe for a cloud GPU's inference endpoint — the same
# check gpu/providers/*/provider.py's health() methods perform over HTTP,
# exposed as a script for manual verification during install Phase B.
#
# Usage: OLLAMA_URL=http://<pod-ip>:<port> ./gpu/scripts/healthcheck.sh
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

if curl -fsS --max-time 5 "${OLLAMA_URL}/" > /dev/null; then
    echo "OK: ${OLLAMA_URL} is responding"
    exit 0
else
    echo "FAIL: ${OLLAMA_URL} did not respond" >&2
    exit 1
fi
