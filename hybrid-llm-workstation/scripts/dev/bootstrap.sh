#!/usr/bin/env bash
# One-shot local dev bootstrap: venv, dependencies, .env, migrations, admin
# user. Safe to re-run — every step is idempotent.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if [ ! -f .env ]; then
    cp .env.example .env
    AUTH_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    AGENT_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    PROXY_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i.bak "s#^AUTH_SECRET=.*#AUTH_SECRET=${AUTH_SECRET}#" .env
    sed -i.bak "s#^EXECUTION_AGENT_TOKEN=.*#EXECUTION_AGENT_TOKEN=${AGENT_TOKEN}#" .env
    sed -i.bak "s#^OPEN_WEBUI_PROXY_TOKEN=.*#OPEN_WEBUI_PROXY_TOKEN=${PROXY_TOKEN}#" .env
    rm -f .env.bak
    echo "Created .env with freshly generated secrets."
else
    echo ".env already exists — leaving it as-is."
fi

if [ ! -x ".venv/bin/python3" ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt -r local-agent/requirements.txt
echo "Python dependencies installed."

set -a
source .env
set +a
.venv/bin/alembic upgrade head
echo "Database migrated."

if [ -z "${WORKSTATION_ADMIN_PASSWORD:-}" ]; then
    echo
    echo "No WORKSTATION_ADMIN_PASSWORD set. Create your admin user with:"
    echo "  PYTHONPATH=libs/core:. .venv/bin/python3 database/seeds/seed_admin.py --username <you> --password <pw>"
else
    PYTHONPATH=libs/core:. .venv/bin/python3 database/seeds/seed_admin.py \
        --username "${WORKSTATION_ADMIN_USERNAME:-admin}" --password "${WORKSTATION_ADMIN_PASSWORD}"
fi

echo
echo "Next steps:"
echo "  make control-dev   # terminal 1"
echo "  make worker-dev    # terminal 2"
echo "  make agent-dev     # terminal 3, on the laptop that should be controllable"
echo "  make health        # verify everything is talking to everything"
