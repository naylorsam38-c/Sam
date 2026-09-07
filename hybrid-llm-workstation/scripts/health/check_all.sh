#!/usr/bin/env bash
# Query every /health/* endpoint on a running control API and report real
# status — no fabricated "all green" output (spec operational rule #12).
set -uo pipefail

CONTROL_URL="${CONTROL_API_URL:-http://localhost:8000}"
FAIL=0

check() {
    local path="$1"
    local url="${CONTROL_URL}${path}"
    if body=$(curl -fsS --max-time 5 "${url}" 2>/dev/null); then
        healthy=$(echo "${body}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["healthy"])' 2>/dev/null || echo "unknown")
        detail=$(echo "${body}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("detail",""))' 2>/dev/null || echo "")
        if [ "${healthy}" = "True" ]; then
            echo "OK    ${path}: ${detail}"
        else
            echo "DOWN  ${path}: ${detail}"
            FAIL=1
        fi
    else
        echo "DOWN  ${path}: unreachable at ${url}"
        FAIL=1
    fi
}

echo "Checking ${CONTROL_URL} ..."
check "/health"
check "/health/local-ollama"
check "/health/cloud"
check "/health/worker"
check "/health/agent"

exit "${FAIL}"
