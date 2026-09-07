# Build Report

## Scope delivered

Every component listed in the build spec's section 26 ("Required
deliverables from builder") exists in this repository and is exercised by
automated tests against real running processes, not mocked internals,
wherever the build environment allowed it:

| Deliverable | Location | Status |
|---|---|---|
| Complete source tree | `apps/`, `worker/`, `local-agent/`, `gpu/`, `libs/` | Done |
| Database migrations | `database/migrations/` (Alembic, one migration covering all 11 tables) | Done, applied and rolled back clean in this environment |
| Configuration templates | `.env.example`, `config/*.yaml` | Done |
| Docker/deployment configuration | `docker-compose.yml`, 3 Dockerfiles | Done, `docker compose config` validated in this environment; full `docker compose up` **not** run here (see "Not verified" below) |
| Open WebUI configuration | `docker-compose.yml` + `docs/OPERATIONS.md` | Done — see "Not verified" |
| Ollama integration | `workstation_core/ollama_client.py` | Done, tested against a real (fake but protocol-real) Ollama HTTP server |
| Cloud GPU adapter | `gpu/providers/{mock,runpod}` | `mock` fully verified end-to-end; `runpod` unit-tested against mocked HTTP (no live account available — see "Not verified") |
| GPU lifecycle implementation | `apps/control/src/control/gpu/lifecycle.py` | Done, full state machine + idle timeout + cost caps verified |
| Background worker | `worker/` | Done, verified against real local, cold-start cloud, and execution-agent task types |
| Task queue | DB-backed, `workstation_core/task_service.py` | Done, atomic-claim race verified |
| Local execution agent | `local-agent/` | Done, independent policy enforcement verified |
| Approval system | `workstation_core/execution_service.py` + agent-side re-check | Done |
| Notifications | `workstation_core/notification_service.py` | Done |
| Audit logging | `audit_events` table (control plane) + separate SQLite (agent) | Done |
| Automated tests | `tests/`, plus per-app test dirs | 151 tests (146 pass, 5 explicitly skipped) |
| Installation scripts | `scripts/install/phase_{a,b,c,d}_*` | Done, phases A/C/D run for real in this environment; phase B's cloud-cost-incurring steps deliberately require explicit confirmation and were not run against a real account |
| Health checks | `scripts/health/` | Done, run for real against a live stack in this environment |
| Operations documentation | `docs/OPERATIONS.md`, `docs/RUNBOOK.md` | Done |
| Security documentation | `docs/SECURITY.md` | Done |
| README | `README.md` | Done |

## What was actually run in this build environment

This environment has no GPU, no cloud account, no Ollama installation, and
no browser. Rather than skip verification, the build stood in a real
Ollama-protocol-compatible HTTP server (`tests/support/fake_ollama.py`,
also usable as `GPU_PROVIDER=mock`, which runs a genuine local server) for
"an Ollama/cloud engine that responds correctly," and confirmed every
component against **that real server**, over real sockets, rather than
mocking the client code that talks to it. Concretely, in one continuous
session:

- Bootstrapped a fresh `.env`, ran migrations, seeded an admin user.
- Started a real control API (`uvicorn`), a real worker (`worker.main`), a
  real local execution agent (`uvicorn`), and a fake local Ollama server —
  four real, independent OS processes talking to each other over HTTP and
  a shared SQLite database.
- Ran `scripts/health/check_all.sh` against them.
- Ran `scripts/install/phase_c_tasks.py` (local chat task, cold-start
  cloud task with the mock GPU provider, notification check) — all passed.
- Ran `scripts/install/phase_d_agent.py` (pairing, harmless read,
  approval flow, denied path, authorized command, audit trail) — all
  passed.
- Inspected the agent's own SQLite audit log directly and confirmed every
  call it actually received was recorded, and that calls denied at the
  control-plane level never reached it at all (as designed).
- Ran `scripts/backup/export_state.py` and `scripts/backup/import_state.py`
  in a round trip into a second, empty database and confirmed the data
  matched.
- Ran `scripts/health/gpu_smoke_test.sh` (start → READY → cost report →
  stop → OFF) against the mock provider.

This manual pass, run *in addition to* the pytest suite, found and fixed
four real bugs that the pytest suite alone had not (see `TEST_REPORT.md`
for the full list) — most notably that `.env.example`'s default
`DATABASE_URL` was a Docker-only path that broke every native run, and that
the model registry never fell back to the GPU's live endpoint, which would
have made cloud models permanently undiscoverable with any provider that
doesn't hand out a static IP (i.e. every real one).

## Not verified (requires hardware this environment doesn't have)

Stated plainly rather than assumed:

- **A real RunPod account.** `gpu/providers/runpod/provider.py` is unit
  tested against RunPod's documented GraphQL response shapes
  (`tests/unit/test_gpu_runpod.py`), but has never made a real API call.
  Run `scripts/install/phase_b_cloud.sh` and `make gpu-smoke-test` (with
  `WORKSTATION_CONFIRM_GPU_COST=yes`) against a real account before
  trusting it in production.
- **A real Ollama installation.** All Ollama-protocol interaction is
  verified against a real HTTP server implementing that protocol; the
  actual `ollama` binary and its GPU-accelerated inference were never
  exercised.
- **Open WebUI itself.** The reverse-proxy endpoint it would talk to
  (`/proxy/cloud`) is tested directly; the Open WebUI container's own
  behavior (does its Admin Settings UI actually accept and use the
  connection as documented) was not — `docker compose config` validates
  the compose file's syntax, not the running container.
- **A browser.** Nothing here can substitute for actually opening Open
  WebUI in a browser and chatting.

## Deviations from the spec's literal text (all disclosed inline in code/docs)

- `CONTROL_API_URL` and `OPEN_WEBUI_PROXY_TOKEN` are additional env vars
  beyond spec section 4's literal list — both are architecturally
  necessary (the worker needs to reach the control API; Open WebUI needs a
  stable cloud endpoint) and documented in `.env.example`.
- `gpu/providers/lambdalabs/` rather than `lambda/` (`lambda` is a Python
  keyword) — see `docs/ARCHITECTURE.md`.
- The `conversations`/`messages` tables exist (migrated, in the schema)
  but have no dedicated CRUD endpoints — spec section 14's endpoint list
  doesn't include any, and the primary interactive-chat surface (Open
  WebUI) persists its own conversations in its own database. See
  `tests/acceptance/test_acceptance_checklist.py::TestLocalLLM::test_conversations_persist`.
