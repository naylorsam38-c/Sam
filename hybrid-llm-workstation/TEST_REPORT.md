# Test Report

## Results

```
apps/control/tests/   41 tests
worker/tests/         11 tests
local-agent/tests/    16 tests
tests/unit/           37 tests
tests/security/        8 tests
tests/integration/     2 tests
tests/e2e/              1 test
tests/acceptance/     35 tests
-----------------------------
Total                151 tests — 146 passed, 5 skipped, 0 failed
```

Run with: `make test`, or
`pytest apps/control/tests worker/tests local-agent/tests tests -q`.

Last run in this build environment: 146 passed, 5 skipped, 0 failed, in
~109 seconds.

## What "skipped" means here

Every skip names, in the test itself, exactly why and points to where the
behavior *is* verified another way. None are placeholders for untested
code:

- `TestLocalLLM::test_open_webui_opens` — needs a real browser.
- `TestLocalLLM::test_conversations_persist` — Open WebUI's own
  responsibility (see `BUILD_REPORT.md`); our equivalent (task
  input/result persistence) is verified elsewhere in the same file.
- `TestGPULifecycle::test_idle_timeout_and_autostop` — time-based;
  verified deterministically (without a real-time wait) in
  `apps/control/tests/test_gpu_monitor.py`.
- `TestLocalExecutionAgent::test_requests_are_authenticated` — covered
  exhaustively in `local-agent/tests/test_execute.py`.
- `TestLocalExecutionAgent::test_cloud_llm_cannot_bypass_the_agent` —
  structurally verified in `local-agent/tests/test_audit_and_bypass.py`
  and `tests/integration/test_control_to_real_agent.py`, not re-run here.

## Real bugs found and fixed during this build

Listed because a report that only shows passing tests after the fact is
not evidence of a careful build — these are the defects the process
actually caught, in the order found:

1. **Illegal task transition on pause.** `QUEUED → PAUSED` wasn't in the
   task state machine's transition table; pausing a freshly-created task
   raised instead of pausing it. Fixed by adding the transition; caught by
   `apps/control/tests/test_tasks.py::test_pause_then_resume_requeues_task`.
2. **`BUSY → STOPPING` missing from the GPU transition table.** A
   force-stop while the GPU was mid-inference would have raised an
   "illegal transition" error instead of stopping it. Fixed in
   `workstation_core/enums.py`.
3. **Un-awaited coroutine on the TRUSTED policy path.**
   `execution_service.submit_request` was a sync function that, for
   `TRUSTED`-level operations, returned `execute_now(...)` — a coroutine
   object, never awaited, so a "trusted" operation silently never ran
   while the API reported success. No default policy ships as TRUSTED, so
   this had zero real-world exposure until someone opted an operation into
   it — but it would have silently done nothing when they did. Fixed by
   making `submit_request` async; caught by a new regression test
   (`apps/control/tests/test_execution_trusted_path.py`) written
   specifically because the existing suite had no TRUSTED-level coverage.
4. **Execution-type tasks routed through model resolution they don't
   need.** Both `POST /api/tasks` and the worker unconditionally tried to
   resolve a `model_id`/`environment` for every task type, so any
   `type: "execution"` task failed immediately with "explicit choice
   required" before ever reaching the agent. Fixed by branching on task
   type before routing.
5. **Task/execution-request state desync after approval.** Approving an
   execution request tied to a task never updated the task's own status —
   it stayed at `REQUIRES_APPROVAL` forever even after the underlying work
   completed. Fixed by adding `execution_service._sync_task`, called after
   every status change to an `ExecutionRequest`; verified by
   `worker/tests/test_execution_task_approval_resume.py`.
6. **Worker didn't check model availability before use.** A model deleted
   or marked unavailable between task creation and worker pickup would
   have been used anyway, failing with a raw connection error instead of a
   clear message. Fixed, then immediately had to be *partially reverted*
   (see bug 9) once cold-start cloud behavior was tested for real.
7. **`DetachedInstanceError` in the worker's claim loop.** A second
   `db.commit()` inside the same session expired the just-claimed `Task`
   object's attributes before they were read outside the `with` block.
   Fixed by capturing `task.id` before the second commit.
8. **`read_file` crashed on every call.** It didn't accept the `timeout`
   kwarg the agent's dispatch table passes uniformly to every operation
   handler (the other five handlers already had a `**_` catch-all; this
   one didn't). Caught immediately by `local-agent/tests/test_execute.py`.
9. **Cloud models could never be selected while the GPU was off — making
   "select a cloud model" → "GPU starts" impossible.** Found only by
   manually driving the real running stack end to end (not by the pytest
   suite, which hadn't exercised a true cold start): both `routing_service`
   and the worker required a model's DB status to already be `available`,
   which for a cloud model is only ever true while the GPU is already up.
   Fixed by allowing an explicitly-selected cloud model to be used
   regardless of its current status (a local model still requires
   `available` — nothing will make Ollama have a model it doesn't have).
   Added regression tests at both the API and worker level.
10. **Model registry (and `/health/cloud`) never used the GPU's live
    endpoint.** `CLOUD_LLM_BASE_URL` is meant to be a *static override*;
    normally it's unset, since a real provider hands out a new IP every
    session. Without a fallback, cloud models could never be discovered
    at all with any provider that isn't statically addressed — i.e. every
    real one. Fixed by falling back to
    `gpu_sessions.session_metadata.endpoint` when the static URL is unset.
11. **`.env.example`'s `DATABASE_URL` default was Docker-only.** Its
    absolute path (`sqlite:////data/workstation.db`) is only writable
    inside the container volume `docker-compose.yml` mounts; every native
    (non-Docker) run failed with `unable to open database file`. Found by
    actually running `scripts/dev/bootstrap.sh` end to end. Fixed by
    commenting it out for the native default and documenting the
    Docker-specific override.
12. **Test isolation leak from a real `.env` file.** Once a real `.env`
    was created for the manual smoke-testing pass above, one control-API
    test started reading the *real* `OLLAMA_LOCAL_URL` it pointed at
    instead of the intended "nothing is listening here" default, because
    `pydantic-settings` reads any `.env` file present in the working
    directory regardless of test isolation intent. Fixed by pinning every
    externally-reachable setting explicitly in each test suite's `app_env`
    fixture; verified by re-running the full suite with a real `.env`
    file still present in the repo root.
13. **Directory listing crashed on any non-empty directory.** `list_directory`
    built a Python `set` of dicts (dicts aren't hashable) instead of a
    list. Caught immediately by `local-agent/tests/test_execute.py`.
14. **Agent audit log's primary key collided on a retried/duplicate
    `request_id`.** Used the client-supplied `request_id` as the audit
    row's own id, so the second call with the same id crashed with a
    `UNIQUE constraint failed` instead of just logging a second row. Fixed
    by generating a fresh id per audit row.

Items 6/9 illustrate the value of the manual, real-process pass beyond the
pytest suite: pytest never exercised a genuine cold start (GPU off, model
never before discovered by that specific test's database), so bug 9 wasn't
caught until the system was actually run and used end to end.

## What the tests deliberately do *not* fake

- No test asserts against a hand-written mock return value standing in for
  an HTTP response — every HTTP-speaking component (Ollama, the cloud
  engine, the control API, the local agent, RunPod) is tested against
  either a real socket (a real local HTTP server, even when it's a
  lightweight stand-in for Ollama or a cloud GPU) or, for RunPod
  specifically, `respx`-mocked HTTP matching its documented response
  shape (disclosed as such — see `BUILD_REPORT.md`'s "Not verified").
- Concurrency (`claim_next_task`'s atomic claim) is tested by actually
  racing two claims against the same row, not by asserting the SQL looks
  right.
- The security suite's injection tests submit real SQL-injection-shaped
  strings through real endpoints and check the database is still intact
  afterward, not just that some sanitizer function returns `True`.
