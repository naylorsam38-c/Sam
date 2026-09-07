#!/usr/bin/env bash
# Starts the configured GPU provider, waits for READY, checks cost
# reporting, then stops it again. Safe and free against GPU_PROVIDER=mock;
# WILL INCUR REAL COST against any real provider (e.g. runpod) — this
# script deliberately requires WORKSTATION_CONFIRM_GPU_COST=yes to proceed
# against anything other than mock, rather than guessing that's what you
# want (spec: "if something is unknown, do not guess... surface it clearly").
#
# Usage: WORKSTATION_USERNAME=sam WORKSTATION_PASSWORD=... bash scripts/health/gpu_smoke_test.sh
set -uo pipefail

CONTROL_URL="${CONTROL_API_URL:-http://localhost:8000}"
USERNAME="${WORKSTATION_USERNAME:?set WORKSTATION_USERNAME}"
PASSWORD="${WORKSTATION_PASSWORD:?set WORKSTATION_PASSWORD}"

TOKEN=$(curl -fsS -X POST "${CONTROL_URL}/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

if [ -z "${TOKEN}" ]; then
    echo "FAIL: could not authenticate against ${CONTROL_URL}" >&2
    exit 1
fi
AUTH=(-H "Authorization: Bearer ${TOKEN}")

PROVIDER=$(curl -fsS "${CONTROL_URL}/api/gpu" "${AUTH[@]}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["provider"])')
echo "GPU_PROVIDER=${PROVIDER}"

if [ "${PROVIDER}" != "mock" ] && [ "${WORKSTATION_CONFIRM_GPU_COST:-}" != "yes" ]; then
    echo "REFUSING to start a real GPU provider ('${PROVIDER}') without confirmation." >&2
    echo "This will incur real cloud cost. Set WORKSTATION_CONFIRM_GPU_COST=yes to proceed." >&2
    exit 1
fi

echo "Starting GPU..."
curl -fsS -X POST "${CONTROL_URL}/api/gpu/start" "${AUTH[@]}" >/dev/null

for _ in $(seq 1 120); do
    STATUS=$(curl -fsS "${CONTROL_URL}/api/gpu" "${AUTH[@]}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
    echo "  status=${STATUS}"
    [ "${STATUS}" = "READY" ] && break
    [ "${STATUS}" = "ERROR" ] && { echo "FAIL: GPU entered ERROR state" >&2; exit 1; }
    sleep 2
done

if [ "${STATUS}" != "READY" ]; then
    echo "FAIL: GPU did not reach READY within the timeout" >&2
    exit 1
fi

echo "Cost report:"
curl -fsS "${CONTROL_URL}/api/gpu/cost" "${AUTH[@]}"
echo

echo "Stopping GPU..."
curl -fsS -X POST "${CONTROL_URL}/api/gpu/stop" "${AUTH[@]}" >/dev/null
STATUS=$(curl -fsS "${CONTROL_URL}/api/gpu" "${AUTH[@]}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
if [ "${STATUS}" = "OFF" ]; then
    echo "PASS: GPU smoke test succeeded (start -> READY -> cost -> stop -> OFF)"
else
    echo "FAIL: GPU did not return to OFF after stop (status=${STATUS})" >&2
    exit 1
fi
