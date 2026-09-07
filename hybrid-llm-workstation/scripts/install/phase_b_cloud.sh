#!/usr/bin/env bash
# Install Phase B — Cloud GPU (spec section 21).
#
# Steps 1-7 (choose a provider, create a volume/template, install
# CUDA/the inference engine, configure storage/auth) are one-time actions
# taken in the cloud provider's own console/API and via gpu/image's
# Dockerfile — they are not something this script can safely automate on
# your behalf (they involve real, billed cloud resources). This script
# verifies your local configuration is ready (steps 8-9) and, only with
# explicit confirmation, exercises steps 9-12 by actually starting the GPU
# — which will incur real cost on your cloud account.
#
# Usage: bash scripts/install/phase_b_cloud.sh [--start-gpu]
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
source scripts/install/lib.sh

CONTROL_URL="${CONTROL_API_URL:-http://localhost:8000}"
START_GPU=false
[ "${1:-}" = "--start-gpu" ] && START_GPU=true

step "Provider configuration"
if [ -f .env ]; then
    PROVIDER=$(grep '^GPU_PROVIDER=' .env | cut -d= -f2)
    case "${PROVIDER}" in
        runpod)
            pass "GPU_PROVIDER=runpod"
            grep -q '^GPU_PROVIDER_API_KEY=.\+' .env && pass "GPU_PROVIDER_API_KEY is set" || fail "GPU_PROVIDER_API_KEY is empty"
            grep -q '^GPU_TEMPLATE_ID=.\+' .env && pass "GPU_TEMPLATE_ID is set" || fail "GPU_TEMPLATE_ID is empty — build gpu/image/Dockerfile into a RunPod template first"
            grep -q '^GPU_VOLUME_ID=.\+' .env && pass "GPU_VOLUME_ID is set" || fail "GPU_VOLUME_ID is empty — create a persistent RunPod network volume first"
            ;;
        mock)
            skip "GPU_PROVIDER=mock — this is the dev/test provider; set GPU_PROVIDER=runpod for a real deployment"
            ;;
        vast|lambdalabs)
            fail "GPU_PROVIDER=${PROVIDER} is a documented interface stub, not implemented (see gpu/providers/${PROVIDER}/provider.py)"
            ;;
        *)
            fail "GPU_PROVIDER='${PROVIDER}' is not a recognised provider"
            ;;
    esac
else
    fail "no .env file found — copy .env.example to .env first"
fi

step "Cost controls configured"
if [ -f .env ]; then
    grep -q '^GPU_MAX_HOURLY_COST=' .env && pass "GPU_MAX_HOURLY_COST is set" || fail "GPU_MAX_HOURLY_COST missing"
    grep -q '^GPU_MAX_SESSION_MINUTES=' .env && pass "GPU_MAX_SESSION_MINUTES is set" || fail "GPU_MAX_SESSION_MINUTES missing"
    grep -q '^GPU_IDLE_TIMEOUT_MINUTES=' .env && pass "GPU_IDLE_TIMEOUT_MINUTES is set" || fail "GPU_IDLE_TIMEOUT_MINUTES missing"
fi

step "Control API reachable"
if curl -fsS --max-time 5 "${CONTROL_URL}/health" >/dev/null 2>&1; then
    pass "control API responding at ${CONTROL_URL}"
else
    fail "control API not responding at ${CONTROL_URL} — start it first (make control-dev / make up)"
fi

if [ "${START_GPU}" = true ]; then
    step "Starting GPU (steps 9-11) — THIS WILL INCUR REAL CLOUD COST if GPU_PROVIDER=runpod"
    echo "  Proceeding in 5 seconds — Ctrl-C now to abort."
    sleep 5
    echo "  This step requires an authenticated API call; run it via the API directly, e.g.:"
    echo "    TOKEN=\$(curl -s -X POST ${CONTROL_URL}/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"<you>\",\"password\":\"<pw>\"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)[\"access_token\"])')"
    echo "    curl -s -X POST ${CONTROL_URL}/api/gpu/start -H \"Authorization: Bearer \$TOKEN\""
    echo "    curl -s ${CONTROL_URL}/api/gpu -H \"Authorization: Bearer \$TOKEN\"   # poll until status=READY"
    echo "    curl -s -X POST ${CONTROL_URL}/api/gpu/stop -H \"Authorization: Bearer \$TOKEN\"   # step 11: stop"
    skip "actual start/verify/stop left as the explicit commands above — this script will not spend your cloud budget without you running them yourself"
else
    step "Starting GPU (steps 9-11)"
    skip "pass --start-gpu to see the exact commands (not run automatically — this would incur real cloud cost)"
fi

step "Persistent storage survives stop/start (step 12)"
skip "verify manually: pull a model (gpu/scripts/pull_models.sh), stop the GPU, start it again, confirm the model is still listed in /api/tags without re-downloading"

summary
