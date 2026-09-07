# Personal LLM Workstation

One interface for local Ollama models, on-demand cloud GPU models,
persistent conversations, background tasks, GPU lifecycle management, and
controlled laptop execution.

This is a standalone system — see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
for the full design and [`HYBRID_LLM_WORKSTATION_BUILD_SPEC.md`](../HYBRID_LLM_WORKSTATION_BUILD_SPEC.md)
(or wherever your copy of the build spec lives) for the requirements this
implements.

## What you get

- **Open WebUI** as the single chat interface, showing local and cloud
  models side by side.
- **Local inference** via your own Ollama installation.
- **Cloud inference** on a GPU you rent on demand (RunPod by default),
  which starts automatically when you need it and stops itself when idle,
  within cost limits you configure.
- **Background tasks** — chat/generate jobs and laptop-action requests
  that run independently of the browser, with persisted progress/results
  and notifications on completion or failure.
- **A local execution agent** — the only thing on your laptop an LLM-driven
  task can ever touch, and only through an explicit, auditable,
  approval-gated policy.

## Quick start (native, no Docker)

```bash
bash scripts/dev/bootstrap.sh          # venv, deps, .env with fresh secrets, migrations
# set WORKSTATION_ADMIN_PASSWORD in .env, or:
PYTHONPATH=libs/core:. .venv/bin/python3 database/seeds/seed_admin.py --username <you> --password <pw>

make control-dev     # terminal 1 — the control API, :8000
make worker-dev       # terminal 2 — a background worker
make agent-dev        # terminal 3 — the local execution agent, :8787
make health           # verify everything is talking to everything
```

Then either talk to the control API directly (see
[`docs/API.md`](docs/API.md)) or run Open WebUI and point it at the local
Ollama connection plus `http://localhost:8000/proxy/cloud` for the cloud
one (see `docker-compose.yml`'s comments).

## Quick start (Docker Compose)

```bash
cp .env.example .env   # then edit AUTH_SECRET, EXECUTION_AGENT_TOKEN, OPEN_WEBUI_PROXY_TOKEN
make up                 # control + worker + open-webui
make agent-dev           # the local agent still runs natively — see local-agent/Dockerfile
```

## Repository layout

```
apps/control/     the control API (FastAPI) — model registry, GPU
                   lifecycle, task API, approvals, notifications, audit
worker/           background worker process(es)
local-agent/      the local execution agent (independent, minimal deps)
gpu/              GPU provider abstraction + implementations + cloud image
libs/core/        shared library used by control + worker (not the agent)
database/         Alembic migrations + seed scripts
config/           models.yaml, providers.yaml, policies.yaml, notifications.yaml
scripts/          install (phases A-D), health checks, backup/restore
tests/            unit, integration, e2e, security, acceptance suites
docs/             architecture, security, API, operations, runbook
```

## Status

Build-ready and covered by 151 automated tests (146 passing, 5 explicitly
skipped where they require hardware this build couldn't provide — see
[`TEST_REPORT.md`](TEST_REPORT.md)). See
[`BUILD_REPORT.md`](BUILD_REPORT.md) for what's been verified against a
real running stack versus what still needs your own Ollama installation,
cloud account, and browser to confirm.

## License

MIT — see [`LICENSE`](LICENSE).
