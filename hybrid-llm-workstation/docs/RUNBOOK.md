# Runbook

Symptom-first. Each entry names what to check and where the relevant code
lives.

## "GPU stuck in ERROR"

1. `GET /api/gpu` — check `error` field for the recorded failure detail
   (`session_metadata.last_error` internally).
2. Common causes: `GPU_TEMPLATE_ID`/`GPU_VOLUME_ID` unset or wrong
   (`gpu/providers/runpod/provider.py::provision`/`start` raise a clear
   message), provider API key invalid/expired, or the pod's health check
   never passed within the boot timeout (`_boot_and_finalize` in
   `apps/control/src/control/gpu/lifecycle.py` — default is
   `min(GPU_MAX_SESSION_MINUTES*60, 600)` seconds).
3. `POST /api/gpu/start` again — restarting from `ERROR` goes straight to
   `STARTING` (skips re-provisioning, since the volume already exists).
4. If the control API process itself was restarted while the GPU was up,
   see `GPULifecycleManager.reconcile_on_startup` — it marks the session
   `ERROR` (not `OFF`) if it can't independently re-verify the provider's
   real state, specifically so you don't get told everything is fine while
   an instance is still running and billing.

## "GPU won't stop"

`POST /api/gpu/stop` returns 409 while status is `BUSY`, `STARTING`,
`BOOTING`, or `PROVISIONING` — this is deliberate (spec: never terminate
active inference). Either wait, or pass `?force=true` if you accept
interrupting in-flight work.

## "Cloud model never appears in the catalogue"

- `POST /api/models/refresh` only discovers cloud models while the GPU is
  `READY`/`BUSY`/`IDLE` (it needs a live endpoint to query). Start the GPU
  first, then refresh.
- Check `CLOUD_LLM_ENGINE` matches what `gpu/image` actually installs
  (`ollama` or `vllm`) — a mismatch means `CloudInferenceClient` speaks the
  wrong protocol to the endpoint.
- A model that was previously discovered stays selectable
  (`status=unavailable`) even with the GPU off — selecting it via
  `POST /api/tasks` is what should bring the GPU back up. If task creation
  is rejected instead, check the model's `environment` field is actually
  `cloud` (local models are correctly always rejected while unavailable).

## "Task stuck in QUEUED forever"

- `GET /health/worker` — if unhealthy, no worker process is running or
  heartbeating. Start one (`make worker-dev`).
- Check the task's `type` — only `chat`, `generate`, and `execution` are
  claimed (`ELIGIBLE_TASK_TYPES` in `worker/src/worker/runner.py`).
- If it's a cloud task, check `GET /api/gpu` — the worker will be blocked
  waiting for `READY` (up to the boot timeout) before it can proceed; a
  GPU stuck in `ERROR` will surface as the task retrying, then failing,
  with that detail in `task.error`.

## "Execution request denied and I don't know why"

`ExecutionRequest.result` is `null` for a `DENIED` request — the reason is
in the corresponding audit trail:
- Control-plane-level denial (out of policy bounds before the agent was
  even contacted): `GET /api/approvals` won't show a row for it at all if
  it was `RESTRICTED`; check `audit_events` (`event_type=execution.denied`).
- Agent-level denial (reached the agent, but its own independent
  classification refused it): only visible in the agent's own local audit
  DB (`local-agent/data/audit.db` by default) — this is intentional, see
  `docs/SECURITY.md`; the control plane only learns "FAILED"/"DENIED", not
  why the agent specifically refused, by design (the agent doesn't leak
  its internal reasoning to a plane it doesn't fully trust).

## "Tests fail locally but pass in CI (or vice versa)"

Check for a real `.env` file in the repo root — `workstation_core.config`
reads it via `pydantic-settings`' `env_file=".env"`, and a developer's own
`OLLAMA_LOCAL_URL`/`CLOUD_LLM_BASE_URL` pointing at something real can leak
into "isolated" tests. Every test conftest pins the externally-reachable
settings to safe, unreachable defaults for exactly this reason
(`apps/control/tests/conftest.py`, `worker/tests/conftest.py`,
`tests/conftest.py`) — if you add a new externally-reachable setting to
`workstation_core/config.py`, add it to those pins too.

## "SQLite 'database is locked'"

Should not happen — `workstation_core/db.py` enables WAL mode and a 5s
busy timeout for exactly this (multiple processes: control API + N
workers, all against one file). If it does happen anyway, check nothing
disabled WAL mode by pointing `DATABASE_URL` at a filesystem that doesn't
support it (some network filesystems don't) — move the DB to local disk,
or migrate to PostgreSQL (the schema was written to support that, see
`docs/OPERATIONS.md`).

## "I need to reset everything"

```bash
rm -f data/workstation.db*
.venv/bin/alembic upgrade head
PYTHONPATH=libs/core:. .venv/bin/python3 database/seeds/seed_admin.py --username <you> --password <pw>
```

Back up first with `make backup` if there's anything you want to keep.
