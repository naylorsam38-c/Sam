# DISPATCH — COMMAND DESK v4 ENFORCEMENT BUILD

**For:** Cowork, working against the real Command Desk repo.
**Source of truth for design:** `COMMAND-DESK-v4-policy-and-events.md`. This document is the execution order and acceptance criteria for that design.

**Prime directive:** rules that can be enforced must not live in prompts. If a rule ends up only in a system prompt when it could have been code, config, or a DB grant, the step is not done.

**Before starting:** confirm Phase 0 (project folder moved out of OneDrive) is complete. Do not build against a OneDrive path.

**Reconcile, don't assume:** the unlimited-agents system (`agent_templates`, `agent_instances`, groups) is already built. Table names in older docs may not match the repo (`conversation_group_members`/`conversation_group_messages` vs actual `group_members`/`group_transcript`). Use what's actually in the repo and note the reconciliation in the commit message.

---

## STEP 1 — Versioning substrate

Nothing else is auditable until this exists. Build it first.

**Create** `core/versioning.py` exposing four semver strings:

- `PROMPT_VERSION` — per agent, read from the agent's stored prompt record
- `POLICY_VERSION` — read from `policy.yaml`
- `SCHEMA_VERSION` — read from the latest applied migration
- `RUNTIME_VERSION` — the deployed backend build (from env/build metadata)

**Migration `003_version_stamps.sql`:** add `prompt_version`, `policy_version`, `schema_version`, `runtime_version` (all `text NOT NULL`) to `tasks`, `lessons`, `patterns`, and (once created) `decisions` and `events`. Backfill existing rows with `'0.0.0'` — explicitly marking pre-versioning data rather than pretending.

**Enforcement:** a single write helper that stamps all four on insert. Direct inserts that bypass it should fail — add a `NOT NULL` constraint with no default so an unstamped insert errors rather than silently writing blanks.

**Done when:** a newly created task row carries four non-`0.0.0` version strings without the caller passing them.

---

## STEP 2 — `policy.yaml` + loader

**Create** `core/policy.yaml` — verbatim from v4 §1. Do not paraphrase or "improve" the values; if something looks wrong, flag it, don't change it.

**Create** `core/policy.py`:

- loads and validates `policy.yaml` at startup; on malformed policy, refuse to start (fail closed, never fall back to defaults)
- exposes `get_escalation_tier(action) -> "silent" | "notify_after" | "require_approval"`
- **unknown action returns `require_approval`.** This is the single most important line in the file. An action nobody anticipated must never default to permitted.
- exposes `get_priority(task)`, `get_loop_rules()`, `get_observer_thresholds()`, `get_response_mode(events)`
- exposes `POLICY_VERSION` from the file's `policy_version` key

**Done when:** `get_escalation_tier("some_action_that_does_not_exist")` returns `require_approval`, proven by a test.

---

## STEP 3 — Enforcement middleware

This is the step that makes the whole thing real. Everything else is scaffolding around it.

**Create** `core/enforcement.py`. Every agent action routes through one execution path, and that path checks policy **before** the action runs:

- `silent` → execute, log
- `notify_after` → execute, log, emit event for Hub
- `require_approval` → **do not execute.** Emit `ApprovalRequired`, persist a pending-action record, return control to Sam. The action executes only on explicit approval, and the approval is logged with who/when.

**Non-negotiable:** the block happens in the execution layer, not by asking the model to hold back. A compromised or confused model calling `spend_money` must hit a wall.

**Audit for bypasses:** find every place an agent currently performs a side effect (file write, HTTP call, DB mutation, external message) and route it through this path. Any side effect reachable without passing through `enforcement.py` is a hole. List them in the commit message if any can't be routed yet.

**Done when:** a test agent instructed to delete a file cannot delete it without an approval record existing — even when its prompt is edited to say approval isn't needed. That's the test that matters: prompt says yes, enforcement says no, no happens.

---

## STEP 4 — Event bus

**Create** `core/events.py` implementing the schema in v4 §2 — eleven event types, each with its fields plus `tenant_id` and the four version stamps.

**Persist events** to an `events` table (migration `004_events.sql`): `id, type, payload jsonb, tenant_id, created_at`, plus the four version columns. Index on `(tenant_id, created_at)` and on `(payload->>'task_id')`.

**Hub subscribes.** Hub does not poll and does not narrate state it wasn't told about. `hub_response_mode` reads the current event set and returns the mode — Hub does not choose its own verbosity.

**Done when:** a task's full lifecycle is replayable from its event rows alone, with no reference to conversation transcript.

---

## STEP 5 — Observer isolation at the DB level

**Create a distinct DB role** `observer_readonly` with `SELECT` only on `lessons`, `patterns`, `monthly_summaries`, `tasks`, `task_messages`, `agent_instances`, and the agent prompt table. No `INSERT`, `UPDATE`, `DELETE`, or `TRUNCATE` anywhere. Revoke default public grants explicitly rather than relying on them being absent.

Observer's connection uses that role's credentials and no other. Credentials live in AWS Secrets Manager, never in the DB or app config.

**Done when:** an `INSERT` issued on Observer's connection raises a permission error from Postgres. Not caught by application code — refused by the database. Prove it with a test that attempts the write and asserts the failure.

Why this specifically: it's the one guarantee that survives prompt injection. Everything else assumes the model is behaving.

---

## STEP 6 — Observer thresholds as SQL

**Create** `sql/observer_thresholds.sql` — five parameterised queries, thresholds injected from `policy.yaml`, never hardcoded:

1. `duplicated_effort` — same problem in ≥3 lessons with no promoted pattern
2. `role_drift` — ≥2 consecutive tasks where `role_drift = true` for one instance
3. `stalled_pattern` — pattern age ≥30 days, `is_stale = true`, not reconfirmed
4. `repeated_friction` — same Tester FAIL reason across ≥2 distinct tasks
5. `unactioned_opportunity` — ≥3 lessons from ≥2 distinct agents with no linked task

Observer receives rows. Observer does **not** decide whether a threshold was met — the query decides; Observer explains what the rows mean. Rows → Confirmed Finding. Below threshold → Emerging Signal. Zero rows → "Nothing crossed threshold this period," which is a complete answer, not a failure.

**Done when:** changing a threshold value in `policy.yaml` changes query behaviour with no code edit.

---

## STEP 7 — Decisions table

**Migration `005_decisions.sql`:**

```
id, decision, reason, evidence_refs[] , agent_id, confidence_evidence,
confidence_reasoning, confidence_execution, prompt_version, policy_version,
schema_version, runtime_version, created_at, tenant_id
```

RLS policy scoped to `current_setting('app.tenant_id', true)`, matching the pattern in `002_rls_new_tables.sql`.

`evidence_refs` accepts only `task_id`, `task_message_id`, `lesson_id`, `pattern_id`, `file_ref` per the provenance policy. **Reject writes with an empty `evidence_refs`** — a decision with no evidence doesn't get recorded as a decision. Three confidence values are stored separately; do not average them into one number.

---

## STEP 8 — Health as counts

Replace every health percentage with a real count query per v4 §5. Milestones, risks, test coverage, documentation, knowledge, roadmap drift events, loop efficiency (with `n`).

**Rule:** if a number can't be computed from a live query, it isn't displayed. No estimates. No percentage without its numerator and denominator both visible. If the query returns nothing, show "no data" — never `0%` and never `100%`.

---

## STEP 9 — Semantic judgments as boolean fields

Three judgments stay with the model because no config can resolve them. Each is written back as a discrete field, and policy — not the model — decides the consequence:

- `drift_detected` → policy: `halt_and_require_approval`
- `same_issue_as_prior` → policy: early-break at round 3, `halt_and_escalate`
- `role_drift` → policy: counter, threshold at 2 consecutive tasks

Add these columns to the relevant task/loop tables. The model writes the field; the model does not act on it. Hub's prompt must not contain the consequence — only the judgment.

---

## STEP 10 — Prompt editor version bumping

The live prompt editor (backend GET/PUT per agent, Sam-auth-gated, wired into the Flutter app) must:

- bump `prompt_version` on every save
- keep all prior versions immutable and retrievable
- reject a save that would silently overwrite without a version bump

**Done when:** editing Hub's prompt, then pulling a task created before the edit, shows the *old* `prompt_version` on that task and the old prompt text is still retrievable.

---

## STEP 11 — Slim the prompts

Only after steps 1–10 pass. Replace Hub and Observer prompts with the slimmed versions in v4 §3 and §4.

Then audit: for every remaining sentence in either prompt, ask whether it is enforced somewhere. If yes, delete it from the prompt — a rule stated in two places drifts out of sync. What remains should be only role, judgment ownership, and provenance discipline.

The prompts should get shorter with each pass, not more polished.

---

## STEP 12 — Terraform / RLS

Write fresh (repo has no existing Terraform). Apply migrations in order: `001_migration.sql` → `002_rls_new_tables.sql` → `003` → `004` → `005`. Match whatever mechanism the stack uses for applying migration SQL after RDS comes up; don't introduce a second one. Include the `observer_readonly` role creation and grants as a migration step so it's reproducible, not a manual console action.

---

## ACCEPTANCE — the five tests that prove it works

1. Unknown action → `require_approval`, not permitted.
2. `require_approval` action blocked at execution layer **with a prompt that tells the model approval isn't needed**.
3. Observer's connection refused an `INSERT` **by Postgres**, not by app code.
4. Task lifecycle fully replayable from `events` rows with no transcript.
5. A task created before a prompt edit still reports the pre-edit `prompt_version`.

If any of the five fails, the step it belongs to isn't done, regardless of what else works.

---

## REPORT BACK

- Which side effects couldn't be routed through `enforcement.py`, if any
- Table-name reconciliations made
- Any place the repo already implements part of this differently — flag it, don't silently replace working code
- Do **not** make design decisions unilaterally. Anything ambiguous comes back to Sam.
