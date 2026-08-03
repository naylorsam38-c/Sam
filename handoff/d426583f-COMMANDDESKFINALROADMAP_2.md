# COMMAND DESK — FINAL BUILD ROADMAP

**For:** Cowork, working against the real Command Desk repo.
**Supersedes:** `DISPATCH-v4-build-spec.md`. Design reference remains `COMMAND-DESK-v4-policy-and-events.md`.

**Prime directive:** rules that can be enforced must not live in prompts. If a rule ends up only in a system prompt when it could have been code, config, or a DB grant, the step is not done.

**Prerequisites**
- Phase 0 complete: project folder moved out of OneDrive. Do not build against a OneDrive path.
- Anthropic API credit added (required for live calls and AWS deploy, not for steps 1–11).

**Reconcile, don't assume:** the unlimited-agents system (`agent_templates`, `agent_instances`, groups) is already built. Older docs may name tables that don't match the repo (`conversation_group_members`/`conversation_group_messages` vs actual `group_members`/`group_transcript`). Use what's in the repo; note reconciliations in the commit message.

**Do not make design decisions unilaterally.** Anything ambiguous comes back to Sam.

---

## THE OPERATING MODEL (what we're building toward)

Each specialist agent stays in its lane. Billing does billing. Email sends email. They hold no workflow logic, no escalation rules, no knowledge of what happens next. They do one job well and hand back output.

**Hub carries the complexity.** Hub routes work, applies quality standards to what comes back, decides whether it goes forward, goes back for a fix, or comes to Sam. Hub runs two tracks: foreground (responding to Sam, routing new work) and background (working through the event queue until every event is resolved). Hub never lets an event go unfinished.

**Observer sits outside all of it.** Read-only, pull-based, no decision authority. It audits and flags — duplicated effort, stalled patterns, repeated friction — and Hub decides what to do about it.

**Worked example.** A quote is needed. `TaskCreated` fires, Hub routes it to the billing agent, and continues other work. Billing produces the quote and emits `TaskCompleted`. Hub picks it up, checks it against standards — either sends it back to billing for a fix, or surfaces it to Sam: "quote done, send it or hold?" Sam decides, Hub logs the decision and routes to the email agent. The event chain closes. Nothing is dropped along the way.

---

## STEP 1 — Versioning substrate

Nothing else is auditable until this exists. Build it first.

**Create** `core/versioning.py` exposing four semver strings:
- `PROMPT_VERSION` — per agent, from the agent's stored prompt record
- `POLICY_VERSION` — from `policy.yaml`
- `SCHEMA_VERSION` — from the latest applied migration
- `RUNTIME_VERSION` — deployed backend build, from env/build metadata

**Migration `003_version_stamps.sql`:** add `prompt_version`, `policy_version`, `schema_version`, `runtime_version` (`text NOT NULL`) to `tasks`, `lessons`, `patterns`, and to `decisions` and `events` once created. Backfill existing rows with `'0.0.0'` — explicitly marking pre-versioning data rather than pretending.

**Enforcement:** one write helper stamps all four on insert. `NOT NULL` with no default, so an unstamped insert errors rather than silently writing blanks.

**Done when:** a newly created task row carries four non-`0.0.0` version strings without the caller passing them.

---

## STEP 2 — Migrations are reversible and verified

Applies to every migration in this build, retroactively to 001 and 002.

- Every migration file has a matching down script (`003_down.sql` drops what `003` created).
- Migrations apply as an atomic batch — transaction wrapper or deploy lock. All five apply or none do. A failure at `004` must not leave `003` half-applied.
- The deploy records which version it reached. The next attempt resumes from the last successful point, not from zero.
- **Down scripts are tested before anything hits AWS.** In CI: apply all migrations against a clean local DB, roll them all back, assert the DB is clean. One untested down script is the difference between a bad afternoon and a production disaster.

**Done when:** CI runs up-then-down on a clean DB and passes.

---

## STEP 3 — `policy.yaml` + loader

**Create** `core/policy.yaml` — verbatim from v4 §1. Don't paraphrase or "improve" values; if something looks wrong, flag it, don't change it.

Add to the policy file:
```yaml
approval:
  ttl_hours: 72          # pending approvals expire; expiry escalates to Sam
  on_expiry: escalate    # never auto-approve, never silently drop
```

**Create** `core/policy.py`:
- loads and validates at startup; on malformed policy, **refuse to start**. Fail closed — never fall back to defaults.
- `get_escalation_tier(action) -> "silent" | "notify_after" | "require_approval"`
- **unknown action returns `require_approval`.** Single most important line in the file. An action nobody anticipated must never default to permitted.
- `get_priority(task)`, `get_loop_rules()`, `get_observer_thresholds()`, `get_response_mode(events)`, `get_approval_ttl()`
- exposes `POLICY_VERSION` from the file's `policy_version` key

**Done when:** `get_escalation_tier("some_action_that_does_not_exist")` returns `require_approval`, proven by a test.

---

## STEP 4 — Enforcement middleware

The step that makes the rest more than scaffolding.

**Create** `core/enforcement.py`. Every agent action routes through one execution path that checks policy **before** the action runs:
- `silent` → execute, log
- `notify_after` → execute, log, emit event for Hub
- `require_approval` → **do not execute.** Emit `ApprovalRequired`, persist a pending-action record with its TTL, return control to Sam. Executes only on explicit approval, logged with who and when.

**Fail closed on error.** Wrap the policy lookup in explicit error handling. If the check throws — corrupt YAML, missing field, DB timeout — the action **does not execute**. Emit an error event, log with full context, return an error to the caller. If we can't determine permission, deny. Never assume authority on an exception. The middleware is now a single point of failure, so its failure mode must be "nothing happens," not "everything is allowed."

**Audit for bypasses.** Find every place an agent performs a side effect — file write, HTTP call, DB mutation, external message — and route it through this path. Any side effect reachable without passing through `enforcement.py` is a hole. List any that can't be routed yet in the commit message.

**Done when:** a test agent instructed to delete a file cannot delete it without an approval record existing — **even when its prompt is edited to say approval isn't needed.** Prompt says yes, enforcement says no, no happens.

---

## STEP 5 — Event bus

**Create** `core/events.py` implementing the schema in v4 §2 — eleven event types, each with its fields plus `tenant_id` and the four version stamps.

**Migration `004_events.sql`:** `id, type, payload jsonb, tenant_id, created_at`, four version columns, plus:
- `handled_at timestamptz NULL`
- `handled_by text NULL`
- `resolution text NULL` — how it closed: completed, escalated, superseded

Index on `(tenant_id, created_at)`, on `(payload->>'task_id')`, and on `(handled_at) WHERE handled_at IS NULL` — the unhandled-queue lookup runs constantly, so it needs to be cheap.

Hub subscribes. Hub does not poll and does not narrate state it wasn't told about. `hub_response_mode` reads the current event set and returns the mode — Hub does not choose its own verbosity.

**Done when:** a task's full lifecycle is replayable from its event rows alone, with no reference to conversation transcript.

---

## STEP 6 — Hub's event completion guarantee

**No event is ever left unfinished.** This is Hub's core job, not a background nicety.

- Events are async — the emitting action fires and moves on. Hub is not a synchronous bottleneck.
- Hub runs a background processor that queries unhandled events (`handled_at IS NULL`), oldest first, and works each one to a resolution: completed, escalated to Sam, or explicitly superseded. Every close writes `handled_at`, `handled_by`, `resolution`.
- Unhandled events are Hub's **priority** work, but they do **not** block foreground work. Two tracks run in parallel.
- Hub scans for stale events on every turn. A pending `ApprovalRequired` past its TTL is surfaced to Sam and escalated — never auto-approved, never quietly dropped.
- The backlog is monitored. An unhandled count above a threshold, or any event older than the TTL, is itself a reportable condition.

**Done when:** a query for events with `handled_at IS NULL` older than the TTL returns zero rows during normal operation, and any row that does appear has been surfaced to Sam.

---

## STEP 7 — Observer isolation at the DB level

**Create a distinct DB role** `observer_readonly` with `SELECT` only on `lessons`, `patterns`, `monthly_summaries`, `tasks`, `task_messages`, `agent_instances`, and the agent prompt table. No `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE` anywhere. Revoke default public grants explicitly rather than assuming they're absent.

Observer's connection uses that role and no other. Credentials live in AWS Secrets Manager, never in the DB or app config. Role creation and grants ship as a migration step so it's reproducible, not a manual console action.

**Done when:** an `INSERT` on Observer's connection raises a permission error **from Postgres**, not caught by application code. Prove it with a test that attempts the write and asserts the failure.

Why this one specifically: it's the only guarantee that survives prompt injection. Everything else assumes the model is behaving.

---

## STEP 8 — Observer thresholds as SQL

**Create** `sql/observer_thresholds.sql` — five parameterised queries, thresholds injected from `policy.yaml`, never hardcoded:

1. `duplicated_effort` — same problem in ≥3 lessons, no promoted pattern
2. `role_drift` — ≥2 consecutive tasks where `role_drift = true` for one instance
3. `stalled_pattern` — pattern age ≥30 days, `is_stale = true`, not reconfirmed
4. `repeated_friction` — same Tester FAIL reason across ≥2 distinct tasks
5. `unactioned_opportunity` — ≥3 lessons from ≥2 distinct agents, no linked task

Observer receives rows. Observer does **not** decide whether a threshold was met — the query decides; Observer explains what the rows mean. Rows → Confirmed Finding. Below threshold → Emerging Signal. Zero rows → "Nothing crossed threshold this period," a complete answer, not a failure.

**Done when:** changing a threshold value in `policy.yaml` changes query behaviour with no code edit.

---

## STEP 9 — Decisions table

**Migration `005_decisions.sql`:**
```
id, decision, reason, evidence_refs[], agent_id, confidence_evidence,
confidence_reasoning, confidence_execution, prompt_version, policy_version,
schema_version, runtime_version, created_at, tenant_id
```

RLS scoped to `current_setting('app.tenant_id', true)`, matching `002_rls_new_tables.sql`.

`evidence_refs` accepts only `task_id`, `task_message_id`, `lesson_id`, `pattern_id`, `file_ref`. **Reject writes with empty `evidence_refs`** — a decision with no evidence isn't recorded as a decision. Three confidence values stored separately; never averaged into one number.

---

## STEP 10 — Health as counts

Replace every health percentage with a real count query per v4 §5: milestones, risks, test coverage, documentation, knowledge, roadmap drift events, loop efficiency (with `n`).

**Rule:** if a number can't be computed from a live query, it isn't displayed. No estimates. No percentage without numerator and denominator both visible. Empty query result shows "no data" — never `0%`, never `100%`.

---

## STEP 11 — Semantic judgments as boolean fields

Three judgments stay with the model because no config resolves them. Each is written back as a discrete field; policy — not the model — decides the consequence:

- `drift_detected` → policy: `halt_and_require_approval`
- `same_issue_as_prior` → policy: early-break at round 3, `halt_and_escalate`
- `role_drift` → policy: counter, threshold at 2 consecutive tasks

Add these columns to the relevant task/loop tables. The model writes the field; the model does not act on it. Hub's prompt contains the judgment, never the consequence.

---

## STEP 12 — Prompt editor version bumping

The live prompt editor (backend GET/PUT per agent, Sam-auth-gated, wired into the Flutter app) must:
- bump `prompt_version` on every save
- keep all prior versions immutable and retrievable
- reject a save that would overwrite without a version bump

**Done when:** editing Hub's prompt, then pulling a task created before the edit, shows the *old* `prompt_version` on that task, and the old prompt text is still retrievable.

---

## STEP 13 — Slim the prompts

Only after steps 1–12 pass. **Exact drop-in text is in `PROMPTS-final-hub-and-observer.md`** — use that file, not v4 §3/§4, which predates the two Hub additions below:

1. **Event completion duty** — Hub processes unhandled events to resolution in the background; no event is left unfinished; foreground work is never blocked by the queue.
2. **Quality gate on returned work** — specialist output comes back to Hub, and Hub decides: forward it, return it to the specialist for a fix, or surface it to Sam for a call. Specialists don't decide what happens to their own output.

Then audit: for every remaining sentence in either prompt, ask whether it's enforced somewhere. If yes, delete it from the prompt — a rule stated in two places drifts out of sync. What remains should be only role, judgment ownership, event duty, quality-gate authority, and provenance discipline.

Prompts get shorter with each pass, not more polished.

---

## STEP 14 — Terraform / RLS / deploy

Write fresh — the repo has no existing Terraform. Apply migrations in order: `001` → `002` → `003` → `004` → `005`, atomically, using whatever mechanism the stack already uses for post-RDS migration SQL. Don't introduce a second mechanism. Include `observer_readonly` role creation and grants as a migration step. Down scripts ship alongside and are exercised in CI before deploy.

---

## ACCEPTANCE — the tests that prove it works

1. Unknown action → `require_approval`, not permitted.
2. `require_approval` action blocked at the execution layer **with a prompt telling the model approval isn't needed**.
3. An exception thrown inside the policy check blocks the action rather than permitting it.
4. Observer's connection refused an `INSERT` **by Postgres**, not by app code.
5. Task lifecycle fully replayable from `events` rows with no transcript.
6. Zero unhandled events older than the approval TTL during normal operation.
7. A task created before a prompt edit still reports the pre-edit `prompt_version`.
8. CI applies all migrations to a clean DB and rolls them all back cleanly.

If any of the eight fails, the step it belongs to isn't done, regardless of what else works.

---

## REPORT BACK

- Which side effects couldn't be routed through `enforcement.py`, if any
- Table-name reconciliations made
- Any place the repo already implements part of this differently — flag it, don't silently replace working code
- Anything ambiguous comes back to Sam rather than being decided in the build
