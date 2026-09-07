#!/usr/bin/env bash
# Install Phase A — Laptop (spec section 21).
# Run from the repo root: bash scripts/install/phase_a_laptop.sh
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
source scripts/install/lib.sh

OLLAMA_URL="${OLLAMA_LOCAL_URL:-http://localhost:11434}"

step "1. Verify operating system"
OS_NAME="$(uname -s)"
case "${OS_NAME}" in
    Linux|Darwin) pass "operating system: ${OS_NAME}" ;;
    *) fail "unsupported/unrecognised OS: ${OS_NAME}" ;;
esac

step "2. Verify Ollama installation"
if have_cmd ollama; then
    pass "ollama binary found: $(command -v ollama)"
else
    fail "ollama is not installed — install it from https://ollama.com before continuing"
fi

step "3. Verify Ollama service"
if curl -fsS --max-time 5 "${OLLAMA_URL}/" >/dev/null 2>&1; then
    pass "Ollama responding at ${OLLAMA_URL}"
else
    fail "Ollama is not responding at ${OLLAMA_URL} — start it with 'ollama serve' (or the installed service)"
fi

step "4. Discover installed local models"
if TAGS=$(curl -fsS --max-time 5 "${OLLAMA_URL}/api/tags" 2>/dev/null); then
    MODEL_COUNT=$(echo "${TAGS}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("models", [])))' 2>/dev/null || echo "?")
    if [ "${MODEL_COUNT}" = "0" ]; then
        skip "Ollama is up but has 0 models installed yet — run 'ollama pull llama3.2' before Phase C"
    else
        pass "found ${MODEL_COUNT} local model(s)"
    fi
else
    skip "could not query /api/tags (Ollama not reachable — see step 3)"
fi

step "5/6. Open WebUI + connection to local Ollama"
if have_cmd docker; then
    if docker compose ps open-webui >/dev/null 2>&1; then
        pass "docker is available; run 'docker compose up -d open-webui' to (re)start it if needed"
    else
        skip "docker is available but open-webui is not running yet — run 'make up' or 'docker compose up -d open-webui'"
    fi
else
    skip "docker not found — install Docker to run Open WebUI via docker-compose.yml, or run it manually per its own docs"
fi

step "7. Verify local chat is reachable end-to-end"
if [ "${MODEL_COUNT:-0}" != "0" ] 2>/dev/null && curl -fsS --max-time 5 "${OLLAMA_URL}/" >/dev/null 2>&1; then
    pass "Ollama is up with at least one model — local chat is exercisable via the control API or Open WebUI"
else
    skip "cannot verify local chat until Ollama is running with at least one model installed"
fi

step "8. Install control service dependencies"
if [ -x ".venv/bin/python3" ]; then
    pass ".venv already exists"
else
    if have_cmd python3; then
        python3 -m venv .venv && .venv/bin/pip install --upgrade pip -q && .venv/bin/pip install -q -r requirements.txt
        pass "created .venv and installed requirements.txt"
    else
        fail "python3 not found — required for the control API and worker"
    fi
fi

step "9. Initialise database"
if [ -x ".venv/bin/alembic" ]; then
    if .venv/bin/alembic upgrade head >/tmp/workstation_migrate.log 2>&1; then
        pass "database migrated to head"
    else
        fail "alembic upgrade head failed — see /tmp/workstation_migrate.log"
    fi
else
    skip "alembic not installed yet (see step 8)"
fi

step "10. Worker"
skip "start with 'make worker-dev' (or docker compose up -d worker) once the control API is confirmed healthy"

step "11. Install local execution agent dependencies"
if [ -x ".venv/bin/python3" ]; then
    .venv/bin/pip install -q -r local-agent/requirements.txt && pass "local-agent dependencies installed into .venv"
else
    skip "no .venv yet (see step 8)"
fi

step "12. Pair/authenticate agent"
if [ -f .env ] && grep -q '^EXECUTION_AGENT_TOKEN=change-me' .env 2>/dev/null; then
    fail "EXECUTION_AGENT_TOKEN in .env is still the placeholder value — generate a real secret before starting the agent"
elif [ -f .env ]; then
    pass "EXECUTION_AGENT_TOKEN appears to have been customised in .env"
else
    skip "no .env file yet — copy .env.example to .env and set AUTH_SECRET / EXECUTION_AGENT_TOKEN"
fi

step "13. Run health checks"
if [ -x scripts/health/check_all.sh ]; then
    bash scripts/health/check_all.sh || true
else
    skip "scripts/health/check_all.sh not found"
fi

summary
