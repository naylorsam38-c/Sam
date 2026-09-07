# Operations

## Running it

See the root [`README.md`](../README.md) for the two quick-start paths
(native / Docker Compose). This document covers day-to-day operation.

## Everyday commands

```
make health              # real /health/* checks against a running deployment
make gpu-smoke-test       # start -> READY -> cost -> stop, safe against GPU_PROVIDER=mock,
                          #   requires WORKSTATION_CONFIRM_GPU_COST=yes against a real provider
make backup               # export all persistent state to backups/workstation-export-*.json
make restore FILE=...     # restore into a freshly-migrated, empty database
make test                 # the full automated suite
```

## Docker Compose topology

`docker-compose.yml` runs `control`, `worker`, and `open-webui`. The
**local execution agent is not a compose service** — run it natively on
the laptop (`make agent-dev`, or the `local-agent/Dockerfile` if you
specifically want it containerized with a bind-mounted workspace). This is
intentional: the agent needs direct, correctly-scoped access to the real
filesystem paths named in `config/policies.yaml`.

On Linux, containers reach the host via `host.docker.internal` (wired via
`extra_hosts: host-gateway` in the compose file already) — set
`OLLAMA_LOCAL_URL` and `EXECUTION_AGENT_URL` in `.env` to
`http://host.docker.internal:<port>` when running via Compose (see the
comments in `.env.example`).

## Open WebUI wiring

1. Start Open WebUI (`make up`, or standalone). It auto-connects to local
   Ollama via `OLLAMA_BASE_URL`.
2. In Open WebUI's Admin Settings → Connections, add a second "Ollama API"
   connection:
   - URL: `http://<control-host>:8000/proxy/cloud`
   - API key: your `OPEN_WEBUI_PROXY_TOKEN`
3. Start the GPU (`POST /api/gpu/start` or your own future UI) and wait
   for `READY`. Open WebUI's cloud connection will then list whatever
   `/api/models/refresh` last discovered — click "refresh" in Open WebUI
   or hit `POST /api/models/refresh` yourself after the GPU becomes ready.

This connection never needs updating again even though the GPU's actual
IP changes every session — the proxy forwards to whatever's currently live.

## GPU cost controls

Configured in `.env`:

| Variable | Meaning |
|---|---|
| `GPU_IDLE_TIMEOUT_MINUTES` | minutes of no activity before the GPU is marked `IDLE` (and stopped, if `GPU_AUTO_STOP`) |
| `GPU_MAX_SESSION_MINUTES` | hard cap on one continuous session's duration |
| `GPU_MAX_HOURLY_COST` | both a pre-flight check (refuses to stay up if the provider's rate exceeds this) and, combined with `GPU_MAX_SESSION_MINUTES`, an accrued-budget cap enforced every `GPU_MONITOR_INTERVAL_SECONDS` |
| `GPU_AUTO_START` / `GPU_AUTO_STOP` | independent on/off switches |

None of these ever terminate active inference (`BUSY` state) — they block
*new* work and stop the GPU at the next safe moment instead. See
`apps/control/tests/test_gpu_monitor.py` for the exact behavior under each
combination.

## Backups

`scripts/backup/export_state.py` dumps every persistent table (users,
models, conversations, messages, tasks, gpu_sessions, workers, approvals,
execution_requests, notifications, audit_events) to one JSON file.
`scripts/backup/import_state.py` restores it into a freshly-migrated,
empty database, skipping rows whose primary key already exists (safe to
re-run). The export contains password hashes and full task/conversation
content — store it with the same care as the database file itself.

Cloud GPU disks are ephemeral by design; the persistent network volume
(`GPU_VOLUME_ID`) is what survives a pod restart or termination, not the
export above (that's the control plane's own state, which lives on your
laptop/server regardless of the GPU).

## Runbook

See [`RUNBOOK.md`](RUNBOOK.md) for step-by-step responses to specific
failure conditions.

## Scaling workers

Multiple worker processes can run against the same database with no
additional configuration — task claiming is an atomic conditional `UPDATE`
(`workstation_core/task_service.py::claim_next_task`), so two workers
racing on the same row never both win. `docker compose up --scale worker=3`.
